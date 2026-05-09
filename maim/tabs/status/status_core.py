# tabs/status/status_core.py
import threading
import time
import subprocess
import re
import socket
import psutil
import requests
from .status_utils import StatusUtils

# ثابت‌های پایش
MONITOR_SPEED_INTERVAL = 1.0      # هر ۱ ثانیه سرعت لحظه‌ای
MONITOR_PING_INTERVAL = 10.0     # هر ۱۰ ثانیه پینگ و پکت‌لاس
MONITOR_IP_INTERVAL = 30.0       # هر ۳۰ ثانیه IP عمومی


class StatusCore:
    """جمع‌آوری واقعی اطلاعات و محاسبه شاخص کیفیت شبکه"""

    def __init__(self, app_controller):
        self.app = app_controller
        self.running = False
        self._stop_event = threading.Event()

        # داده‌های لحظه‌ای
        self.data = {
            "vpn": {"connected": False, "protocol": "", "server": "", "ip": ""},
            "dns": {"connected": False, "server": ""},
            "warp": {"connected": False},
            "tor": {"connected": False},
            "psiphon": {"connected": False},
            "antifilter": {"running": False},
            "gaming": {"accelerator": False, "ping_stab": False},
            "messenger": {"hosting": False, "connected": False},
            "browser": {"tor_mode": False},
            "network": {
                "ping": 0,
                "packet_loss": 0.0,
                "download_speed": 0.0,   # KB/s
                "upload_speed": 0.0,
                "public_ip": "",
                "country": "",
                "isp": "",
                "countryCode": "UN"
            }
        }
        self.network_quality_index = 50   # مقدار اولیه

        # برای محاسبه سرعت لحظه‌ای
        self._last_net_io = psutil.net_io_counters()
        self._last_io_time = time.time()

        # زمان آخرین به‌روزرسانی‌ها
        self._last_ping_time = 0.0
        self._last_ip_time = 0.0

    # -----------------------------------------------------------------
    def start_monitoring(self):
        self.running = True
        self._stop_event.clear()
        self._last_net_io = psutil.net_io_counters()
        self._last_io_time = time.time()
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop_monitoring(self):
        self.running = False
        self._stop_event.set()

    # -----------------------------------------------------------------
    def _monitor_loop(self):
        while not self._stop_event.is_set():
            now = time.time()

            # ۱. سرعت لحظه‌ای (هر ۱ ثانیه)
            if now - self._last_io_time >= MONITOR_SPEED_INTERVAL:
                self._update_speed()

            # ۲. وضعیت سرویس‌ها (هر ۲ ثانیه)
            self._collect_services_status()

            # ۳. پینگ و پکت‌لاس (هر ۱۰ ثانیه)
            if now - self._last_ping_time >= MONITOR_PING_INTERVAL:
                self._update_network_quality()
                self._last_ping_time = now

            # ۴. IP عمومی (هر ۳۰ ثانیه)
            if now - self._last_ip_time >= MONITOR_IP_INTERVAL:
                self._update_public_ip()
                self._last_ip_time = now

            # ۵. محاسبه شاخص کیفیت
            self._calculate_quality_index()

            time.sleep(0.5)   # چک مداوم

    # -----------------------------------------------------------------
    # سرعت لحظه‌ای با psutil
    def _update_speed(self):
        try:
            now = time.time()
            current_io = psutil.net_io_counters()
            dt = now - self._last_io_time
            if dt <= 0:
                return
            dl_bytes = current_io.bytes_recv - self._last_net_io.bytes_recv
            ul_bytes = current_io.bytes_sent - self._last_net_io.bytes_sent
            self.data["network"]["download_speed"] = round(dl_bytes / 1024 / dt, 1)
            self.data["network"]["upload_speed"] = round(ul_bytes / 1024 / dt, 1)
            self._last_net_io = current_io
            self._last_io_time = now
        except Exception:
            pass

    # -----------------------------------------------------------------
    # وضعیت تمام سرویس‌ها از core فریم‌ها
    def _collect_services_status(self):
        # VPN Client (ClientUI)
        if hasattr(self.app, 'client_frame') and hasattr(self.app.client_frame, 'core'):
            self.data["vpn"]["connected"] = self.app.client_frame.core.is_connected
            if self.data["vpn"]["connected"]:
                self.data["vpn"]["protocol"] = "VLESS/V2Ray"
                sel = self.app.client_frame.config_manager.get_selected_config()
                self.data["vpn"]["server"] = sel if sel else "Unknown"
            else:
                self.data["vpn"]["protocol"] = ""
                self.data["vpn"]["server"] = ""
        else:
            self.data["vpn"]["connected"] = False

        # DNS Changer
        if hasattr(self.app, 'dns_frame'):
            self.data["dns"]["connected"] = getattr(self.app.dns_frame, 'is_connected', False)
            self.data["dns"]["server"] = getattr(self.app.dns_frame, 'current_full_addr', '')

        # WARP
        if hasattr(self.app, 'warp_frame'):
            self.data["warp"]["connected"] = getattr(self.app.warp_frame, 'is_connected', False)

        # Tor
        if hasattr(self.app, 'tor_frame'):
            self.data["tor"]["connected"] = getattr(self.app.tor_frame, 'is_running', False)

        # Psiphon
        if hasattr(self.app, 'psiphon_frame'):
            self.data["psiphon"]["connected"] = getattr(self.app.psiphon_frame, 'is_connected', False)

        # Anti-Filter
        if hasattr(self.app, 'antifilter_frame'):
            self.data["antifilter"]["running"] = getattr(self.app.antifilter_frame, 'is_running', False)

        # Gaming
        if hasattr(self.app, 'gaming_frame'):
            self.data["gaming"]["accelerator"] = getattr(self.app.gaming_frame, 'accelerator_active', False)
            self.data["gaming"]["ping_stab"] = getattr(self.app.gaming_frame, 'ping_active', False)

        # Messenger
        if hasattr(self.app, 'messenger_frame'):
            self.data["messenger"]["hosting"] = getattr(self.app.messenger_frame, 'is_hosting', False)
            self.data["messenger"]["connected"] = getattr(self.app.messenger_frame, 'is_connected', False)

        # Browser Tor mode
        if hasattr(self.app, 'browser_frame'):
            self.data["browser"]["tor_mode"] = getattr(self.app.browser_frame, 'tor_mode', False)

    # -----------------------------------------------------------------
    # پینگ و پکت‌لاس به 8.8.8.8
    def _update_network_quality(self):
        host = "8.8.8.8"
        try:
            # پینگ ۳ بسته
            cmd = ["ping", "-n", "3", host] if hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT') else ["ping", "-c", "3", host]
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            output = result.stdout

            # پینگ متوسط
            match = re.search(r"Average = (\d+)ms", output)
            if match:
                self.data["network"]["ping"] = int(match.group(1))
            else:
                # fallback
                self.data["network"]["ping"] = 0

            # پکت‌لاس
            match = re.search(r"Lost = (\d+)", output)
            if match:
                lost = int(match.group(1))
                self.data["network"]["packet_loss"] = round((lost / 3) * 100, 1)
            else:
                # ممکنه 0% باشه
                if "0% loss" in output or "0% packet loss" in output:
                    self.data["network"]["packet_loss"] = 0.0
        except Exception:
            # در صورت خطا، مقدار پیش‌فرض
            self.data["network"]["ping"] = 0
            self.data["network"]["packet_loss"] = 0.0

    # -----------------------------------------------------------------
    # IP عمومی و ISP
    def _update_public_ip(self):
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.data["network"]["public_ip"] = data.get("query", "")
                self.data["network"]["country"] = data.get("country", "Unknown")
                self.data["network"]["isp"] = data.get("isp", "Unknown")
                self.data["network"]["countryCode"] = data.get("countryCode", "UN")
        except Exception:
            pass

    # -----------------------------------------------------------------
    def _calculate_quality_index(self):
        ping = self.data["network"]["ping"]
        loss = self.data["network"]["packet_loss"]

        # هرچه پینگ کمتر و لاس صفرتر، امتیاز بالاتر
        ping_score = max(0, 100 - ping * 0.5)
        loss_score = max(0, 100 - loss * 10)
        self.network_quality_index = int((ping_score + loss_score) / 2)

    # -----------------------------------------------------------------
    def get_data(self):
        return self.data

    def get_quality(self):
        return self.network_quality_index
