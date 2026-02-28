# tab_scanner.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import concurrent.futures
import random
import socket
import ipaddress
import json
import os
import time
import requests
import base64
import urllib.parse
import shutil
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from config import STANDARD_PORTS, ALL_PORTS, CLOUDFLARE_CIDRS, CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, CF_API_URL, DEFAULT_DNS, DIRS, BASE_DIR

TEST_DL_LIMIT_KB = 50
TEST_UL_SIZE_KB = 15
TIMEOUT = 3

class ScannerFrame(ctk.CTkFrame):
    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.grid_columnconfigure(0, weight=1)

        self.stop_event = threading.Event()
        self.best_pairs =[]
        self.completed_tasks = 0
        self.total_tasks = 0
        self.results_lock = threading.Lock()
        
        self.dns_list = DEFAULT_DNS.copy()
        self.custom_ports = STANDARD_PORTS.copy()
        self.custom_cidrs = CLOUDFLARE_CIDRS.copy()
        
        self.fragment_settings = {"packets": "1-1", "length": "100-200", "interval": "1"}
        
        # استفاده از مسیرهای مرکزی
        self.target_dir = BASE_DIR
        self.configs_dir = DIRS["configs"]
        self.subs_dir = DIRS["subs"]

        self.var_tls = ctk.IntVar(value=1)
        self.var_none = ctk.IntVar(value=1)
        self.var_h2 = ctk.IntVar(value=1)
        self.var_http1 = ctk.IntVar(value=1)
        
        self.var_ws = ctk.IntVar(value=1)
        self.var_grpc = ctk.IntVar(value=0)
        self.var_tcp = ctk.IntVar(value=0)
        
        self.var_frag_enable = ctk.IntVar(value=1)

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        config_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        config_frame.grid(row=0, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(config_frame, text="UUID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_uuid = ctk.CTkEntry(config_frame, width=220, placeholder_text="VLESS UUID")
        self.entry_uuid.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkLabel(config_frame, text="WS/gRPC Path:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entry_path = ctk.CTkEntry(config_frame, width=120, placeholder_text="/path")
        self.entry_path.grid(row=0, column=3, padx=10, pady=10)

        ctk.CTkLabel(config_frame, text="Worker Host:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_host = ctk.CTkEntry(config_frame, width=220, placeholder_text="app.workers.dev")
        self.entry_host.grid(row=1, column=1, padx=10, pady=10)

        perf_frame = ctk.CTkFrame(self, fg_color="transparent")
        perf_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        perf_frame.grid_columnconfigure((0,1), weight=1)

        thread_frame = ctk.CTkFrame(perf_frame, fg_color=BG_PANEL, corner_radius=10)
        thread_frame.grid(row=0, column=0, padx=5, sticky="ew")
        self.lbl_threads = ctk.CTkLabel(thread_frame, text="Threads: 50")
        self.lbl_threads.pack(pady=(5,0))
        self.slider_threads = ctk.CTkSlider(thread_frame, from_=10, to=200, number_of_steps=19, progress_color=CF_ORANGE, command=self.update_thread_lbl)
        self.slider_threads.set(50)
        self.slider_threads.pack(pady=10, padx=10, fill="x")

        ip_frame = ctk.CTkFrame(perf_frame, fg_color=BG_PANEL, corner_radius=10)
        ip_frame.grid(row=0, column=1, padx=5, sticky="ew")
        self.lbl_ips = ctk.CTkLabel(ip_frame, text="IPs per Range: 100")
        self.lbl_ips.pack(pady=(5,0))
        self.slider_ips = ctk.CTkSlider(ip_frame, from_=10, to=500, number_of_steps=49, progress_color=CF_ORANGE, command=self.update_ip_lbl)
        self.slider_ips.set(100)
        self.slider_ips.pack(pady=10, padx=10, fill="x")

        opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        opt_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        opt_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.ip_source = ctk.StringVar(value="Default List")
        self.seg_source = ctk.CTkSegmentedButton(opt_frame, values=["Default List", "Fetch API IPs"], variable=self.ip_source, selected_color=CF_ORANGE, selected_hover_color=CF_ORANGE_HOVER)
        self.seg_source.grid(row=0, column=0, padx=2, sticky="ew")

        self.scan_mode = ctk.StringVar(value="Standard Ports")
        self.seg_ports = ctk.CTkSegmentedButton(opt_frame, values=["Standard Ports", "Deep Scan (All)"], variable=self.scan_mode, selected_color=CF_ORANGE, selected_hover_color=CF_ORANGE_HOVER)
        self.seg_ports.grid(row=0, column=1, padx=2, sticky="ew")

        btn_dns = ctk.CTkButton(opt_frame, text="⚙️ DNS", fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.open_dns_manager)
        btn_dns.grid(row=0, column=2, padx=2, sticky="ew")

        btn_cidrs = ctk.CTkButton(opt_frame, text="🌐 IP Ranges", fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.open_cidr_manager)
        btn_cidrs.grid(row=0, column=3, padx=2, sticky="ew")

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        ctk.CTkLabel(filter_frame, text="⚙️ Config Types:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(filter_frame, text="TLS", variable=self.var_tls, fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)
        ctk.CTkCheckBox(filter_frame, text="None", variable=self.var_none, fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)
        ctk.CTkCheckBox(filter_frame, text="H2", variable=self.var_h2, fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)
        ctk.CTkCheckBox(filter_frame, text="HTTP/1.1", variable=self.var_http1, fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)

        btn_ports = ctk.CTkButton(filter_frame, text="🔌 Ports & Network", fg_color="transparent", border_width=1, border_color="#29B6F6", text_color="#29B6F6", hover_color="#0D47A1", command=self.open_ports_manager)
        btn_ports.pack(side="right", padx=0)

        # ================= FRAGMENT FRAME =================
        frag_frame = ctk.CTkFrame(self, fg_color="transparent")
        frag_frame.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        self.chk_frag = ctk.CTkCheckBox(frag_frame, text="🧩 Enable Fragment", font=ctk.CTkFont(weight="bold"), variable=self.var_frag_enable, fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER, command=self.toggle_frag_ui)
        self.chk_frag.pack(side="left", padx=(0, 10))
        
        self.frag_mode = ctk.StringVar(value="Auto")
        self.seg_frag = ctk.CTkSegmentedButton(frag_frame, values=["Auto", "Manual"], variable=self.frag_mode, selected_color=CF_ORANGE, selected_hover_color=CF_ORANGE_HOVER, command=self.toggle_frag_ui)
        self.seg_frag.pack(side="left", padx=10)

        ctk.CTkLabel(frag_frame, text="Packets:").pack(side="left", padx=(10, 2))
        self.entry_frag_packets = ctk.CTkEntry(frag_frame, width=70, placeholder_text="1-1")
        self.entry_frag_packets.pack(side="left", padx=2)

        ctk.CTkLabel(frag_frame, text="Length:").pack(side="left", padx=(10, 2))
        self.entry_frag_length = ctk.CTkEntry(frag_frame, width=80, placeholder_text="100-200")
        self.entry_frag_length.pack(side="left", padx=2)

        ctk.CTkLabel(frag_frame, text="Interval:").pack(side="left", padx=(10, 2))
        self.entry_frag_interval = ctk.CTkEntry(frag_frame, width=60, placeholder_text="1")
        self.entry_frag_interval.pack(side="left", padx=2)

        self.toggle_frag_ui()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_start = ctk.CTkButton(btn_frame, text="▶ START ADVANCED SCAN", fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER, text_color="black", font=ctk.CTkFont(weight="bold", size=14), command=self.start_scan)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=5, ipady=5)

        self.btn_stop = ctk.CTkButton(btn_frame, text="⏹ STOP & GENERATE", fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(weight="bold", size=14), state="disabled", command=self.stop_scan)
        self.btn_stop.pack(side="right", expand=True, fill="x", padx=5, ipady=5)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Ready", text_color=CF_ORANGE, font=ctk.CTkFont(weight="bold"))
        self.lbl_status.grid(row=6, column=0, padx=20, sticky="w")

        self.progressbar = ctk.CTkProgressBar(self, progress_color=CF_ORANGE)
        self.progressbar.grid(row=7, column=0, padx=20, pady=5, sticky="ew")
        self.progressbar.set(0)

        self.log_box = ctk.CTkTextbox(self, height=110, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG_PANEL, border_color="gray20", border_width=1)
        self.log_box.grid(row=8, column=0, padx=20, pady=5, sticky="nsew")

    def toggle_frag_ui(self, *args):
        is_enabled = self.var_frag_enable.get() == 1
        mode = self.frag_mode.get()

        if not is_enabled:
            self.seg_frag.configure(state="disabled")
            self.entry_frag_packets.configure(state="disabled", fg_color=BG_PANEL)
            self.entry_frag_length.configure(state="disabled", fg_color=BG_PANEL)
            self.entry_frag_interval.configure(state="disabled", fg_color=BG_PANEL)
        else:
            self.seg_frag.configure(state="normal")
            if mode == "Manual":
                self.entry_frag_packets.configure(state="normal", fg_color="#121212")
                self.entry_frag_length.configure(state="normal", fg_color="#121212")
                self.entry_frag_interval.configure(state="normal", fg_color="#121212")
            else:
                self.entry_frag_packets.configure(state="disabled", fg_color=BG_PANEL)
                self.entry_frag_length.configure(state="disabled", fg_color=BG_PANEL)
                self.entry_frag_interval.configure(state="disabled", fg_color=BG_PANEL)

    def update_thread_lbl(self, val): self.lbl_threads.configure(text=f"Threads: {int(val)}")
    def update_ip_lbl(self, val): self.lbl_ips.configure(text=f"IPs per Range: {int(val)}")

    def open_cidr_manager(self):
        cidr_win = ctk.CTkToplevel(self)
        cidr_win.title("IP Ranges (CIDRs) Manager")
        cidr_win.geometry("400x500")
        cidr_win.attributes("-topmost", True)
        cidr_win.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(cidr_win, text="Target IP Ranges", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=10)
        
        self.cidr_scroll = ctk.CTkScrollableFrame(cidr_win, width=350, height=300)
        self.cidr_scroll.pack(pady=5, padx=10, fill="both", expand=True)
        self.refresh_cidr_ui()

        add_frame = ctk.CTkFrame(cidr_win, fg_color="transparent")
        add_frame.pack(pady=10, fill="x", padx=20)
        self.entry_new_cidr = ctk.CTkEntry(add_frame, placeholder_text="IP or Range (1.1.1.1, 104.16/13)", width=220)
        self.entry_new_cidr.pack(side="left", padx=5)
        
        ctk.CTkButton(add_frame, text="Add", width=60, fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, command=self.add_cidr).pack(side="left")
        ctk.CTkButton(cidr_win, text="🔄 Reset Defaults", fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.reset_cidrs).pack(pady=10)

    def refresh_cidr_ui(self):
        for widget in self.cidr_scroll.winfo_children(): widget.destroy()
        for c in self.custom_cidrs:
            row = ctk.CTkFrame(self.cidr_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=c, width=180, anchor="w").pack(side="left", padx=5)
            ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", text_color="#EF5350", hover_color="#3A1D1D", command=lambda cidr=c: self.remove_cidr(cidr)).pack(side="right")

    def add_cidr(self):
        input_text = self.entry_new_cidr.get().strip()
        if not input_text:
            return

        raw_items = input_text.replace(',', ' ').split()
        added_count = 0
        invalid_items = []
        duplicate_items =[]

        for item in raw_items:
            item = item.strip()
            if not item: continue
            try:
                ipaddress.ip_network(item, strict=False)
                if item not in self.custom_cidrs:
                    self.custom_cidrs.append(item)
                    added_count += 1
                else:
                    duplicate_items.append(item)
            except ValueError:
                invalid_items.append(item)

        if added_count > 0:
            self.save_config()
            self.entry_new_cidr.delete(0, "end")
            self.refresh_cidr_ui()
            
        if invalid_items:
            messagebox.showwarning("Warning", f"Added {added_count} items.\n\nInvalid format ignored:\n{', '.join(invalid_items)}")
        elif duplicate_items and added_count == 0:
            messagebox.showinfo("Info", "All entered IPs/Ranges already exist in the list.")

    def remove_cidr(self, cidr):
        if cidr in self.custom_cidrs:
            self.custom_cidrs.remove(cidr)
            self.save_config()
            self.refresh_cidr_ui()

    def reset_cidrs(self):
        self.custom_cidrs = CLOUDFLARE_CIDRS.copy()
        self.save_config()
        self.refresh_cidr_ui()

    def open_dns_manager(self):
        dns_win = ctk.CTkToplevel(self)
        dns_win.title("DNS Manager")
        dns_win.geometry("400x500")
        dns_win.attributes("-topmost", True)
        dns_win.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dns_win, text="Custom DNS List", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=10)
        self.dns_scroll = ctk.CTkScrollableFrame(dns_win, width=350, height=300)
        self.dns_scroll.pack(pady=5, padx=10, fill="both", expand=True)
        self.refresh_dns_ui()

        add_frame = ctk.CTkFrame(dns_win, fg_color="transparent")
        add_frame.pack(pady=10, fill="x", padx=20)
        self.entry_new_dns = ctk.CTkEntry(add_frame, placeholder_text="e.g. 8.8.4.4", width=200)
        self.entry_new_dns.pack(side="left", padx=5)
        ctk.CTkButton(add_frame, text="Add", width=60, fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, command=self.add_dns).pack(side="left")
        ctk.CTkButton(dns_win, text="🔍 Test All DNS Pings", fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.test_all_dns).pack(pady=10)

    def refresh_dns_ui(self):
        for widget in self.dns_scroll.winfo_children(): widget.destroy()
        for idx, dns in enumerate(self.dns_list):
            row = ctk.CTkFrame(self.dns_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=dns, width=120, anchor="w").pack(side="left", padx=5)
            lbl_ping = ctk.CTkLabel(row, text="--- ms", width=60, text_color="gray")
            lbl_ping.pack(side="left", padx=5)
            setattr(self, f"ping_lbl_{idx}", lbl_ping)
            ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", text_color="#EF5350", hover_color="#3A1D1D", command=lambda d=dns: self.remove_dns(d)).pack(side="right")

    def add_dns(self):
        new_dns = self.entry_new_dns.get().strip()
        if new_dns and new_dns not in self.dns_list:
            self.dns_list.append(new_dns)
            self.save_config()
            self.entry_new_dns.delete(0, "end")
            self.refresh_dns_ui()

    def remove_dns(self, dns):
        if dns in self.dns_list:
            self.dns_list.remove(dns)
            self.save_config()
            self.refresh_dns_ui()

    def test_all_dns(self):
        def pinger(dns, idx):
            start = time.time()
            try:
                socket.create_connection((dns, 53), timeout=1.5).close()
                ms = int((time.time() - start) * 1000)
                color = "#66BB6A" if ms < 150 else ("#FFA726" if ms < 300 else "#EF5350")
                return idx, f"{ms} ms", color
            except: return idx, "Timeout", "#EF5350"

        def runner():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures =[executor.submit(pinger, dns, idx) for idx, dns in enumerate(self.dns_list)]
                for future in concurrent.futures.as_completed(futures):
                    idx, text, color = future.result()
                    try: getattr(self, f"ping_lbl_{idx}").configure(text=text, text_color=color)
                    except: pass
        threading.Thread(target=runner, daemon=True).start()

    def open_ports_manager(self):
        ports_win = ctk.CTkToplevel(self)
        ports_win.title("Ports & Network Types")
        ports_win.geometry("450x550")
        ports_win.attributes("-topmost", True)
        ports_win.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(ports_win, text="🌐 Network Protocols", font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15, 5))
        
        net_frame = ctk.CTkFrame(ports_win, fg_color="transparent")
        net_frame.pack(pady=5, fill="x", padx=20)
        
        ctk.CTkCheckBox(net_frame, text="WebSocket (ws)", variable=self.var_ws, fg_color="#29B6F6", hover_color="#0D47A1").pack(side="left", padx=10)
        ctk.CTkCheckBox(net_frame, text="gRPC", variable=self.var_grpc, fg_color="#29B6F6", hover_color="#0D47A1").pack(side="left", padx=10)
        ctk.CTkCheckBox(net_frame, text="TCP", variable=self.var_tcp, fg_color="#29B6F6", hover_color="#0D47A1").pack(side="left", padx=10)

        ctk.CTkLabel(ports_win, text="🔌 Custom Ports List", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(25, 5))
        
        self.ports_scroll = ctk.CTkScrollableFrame(ports_win, width=350, height=250)
        self.ports_scroll.pack(pady=5, padx=20, fill="both", expand=True)
        self.refresh_ports_ui()

        add_p_frame = ctk.CTkFrame(ports_win, fg_color="transparent")
        add_p_frame.pack(pady=10, fill="x", padx=20)
        self.entry_new_port = ctk.CTkEntry(add_p_frame, placeholder_text="e.g. 8443", width=150)
        self.entry_new_port.pack(side="left", padx=5)
        
        ctk.CTkButton(add_p_frame, text="Add Port", width=80, fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, command=self.add_port).pack(side="left", padx=5)
        ctk.CTkButton(add_p_frame, text="Reset Default", width=100, fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.reset_ports).pack(side="right", padx=5)

        ports_win.protocol("WM_DELETE_WINDOW", lambda: self.close_ports_manager(ports_win))

    def close_ports_manager(self, win):
        self.save_config()
        win.destroy()

    def refresh_ports_ui(self):
        for widget in self.ports_scroll.winfo_children(): widget.destroy()
        for p in sorted(self.custom_ports):
            row = ctk.CTkFrame(self.ports_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            sec_type = "TLS" if p in[443, 2053, 2083, 2087, 2096, 8443] else "HTTP/None"
            ctk.CTkLabel(row, text=f"{p} ({sec_type})", width=120, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", text_color="#EF5350", hover_color="#3A1D1D", command=lambda pt=p: self.remove_port(pt)).pack(side="right")

    def add_port(self):
        try:
            port = int(self.entry_new_port.get().strip())
            if port <= 0 or port > 65535: raise ValueError
            if port not in self.custom_ports:
                self.custom_ports.append(port)
                self.save_config()
                self.entry_new_port.delete(0, "end")
                self.refresh_ports_ui()
            else: messagebox.showwarning("Warning", "Port already exists!")
        except ValueError: messagebox.showerror("Error", "Enter a valid port (1-65535)")

    def remove_port(self, port):
        if port in self.custom_ports:
            self.custom_ports.remove(port)
            self.save_config()
            self.refresh_ports_ui()

    def reset_ports(self):
        self.custom_ports = STANDARD_PORTS.copy()
        self.save_config()
        self.refresh_ports_ui()

    def log(self, text):
        self.after(0, self._log_safe, text)
        
    def _log_safe(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def load_config(self):
        path = os.path.join(DIRS["settings"], "Scanner_Config.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.entry_uuid.insert(0, data.get('UUID', ''))
                    self.entry_path.insert(0, data.get('PATH', ''))
                    self.entry_host.insert(0, data.get('HOST', ''))
                    if 'DNS' in data: self.dns_list = data['DNS']
                    if 'PORTS' in data: self.custom_ports = data['PORTS']
                    if 'CIDRS' in data: self.custom_cidrs = data['CIDRS']
                    if 'TLS' in data: self.var_tls.set(data['TLS'])
                    if 'NONE' in data: self.var_none.set(data['NONE'])
                    if 'H2' in data: self.var_h2.set(data['H2'])
                    if 'HTTP1' in data: self.var_http1.set(data['HTTP1'])
                    if 'WS' in data: self.var_ws.set(data['WS'])
                    if 'GRPC' in data: self.var_grpc.set(data['GRPC'])
                    if 'TCP' in data: self.var_tcp.set(data['TCP'])
                    
                    if 'FRAG_ENABLE' in data:
                        self.var_frag_enable.set(data['FRAG_ENABLE'])
                    if 'FRAG_MODE' in data:
                        self.frag_mode.set(data['FRAG_MODE'])
                    if 'FRAG_PACKETS' in data:
                        self.entry_frag_packets.delete(0, 'end')
                        self.entry_frag_packets.insert(0, data['FRAG_PACKETS'])
                    if 'FRAG_LENGTH' in data:
                        self.entry_frag_length.delete(0, 'end')
                        self.entry_frag_length.insert(0, data['FRAG_LENGTH'])
                    if 'FRAG_INTERVAL' in data:
                        self.entry_frag_interval.delete(0, 'end')
                        self.entry_frag_interval.insert(0, data['FRAG_INTERVAL'])
                        
            except: pass
        self.toggle_frag_ui()

    def save_config(self):
        path = os.path.join(DIRS["settings"], "Scanner_Config.json")
        data = {
            'UUID': self.entry_uuid.get(), 
            'PATH': self.entry_path.get(), 
            'HOST': self.entry_host.get(), 
            'DNS': self.dns_list,
            'PORTS': self.custom_ports,
            'CIDRS': self.custom_cidrs,
            'TLS': self.var_tls.get(),
            'NONE': self.var_none.get(),
            'H2': self.var_h2.get(),
            'HTTP1': self.var_http1.get(),
            'WS': self.var_ws.get(),
            'GRPC': self.var_grpc.get(),
            'TCP': self.var_tcp.get(),
            'FRAG_ENABLE': self.var_frag_enable.get(),
            'FRAG_MODE': self.frag_mode.get(),
            'FRAG_PACKETS': self.entry_frag_packets.get(),
            'FRAG_LENGTH': self.entry_frag_length.get(),
            'FRAG_INTERVAL': self.entry_frag_interval.get()
        }
        try:
            with open(path, 'w') as f: json.dump(data, f)
        except: pass

    def start_scan(self):
        if not self.entry_uuid.get() or not self.entry_host.get():
            messagebox.showerror("Error", "Please fill UUID and Host fields!")
            return
            
        if self.var_tls.get() == 0 and self.var_none.get() == 0:
            messagebox.showerror("Error", "Please select at least one security type (TLS or None)!")
            return
            
        if self.var_tls.get() == 1 and self.var_h2.get() == 0 and self.var_http1.get() == 0:
            messagebox.showerror("Error", "You selected TLS but unchecked both ALPN types! Please select H2 or HTTP/1.1")
            return
            
        if self.var_ws.get() == 0 and self.var_grpc.get() == 0 and self.var_tcp.get() == 0:
            messagebox.showerror("Error", "Please select at least one Network Protocol (ws, grpc, or tcp) in 'Ports & Network'!")
            return
        
        self.save_config()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal", text="⏹ STOP & GENERATE")
        self.log_box.delete("1.0", "end")
        self.stop_event.clear()
        self.best_pairs =[]
        self.completed_tasks = 0

        if os.path.exists(self.configs_dir):
            try: shutil.rmtree(self.configs_dir)
            except: pass
        os.makedirs(self.configs_dir, exist_ok=True)
        os.makedirs(self.subs_dir, exist_ok=True)

        threading.Thread(target=self.scan_engine, daemon=True).start()

    def stop_scan(self):
        self.btn_stop.configure(state="disabled", text="⏳ GENERATING...")
        self.log("\n[!] STOP PRESSED! Halting scanner and generating configs for found IPs...")
        self.stop_event.set()

    def detect_isp_and_adjust_fragment(self):
        if self.var_frag_enable.get() == 0:
            self.log("🧩 Fragment Option is Disabled.")
            return

        if self.frag_mode.get() == "Manual":
            self.fragment_settings = {
                "packets": self.entry_frag_packets.get().strip() or "1-1",
                "length": self.entry_frag_length.get().strip() or "100-200",
                "interval": self.entry_frag_interval.get().strip() or "1"
            }
            self.log(f"🧩 Manual Fragment Applied: {self.fragment_settings}")
            return

        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5).json()
            isp, org = resp.get("isp", "").lower(), resp.get("org", "").lower()
            if any(kw in isp or kw in org for kw in ['mci', 'hamrah']): 
                self.fragment_settings = {"packets": "1-1", "length": "10-20", "interval": "5"}
                self.log(f"📶 Auto Fragment (MCI): {self.fragment_settings}")
            elif any(kw in isp or kw in org for kw in ['mtn', 'irancell']): 
                self.fragment_settings = {"packets": "1-1", "length": "1-3", "interval": "10"}
                self.log(f"📶 Auto Fragment (Irancell): {self.fragment_settings}")
            elif 'rightel' in isp: 
                self.fragment_settings = {"packets": "1-1", "length": "20-40", "interval": "5"}
                self.log(f"📶 Auto Fragment (Rightel): {self.fragment_settings}")
            else: 
                self.fragment_settings = {"packets": "1-1", "length": "100-200", "interval": "1"}
                self.log(f"🌐 Auto Fragment (Broadband): {self.fragment_settings}")
        except: 
            self.fragment_settings = {"packets": "1-1", "length": "100-200", "interval": "1"}
            self.log(f"⚠️ ISP Detection Failed (Using Default Fragment): {self.fragment_settings}")

    def test_worker_handshake(self, ip, port):
        try:
            path = self.entry_path.get()
            if not path.startswith("/"): path = "/" + path
            url = f"http://{ip}:{port}{path}"
            headers = {
                "Host": self.entry_host.get(),
                "User-Agent": "Mozilla/5.0",
                "Connection": "Upgrade",
                "Upgrade": "websocket"
            }
            resp = requests.get(url, headers=headers, timeout=2, allow_redirects=False)
            if resp.status_code == 101 or ("cloudflare" in resp.headers.get("Server", "").lower() and resp.status_code in [200, 400, 403, 404]):
                return True
        except: pass
        return False

    def find_working_port(self, ip, port_list):
        ports_to_check = list(port_list)
        random.shuffle(ports_to_check)
        found_port = None

        def worker():
            nonlocal found_port
            while ports_to_check and not self.stop_event.is_set() and found_port is None:
                try:
                    port = ports_to_check.pop()
                except IndexError:
                    break
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        if s.connect_ex((ip, port)) == 0:
                            if self.test_worker_handshake(ip, port):
                                if found_port is None:
                                    found_port = port
                                break
                except:
                    pass

        threads =[]
        for _ in range(min(10, len(ports_to_check))):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
        return found_port

    def perform_ping_twice(self, ip, port):
        avg_ping, valid = 0, 0
        for _ in range(2):
            if self.stop_event.is_set(): return 9999
            start = time.time()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(TIMEOUT)
                    s.connect((ip, port))
                avg_ping += int((time.time() - start) * 1000)
                valid += 1
            except: pass
        return int(avg_ping / valid) if valid > 0 else 9999

    def perform_speed_test(self, ip, port, host_header):
        try:
            headers = {'Host': host_header, 'User-Agent': 'Mozilla/5.0'}
            path = self.entry_path.get()
            if not path.startswith("/"): path = "/" + path
            
            req_path = f"/__down?bytes={TEST_DL_LIMIT_KB * 1024}" if "speed.cloudflare.com" in host_header else path
            url = f"http://{ip}:{port}{req_path}"
            
            st = time.time()
            r = requests.get(url, headers=headers, timeout=4, stream=True)
            size = 0
            for chunk in r.iter_content(1024):
                if self.stop_event.is_set(): return 0, 0
                size += len(chunk)
                if size > TEST_DL_LIMIT_KB * 1024: break
            
            dl_t = max(time.time() - st, 0.01)
            dl_s = round((size/1024)/dl_t, 1)

            st_ul = time.time()
            try:
                if not self.stop_event.is_set():
                    up_path = "/__up" if "speed.cloudflare.com" in host_header else path
                    up_url = f"http://{ip}:{port}{up_path}"
                    requests.post(up_url, headers=headers, data=b'0'*(TEST_UL_SIZE_KB*1024), timeout=4)
            except: pass
            
            ul_t = max(time.time() - st_ul, 0.01)
            ul_s = round(TEST_UL_SIZE_KB/ul_t, 1)
            
            return dl_s, ul_s
        except: 
            return 0, 0

    def process_ip(self, ip, port_list):
        if self.stop_event.is_set(): return

        working_port = self.find_working_port(ip, port_list)
        if not working_port: return

        avg_ping = self.perform_ping_twice(ip, working_port)
        if avg_ping > 1500: return

        best_combo = None
        max_dl = -1
        min_ping = 9999
        hosts_to_test =[{"name": "Worker", "header": self.entry_host.get()}, {"name": "SpeedTest", "header": "speed.cloudflare.com"}]
        cache = {}

        for h in hosts_to_test:
            if self.stop_event.is_set(): break
            ping = self.perform_ping_twice(ip, working_port)
            dl, ul = self.perform_speed_test(ip, working_port, h['header'])
            cache[h['name']] = {"ping": ping, "dl": dl, "ul": ul}
            
            if ping < 1500 and dl > 0 and (dl > max_dl or (dl == max_dl and ping < min_ping)):
                max_dl = dl
                min_ping = ping
                best_combo = {"ip": ip, "port": working_port, "dns_ip": "8.8.8.8", "ping": ping, "dl": dl, "ul": ul}

        for dns in self.dns_list:
            if self.stop_event.is_set(): break
            for h in hosts_to_test:
                res = cache.get(h['name'])
                if not res: continue
                if res['ping'] < 1500 and res['dl'] > 0 and (res['dl'] > max_dl or (res['dl'] == max_dl and res['ping'] < min_ping)):
                    max_dl = res['dl']
                    min_ping = res['ping']
                    best_combo = {"ip": ip, "port": working_port, "dns_ip": dns, "ping": res['ping'], "dl": res['dl'], "ul": res['ul']}

        if best_combo and not self.stop_event.is_set():
            with self.results_lock:
                self.best_pairs.append(best_combo)
            self.log(f"✅[HIT] {ip}:{working_port} | DL: {best_combo['dl']} KB/s | Ping: {best_combo['ping']}ms")

    def scan_engine(self):
        self.detect_isp_and_adjust_fragment()
        scan_ips =[]
        samples_count = int(self.slider_ips.get())
        max_threads = int(self.slider_threads.get())
        
        if self.ip_source.get() == "Fetch API IPs":
            self.log("[*] Downloading fresh IPs from API...")
            try:
                resp = requests.get(CF_API_URL, timeout=10)
                if resp.status_code == 200:
                    fetched =[ip.strip() for ip in resp.text.split('\n') if ip.strip()]
                    scan_ips.extend(fetched)
                    self.log(f"[+] Loaded {len(scan_ips)} IPs from API.")
                else: self.log("[-] API Failed. Using defaults.")
            except: self.log("[-] Network Error. Using defaults.")

        if not scan_ips:
            for cidr in self.custom_cidrs:
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                    if net.num_addresses <= samples_count:
                        scan_ips.extend([str(ip) for ip in net])
                    else:
                        limit = samples_count
                        selected = set()
                        while len(selected) < limit:
                            selected.add(str(net[random.randint(0, net.num_addresses - 1)]))
                        scan_ips.extend(list(selected))
                except Exception:
                    pass

        base_ports = self.custom_ports if self.scan_mode.get() == "Standard Ports" else ALL_PORTS
        none_cf_ports =[80, 8080, 8880, 2052, 2082, 2095]
        filtered_ports =[]
        
        for p in base_ports:
            is_none = p in none_cf_ports
            if not is_none and self.var_tls.get() == 1:
                filtered_ports.append(p)
            elif is_none and self.var_none.get() == 1:
                filtered_ports.append(p)
                
        if not filtered_ports:
            self.log("[-] Error: No ports selected based on your config types.")
            self.after(0, self.stop_scan)
            return

        self.total_tasks = len(scan_ips)
        self.log(f"\n🚀 Scanning {self.total_tasks} IPs with {max_threads} Threads...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(self.process_ip, ip, filtered_ports): ip for ip in scan_ips}
            for future in concurrent.futures.as_completed(futures):
                if self.stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                self.completed_tasks += 1
                
                pct = self.completed_tasks / self.total_tasks
                self.after(0, lambda p=pct, c=self.completed_tasks, t=self.total_tasks, b=len(self.best_pairs): 
                           (self.progressbar.set(p), self.lbl_status.configure(text=f"Scanning: {c}/{t} | Found: {b}")))

        self.generate_final_configs()

    def get_countries_batch(self, ip_list):
        country_map = {ip: "UNK" for ip in ip_list}
        unique_ips = list(set(ip_list))
        for i in range(0, len(unique_ips), 100):
            try:
                res = requests.post("http://ip-api.com/batch?fields=query,countryCode", json=unique_ips[i:i+100], timeout=5)
                if res.status_code == 200:
                    for item in res.json(): country_map[item['query']] = item.get('countryCode', 'UNK')
            except: pass
        return country_map

    def generate_final_configs(self):
        if not self.best_pairs:
            self.log("\n❌ Process stopped. No working IPs found.")
            self.after(0, lambda: (self.btn_start.configure(state="normal"), self.btn_stop.configure(state="disabled", text="⏹ STOP & GENERATE"), self.lbl_status.configure(text="Status: Finished (No Results)")))
            self.show_summary_popup(0, 0)
            return

        # ========================================================
        # ویژگی جدید: مرتب‌سازی و انتخاب فقط 15 آی‌پی برتر 
        # (جلوگیری از ساخت صدها کانفیگ و فریز شدن اپلیکیشن کلاینت)
        # ========================================================
        sorted_best = sorted(self.best_pairs, key=lambda x: (x.get('dl', 0), -x.get('ping', 9999)), reverse=True)
        sorted_best = sorted_best[:15] # فقط 15 تا نگه داشته می‌شود

        self.log(f"\n🌍 Filtering applied! Generating configs for the TOP {len(sorted_best)} best IPs...")
        ip_countries_map = self.get_countries_batch([d['ip'] for d in sorted_best])
        
        vless_links =[]
        global_index = 1
        
        gen_tls = self.var_tls.get() == 1
        gen_none = self.var_none.get() == 1
        gen_h2 = self.var_h2.get() == 1
        gen_http1 = self.var_http1.get() == 1
        
        net_types =[]
        if self.var_ws.get() == 1: net_types.append("ws")
        if self.var_grpc.get() == 1: net_types.append("grpc")
        if self.var_tcp.get() == 1: net_types.append("tcp")

        for data in sorted_best:
            ip, port = data['ip'], int(data['port'])
            sec = "none" if port in[80, 8080, 8880, 2052, 2082, 2095] else "tls"
            cc = ip_countries_map.get(ip, "UNK")
            dl_speed = data.get('dl', 0)
            
            if sec == "tls" and not gen_tls: continue
            if sec == "none" and not gen_none: continue
            
            alpns =[]
            if sec == "tls":
                if gen_http1: alpns.append("http/1.1")
                if gen_h2: alpns.append("h2,http/1.1")
            else:
                alpns = [""]
            
            for alpn in alpns:
                for net_type in net_types:
                    self.create_config_json(data, global_index, alpn, cc, sec, net_type)
                    
                    alpn_lbl = "H2" if "h2" in alpn else ("HTTP1" if alpn else "None")
                    alias = f"🌍{cc} | {ip}:{port} | {sec.upper()} | {net_type.upper()} | DL:{dl_speed}K"
                    
                    sec_param = f"&security=tls&alpn={urllib.parse.quote(alpn)}&sni={self.entry_host.get()}" if sec == "tls" else "&security=none"
                    
                    path = self.entry_path.get()
                    if not path.startswith("/"): path = "/" + path
                    
                    net_params = f"&type={net_type}"
                    if net_type == "ws":
                        net_params += f"&host={self.entry_host.get()}&path={urllib.parse.quote(path)}"
                    elif net_type == "grpc":
                        svc_name = path.lstrip("/")
                        net_params += f"&serviceName={urllib.parse.quote(svc_name)}&mode=multi"
                    elif net_type == "tcp":
                        net_params += f"&headerType=http&host={self.entry_host.get()}&path={urllib.parse.quote(path)}"
                    
                    if self.var_frag_enable.get() == 1:
                        packet_val = self.fragment_settings['packets']
                        length_val = self.fragment_settings['length']
                        interval_val = self.fragment_settings['interval']
                        frag_param = f"&fragment={urllib.parse.quote(f'{packet_val},{length_val},{interval_val}')}"
                        net_params += frag_param

                    vless_link = (f"vless://{self.entry_uuid.get()}@{ip}:{port}?encryption=none"
                                  f"{net_params}&fp=chrome{sec_param}#{urllib.parse.quote(alias)}")
                    vless_links.append(vless_link)
                    global_index += 1

        try:
            with open(os.path.join(self.subs_dir, "sub.txt"), "w") as f:
                f.write(base64.b64encode("\n".join(vless_links).encode()).decode())
        except: pass

        self.log(f"\n🎉 ALL DONE! Generated {len(vless_links)} configs from top IPs.")
        self.after(0, lambda: (self.btn_start.configure(state="normal"), self.btn_stop.configure(state="disabled", text="⏹ STOP & GENERATE"), self.lbl_status.configure(text="Status: Finished & Saved!")))
        
        self.show_summary_popup(len(self.best_pairs), len(vless_links))

    def create_config_json(self, data, index, alpn, cc, sec, net_type):
        alpn_lbl = "H2" if "h2" in alpn else ("HTTP1" if alpn else "None")
        path = self.entry_path.get()
        if not path.startswith("/"): path = "/" + path

        stream_settings = {
            "network": net_type,
            "security": sec,
            "sockopt": {"domainStrategy": "UseIP", "tcpFastOpen": True}
        }
        
        if self.var_frag_enable.get() == 1:
            stream_settings["sockopt"]["fragment"] = self.fragment_settings
        
        if net_type == "ws":
            stream_settings["wsSettings"] = {"host": self.entry_host.get(), "path": path}
        elif net_type == "grpc":
            stream_settings["grpcSettings"] = {"serviceName": path.lstrip("/"), "multiMode": False}
        elif net_type == "tcp":
            stream_settings["tcpSettings"] = {"header": {"type": "http", "request": {"path": [path], "headers": {"Host":[self.entry_host.get()]}}}}

        if sec == "tls" and alpn:
            stream_settings["tlsSettings"] = {"serverName": self.entry_host.get(), "alpn": alpn.split(","), "fingerprint": "chrome"}

        config = {
          "remarks": f"🌍{cc} | {data['ip']}:{data['port']} | {net_type.upper()} | {alpn_lbl} | DL:{data.get('dl', 0)}K | {sec.upper()}",
          "dns": {"servers": [{"address": data['dns_ip'], "tag": "remote-dns"}]},
          "inbounds":[{"listen": "127.0.0.1", "port": 10808, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}, "sniffing": {"destOverride":["http", "tls"], "enabled": True, "routeOnly": True}}],
          "outbounds":[
            {
              "protocol": "vless",
              "settings": {"vnext": [{"address": data['ip'], "port": data['port'], "users":[{"id": self.entry_uuid.get(), "encryption": "none"}]}]},
              "streamSettings": stream_settings
            },
            {"protocol": "dns", "tag": "dns-out"},
            {"protocol": "freedom", "tag": "direct"}
          ],
          "routing": {"domainStrategy": "IPIfNonMatch", "rules":[{"inboundTag": ["remote-dns"], "outboundTag": "proxy", "type": "field"}, {"network": "tcp", "outboundTag": "proxy", "type": "field"}]}
        }

        safe_ip = data['ip'].replace(':', '_')
        filename = f"Config_{index}_{cc}_{sec}_{net_type}_{alpn_lbl}_{data['port']}_{safe_ip}.json"
        try:
            with open(os.path.join(self.configs_dir, filename), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except: pass

    def show_summary_popup(self, ips_found, configs_generated):
        popup = ctk.CTkToplevel(self)
        popup.title("Generation Report")
        popup.geometry("350x250")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=BG_PANEL)
        
        if ips_found == 0 or configs_generated == 0:
            ctk.CTkLabel(popup, text="⚠️", font=ctk.CTkFont(size=40)).pack(pady=(20,0))
            ctk.CTkLabel(popup, text="No configs were generated!", font=ctk.CTkFont(size=16, weight="bold"), text_color="red").pack(pady=10)
        else:
            ctk.CTkLabel(popup, text="✅", font=ctk.CTkFont(size=40)).pack(pady=(20,0))
            ctk.CTkLabel(popup, text="Success!", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack()
            
            ctk.CTkLabel(popup, text=f"Clean IPs Found: {ips_found}", font=ctk.CTkFont(size=14)).pack(pady=(10,2))
            ctk.CTkLabel(popup, text=f"Configs Generated: {configs_generated} (Top 15 IPs)", font=ctk.CTkFont(size=14)).pack(pady=(2,10))

            ctk.CTkButton(popup, text="📂 Go to Storage", fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold"), command=lambda: self.go_to_storage_from_popup(popup)).pack(pady=10)

    def go_to_storage_from_popup(self, popup_window):
        popup_window.destroy()
        if self.app_controller:
            self.app_controller.select_frame_by_name("storage")