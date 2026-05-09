# tabs/scanner/scanner_core.py
import threading
import concurrent.futures
import random
import ipaddress
import time
import socket
import struct
import requests
import urllib3
from .scanner_utils import ScannerUtils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import socks
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False

CF_API_URL = "https://raw.githubusercontent.com/vfarid/cf-ip-scanner/main/ipv4.txt"
TIMEOUT = 3
TEST_DL_LIMIT_KB = 50
TEST_UL_SIZE_KB = 15

# ثابت‌های SOCKS5
SOCKS_VERSION = 0x05
SOCKS_CMD_CONNECT = 0x01
SOCKS_ATYP_IPV4 = 0x01
SOCKS_ATYP_DOMAIN = 0x03
SOCKS_ATYP_IPV6 = 0x04
SOCKS_AUTH_NONE = 0x00

class ScannerCore:
    def __init__(self):
        self.stop_event = threading.Event()
        self.best_pairs = []
        self.completed_tasks = 0
        self.total_tasks = 0
        self.results_lock = threading.Lock()
        self.dns_list = []
        self.custom_ports = []
        self.custom_cidrs = []
        self.entry_host = ""
        self.entry_path = ""
        self.var_tls = None
        self.var_none = None
        self.var_h2 = None
        self.var_http1 = None
        self.var_ws = None
        self.var_grpc = None
        self.var_tcp = None
        self.fragment_settings = {"packets": "1-1", "length": "100-200", "interval": "1"}
        self.log_callback = None
        self.progress_callback = None
        self.proxy_address = None   # e.g. "socks5://127.0.0.1:10815"

    def set_callbacks(self, log_callback, progress_callback):
        self.log_callback = log_callback
        self.progress_callback = progress_callback

    def log(self, text):
        if self.log_callback:
            self.log_callback(text)

    def update_progress(self, completed, total, found):
        if self.progress_callback:
            self.progress_callback(completed, total, found)

    # ----- SOCKS5 Client Helper -----
    def _connect_socks5(self, target_host, target_port, timeout=TIMEOUT):
        if not self.proxy_address:
            raise ValueError("SOCKS5 proxy address not set")

        proxy_url = self.proxy_address
        if proxy_url.startswith("socks5://"):
            proxy_url = proxy_url[9:]
        proxy_host, _, proxy_port_str = proxy_url.partition(':')
        proxy_port = int(proxy_port_str) if proxy_port_str else 1080

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((proxy_host, proxy_port))

        # 1. Handshake
        sock.sendall(struct.pack('BBB', SOCKS_VERSION, 1, SOCKS_AUTH_NONE))
        resp = sock.recv(2)
        if len(resp) != 2 or resp[0] != SOCKS_VERSION or resp[1] != SOCKS_AUTH_NONE:
            sock.close()
            raise ConnectionError("SOCKS5 handshake failed")

        # 2. Request
        try:
            ip_bytes = socket.inet_pton(socket.AF_INET, target_host)
            addr_type = SOCKS_ATYP_IPV4
            addr_data = ip_bytes
        except socket.error:
            addr_type = SOCKS_ATYP_DOMAIN
            domain_bytes = target_host.encode()
            addr_data = len(domain_bytes).to_bytes(1, 'big') + domain_bytes

        port_bytes = struct.pack('>H', target_port)
        request = struct.pack('BBBB', SOCKS_VERSION, SOCKS_CMD_CONNECT, 0, addr_type) + addr_data + port_bytes
        sock.sendall(request)

        # 3. Receive response
        resp = sock.recv(4)
        if len(resp) < 4 or resp[0] != SOCKS_VERSION or resp[1] != 0x00:
            sock.close()
            raise ConnectionError("SOCKS5 connect request failed")
        atyp = resp[3]
        if atyp == SOCKS_ATYP_IPV4:
            sock.recv(4)
        elif atyp == SOCKS_ATYP_DOMAIN:
            length = ord(sock.recv(1))
            sock.recv(length)
        elif atyp == SOCKS_ATYP_IPV6:
            sock.recv(16)
        else:
            sock.close()
            raise ConnectionError("Unknown address type in SOCKS5 response")
        sock.recv(2)  # port

        return sock

    def _wrap_socket_proxy(self, host, port, timeout=TIMEOUT):
        if self.proxy_address:
            return self._connect_socks5(host, port, timeout)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            return sock

    # ---------- Worker handshake ----------
    def test_worker_handshake(self, ip, port):
        try:
            path = self.entry_path
            if not path.startswith("/"): path = "/" + path
            url = f"http://{ip}:{port}{path}"
            headers = {
                "Host": self.entry_host,
                "User-Agent": "Mozilla/5.0",
                "Connection": "Upgrade",
                "Upgrade": "websocket"
            }
            proxies = None
            if self.proxy_address and HAS_SOCKS:
                proxies = {'http': self.proxy_address, 'https': self.proxy_address}
            resp = requests.get(url, headers=headers, timeout=2, allow_redirects=False, proxies=proxies)
            if resp.status_code == 101 or (
                "cloudflare" in resp.headers.get("Server", "").lower()
                and resp.status_code in [200, 400, 403, 404]):
                return True
        except:
            pass
        return False

    def find_working_port(self, ip, port_list):
        ports_to_check = list(port_list)
        random.shuffle(ports_to_check)
        found_port = None

        def worker():
            nonlocal found_port
            while ports_to_check and not self.stop_event.is_set() and found_port is None:
                try:
                    port = ports_to_check.pop()
                except IndexError:
                    break
                try:
                    with self._wrap_socket_proxy(ip, port, 1.0) as s:
                        pass
                    if self.test_worker_handshake(ip, port):
                        if found_port is None:
                            found_port = port
                        break
                except:
                    pass

        threads = []
        for _ in range(min(10, len(ports_to_check))):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        return found_port

    def perform_ping_twice(self, ip, port):
        avg_ping, valid = 0, 0
        for _ in range(2):
            if self.stop_event.is_set(): return 9999
            start = time.time()
            try:
                with self._wrap_socket_proxy(ip, port, TIMEOUT) as s:
                    pass
                avg_ping += int((time.time() - start) * 1000)
                valid += 1
            except:
                pass
        return int(avg_ping / valid) if valid > 0 else 9999

    def perform_speed_test(self, ip, port, host_header):
        try:
            headers = {'Host': host_header, 'User-Agent': 'Mozilla/5.0'}
            path = self.entry_path
            if not path.startswith("/"): path = "/" + path
            req_path = f"/__down?bytes={TEST_DL_LIMIT_KB * 1024}" if "speed.cloudflare.com" in host_header else path
            url = f"http://{ip}:{port}{req_path}"
            proxies = None
            if self.proxy_address and HAS_SOCKS:
                proxies = {'http': self.proxy_address, 'https': self.proxy_address}

            st = time.time()
            r = requests.get(url, headers=headers, timeout=4, stream=True, proxies=proxies)
            size = 0
            for chunk in r.iter_content(1024):
                if self.stop_event.is_set(): return 0, 0
                size += len(chunk)
                if size > TEST_DL_LIMIT_KB * 1024: break
            dl_t = max(time.time() - st, 0.01)
            dl_s = round((size / 1024) / dl_t, 1)

            st_ul = time.time()
            try:
                if not self.stop_event.is_set():
                    up_path = "/__up" if "speed.cloudflare.com" in host_header else path
                    up_url = f"http://{ip}:{port}{up_path}"
                    requests.post(up_url, headers=headers, data=b'0' * (TEST_UL_SIZE_KB * 1024), timeout=4,
                                  proxies=proxies)
            except:
                pass
            ul_t = max(time.time() - st_ul, 0.01)
            ul_s = round(TEST_UL_SIZE_KB / ul_t, 1)
            return dl_s, ul_s
        except:
            return 0, 0

    def process_ip(self, ip, port_list):
        if self.stop_event.is_set():
            return

        working_port = self.find_working_port(ip, port_list)
        if not working_port:
            return

        avg_ping = self.perform_ping_twice(ip, working_port)
        if avg_ping > 1500:
            return

        best_combo = None
        max_dl = -1
        min_ping = 9999
        hosts_to_test = [
            {"name": "Worker", "header": self.entry_host},
            {"name": "SpeedTest", "header": "speed.cloudflare.com"}
        ]
        cache = {}

        for h in hosts_to_test:
            if self.stop_event.is_set():
                break
            ping = self.perform_ping_twice(ip, working_port)
            dl, ul = self.perform_speed_test(ip, working_port, h['header'])
            cache[h['name']] = {"ping": ping, "dl": dl, "ul": ul}

            if ping < 1500 and dl > 0 and (dl > max_dl or (dl == max_dl and ping < min_ping)):
                max_dl = dl
                min_ping = ping
                best_combo = {"ip": ip, "port": working_port, "dns_ip": "8.8.8.8", "ping": ping, "dl": dl, "ul": ul}

        for dns in self.dns_list:
            if self.stop_event.is_set():
                break
            for h in hosts_to_test:
                res = cache.get(h['name'])
                if not res:
                    continue
                if res['ping'] < 1500 and res['dl'] > 0 and (res['dl'] > max_dl or (res['dl'] == max_dl and res['ping'] < min_ping)):
                    max_dl = res['dl']
                    min_ping = res['ping']
                    best_combo = {"ip": ip, "port": working_port, "dns_ip": dns, "ping": res['ping'], "dl": res['dl'], "ul": res['ul']}

        if best_combo and not self.stop_event.is_set():
            with self.results_lock:
                self.best_pairs.append(best_combo)
            self.log(f"✅[HIT] {ip}:{working_port} | DL: {best_combo['dl']} KB/s | Ping: {best_combo['ping']}ms")

    def scan_engine(self, ip_source, samples_count, max_threads, scan_mode):
        scan_ips = []
        if ip_source == "Fetch API IPs":
            self.log("[*] Downloading fresh IPs from API...")
            try:
                resp = requests.get(CF_API_URL, timeout=10)
                if resp.status_code == 200:
                    fetched = [ip.strip() for ip in resp.text.split('\n') if ip.strip()]
                    scan_ips.extend(fetched)
                    self.log(f"[+] Loaded {len(scan_ips)} IPs from API.")
                else:
                    self.log("[-] API Failed. Using defaults.")
            except:
                self.log("[-] Network Error. Using defaults.")

        if not scan_ips:
            for cidr in self.custom_cidrs:
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                    if net.num_addresses <= samples_count:
                        scan_ips.extend([str(ip) for ip in net])
                    else:
                        limit = samples_count
                        selected = set()
                        while len(selected) < limit:
                            selected.add(str(net[random.randint(0, net.num_addresses - 1)]))
                        scan_ips.extend(list(selected))
                except:
                    pass

        from config import STANDARD_PORTS, ALL_PORTS
        base_ports = self.custom_ports if scan_mode == "Standard Ports" else ALL_PORTS
        none_cf_ports = [80, 8080, 8880, 2052, 2082, 2095]
        filtered_ports = []
        for p in base_ports:
            is_none = p in none_cf_ports
            if not is_none and self.var_tls.get() == 1:
                filtered_ports.append(p)
            elif is_none and self.var_none.get() == 1:
                filtered_ports.append(p)

        if not filtered_ports:
            self.log("[-] Error: No ports selected based on your config types.")
            return False

        self.total_tasks = len(scan_ips)
        self.log(f"\n🚀 Scanning {self.total_tasks} IPs with {max_threads} Threads...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(self.process_ip, ip, filtered_ports): ip for ip in scan_ips}
            for future in concurrent.futures.as_completed(futures):
                if self.stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                self.completed_tasks += 1
                pct = self.completed_tasks / self.total_tasks
                self.update_progress(self.completed_tasks, self.total_tasks, len(self.best_pairs))

        return True
