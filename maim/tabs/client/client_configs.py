# tabs/client/client_configs.py
import os
import json
import time
import urllib.parse
from tkinter import messagebox
import customtkinter as ctk
from config import CF_ORANGE, BG_PANEL
from tabs.crypto_manager import storage_crypto


class ConfigEditDialog(ctk.CTkToplevel):
    """پنجره ویرایش کانفیگ"""

    def __init__(self, parent, config_path, config_data, on_save_callback):
        super().__init__(parent)
        self.parent = parent
        self.config_path = config_path
        self.config_data = config_data
        self.on_save_callback = on_save_callback

        self.title("Edit Configuration")
        self.geometry("650x750")
        self.attributes("-topmost", True)
        self.configure(fg_color=BG_PANEL)

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ctk.CTkLabel(self, text="✏️ Edit Configuration",
                              font=ctk.CTkFont(size=20, weight="bold"),
                              text_color=CF_ORANGE)
        header.pack(pady=(20, 10))

        # Scrollable frame for fields
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        outbound = self.config_data.get("outbounds", [{}])[0]
        protocol = outbound.get("protocol", "unknown")

        # نمایش نوع پروتکل
        protocol_label = ctk.CTkLabel(scroll, text=f"Protocol: {protocol.upper()}",
                                      font=ctk.CTkFont(size=16, weight="bold"),
                                      text_color=CF_ORANGE)
        protocol_label.pack(anchor="w", pady=(0, 15))

        # Remark (نام کانفیگ)
        remark_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        remark_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(remark_frame, text="Remark (Name):", width=130, anchor="w").pack(side="left")
        self.remark_entry = ctk.CTkEntry(remark_frame, width=420)
        self.remark_entry.pack(side="left", padx=10)
        self.remark_entry.insert(0, self.config_data.get("remarks", ""))

        # فیلدهای عمومی بر اساس پروتکل
        if protocol == "vless":
            self._add_vless_fields(scroll, outbound)
        elif protocol == "vmess":
            self._add_vmess_fields(scroll, outbound)
        elif protocol == "shadowsocks":
            self._add_ss_fields(scroll, outbound)
        elif protocol == "trojan":
            self._add_trojan_fields(scroll, outbound)
        elif protocol == "hysteria2":
            self._add_hysteria2_fields(scroll, outbound)
        elif protocol == "tuic":
            self._add_tuic_fields(scroll, outbound)
        elif protocol == "wireguard":
            self._add_wireguard_fields(scroll, outbound)
        elif protocol == "socks":
            self._add_socks_fields(scroll, outbound)
        elif protocol == "http":
            self._add_http_fields(scroll, outbound)
        else:
            # پروتکل ناشناس
            ctk.CTkLabel(scroll, text=f"Editing not supported for protocol: {protocol}",
                        text_color="red").pack(pady=20)

        # دکمه‌های Save و Cancel
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="💾 Save", fg_color="#2E7D32", hover_color="#1B5E20",
                     width=120, command=self.save_config).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", hover_color="#555",
                     width=120, command=self.destroy).pack(side="left", padx=10)

    def _add_vless_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل VLESS"""
        settings = outbound.get("settings", {})
        vnext = settings.get("vnext", [{}])[0]
        user = vnext.get("users", [{}])[0]
        stream = outbound.get("streamSettings", {})

        fields = [
            ("Server Address:", vnext.get("address", ""), "address"),
            ("Port:", str(vnext.get("port", 443)), "port"),
            ("UUID:", user.get("id", ""), "uuid"),
            ("Flow:", user.get("flow", ""), "flow"),
            ("Encryption:", user.get("encryption", "none"), "encryption"),
            ("Network (tcp/ws/grpc):", stream.get("network", "tcp"), "network"),
            ("Security (none/tls/reality):", stream.get("security", "none"), "security"),
            ("Path (for ws/grpc):", "", "path"),
            ("Host (for ws):", "", "host"),
            ("SNI:", "", "sni"),
            ("Fingerprint:", "", "fingerprint"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

        # فیلدهای اضافی برای ws/grpc
        ws_settings = stream.get("wsSettings", {})
        grpc_settings = stream.get("grpcSettings", {})
        tls_settings = stream.get("tlsSettings", {})
        reality_settings = stream.get("realitySettings", {})

        self.entries["path"].insert(0, ws_settings.get("path", grpc_settings.get("serviceName", "")))
        self.entries["host"].insert(0, ws_settings.get("headers", {}).get("Host", ""))
        self.entries["sni"].insert(0, tls_settings.get("serverName", reality_settings.get("serverName", "")))
        self.entries["fingerprint"].insert(0, tls_settings.get("fingerprint", reality_settings.get("fingerprint", "chrome")))

    def _add_vmess_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل VMESS"""
        settings = outbound.get("settings", {})
        vnext = settings.get("vnext", [{}])[0]
        user = vnext.get("users", [{}])[0]
        stream = outbound.get("streamSettings", {})

        fields = [
            ("Server Address:", vnext.get("address", ""), "address"),
            ("Port:", str(vnext.get("port", 443)), "port"),
            ("UUID:", user.get("id", ""), "uuid"),
            ("Security:", user.get("security", "auto"), "security"),
            ("Alter ID:", str(user.get("alterId", 0)), "alterId"),
            ("Network (tcp/ws/grpc):", stream.get("network", "tcp"), "network"),
            ("Path:", "", "path"),
            ("Host:", "", "host"),
            ("TLS (none/tls):", stream.get("security", "none"), "security_type"),
            ("SNI:", "", "sni"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

        # پر کردن فیلدهای اضافی
        ws_settings = stream.get("wsSettings", {})
        tls_settings = stream.get("tlsSettings", {})
        self.entries["path"].insert(0, ws_settings.get("path", ""))
        self.entries["host"].insert(0, ws_settings.get("headers", {}).get("Host", ""))
        self.entries["sni"].insert(0, tls_settings.get("serverName", ""))

    def _add_ss_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل Shadowsocks"""
        settings = outbound.get("settings", {})
        server = settings.get("servers", [{}])[0]

        fields = [
            ("Server Address:", server.get("address", ""), "address"),
            ("Port:", str(server.get("port", 443)), "port"),
            ("Method:", server.get("method", "chacha20-ietf-poly1305"), "method"),
            ("Password:", server.get("password", ""), "password"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

    def _add_trojan_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل Trojan"""
        settings = outbound.get("settings", {})
        server = settings.get("servers", [{}])[0]
        stream = outbound.get("streamSettings", {})

        fields = [
            ("Server Address:", server.get("address", ""), "address"),
            ("Port:", str(server.get("port", 443)), "port"),
            ("Password:", server.get("password", ""), "password"),
            ("SNI:", "", "sni"),
            ("Fingerprint:", "", "fingerprint"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

        tls_settings = stream.get("tlsSettings", {})
        self.entries["sni"].insert(0, tls_settings.get("serverName", ""))
        self.entries["fingerprint"].insert(0, tls_settings.get("fingerprint", "chrome"))

    def _add_hysteria2_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل Hysteria2"""
        settings = outbound.get("settings", {})

        fields = [
            ("Server Address:", settings.get("address", ""), "address"),
            ("Port:", str(settings.get("port", 443)), "port"),
            ("Password:", settings.get("password", ""), "password"),
            ("SNI:", settings.get("sni", ""), "sni"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

    def _add_tuic_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل TUIC"""
        settings = outbound.get("settings", {})

        fields = [
            ("Server Address:", settings.get("address", ""), "address"),
            ("Port:", str(settings.get("port", 443)), "port"),
            ("UUID:", settings.get("uuid", ""), "uuid"),
            ("Password:", settings.get("password", ""), "password"),
            ("SNI:", settings.get("sni", ""), "sni"),
            ("Congestion Control:", settings.get("congestion_control", "bbr"), "congestion"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

    def _add_wireguard_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل WireGuard"""
        settings = outbound.get("settings", {})
        peer = settings.get("peers", [{}])[0]

        fields = [
            ("Local Address:", settings.get("address", ""), "address"),
            ("Private Key:", settings.get("private_key", ""), "private_key"),
            ("Peer Address:", peer.get("address", ""), "peer_address"),
            ("Peer Port:", str(peer.get("port", 51820)), "peer_port"),
            ("Peer Public Key:", peer.get("public_key", ""), "peer_key"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

    def _add_socks_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل SOCKS"""
        settings = outbound.get("settings", {})
        server = settings.get("servers", [{}])[0]

        fields = [
            ("Server Address:", server.get("address", ""), "address"),
            ("Port:", str(server.get("port", 1080)), "port"),
            ("Username:", "", "username"),
            ("Password:", "", "password"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

        users = server.get("users", [{}])[0] if server.get("users") else {}
        self.entries["username"].insert(0, users.get("user", ""))
        self.entries["password"].insert(0, users.get("pass", ""))

    def _add_http_fields(self, parent, outbound):
        """فیلدهای ویرایش برای پروتکل HTTP"""
        settings = outbound.get("settings", {})
        server = settings.get("servers", [{}])[0]

        fields = [
            ("Server Address:", server.get("address", ""), "address"),
            ("Port:", str(server.get("port", 8080)), "port"),
            ("Username:", "", "username"),
            ("Password:", "", "password"),
        ]

        self.entries = {}
        for label, default, key in fields:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, default)
            self.entries[key] = entry

        users = server.get("users", [{}])[0] if server.get("users") else {}
        self.entries["username"].insert(0, users.get("user", ""))
        self.entries["password"].insert(0, users.get("pass", ""))

    def save_config(self):
        """ذخیره تغییرات در فایل JSON (رمزنگاری شده)"""
        try:
            outbound = self.config_data.get("outbounds", [{}])[0]
            protocol = outbound.get("protocol", "unknown")

            # ذخیره Remark
            self.config_data["remarks"] = self.remark_entry.get()

            # ذخیره بر اساس پروتکل
            if protocol == "vless":
                self._save_vless_config(outbound)
            elif protocol == "vmess":
                self._save_vmess_config(outbound)
            elif protocol == "shadowsocks":
                self._save_ss_config(outbound)
            elif protocol == "trojan":
                self._save_trojan_config(outbound)
            elif protocol == "hysteria2":
                self._save_hysteria2_config(outbound)
            elif protocol == "tuic":
                self._save_tuic_config(outbound)
            elif protocol == "wireguard":
                self._save_wireguard_config(outbound)
            elif protocol == "socks":
                self._save_socks_config(outbound)
            elif protocol == "http":
                self._save_http_config(outbound)

            # ذخیره در فایل با رمزنگاری
            storage_crypto.save_json(self.config_path, self.config_data)

            messagebox.showinfo("Success", "Configuration saved successfully!")
            self.on_save_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{str(e)}")

    def _save_vless_config(self, outbound):
        """ذخیره VLESS config"""
        vnext = outbound.setdefault("settings", {}).setdefault("vnext", [{}])[0]
        user = vnext.setdefault("users", [{}])[0]
        stream = outbound.setdefault("streamSettings", {})

        vnext["address"] = self.entries["address"].get()
        vnext["port"] = int(self.entries["port"].get())
        user["id"] = self.entries["uuid"].get()
        user["flow"] = self.entries["flow"].get()
        user["encryption"] = self.entries["encryption"].get()

        stream["network"] = self.entries["network"].get()
        stream["security"] = self.entries["security"].get()

        # تنظیم ws/grpc settings
        net_type = self.entries["network"].get()
        if net_type == "ws":
            ws_settings = stream.setdefault("wsSettings", {})
            ws_settings["path"] = self.entries["path"].get()
            ws_settings["headers"] = {"Host": self.entries["host"].get()}
        elif net_type == "grpc":
            grpc_settings = stream.setdefault("grpcSettings", {})
            grpc_settings["serviceName"] = self.entries["path"].get()

        # تنظیم TLS/Reality
        if stream["security"] == "tls":
            tls_settings = stream.setdefault("tlsSettings", {})
            tls_settings["serverName"] = self.entries["sni"].get()
            tls_settings["fingerprint"] = self.entries["fingerprint"].get()
        elif stream["security"] == "reality":
            reality_settings = stream.setdefault("realitySettings", {})
            reality_settings["serverName"] = self.entries["sni"].get()
            reality_settings["fingerprint"] = self.entries["fingerprint"].get()

    def _save_vmess_config(self, outbound):
        """ذخیره VMESS config"""
        vnext = outbound.setdefault("settings", {}).setdefault("vnext", [{}])[0]
        user = vnext.setdefault("users", [{}])[0]
        stream = outbound.setdefault("streamSettings", {})

        vnext["address"] = self.entries["address"].get()
        vnext["port"] = int(self.entries["port"].get())
        user["id"] = self.entries["uuid"].get()
        user["security"] = self.entries["security"].get()
        user["alterId"] = int(self.entries["alterId"].get())

        stream["network"] = self.entries["network"].get()
        stream["security"] = self.entries["security_type"].get()

        if stream["network"] == "ws":
            ws_settings = stream.setdefault("wsSettings", {})
            ws_settings["path"] = self.entries["path"].get()
            ws_settings["headers"] = {"Host": self.entries["host"].get()}

        if stream["security"] == "tls":
            tls_settings = stream.setdefault("tlsSettings", {})
            tls_settings["serverName"] = self.entries["sni"].get()

    def _save_ss_config(self, outbound):
        """ذخیره Shadowsocks config"""
        servers = outbound.setdefault("settings", {}).setdefault("servers", [{}])[0]
        servers["address"] = self.entries["address"].get()
        servers["port"] = int(self.entries["port"].get())
        servers["method"] = self.entries["method"].get()
        servers["password"] = self.entries["password"].get()

    def _save_trojan_config(self, outbound):
        """ذخیره Trojan config"""
        servers = outbound.setdefault("settings", {}).setdefault("servers", [{}])[0]
        stream = outbound.setdefault("streamSettings", {})

        servers["address"] = self.entries["address"].get()
        servers["port"] = int(self.entries["port"].get())
        servers["password"] = self.entries["password"].get()

        tls_settings = stream.setdefault("tlsSettings", {})
        tls_settings["serverName"] = self.entries["sni"].get()
        tls_settings["fingerprint"] = self.entries["fingerprint"].get()

    def _save_hysteria2_config(self, outbound):
        """ذخیره Hysteria2 config"""
        settings = outbound.setdefault("settings", {})
        settings["address"] = self.entries["address"].get()
        settings["port"] = int(self.entries["port"].get())
        settings["password"] = self.entries["password"].get()
        if self.entries["sni"].get():
            settings["sni"] = self.entries["sni"].get()

    def _save_tuic_config(self, outbound):
        """ذخیره TUIC config"""
        settings = outbound.setdefault("settings", {})
        settings["address"] = self.entries["address"].get()
        settings["port"] = int(self.entries["port"].get())
        settings["uuid"] = self.entries["uuid"].get()
        settings["password"] = self.entries["password"].get()
        settings["congestion_control"] = self.entries["congestion"].get()
        if self.entries["sni"].get():
            settings["sni"] = self.entries["sni"].get()

    def _save_wireguard_config(self, outbound):
        """ذخیره WireGuard config"""
        settings = outbound.setdefault("settings", {})
        peer = settings.setdefault("peers", [{}])[0]

        settings["address"] = self.entries["address"].get()
        settings["private_key"] = self.entries["private_key"].get()
        peer["address"] = self.entries["peer_address"].get()
        peer["port"] = int(self.entries["peer_port"].get())
        peer["public_key"] = self.entries["peer_key"].get()

    def _save_socks_config(self, outbound):
        """ذخیره SOCKS config"""
        servers = outbound.setdefault("settings", {}).setdefault("servers", [{}])[0]
        servers["address"] = self.entries["address"].get()
        servers["port"] = int(self.entries["port"].get())

        if self.entries["username"].get():
            servers["users"] = [{"user": self.entries["username"].get(), "pass": self.entries["password"].get()}]
        elif "users" in servers:
            del servers["users"]

    def _save_http_config(self, outbound):
        """ذخیره HTTP config"""
        servers = outbound.setdefault("settings", {}).setdefault("servers", [{}])[0]
        servers["address"] = self.entries["address"].get()
        servers["port"] = int(self.entries["port"].get())

        if self.entries["username"].get():
            servers["users"] = [{"user": self.entries["username"].get(), "pass": self.entries["password"].get()}]
        elif "users" in servers:
            del servers["users"]


class ClientConfigs:
    """مدیریت لیست کانفیگ‌ها - لود، حذف، انتخاب، ویرایش، و Revive"""

    def __init__(self, parent, configs_dir, scroll_area):
        self.parent = parent
        self.configs_dir = configs_dir
        self.scroll_area = scroll_area
        self.config_buttons = []
        self.selected_config_path = None
        self.is_connected = False
        self.on_select_callback = None
        self.on_delete_callback = None
        self.on_edit_callback = None

    def set_callbacks(self, on_select, on_delete, on_edit, is_connected_func):
        self.on_select_callback = on_select
        self.on_delete_callback = on_delete
        self.on_edit_callback = on_edit
        self.is_connected = is_connected_func() if callable(is_connected_func) else False

    def load_configs(self):
        """بارگذاری لیست کانفیگ‌ها (با پشتیبانی از رمزنگاری)"""
        for widget in self.scroll_area.winfo_children():
            widget.destroy()
        self.config_buttons.clear()

        if not os.path.exists(self.configs_dir):
            return

        files = [f for f in os.listdir(self.configs_dir) if f.endswith('.json')]
        if not files:
            return

        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.configs_dir, x)), reverse=True)

        for file in files:
            path = os.path.join(self.configs_dir, file)
            remark_name = file
            protocol = "unknown"
            try:
                # بارگذاری با رمزنگاری (fallback به فایل معمولی)
                data = storage_crypto.load_json(path)
                if data is None:
                    # تلاش برای بارگذاری از فایل معمولی (برای مهاجرت)
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # رمزنگاری و ذخیره مجدد
                        storage_crypto.save_json(path, data)
                remark_name = data.get('remarks', file)
                outbound = data.get("outbounds", [{}])[0]
                protocol = outbound.get("protocol", "unknown").upper()
            except:
                pass

            row_frame = ctk.CTkFrame(self.scroll_area, fg_color=BG_PANEL, corner_radius=8)
            row_frame.pack(fill="x", padx=10, pady=5)
            row_frame.grid_columnconfigure(0, weight=1)

            # دکمه انتخاب کانفیگ
            btn_text = f"[{protocol}] {remark_name}" if protocol != "unknown" else remark_name
            btn = ctk.CTkButton(row_frame, text=btn_text, fg_color="transparent",
                               text_color="white", hover_color="#332015", anchor="w",
                               command=lambda p=path, rf=row_frame: self.select_config(p, rf))
            btn.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

            # لیبل پینگ
            lbl_ping = ctk.CTkLabel(row_frame, text="-- ms", width=60, text_color="gray", font=ctk.CTkFont(weight="bold"))
            lbl_ping.grid(row=0, column=1, padx=10, pady=5)

            # دکمه ویرایش (مداد)
            btn_edit = ctk.CTkButton(row_frame, text="✏️", width=35, fg_color="transparent",
                                    text_color="#29B6F6", hover_color="#0D47A1",
                                    command=lambda p=path: self.edit_config(p))
            btn_edit.grid(row=0, column=2, padx=2, pady=5)

            # دکمه حذف
            btn_del = ctk.CTkButton(row_frame, text="🗑️", width=35, fg_color="transparent",
                                   text_color="#EF5350", hover_color="#3A1D1D",
                                   command=lambda p=path: self.delete_config(p))
            btn_del.grid(row=0, column=3, padx=5, pady=5)

            # دکمه Revive (جدید)
            btn_revive = ctk.CTkButton(row_frame, text="🔄", width=35, fg_color="transparent",
                                      text_color="#66BB6A", hover_color="#1B5E20",
                                      command=lambda p=path: self.revive_config(p))
            btn_revive.grid(row=0, column=4, padx=2, pady=5)

            self.config_buttons.append({
                "frame": row_frame,
                "path": path,
                "lbl_ping": lbl_ping,
                "protocol": protocol
            })

    def revive_config(self, path):
        """
        بازسازی کانفیگ با جایگزینی SNI با SNI پروفایل فعال Traffic Mimicry
        (برای سازگاری با فیلترینگ وایت‌لیست)
        """
        if self.is_connected and self.selected_config_path == path:
            messagebox.showwarning("Warning", "Cannot revive active config.\nDisconnect first!")
            return

        try:
            # بارگذاری کانفیگ اصلی
            with open(path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # دسترسی به mimicry_manager از طریق parent (ClientUI)
            mimicry_manager = None
            if hasattr(self.parent, 'mimicry_manager'):
                mimicry_manager = self.parent.mimicry_manager

            fake_sni = "www.aparat.com"  # پیش‌فرض
            if mimicry_manager and mimicry_manager.current_profile:
                profile = mimicry_manager.current_profile
                fake_sni = profile.tls.server_name or fake_sni

            # پیدا کردن outbound اصلی و تغییر SNI
            outbound = None
            for ob in config_data.get('outbounds', []):
                if ob.get('protocol') in ['vless', 'vmess', 'trojan']:
                    outbound = ob
                    break
            if not outbound:
                outbound = config_data['outbounds'][0]

            if 'streamSettings' not in outbound:
                outbound['streamSettings'] = {}
            if 'tlsSettings' not in outbound['streamSettings']:
                outbound['streamSettings']['tlsSettings'] = {}
            outbound['streamSettings']['tlsSettings']['serverName'] = fake_sni
            outbound['streamSettings']['tlsSettings']['fingerprint'] = 'chrome'

            # تغییر نام
            old_remarks = config_data.get('remarks', 'Config')
            config_data['remarks'] = f"[Revived] {old_remarks}"

            # ذخیره کانفیگ جدید
            new_filename = f"Revived_{int(time.time())}_{os.path.basename(path)}"
            new_path = os.path.join(self.configs_dir, new_filename)
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Success", f"Config revived with SNI: {fake_sni}\nSaved as: {new_filename}")
            self.load_configs()  # به‌روزرسانی لیست

        except Exception as e:
            messagebox.showerror("Error", f"Failed to revive config:\n{str(e)}")

    def edit_config(self, path):
        """ویرایش کانفیگ"""
        if self.is_connected and self.selected_config_path == path:
            messagebox.showwarning("Warning", "Cannot edit active config.\nDisconnect first!")
            return

        try:
            # بارگذاری با رمزنگاری
            config_data = storage_crypto.load_json(path)
            if config_data is None:
                with open(path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

            ConfigEditDialog(self.parent, path, config_data, self.load_configs)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config for editing:\n{str(e)}")

    def select_config(self, path, frame_widget):
        """انتخاب یک کانفیگ"""
        if self.is_connected:
            messagebox.showwarning("Warning", "Disconnect first before changing the server.")
            return
        self.selected_config_path = path
        for item in self.config_buttons:
            if item["path"] == path:
                item["frame"].configure(border_width=2, border_color=CF_ORANGE)
            else:
                item["frame"].configure(border_width=0)
        if self.on_select_callback:
            self.on_select_callback(path)

    def delete_config(self, path):
        """حذف یک کانفیگ"""
        if self.is_connected and self.selected_config_path == path:
            messagebox.showwarning("Warning", "Cannot delete active config.\nDisconnect first!")
            return
        if messagebox.askyesno("Delete", "Delete this config?"):
            # حذف فایل اصلی و فایل رمزنگاری شده (در صورت وجود)
            if os.path.exists(path):
                os.remove(path)
            enc_path = path + '.enc'
            if os.path.exists(enc_path):
                os.remove(enc_path)
            self.load_configs()
            if self.on_delete_callback:
                self.on_delete_callback(path)

    def update_ping(self, path, text, color):
        """به‌روزرسانی مقدار پینگ برای یک کانفیگ"""
        for item in self.config_buttons:
            if item["path"] == path:
                item["lbl_ping"].configure(text=text, text_color=color)
                break

    def sort_by_ping(self):
        """مرتب‌سازی کانفیگ‌ها بر اساس پینگ"""
        if not self.config_buttons:
            return

        def get_ping_val(item):
            txt = item["lbl_ping"].cget("text")
            try:
                if "ms" in txt and "--" not in txt:
                    return int(txt.replace(" ms", "").strip())
                return 999999
            except:
                return 999999

        self.config_buttons.sort(key=get_ping_val)

        for item in self.config_buttons:
            item["frame"].pack_forget()
            item["frame"].pack(fill="x", padx=10, pady=5)

    def get_selected_config(self):
        return self.selected_config_path
