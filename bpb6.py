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
import platform
import sys
# === کتابخانه های جدید برای ساخت لوکال هاست ===
import webbrowser
import http.server

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

WORKER_HOST = ""

WS_PATH = ""
USER_UUID = ""

# پورت‌های استاندارد کلودفلر
STANDARD_PORTS = [80, 443, 8080, 8880, 2052, 2082, 2095, 2053]

# تمام پورت‌های مجاز شبکه برای حالت Deep و Hope
ALL_PORTS = list(range(1, 65536))

CLOUDFLARE_CIDRS = [
    # --- رنج‌های رسمی کلودفلر ---
    "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "104.16.0.0/13",
    "104.24.0.0/14", "108.162.192.0/18", "131.0.72.0/22", "141.101.64.0/18",
    "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
    "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17",
    # --- رنج‌های توسعه‌یافته و مخفی ---
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

STANDARD_DNS = [
    {"name": "Cloudflare", "ip": "1.1.1.1"},
    {"name": "Google",     "ip": "8.8.8.8"},
    {"name": "Quad9",      "ip": "9.9.9.9"},
    {"name": "Electro",    "ip": "78.157.42.100"},
    {"name": "Shecan",     "ip": "178.22.122.100"}
]

# دی‌ان‌اس‌های عظیم برای حالت Hope Mode
HOPE_DNS = STANDARD_DNS + [
    {"name": "NextDNS",    "ip": "45.90.28.0"},
    {"name": "OpenDNS",    "ip": "208.67.222.222"},
    {"name": "AdGuard",    "ip": "94.140.14.14"},
    {"name": "Yandex",     "ip": "77.88.8.8"},
    {"name": "RadarGame",  "ip": "10.202.10.10"},
    {"name": "403.online", "ip": "10.202.10.202"},
    {"name": "Begzar",     "ip": "185.55.226.26"},
    {"name": "HostIran",   "ip": "172.29.0.100"},
    {"name": "CleanBrows", "ip": "185.228.168.9"},
    {"name": "Level3",     "ip": "4.2.2.4"},
    {"name": "Verisign",   "ip": "64.6.64.6"}
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

GLOBAL_FRAGMENT_SETTINGS = {
    "packets": "1-1",
    "length": "100-200",
    "interval": "1"
}

COMPLETED_TASKS_COUNT = 0


# ==========================================
#        LOCAL WEB SERVER & SAVING CONFIG
# ==========================================

def get_saved_config_path():
    system = platform.system().lower()
    # پیدا کردن مسیر دسکتاپ (یا دانلودها در اندروید)
    if 'android' in system or os.path.exists('/storage/emulated/0/'):
        base_dir = "/storage/emulated/0/Download"
    elif system == 'windows':
        base_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    else:
        # مک و لینوکس
        base_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    
    # در صورتی که پوشه دسکتاپ به هر دلیلی پیدا نشد، در پوشه اصلی کاربر بسازد
    if not os.path.exists(base_dir):
        base_dir = os.path.expanduser("~")
        
    config_folder = os.path.join(base_dir, "Scanner_Settings")
    if not os.path.exists(config_folder):
        try:
            os.makedirs(config_folder)
        except Exception:
            pass
            
    return os.path.join(config_folder, "user_config.json")

def load_saved_config():
    global WORKER_HOST, WS_PATH, USER_UUID
    config_path = get_saved_config_path()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('USER_UUID') and data.get('WS_PATH') and data.get('WORKER_HOST'):
                    USER_UUID = data['USER_UUID']
                    WS_PATH = data['WS_PATH']
                    WORKER_HOST = data['WORKER_HOST']
                    print(f"{Fore.GREEN}✅ Loaded saved configuration from: {config_path}")
                    # آپدیت کردن هاست برای تست اسپید
                    HOSTS_FOR_TEST[0]['header'] = WORKER_HOST
                    return True
        except Exception as e:
            print(f"{Fore.RED}⚠️ Failed to read saved config file: {e}")
            
    return False

def save_config_to_disk():
    config_path = get_saved_config_path()
    data = {
        'USER_UUID': USER_UUID,
        'WS_PATH': WS_PATH,
        'WORKER_HOST': WORKER_HOST
    }
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"\n{Fore.GREEN}✅ Configuration saved successfully to: {config_path}")
        print(f"{Fore.YELLOW}💡 Note: To change settings in the future, simply delete the 'user_config.json' file.\n")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Failed to save configuration to disk: {e}")

class WebConfigHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html lang="fa" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>تنظیمات اولیه اسکنر</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #121212; color: #e0e0e0;
                    display: flex; justify-content: center; align-items: center;
                    height: 100vh; margin: 0; direction: ltr;
                }}
                .container {{
                    background-color: #1e1e1e; padding: 30px;
                    border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                    width: 100%; max-width: 450px;
                    border: 1px solid #333;
                }}
                h2 {{ text-align: center; color: #00bcd4; margin-top: 0; }}
                label {{ display: block; margin-top: 15px; font-weight: bold; color: #aaa; font-size: 14px; }}
                input {{
                    width: 100%; padding: 10px; margin-top: 8px;
                    background-color: #2b2b2b; border: 1px solid #444;
                    color: #fff; border-radius: 5px; box-sizing: border-box;
                    font-family: monospace; font-size: 13px;
                }}
                input:focus {{ outline: none; border-color: #00bcd4; }}
                button {{
                    width: 100%; padding: 12px; margin-top: 25px;
                    background-color: #00bcd4; border: none;
                    color: #000; font-weight: bold; font-size: 16px;
                    border-radius: 5px; cursor: pointer; transition: 0.3s;
                }}
                button:hover {{ background-color: #008ba3; }}
                .info {{ text-align: center; font-size: 12px; color: #777; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>⚙️ Scanner Setup</h2>
                <form method="POST">
                    <label>UUID:</label>
                    <input type="text" name="uuid" value="{USER_UUID}" required>
                    
                    <label>WS Path:</label>
                    <input type="text" name="path" value="{WS_PATH}" required>
                    
                    <label>Worker Host:</label>
                    <input type="text" name="host" value="{WORKER_HOST}" required>
                    
                    <button type="submit">Save & Start Scanning</button>
                </form>
                <div class="info">After saving, return to your terminal.</div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        global USER_UUID, WS_PATH, WORKER_HOST
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed_data = urllib.parse.parse_qs(post_data)

        if 'uuid' in parsed_data: USER_UUID = parsed_data['uuid'][0].strip()
        if 'path' in parsed_data: WS_PATH = parsed_data['path'][0].strip()
        if 'host' in parsed_data: WORKER_HOST = parsed_data['host'][0].strip()

        # ذخیره در فایل برای دفعات بعد
        save_config_to_disk()
        
        # آپدیت کردن هاست برای تست اسپید
        HOSTS_FOR_TEST[0]['header'] = WORKER_HOST

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        success_html = """
        <!DOCTYPE html>
        <html><head>
        <style>body{background:#121212;color:#00ff00;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;text-align:center;}</style>
        </head><body>
        <div><h2>✅ Saved Successfully!</h2><p>You can close this tab and return to the terminal.</p></div>
        <script>setTimeout(() => window.close(), 3000);</script>
        </body></html>
        """
        self.wfile.write(success_html.encode('utf-8'))

        threading.Thread(target=self.server.shutdown, daemon=True).start()

def get_user_configs_via_browser():
    print(f"{Fore.CYAN}🌐 Starting local web server for configuration...")
    
    server = http.server.HTTPServer(('127.0.0.1', 0), WebConfigHandler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    
    print(f"{Fore.YELLOW}🚀 Opening browser at: {url}")
    print(f"{Fore.WHITE}Please fill in your configuration in the browser to continue...\n")
    
    webbrowser.open(url)
    server.serve_forever()
    
    print(f"{Fore.GREEN}✅ Configuration Received successfully!\n")


# ==========================================
#        PRECISE ISP DETECTION (IMPROVED)
# ==========================================

def detect_isp_and_adjust_fragment():
    global GLOBAL_FRAGMENT_SETTINGS
    print(f"\n{Fore.YELLOW}🔍 Detecting precise ISP and applying smart fragments...")
    try:
        resp = requests.get("http://ip-api.com/json/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            isp = data.get("isp", "").lower()
            org = data.get("org", "").lower()
            print(f"{Fore.CYAN}🏢 Network Info: {Fore.WHITE}{data.get('isp')} / {data.get('org')}")

            # همراه اول
            if any(kw in isp or kw in org for kw in ['mci', 'hamrah', 'mobile telecommunication', 'mobile communication']):
                print(f"{Fore.GREEN}📶 MCI (Hamrah Aval) Detected -> Strict Fragment [Length: 10-20, Interval: 5]")
                GLOBAL_FRAGMENT_SETTINGS = {"packets": "1-1", "length": "10-20", "interval": "5"}
            # ایرانسل
            elif any(kw in isp or kw in org for kw in ['mtn', 'irancell']):
                print(f"{Fore.GREEN}📶 Irancell Detected -> Aggressive DPI Fragment [Length: 1-3, Interval: 10]")
                GLOBAL_FRAGMENT_SETTINGS = {"packets": "1-1", "length": "1-3", "interval": "10"}
            # رایتل
            elif 'rightel' in isp or 'rightel' in org:
                print(f"{Fore.GREEN}📶 Rightel Detected -> Custom Fragment [Length: 20-40, Interval: 5]")
                GLOBAL_FRAGMENT_SETTINGS = {"packets": "1-1", "length": "20-40", "interval": "5"}
            # مخابرات
            elif any(kw in isp or kw in org for kw in ['tci', 'telecommunication company of iran', 'mokhaberat']):
                print(f"{Fore.BLUE}🌐 TCI (Mokhaberat) Detected -> Stable Fragment [Length: 50-100, Interval: 2]")
                GLOBAL_FRAGMENT_SETTINGS = {"packets": "1-1", "length": "50-100", "interval": "2"}
            # سایر اینترنت‌های ثابت
            else:
                print(f"{Fore.BLUE}🌐 Other Broadband Detected -> Default Stable Fragment [Length: 100-200, Interval: 1]")
                GLOBAL_FRAGMENT_SETTINGS = {"packets": "1-1", "length": "100-200", "interval": "1"}
        else:
            print(f"{Fore.RED}⚠️ Could not fetch ISP. Using generic default fragment.")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Network error during ISP detection. Using generic default fragment.")

# ==========================================
#        DIRECTORY MANAGEMENT 
# ==========================================

def setup_directories(folder_name):
    global TARGET_DIR, CONFIGS_DIR, OUTPUT_FILE, CLEAN_IPS_FILE, SUBSCRIPTION_FILE
    
    system = platform.system().lower()
    base_dir = ""

    if 'android' in system or os.path.exists('/storage/emulated/0/'):
        base_dir = "/storage/emulated/0/Download"
        if not os.path.exists(base_dir):
            base_dir = "/storage/emulated/0" 
        print(f"{Fore.GREEN}📱 Android OS detected.")
    elif system == 'windows':
        if os.path.exists("D:\\"):
            base_dir = "D:\\"
        else:
            base_dir = "C:\\Temp"
        print(f"{Fore.GREEN}🪟 Windows OS detected.")
    else:
        base_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(base_dir):
            base_dir = os.path.expanduser("~")
        print(f"{Fore.GREEN}🐧 Linux/macOS detected.")

    TARGET_DIR = os.path.join(base_dir, folder_name)

    if os.path.exists(TARGET_DIR):
        print(f"{Fore.YELLOW}⚠️  Directory found: {TARGET_DIR}")
        print(f"{Fore.YELLOW}🧹 Cleaning up old files...")
        try:
            for filename in os.listdir(TARGET_DIR):
                file_path = os.path.join(TARGET_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass
            print(f"{Fore.GREEN}✅ Directory cleaned.")
        except Exception:
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
#               CORE FUNCTIONS
# ==========================================

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def get_ping_color(val):
    if val == "Err" or val == "Timeout":
        return Fore.RED
    try:
        v = int(val)
        if v < 200:
            return Fore.GREEN
        elif v < 400:
            return Fore.YELLOW
        return Fore.RED
    except Exception:
        return Fore.RED

def get_speed_color(val):
    if "Error" in val or "0.0" in val:
        return Fore.RED
    return Fore.CYAN

def generate_random_ips(cidr, count):
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        if net.num_addresses <= count:
            return [str(ip) for ip in net]
        selected = set()
        attempts = 0
        while len(selected) < count and attempts < count * 3:
            rand_idx = random.randint(0, net.num_addresses - 1)
            selected.add(str(net[rand_idx]))
            attempts += 1
        return list(selected)
    except Exception:
        return []

def get_countries_batch(ip_list):
    country_map = {ip: "UNK" for ip in ip_list}
    unique_ips = list(set(ip_list))
    
    if not unique_ips:
        return country_map
        
    for i in range(0, len(unique_ips), 100):
        chunk = unique_ips[i:i+100]
        try:
            res = requests.post("http://ip-api.com/batch?fields=query,countryCode", json=chunk, timeout=5)
            if res.status_code == 200:
                for item in res.json():
                    country_map[item['query']] = item.get('countryCode', 'UNK')
        except Exception:
            pass
            
    return country_map

def is_port_open_fast(ip, port, timeout=0.3):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            return result == 0
    except Exception:
        return False

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
    except Exception:
        return False

def check_single_port_full(ip, port):
    if STOP_EVENT.is_set():
        return None
        
    if is_port_open_fast(ip, port):
        if test_worker_handshake(ip, port):
            return port
            
    return None

def find_working_port(ip, port_list):
    ports_to_check = list(port_list)
    random.shuffle(ports_to_check)
    
    if len(ports_to_check) <= 20:
        for port in ports_to_check:
            if STOP_EVENT.is_set():
                return None
                
            res = check_single_port_full(ip, port)
            if res:
                return res
        return None
    
    found_port = None
    
    def worker():
        nonlocal found_port
        while ports_to_check and not STOP_EVENT.is_set() and not found_port:
            try:
                port = ports_to_check.pop()
            except IndexError:
                break
                
            if STOP_EVENT.is_set():
                break
                
            res = check_single_port_full(ip, port)
            if res:
                found_port = res
                break

    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()
        
    return found_port

def perform_ping_twice(ip, port):
    results = []
    avg_ping = 9999
    valid_count = 0
    
    for _ in range(2):
        if STOP_EVENT.is_set():
            return ["Err", "Err"], 9999
            
        start = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(TIMEOUT)
            s.connect((ip, port))
            s.close()
            latency = int((time.time() - start) * 1000)
            results.append(str(latency))
            
            if avg_ping == 9999:
                avg_ping = 0
            avg_ping += latency
            valid_count += 1
        except Exception:
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
            if STOP_EVENT.is_set():
                return "Error", "Error", 0
                
            size += len(chunk)
            if size > TEST_DL_LIMIT_KB * 1024:
                break
                
        dl_t = time.time() - st
        if dl_t <= 0:
            dl_t = 0.01
        dl_s = round((size/1024)/dl_t, 1)

        st = time.time()
        try:
            if not STOP_EVENT.is_set():
                requests.post(url, headers=headers, data=b'0'*(TEST_UL_SIZE_KB*1024), timeout=4)
        except Exception:
            pass
            
        ul_t = time.time() - st
        if ul_t <= 0:
            ul_t = 0.01
        ul_s = round(TEST_UL_SIZE_KB/ul_t, 1)
        
        return f"{dl_s} KB", f"{ul_s} KB", dl_s
        
    except Exception:
        return "Error", "Error", 0

def format_row(label, p1, p2, dl, ul):
    return (
        f"{Fore.CYAN}│ {Fore.WHITE}{label:<25} "
        f"{Fore.CYAN}│ {get_ping_color(p1)}{p1:<6} "
        f"{Fore.CYAN}│ {get_ping_color(p2)}{p2:<6} "
        f"{Fore.CYAN}│ {get_speed_color(dl)}{dl:<10} "
        f"{Fore.CYAN}│ {get_speed_color(ul)}{ul:<10} {Fore.CYAN}│"
    )

def process_ip(ip, port_list, dns_list):
    if STOP_EVENT.is_set():
        return None

    working_port = find_working_port(ip, port_list)
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
        if STOP_EVENT.is_set():
            break
            
        pings, avg = perform_ping_twice(ip, working_port)
        dl, ul, dl_val = perform_speed_test(ip, working_port, h['header'])
        lines.append(format_row(f"{h['name']} (Direct)", pings[0], pings[1], dl, ul))
        
        if avg < 600 and dl_val > 0 and avg < min_ping_recorded:
            min_ping_recorded = avg
            best_combo_for_this_ip = {
                "ip": ip, 
                "port": working_port, 
                "dns_ip": "8.8.8.8", 
                "dns_name": "Direct", 
                "ping": avg
            }

    lines.append(f"{Fore.CYAN}├{'─'*78}┤")

    for dns in dns_list:
        if STOP_EVENT.is_set():
            break 
            
        for h in HOSTS_FOR_TEST:
            if STOP_EVENT.is_set():
                break
                
            pings, avg = perform_ping_twice(ip, working_port)
            dl, ul, dl_val = perform_speed_test(ip, working_port, h['header'])
            
            lines.append(format_row(f"{h['name']} ({dns['name'][:10]})", pings[0], pings[1], dl, ul))
            
            if avg < 600 and dl_val > 0:
                if avg < min_ping_recorded:
                    min_ping_recorded = avg
                    best_combo_for_this_ip = {
                        "ip": ip, 
                        "port": working_port, 
                        "dns_ip": dns['ip'], 
                        "dns_name": dns['name'], 
                        "ping": avg
                    }
    
    lines.append(f"{Fore.CYAN}└{'─'*78}┘")
    
    if best_combo_for_this_ip and not STOP_EVENT.is_set():
        with RESULTS_LOCK:
            BEST_PAIRS_FOUND.append(best_combo_for_this_ip)

    return "\n".join(lines)

def save_and_print(text):
    if not text:
        return
        
    clean_text = strip_ansi(text)
    with print_lock:
        sys.stdout.write(f"\r{' '*100}\r")
        sys.stdout.flush()
        
        print(text)
        
        try:
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(clean_text + "\n")
        except Exception:
            pass

def create_config_file(data, index, alpn_str="", country_code="UNK"):
    ip = data['ip']
    port = int(data['port'])
    dns_ip = data['dns_ip']
    ping = data['ping']
    
    tls_ports = [443, 2053, 2083, 2087, 2096, 8443]
    
    if port in tls_ports:
        security_type = "tls"
    else:
        security_type = "none"

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
            "fragment": GLOBAL_FRAGMENT_SETTINGS,
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
      "version": {
          "min": "25.10.15"
      },
      "log": {
          "loglevel": "warning"
      },
      "dns": {
        "servers": [
          {
              "address": f"https://{dns_ip}/dns-query",
              "tag": "remote-dns"
          }
        ],
        "queryStrategy": "UseIP",
        "tag": "dns"
      },
      "inbounds": [
        {
          "listen": "127.0.0.1",
          "port": 10808,
          "protocol": "socks",
          "settings": {
              "auth": "noauth",
              "udp": True
          },
          "sniffing": {
              "destOverride": ["http", "tls"],
              "enabled": True,
              "routeOnly": True
          },
          "tag": "mixed-in"
        }
      ],
      "outbounds": [
        {
          "protocol": "vless",
          "settings": {
            "vnext": [
              {
                  "address": ip,
                  "port": port,
                  "users": [
                      {
                          "id": USER_UUID,
                          "encryption": "none"
                      }
                  ]
              }
            ]
          },
          "streamSettings": stream_settings,
          "tag": "proxy"
        },
        {
            "protocol": "dns",
            "settings": {
                "nonIPQuery": "reject"
            },
            "tag": "dns-out"
        },
        {
            "protocol": "freedom",
            "settings": {
                "domainStrategy": "UseIP"
            },
            "tag": "direct"
        },
        {
            "protocol": "blackhole",
            "settings": {
                "response": {
                    "type": "http"
                }
            },
            "tag": "block"
        }
      ],
      "routing": {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
          {
              "inboundTag": ["remote-dns"],
              "outboundTag": "proxy",
              "type": "field"
          },
          {
              "network": "udp",
              "outboundTag": "block",
              "type": "field"
          },
          {
              "network": "tcp",
              "outboundTag": "proxy",
              "type": "field"
          }
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

# ==========================================
#        LIVE PROGRESS MONITORING
# ==========================================

def display_live_progress(total_ips):
    global COMPLETED_TASKS_COUNT
    spinners = ['|', '/', '-', '\\']
    idx = 0
    
    while not STOP_EVENT.is_set() and COMPLETED_TASKS_COUNT < total_ips:
        percentage = (COMPLETED_TASKS_COUNT / total_ips) * 100
        with print_lock:
            progress_text = (
                f"\r{Fore.CYAN}⚙️ Live Scan {spinners[idx]} "
                f"{Fore.YELLOW}{percentage:.3f}% {DARK_GREY}| "
                f"{Fore.WHITE}{COMPLETED_TASKS_COUNT}/{total_ips} {DARK_GREY}| "
                f"{Fore.GREEN}Found: {len(BEST_PAIRS_FOUND)}{Style.RESET_ALL}   "
            )
            sys.stdout.write(progress_text)
            sys.stdout.flush()
            
        idx = (idx + 1) % 4
        time.sleep(0.1)
    
    with print_lock:
        sys.stdout.write(f"\r{' '*100}\r")
        sys.stdout.flush()

def listen_for_stop():
    if not msvcrt:
        return 
        
    while not STOP_EVENT.is_set():
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\r':
                STOP_EVENT.set()
                with print_lock:
                    sys.stdout.write(f"\r{' '*100}\r")
                    print(f"\n{Back.RED}{Fore.WHITE} 🛑 STOP SIGNAL RECEIVED (Ctrl+M/Enter) {Style.RESET_ALL}")
                break
        time.sleep(0.1)

def execute_scan(scan_ips, ports_list, dns_list, scan_label):
    global COMPLETED_TASKS_COUNT
    COMPLETED_TASKS_COUNT = 0
    total_ips = len(scan_ips)

    print(f"\n{Back.MAGENTA}{Fore.WHITE}🚀 STARTING SCAN: {scan_label} {Style.RESET_ALL}")
    print(f"{DARK_GREY}Testing Ports Count: {len(ports_list)} | DNS Count: {len(dns_list)}")
    print(f"{DARK_GREY}Total IPs to scan: {total_ips}\n")
    print(f"{Back.YELLOW}{Fore.BLACK} ℹ️ INFO: Press 'Enter' at any time to STOP! {Style.RESET_ALL}\n")

    STOP_EVENT.clear()
    
    progress_thread = threading.Thread(target=display_live_progress, args=(total_ips,), daemon=True)
    progress_thread.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_ip, ip, ports_list, dns_list): ip for ip in scan_ips}
        
        for future in concurrent.futures.as_completed(futures):
            if STOP_EVENT.is_set():
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                break
                
            try:
                res = future.result()
                if res:
                    save_and_print(res)
            except Exception:
                pass
            finally:
                COMPLETED_TASKS_COUNT += 1

    progress_thread.join(timeout=1)

# ==========================================
#               MAIN EXECUTION
# ==========================================

def main():
    print(f"\n{Back.BLUE}{Fore.WHITE}  MULTI-PORT CLOUDFLARE SCANNER (v6 - LIVE PROGRESS UI)  {Style.RESET_ALL}")
    
    # ---- بررسی ذخیره بودن اطلاعات روی دسکتاپ ----
    if not load_saved_config():
        # در صورت نبود فایل ذخیره شده، لوکال هاست برای گرفتن اطلاعات باز می شود
        get_user_configs_via_browser()

    # پاک کردن صفحه ترمینال برای شروع کار اسکنر
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"\n{Back.BLUE}{Fore.WHITE}  MULTI-PORT CLOUDFLARE SCANNER (v6 - LIVE PROGRESS UI)  {Style.RESET_ALL}")
    
    detect_isp_and_adjust_fragment()
    
    print(f"\n{Fore.CYAN}1.{Fore.WHITE} Default Scanner (Standard Ports - 8)")
    print(f"{Fore.CYAN}2.{Fore.WHITE} Custom Scanner (Standard Ports - Input IPs)")
    print(f"{Fore.CYAN}3.{Fore.WHITE} Deep Scanner (Ports 1 to 65535 - Takes Time!)")
    print(f"{Fore.CYAN}4.{Fore.WHITE} Hope Mode (Ports 1 to 65535 + Massive DNS List)")
    
    choice = input(f"\n{Fore.YELLOW}» Enter choice (1/2/3/4): {Fore.WHITE}").strip()
    
    scan_ips = []
    ports_to_use = STANDARD_PORTS
    dns_to_use = STANDARD_DNS
    scan_label = ""
    is_custom_ip = False

    if choice in ['1', '3', '4']:
        if choice == '1':
            folder_name = "Scan_Results"
        else:
            folder_name = f"Scan_Results_Mode{choice}"
            
        if not setup_directories(folder_name):
            return
            
        for cidr in CLOUDFLARE_CIDRS:
            scan_ips.extend(generate_random_ips(cidr, SAMPLES_PER_CIDR))
            
        if choice == '1':
            scan_label = "Default Standard Scanner"
        elif choice == '3':
            ports_to_use = ALL_PORTS
            scan_label = "Deep Scanner (Full Port Range)"
        elif choice == '4':
            ports_to_use = ALL_PORTS
            dns_to_use = HOPE_DNS
            scan_label = "HOPE MODE (Full Ports + Massive DNS)"
            
    elif choice == '2':
        if not setup_directories("CustomScanner"):
            return
            
        scan_label = "Custom IPs Scanner"
        user_input = input(f"{Fore.YELLOW}» Enter IPs (comma/space separated): {Fore.WHITE}")
        
        raw_ips = re.split(r'[,\s]+', user_input)
        for ip in raw_ips:
            ip = ip.strip()
            try:
                ipaddress.ip_address(ip)
                scan_ips.append(ip)
            except Exception:
                pass
                
        if not scan_ips:
            return
            
        is_custom_ip = True

    try:
        with open(OUTPUT_FILE, 'w') as f:
            f.write(f"Scan Start: {datetime.now()} - Worker: {WORKER_HOST}\n\n")
    except Exception:
        pass

    stop_monitor_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_monitor_thread.start()

    execute_scan(scan_ips, ports_to_use, dns_to_use, scan_label)

    if choice in ['1', '2'] and len(BEST_PAIRS_FOUND) == 0 and not STOP_EVENT.is_set():
        print(f"\n\n{Back.RED}{Fore.WHITE} ⚠️ NO IPs FOUND ON STANDARD PORTS! {Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔄 Auto-Fallback Triggered: Initiating DEEP SCAN on Range(1-65535)...")
        
        if not is_custom_ip:
            scan_ips = []
            for cidr in CLOUDFLARE_CIDRS:
                scan_ips.extend(generate_random_ips(cidr, SAMPLES_PER_CIDR))
                
        execute_scan(scan_ips, ALL_PORTS, STANDARD_DNS, "DEEP SCAN (Auto Fallback)")

    time.sleep(0.5)
    
    print(f"\n\n{Back.GREEN}{Fore.BLACK}  GENERATING CONFIGS & SUB LINK (Found {len(BEST_PAIRS_FOUND)} Good IPs)  {Style.RESET_ALL}\n")
    
    if not BEST_PAIRS_FOUND:
        print(f"{Fore.RED}❌ No Clean IPs found after all tests.")
        input("Press Enter to exit...")
        return

    sorted_best = sorted(BEST_PAIRS_FOUND, key=lambda x: x['ping'])
    
    clean_ips_list = []
    vless_links_list = []
    global_index = 1

    unique_clean_ips = list(set([data['ip'] for data in sorted_best]))
    print(f"{Fore.YELLOW}🌍 Looking up Countries for {len(unique_clean_ips)} IP(s)...")
    ip_countries_map = get_countries_batch(unique_clean_ips)
    print(f"{Fore.GREEN}✅ Lookup Complete.\n")

    for data in sorted_best:
        p_val = int(data['port'])
        
        if p_val in [443, 2053, 2083, 2087, 2096, 8443]:
            sec_display = "TLS"
        else:
            sec_display = "NONE"
            
        country_code = ip_countries_map.get(data['ip'], "UNK")
        
        if sec_display == "TLS":
            alpn_variants = ["http/1.1", "h2,http/1.1"]
        else:
            alpn_variants = [""]
        
        for alpn in alpn_variants:
            fname = create_config_file(data, global_index, alpn, country_code)
            
            if fname:
                if alpn:
                    alpn_print = alpn
                else:
                    alpn_print = "N/A"
                    
                print(f"{Fore.WHITE}[{global_index}] Cntry: {Fore.YELLOW}{country_code:<3} "
                      f"{Fore.WHITE}| IP: {Fore.GREEN}{data['ip']:<15} "
                      f"{Fore.WHITE}| Port: {Fore.MAGENTA}{data['port']:<5} "
                      f"{Fore.WHITE}| Sec: {Fore.CYAN}{sec_display} "
                      f"{Fore.WHITE}| ALPN: {Fore.YELLOW}{alpn_print:<12} "
                      f"{Fore.WHITE}| Ping: {Fore.YELLOW}{data['ping']}ms")
                
                if data['ip'] not in clean_ips_list:
                    clean_ips_list.append(data['ip'])
                    
                if "h2" in alpn:
                    alias_alpn = "H2"
                elif alpn:
                    alias_alpn = "HTTP1.1"
                else:
                    alias_alpn = "NONE"
                    
                alias = f"🌍{country_code} | {data['ip']}:{data['port']} | {sec_display} | {alias_alpn} | {data['ping']}ms"
                
                if sec_display == "TLS":
                    sec_param = "tls"
                    alpn_param = f"&alpn={alpn}&sni={WORKER_HOST}"
                else:
                    sec_param = "none"
                    alpn_param = ""
                    
                vless_link = (
                    f"vless://{USER_UUID}@{data['ip']}:{data['port']}"
                    f"?encryption=none&security={sec_param}&type=ws&host={WORKER_HOST}"
                    f"&path={urllib.parse.quote(WS_PATH)}&fp=chrome{alpn_param}#{urllib.parse.quote(alias)}"
                )
                
                vless_links_list.append(vless_link)
                
            global_index += 1

    if clean_ips_list:
        try:
            with open(CLEAN_IPS_FILE, 'w', encoding='utf-8') as f:
                f.write(",".join(clean_ips_list))
        except Exception:
            pass
            
    if vless_links_list:
        try:
            with open(SUBSCRIPTION_FILE, "w", encoding='utf-8') as f:
                all_links_text = "\n".join(vless_links_list)
                encoded_bytes = base64.b64encode(all_links_text.encode("utf-8"))
                f.write(encoded_bytes.decode("utf-8"))
        except Exception:
            pass

    print(f"\n{Fore.CYAN}┌{'─'*60}┐")
    print(f"{Fore.CYAN}│ {Fore.WHITE}{Style.BRIGHT}{'📊 SCAN SUMMARY REPORT':^58} {Fore.CYAN}│")
    print(f"{Fore.CYAN}├{'─'*60}┤")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Clean/Working IPs:   {Fore.GREEN}{str(len(clean_ips_list)):<37} {Fore.CYAN}│")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Total Configs Gen:   {Fore.MAGENTA}{str(len(vless_links_list)):<37} {Fore.CYAN}│")
    print(f"{Fore.CYAN}├{'─'*60}┤")
    print(f"{Fore.CYAN}│ {Fore.GREEN}✅ Subscription file created: {Fore.WHITE}{'sub.txt':<29} {Fore.CYAN}│")
    print(f"{Fore.CYAN}│ {Fore.GREEN}📂 Saved Folder: {Fore.WHITE}{TARGET_DIR:<43} {Fore.CYAN}│")
    print(f"{Fore.CYAN}└{'─'*60}┘\n")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
