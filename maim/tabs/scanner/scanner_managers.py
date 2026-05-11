# tabs/scanner/scanner_managers.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import concurrent.futures
import socket
import time
import ipaddress
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK, STANDARD_PORTS, CLOUDFLARE_CIDRS, DEFAULT_DNS


class ScannerManagers:
    """مدیریت‌های اسکنر - CIDR Manager, DNS Manager, Ports Manager"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
    # ==========================================
    # CIDR Manager (مدیریت رنج‌های IP)
    # ==========================================
    def open_cidr_manager(self, custom_cidrs, save_callback, refresh_callback):
        """باز کردن پنجره مدیریت CIDR با پشتیبانی از لیست‌های حجیم"""
        cidr_win = ctk.CTkToplevel(self.parent)
        cidr_win.title("IP Ranges (CIDRs) Manager")
        cidr_win.geometry("450x550")
        cidr_win.attributes("-topmost", True)
        cidr_win.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(cidr_win, text="Target IP Ranges", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color=CF_ORANGE).pack(pady=10)

        # جعبه متن برای نمایش و ویرایش (هر خط یک CIDR)
        self.cidr_textbox = ctk.CTkTextbox(cidr_win, height=350, font=ctk.CTkFont(size=11))
        self.cidr_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.cidr_textbox.insert("1.0", "\n".join(custom_cidrs))

        # دکمه‌های پایین
        btn_frame = ctk.CTkFrame(cidr_win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        def add_line():
            """افزودن یک خط خالی در انتهای متن"""
            content = self.cidr_textbox.get("1.0", "end-1c")
            if not content.endswith('\n') and content:
                content += '\n'
            content += ' '
            self.cidr_textbox.delete("1.0", "end")
            self.cidr_textbox.insert("1.0", content)
            self.cidr_textbox.see("end")

        ctk.CTkButton(btn_frame, text="➕ Add Line", width=80, fg_color="transparent",
                     border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                     command=add_line).pack(side="left", padx=5)

        def save_changes():
            """ذخیره کردن محتوای Textbox در custom_cidrs و صدا زدن callback"""
            raw = self.cidr_textbox.get("1.0", "end-1c").strip()
            # تبدیل به لیست، حذف خطوط خالی و فضای اضافی
            new_list = [line.strip() for line in raw.splitlines() if line.strip()]
            custom_cidrs.clear()
            custom_cidrs.extend(new_list)
            if save_callback:
                save_callback()
            messagebox.showinfo("Saved", f"{len(new_list)} CIDR(s) saved successfully!")
            cidr_win.destroy()

        ctk.CTkButton(btn_frame, text="💾 Save & Close", fg_color=CF_ORANGE, text_color="black",
                     hover_color=CF_ORANGE_HOVER, command=save_changes).pack(side="right", padx=5)

        # ----- دکمه Clear All (قبلاً به اشتباه Reset Defaults نام داشت) -----
        def clear_editor():
            """پاک کردن کامل Textbox"""
            self.cidr_textbox.delete("1.0", "end")

        ctk.CTkButton(btn_frame, text="Clear All", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015",
                     command=clear_editor).pack(pady=(5, 0))
        
        # تابع به‌روزرسانی لیست (در این نسخه استفاده نمی‌شود ولی نگه داشته شده)
        def refresh_cidr_ui():
            for widget in cidr_scroll.winfo_children():
                widget.destroy()
            for cidr in custom_cidrs:
                row = ctk.CTkFrame(cidr_scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=cidr, width=180, anchor="w").pack(side="left", padx=5)
                ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", text_color="#EF5350", 
                             hover_color="#3A1D1D", 
                             command=lambda c=cidr: remove_cidr(c)).pack(side="right")
        
        # حذف CIDR
        def remove_cidr(cidr):
            if cidr in custom_cidrs:
                custom_cidrs.remove(cidr)
                save_callback()
                refresh_cidr_ui()
        
        # افزودن CIDR جدید
        add_frame = ctk.CTkFrame(cidr_win, fg_color="transparent")
        add_frame.pack(pady=10, fill="x", padx=20)
        entry_new_cidr = ctk.CTkEntry(add_frame, placeholder_text="IP or Range (1.1.1.1, 104.16/13)", width=220)
        entry_new_cidr.pack(side="left", padx=5)
        
        def add_cidr():
            input_text = entry_new_cidr.get().strip()
            if not input_text:
                return
            raw_items = input_text.replace(',', ' ').split()
            added_count = 0
            invalid_items = []
            for item in raw_items:
                item = item.strip()
                if not item: 
                    continue
                try:
                    ipaddress.ip_network(item, strict=False)
                    if item not in custom_cidrs:
                        custom_cidrs.append(item)
                        added_count += 1
                except ValueError:
                    invalid_items.append(item)
            if added_count > 0:
                save_callback()
                entry_new_cidr.delete(0, "end")
                refresh_cidr_ui()
            if invalid_items:
                messagebox.showwarning("Warning", f"Invalid format:\n{', '.join(invalid_items)}")
        
        ctk.CTkButton(add_frame, text="Add", width=60, fg_color=CF_ORANGE, text_color="black", 
                     hover_color=CF_ORANGE_HOVER, command=add_cidr).pack(side="left")
        
        # دکمه بازنشانی اصلی (ذخیره و جایگزینی لیست با پیش‌فرض)
        def reset_cidrs():
            custom_cidrs.clear()
            custom_cidrs.extend(CLOUDFLARE_CIDRS)
            save_callback()
            refresh_cidr_ui()
        
        ctk.CTkButton(cidr_win, text="🔄 Reset to Defaults", fg_color="transparent", border_width=1, 
                     border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", 
                     command=reset_cidrs).pack(pady=10)
        
        # refresh_cidr_ui() اولیه حذف شده (چون دیگر با Textbox کار می‌کنیم)
    
    # ==========================================
    # DNS Manager (مدیریت DNS)
    # ==========================================
    def open_dns_manager(self, dns_list, save_callback, refresh_callback):
        """باز کردن پنجره مدیریت DNS"""
        dns_win = ctk.CTkToplevel(self.parent)
        dns_win.title("DNS Manager")
        dns_win.geometry("400x500")
        dns_win.attributes("-topmost", True)
        dns_win.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dns_win, text="Custom DNS List", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color=CF_ORANGE).pack(pady=10)
        
        # اسکرول برای لیست DNSها
        dns_scroll = ctk.CTkScrollableFrame(dns_win, width=350, height=300)
        dns_scroll.pack(pady=5, padx=10, fill="both", expand=True)
        
        # دیکشنری برای نگهداری لیبل‌های پینگ
        ping_labels = {}
        
        # تابع به‌روزرسانی لیست DNS
        def refresh_dns_ui():
            for widget in dns_scroll.winfo_children():
                widget.destroy()
            ping_labels.clear()
            for idx, dns in enumerate(dns_list):
                row = ctk.CTkFrame(dns_scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=dns, width=120, anchor="w").pack(side="left", padx=5)
                lbl_ping = ctk.CTkLabel(row, text="--- ms", width=60, text_color="gray")
                lbl_ping.pack(side="left", padx=5)
                ping_labels[dns] = lbl_ping
                ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", text_color="#EF5350", 
                             hover_color="#3A1D1D", 
                             command=lambda d=dns: remove_dns(d)).pack(side="right")
        
        # حذف DNS
        def remove_dns(dns):
            if dns in dns_list:
                dns_list.remove(dns)
                save_callback()
                refresh_dns_ui()
        
        # افزودن DNS جدید
        add_frame = ctk.CTkFrame(dns_win, fg_color="transparent")
        add_frame.pack(pady=10, fill="x", padx=20)
        entry_new_dns = ctk.CTkEntry(add_frame, placeholder_text="e.g. 8.8.4.4", width=200)
        entry_new_dns.pack(side="left", padx=5)
        
        def add_dns():
            new_dns = entry_new_dns.get().strip()
            if new_dns and new_dns not in dns_list:
                dns_list.append(new_dns)
                save_callback()
                entry_new_dns.delete(0, "end")
                refresh_dns_ui()
        
        ctk.CTkButton(add_frame, text="Add", width=60, fg_color=CF_ORANGE, text_color="black", 
                     hover_color=CF_ORANGE_HOVER, command=add_dns).pack(side="left")
        
        # تست پینگ همه DNSها
        def test_all_dns():
            def pinger(dns):
                start = time.time()
                try:
                    socket.create_connection((dns, 53), timeout=1.5).close()
                    ms = int((time.time() - start) * 1000)
                    color = "#66BB6A" if ms < 150 else ("#FFA726" if ms < 300 else "#EF5350")
                    return dns, f"{ms} ms", color
                except: 
                    return dns, "Timeout", "#EF5350"
            
            def runner():
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(pinger, dns) for dns in dns_list]
                    for future in concurrent.futures.as_completed(futures):
                        dns, text, color = future.result()
                        if dns in ping_labels:
                            ping_labels[dns].configure(text=text, text_color=color)
            
            # غیرفعال کردن دکمه در حین تست
            test_btn.configure(state="disabled", text="⏳ Testing...")
            threading.Thread(target=runner, daemon=True).start()
            # فعال کردن مجدد دکمه بعد از 10 ثانیه (حداکثر زمان تست)
            dns_win.after(10000, lambda: test_btn.configure(state="normal", text="🔍 Test All DNS Pings"))
        
        test_btn = ctk.CTkButton(dns_win, text="🔍 Test All DNS Pings", fg_color="transparent", 
                                 border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, 
                                 hover_color="#332015", command=test_all_dns)
        test_btn.pack(pady=10)
        
        refresh_dns_ui()
    
    # ==========================================
    # Ports Manager (مدیریت پورت‌ها و پروتکل‌ها)
    # ==========================================
    def open_ports_manager(self, custom_ports, var_ws, var_grpc, var_tcp, save_callback):
        """باز کردن پنجره مدیریت پورت‌ها و پروتکل‌های شبکه"""
        ports_win = ctk.CTkToplevel(self.parent)
        ports_win.title("Ports & Network Types")
        ports_win.geometry("450x550")
        ports_win.attributes("-topmost", True)
        ports_win.configure(fg_color=BG_PANEL)

        # بخش پروتکل‌های شبکه
        ctk.CTkLabel(ports_win, text="🌐 Network Protocols", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color="#29B6F6").pack(pady=(15, 5))
        
        net_frame = ctk.CTkFrame(ports_win, fg_color="transparent")
        net_frame.pack(pady=5, fill="x", padx=20)
        
        # چک‌باکس‌های پروتکل (با اتصال به متغیرهای اصلی)
        cb_ws = ctk.CTkCheckBox(net_frame, text="WebSocket (ws)", variable=var_ws, 
                               fg_color="#29B6F6", hover_color="#0D47A1")
        cb_ws.pack(side="left", padx=10)
        
        cb_grpc = ctk.CTkCheckBox(net_frame, text="gRPC", variable=var_grpc, 
                                 fg_color="#29B6F6", hover_color="#0D47A1")
        cb_grpc.pack(side="left", padx=10)
        
        cb_tcp = ctk.CTkCheckBox(net_frame, text="TCP", variable=var_tcp, 
                                fg_color="#29B6F6", hover_color="#0D47A1")
        cb_tcp.pack(side="left", padx=10)
        
        # بخش لیست پورت‌ها
        ctk.CTkLabel(ports_win, text="🔌 Custom Ports List", font=ctk.CTkFont(size=16, weight="bold"), 
                    text_color=CF_ORANGE).pack(pady=(25, 5))
        
        # اسکرول برای لیست پورت‌ها
        ports_scroll = ctk.CTkScrollableFrame(ports_win, width=350, height=250)
        ports_scroll.pack(pady=5, padx=20, fill="both", expand=True)
        
        # تابع به‌روزرسانی لیست پورت‌ها
        def refresh_ports_ui():
            for widget in ports_scroll.winfo_children():
                widget.destroy()
            for port in sorted(custom_ports):
                row = ctk.CTkFrame(ports_scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)
                # تشخیص نوع امنیت پورت
                sec_type = "TLS" if port in [443, 2053, 2083, 2087, 2096, 8443] else "HTTP/None"
                ctk.CTkLabel(row, text=f"{port} ({sec_type})", width=120, anchor="w", 
                            font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
                ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", text_color="#EF5350", 
                             hover_color="#3A1D1D", 
                             command=lambda p=port: remove_port(p)).pack(side="right")
        
        # حذف پورت
        def remove_port(port):
            if port in custom_ports:
                custom_ports.remove(port)
                save_callback()
                refresh_ports_ui()
        
        # افزودن پورت جدید
        add_p_frame = ctk.CTkFrame(ports_win, fg_color="transparent")
        add_p_frame.pack(pady=10, fill="x", padx=20)
        entry_new_port = ctk.CTkEntry(add_p_frame, placeholder_text="e.g. 8443", width=150)
        entry_new_port.pack(side="left", padx=5)
        
        def add_port():
            try:
                port = int(entry_new_port.get().strip())
                if port <= 0 or port > 65535:
                    raise ValueError
                if port not in custom_ports:
                    custom_ports.append(port)
                    save_callback()
                    entry_new_port.delete(0, "end")
                    refresh_ports_ui()
                else:
                    messagebox.showwarning("Warning", "Port already exists!")
            except ValueError:
                messagebox.showerror("Error", "Enter a valid port (1-65535)")
        
        ctk.CTkButton(add_p_frame, text="Add Port", width=80, fg_color=CF_ORANGE, text_color="black", 
                     hover_color=CF_ORANGE_HOVER, command=add_port).pack(side="left", padx=5)
        
        # دکمه ریست به حالت پیش‌فرض
        def reset_ports():
            custom_ports.clear()
            custom_ports.extend(STANDARD_PORTS)
            save_callback()
            refresh_ports_ui()
        
        ctk.CTkButton(add_p_frame, text="Reset Default", width=100, fg_color="transparent", 
                     border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, 
                     command=reset_ports).pack(side="right", padx=5)
        
        # تابع ذخیره و بستن
        def on_close():
            save_callback()
            ports_win.destroy()
        
        ports_win.protocol("WM_DELETE_WINDOW", on_close)
        refresh_ports_ui()
