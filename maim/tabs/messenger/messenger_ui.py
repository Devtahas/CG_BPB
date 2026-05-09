# tabs/messenger/messenger_ui.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import random
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

from .messenger_core import MessengerServer, MessengerClient
from .messenger_utils import MessengerUtils


class MessengerUI(ctk.CTkFrame):
    """کلاس اصلی تب Messenger"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.server = None
        self.client = None
        self.is_hosting = False
        self.is_connected = False
        self.messages = []
        
        self.setup_ui()

        # ★ پشتیبانی از پلاگین‌های دسته "messenger"
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("messenger")
    
    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="💬 Secure Messenger (E2E + TLS 1.3)", 
                    font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE,
                                     segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_chat = self.tabview.add("💬 Chat")
        self.tab_host = self.tabview.add("🚀 Host Room")
        self.tab_join = self.tabview.add("🔗 Join Room")
        self.tab_settings = self.tabview.add("⚙️ Settings")
        
        self.setup_chat_tab()
        self.setup_host_tab()
        self.setup_join_tab()
        self.setup_settings_tab()
    
    def setup_chat_tab(self):
        """تب چت"""
        scroll = ctk.CTkScrollableFrame(self.tab_chat, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # نمایش پیام‌ها
        self.chat_display = ctk.CTkTextbox(scroll, height=400, font=ctk.CTkFont(size=12))
        self.chat_display.pack(fill="both", expand=True, pady=10)
        self.chat_display.configure(state="disabled")
        
        # ورودی پیام
        input_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        input_frame.pack(fill="x", pady=10)
        
        self.msg_entry = ctk.CTkEntry(input_frame, placeholder_text="Type your message...", height=40)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())
        
        self.send_btn = ctk.CTkButton(input_frame, text="Send", width=80, fg_color=CF_ORANGE,
                                     text_color="black", command=self.send_message)
        self.send_btn.pack(side="right")
        
        # وضعیت اتصال
        self.conn_status = ctk.CTkLabel(scroll, text="⚪ Not connected", text_color="gray")
        self.conn_status.pack(pady=5)
    
    def setup_host_tab(self):
        """تب هاست کردن اتاق"""
        scroll = ctk.CTkScrollableFrame(self.tab_host, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # تنظیمات سرور
        settings_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        settings_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(settings_frame, text="🏠 Room Settings", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color=CF_ORANGE).pack(pady=(15, 10))
        
        # پورت
        port_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(port_frame, text="Port:", width=100).pack(side="left")
        self.host_port = ctk.CTkEntry(port_frame, width=150, placeholder_text="8888")
        self.host_port.insert(0, "8888")
        self.host_port.pack(side="left", padx=10)
        
        # رمز اتاق (اختیاری)
        pass_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        pass_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(pass_frame, text="Room Password (optional):", width=150).pack(side="left")
        self.host_password = ctk.CTkEntry(pass_frame, width=200, placeholder_text="Leave empty for open room")
        self.host_password.pack(side="left", padx=10)
        
        # دکمه تولید رمز خودکار
        ctk.CTkButton(pass_frame, text="Generate", width=80, fg_color="transparent",
                     border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                     command=self.generate_room_password).pack(side="left", padx=5)
        
        # IP محلی
        local_ip = MessengerUtils.get_local_ip()
        ctk.CTkLabel(settings_frame, text=f"Your Local IP: {local_ip}", text_color="gray").pack(pady=10)
        
        # دکمه شروع سرور
        self.start_server_btn = ctk.CTkButton(settings_frame, text="🚀 START HOSTING", fg_color="#2E7D32",
                                             hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14),
                                             command=self.start_hosting)
        self.start_server_btn.pack(pady=20)
        
        # لاگ سرور
        self.host_log = ctk.CTkTextbox(scroll, height=150, font=ctk.CTkFont(size=11))
        self.host_log.pack(fill="x", pady=10)
    
    def setup_join_tab(self):
        """تب اتصال به اتاق"""
        scroll = ctk.CTkScrollableFrame(self.tab_join, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # تنظیمات کلاینت
        settings_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        settings_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(settings_frame, text="🔗 Connection Settings", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color=CF_ORANGE).pack(pady=(15, 10))
        
        # سرور IP
        ip_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ip_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(ip_frame, text="Server IP:", width=100).pack(side="left")
        self.join_ip = ctk.CTkEntry(ip_frame, width=200, placeholder_text="192.168.1.100")
        self.join_ip.pack(side="left", padx=10)
        
        # پورت
        port_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(port_frame, text="Port:", width=100).pack(side="left")
        self.join_port = ctk.CTkEntry(port_frame, width=150, placeholder_text="8888")
        self.join_port.insert(0, "8888")
        self.join_port.pack(side="left", padx=10)
        
        # نام کاربری
        name_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        name_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(name_frame, text="Username:", width=100).pack(side="left")
        self.join_username = ctk.CTkEntry(name_frame, width=200, placeholder_text="Your name")
        self.join_username.pack(side="left", padx=10)
        ctk.CTkButton(name_frame, text="Random", width=70, fg_color="transparent",
                     border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                     command=self.generate_random_username).pack(side="left", padx=5)
        
        # رمز اتاق
        room_pass_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        room_pass_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(room_pass_frame, text="Room Password:", width=100).pack(side="left")
        self.join_password = ctk.CTkEntry(room_pass_frame, width=200, placeholder_text="If required")
        self.join_password.pack(side="left", padx=10)
        
        # دکمه اتصال
        self.join_btn = ctk.CTkButton(settings_frame, text="🔗 CONNECT", fg_color="#2E7D32",
                                     hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14),
                                     command=self.join_room)
        self.join_btn.pack(pady=20)
        
        # وضعیت
        self.join_status = ctk.CTkLabel(scroll, text="", text_color="gray")
        self.join_status.pack()
    
    def setup_settings_tab(self):
        """تنظیمات پیشرفته"""
        scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Auto Setting Setter
        auto_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        auto_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(auto_frame, text="⚙️ Auto Setting Setter", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color="#29B6F6").pack(pady=(15, 10))
        ctk.CTkLabel(auto_frame, text="Automatically configure optimal settings for LAN/Hoster", text_color="gray").pack()
        
        self.auto_setting_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(auto_frame, text="Enable Auto Setting", variable=self.auto_setting_var,
                     progress_color=CF_ORANGE).pack(pady=10)
        
        # TLS 1.3
        tls_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        tls_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tls_frame, text="🔒 TLS 1.3", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color="#AB47BC").pack(pady=(15, 10))
        ctk.CTkLabel(tls_frame, text="Force TLS 1.3 for secure connections", text_color="gray").pack()
        
        self.tls_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(tls_frame, text="Force TLS 1.3", variable=self.tls_var,
                     progress_color=CF_ORANGE).pack(pady=10)
        
        # E2E Encryption Info
        e2e_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        e2e_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(e2e_frame, text="🔐 End-to-End Encryption", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color="#66BB6A").pack(pady=(15, 10))
        ctk.CTkLabel(e2e_frame, text="RSA 2048-bit key exchange + AES-256-GCM for messages", text_color="gray").pack()
        ctk.CTkLabel(e2e_frame, text="✅ All messages are encrypted locally before sending", text_color="gray").pack(pady=(0, 15))
    
    # ==========================================
    # Hosting Methods
    # ==========================================
    def generate_room_password(self):
        password = MessengerUtils.generate_connection_password()
        self.host_password.delete(0, "end")
        self.host_password.insert(0, password)
    
    def start_hosting(self):
        if self.is_hosting:
            self.stop_hosting()
            return
        
        try:
            port = int(self.host_port.get())
        except:
            messagebox.showerror("Error", "Invalid port number")
            return
        
        room_password = self.host_password.get().strip()
        if not room_password:
            room_password = None
        
        self.server = MessengerServer(host='0.0.0.0', port=port, log_callback=self.log_host)
        if self.server.start(room_password):
            self.is_hosting = True
            self.start_server_btn.configure(text="⏹ STOP HOSTING", fg_color="#C62828")
            self.host_log.insert("end", f"✅ Server started on port {port}\n")
            self.host_log.see("end")
            
            # نمایش اطلاعات برای اتصال در LAN
            local_ip = MessengerUtils.get_local_ip()
            self.host_log.insert("end", f"📡 Connect via: {local_ip}:{port}\n")
            if room_password:
                self.host_log.insert("end", f"🔑 Room password: {room_password}\n")
            self.host_log.see("end")
        else:
            messagebox.showerror("Error", "Failed to start server")
    
    def stop_hosting(self):
        if self.server:
            self.server.stop()
            self.server = None
        self.is_hosting = False
        self.start_server_btn.configure(text="🚀 START HOSTING", fg_color="#2E7D32")
        self.log_host("Server stopped")
    
    def log_host(self, msg):
        self.after(0, lambda: self.host_log.insert("end", f"{msg}\n"))
        self.after(0, lambda: self.host_log.see("end"))
    
    # ==========================================
    # Join Methods
    # ==========================================
    def generate_random_username(self):
        import random
        import string
        username = "User_" + ''.join(random.choices(string.digits, k=4))
        self.join_username.delete(0, "end")
        self.join_username.insert(0, username)
    
    def join_room(self):
        if self.is_connected:
            self.disconnect()
            return
        
        host = self.join_ip.get().strip()
        if not host:
            messagebox.showerror("Error", "Please enter server IP")
            return
        
        try:
            port = int(self.join_port.get())
        except:
            messagebox.showerror("Error", "Invalid port")
            return
        
        username = self.join_username.get().strip()
        if not username:
            username = "Anonymous"
        
        room_password = self.join_password.get().strip()
        if not room_password:
            room_password = None
        
        self.client = MessengerClient(log_callback=self.log_join, message_callback=self.on_message)
        
        if self.client.connect(host, port, username, room_password):
            self.is_connected = True
            self.join_btn.configure(text="⏹ DISCONNECT", fg_color="#C62828")
            self.conn_status.configure(text="🟢 Connected", text_color="#66BB6A")
            self.send_btn.configure(state="normal")
            self.msg_entry.configure(state="normal")
        else:
            self.client = None
            messagebox.showerror("Error", "Failed to connect to server")
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.client = None
        self.is_connected = False
        self.join_btn.configure(text="🔗 CONNECT", fg_color="#2E7D32")
        self.conn_status.configure(text="⚪ Not connected", text_color="gray")
        self.send_btn.configure(state="disabled")
        self.msg_entry.configure(state="disabled")
    
    def log_join(self, msg):
        self.after(0, lambda: self.join_status.configure(text=msg, text_color=CF_ORANGE))
        self.after(2000, lambda: self.join_status.configure(text=""))
    
    def on_message(self, username, message, timestamp):
        """دریافت پیام جدید"""
        import time
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp)) if timestamp else ""
        self.messages.append((username, message))
        
        self.after(0, lambda: self.chat_display.configure(state="normal"))
        if username == "🔔 SYSTEM":
            self.after(0, lambda: self.chat_display.insert("end", f"\n[{time_str}] {message}\n", "system"))
        elif username.startswith("[PV]"):
            self.after(0, lambda: self.chat_display.insert("end", f"\n[{time_str}] {username}: {message}\n", "private"))
        else:
            self.after(0, lambda: self.chat_display.insert("end", f"\n[{time_str}] {username}: {message}\n", "normal"))
        self.after(0, lambda: self.chat_display.see("end"))
        self.after(0, lambda: self.chat_display.configure(state="disabled"))
    
    def send_message(self):
        if not self.is_connected or not self.client:
            return
        
        message = self.msg_entry.get().strip()
        if not message:
            return
        
        if message.startswith("/pv "):
            # پیام خصوصی: /pv username message
            parts = message.split(" ", 2)
            if len(parts) >= 3:
                target = parts[1]
                msg = parts[2]
                self.client.send_message(msg, target)
                self.after(0, lambda: self.chat_display.configure(state="normal"))
                self.after(0, lambda: self.chat_display.insert("end", f"\n[You → {target}]: {msg}\n", "private"))
                self.after(0, lambda: self.chat_display.see("end"))
                self.after(0, lambda: self.chat_display.configure(state="disabled"))
        else:
            self.client.send_message(message)
            self.after(0, lambda: self.chat_display.configure(state="normal"))
            self.after(0, lambda: self.chat_display.insert("end", f"\n[You]: {message}\n", "self"))
            self.after(0, lambda: self.chat_display.see("end"))
            self.after(0, lambda: self.chat_display.configure(state="disabled"))
        
        self.msg_entry.delete(0, "end")

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
