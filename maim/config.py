# config.py

import os

# === Cloudflare Theme Colors ===
CF_ORANGE = "#F38020"
CF_ORANGE_HOVER = "#D9680B"
BG_DARK = "#18181B"      # پس زمینه بسیار تیره و مدرن
BG_PANEL = "#27272A"     # رنگ پنل‌ها و فریم‌ها

STANDARD_PORTS =[80, 443, 8080, 8880, 2052, 2082, 2095, 2053]
ALL_PORTS = list(range(1, 65536))
SAMPLES_PER_CIDR = 200
MAX_WORKERS = 50
TIMEOUT = 3

# لینک API برای دریافت مستقیم IPهای تمیز کلودفلر (میتوانید تغییر دهید)
CF_API_URL = "https://raw.githubusercontent.com/vfarid/cf-ip-scanner/main/ipv4.txt"

CLOUDFLARE_CIDRS =[
    "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "104.16.0.0/13",
    "104.24.0.0/14", "108.162.192.0/18", "131.0.72.0/22", "141.101.64.0/18",
    "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
    "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "8.238.64.0/18", "8.242.72.0/21", "8.243.216.0/21", "45.188.16.0/22"
]

# دی‌ان‌اس‌های پیشفرض (در برنامه قابل ویرایش است)
DEFAULT_DNS =[
    "1.1.1.1", "8.8.8.8", "9.9.9.9", "78.157.42.100", "178.22.122.100"
]

# ==========================================
# سیستم پوشه‌بندی مرکزی در دسکتاپ
# ==========================================
# یک پوشه تمیز روی دسکتاپ کاربر برای تمام اطلاعات نرم‌افزار ساخته می‌شود
BASE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data")

# زیرپوشه‌های مرتب‌شده
DIRS = {
    "configs": os.path.join(BASE_DIR, "Configs"),
    "subs": os.path.join(BASE_DIR, "Subscriptions"),
    "settings": os.path.join(BASE_DIR, "Settings")
}

# ساخت خودکار پوشه‌ها در صورت عدم وجود در هنگام اجرای برنامه
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)