# tab_dns.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import socket
import subprocess
import json
import os
import ctypes
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# اضافه شدن DIRS به لیست ایمپورت‌ها
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK, DIRS

# ترکیب لیست DNSهای کلاسیک (IPv4) و امن (DoH)
DEFAULT_DNS_LIST =[
    {"name": "Google", "primary": "8.8.8.8", "secondary": "8.8.4.4", "type": "IPv4"},
    {"name": "Google (DoH)", "primary": "https://dns.google/dns-query", "secondary": "", "type": "DoH"},
    {"name": "Cloudflare", "primary": "1.1.1.1", "secondary": "1.0.0.1", "type": "IPv4"},
    {"name": "Cloudflare (DoH)", "primary": "https://cloudflare-dns.com/dns-query", "secondary": "", "type": "DoH"},
    {"name": "Electro (IR)", "primary": "78.157.42.100", "secondary": "78.157.42.101", "type": "IPv4"},
    {"name": "Shecan (IR)", "primary": "178.22.122.100", "secondary": "185.51.200.2", "type": "IPv4"},
    {"name": "Radar Game (IR)", "primary": "10.202.10.10", "secondary": "10.202.10.11", "type": "IPv4"},
    {"name": "Quad9 (DoH)", "primary": "https://dns.quad9.net/dns-query", "secondary": "", "type": "DoH"}
]

# ==========================================
# مینی سرور پروکسی محلی برای هندل کردن DoH
# ==========================================
class LocalDoHServer:
    def __init__(self, doh_url):
        self.doh_url = doh_url
        self.running = False
        self.sock = None
        self.bound_ip = None
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.session = requests.Session() # برای سرعت بخشیدن به درخواست‌های HTTPS متوالی

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # جستجو برای یک آی‌پی لوکال آزاد در رنج 127.0.0.x برای جلوگیری از تداخل با سایر برنامه‌ها
        for i in range(1, 15):
            ip = f'127.0.0.{i}'
            try:
                self.sock.bind((ip, 53))
                self.bound_ip = ip
                break
            except OSError:
                continue
                
        if not self.bound_ip:
            return False
            
        threading.Thread(target=self._listen, daemon=True).start()
        return True

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self.executor.submit(self._handle_request, data, addr)
            except Exception:
                break

    def _handle_request(self, data, addr):
        try:
            headers = {
                'Accept': 'application/dns-message',
                'Content-Type': 'application/dns-message'
            }
            # ارسال درخواست DNS به صورت رمزنگاری شده (HTTPS)
            resp = self.session.post(self.doh_url, data=data, headers=headers, timeout=3, verify=False)
            if resp.status_code == 200 and self.running and self.sock:
                self.sock.sendto(resp.content, addr)
        except Exception:
            pass

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception: pass
        self.executor.shutdown(wait=False)

# ==========================================
# فریم اصلی DNS Changer
# ==========================================
class DNSChangerFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # تغییر مسیر فایل تنظیمات DNS به پوشه مرکزی Settings
        self.dns_file = os.path.join(DIRS["settings"], "NetTools_DNS.json")
        
        self.dns_list = self.load_dns_list()
        self.is_connected = False
        self.doh_server_instance = None
        self.active_interface = self.get_active_network_interface()
        self.current_full_addr = ""

        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🌍 Advanced DNS Changer", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)
        ctk.CTkButton(header_frame, text="🔄 Refresh Network", fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.refresh_interface).pack(side="right", padx=40)

        # --- Main Layout ---
        main_layout = ctk.CTkFrame(self, fg_color="transparent")
        main_layout.grid(row=1, column=0, padx=40, pady=20, sticky="nsew")
        main_layout.grid_columnconfigure(0, weight=1)
        main_layout.grid_columnconfigure(1, weight=2)

        # === LEFT SIDE: Power Button ===
        left_frame = ctk.CTkFrame(main_layout, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=20)
        
        self.btn_power = ctk.CTkButton(left_frame, text="OFF", font=ctk.CTkFont(size=38, weight="bold"), 
                                       width=160, height=160, corner_radius=80, 
                                       fg_color="#37474F", hover_color="#455A64", 
                                       command=self.toggle_dns)
        self.btn_power.pack(expand=True, pady=(20, 10))

        self.lbl_status = ctk.CTkLabel(left_frame, text="Disconnected", font=ctk.CTkFont(size=20, weight="bold"), text_color="gray")
        self.lbl_status.pack()

        # === RIGHT SIDE: Info Card ===
        right_frame = ctk.CTkFrame(main_layout, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=20)
        
        select_frame = ctk.CTkFrame(right_frame, fg_color=BG_PANEL, corner_radius=20)
        select_frame.pack(fill="x", pady=(20, 10), ipady=10)
        
        self.combo_dns = ctk.CTkComboBox(select_frame, values=[d["name"] for d in self.dns_list], width=280, font=ctk.CTkFont(size=14), dropdown_fg_color=BG_DARK, command=self.on_dns_select)
        self.combo_dns.pack(pady=10)
        self.combo_dns.set(self.dns_list[0]["name"])

        # Info Box 
        info_box = ctk.CTkFrame(right_frame, fg_color=BG_PANEL, corner_radius=20)
        info_box.pack(fill="both", expand=True, pady=10)
        info_box.grid_columnconfigure((0, 1), weight=1)
        info_box.grid_rowconfigure((0, 1, 2, 3), weight=1)

        # Name & Type
        ctk.CTkLabel(info_box, text="Name & Protocol", text_color="gray", font=ctk.CTkFont(size=13)).grid(row=0, column=0, pady=(20, 0))
        self.lbl_info_name = ctk.CTkLabel(info_box, text="--", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_info_name.grid(row=1, column=0, pady=(0, 20))

        # Ping
        ctk.CTkLabel(info_box, text="Ping Test", text_color="gray", font=ctk.CTkFont(size=13)).grid(row=0, column=1, pady=(20, 0))
        self.lbl_info_ping = ctk.CTkLabel(info_box, text="-- ms", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_info_ping.grid(row=1, column=1, pady=(0, 20))

        # Address/URL
        ctk.CTkLabel(info_box, text="Address / URL", text_color="gray", font=ctk.CTkFont(size=13)).grid(row=2, column=0, pady=(10, 0))
        addr_frame = ctk.CTkFrame(info_box, fg_color="transparent")
        addr_frame.grid(row=3, column=0, pady=(0, 20))
        self.lbl_info_addr = ctk.CTkLabel(addr_frame, text="--", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_info_addr.pack(side="left")
        ctk.CTkButton(addr_frame, text="📋", width=30, fg_color="transparent", hover_color="#332015", text_color=CF_ORANGE, command=self.copy_dns).pack(side="left", padx=5)

        # Network Interface
        ctk.CTkLabel(info_box, text="Network Adapter", text_color="gray", font=ctk.CTkFont(size=13)).grid(row=2, column=1, pady=(10, 0))
        self.lbl_info_net = ctk.CTkLabel(info_box, text=f"🟢 {self.active_interface}", font=ctk.CTkFont(size=14, weight="bold"), text_color="#66BB6A")
        self.lbl_info_net.grid(row=3, column=1, pady=(0, 20))

        # Actions
        action_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(action_frame, text="➕ Add Custom", fg_color="transparent", border_width=1, border_color="#29B6F6", text_color="#29B6F6", hover_color="#0D47A1", command=self.open_add_dialog).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(action_frame, text="🗑️ Delete", fg_color="transparent", border_width=1, border_color="#EF5350", text_color="#EF5350", hover_color="#3A1D1D", command=self.delete_dns).pack(side="right", expand=True, padx=5)

        self.on_dns_select(self.combo_dns.get())

    # ==========================================
    # شناسایی شبکه، کپی و مدیریت استیت
    # ==========================================
    def get_active_network_interface(self):
        if not HAS_PSUTIL: return "Wi-Fi"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address == local_ip:
                        return interface
        except: pass
        return "Wi-Fi"

    def refresh_interface(self):
        self.active_interface = self.get_active_network_interface()
        self.lbl_info_net.configure(text=f"🟢 {self.active_interface}")

    def copy_dns(self):
        self.clipboard_clear()
        self.clipboard_append(self.current_full_addr)
        self.update()

    def on_dns_select(self, choice):
        selected = next((d for d in self.dns_list if d["name"] == choice), None)
        if selected:
            is_doh = selected.get("type", "IPv4") == "DoH"
            protocol_badge = " [DoH 🔒]" if is_doh else " [IPv4 🌐]"
            
            self.lbl_info_name.configure(text=selected["name"] + protocol_badge)
            
            # خلاصه کردن آدرس‌های طولانی
            self.current_full_addr = selected["primary"]
            disp_addr = self.current_full_addr if len(self.current_full_addr) < 22 else self.current_full_addr[:19] + "..."
            self.lbl_info_addr.configure(text=disp_addr)
            
            self.lbl_info_ping.configure(text="Testing...", text_color="gray")
            
            if self.is_connected:
                self.disconnect_dns(update_ui=False)
                self.is_connected = False
                self.update_power_button()

            threading.Thread(target=self._ping_dns, args=(selected["primary"], is_doh), daemon=True).start()

    def _ping_dns(self, target, is_doh):
        start = time.time()
        try:
            if is_doh:
                requests.get(target, timeout=2.0, verify=False) # پینگ بر اساس پاسخ HTTP
            else:
                socket.create_connection((target, 53), timeout=2.0).close() # پینگ بر اساس پورت 53 UDP/TCP
            
            ping_ms = int((time.time() - start) * 1000)
            color = "#66BB6A" if ping_ms < 100 else ("#FFA726" if ping_ms < 250 else "#EF5350")
            self.after(0, lambda: self.lbl_info_ping.configure(text=f"📊 {ping_ms} ms", text_color=color))
        except Exception:
            self.after(0, lambda: self.lbl_info_ping.configure(text="Timeout", text_color="#EF5350"))

    # ==========================================
    # هسته تغییر DNS
    # ==========================================
    def is_admin(self):
        try: return ctypes.windll.shell32.IsUserAnAdmin()
        except: return False

    def toggle_dns(self):
        if not self.is_admin():
            messagebox.showerror("Admin Required", "Changing system DNS requires Administrator privileges!\n\nPlease Run the app as Administrator.")
            return

        if not self.is_connected: self.connect_dns()
        else: self.disconnect_dns()

    def connect_dns(self):
        choice = self.combo_dns.get()
        selected = next((d for d in self.dns_list if d["name"] == choice), None)
        if not selected: return

        self.btn_power.configure(state="disabled")
        self.lbl_status.configure(text="Connecting...")
        threading.Thread(target=self._apply_dns_thread, args=(selected,), daemon=True).start()

    def _apply_dns_thread(self, dns_data):
        try:
            adapter = self.active_interface
            primary = dns_data["primary"]
            is_doh = dns_data.get("type", "IPv4") == "DoH"

            # 1. اگر DoH بود، سرور محلی را اجرا کن
            if is_doh:
                self.doh_server_instance = LocalDoHServer(primary)
                if not self.doh_server_instance.start():
                    raise Exception("Local Proxy Port 53 is busy.")
                
                # به ویندوز می‌گوییم به آی‌پی لوکال ما وصل شود
                setup_primary = self.doh_server_instance.bound_ip
                setup_secondary = ""
            else:
                # 2. اگر IPv4 عادی بود، مستقیم ست کن
                setup_primary = primary
                setup_secondary = dns_data.get("secondary", "")

            # تغییر در ویندوز
            cmd1 = f'netsh interface ipv4 set dnsservers name="{adapter}" source=static address="{setup_primary}" primary'
            subprocess.run(cmd1, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)

            if setup_secondary:
                cmd2 = f'netsh interface ipv4 add dnsservers name="{adapter}" address="{setup_secondary}" index=2'
                subprocess.run(cmd2, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

            self.is_connected = True
            self.after(0, self.update_power_button)
        except Exception as e:
            self.disconnect_dns(update_ui=False)
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to connect:\n{str(e)}"))
            self.after(0, self.update_power_button)

    def disconnect_dns(self, update_ui=True):
        adapter = self.active_interface
        
        # بستن تونل لوکال DoH در صورت وجود
        if self.doh_server_instance:
            self.doh_server_instance.stop()
            self.doh_server_instance = None
            
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{adapter}" source=dhcp'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except: pass
        
        self.is_connected = False
        if update_ui: self.after(0, self.update_power_button)

    def update_power_button(self):
        self.btn_power.configure(state="normal")
        if self.is_connected:
            self.btn_power.configure(text="ON", fg_color="#2E7D32", hover_color="#1B5E20")
            self.lbl_status.configure(text="Connected", text_color="#66BB6A")
        else:
            self.btn_power.configure(text="OFF", fg_color="#37474F", hover_color="#455A64")
            self.lbl_status.configure(text="Disconnected", text_color="gray")

    # ==========================================
    # افزودن و حذف
    # ==========================================
    def load_dns_list(self):
        if os.path.exists(self.dns_file):
            try:
                with open(self.dns_file, 'r') as f:
                    data = json.load(f)
                    # پشتیبانی از نسخه‌های قبلی تنظیمات کاربر
                    for d in data:
                        if "type" not in d:
                            d["type"] = "DoH" if str(d.get("primary", "")).startswith("http") else "IPv4"
                    return data
            except: pass
        return DEFAULT_DNS_LIST.copy()

    def save_dns_list(self):
        try:
            with open(self.dns_file, 'w') as f: json.dump(self.dns_list, f, indent=4)
        except: pass

    def delete_dns(self):
        choice = self.combo_dns.get()
        if len(self.dns_list) <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last DNS in the list!")
            return
        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{choice}'?"):
            self.dns_list =[d for d in self.dns_list if d["name"] != choice]
            self.save_dns_list()
            new_values =[d["name"] for d in self.dns_list]
            self.combo_dns.configure(values=new_values)
            self.combo_dns.set(new_values[0])
            self.on_dns_select(new_values[0])

    def open_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Custom DNS")
        dialog.geometry("380x380")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dialog, text="Add New DNS", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(20, 10))

        # انتخابگر نوع دی‌ان‌اس (عادی یا HTTPS)
        self.add_type_var = ctk.StringVar(value="IPv4")
        seg = ctk.CTkSegmentedButton(dialog, values=["IPv4", "DNS over HTTPS"], variable=self.add_type_var, selected_color=CF_ORANGE, selected_hover_color=CF_ORANGE_HOVER, command=lambda val: toggle_fields(val))
        seg.pack(pady=(0, 15))

        entry_name = ctk.CTkEntry(dialog, placeholder_text="Name (e.g. My DNS)", width=280)
        entry_name.pack(pady=5)

        entry_primary = ctk.CTkEntry(dialog, placeholder_text="Primary IP (e.g. 8.8.8.8)", width=280)
        entry_primary.pack(pady=5)

        entry_secondary = ctk.CTkEntry(dialog, placeholder_text="Secondary IP (Optional)", width=280)
        entry_secondary.pack(pady=5)

        def toggle_fields(val):
            if val == "IPv4":
                entry_primary.configure(placeholder_text="Primary IP (e.g. 8.8.8.8)")
                entry_secondary.pack(pady=5)
            else:
                entry_primary.configure(placeholder_text="DoH URL (e.g. https://dns.google/dns-query)")
                entry_secondary.pack_forget()

        def save_new():
            name = entry_name.get().strip()
            primary = entry_primary.get().strip()
            dns_type = "DoH" if self.add_type_var.get() == "DNS over HTTPS" else "IPv4"
            
            if not name or not primary:
                messagebox.showerror("Error", "Name and Address/URL are required!")
                return
            if dns_type == "DoH" and not primary.startswith("http"):
                messagebox.showerror("Error", "DoH URL must start with http:// or https://")
                return
            
            new_dns = {"name": name, "primary": primary, "secondary": entry_secondary.get().strip() if dns_type == "IPv4" else "", "type": dns_type}
            self.dns_list.append(new_dns)
            self.save_dns_list()
            
            new_values =[d["name"] for d in self.dns_list]
            self.combo_dns.configure(values=new_values)
            self.combo_dns.set(name)
            self.on_dns_select(name)
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save DNS", fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold"), command=save_new).pack(pady=20)