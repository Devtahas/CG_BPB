# tabs/client/client_ui.py
import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import threading
import concurrent.futures
import requests
import time
import random
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, DIRS

from .client_core import ClientCore
from .client_configs import ClientConfigs
from .client_import import ClientImport
from .client_utils import ClientUtils
from .mimicry import MimicryManager
from .config_explorer import ConfigExplorerTab
from .vpn_chain import VpnChainFrame          # ★ تب جدید زنجیره
from .mimicry.profile_recorder import ProfileRecorder   # ★ ضبط ۱۰ دقیقه‌ای


class ProtocolSelectDialog(ctk.CTkToplevel):
    """پنجره انتخاب نوع پروتکل برای ADD کردن کانفیگ"""

    def __init__(self, parent, on_protocol_selected):
        super().__init__(parent)
        self.parent = parent
        self.on_protocol_selected = on_protocol_selected

        self.title("Select Protocol")
        self.geometry("380x550")
        self.attributes("-topmost", True)
        self.configure(fg_color=BG_PANEL)

        self.setup_ui()

    def setup_ui(self):
        header = ctk.CTkLabel(self, text="➕ Import Config from Clipboard",
                              font=ctk.CTkFont(size=18, weight="bold"),
                              text_color=CF_ORANGE)
        header.pack(pady=(20, 10))

        desc = ctk.CTkLabel(self, text="1. Select your protocol type\n2. Make sure the config link is in clipboard\n3. Click Import",
                            text_color="gray", justify="left")
        desc.pack(pady=(0, 20))

        protocols_frame = ctk.CTkScrollableFrame(self, width=320, height=380, fg_color="transparent")
        protocols_frame.pack(padx=20, pady=10, fill="both", expand=True)

        protocols = [
            ("VLESS", "vless://", "Most common for Cloudflare"),
            ("VMESS", "vmess://", "Legacy but widely used"),
            ("Shadowsocks", "ss://", "Lightweight proxy"),
            ("Trojan", "trojan://", "HTTPS masquerading"),
            ("Hysteria2", "hy2://", "Fast UDP-based"),
            ("TUIC", "tuic://", "Modern UDP protocol"),
            ("WireGuard", "wireguard://", "VPN protocol"),
            ("SOCKS4/5", "socks4://", "Generic proxy"),
            ("HTTP/HTTPS", "http://", "HTTP proxy"),
        ]

        for name, prefix, desc_text in protocols:
            btn = ctk.CTkButton(
                protocols_frame,
                text=f"{name}\n{desc_text}",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                border_width=1,
                border_color=CF_ORANGE,
                text_color="white",
                anchor="w",
                height=60,
                command=lambda p=prefix, n=name: self.select_protocol(p, n)
            )
            btn.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(self, text="Cancel", fg_color="gray", hover_color="#555",
                     command=self.destroy).pack(pady=20)

    def select_protocol(self, prefix, name):
        self.destroy()
        self.on_protocol_selected(prefix, name)


class ClientUI(ctk.CTkFrame):
    """کلاس اصلی UI کلاینت VPN"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.configs_dir = DIRS["configs"]

        self.core = ClientCore()
        self.core.set_callbacks(self.update_status, self.update_traffic, self.update_connect_button_text)

        self.var_tun = ctk.BooleanVar(value=False)
        self.selected_config_path = None

        self.dpi_settings = {}

        self.mimicry_manager = MimicryManager()

        # ========== ابتدا UI را بساز ==========
        self.setup_ui()

        # ========== سپس مدیران را با reference به scroll_area ایجاد کن ==========
        self.config_manager = ClientConfigs(self, self.configs_dir, self.scroll_area)
        self.importer = ClientImport(self, self.configs_dir, self.load_configs)

        self.load_configs()

        self.config_manager.set_callbacks(
            on_select=self.on_config_selected,
            on_delete=None,
            on_edit=None,
            is_connected_func=lambda: self.core.is_connected
        )
        self.importer.set_status_callback(self.update_status)

        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("client")

    def setup_ui(self):
        # HEADER FRAME
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 5), sticky="ew")

        ctk.CTkLabel(header_frame, text="🛡️ VPN Client", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        self.btn_add = ctk.CTkButton(header_frame, text="➕ ADD", width=50, fg_color="#2E7D32",
                                     hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"),
                                     command=self.open_add_dialog)
        self.btn_add.pack(side="right", padx=5)

        self.btn_refresh = ctk.CTkButton(header_frame, text="🔄", width=30, fg_color="transparent",
                                         border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                                         hover_color="#332015", command=self.load_configs)
        self.btn_refresh.pack(side="right", padx=5)

        self.btn_ping_all = ctk.CTkButton(header_frame, text="⚡ Pings", width=60, fg_color="#F9A825",
                                          hover_color="#F57F17", text_color="black",
                                          font=ctk.CTkFont(weight="bold"), command=self.test_all_pings)
        self.btn_ping_all.pack(side="right", padx=5)

        self.btn_sort = ctk.CTkButton(header_frame, text="🔽 Sort", width=60, fg_color="#00ACC1",
                                      hover_color="#006064", font=ctk.CTkFont(weight="bold"),
                                      command=self.sort_by_ping)
        self.btn_sort.pack(side="right", padx=5)

        self.btn_sub = ctk.CTkButton(header_frame, text="🔗 Sub Link", width=80, fg_color="#8E24AA",
                                     hover_color="#6A1B9A", font=ctk.CTkFont(weight="bold"),
                                     command=lambda: self.importer.import_sub_link(None) if hasattr(self, 'importer') else None)
        self.btn_sub.pack(side="right", padx=5)

        self.btn_qr = ctk.CTkButton(header_frame, text="🔳 QR", width=60, fg_color="#1565C0",
                                    hover_color="#0D47A1", font=ctk.CTkFont(weight="bold"),
                                    command=lambda: self.importer.import_from_qr() if hasattr(self, 'importer') else None)
        self.btn_qr.pack(side="right", padx=5)

        self.btn_paste = ctk.CTkButton(header_frame, text="📋 Paste", width=70, fg_color="#2E7D32",
                                       hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"),
                                       command=lambda: self.importer.import_from_clipboard() if hasattr(self, 'importer') else None)
        self.btn_paste.pack(side="right", padx=5)

        # ========== Tabview اصلی ==========
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE,
                                      segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.tab_main = self.tabview.add("🔌 Connection")
        self.tab_chain = self.tabview.add("🔁 VPN-in-VPN Chain")    # ★ تب جدید
        self.tab_pre_vpn = self.tabview.add("🔗 Pre‑VPN Chain")
        self.tab_advanced = self.tabview.add("🚀 Advanced DPI Bypass")
        self.tab_mimicry = self.tabview.add("🎭 Traffic Mimicry")
        self.tab_explorer = self.tabview.add("📁 Config Explorer")

        # ★ نمونه‌سازی Chain Frame
        self.chain_frame = VpnChainFrame(self.tab_chain, app_controller=self)
        self.chain_frame.pack(fill="both", expand=True)

        # ساخت سایر تب‌ها
        self.setup_main_tab()
        self.setup_pre_vpn_tab()
        self.setup_advanced_tab()
        self.setup_mimicry_tab()
        self.setup_explorer_tab()

    def setup_main_tab(self):
        self.status_frame = ctk.CTkFrame(self.tab_main, fg_color=BG_PANEL, corner_radius=15)
        self.status_frame.pack(fill="x", padx=20, pady=20)
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Status: Disconnected",
                                       font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.lbl_traffic = ctk.CTkLabel(self.status_frame, text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s",
                                        font=ctk.CTkFont(size=14, weight="bold"), text_color="#29B6F6")
        self.lbl_traffic.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")

        self.switch_tun = ctk.CTkSwitch(self.status_frame, text="TUN Mode", variable=self.var_tun,
                                        progress_color=CF_ORANGE, font=ctk.CTkFont(weight="bold"),
                                        command=self.on_tun_toggle)
        self.switch_tun.grid(row=0, column=2, rowspan=2, padx=15, sticky="e")

        self.btn_connect = ctk.CTkButton(self.status_frame, text="▶ CONNECT", fg_color="#2E7D32",
                                         hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14),
                                         command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=3, rowspan=2, padx=20, pady=15, sticky="e")

        self.ip_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.ip_frame.pack(fill="x", padx=40, pady=0)

        self.btn_check_ip = ctk.CTkButton(self.ip_frame, text="🌍 Check My IP", width=120,
                                          fg_color="transparent", border_width=1, border_color="#29B6F6",
                                          text_color="#29B6F6", command=self.check_my_ip)
        self.btn_check_ip.pack(side="left", padx=0)

        self.lbl_ip_info = ctk.CTkLabel(self.ip_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_ip_info.pack(side="left", padx=15)

        self.scroll_area = ctk.CTkScrollableFrame(self.tab_main, fg_color="transparent")
        self.scroll_area.pack(fill="both", expand=True, padx=30, pady=10)
        self.scroll_area.grid_columnconfigure(0, weight=1)

    def setup_pre_vpn_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_pre_vpn, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="🔗 Pre‑VPN Chain", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=CF_ORANGE).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Select a Pre‑VPN config (from Datacenter Scanner) to act as front proxy.\n"
                    "Your main config will route through this Pre‑VPN.",
                    text_color="gray", justify="left").pack(anchor="w", pady=(0, 20))

        select_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        select_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(select_frame, text="Active Pre‑VPN:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))

        pre_vpn_configs = self._get_pre_vpn_configs()
        self.pre_vpn_combo = ctk.CTkComboBox(
            select_frame, values=pre_vpn_configs, width=300,
            state="readonly", dropdown_fg_color="#18181B"
        )
        self.pre_vpn_combo.pack(anchor="w", padx=20, pady=5)
        if pre_vpn_configs:
            self.pre_vpn_combo.set(pre_vpn_configs[0])
            self.selected_pre_vpn_path = os.path.join(DIRS["configs"], pre_vpn_configs[0])
        else:
            self.selected_pre_vpn_path = None

        self.pre_vpn_enabled = ctk.BooleanVar(value=False)
        self.pre_vpn_switch = ctk.CTkSwitch(
            select_frame, text="Enable Pre‑VPN Chaining",
            variable=self.pre_vpn_enabled,
            command=self.toggle_pre_vpn,
            progress_color=CF_ORANGE
        )
        self.pre_vpn_switch.pack(pady=10)

        self.pre_vpn_status = ctk.CTkLabel(scroll, text="Pre‑VPN is inactive", text_color="gray")
        self.pre_vpn_status.pack(pady=10)

        info_text = """
        🎯 How Pre‑VPN Chain works:
        1. Datacenter Scanner finds clean Iranian IPs that can reach Cloudflare Workers.
        2. Select a [PreVPN] config above.
        3. Enable Pre‑VPN Chaining.
        4. Connect your main config as usual.

        The main config will route through the Pre‑VPN, increasing the chance of
        bypassing whitelist filters.
        """
        ctk.CTkLabel(scroll, text=info_text, justify="left", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=20)

    def setup_advanced_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_advanced, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(header_frame, text="🛡️ Advanced DPI Bypass Engine",
                    font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack()
        ctk.CTkLabel(header_frame, text="Bypass deep packet inspection and censorship systems",
                    text_color="gray").pack()

        # لایه TLS
        tls_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        tls_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tls_frame, text="🔒 TLS Layer Techniques", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#29B6F6").pack(pady=(15, 5), anchor="w", padx=20)

        self.tls13_var = ctk.BooleanVar(value=False)
        tls13_frame = ctk.CTkFrame(tls_frame, fg_color="transparent")
        tls13_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkSwitch(tls13_frame, text="Force TLS 1.3", variable=self.tls13_var,
                     command=self.on_tls13_toggle, progress_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(tls13_frame, text="Use TLS 1.3 protocol for enhanced security",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        self.sni_spoof_var = ctk.BooleanVar(value=False)
        sni_frame = ctk.CTkFrame(tls_frame, fg_color="transparent")
        sni_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkSwitch(sni_frame, text="SNI Spoofing", variable=self.sni_spoof_var,
                     command=self.on_sni_spoof_toggle, progress_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(sni_frame, text="Spoof Server Name Indication to bypass SNI-based filters",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        sni_target_frame = ctk.CTkFrame(tls_frame, fg_color="transparent")
        sni_target_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(sni_target_frame, text="Fake SNI Target:", width=120).pack(side="left")
        self.sni_target = ctk.CTkEntry(sni_target_frame, width=200, placeholder_text="www.google.com")
        self.sni_target.insert(0, "www.google.com")
        self.sni_target.pack(side="left", padx=10)
        self.sni_target.configure(state="disabled")

        self.reality_var = ctk.BooleanVar(value=False)
        reality_frame = ctk.CTkFrame(tls_frame, fg_color="transparent")
        reality_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkSwitch(reality_frame, text="REALITY Protocol", variable=self.reality_var,
                     command=self.on_reality_toggle, progress_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(reality_frame, text="Most advanced protocol - traffic looks like real HTTPS",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        reality_settings = ctk.CTkFrame(tls_frame, fg_color="transparent")
        reality_settings.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(reality_settings, text="Server Name:", width=100).pack(side="left")
        self.reality_sni = ctk.CTkEntry(reality_settings, width=180, placeholder_text="www.google.com")
        self.reality_sni.insert(0, "www.google.com")
        self.reality_sni.pack(side="left", padx=5)
        self.reality_sni.configure(state="disabled")

        ctk.CTkLabel(reality_settings, text="Public Key:", width=80).pack(side="left", padx=(10, 0))
        self.reality_pubkey = ctk.CTkEntry(reality_settings, width=200, placeholder_text="Server public key")
        self.reality_pubkey.pack(side="left", padx=5)
        self.reality_pubkey.configure(state="disabled")

        # لایه Packet Manipulation
        packet_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        packet_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(packet_frame, text="📦 Packet Manipulation", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#AB47BC").pack(pady=(15, 5), anchor="w", padx=20)

        self.fragment_var = ctk.BooleanVar(value=False)
        frag_frame = ctk.CTkFrame(packet_frame, fg_color="transparent")
        frag_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkSwitch(frag_frame, text="Packet Fragmentation", variable=self.fragment_var,
                     command=self.on_fragment_toggle, progress_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(frag_frame, text="Split first packet into small fragments to confuse DPI",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        frag_settings = ctk.CTkFrame(packet_frame, fg_color="transparent")
        frag_settings.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(frag_settings, text="Packets:", width=60).pack(side="left")
        self.frag_packets = ctk.CTkEntry(frag_settings, width=60, placeholder_text="1-1")
        self.frag_packets.insert(0, "1-1")
        self.frag_packets.pack(side="left", padx=5)
        self.frag_packets.configure(state="disabled")

        ctk.CTkLabel(frag_settings, text="Length:", width=50).pack(side="left", padx=(10, 0))
        self.frag_length = ctk.CTkEntry(frag_settings, width=70, placeholder_text="10-20")
        self.frag_length.insert(0, "10-20")
        self.frag_length.pack(side="left", padx=5)
        self.frag_length.configure(state="disabled")

        ctk.CTkLabel(frag_settings, text="Interval:", width=55).pack(side="left", padx=(10, 0))
        self.frag_interval = ctk.CTkEntry(frag_settings, width=60, placeholder_text="5")
        self.frag_interval.insert(0, "5")
        self.frag_interval.pack(side="left", padx=5)
        self.frag_interval.configure(state="disabled")

        # لایه HTTP/HTTPS
        http_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        http_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(http_frame, text="🌐 HTTP/HTTPS Techniques", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#EF5350").pack(pady=(15, 5), anchor="w", padx=20)

        self.fake_tls_var = ctk.BooleanVar(value=False)
        faketls_frame = ctk.CTkFrame(http_frame, fg_color="transparent")
        faketls_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkSwitch(faketls_frame, text="FakeTLS", variable=self.fake_tls_var,
                     command=self.on_fake_tls_toggle, progress_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(faketls_frame, text="Disguise traffic as normal HTTPS (requires GoodbyeDPI)",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        self.fake_http_var = ctk.BooleanVar(value=False)
        fakehttp_frame = ctk.CTkFrame(http_frame, fg_color="transparent")
        fakehttp_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkSwitch(fakehttp_frame, text="FakeHTTP", variable=self.fake_http_var,
                     command=self.on_fake_http_toggle, progress_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(fakehttp_frame, text="Send fake HTTP requests to confuse DPI (requires GoodbyeDPI)",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        fake_target_frame = ctk.CTkFrame(http_frame, fg_color="transparent")
        fake_target_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(fake_target_frame, text="Fake Target Host:", width=120).pack(side="left")
        self.fake_target_host = ctk.CTkEntry(fake_target_frame, width=200, placeholder_text="www.google.com")
        self.fake_target_host.insert(0, "www.google.com")
        self.fake_target_host.pack(side="left", padx=10)
        self.fake_target_host.configure(state="disabled")

        status_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        status_frame.pack(fill="x", pady=10)

        self.dpi_status = ctk.CTkTextbox(status_frame, height=120, font=ctk.CTkFont(size=11))
        self.dpi_status.pack(fill="x", padx=20, pady=10)

        btn_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Apply Selected Methods", fg_color=CF_ORANGE, text_color="black",
                     font=ctk.CTkFont(weight="bold"), command=self.apply_dpi_bypass).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Reset All", fg_color="#C62828", text_color="white",
                     command=self.reset_dpi_bypass).pack(side="left", padx=5)

    def setup_mimicry_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_mimicry, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="🎭 Traffic Mimicry", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=CF_ORANGE).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Disguise your VPN traffic as normal website traffic (Aparat, YouTube, etc.)",
                    text_color="gray").pack(anchor="w", pady=(0, 20))

        gen_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        gen_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(gen_frame, text="🔍 Auto-Generate Profile from URL",
                    font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))

        url_frame = ctk.CTkFrame(gen_frame, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=5)
        self.mimicry_url_entry = ctk.CTkEntry(url_frame, placeholder_text="https://www.aparat.com")
        self.mimicry_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_generate_profile = ctk.CTkButton(url_frame, text="Generate Profile", fg_color=CF_ORANGE,
                                                 text_color="black", command=self.auto_generate_mimicry_profile)
        self.btn_generate_profile.pack(side="right", padx=(0, 5))

        # ★ دکمه ضبط ۱۰ دقیقه‌ای
        self.btn_record_profile = ctk.CTkButton(url_frame, text="🎥 Record Full (10m)",
                                               fg_color="#AB47BC", text_color="white",
                                               command=self.record_full_profile)
        self.btn_record_profile.pack(side="right")

        ctk.CTkLabel(gen_frame, text="This will analyze the target site and create a mimicry profile automatically.",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(0, 15))

        enable_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        enable_frame.pack(fill="x", pady=10)

        self.mimicry_enabled_var = ctk.BooleanVar(value=False)
        self.mimicry_switch = ctk.CTkSwitch(
            enable_frame, text="Enable Traffic Mimicry",
            variable=self.mimicry_enabled_var,
            command=self.toggle_mimicry,
            progress_color=CF_ORANGE
        )
        self.mimicry_switch.pack(pady=15)

        profile_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        profile_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(profile_frame, text="Select Profile:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))

        profiles = self.mimicry_manager.get_available_profiles()
        self.mimicry_profile_combo = ctk.CTkComboBox(
            profile_frame, values=profiles, width=200,
            state="readonly", dropdown_fg_color="#18181B"
        )
        self.mimicry_profile_combo.pack(anchor="w", padx=20, pady=(0, 15))
        if profiles:
            self.mimicry_profile_combo.set(profiles[0])

        btn_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(btn_frame, text="➕ New Profile", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE,
                     command=self.create_mimicry_profile).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="✏️ Edit Profile", fg_color="transparent", border_width=1,
                     border_color="#29B6F6", text_color="#29B6F6",
                     command=self.edit_mimicry_profile).pack(side="left", padx=5)

        self.mimicry_status = ctk.CTkLabel(scroll, text="Status: Stopped", text_color="gray")
        self.mimicry_status.pack(pady=10)

        info_text = """
        🎯 How it works:
        1. Enter a target URL (e.g., https://www.aparat.com) and click "Generate Profile" or "Record Full (10m)".
        2. Select the generated/recorded profile from the list.
        3. Enable Traffic Mimicry.
        4. Connect to VPN as usual.

        All your traffic will be disguised with:
        • TLS Fingerprint (JA3/JA4)
        • HTTP Headers matching the target site
        • Realistic packet timing & jitter
        • Random padding to evade DPI
        """
        ctk.CTkLabel(scroll, text=info_text, justify="left", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=20)

    def setup_explorer_tab(self):
        self.explorer_tab = ConfigExplorerTab(self.tab_explorer, self.configs_dir)
        self.explorer_tab.pack(fill="both", expand=True)

    # ==========================================
    # Pre‑VPN Chain Methods
    # ==========================================
    def _get_pre_vpn_configs(self):
        configs = []
        if not os.path.exists(self.configs_dir):
            return configs
        for f in os.listdir(self.configs_dir):
            if f.startswith("[PreVPN]") and f.endswith(".json"):
                configs.append(f)
        return configs

    def toggle_pre_vpn(self):
        if self.pre_vpn_enabled.get():
            selected = self.pre_vpn_combo.get()
            if not selected:
                messagebox.showerror("Error", "Please select a Pre‑VPN config first.")
                self.pre_vpn_enabled.set(False)
                return
            self.selected_pre_vpn_path = os.path.join(self.configs_dir, selected)
            self.pre_vpn_status.configure(text=f"Pre‑VPN active: {selected}", text_color="#66BB6A")
        else:
            self.selected_pre_vpn_path = None
            self.pre_vpn_status.configure(text="Pre‑VPN is inactive", text_color="gray")

    def _get_pre_vpn_config_path(self):
        if self.pre_vpn_enabled.get() and self.selected_pre_vpn_path:
            return self.selected_pre_vpn_path
        return None

    # ==========================================
    # دکمه ADD و مدیریت import خودکار
    # ==========================================
    def open_add_dialog(self):
        ProtocolSelectDialog(self, self.import_from_clipboard_by_protocol)

    def import_from_clipboard_by_protocol(self, prefix, protocol_name):
        try:
            clipboard_text = self.clipboard_get().strip()
            if not clipboard_text:
                messagebox.showerror("Error", "Clipboard is empty!\n\nPlease copy a config link first.")
                return

            if not clipboard_text.startswith(prefix):
                if prefix == "socks4://" and clipboard_text.startswith("socks5://"):
                    pass
                elif prefix == "http://" and clipboard_text.startswith("https://"):
                    pass
                else:
                    messagebox.showerror(
                        "Protocol Mismatch",
                        f"Clipboard content does not start with {prefix}\n\n"
                        f"Expected: {prefix}...\n"
                        f"Found: {clipboard_text[:50]}...\n\n"
                        f"Please copy a {protocol_name} config link and try again."
                    )
                    return

            self.importer.process_imported_link(clipboard_text)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read clipboard:\n{str(e)}")

    # ==========================================
    # متدهای UI و وضعیت
    # ==========================================
    def update_status(self, text, color):
        """به‌روزرسانی وضعیت اتصال (هم تب اصلی و هم تب زنجیره)"""
        self.lbl_status.configure(text=text, text_color=color)
        if hasattr(self, 'chain_frame'):
            self.chain_frame.update_chain_status(text, color)

    def update_traffic(self, dl, ul):
        """به‌روزرسانی نمایش ترافیک (هم تب اصلی و هم تب زنجیره)"""
        self.lbl_traffic.configure(text=f"⬇️ {dl}   |   ⬆️ {ul}")
        if hasattr(self, 'chain_frame'):
            self.chain_frame.update_chain_traffic(dl, ul)

    def update_connect_button_text(self, text):
        if text == "▶ CONNECT":
            self.btn_connect.configure(text=text, fg_color="#2E7D32", hover_color="#1B5E20", state="normal")
        elif text == "⏳ DOWNLOADING XRAY...":
            self.btn_connect.configure(text=text, state="disabled")
        else:
            self.btn_connect.configure(text=text)

    def on_tun_toggle(self):
        if self.var_tun.get():
            messagebox.showinfo("TUN Mode", "TUN Mode routes ALL Windows traffic through the VPN.\n\n⚠️ Note: You must Run the App as Administrator for this to work!")

    # ==========================================
    # متدهای IP
    # ==========================================
    def check_my_ip(self):
        self.btn_check_ip.configure(state="disabled", text="⏳ Checking...")
        self.lbl_ip_info.configure(text="")
        threading.Thread(target=self._check_ip_thread, daemon=True).start()

    def _check_ip_thread(self):
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5).json()
            ip = resp.get("query", "Unknown")
            isp = resp.get("isp", "Unknown")
            cc = resp.get("countryCode", "UN")
            flag = ClientUtils.get_flag_emoji(cc)
            info_text = f"{flag} {ip}  |  ISP: {isp}"
            color = "#66BB6A" if self.core.is_connected else "gray"
            self.after(0, lambda: self.lbl_ip_info.configure(text=info_text, text_color=color))
        except Exception:
            self.after(0, lambda: self.lbl_ip_info.configure(text="❌ Failed to fetch IP", text_color="#EF5350"))
        finally:
            self.after(0, lambda: self.btn_check_ip.configure(state="normal", text="🌍 Check My IP"))

    # ==========================================
    # متدهای اتصال
    # ==========================================
    def toggle_connection(self):
        if not self.core.is_connected:
            self.start_connection()
        else:
            self.stop_connection()

    def start_connection(self):
        self.core.set_mimicry_manager(self.mimicry_manager)
        self.core.set_dpi_settings(self.dpi_settings)

        if getattr(sys, 'frozen', False):
            root_dir = os.path.dirname(sys.executable)
        else:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        pre_vpn_path = self._get_pre_vpn_config_path()

        success = self.core.start_connection(
            self.config_manager.get_selected_config(),
            self.var_tun,
            root_dir,
            self.configs_dir,
            mimicry_manager=self.mimicry_manager,
            pre_vpn_config_path=pre_vpn_path
        )

        if success:
            self.btn_connect.configure(text="⏹ DISCONNECT", fg_color="#C62828", hover_color="#8E0000")

    def stop_connection(self):
        self.core.stop_connection()
        self.btn_connect.configure(text="▶ CONNECT", fg_color="#2E7D32", hover_color="#1B5E20")

    def on_config_selected(self, path):
        self.selected_config_path = path

    # ==========================================
    # متدهای کانفیگ
    # ==========================================
    def load_configs(self):
        if hasattr(self, 'config_manager'):
            self.config_manager.load_configs()

    def test_all_pings(self):
        if not hasattr(self, 'config_manager') or not self.config_manager.config_buttons:
            return
        self.btn_ping_all.configure(state="disabled", text="⏳ Testing...")
        threading.Thread(target=self._run_ping_tests, daemon=True).start()

    def _run_ping_tests(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            for item in self.config_manager.config_buttons:
                future = executor.submit(
                    ClientUtils.ping_config,
                    item["path"],
                    self.config_manager.update_ping
                )
                futures.append(future)
            concurrent.futures.wait(futures)
        self.after(0, lambda: self.btn_ping_all.configure(state="normal", text="⚡ Pings"))
        self.after(500, self.sort_by_ping)

    def sort_by_ping(self):
        if hasattr(self, 'config_manager'):
            self.config_manager.sort_by_ping()

    # ==========================================
    # متدهای DPI Bypass
    # ==========================================
    def on_tls13_toggle(self):
        if self.tls13_var.get():
            self.log_dpi("TLS 1.3 will be applied on next connection")
        else:
            self.log_dpi("TLS 1.3 disabled")

    def on_sni_spoof_toggle(self):
        state = "enabled" if self.sni_spoof_var.get() else "disabled"
        self.sni_target.configure(state="normal" if self.sni_spoof_var.get() else "disabled")
        self.log_dpi(f"SNI Spoofing {state}")

    def on_reality_toggle(self):
        state = "enabled" if self.reality_var.get() else "disabled"
        self.reality_sni.configure(state="normal" if self.reality_var.get() else "disabled")
        self.reality_pubkey.configure(state="normal" if self.reality_var.get() else "disabled")
        self.log_dpi(f"REALITY Protocol {state}")

    def on_fragment_toggle(self):
        state = "enabled" if self.fragment_var.get() else "disabled"
        self.frag_packets.configure(state="normal" if self.fragment_var.get() else "disabled")
        self.frag_length.configure(state="normal" if self.fragment_var.get() else "disabled")
        self.frag_interval.configure(state="normal" if self.fragment_var.get() else "disabled")
        self.log_dpi(f"Packet Fragmentation {state}")

    def on_fake_tls_toggle(self):
        state = "enabled" if self.fake_tls_var.get() else "disabled"
        self.fake_target_host.configure(state="normal" if self.fake_tls_var.get() else "disabled")
        self.log_dpi(f"FakeTLS {state}")

    def on_fake_http_toggle(self):
        state = "enabled" if self.fake_http_var.get() else "disabled"
        self.log_dpi(f"FakeHTTP {state}")

    def log_dpi(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.dpi_status.insert("end", f"[{timestamp}] {msg}\n")
        self.dpi_status.see("end")

    def apply_dpi_bypass(self):
        self.log_dpi("=" * 50)
        self.log_dpi("Applying DPI Bypass settings...")

        self.dpi_settings = {
            "tls13": self.tls13_var.get(),
            "sni_spoof": self.sni_spoof_var.get(),
            "sni_target": self.sni_target.get().strip() if self.sni_spoof_var.get() else "",
            "reality": self.reality_var.get(),
            "reality_sni": self.reality_sni.get().strip() if self.reality_var.get() else "",
            "reality_pubkey": self.reality_pubkey.get().strip() if self.reality_var.get() else "",
            "fragment": self.fragment_var.get(),
            "frag_packets": self.frag_packets.get().strip() if self.fragment_var.get() else "1-1",
            "frag_length": self.frag_length.get().strip() if self.fragment_var.get() else "10-20",
            "frag_interval": self.frag_interval.get().strip() if self.fragment_var.get() else "5",
            "fake_tls": self.fake_tls_var.get(),
            "fake_http": self.fake_http_var.get(),
            "fake_target": self.fake_target_host.get().strip() if self.fake_tls_var.get() else ""
        }

        self.log_dpi("✅ DPI Bypass settings saved")
        self.log_dpi("⚠️ Restart connection to apply changes")

        if self.core.is_connected:
            self.log_dpi("⚠️ You are currently connected. Disconnect and reconnect to apply changes.")

    def reset_dpi_bypass(self):
        self.tls13_var.set(False)
        self.sni_spoof_var.set(False)
        self.reality_var.set(False)
        self.fragment_var.set(False)
        self.fake_tls_var.set(False)
        self.fake_http_var.set(False)

        self.sni_target.configure(state="disabled")
        self.reality_sni.configure(state="disabled")
        self.reality_pubkey.configure(state="disabled")
        self.frag_packets.configure(state="disabled")
        self.frag_length.configure(state="disabled")
        self.frag_interval.configure(state="disabled")
        self.fake_target_host.configure(state="disabled")

        self.dpi_settings = {}
        self.log_dpi("🔄 All DPI Bypass settings reset")
        self.log_dpi("⚠️ Restart connection to apply changes")

    # ★ متد بارگذاری پلاگین‌ها
    def load_category_plugins(self, category: str):
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

    # ----- Mimicry Profile Generation -----
    def auto_generate_mimicry_profile(self):
        """تولید خودکار پروفایل از URL وارد شده."""
        url = self.mimicry_url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return

        if not url.startswith("http"):
            url = "https://" + url

        self.btn_generate_profile.configure(state="disabled", text="Generating...")
        self.mimicry_status.configure(text="Analyzing target site...", text_color=CF_ORANGE)

        def _generate():
            try:
                if hasattr(self.mimicry_manager, 'generate_profile_from_url'):
                    profile = self.mimicry_manager.generate_profile_from_url(url)
                else:
                    from tabs.client.mimicry.mimicry_profile import MimicryProfile
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.path.split('/')[0]
                    profile = MimicryProfile()
                    profile.name = domain.split('.')[0].capitalize()
                    profile.description = f"Auto-generated profile for {domain}"
                    profile.tls.server_name = domain
                    self.mimicry_manager.save_profile(profile)

                self.after(0, lambda: self.btn_generate_profile.configure(state="normal", text="Generate Profile"))

                if profile:
                    self.after(0, lambda: messagebox.showinfo("Success", f"Profile '{profile.name}' created successfully."))
                    profiles = self.mimicry_manager.get_available_profiles()
                    self.after(0, lambda: self.mimicry_profile_combo.configure(values=profiles))
                    self.after(0, lambda: self.mimicry_profile_combo.set(profile.name))
                    self.after(0, lambda: self.mimicry_status.configure(text=f"Profile '{profile.name}' ready", text_color="#66BB6A"))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Failed to generate profile."))
                    self.after(0, lambda: self.mimicry_status.configure(text="Generation failed", text_color="#EF5350"))
            except Exception as e:
                self.after(0, lambda: self.btn_generate_profile.configure(state="normal", text="Generate Profile"))
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to generate profile:\n{str(e)}"))
                self.after(0, lambda: self.mimicry_status.configure(text="Generation failed", text_color="#EF5350"))

        threading.Thread(target=_generate, daemon=True).start()

    # ----- ضبط ۱۰ دقیقه‌ای -----
    def record_full_profile(self):
        """ضبط ۱۰ دقیقه‌ای پروفایل با ProfileRecorder"""
        url = self.mimicry_url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return

        if not url.startswith("http"):
            url = "https://" + url

        dialog = ctk.CTkInputDialog(text="Enter a name for the recorded profile:",
                                    title="Profile Name")
        profile_name = dialog.get_input()
        if not profile_name:
            return

        self.btn_record_profile.configure(state="disabled", text="⏳ Recording...")
        self.mimicry_status.configure(text="Recording 10-min traffic... Keep the window open.", text_color="#FFA726")

        def _record():
            try:
                recorder = ProfileRecorder()
                profile = recorder.record(
                    url=url,
                    profile_name=profile_name,
                    output_dir=self.mimicry_manager.profiles_dir,
                    duration=600
                )
                if profile:
                    self.after(0, lambda: messagebox.showinfo(
                        "Success", f"Profile '{profile_name}' recorded successfully!"))
                    profiles = self.mimicry_manager.get_available_profiles()
                    self.after(0, lambda: self.mimicry_profile_combo.configure(values=profiles))
                    self.after(0, lambda: self.mimicry_profile_combo.set(profile_name))
                    self.after(0, lambda: self.mimicry_status.configure(
                        text=f"Profile '{profile_name}' ready", text_color="#66BB6A"))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Recording failed."))
                    self.after(0, lambda: self.mimicry_status.configure(text="Recording failed", text_color="#EF5350"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Recording failed:\n{str(e)}"))
                self.after(0, lambda: self.mimicry_status.configure(text="Recording failed", text_color="#EF5350"))
            finally:
                self.after(0, lambda: self.btn_record_profile.configure(state="normal", text="🎥 Record Full (10m)"))

        threading.Thread(target=_record, daemon=True).start()

    def toggle_mimicry(self):
        """فعال/غیرفعال کردن Traffic Mimicry"""
        if self.mimicry_enabled_var.get():
            profile_name = self.mimicry_profile_combo.get()
            if not profile_name:
                messagebox.showerror("Error", "Please select a profile first.")
                self.mimicry_enabled_var.set(False)
                return
            if self.mimicry_manager.set_active_profile(profile_name):
                if self.mimicry_manager.start():
                    self.mimicry_status.configure(text=f"Status: Running ({profile_name})", text_color="#66BB6A")
                else:
                    messagebox.showerror("Error", "Failed to start mimicry proxy.")
                    self.mimicry_enabled_var.set(False)
            else:
                messagebox.showerror("Error", f"Profile '{profile_name}' not found.")
                self.mimicry_enabled_var.set(False)
        else:
            self.mimicry_manager.stop()
            self.mimicry_status.configure(text="Status: Stopped", text_color="gray")

    def create_mimicry_profile(self):
        """ایجاد پروفایل جدید (نسخه اولیه ساده)"""
        messagebox.showinfo("Coming Soon", "Profile editor will be available in the next update.")

    def edit_mimicry_profile(self):
        """ویرایش پروفایل (نسخه اولیه ساده)"""
        messagebox.showinfo("Coming Soon", "Profile editor will be available in the next update.")
