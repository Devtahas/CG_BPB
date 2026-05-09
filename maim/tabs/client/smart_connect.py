# tabs/client/smart_connect.py

import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import json
import os
import random
import socket
import concurrent.futures
from typing import Optional, Dict, Any, List

# وابستگی‌های داخلی برنامه
from config import CF_ORANGE, BG_PANEL, DIRS
from tabs.crypto_manager import storage_crypto

# ایمپورت‌های اختیاری (در صورت وجود)
try:
    from tabs.scanner.scanner_utils import ScannerUtils
    from tabs.dns.dns_hunter import DNSHunter
    from tabs.client.mimicry import MimicryManager
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SmartConnect(ctk.CTkFrame):
    """
    دستیار هوشمند اتصال – بهینه‌سازی کامل و اتصال خودکار.
    بهترین DNS، پورت، کانفیگ، Fragment، Fingerprint و Padding را پیدا کرده و اعمال می‌کند.
    """

    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_controller
        self.grid_columnconfigure(0, weight=1)

        self.best_dns = None
        self.best_port = None
        self.best_config = None
        self.best_fragment = None
        self.best_fingerprint = None
        self.best_padding = None
        self.is_optimizing = False

        # نمونه‌های کمکی
        self.dns_hunter = DNSHunter() if SCANNER_AVAILABLE else None
        self.mimicry_manager = None
        if self.app and hasattr(self.app, 'client_frame'):
            client_frame = self.app.client_frame
            if hasattr(client_frame, 'mimicry_manager'):
                self.mimicry_manager = client_frame.mimicry_manager

        self.setup_ui()

    # -----------------------------------------------------------------
    def setup_ui(self):
        # عنوان
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(20, 10))
        ctk.CTkLabel(header, text="🧠 Smart Connect",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=CF_ORANGE).pack(side="left", padx=20)

        # توضیح
        ctk.CTkLabel(self,
                     text="Automatically selects the best port, DNS, config, fragment and more based on your network.",
                     text_color="gray", wraplength=500).pack(pady=(0, 15))

        # پنل نتایج
        res_panel = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        res_panel.pack(fill="both", expand=True, padx=20, pady=10)

        # نوار پیشرفت
        self.progress = ctk.CTkProgressBar(res_panel, progress_color=CF_ORANGE)
        self.progress.pack(fill="x", padx=20, pady=(20, 5))
        self.progress.set(0)

        self.lbl_status = ctk.CTkLabel(res_panel, text="Ready", text_color="gray")
        self.lbl_status.pack(pady=(0, 10))

        # جعبه متن برای نمایش لاگ
        self.txt_log = ctk.CTkTextbox(res_panel, height=180, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=5)

        # دکمه‌ها
        btn_frame = ctk.CTkFrame(res_panel, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.btn_optimize = ctk.CTkButton(btn_frame, text="🔍 OPTIMIZE",
                                          fg_color=CF_ORANGE, text_color="black",
                                          font=ctk.CTkFont(weight="bold"),
                                          command=self.start_optimization)
        self.btn_optimize.pack(side="left", padx=5)

        self.btn_connect = ctk.CTkButton(btn_frame, text="⚡ CONNECT NOW",
                                         fg_color="#2E7D32", hover_color="#1B5E20",
                                         font=ctk.CTkFont(weight="bold"),
                                         command=self.apply_and_connect, state="disabled")
        self.btn_connect.pack(side="left", padx=5)

    # -----------------------------------------------------------------
    def log(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.update_idletasks()

    def set_progress(self, val: float, status: str = ""):
        self.progress.set(val)
        if status:
            self.lbl_status.configure(text=status)
        self.update_idletasks()

    # -----------------------------------------------------------------
    def start_optimization(self):
        if self.is_optimizing:
            return
        self.is_optimizing = True
        self.btn_optimize.configure(state="disabled", text="⏳ ANALYZING...")
        self.txt_log.delete("1.0", "end")
        self.btn_connect.configure(state="disabled")

        threading.Thread(target=self._optimization_thread, daemon=True).start()

    def _optimization_thread(self):
        try:
            # 1. بهترین DNS
            self.set_progress(0.15, "Testing DNS...")
            self.log("🔍 Finding best DNS...")
            self.best_dns = self._find_best_dns()
            self.log(f"✅ Best DNS: {self.best_dns or 'None (using system)'}")

            # 2. بهترین پورت
            self.set_progress(0.3, "Scanning ports...")
            self.log("🔌 Finding best port...")
            self.best_port = self._find_best_port()
            self.log(f"✅ Best Port: {self.best_port or 'default'}")

            # 3. بهترین کانفیگ
            self.set_progress(0.5, "Evaluating configs...")
            self.log("📁 Selecting best config...")
            self.best_config = self._select_best_config()
            if self.best_config:
                self.log(f"✅ Best Config: {os.path.basename(self.best_config)}")
            else:
                self.log("⚠️ No config available. Please import a config first.")

            # 4. Fragment و Fingerprint
            self.set_progress(0.75, "Optimizing DPI bypass...")
            self.log("🧩 Optimizing DPI bypass (fragment & fingerprint)...")
            self._optimize_dpi_bypass()
            self.log(f"✅ Fragment: {self.best_fragment}")
            self.log(f"✅ Fingerprint: {self.best_fingerprint}")

            # 5. Padding
            self.set_progress(0.9, "Selecting padding...")
            self.log("🧱 Selecting best padding...")
            self._select_padding()
            self.log(f"✅ Padding: {self.best_padding}")

            # خلاصه
            self.set_progress(1.0, "Done!")
            self.after(0, self._display_summary)

        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
        finally:
            self.is_optimizing = False
            self.after(0, lambda: self.btn_optimize.configure(state="normal", text="🔍 OPTIMIZE"))

    # -----------------------------------------------------------------
    def _find_best_dns(self) -> Optional[str]:
        """
        تست سریع چند DNS معروف و انتخاب سریع‌ترین.
        اگر DNSHunter موجود باشد، از کوئری UDP استفاده می‌کند.
        """
        test_dns_list = [
            "8.8.8.8", "1.1.1.1", "9.9.9.9", "178.22.122.100",
            "78.157.42.100", "208.67.222.222", "94.140.14.14", "185.228.168.9"
        ]
        if SCANNER_AVAILABLE and self.dns_hunter:
            results = []
            for dns in test_dns_list:
                try:
                    latency, ok = ScannerUtils.ping_dns_udp(dns, query_domain="google.com", timeout=2.0)
                    if ok:
                        results.append({"dns": dns, "latency": latency})
                except Exception:
                    pass
            if results:
                best = min(results, key=lambda x: x['latency'])
                return best['dns']

        # Fallback با سوکت TCP:53
        best, best_ping = None, 9999
        for dns in test_dns_list:
            try:
                start = time.time()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                s.connect((dns, 53))
                s.close()
                ping = int((time.time() - start) * 1000)
                if ping < best_ping:
                    best_ping = ping
                    best = dns
            except:
                pass
        return best

    def _find_best_port(self) -> Optional[int]:
        """
        اگر کانفیگ انتخاب شده داشته باشیم، پورت آن را برمی‌گردانیم.
        در غیر این صورت از میان چند پورت معروف تست سریع انجام می‌دهیم.
        """
        # چک کانفیگ فعلی
        client = getattr(self.app, 'client_frame', None)
        if client and hasattr(client, 'config_manager'):
            sel = client.config_manager.get_selected_config()
            if sel:
                try:
                    data = storage_crypto.load_json(sel)
                    if data:
                        out = data.get("outbounds", [{}])[0]
                        port = out.get("settings", {}).get("vnext", [{}])[0].get("port")
                        if port:
                            return int(port)
                except:
                    pass

        # تست سریع چند پورت
        test_ports = [443, 2053, 2083, 2087, 2096]
        best_port, best_ping = None, 9999
        for port in test_ports:
            try:
                start = time.time()
                with socket.create_connection(("1.1.1.1", port), timeout=1.5):
                    ping = int((time.time() - start) * 1000)
                    if ping < best_ping:
                        best_ping = ping
                        best_port = port
            except:
                continue
        return best_port

    def _select_best_config(self) -> Optional[str]:
        """
        از میان کانفیگ‌های موجود، آن که پینگ کمتری دارد را انتخاب می‌کند.
        """
        client = getattr(self.app, 'client_frame', None)
        if not client or not hasattr(client, 'config_manager'):
            return None
        items = client.config_manager.config_buttons
        if not items:
            return None

        best_path, best_ping = None, 9999
        for item in items:
            try:
                ping_str = item["lbl_ping"].cget("text")
                if "ms" in ping_str and "--" not in ping_str:
                    ping = int(ping_str.replace(" ms", "").strip())
                    if ping < best_ping:
                        best_ping = ping
                        best_path = item["path"]
            except:
                pass
        if best_path:
            return best_path
        # اگر پینگی وجود نداشت، کانفیگ انتخاب شده فعلی را برگردان
        return client.config_manager.get_selected_config()

    def _optimize_dpi_bypass(self):
        """
        بر اساس ISP کاربر، fragment و fingerprint بهینه را انتخاب می‌کند.
        """
        fragment = {"packets": "1-1", "length": "100-200", "interval": "1"}
        fingerprint = "chrome"

        try:
            if REQUESTS_AVAILABLE:
                resp = requests.get("http://ip-api.com/json/", timeout=5).json()
                isp = resp.get("isp", "").lower()
                org = resp.get("org", "").lower()
                if any(kw in isp or kw in org for kw in ['mci', 'hamrah']):
                    fragment = {"packets": "1-1", "length": "10-20", "interval": "5"}
                    fingerprint = "firefox"
                elif any(kw in isp or kw in org for kw in ['mtn', 'irancell']):
                    fragment = {"packets": "1-1", "length": "1-3", "interval": "10"}
                    fingerprint = "chrome"
                elif 'rightel' in isp:
                    fragment = {"packets": "1-1", "length": "20-40", "interval": "5"}
                    fingerprint = "safari"
        except:
            pass

        self.best_fragment = fragment
        self.best_fingerprint = fingerprint

    def _select_padding(self):
        """
        اگر Traffic Mimicry فعال باشد، مقادیر padding را از پروفایل می‌خواند.
        """
        if self.mimicry_manager and self.mimicry_manager.enabled:
            prof = self.mimicry_manager.current_profile
            if prof:
                min_p = prof.traffic.padding_min_bytes
                max_p = prof.traffic.padding_max_bytes
                self.best_padding = f"{min_p}-{max_p} bytes"
                return
        self.best_padding = "0-128 bytes (default)"

    def _display_summary(self):
        """
        نمایش خلاصه بهینه‌سازی و فعال‌سازی دکمه اتصال.
        """
        sb = []
        sb.append("=" * 45)
        sb.append("📊 SMART CONNECT SUMMARY")
        sb.append("-" * 45)
        sb.append(f"🌐 DNS          : {self.best_dns or 'Auto'}")
        sb.append(f"🔌 Port         : {self.best_port or 'Default'}")
        sb.append(f"📁 Config       : {os.path.basename(self.best_config) if self.best_config else 'None'}")
        sb.append(f"🧩 Fragment     : {self.best_fragment}")
        sb.append(f"🖐 Fingerprint  : {self.best_fingerprint}")
        sb.append(f"🧱 Padding      : {self.best_padding}")
        sb.append("=" * 45)
        summary = "\n".join(sb)
        self.txt_log.insert("end", "\n" + summary + "\n")
        self.txt_log.see("end")

        self.btn_connect.configure(state="normal")

    def apply_and_connect(self):
        """
        اعمال تنظیمات بهینه روی کلاینت و شروع اتصال VPN.
        """
        client = getattr(self.app, 'client_frame', None)
        if not client:
            messagebox.showerror("Error", "VPN Client not available.")
            return

        # 1. DNS
        dns_frame = getattr(self.app, 'dns_frame', None)
        if dns_frame and self.best_dns:
            dns_data = dns_frame.servers_manager.find_by_primary(self.best_dns)
            if not dns_data:
                dns_data = {"name": "Smart DNS", "primary": self.best_dns, "secondary": "", "type": "IPv4"}
            dns_frame.current_dns_info = dns_data
            dns_frame.connect_dns()

        # 2. انتخاب کانفیگ
        if self.best_config:
            client.config_manager.select_config(self.best_config, None)

        # 3. Fragment و fingerprint
        if self.best_fragment:
            client.core.dpi_settings.update({
                "fragment": True,
                "frag_packets": self.best_fragment["packets"],
                "frag_length": self.best_fragment["length"],
                "frag_interval": self.best_fragment["interval"]
            })
        if self.best_fingerprint:
            client.core.dpi_settings["fingerprint"] = self.best_fingerprint

        # 4. اتصال
        client.start_connection()
        messagebox.showinfo("Smart Connect", "Connected with optimized settings!")
