# tabs/client/vpn_chain.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import os
import socket
import requests
from config import CF_ORANGE, BG_PANEL, DIRS
from tabs.crypto_manager import storage_crypto

try:
    from tabs.scanner.scanner_utils import ScannerUtils
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False


class ChainOptimizer:
    """بهینه‌ساز زنجیره: انتخاب بهترین تنظیمات"""

    @staticmethod
    def find_best_dns() -> str:
        test_dns = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "178.22.122.100",
                    "78.157.42.100", "208.67.222.222", "94.140.14.14", "185.228.168.9"]
        best, best_ping = None, 9999
        for dns in test_dns:
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
        return best if best else "8.8.8.8"

    @staticmethod
    def find_best_port(client_ui) -> int:
        """client_ui: نمونه ClientUI"""
        if client_ui and hasattr(client_ui, 'config_manager'):
            sel = client_ui.config_manager.get_selected_config()
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
        return best_port if best_port else 443

    @staticmethod
    def select_best_config(client_ui) -> str:
        if not client_ui or not hasattr(client_ui, 'config_manager'):
            return None
        items = client_ui.config_manager.config_buttons
        if not items:
            return client_ui.config_manager.get_selected_config()
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
        return best_path if best_path else client_ui.config_manager.get_selected_config()

    @staticmethod
    def get_isp_fragment_and_fingerprint():
        fragment = {"packets": "1-1", "length": "100-200", "interval": "1"}
        fingerprint = "chrome"
        try:
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
        return fragment, fingerprint


class VpnChainFrame(ctk.CTkFrame):
    """داشبورد اتصال زنجیره‌ای: Mimicry → Pre‑VPN → Main"""

    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_controller          # این همان ClientUI است
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # حالا تمام اجزای مورد نیاز از self.app قابل دسترسی‌اند
        self.core = self.app.core
        self.mimicry_manager = self.app.mimicry_manager

        self.chain_active = False
        self.best_dns = None
        self.best_config = None
        self.best_fragment = None
        self.best_fingerprint = None
        self.selected_pre_vpn_path = None

        self.setup_ui()

    def setup_ui(self):
        # ---- Header ----
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, pady=(20, 10), sticky="ew")
        ctk.CTkLabel(header, text="🔁 VPN‑in‑VPN Chain",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=CF_ORANGE).pack(side="left", padx=20)

        # ---- Status frame (مشابه Connection) ----
        self.status_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.status_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Status: Disconnected",
                                       font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.lbl_traffic = ctk.CTkLabel(self.status_frame, text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s",
                                        font=ctk.CTkFont(size=14, weight="bold"), text_color="#29B6F6")
        self.lbl_traffic.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")

        # IP Info
        self.ip_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.ip_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")
        self.lbl_ip = ctk.CTkLabel(self.ip_frame, text="", font=ctk.CTkFont(size=13))
        self.lbl_ip.pack(side="left")
        self.btn_check_ip = ctk.CTkButton(self.ip_frame, text="🌍 Check IP", width=90,
                                          fg_color="transparent", border_width=1,
                                          border_color="#29B6F6", text_color="#29B6F6",
                                          command=self.check_ip)
        self.btn_check_ip.pack(side="left", padx=10)

        # دکمه اتصال
        self.btn_connect = ctk.CTkButton(self.status_frame, text="⚡ START CHAIN",
                                         fg_color="#2E7D32", hover_color="#1B5E20",
                                         font=ctk.CTkFont(weight="bold", size=14),
                                         command=self.toggle_chain)
        self.btn_connect.grid(row=0, column=2, rowspan=3, padx=20, pady=15, sticky="e")

        # ---- Progress & Log ----
        self.progress = ctk.CTkProgressBar(self, progress_color=CF_ORANGE)
        self.progress.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.progress.set(0)

        self.log_text = ctk.CTkTextbox(self, height=120, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_text.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        # ---- اطلاعات تکمیلی (پینگ و ...) ----
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.lbl_ping = ctk.CTkLabel(info_frame, text="Ping: -- ms", font=ctk.CTkFont(weight="bold"))
        self.lbl_ping.pack(side="left", padx=10)
        self.lbl_packetloss = ctk.CTkLabel(info_frame, text="Loss: --%")
        self.lbl_packetloss.pack(side="left", padx=10)

    # ---------- logging ----------
    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.update_idletasks()

    def set_progress(self, val, text=""):
        self.progress.set(val)
        if text:
            self.lbl_status.configure(text=text)
        self.update_idletasks()

    # ---------- بهینه‌سازی و اتصال ----------
    def toggle_chain(self):
        if self.chain_active:
            self.disconnect_chain()
        else:
            self.start_chain()

    def start_chain(self):
        """اجرای هوشمند زنجیره"""
        self.btn_connect.configure(state="disabled", text="⏳ OPTIMIZING...")
        self.log_text.delete("1.0", "end")
        self.chain_active = True

        threading.Thread(target=self._chain_thread, daemon=True).start()

    def _chain_thread(self):
        try:
            # 1. انتخاب بهترین DNS
            self.set_progress(0.1, "Finding best DNS...")
            self.log("🔍 Finding best DNS...")
            self.best_dns = ChainOptimizer.find_best_dns()
            self.log(f"  ✅ DNS: {self.best_dns}")

            # 2. انتخاب بهترین پورت
            self.set_progress(0.2, "Testing ports...")
            self.log("🔌 Testing ports...")
            best_port = ChainOptimizer.find_best_port(self.app)   # پاس دادن client_ui
            self.log(f"  ✅ Port: {best_port}")

            # 3. انتخاب بهترین کانفیگ
            self.set_progress(0.3, "Selecting best config...")
            self.log("📁 Selecting best config...")
            self.best_config = ChainOptimizer.select_best_config(self.app)
            if self.best_config:
                self.log(f"  ✅ Config: {os.path.basename(self.best_config)}")
            else:
                self.log("  ⚠️ No config found. Please import a config first.")
                self._finish_chain(False)
                return

            # 4. انتخاب Fragment و Fingerprint
            self.set_progress(0.4, "Optimizing DPI bypass...")
            self.log("🧩 Optimizing fragment & fingerprint...")
            self.best_fragment, self.best_fingerprint = ChainOptimizer.get_isp_fragment_and_fingerprint()
            self.log(f"  ✅ Fragment: {self.best_fragment}")
            self.log(f"  ✅ Fingerprint: {self.best_fingerprint}")

            # 5. انتخاب Pre‑VPN (در صورت وجود)
            self.set_progress(0.5, "Selecting Pre‑VPN...")
            pre_vpn_configs = self.app._get_pre_vpn_configs()
            if pre_vpn_configs:
                self.selected_pre_vpn_path = os.path.join(DIRS["configs"], pre_vpn_configs[0])
                self.log(f"  ✅ Pre‑VPN: {pre_vpn_configs[0]}")
            else:
                self.selected_pre_vpn_path = None
                self.log("  ⚠️ No Pre‑VPN config available (chain will work without middle layer)")

            # 6. فعال‌سازی Traffic Mimicry
            self.set_progress(0.6, "Enabling Traffic Mimicry...")
            profile_name = self.app.mimicry_profile_combo.get()
            if profile_name and self.mimicry_manager.set_active_profile(profile_name):
                if not self.mimicry_manager.start():
                    self.log("  ❌ Failed to start Mimicry proxy.")
                    self._finish_chain(False)
                    return
                self.log(f"  ✅ Mimicry started with profile: {profile_name}")
            else:
                self.log("  ⚠️ Mimicry disabled (no profile selected)")

            # 7. اعمال تنظیمات DPI
            self.set_progress(0.7, "Applying DPI bypass...")
            self.app.dpi_settings["fragment"] = True
            self.app.dpi_settings["frag_packets"] = self.best_fragment["packets"]
            self.app.dpi_settings["frag_length"] = self.best_fragment["length"]
            self.app.dpi_settings["frag_interval"] = self.best_fragment["interval"]
            if self.best_fingerprint:
                self.app.dpi_settings["fingerprint"] = self.best_fingerprint

            # 8. اعمال DNS
            self.set_progress(0.8, "Setting DNS...")
            dns_frame = getattr(self.app.master, 'dns_frame', None)
            if dns_frame and self.best_dns:
                dns_data = {"name": "Smart DNS", "primary": self.best_dns, "secondary": "", "type": "IPv4"}
                dns_frame.current_dns_info = dns_data
                dns_frame.connect_dns()

            # 9. شروع زنجیره
            self.set_progress(0.9, "Starting chain...")
            self.log("⚡ Initiating 3‑layer chain...")
            self.app.config_manager.select_config(self.best_config, None)

            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            success = self.core.start_connection(
                self.best_config,
                self.app.var_tun,
                root_dir,
                DIRS["configs"],
                mimicry_manager=self.mimicry_manager,
                pre_vpn_config_path=self.selected_pre_vpn_path
            )

            if success:
                self.log("✅ Chain connected successfully!")
                self._finish_chain(True)
            else:
                self.log("❌ Chain connection failed.")
                self._finish_chain(False)

        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self._finish_chain(False)

    def _finish_chain(self, success):
        self.chain_active = success
        if success:
            self.btn_connect.configure(state="normal", text="⏹ DISCONNECT CHAIN",
                                      fg_color="#C62828", hover_color="#8E0000")
        else:
            self.btn_connect.configure(state="normal", text="⚡ START CHAIN")
        self.set_progress(1.0 if success else 0.0)

    def disconnect_chain(self):
        self.core.stop_connection()
        self.chain_active = False
        self.btn_connect.configure(state="normal", text="⚡ START CHAIN")
        self.lbl_status.configure(text="Status: Disconnected", text_color="#EF5350")
        self.lbl_traffic.configure(text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s")
        self.log("Chain disconnected.")

    def check_ip(self):
        self.btn_check_ip.configure(state="disabled", text="⏳")
        threading.Thread(target=self._check_ip_thread, daemon=True).start()

    def _check_ip_thread(self):
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5).json()
            ip = resp.get("query", "Unknown")
            cc = resp.get("countryCode", "UN")
            flag = ''.join(chr(ord(c.upper()) + 127397) for c in cc)
            self.after(0, lambda: self.lbl_ip.configure(text=f"{flag} {ip}"))
        except:
            self.after(0, lambda: self.lbl_ip.configure(text="❌ Failed"))
        finally:
            self.after(0, lambda: self.btn_check_ip.configure(state="normal", text="🌍 Check IP"))

    def update_chain_status(self, status_text, color):
        if self.chain_active:
            self.lbl_status.configure(text=status_text, text_color=color)

    def update_chain_traffic(self, dl, ul):
        if self.chain_active:
            self.lbl_traffic.configure(text=f"⬇️ {dl}   |   ⬆️ {ul}")
