# tabs/browser/browser_core.py
import threading
import time
import subprocess
import os
import sys


class TorController:
    """مدیریت تور برای حالت Built-in Tor Mode"""
    
    def __init__(self, log_callback=None):
        self.tor_process = None
        self.running = False
        self.log_callback = log_callback
        self.socks_port = 9050
        self.control_port = 9051
    
    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
    
    def start_tor(self):
        """شروع فرآیند تور در پس‌زمینه"""
        if self.running:
            return True
        
        # پیدا کردن مسیر tor
        tor_path = self._find_tor()
        if not tor_path:
            self.log("❌ Tor not found. Please install Tor Browser or tor service.")
            return False
        
        try:
            self.tor_process = subprocess.Popen(
                [tor_path, "--SocksPort", str(self.socks_port), "--ControlPort", str(self.control_port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.running = True
            self.log("✅ Tor started successfully on port 9050")
            return True
        except Exception as e:
            self.log(f"❌ Failed to start Tor: {str(e)}")
            return False
    
    def _find_tor(self):
        """پیدا کردن مسیر اجرایی تور"""
        import shutil
        tor_path = shutil.which("tor")
        if tor_path:
            return tor_path
        
        # مسیرهای پیش‌فرض در ویندوز
        if sys.platform == "win32":
            possible_paths = [
                "C:\\Program Files\\Tor\\tor.exe",
                "C:\\Program Files (x86)\\Tor\\tor.exe",
                os.path.expanduser("~\\Desktop\\Tor Browser\\Browser\\TorBrowser\\Tor\\tor.exe")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path
        return None
    
    def stop_tor(self):
        """متوقف کردن تور"""
        if self.tor_process:
            self.tor_process.terminate()
            self.tor_process = None
        self.running = False
        self.log("🛑 Tor stopped")
    
    def get_proxy_config(self):
        """بازگرداندن تنظیمات پروکسی تور برای استفاده در مرورگر"""
        if self.running:
            return {"http": f"socks5://127.0.0.1:{self.socks_port}", "https": f"socks5://127.0.0.1:{self.socks_port}"}
        return None
