import socket
import random
import ipaddress
import time
import concurrent.futures
from datetime import datetime
from colorama import init, Fore, Style, Back
import os
import requests
import urllib3
import threading
import re
import json
import base64
import urllib.parse
import shutil

# تلاش برای ایمپورت msvcrt برای تشخیص دکمه در ویندوز
try:
    import msvcrt
except ImportError:
    msvcrt = None

# غیرفعال کردن اخطارهای امنیتی
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# فعال‌سازی رنگ‌ها در ترمینال
init(autoreset=True)
print_lock = threading.Lock()

DARK_GREY = Fore.LIGHTBLACK_EX  

# ==========================================
#               CONFIGURATION
# ==========================================

WORKER_HOST = "devtahair.alexnewyorkapolo.workers.dev"

WS_PATH = "/eyJqdW5rIjoicGFJTU1YRnIiLCJwcm90b2NvbCI6InZsIiwibW9kZSI6InByb3h5aXAiLCJwYW5lbElQcyI6WyJGVUNLLlRBV0FOQVBST1hZQS5PTkxJTkUiLCI4My4yMTkuMjQ5LjEwOCIsIkZVQ0sxLlRBV0FOQVBST1hZQS5PTkxJTkUiXX0="

USER_UUID = "c9420e4d-c835-4a31-ba06-6d42783c02b1"

HTTP_PORTS = [80, 443, 8080, 8880, 2052, 2082, 2095, 2053]

CLOUDFLARE_CIDRS = [
    # --- رنج‌های رسمی کلودفلر ---
    "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "104.16.0.0/13",
    "104.24.0.0/14", "108.162.192.0/18", "131.0.72.0/22", "141.101.64.0/18",
    "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
    "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17",
    # --- رنج‌های توسعه‌یافته و مخفی (BGP Routing) ---
    "8.238.64.0/18", "8.242.72.0/21", "8.243.216.0/21", "45.188.16.0/22",
    "45.239.36.0/22", "66.23.232.0/21", "80.94.96.0/20", "103.187.68.0/22",
    "103.187.72.0/22", "103.187.76.0/22", "103.187.80.0/22", "103.187.84.0/22",
    "103.187.88.0/22", "141.101.112.0/20", "141.101.120.0/21", "147.161.128.0/17",
    "162.159.0.0/16", "172.253.0.0/16", "192.64.0.0/24", "198.41.192.0/18",
    "205.251.192.0/19", "210.158.0.0/16"
]

SAMPLES_PER_CIDR = 200   
MAX_WORKERS = 50         
TIMEOUT = 3              
TEST_DL_LIMIT_KB = 50    
TEST_UL_SIZE_KB = 15     

DNS_SERVERS = [
    {"name": "Cloudflare", "ip": "1.1.1.1"},
    {"name": "Google",     "ip": "8.8.8.8"},
    {"name": "Quad9",      "ip": "9.9.9.9"},
    {"name": "NextDNS",    "ip": "45.90.28.0"},
    {"name": "Electro",    "ip": "78.157.42.100"},
    {"name": "Shecan",     "ip": "178.22.122.100"}
]

HOSTS_FOR_TEST = [
    {"name": "Worker", "header": WORKER_HOST},
    {"name": "SpeedTest", "header": "speed.cloudflare.com"}
]

TARGET_DIR = ""
CONFIGS_DIR = ""
OUTPUT_FILE = ""
CLEAN_IPS_FILE = ""
SUBSCRIPTION_FILE = ""
BEST_PAIRS_FOUND = []
RESULTS_LOCK = threading.Lock()
STOP_EVENT = threading.Event()

# ==========================================
#        DIRECTORY MANAGEMENT (CLEANUP)
# ==========================================

def setup_directories(folder_name):
    global TARGET_DIR, CONFIGS_DIR, OUTPUT_FILE, CLEAN_IPS_FILE, SUBSCRIPTION_FILE
    
    if not os.path.exists("D:\\"):
        print(f"{Fore.RED}❌ Error: Drive D: not found on this system! Switching to C:\\Temp")
        base_drive = "C:\\Temp"
        if not os.path.exists(base_drive):
            os.makedirs(base_drive)
    else:
        base_drive = "D:\\"

    TARGET_DIR = os.path.join(base_drive, folder_name)

    if os.path.exists(TARGET_DIR):
        print(f"{Fore.YELLOW}⚠️  Directory found: {TARGET_DIR}")
        print(f"{Fore.YELLOW}🧹 Wiping old files (Cleaning)...")
        try:
            for filename in os.listdir(TARGET_DIR):
                file_path = os.path.join(TARGET_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except:
                    pass
            print(f"{Fore.GREEN}✅ Directory cleaned.")
        except:
            pass
    else:
        print(f"{Fore.GREEN}📁 Creating new directory: {TARGET_DIR}")
        try:
            os.makedirs(TARGET_DIR)
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to create directory! Check permissions.")
            return False

    CONFIGS_DIR = os.path.join(TARGET_DIR, "Configs")
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR)
    
    OUTPUT_FILE = os.path.join(TARGET_DIR, "scan_log.txt")
    CLEAN_IPS_FILE = os.path.join(TARGET_DIR, "Verified_IPs.txt")
    SUBSCRIPTION_FILE = os.path.join(TARGET_DIR, "sub.txt")
    
    return True

# ==========================================
#               FUNCTIONS
# ==========================================

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def get_ping_color(val):
    if val == "Err" or val == "Timeout": return Fore.RED
    try:
        v = int(val)
        if v < 200: return Fore.GREEN
        if v < 400: return Fore.YELLOW
        return Fore.RED
    except: return Fore.RED

def get_speed_color(val):
    if "Error" in val or "0.0" in val: return Fore.RED
    return Fore.CYAN

def generate_random_ips(cidr, count):
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        if net.num_addresses <= count: return [str(ip) for ip in net]
        selected = set()
        attempts = 0
        while len(selected) < count and attempts < count * 3:
            rand_idx = random.randint(0, net.num_addresses - 1)
            selected.add(str(net[rand_idx]))
            attempts += 1
        return list(selected)
    except: return []

# 🌟 تابع جدید برای دریافت کشور به صورت گروهی (سریع)
def get_countries_batch(ip_list):
    country_map = {ip: "UNK" for ip in ip_list}
    unique_ips = list(set(ip_list))
    
    if not unique_ips: return country_map

    # دریافت اطلاعات کشور هر ۱۰۰ آی‌پی در یک درخواست (جلوگیری از بلاک شدن توسط API)
    for i in range(0, len(unique_ips), 100):
        chunk = unique_ips[i:i+100]
        try:
            res = requests.post("http://ip-api.com/batch?fields=query,countryCode", json=chunk, timeout=5)
            if res.status_code == 200:
                for item in res.json():
                    country_map[item['query']] = item.get('countryCode', 'UNK')
        except:
            pass
    return country_map

def test_worker_handshake(ip, port):
    try:
        url = f"http://{ip}:{port}{WS_PATH}"
        headers = {
            "Host": WORKER_HOST,
            "User-Agent": "Mozilla/5.0",
            "Connection": "Upgrade",
            "Upgrade": "websocket"
        }
        resp = requests.get(url, headers=headers, timeout=2, allow_redirects=False)
        server_header = resp.headers.get("Server", "").lower()
        
        if resp.status_code == 101:
            return True
        elif "cloudflare" in server_header and resp.status_code in [200, 400, 403, 404]:
            return True
        return False
    except:
        return False

def find_working_port(ip):
    ports_to_check = list(HTTP_PORTS)
    random.shuffle(ports_to_check)
    for port in ports_to_check:
        if test_worker_handshake(ip, port):
            return port
    return None

def perform_ping_twice(ip, port):
    results = []
    avg_ping = 9999
    valid_count = 0
    for _ in range(2):
        start = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(TIMEOUT)
            s.connect((ip, port))
            s.close()
            latency = int((time.time() - start) * 1000)
            results.append(str(latency))
            avg_ping = 0 if avg_ping == 9999 else avg_ping
            avg_ping += latency
            valid_count += 1
        except:
            results.append("Err")
        time.sleep(0.1)
    
    final_avg = int(avg_ping / valid_count) if valid_count > 0 else 9999
    return results, final_avg

def perform_speed_test(ip, port, host_header):
    try:
        headers = {'Host': host_header, 'User-Agent': 'Mozilla/5.0'}
        url = f"http://{ip}:{port}/"
        st = time.time()
        r = requests.get(url, headers=headers, timeout=4, stream=True)
        size = 0
        for chunk in r.iter_content(1024):
            size += len(chunk)
            if size > TEST_DL_LIMIT_KB * 1024: break
        dl_t = time.time() - st
        if dl_t <= 0: dl_t = 0.01
        dl_s = round((size/1024)/dl_t, 1)

        st = time.time()
        try:
            requests.post(url, headers=headers, data=b'0'*(TEST_UL_SIZE_KB*1024), timeout=4)
        except: pass
        ul_t = time.time() - st
        if ul_t <= 0: ul_t = 0.01
        ul_s = round(TEST_UL_SIZE_KB/ul_t, 1)
        
        return f"{dl_s} KB", f"{ul_s} KB", dl_s
    except:
        return "Error", "Error", 0

def format_row(label, p1, p2, dl, ul):
    return (
        f"{Fore.CYAN}│ {Fore.WHITE}{label:<25} "
        f"{Fore.CYAN}│ {get_ping_color(p1)}{p1:<6} "
        f"{Fore.CYAN}│ {get_ping_color(p2)}{p2:<6} "
        f"{Fore.CYAN}│ {get_speed_color(dl)}{dl:<10} "
        f"{Fore.CYAN}│ {get_speed_color(ul)}{ul:<10} {Fore.CYAN}│"
    )

def process_ip(ip):
    if STOP_EVENT.is_set(): return None

    working_port = find_working_port(ip)
    if not working_port:
        return None 

    pings, avg_ping = perform_ping_twice(ip, working_port)
    if pings[0] == "Err" and pings[1] == "Err":
        return None

    lines = []
    lines.append(f"{Fore.CYAN}┌{'─'*78}┐")
    lines.append(f"{Fore.CYAN}│ {Fore.YELLOW}{Style.BRIGHT}IP: {ip:<15} | PORT: {working_port:<5} | Scan Info{' '*28}{Fore.CYAN}│")
    lines.append(f"{Fore.CYAN}├{'─'*26}┬{'─'*8}┬{'─'*8}┬{'─'*12}┬{'─'*12}┤")
    lines.append(f"{Fore.CYAN}│ {Fore.WHITE}{'SCENARIO':<25} {Fore.CYAN}│ {Fore.WHITE}PING1  {Fore.CYAN}│ {Fore.WHITE}PING2  {Fore.CYAN}│ {Fore.WHITE}DOWNLOAD   {Fore.CYAN}│ {Fore.WHITE}UPLOAD     {Fore.CYAN}│")
    lines.append(f"{Fore.CYAN}├{'─'*78}┤")

    best_combo_for_this_ip = None
    min_ping_recorded = 9999

    for h in HOSTS_FOR_TEST:
        if STOP_EVENT.is_set(): break

        pings, avg = perform_ping_twice(ip, working_port)
        dl, ul, dl_val = perform_speed_test(ip, working_port, h['header'])
        lines.append(format_row(f"{h['name']} (Direct)", pings[0], pings[1], dl, ul))
        
        if avg < 600 and dl_val > 0 and avg < min_ping_recorded:
            min_ping_recorded = avg
            best_combo_for_this_ip = {
                "ip": ip, "port": working_port, "dns_ip": "8.8.8.8", "dns_name": "Direct", "ping": avg
            }

    lines.append(f"{Fore.CYAN}├{'─'*78}┤")

    for dns in DNS_SERVERS:
        if STOP_EVENT.is_set(): break 

        for h in HOSTS_FOR_TEST:
            if STOP_EVENT.is_set(): break
            
            pings, avg = perform_ping_twice(ip, working_port)
            dl, ul, dl_val = perform_speed_test(ip, working_port, h['header'])
            
            lines.append(format_row(f"{h['name']} ({dns['name']})", pings[0], pings[1], dl, ul))
            
            if avg < 600 and dl_val > 0:
                if avg < min_ping_recorded:
                    min_ping_recorded = avg
                    best_combo_for_this_ip = {
                        "ip": ip, "port": working_port, "dns_ip": dns['ip'], "dns_name": dns['name'], "ping": avg
                    }
    
    lines.append(f"{Fore.CYAN}└{'─'*78}┘")
    
    if best_combo_for_this_ip:
        with RESULTS_LOCK:
            BEST_PAIRS_FOUND.append(best_combo_for_this_ip)

    return "\n".join(lines)

def save_and_print(text):
    if not text: return
    clean_text = strip_ansi(text)
    with print_lock:
        print(text)
        try:
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(clean_text + "\n")
        except: pass

# 🌟 بروزرسانی تابع برای ثبت کشور در نام فایل و کانفیگ JSON
def create_config_file(data, index, alpn_str="", country_code="UNK"):
    ip = data['ip']
    port = int(data['port'])
    dns_ip = data['dns_ip']
    dns_name = data['dns_name']
    ping = data['ping']

    tls_ports = [443, 2053, 2083, 2087, 2096, 8443]
    if port in tls_ports:
        security_type = "tls"
    else:
        security_type = "none"

    fragment_settings = {
        "packets": "1-1",
        "length": "3-5",
        "interval": "1"
    }
    
    stream_settings = {
        "network": "ws",
        "wsSettings": {
            "host": WORKER_HOST,
            "path": WS_PATH
        },
        "security": security_type,
        "sockopt": {
            "domainStrategy": "UseIP",
            "tcpFastOpen": True,
            "fragment": fragment_settings,
            "happyEyeballs": {
                "tryDelayMs": 250,
                "prioritizeIPv6": False,
                "interleave": 2,
                "maxConcurrentTry": 4
            }
        }
    }

    alpn_label = "None"
    if security_type == "tls" and alpn_str:
        alpn_list = alpn_str.split(",")
        stream_settings["tlsSettings"] = {
            "serverName": WORKER_HOST,
            "alpn": alpn_list,
            "fingerprint": "chrome"
        }
        alpn_label = "H2" if "h2" in alpn_str else "HTTP1"

    config_structure = {
      "remarks": f"🌍{country_code} | {ip}:{port} | {alpn_label} | {ping}ms | {security_type.upper()}",
      "version": { "min": "25.10.15" },
      "log": { "loglevel": "warning" },
      "dns": {
        "servers": [
          { "address": f"https://{dns_ip}/dns-query", "tag": "remote-dns" }
        ],
        "queryStrategy": "UseIP",
        "tag": "dns"
      },
      "inbounds": [
        {
          "listen": "127.0.0.1",
          "port": 10808,
          "protocol": "socks",
          "settings": { "auth": "noauth", "udp": True },
          "sniffing": { "destOverride": ["http", "tls"], "enabled": True, "routeOnly": True },
          "tag": "mixed-in"
        }
      ],
      "outbounds": [
        {
          "protocol": "vless",
          "settings": {
            "vnext": [
              { "address": ip, "port": port, "users": [ { "id": USER_UUID, "encryption": "none" } ] }
            ]
          },
          "streamSettings": stream_settings,
          "tag": "proxy"
        },
        { "protocol": "dns", "settings": { "nonIPQuery": "reject" }, "tag": "dns-out" },
        { "protocol": "freedom", "settings": { "domainStrategy": "UseIP" }, "tag": "direct" },
        { "protocol": "blackhole", "settings": { "response": { "type": "http" } }, "tag": "block" }
      ],
      "routing": {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
          { "inboundTag": ["remote-dns"], "outboundTag": "proxy", "type": "field" },
          { "network": "udp", "outboundTag": "block", "type": "field" },
          { "network": "tcp", "outboundTag": "proxy", "type": "field" }
        ]
      }
    }
    
    safe_ip = ip.replace(':', '_')
    filename = f"Config_{index}_{country_code}_{security_type}_{alpn_label}_{port}_{safe_ip}.json"
    filepath = os.path.join(CONFIGS_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_structure, f, indent=2, ensure_ascii=False)
        return filename
    except Exception as e:
        print(f"{Fore.RED}Error saving config for IP {ip}: {e}")
        return None

def listen_for_stop():
    if not msvcrt: return 
    while not STOP_EVENT.is_set():
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\r':
                STOP_EVENT.set()
                print(f"\n{Back.RED}{Fore.WHITE} 🛑 STOP SIGNAL RECEIVED (Ctrl+M/Enter) {Style.RESET_ALL}")
                print(f"{Fore.YELLOW}» Finishing pending tasks and generating configs immediately...")
                break
        time.sleep(0.1)

# ==========================================
#               MAIN EXECUTION
# ==========================================

def main():
    print(f"\n{Back.BLUE}{Fore.WHITE}  MULTI-PORT CLOUDFLARE SCANNER (HTTP/2 ENABLED)  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}1.{Fore.WHITE} Default Scanner (Scan Mega BGP Cloudflare IPs)")
    print(f"{Fore.CYAN}2.{Fore.WHITE} Custom Scanner (Input your own IPs)")
    
    choice = input(f"\n{Fore.YELLOW}» Enter choice (1/2): {Fore.WHITE}").strip()
    
    scan_ips = []
    
    if choice == '1':
        if not setup_directories("allconfigs"): return
        print(f"\n{Fore.MAGENTA}» Mode: Mega Default Scanner")
        for cidr in CLOUDFLARE_CIDRS:
            scan_ips.extend(generate_random_ips(cidr, SAMPLES_PER_CIDR))
            
    elif choice == '2':
        if not setup_directories("CustomScanner"): return
        print(f"\n{Fore.MAGENTA}» Mode: Custom Scanner")
        user_input = input(f"{Fore.YELLOW}» Enter IPs: {Fore.WHITE}")
        raw_ips = re.split(r'[,\s]+', user_input)
        for ip in raw_ips:
            ip = ip.strip()
            try:
                ipaddress.ip_address(ip)
                scan_ips.append(ip)
            except:
                if ip: print(f"{Fore.RED}Invalid IP ignored: {ip}")
        
        if not scan_ips:
            print(f"{Fore.RED}❌ No valid IPs entered. Exiting.")
            return

    total_scanned_count = len(scan_ips)

    print(f"{Fore.YELLOW}Target Worker: {WORKER_HOST}")
    print(f"{DARK_GREY}Saving to: {TARGET_DIR}")
    print(f"{DARK_GREY}Testing Ports: {HTTP_PORTS}")
    print(f"{DARK_GREY}Total IPs to scan: {total_scanned_count}\n")
    print(f"{Back.MAGENTA}{Fore.WHITE} ℹ️  INFO: Press 'Enter' at any time to STOP scan and generate results! {Style.RESET_ALL}\n")

    try:
        with open(OUTPUT_FILE, 'w') as f:
            f.write(f"Scan Start: {datetime.now()} - Worker: {WORKER_HOST}\n\n")
    except: pass

    stop_monitor_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_monitor_thread.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_ip, ip): ip for ip in scan_ips}

        for future in concurrent.futures.as_completed(futures):
            if STOP_EVENT.is_set():
                try: executor.shutdown(wait=False, cancel_futures=True)
                except: pass
                break

            try:
                res = future.result()
                if res: save_and_print(res)
                else:
                    with print_lock: print(f"{Fore.RED}.", end="", flush=True)
            except: pass

    print(f"\n\n{Back.GREEN}{Fore.BLACK}  GENERATING CONFIGS & SUB LINK (Processed {len(BEST_PAIRS_FOUND)} good IPs)  {Style.RESET_ALL}\n")
    
    if not BEST_PAIRS_FOUND:
        print(f"{Fore.RED}❌ No Clean IPs found so far.")
        input("Press Enter to exit...")
        return

    sorted_best = sorted(BEST_PAIRS_FOUND, key=lambda x: x['ping'])
    
    clean_ips_list = []
    vless_links_list = []
    global_index = 1

    # 🌟 پیدا کردن کشور همه آی‌پی‌های تمیز به صورت یکجا
    unique_clean_ips = list(set([data['ip'] for data in sorted_best]))
    print(f"{Fore.YELLOW}🌍 Looking up Countries for {len(unique_clean_ips)} IP(s)...")
    ip_countries_map = get_countries_batch(unique_clean_ips)
    print(f"{Fore.GREEN}✅ Lookup Complete.\n")

    for data in sorted_best:
        p_val = int(data['port'])
        sec_display = "TLS" if p_val in [443, 2053, 2083, 2087, 2096, 8443] else "NONE"
        country_code = ip_countries_map.get(data['ip'], "UNK")
        
        alpn_variants = ["http/1.1", "h2,http/1.1"] if sec_display == "TLS" else [""]
        
        for alpn in alpn_variants:
            fname = create_config_file(data, global_index, alpn, country_code)
            
            if fname:
                alpn_print = alpn if alpn else "N/A"
                print(f"{Fore.WHITE}[{global_index}] Cntry: {Fore.YELLOW}{country_code:<3} {Fore.WHITE}| IP: {Fore.GREEN}{data['ip']:<15} {Fore.WHITE}| Port: {Fore.MAGENTA}{data['port']:<5} {Fore.WHITE}| Sec: {Fore.CYAN}{sec_display} {Fore.WHITE}| ALPN: {Fore.YELLOW}{alpn_print:<12} {Fore.WHITE}| Ping: {Fore.YELLOW}{data['ping']}ms")
                
                if data['ip'] not in clean_ips_list:
                    clean_ips_list.append(data['ip'])

                # 🌟 اضافه کردن پرچم/کد کشور به نام کانفیگ
                alias_alpn = "H2" if "h2" in alpn else "HTTP1.1" if alpn else "NONE"
                alias = f"🌍{country_code} | {data['ip']}:{data['port']} | {sec_display} | {alias_alpn} | {data['ping']}ms"
                safe_alias = urllib.parse.quote(alias)
                safe_path = urllib.parse.quote(WS_PATH)
                
                sec_param = "tls" if sec_display == "TLS" else "none"
                alpn_param = f"&alpn={alpn}&sni={WORKER_HOST}" if sec_display == "TLS" else ""
                
                vless_link = (
                    f"vless://{USER_UUID}@{data['ip']}:{data['port']}"
                    f"?encryption=none&security={sec_param}&type=ws&host={WORKER_HOST}&path={safe_path}"
                    f"&fp=chrome{alpn_param}"
                    f"#{safe_alias}"
                )
                vless_links_list.append(vless_link)
                
            global_index += 1

    if clean_ips_list:
        try:
            with open(CLEAN_IPS_FILE, 'w', encoding='utf-8') as f:
                f.write(",".join(clean_ips_list))
        except: pass

    if vless_links_list:
        all_links_text = "\n".join(vless_links_list)
        encoded_bytes = base64.b64encode(all_links_text.encode("utf-8"))
        encoded_string = encoded_bytes.decode("utf-8")
        
        try:
            with open(SUBSCRIPTION_FILE, "w", encoding='utf-8') as f:
                f.write(encoded_string)
        except: pass

    # 🌟 گزارش آماری نهایی 
    total_clean = len(clean_ips_list)
    total_dead = total_scanned_count - total_clean

    print(f"\n{Fore.CYAN}┌{'─'*60}┐")
    print(f"{Fore.CYAN}│ {Fore.WHITE}{Style.BRIGHT}{'📊 SCAN SUMMARY REPORT':^58} {Fore.CYAN}│")
    print(f"{Fore.CYAN}├{'─'*60}┤")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Total IPs Scanned:   {Fore.YELLOW}{str(total_scanned_count):<37} {Fore.CYAN}│")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Clean/Working IPs:   {Fore.GREEN}{str(total_clean):<37} {Fore.CYAN}│")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Dead/Failed IPs:     {Fore.RED}{str(total_dead):<37} {Fore.CYAN}│")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Total Configs Gen:   {Fore.MAGENTA}{str(len(vless_links_list)):<37} {Fore.CYAN}│")
    print(f"{Fore.CYAN}├{'─'*60}┤")
    print(f"{Fore.CYAN}│ {Fore.GREEN}✅ Subscription file created: {Fore.WHITE}{'sub.txt':<29} {Fore.CYAN}│")
    print(f"{Fore.CYAN}│ {Fore.GREEN}📂 Saved Folder: {Fore.WHITE}{TARGET_DIR:<43} {Fore.CYAN}│")
    print(f"{Fore.CYAN}└{'─'*60}┘\n")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()