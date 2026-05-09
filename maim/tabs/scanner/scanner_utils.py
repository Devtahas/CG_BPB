# tabs/scanner/scanner_utils.py
import socket
import time
import requests
import random
import threading
from config import TIMEOUT, TEST_DL_LIMIT_KB, TEST_UL_SIZE_KB


class ScannerUtils:
    """توابع کمکی اسکنر - پینگ، اسپیدتست، هندشیک و..."""
    
    @staticmethod
    def test_worker_handshake(ip, port, worker_host, worker_path):
        """تست هندشیک با ورکر کلادفلر"""
        try:
            path = worker_path
            if not path.startswith("/"): 
                path = "/" + path
            url = f"http://{ip}:{port}{path}"
            headers = {
                "Host": worker_host,
                "User-Agent": "Mozilla/5.0",
                "Connection": "Upgrade",
                "Upgrade": "websocket"
            }
            resp = requests.get(url, headers=headers, timeout=2, allow_redirects=False)
            if resp.status_code == 101 or ("cloudflare" in resp.headers.get("Server", "").lower() and resp.status_code in [200, 400, 403, 404]):
                return True
        except: 
            pass
        return False
    
    @staticmethod
    def find_working_port(ip, port_list, worker_host, worker_path, stop_event):
        """پیدا کردن پورت کاری روی IP"""
        ports_to_check = list(port_list)
        random.shuffle(ports_to_check)
        found_port = None
        lock = threading.Lock()   # ← قفل برای محافظت از منابع اشتراکی

        def worker():
            nonlocal found_port
            while True:
                # بررسی توقف قبل از گرفتن کار جدید
                if stop_event.is_set():
                    break

                # قفل‌گذاری برای برداشتن امن یک پورت از لیست
                with lock:
                    if found_port is not None:
                        break
                    if not ports_to_check:
                        break
                    try:
                        port = ports_to_check.pop()
                    except IndexError:
                        break

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        if s.connect_ex((ip, port)) == 0:
                            if ScannerUtils.test_worker_handshake(ip, port, worker_host, worker_path):
                                # فقط یک ترد مقدار found_port را تنظیم می‌کند
                                with lock:
                                    if found_port is None:
                                        found_port = port
                                break   # کار این ترد تمام شد
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
    
    @staticmethod
    def perform_ping_twice(ip, port, stop_event):
        """انجام پینگ دو مرحله‌ای"""
        avg_ping, valid = 0, 0
        for _ in range(2):
            if stop_event.is_set(): 
                return 9999
            start = time.time()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(TIMEOUT)
                    s.connect((ip, port))
                avg_ping += int((time.time() - start) * 1000)
                valid += 1
            except: 
                pass
        return int(avg_ping / valid) if valid > 0 else 9999
    
    @staticmethod
    def perform_speed_test(ip, port, host_header, worker_path, stop_event):
        """تست سرعت دانلود و آپلود"""
        try:
            headers = {'Host': host_header, 'User-Agent': 'Mozilla/5.0'}
            path = worker_path
            if not path.startswith("/"): 
                path = "/" + path
            
            req_path = f"/__down?bytes={TEST_DL_LIMIT_KB * 1024}" if "speed.cloudflare.com" in host_header else path
            url = f"http://{ip}:{port}{req_path}"
            
            st = time.time()
            r = requests.get(url, headers=headers, timeout=4, stream=True)
            size = 0
            for chunk in r.iter_content(1024):
                if stop_event.is_set(): 
                    return 0, 0
                size += len(chunk)
                if size > TEST_DL_LIMIT_KB * 1024: 
                    break
            
            dl_t = max(time.time() - st, 0.01)
            dl_s = round((size/1024)/dl_t, 1)

            st_ul = time.time()
            try:
                if not stop_event.is_set():
                    up_path = "/__up" if "speed.cloudflare.com" in host_header else path
                    up_url = f"http://{ip}:{port}{up_path}"
                    requests.post(up_url, headers=headers, data=b'0'*(TEST_UL_SIZE_KB*1024), timeout=4)
            except: 
                pass
            
            ul_t = max(time.time() - st_ul, 0.01)
            ul_s = round(TEST_UL_SIZE_KB/ul_t, 1)
            
            return dl_s, ul_s
        except: 
            return 0, 0
    
    @staticmethod
    def get_countries_batch(ip_list):
        """دریافت کشور IPها به صورت دسته‌ای"""
        country_map = {ip: "UNK" for ip in ip_list}
        unique_ips = list(set(ip_list))
        for i in range(0, len(unique_ips), 100):
            try:
                res = requests.post("http://ip-api.com/batch?fields=query,countryCode", json=unique_ips[i:i+100], timeout=5)
                if res.status_code == 200:
                    for item in res.json(): 
                        country_map[item['query']] = item.get('countryCode', 'UNK')
            except: 
                pass
        return country_map
    
    @staticmethod
    def detect_isp_and_adjust_fragment(frag_enable, frag_mode, manual_packets, manual_length, manual_interval, log_callback):
        """تشخیص ISP و تنظیم خودکار Fragment"""
        if frag_enable == 0:
            log_callback("🧩 Fragment Option is Disabled.")
            return {"packets": "1-1", "length": "100-200", "interval": "1"}

        if frag_mode == "Manual":
            settings = {
                "packets": manual_packets.strip() or "1-1",
                "length": manual_length.strip() or "100-200",
                "interval": manual_interval.strip() or "1"
            }
            log_callback(f"🧩 Manual Fragment Applied: {settings}")
            return settings

        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5).json()
            isp, org = resp.get("isp", "").lower(), resp.get("org", "").lower()
            if any(kw in isp or kw in org for kw in ['mci', 'hamrah']): 
                settings = {"packets": "1-1", "length": "10-20", "interval": "5"}
                log_callback(f"📶 Auto Fragment (MCI): {settings}")
            elif any(kw in isp or kw in org for kw in ['mtn', 'irancell']): 
                settings = {"packets": "1-1", "length": "1-3", "interval": "10"}
                log_callback(f"📶 Auto Fragment (Irancell): {settings}")
            elif 'rightel' in isp: 
                settings = {"packets": "1-1", "length": "20-40", "interval": "5"}
                log_callback(f"📶 Auto Fragment (Rightel): {settings}")
            else: 
                settings = {"packets": "1-1", "length": "100-200", "interval": "1"}
                log_callback(f"🌐 Auto Fragment (Broadband): {settings}")
        except: 
            settings = {"packets": "1-1", "length": "100-200", "interval": "1"}
            log_callback(f"⚠️ ISP Detection Failed (Using Default Fragment): {settings}")
        
        return settings
