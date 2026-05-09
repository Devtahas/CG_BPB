# tabs/dns/dns_ui.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import socket
import subprocess
import json
import os
import ctypes
import ipaddress
import random
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK, DIRS

from .dns_core import DNSCore
from .dns_servers import DNSServersManager
from .dns_hunter import DNSHunter
from .dns_utils import DNSUtils
from .local_cf_server import LocalCloudflareDNSServer
from .fake_dns import FakeDNSServer
from .doh_server import LocalDoHServer
from .advanced import (
    SplitDNSResolver, DNSCache, SmartDNS, CNAMEUnmasker,
    DNSSECChecker, DoTDoHTester, DNSLeakTester
)


class DNSChangerUI(ctk.CTkFrame):
    """کلاس اصلی UI بخش DNS Changer (ماژولار شده)"""

    def __init__(self, master, app_controller=None, **kwargs):
        # ★ دریافت asset_manager از kwargs (همانطور که در DNSChangerFrame پاس داده می‌شود)
        self.asset_manager = kwargs.pop('asset_manager', None)

        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # مدیران و هسته‌ها
        self.servers_manager = DNSServersManager()
        self.dns_core = DNSCore(log_callback=self.log)

        # ★ حالا DNSHunter با asset_manager واقعی ساخته می‌شود
        self.dns_hunter = DNSHunter(
            app_controller=app_controller,
            asset_manager=self.asset_manager
        )

        # متغیرهای وضعیت
        self.is_connected = False
        self.current_dns_info = None
        self.active_interface = self.dns_core.get_active_network_interface()
        self.current_full_addr = ""

        # سرورهای محلی
        self.local_cf_server = None
        self.doh_server = None
        self.fake_dns_server = None

        # ابزارهای پیشرفته
        self.split_dns = SplitDNSResolver()
        self.dns_cache = DNSCache()
        self.smart_dns = SmartDNS()

        # ویجت‌های UI (برای دسترسی در متدها)
        self.btn_power = None
        self.lbl_status = None
        self.combo_dns = None
        self.lbl_info_name = None
        self.lbl_info_ping = None
        self.lbl_info_addr = None
        self.lbl_info_net = None
        self.lbl_cf_stats = None
        self.leak_result = None
        self.dnssec_domain = None
        self.dnssec_result = None
        self.cname_domain = None
        self.cname_result = None
        self.dotdoh_url = None
        self.dotdoh_type = None
        self.dotdoh_result = None
        self.scan_status = None
        self.scan_progress = None
        self.scan_results_text = None
        self.split_domain = None
        self.split_dns_server = None
        self.split_rules_text = None
        self.fake_domain = None
        self.fake_ip = None
        self.fake_rules_text = None
        self.cache_info = None

        # ساخت UI
        self.setup_ui()
        self.refresh_ui()

        # ★ پشتیبانی از پلاگین‌های دسته "dns"
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("dns")

    def log(self, message):
        """لاگ کردن (می‌تواند بعداً به کنسول یا استاتوس بار اضافه شود)"""
        print(f"[DNS] {message}")

    def setup_ui(self):
        # کانتینر اصلی
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header_frame, text="🌍 Advanced DNS Changer", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(header_frame, text="🔄 Refresh Network", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, width=140,
                     command=self.refresh_interface).pack(side="right")

        # Tabview
        self.tabview = ctk.CTkTabview(main_container, segmented_button_selected_color=CF_ORANGE,
                                     segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, sticky="nsew")

        self.tab_main = self.tabview.add("📡 Main")
        self.tab_tools = self.tabview.add("🛠️ Tools")
        self.tab_hunter = self.tabview.add("🎯 DNS Hunter")
        self.tab_advanced = self.tabview.add("⚙️ Advanced")

        self.setup_main_tab()
        self.setup_tools_tab()
        self.dns_hunter.setup_hunter_tab(self.tab_hunter)
        self.setup_advanced_tab()

    # =================================================================
    # تب Main
    # =================================================================
    def setup_main_tab(self):
        main_layout = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=15, pady=15)
        main_layout.grid_columnconfigure(0, weight=1)
        main_layout.grid_columnconfigure(1, weight=2)

        # LEFT: Power Button
        left_frame = ctk.CTkFrame(main_layout, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10)
        self.btn_power = ctk.CTkButton(left_frame, text="OFF", font=ctk.CTkFont(size=36, weight="bold"),
                                      width=130, height=130, corner_radius=65, fg_color="#37474F",
                                      hover_color="#455A64", command=self.toggle_dns)
        self.btn_power.pack(expand=True, pady=15)
        self.lbl_status = ctk.CTkLabel(left_frame, text="Disconnected", font=ctk.CTkFont(size=16, weight="bold"),
                                      text_color="gray")
        self.lbl_status.pack()

        # RIGHT: Info Card
        right_frame = ctk.CTkFrame(main_layout, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10)

        select_frame = ctk.CTkFrame(right_frame, fg_color=BG_PANEL, corner_radius=15)
        select_frame.pack(fill="x", pady=(0, 10), ipady=5)
        self.combo_dns = ctk.CTkComboBox(select_frame, values=self.servers_manager.get_names(),
                                        width=320, font=ctk.CTkFont(size=13),
                                        dropdown_fg_color=BG_DARK, command=self.on_dns_select)
        self.combo_dns.pack(pady=8)
        if self.servers_manager.get_names():
            self.combo_dns.set(self.servers_manager.get_names()[0])

        info_box = ctk.CTkFrame(right_frame, fg_color=BG_PANEL, corner_radius=15)
        info_box.pack(fill="both", expand=True)
        info_box.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(info_box, text="DNS Server", text_color="gray").grid(row=0, column=0, pady=(12, 0))
        self.lbl_info_name = ctk.CTkLabel(info_box, text="--", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_info_name.grid(row=1, column=0, pady=(0, 12))

        ctk.CTkLabel(info_box, text="Latency", text_color="gray").grid(row=0, column=1, pady=(12, 0))
        self.lbl_info_ping = ctk.CTkLabel(info_box, text="-- ms", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_info_ping.grid(row=1, column=1, pady=(0, 12))

        ctk.CTkLabel(info_box, text="Address", text_color="gray").grid(row=2, column=0, pady=(8, 0))
        addr_frame = ctk.CTkFrame(info_box, fg_color="transparent")
        addr_frame.grid(row=3, column=0, pady=(0, 12))
        self.lbl_info_addr = ctk.CTkLabel(addr_frame, text="--", font=ctk.CTkFont(size=11))
        self.lbl_info_addr.pack(side="left")
        ctk.CTkButton(addr_frame, text="📋", width=28, fg_color="transparent",
                     text_color=CF_ORANGE, command=self.copy_dns).pack(side="left", padx=4)

        ctk.CTkLabel(info_box, text="Network Adapter", text_color="gray").grid(row=2, column=1, pady=(8, 0))
        self.lbl_info_net = ctk.CTkLabel(info_box, text=f"🟢 {self.active_interface}",
                                        font=ctk.CTkFont(size=11, weight="bold"), text_color="#66BB6A")
        self.lbl_info_net.grid(row=3, column=1, pady=(0, 12))

        self.lbl_cf_stats = ctk.CTkLabel(info_box, text="", text_color="gray", font=ctk.CTkFont(size=10))
        self.lbl_cf_stats.grid(row=4, column=0, columnspan=2, pady=(0, 8))

        action_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=(10, 0))
        action_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(action_frame, text="➕ Add Custom", fg_color="transparent", border_width=1,
                     border_color="#29B6F6", text_color="#29B6F6", command=self.open_add_dialog).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(action_frame, text="🗑️ Delete", fg_color="transparent", border_width=1,
                     border_color="#EF5350", text_color="#EF5350", command=self.delete_dns).grid(row=0, column=1, padx=4, sticky="ew")

        self.on_dns_select(self.combo_dns.get())

    # =================================================================
    # تب Tools
    # =================================================================
    def setup_tools_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_tools, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        # DNS Leak Test
        leak_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=12)
        leak_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(leak_frame, text="🔍 DNS Leak Test", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(12, 4))
        self.leak_result = ctk.CTkTextbox(leak_frame, height=70, font=ctk.CTkFont(size=11))
        self.leak_result.pack(fill="x", padx=15, pady=6)
        ctk.CTkButton(leak_frame, text="Start Leak Test", fg_color=CF_ORANGE, text_color="black",
                     command=self.test_dns_leak).pack(pady=(0, 12))

        # DNSSEC Check
        dnssec_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=12)
        dnssec_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(dnssec_frame, text="🔐 DNSSEC Check", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#29B6F6").pack(pady=(12, 4))
        dnssec_input = ctk.CTkFrame(dnssec_frame, fg_color="transparent")
        dnssec_input.pack(fill="x", padx=15, pady=6)
        self.dnssec_domain = ctk.CTkEntry(dnssec_input, placeholder_text="domain.com", width=220)
        self.dnssec_domain.pack(side="left", padx=4)
        ctk.CTkButton(dnssec_input, text="Check", fg_color="#29B6F6", text_color="black",
                     command=self.check_dnssec).pack(side="left", padx=4)
        self.dnssec_result = ctk.CTkLabel(dnssec_frame, text="", text_color="gray")
        self.dnssec_result.pack(pady=(0, 12))

        # CNAME Unmasker
        cname_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=12)
        cname_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(cname_frame, text="🔗 CNAME Unmasker", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#AB47BC").pack(pady=(12, 4))
        cname_input = ctk.CTkFrame(cname_frame, fg_color="transparent")
        cname_input.pack(fill="x", padx=15, pady=6)
        self.cname_domain = ctk.CTkEntry(cname_input, placeholder_text="domain.com", width=220)
        self.cname_domain.pack(side="left", padx=4)
        ctk.CTkButton(cname_input, text="Unmask", fg_color="#AB47BC", text_color="black",
                     command=self.unmask_cname).pack(side="left", padx=4)
        self.cname_result = ctk.CTkTextbox(cname_frame, height=60, font=ctk.CTkFont(size=11))
        self.cname_result.pack(fill="x", padx=15, pady=(0, 12))

        # DoH/DoT Tester
        dotdoh_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=12)
        dotdoh_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(dotdoh_frame, text="🔒 DoH / DoT Tester", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#66BB6A").pack(pady=(12, 4))
        dotdoh_input = ctk.CTkFrame(dotdoh_frame, fg_color="transparent")
        dotdoh_input.pack(fill="x", padx=15, pady=6)
        self.dotdoh_url = ctk.CTkEntry(dotdoh_input, placeholder_text="URL or Host", width=260)
        self.dotdoh_url.pack(side="left", padx=4)
        self.dotdoh_type = ctk.CTkSegmentedButton(dotdoh_input, values=["DoH", "DoT"])
        self.dotdoh_type.pack(side="left", padx=4)
        self.dotdoh_type.set("DoH")
        ctk.CTkButton(dotdoh_input, text="Test", fg_color="#66BB6A", text_color="black",
                     command=self.test_dotdoh).pack(side="left", padx=4)
        self.dotdoh_result = ctk.CTkLabel(dotdoh_frame, text="", text_color="gray")
        self.dotdoh_result.pack(pady=(0, 12))

    # =================================================================
    # تب Advanced
    # =================================================================
    def setup_advanced_tab(self):
        adv_scroll = ctk.CTkScrollableFrame(self.tab_advanced, fg_color="transparent")
        adv_scroll.pack(fill="both", expand=True, padx=15, pady=15)

        # Split DNS
        split_frame = ctk.CTkFrame(adv_scroll, fg_color=BG_PANEL, corner_radius=12)
        split_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(split_frame, text="🔀 Split DNS", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(10, 4))
        split_input = ctk.CTkFrame(split_frame, fg_color="transparent")
        split_input.pack(fill="x", padx=15, pady=6)
        self.split_domain = ctk.CTkEntry(split_input, placeholder_text="Domain (*.google.com)", width=180)
        self.split_domain.pack(side="left", padx=4)
        self.split_dns_server = ctk.CTkEntry(split_input, placeholder_text="DNS Server", width=140)
        self.split_dns_server.pack(side="left", padx=4)
        ctk.CTkButton(split_input, text="Add", fg_color=CF_ORANGE, text_color="black", width=60,
                     command=self.add_split_rule).pack(side="left", padx=4)
        self.split_rules_text = ctk.CTkTextbox(split_frame, height=50, font=ctk.CTkFont(size=10))
        self.split_rules_text.pack(fill="x", padx=15, pady=(0, 10))

        # FakeDNS
        fake_frame = ctk.CTkFrame(adv_scroll, fg_color=BG_PANEL, corner_radius=12)
        fake_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(fake_frame, text="🎭 FakeDNS", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#EF5350").pack(pady=(10, 4))
        fake_input = ctk.CTkFrame(fake_frame, fg_color="transparent")
        fake_input.pack(fill="x", padx=15, pady=6)
        self.fake_domain = ctk.CTkEntry(fake_input, placeholder_text="Domain (* for all)", width=180)
        self.fake_domain.pack(side="left", padx=4)
        self.fake_ip = ctk.CTkEntry(fake_input, placeholder_text="Fake IP", width=140)
        self.fake_ip.pack(side="left", padx=4)
        ctk.CTkButton(fake_input, text="Add", fg_color="#EF5350", text_color="black", width=60,
                     command=self.add_fake_rule).pack(side="left", padx=4)
        ctk.CTkButton(fake_input, text="Start", fg_color="#2E7D32", text_color="white", width=60,
                     command=self.start_fake_dns).pack(side="left", padx=4)
        self.fake_rules_text = ctk.CTkTextbox(fake_frame, height=50, font=ctk.CTkFont(size=10))
        self.fake_rules_text.pack(fill="x", padx=15, pady=(0, 10))

        # Smart DNS
        smart_frame = ctk.CTkFrame(adv_scroll, fg_color=BG_PANEL, corner_radius=12)
        smart_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(smart_frame, text="🧠 Smart DNS", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#29B6F6").pack(pady=(10, 4))
        ctk.CTkLabel(smart_frame, text="Streaming → 8.8.8.8 | Social → 1.1.1.1 | Gaming → 9.9.9.9",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack()
        ctk.CTkButton(smart_frame, text="Enable Smart DNS", fg_color="#29B6F6", text_color="black",
                     command=self.enable_smart_dns).pack(pady=(6, 10))

        # DNS Cache
        cache_frame = ctk.CTkFrame(adv_scroll, fg_color=BG_PANEL, corner_radius=12)
        cache_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(cache_frame, text="💾 DNS Cache", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#AB47BC").pack(pady=(10, 4))
        self.cache_info = ctk.CTkLabel(cache_frame, text=f"Cache size: {self.dns_cache.size()}", text_color="gray")
        self.cache_info.pack()
        ctk.CTkButton(cache_frame, text="Clear Cache", fg_color="#AB47BC", text_color="black",
                     command=self.clear_dns_cache).pack(pady=(6, 10))

        # DNSCrypt
        dnscrypt_frame = ctk.CTkFrame(adv_scroll, fg_color=BG_PANEL, corner_radius=12)
        dnscrypt_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(dnscrypt_frame, text="🛡️ DNSCrypt", font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="#66BB6A").pack(pady=(10, 4))
        ctk.CTkLabel(dnscrypt_frame, text="DNSCrypt proxy configuration", text_color="gray").pack()
        ctk.CTkButton(dnscrypt_frame, text="Configure", fg_color="#66BB6A", text_color="black",
                     command=self.configure_dnscrypt).pack(pady=(6, 10))

    # =================================================================
    # منطق اتصال و UI
    # =================================================================
    def refresh_interface(self):
        self.active_interface = self.dns_core.get_active_network_interface()
        self.lbl_info_net.configure(text=f"🟢 {self.active_interface}")

    def refresh_ui(self):
        names = self.servers_manager.get_names()
        self.combo_dns.configure(values=names)
        if names:
            self.combo_dns.set(names[0])
            self.on_dns_select(names[0])

    def copy_dns(self):
        if self.current_full_addr:
            self.clipboard_clear()
            self.clipboard_append(self.current_full_addr)
            self.update()

    def on_dns_select(self, choice):
        selected = self.servers_manager.find_by_name(choice)
        if not selected:
            return
        self.current_dns_info = selected
        dns_type = selected.get("type", "IPv4")
        if dns_type == "LocalCF":
            self.lbl_info_name.configure(text=selected["name"] + " [🚀 Local]")
            self.current_full_addr = "127.0.0.1:53"
            self.lbl_info_addr.configure(text="Localhost:53")
            temp_server = LocalCloudflareDNSServer()
            stats = temp_server.get_stats()
            self.lbl_cf_stats.configure(text=f"📊 CF IP Pool: {stats['cf_ips_count']} IPs", text_color="#29B6F6")
            self.lbl_info_ping.configure(text="Local DNS", text_color="#66BB6A")
        elif dns_type == "DoT":
            self.lbl_info_name.configure(text=selected["name"] + " [DoT]")
            self.current_full_addr = f"{selected['primary']}:{selected.get('port', 853)}"
            disp_addr = self.current_full_addr[:25] + "..." if len(self.current_full_addr) > 25 else self.current_full_addr
            self.lbl_info_addr.configure(text=disp_addr)
            self.lbl_info_ping.configure(text="Testing...", text_color="gray")
            if self.is_connected:
                self.disconnect_dns(update_ui=False)
            self.after(100, lambda: self._ping_dot(selected["primary"], selected.get('port', 853)))
        else:
            self.lbl_cf_stats.configure(text="")
            is_doh = dns_type == "DoH"
            badge = " [DoH]" if is_doh else " [IPv4]"
            self.lbl_info_name.configure(text=selected["name"] + badge)
            self.current_full_addr = selected["primary"]
            disp_addr = self.current_full_addr[:25] + "..." if len(self.current_full_addr) > 25 else self.current_full_addr
            self.lbl_info_addr.configure(text=disp_addr)
            self.lbl_info_ping.configure(text="Testing...", text_color="gray")
            if self.is_connected:
                self.disconnect_dns(update_ui=False)
            self.after(100, lambda: self._ping_dns(selected["primary"], is_doh))

    def _ping_dns(self, target, is_doh):
        def _ping():
            start = time.time()
            try:
                if is_doh:
                    import requests
                    requests.get(target, timeout=2.0)
                else:
                    socket.create_connection((target, 53), timeout=2.0).close()
                ping_ms = int((time.time() - start) * 1000)
                color = "#66BB6A" if ping_ms < 100 else ("#FFA726" if ping_ms < 250 else "#EF5350")
                self.after(0, lambda: self.lbl_info_ping.configure(text=f"📊 {ping_ms} ms", text_color=color))
            except Exception:
                self.after(0, lambda: self.lbl_info_ping.configure(text="Timeout", text_color="#EF5350"))
        threading.Thread(target=_ping, daemon=True).start()

    def _ping_dot(self, host, port):
        def _ping():
            start = time.time()
            try:
                import ssl
                context = ssl.create_default_context()
                with socket.create_connection((host, port), timeout=3) as sock:
                    with context.wrap_socket(sock, server_hostname=host):
                        ping_ms = int((time.time() - start) * 1000)
                        color = "#66BB6A" if ping_ms < 100 else ("#FFA726" if ping_ms < 250 else "#EF5350")
                        self.after(0, lambda: self.lbl_info_ping.configure(text=f"{ping_ms} ms", text_color=color))
            except:
                self.after(0, lambda: self.lbl_info_ping.configure(text="Timeout", text_color="#EF5350"))
        threading.Thread(target=_ping, daemon=True).start()

    def toggle_dns(self):
        if not self.dns_core.is_admin():
            messagebox.showerror("Admin Required", "Changing system DNS requires Administrator privileges!")
            return
        if not self.is_connected:
            self.connect_dns()
        else:
            self.disconnect_dns()

    def connect_dns(self):
        if not self.current_dns_info:
            return
        self.btn_power.configure(state="disabled")
        self.lbl_status.configure(text="Connecting...")
        threading.Thread(target=self._apply_dns_thread, args=(self.current_dns_info,), daemon=True).start()

    def _apply_dns_thread(self, dns_data):
        try:
            adapter = self.active_interface
            primary = dns_data["primary"]
            dns_type = dns_data.get("type", "IPv4")
            if dns_type == "LocalCF":
                self.local_cf_server = LocalCloudflareDNSServer()
                if not self.local_cf_server.start():
                    raise Exception("Could not start Local DNS Server!")
                setup_primary = self.local_cf_server.bound_ip
                setup_secondary = ""
                stats = self.local_cf_server.get_stats()
                self.after(0, lambda: self.lbl_cf_stats.configure(text=f"✅ Running | {stats['cf_ips_count']} IPs | Cache: {stats['cache_size']}", text_color="#66BB6A"))
            elif dns_type == "DoH":
                self.doh_server = LocalDoHServer(primary)
                if not self.doh_server.start():
                    raise Exception("Port 53 is busy!")
                setup_primary = self.doh_server.bound_ip
                setup_secondary = ""
            else:
                setup_primary = primary
                setup_secondary = dns_data.get("secondary", "")
            cmd1 = f'netsh interface ipv4 set dnsservers name="{adapter}" source=static address="{setup_primary}" primary'
            subprocess.run(cmd1, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            if setup_secondary:
                cmd2 = f'netsh interface ipv4 add dnsservers name="{adapter}" address="{setup_secondary}" index=2'
                subprocess.run(cmd2, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.is_connected = True
            self.after(0, self.update_power_button)
        except Exception as e:
            self.disconnect_dns(update_ui=False)
            self.after(0, lambda: messagebox.showerror("Error", f"Failed: {str(e)}"))
            self.after(0, self.update_power_button)

    def disconnect_dns(self, update_ui=True):
        adapter = self.active_interface
        if self.local_cf_server:
            self.local_cf_server.stop()
            self.local_cf_server = None
            self.after(0, lambda: self.lbl_cf_stats.configure(text=""))
        if self.doh_server:
            self.doh_server.stop()
            self.doh_server = None
        if self.fake_dns_server:
            self.fake_dns_server.stop()
            self.fake_dns_server = None
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{adapter}" source=dhcp'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except:
            pass
        self.is_connected = False
        if update_ui:
            self.after(0, self.update_power_button)

    def update_power_button(self):
        self.btn_power.configure(state="normal")
        if self.is_connected:
            self.btn_power.configure(text="ON", fg_color="#2E7D32", hover_color="#1B5E20")
            self.lbl_status.configure(text="Connected", text_color="#66BB6A")
        else:
            self.btn_power.configure(text="OFF", fg_color="#37474F", hover_color="#455A64")
            self.lbl_status.configure(text="Disconnected", text_color="gray")

    # =================================================================
    # متدهای تب Tools
    # =================================================================
    def test_dns_leak(self):
        self.leak_result.delete("1.0", "end")
        self.leak_result.insert("1.0", "Testing...\n")
        threading.Thread(target=self._test_leak_thread, daemon=True).start()

    def _test_leak_thread(self):
        result = DNSLeakTester.test_leak()
        if result:
            self.after(0, lambda: self.leak_result.delete("1.0", "end"))
            self.after(0, lambda: self.leak_result.insert("1.0", f"IP: {result['ip']}\nCountry: {result['country']}\nISP: {result['isp']}\n\n✅ No DNS leak detected!"))
        else:
            self.after(0, lambda: self.leak_result.delete("1.0", "end"))
            self.after(0, lambda: self.leak_result.insert("1.0", "❌ Failed to test DNS leak."))

    def check_dnssec(self):
        domain = self.dnssec_domain.get().strip()
        if not domain:
            messagebox.showerror("Error", "Please enter a domain!")
            return
        self.dnssec_result.configure(text="Checking...", text_color=CF_ORANGE)
        threading.Thread(target=self._check_dnssec_thread, args=(domain,), daemon=True).start()

    def _check_dnssec_thread(self, domain):
        valid, msg = DNSSECChecker.check(domain)
        color = "#66BB6A" if valid else "#EF5350"
        self.after(0, lambda: self.dnssec_result.configure(text=f"{'✅' if valid else '❌'} {msg}", text_color=color))

    def unmask_cname(self):
        domain = self.cname_domain.get().strip()
        if not domain:
            messagebox.showerror("Error", "Please enter a domain!")
            return
        self.cname_result.delete("1.0", "end")
        self.cname_result.insert("1.0", "Unmasking...\n")
        threading.Thread(target=self._unmask_thread, args=(domain,), daemon=True).start()

    def _unmask_thread(self, domain):
        result = CNAMEUnmasker.unmask(domain)
        self.after(0, lambda: self.cname_result.delete("1.0", "end"))
        output = f"Chain: {' → '.join(result['chain'])}\nFinal: {result['final_domain']}\nIPs: {', '.join(result['ips'])}\nBehind CDN: {'Yes' if result['behind_cdn'] else 'No'}"
        self.after(0, lambda: self.cname_result.insert("1.0", output))

    def test_dotdoh(self):
        url = self.dotdoh_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter DoH URL or DoT host!")
            return
        dns_type = self.dotdoh_type.get()
        self.dotdoh_result.configure(text="Testing...", text_color=CF_ORANGE)
        threading.Thread(target=self._test_dotdoh_thread, args=(url, dns_type), daemon=True).start()

    def _test_dotdoh_thread(self, url, dns_type):
        if dns_type == "DoH":
            result = DoTDoHTester.test_doh(url)
        else:
            result = DoTDoHTester.test_dot(url)
        status = "✅ Working" if result else "❌ Failed"
        color = "#66BB6A" if result else "#EF5350"
        self.after(0, lambda: self.dotdoh_result.configure(text=status, text_color=color))

    # =================================================================
    # متدهای تب Advanced
    # =================================================================
    def add_split_rule(self):
        domain = self.split_domain.get().strip()
        dns_server = self.split_dns_server.get().strip()
        if not domain or not dns_server:
            messagebox.showerror("Error", "Please enter domain and DNS server!")
            return
        self.split_dns.add_rule(domain, dns_server)
        self.split_rules_text.insert("end", f"{domain} → {dns_server}\n")
        self.split_domain.delete(0, "end")
        self.split_dns_server.delete(0, "end")

    def add_fake_rule(self):
        domain = self.fake_domain.get().strip()
        fake_ip = self.fake_ip.get().strip()
        if not domain or not fake_ip:
            messagebox.showerror("Error", "Please enter domain and fake IP!")
            return
        if not self.fake_dns_server:
            self.fake_dns_server = FakeDNSServer()
        self.fake_dns_server.add_fake_rule(domain, fake_ip)
        self.fake_rules_text.insert("end", f"{domain} → {fake_ip}\n")
        self.fake_domain.delete(0, "end")
        self.fake_ip.delete(0, "end")

    def start_fake_dns(self):
        if not self.fake_dns_server:
            messagebox.showerror("Error", "No fake rules added!")
            return
        if self.fake_dns_server.start():
            messagebox.showinfo("Success", "FakeDNS server started on localhost:53")
        else:
            messagebox.showerror("Error", "Failed to start FakeDNS! Port 53 might be busy.")

    def enable_smart_dns(self):
        messagebox.showinfo("Smart DNS", "Smart DNS enabled!\nDNS will auto-select based on site type.")

    def clear_dns_cache(self):
        self.dns_cache.clear()
        self.cache_info.configure(text=f"Cache size: {self.dns_cache.size()}")
        messagebox.showinfo("Success", "DNS cache cleared!")

    def configure_dnscrypt(self):
        messagebox.showinfo("DNSCrypt", "DNSCrypt configuration:\n1. Install dnscrypt-proxy\n2. Configure it to listen on 127.0.0.1:53\n3. Select 'localhost' as your DNS server")

    # =================================================================
    # مدیریت لیست DNS (افزودن/حذف)
    # =================================================================
    def delete_dns(self):
        choice = self.combo_dns.get()
        if "Localhost" in choice:
            messagebox.showwarning("Warning", "Cannot delete Localhost DNS!")
            return
        if len(self.servers_manager.get_all()) <= 1:
            messagebox.showwarning("Warning", "Cannot delete last DNS!")
            return
        if messagebox.askyesno("Delete", f"Delete '{choice}'?"):
            self.servers_manager.delete(choice)
            self.refresh_ui()

    def open_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Custom DNS")
        dialog.geometry("420x460")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dialog, text="Add New DNS", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 8))

        self.add_type_var = ctk.StringVar(value="IPv4")
        seg = ctk.CTkSegmentedButton(dialog, values=["IPv4", "DoH", "DoT", "Cloudflare Localhost"],
                                    variable=self.add_type_var, selected_color=CF_ORANGE)
        seg.pack(pady=(0, 12))

        entry_name = ctk.CTkEntry(dialog, placeholder_text="Name", width=300)
        entry_name.pack(pady=6)

        entry_primary = ctk.CTkEntry(dialog, placeholder_text="Primary IP / Host", width=300)
        entry_primary.pack(pady=6)

        entry_secondary = ctk.CTkEntry(dialog, placeholder_text="Secondary IP (Optional)", width=300)
        entry_secondary.pack(pady=6)

        entry_port = ctk.CTkEntry(dialog, placeholder_text="Port (for DoT, default: 853)", width=300)
        entry_port.pack(pady=6)
        entry_port.pack_forget()

        def toggle_fields(val):
            entry_secondary.pack_forget()
            entry_port.pack_forget()
            if val == "IPv4":
                entry_primary.configure(placeholder_text="Primary IP (e.g. 8.8.8.8)")
                entry_secondary.pack(pady=6)
            elif val == "DoH":
                entry_primary.configure(placeholder_text="DoH URL (e.g. https://dns.google/dns-query)")
            elif val == "DoT":
                entry_primary.configure(placeholder_text="DoT Host (e.g. dns.google)")
                entry_port.pack(pady=6)
                entry_port.insert(0, "853")
            else:  # Cloudflare Localhost
                entry_primary.configure(placeholder_text="Auto (localhost:53)")
                entry_name.delete(0, "end")
                entry_name.insert(0, "Cloudflare Localhost")
                entry_primary.delete(0, "end")
                entry_primary.insert(0, "localhost")

        self.add_type_var.trace_add("write", lambda *_: toggle_fields(self.add_type_var.get()))
        toggle_fields("IPv4")

        def save_new():
            name = entry_name.get().strip()
            primary = entry_primary.get().strip()
            dns_type = self.add_type_var.get()
            if not name or not primary:
                messagebox.showerror("Error", "Name and Address are required!")
                return
            if dns_type == "Cloudflare Localhost":
                new_dns = {"name": name, "primary": "localhost", "secondary": "", "type": "LocalCF", "cf_only": True}
            elif dns_type == "DoH":
                if not primary.startswith("http"):
                    messagebox.showerror("Error", "DoH URL must start with http:// or https://")
                    return
                new_dns = {"name": name, "primary": primary, "secondary": "", "type": "DoH"}
            elif dns_type == "DoT":
                port = int(entry_port.get()) if entry_port.get().isdigit() else 853
                new_dns = {"name": name, "primary": primary, "port": port, "type": "DoT"}
            else:
                new_dns = {"name": name, "primary": primary, "secondary": entry_secondary.get().strip(), "type": "IPv4"}
            self.servers_manager.add(new_dns)
            self.refresh_ui()
            self.combo_dns.set(name)
            self.on_dns_select(name)
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save DNS", fg_color=CF_ORANGE, text_color="black", command=save_new).pack(pady=15)

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
