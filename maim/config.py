# config.py

import os
import json
from tabs.crypto_manager import StorageCrypto


# ==========================================
# تنظیمات تست سرعت اسکنر
# ==========================================
TEST_DL_LIMIT_KB = 50      # حجم دانلود تست (کیلوبایت)
TEST_UL_SIZE_KB = 15       # حجم آپلود تست (کیلوبایت)
TIMEOUT = 3                # تایم‌اوت کلی (ثانیه)

# === Cloudflare Theme Colors ===
CF_ORANGE = "#F38020"
CF_ORANGE_HOVER = "#D9680B"
BG_DARK = "#18181B"      # پس زمینه بسیار تیره و مدرن
BG_PANEL = "#27272A"     # رنگ پنل‌ها و فریم‌ها

# === Pre‑Processor Settings ===
PREPROCESSOR_PORT = 10815   # پورت پیش‌فرض برای پراکسی SOCKS5 محلی

STANDARD_PORTS = [80, 443, 8080, 8880, 2052, 2082, 2095, 2053]
ALL_PORTS = list(range(1, 65536))
SAMPLES_PER_CIDR = 200
MAX_WORKERS = 50

# لینک API برای دریافت مستقیم IPهای تمیز کلودفلر (میتوانید تغییر دهید)
CF_API_URL = "https://raw.githubusercontent.com/vfarid/cf-ip-scanner/main/ipv4.txt"

CLOUDFLARE_CIDRS = [
    # Comprehensive Cloudflare IPv4 CIDR List
    # Source: Aggregated from official Cloudflare API, AS13335 records, and community-maintained scanners

    # Core Official Ranges (Cloudflare's own list)
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "108.162.192.0/18",
    "131.0.72.0/22",
    "141.101.64.0/18",
    "162.158.0.0/15",
    "172.64.0.0/13",
    "173.245.48.0/20",
    "188.114.96.0/20",
    "190.93.240.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",

    # Additional Known & Extended Ranges (Collected from AS13335, Scanners, and Community)
    "5.226.176.0/24",
    "5.226.177.0/24",
    "5.226.178.0/24",
    "5.226.179.0/24",
    "5.226.180.0/24",
    "5.226.181.0/24",
    "5.226.182.0/24",
    "5.226.183.0/24",
    "23.227.38.0/24",
    "23.227.39.0/24",
    "23.227.60.0/24",
    "23.247.163.0/24",
    "31.22.116.0/24",
    "31.43.179.0/24",
    "45.8.104.0/24",
    "45.8.105.0/24",
    "45.8.106.0/24",
    "45.8.107.0/24",
    "45.8.211.0/24",
    "45.12.30.0/24",
    "45.12.31.0/24",
    "45.14.174.0/24",
    "45.32.177.0/24",
    "45.67.215.0/24",
    "45.80.111.0/24",
    "45.85.118.0/24",
    "45.85.119.0/24",
    "45.87.175.0/24",
    "45.94.169.0/24",
    "45.95.240.0/24",
    "45.95.241.0/24",
    "45.95.242.0/24",
    "45.95.243.0/24",
    "45.131.4.0/24",
    "45.131.5.0/24",
    "45.131.6.0/24",
    "45.131.7.0/24",
    "45.131.208.0/24",
    "45.131.209.0/24",
    "45.131.210.0/24",
    "45.131.211.0/24",
    "45.133.247.0/24",
    "45.142.120.0/24",
    "45.159.216.0/24",
    "45.159.217.0/24",
    "45.159.218.0/24",
    "45.159.219.0/24",
    "63.141.128.0/24",
    "64.68.192.0/24",
    "66.81.247.0/24",
    "66.235.200.0/24",
    "69.84.182.0/24",
    "80.94.83.0/24",
    "89.47.56.0/24",
    "89.116.250.0/24",
    "89.207.18.0/24",
    "91.193.58.0/24",
    "91.195.110.0/24",
    "93.114.64.0/24",
    "94.140.0.0/24",
    "103.11.212.0/24",
    "103.11.214.0/24",
    "103.160.204.0/24",
    "103.169.142.0/24",
    "103.172.110.0/24",
    "103.172.111.0/24",
    "103.184.44.0/24",
    "103.184.45.0/24",
    "154.84.175.0/24",
    "185.62.140.0/22"
]

# دی‌ان‌اس‌های پیشفرض (در برنامه قابل ویرایش است)
DEFAULT_DNS = [
    "1.1.1.1", "8.8.8.8", "9.9.9.9", "78.157.42.100", "178.22.122.100"
]

# ==========================================
# مدیریت مسیر ذخیره‌سازی (قابل تنظیم توسط کاربر)
# ==========================================
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data", "Settings", "storage_path.json")
DEFAULT_BASE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data")

def load_storage_path():
    """بارگذاری مسیر ذخیره‌سازی از فایل پیکربندی"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                custom_path = data.get('base_dir', DEFAULT_BASE_DIR)
                if os.path.exists(os.path.dirname(custom_path)):
                    return custom_path
    except Exception:
        pass
    return DEFAULT_BASE_DIR

def save_storage_path(path):
    """ذخیره مسیر جدید در فایل پیکربندی"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'base_dir': path}, f, indent=2)
        return True
    except Exception:
        return False

def reset_storage_path():
    """بازنشانی به مسیر پیش‌فرض (دسکتاپ)"""
    return save_storage_path(DEFAULT_BASE_DIR)

# مسیر پایه فعلی (قابل تغییر توسط کاربر)
BASE_DIR = load_storage_path()

# زیرپوشه‌های مرتب‌شده
DIRS = {
    "configs": os.path.join(BASE_DIR, "Configs"),
    "subs": os.path.join(BASE_DIR, "Subscriptions"),
    "settings": os.path.join(BASE_DIR, "Settings")
}

def update_dirs(new_base_dir):
    """به‌روزرسانی مسیرهای DIRS بر اساس مسیر جدید"""
    global BASE_DIR, DIRS
    BASE_DIR = new_base_dir
    DIRS = {
        "configs": os.path.join(BASE_DIR, "Configs"),
        "subs": os.path.join(BASE_DIR, "Subscriptions"),
        "settings": os.path.join(BASE_DIR, "Settings")
    }
    # ساخت پوشه‌ها
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)

# ساخت خودکار پوشه‌ها در صورت عدم وجود در هنگام اجرای برنامه
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# ==========================================
# رمزنگاری ذخیره‌سازی
# ==========================================
storage_crypto = StorageCrypto(storage_dir=DIRS["settings"])
