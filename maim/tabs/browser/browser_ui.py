# tabs/browser/browser_ui.py
import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import re
import urllib.parse
import shutil
import random
import platform
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK
from .browser_utils import BrowserUtils
from .browser_core import TorController

class BrowserUI(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # تنظیمات
        self.current_ua = BrowserUtils.get_current_platform_ua()
        self.custom_ua = None
        self.use_proxy = False
        self.proxy_server = None   # مثلاً "127.0.0.1:9050"
        self.proxy_type = "socks5"  # یا http
        self.adblock_enabled = True
        self.tor_mode = False
        self.tor_controller = TorController(log_callback=self.log_tor_status)
        self.browser_path = self._find_browser()

        self.setup_ui()

        # ★ پشتیبانی از پلاگین‌های دسته "browser"
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("browser")

    def _find_browser(self):
        """پیدا کردن مسیر مرورگر کروم یا اج"""
        possible_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        # اگر پیدا نشد، دستور chrome را در PATH جستجو کن
        chrome_path = shutil.which("chrome") or shutil.which("msedge")
        if chrome_path:
            return chrome_path
        messagebox.showerror("Browser Not Found", "Google Chrome or Microsoft Edge is required.")
        return None

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🌐 Secure Browser (Chrome/Edge)", 
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        # نوار آدرس و دکمه
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        nav_frame.grid_columnconfigure(3, weight=1)

        self.url_entry = ctk.CTkEntry(nav_frame, placeholder_text="Enter URL or search...")
        self.url_entry.grid(row=0, column=3, sticky="ew", padx=5)
        self.url_entry.bind("<Return>", lambda e: self.open_browser())

        self.btn_go = ctk.CTkButton(nav_frame, text="Open Browser", width=120, fg_color=CF_ORANGE, text_color="black",
                                    command=self.open_browser)
        self.btn_go.grid(row=0, column=4, padx=2)

        # تب‌ها
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE,
                                      segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.tab_privacy = self.tabview.add("🛡️ Privacy")
        self.tab_network = self.tabview.add("🌐 Network")
        self.tab_other = self.tabview.add("⚙️ Other")

        self.setup_privacy_tab()
        self.setup_network_tab()
        self.setup_other_tab()

    def setup_privacy_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_privacy, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # 1. User-Agent Changer
        ua_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ua_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(ua_frame, text="🔄 User-Agent Changer", font=ctk.CTkFont(size=16, weight="bold"), 
                     text_color=CF_ORANGE).pack(pady=(15,5))
        ctk.CTkLabel(ua_frame, text="Change browser identity (restart browser)", text_color="gray").pack()
        self.ua_var = ctk.StringVar(value="Default (Platform)")
        ua_menu = ctk.CTkOptionMenu(ua_frame, values=["Default (Platform)"] + list(BrowserUtils.USER_AGENTS.keys()),
                                    variable=self.ua_var, command=self.change_user_agent)
        ua_menu.pack(pady=10)

        # 2. Fingerprint Randomizer (via Chrome flags)
        fp_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        fp_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(fp_frame, text="🎭 Fingerprint Randomizer", font=ctk.CTkFont(size=16, weight="bold"), 
                     text_color="#29B6F6").pack(pady=(15,5))
        ctk.CTkLabel(fp_frame, text="Add flags to reduce fingerprinting (WebRTC, Canvas, etc.)", text_color="gray").pack()
        self.fp_var = ctk.BooleanVar(value=True)
        self.fp_switch = ctk.CTkSwitch(fp_frame, text="Enable Anti-Fingerprinting Flags", 
                                       variable=self.fp_var, progress_color=CF_ORANGE)
        self.fp_switch.pack(pady=10)
        self.fp_status = ctk.CTkLabel(fp_frame, text="", text_color="gray")
        self.fp_status.pack(pady=(0,10))

        # 3. Ad Blocking (via hosts file - simple)
        ad_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ad_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(ad_frame, text="🚫 Ad Blocking", font=ctk.CTkFont(size=16, weight="bold"), 
                     text_color="#EF5350").pack(pady=(15,5))
        ctk.CTkLabel(ad_frame, text="Block known ad servers via system hosts file", text_color="gray").pack()
        self.ad_var = ctk.BooleanVar(value=False)
        self.ad_switch = ctk.CTkSwitch(ad_frame, text="Enable Ad Block (requires admin)", 
                                       variable=self.ad_var, command=self.toggle_adblock,
                                       progress_color=CF_ORANGE)
        self.ad_switch.pack(pady=10)

    def setup_network_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_network, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # 4. Proxy / Tor Mode
        proxy_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        proxy_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(proxy_frame, text="🧅 Proxy & Tor Mode", font=ctk.CTkFont(size=16, weight="bold"), 
                     text_color="#AB47BC").pack(pady=(15,5))
        ctk.CTkLabel(proxy_frame, text="Route browser through a proxy or Tor network", text_color="gray").pack()

        # Proxy type
        proxy_type_frame = ctk.CTkFrame(proxy_frame, fg_color="transparent")
        proxy_type_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(proxy_type_frame, text="Proxy Type:", width=80).pack(side="left")
        self.proxy_type_var = ctk.StringVar(value="SOCKS5")
        proxy_type_menu = ctk.CTkComboBox(proxy_type_frame, values=["SOCKS5", "HTTP"], width=100, variable=self.proxy_type_var)
        proxy_type_menu.pack(side="left", padx=10)

        # Proxy server
        proxy_server_frame = ctk.CTkFrame(proxy_frame, fg_color="transparent")
        proxy_server_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(proxy_server_frame, text="Server:Port:", width=80).pack(side="left")
        self.proxy_entry = ctk.CTkEntry(proxy_server_frame, width=200, placeholder_text="127.0.0.1:9050")
        self.proxy_entry.pack(side="left", padx=10)
        self.proxy_entry.insert(0, "127.0.0.1:9050")

        self.proxy_var = ctk.BooleanVar(value=False)
        self.proxy_switch = ctk.CTkSwitch(proxy_frame, text="Enable Proxy", variable=self.proxy_var,
                                          command=self.toggle_proxy, progress_color=CF_ORANGE)
        self.proxy_switch.pack(pady=10)

        # Tor Mode (استفاده از تور داخلی)
        self.tor_var = ctk.BooleanVar(value=False)
        self.tor_switch = ctk.CTkSwitch(proxy_frame, text="Enable Tor Mode (auto proxy)", variable=self.tor_var,
                                        command=self.toggle_tor_mode, progress_color=CF_ORANGE)
        self.tor_switch.pack(pady=10)
        self.tor_status = ctk.CTkLabel(proxy_frame, text="", text_color="gray")
        self.tor_status.pack(pady=5)

    def setup_other_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_other, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # 5. Smart Routing / Extra flags
        extra_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        extra_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(extra_frame, text="🧠 Smart Routing & Extra Flags", font=ctk.CTkFont(size=16, weight="bold"), 
                     text_color="#29B6F6").pack(pady=(15,5))
        ctk.CTkLabel(extra_frame, text="Add custom command-line arguments to browser", text_color="gray").pack()
        self.extra_flags = ctk.CTkTextbox(extra_frame, height=80, font=ctk.CTkFont(size=11))
        self.extra_flags.pack(fill="x", padx=20, pady=10)
        self.extra_flags.insert("1.0", "--disable-blink-features=AutomationControlled\n--disable-features=IsolateOrigins,site-per-process")

        ctk.CTkButton(extra_frame, text="Apply & Launch", fg_color=CF_ORANGE, text_color="black",
                      command=self.open_browser).pack(pady=10)

    # ========== Logic ==========
    def change_user_agent(self, choice):
        if choice == "Default (Platform)":
            self.custom_ua = None
            self.current_ua = BrowserUtils.get_current_platform_ua()
        else:
            self.custom_ua = BrowserUtils.USER_AGENTS.get(choice)
            self.current_ua = self.custom_ua
        messagebox.showinfo("User-Agent", f"User-Agent set to:\n{self.current_ua[:80]}...\nWill apply on next launch.")

    def toggle_adblock(self):
        self.adblock_enabled = self.ad_var.get()
        if self.adblock_enabled:
            # درخواست ادمین برای ویرایش hosts
            try:
                import ctypes
                if ctypes.windll.shell32.IsUserAnAdmin():
                    self._update_hosts_file(True)
                else:
                    messagebox.showwarning("Admin Required", "Ad block requires administrator privileges.\nPlease run the app as admin.")
                    self.ad_var.set(False)
            except:
                self.ad_var.set(False)
        else:
            self._update_hosts_file(False)

    def _update_hosts_file(self, enable):
        """ساده: اضافه کردن چند دامنه تبلیغاتی به hosts (نیازمند ادمین)"""
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        ad_domains = [
            "0.0.0.0 doubleclick.net",
            "0.0.0.0 googleadservices.com",
            "0.0.0.0 googlesyndication.com",
            "0.0.0.0 google-analytics.com",
            "0.0.0.0 facebook.com/tr",
        ]
        try:
            with open(hosts_path, "r+") as f:
                content = f.read()
                if enable:
                    # اضافه کردن خطوط
                    for line in ad_domains:
                        if line not in content:
                            f.write("\n" + line)
                else:
                    # حذف خطوط
                    new_content = content
                    for line in ad_domains:
                        new_content = new_content.replace(line, "")
                    f.seek(0)
                    f.write(new_content)
                    f.truncate()
            messagebox.showinfo("Ad Block", "Ad block settings applied. You may need to flush DNS (ipconfig /flushdns).")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to modify hosts file: {e}")

    def toggle_proxy(self):
        if self.proxy_var.get():
            self.use_proxy = True
            proxy_text = self.proxy_entry.get().strip()
            if ":" not in proxy_text:
                messagebox.showerror("Error", "Invalid proxy format. Use host:port")
                self.proxy_var.set(False)
                self.use_proxy = False
                return
            self.proxy_server = proxy_text
            self.proxy_type = self.proxy_type_var.get().lower()
        else:
            self.use_proxy = False
            self.proxy_server = None

    def toggle_tor_mode(self):
        if self.tor_var.get():
            # غیرفعال کردن proxy دستی در صورت فعال بودن
            if self.proxy_var.get():
                self.proxy_var.set(False)
                self.use_proxy = False
            self.tor_status.configure(text="Starting Tor...", text_color=CF_ORANGE)
            if self.tor_controller.start_tor():
                self.tor_mode = True
                self.use_proxy = True
                self.proxy_server = "127.0.0.1:9050"
                self.proxy_type = "socks5"
                self.tor_status.configure(text="✅ Tor running on port 9050", text_color="#66BB6A")
                messagebox.showinfo("Tor Mode", "Tor enabled. Proxy set to 127.0.0.1:9050")
            else:
                self.tor_var.set(False)
                self.tor_mode = False
                self.tor_status.configure(text="❌ Tor failed. Install Tor Browser.", text_color="#EF5350")
        else:
            self.tor_controller.stop_tor()
            self.tor_mode = False
            self.tor_status.configure(text="Tor disabled", text_color="gray")
            if not self.proxy_var.get():
                self.use_proxy = False

    def open_browser(self):
        if not self.browser_path:
            messagebox.showerror("Error", "No browser found. Install Chrome or Edge.")
            return

        # ساخت URL از ورودی
        query = self.url_entry.get().strip()
        if not query:
            query = "https://www.google.com"
        else:
            domain_pattern = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$')
            if domain_pattern.match(query) or query.startswith(('http://', 'https://')):
                if not query.startswith(('http://', 'https://')):
                    query = 'https://' + query
                url = query
            else:
                encoded = urllib.parse.quote(query)
                url = f'https://www.google.com/search?q={encoded}'

        # ساخت آرگومان‌های خط فرمان
        args = [self.browser_path, url]

        # User-Agent
        if self.custom_ua:
            args.append(f'--user-agent="{self.custom_ua}"')

        # Proxy
        if self.use_proxy and self.proxy_server:
            if self.proxy_type == "socks5":
                args.append(f'--proxy-server="socks5://{self.proxy_server}"')
            else:
                args.append(f'--proxy-server="http://{self.proxy_server}"')

        # Anti-fingerprinting flags
        if self.fp_var.get():
            flags = [
                "--disable-webrtc",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-canvas-tainting",
                "--disable-remote-fonts",
                "--disable-reading-from-canvas",
                "--disable-3d-apis",
                "--disable-accelerated-2d-canvas",
                "--disable-webgl",
                "--disable-gpu",
            ]
            args.extend(flags)

        # اضافه کردن فلگ‌های سفارشی از textbox
        extra = self.extra_flags.get("1.0", "end-1c").strip()
        if extra:
            for flag in extra.splitlines():
                if flag.strip():
                    args.append(flag.strip())

        # اجرا
        try:
            subprocess.Popen(args, shell=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch browser:\n{e}")

    def log_tor_status(self, msg):
        self.after(0, lambda: self.tor_status.configure(text=msg, text_color=CF_ORANGE))

    # ★ متد بارگذاری پلاگین‌ها
    def load_category_plugins(self, category: str):
        """تب‌های جدید برای پلاگین‌های فعال با دستهٔ مشخص شده اضافه می‌کند."""
        app = self.master
        if not hasattr(app, "plugin_manager"):
            return

        pm = app.plugin_manager
        for p in pm.get_plugins_by_category(category):
            plugin_id = p["id"]
            manifest = p["manifest"]
            tab_name = manifest.get("name", plugin_id)[:25]

            try:
                new_tab = self.tabview.add(tab_name)
            except Exception:
                new_tab = self.tabview.add(f"{tab_name}_{random.randint(0, 999)}")

            instance = pm.get_plugin_instance(plugin_id)
            if instance:
                panel = instance.get_ui_panel(new_tab)
                if panel:
                    panel.pack(fill="both", expand=True, padx=10, pady=10)
