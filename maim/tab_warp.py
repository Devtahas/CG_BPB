# tab_warp.py
import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import threading
import ctypes
import time
import json
import requests
import datetime
import urllib3
import socket
import random
import concurrent.futures
import ipaddress
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK, DIRS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_core_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# ==========================================
# پنجره اسکنر پیشرفته و اختصاصی WARP
# ==========================================
class WarpScannerWindow(ctk.CTkToplevel):
    def __init__(self, parent, combo_endpoint, profile_path):
        super().__init__(parent)
        self.title("⚙️ Advanced WARP Scanner")
        self.geometry("650x650")
        self.attributes("-topmost", True)
        self.configure(fg_color=BG_DARK)
        self.combo_endpoint = combo_endpoint
        self.profile_path = profile_path

        self.config_file = os.path.join(DIRS["settings"], "Warp_Scanner_Config.json")
        self.stop_event = threading.Event()

        self.default_cidrs =["162.159.192.0/24", "162.159.193.0/24", "162.159.195.0/24", "188.114.96.0/24", "188.114.97.0/24", "188.114.98.0/24", "188.114.99.0/24"]
        self.default_ports =[2408, 1701, 854, 500, 4500, 894, 908]
        
        self.custom_cidrs = self.default_cidrs.copy()
        self.custom_ports = self.default_ports.copy()
        self.threads_val = 50
        self.samples_val = 20

        self.load_config()
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        left_frame.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="nsew")
        
        ctk.CTkLabel(left_frame, text="🌐 Target IPs & Ranges", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 5))
        
        self.cidr_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="#121212", corner_radius=10)
        self.cidr_scroll.pack(fill="both", expand=True, padx=15, pady=5)
        
        cidr_add_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        cidr_add_frame.pack(fill="x", padx=15, pady=(5, 15))
        self.entry_cidr = ctk.CTkEntry(cidr_add_frame, placeholder_text="e.g. 1.2.3.4, 5.6.7.0/24")
        self.entry_cidr.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(cidr_add_frame, text="Add", width=50, fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, command=self.add_cidr).pack(side="left")

        right_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        right_frame.grid(row=0, column=1, padx=(5, 15), pady=15, sticky="nsew")
        
        ctk.CTkLabel(right_frame, text="🔌 Target Ports", font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15, 5))
        
        self.port_scroll = ctk.CTkScrollableFrame(right_frame, height=120, fg_color="#121212", corner_radius=10)
        self.port_scroll.pack(fill="both", expand=True, padx=15, pady=5)
        
        port_add_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        port_add_frame.pack(fill="x", padx=15, pady=(5, 15))
        self.entry_port = ctk.CTkEntry(port_add_frame, placeholder_text="e.g. 2408, 1701")
        self.entry_port.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(port_add_frame, text="Add", width=50, fg_color="#29B6F6", text_color="black", hover_color="#0D47A1", command=self.add_port).pack(side="left")

        settings_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        settings_frame.pack(fill="x", padx=15, pady=5)
        
        self.lbl_threads = ctk.CTkLabel(settings_frame, text=f"Threads: {self.threads_val}")
        self.lbl_threads.pack(anchor="w")
        self.slider_threads = ctk.CTkSlider(settings_frame, from_=10, to=200, progress_color=CF_ORANGE, command=lambda v: self.lbl_threads.configure(text=f"Threads: {int(v)}"))
        self.slider_threads.set(self.threads_val)
        self.slider_threads.pack(fill="x", pady=(0, 10))

        self.lbl_samples = ctk.CTkLabel(settings_frame, text=f"IPs per Range: {self.samples_val}")
        self.lbl_samples.pack(anchor="w")
        self.slider_samples = ctk.CTkSlider(settings_frame, from_=5, to=256, progress_color="#29B6F6", command=lambda v: self.lbl_samples.configure(text=f"IPs per Range: {int(v)}"))
        self.slider_samples.set(self.samples_val)
        self.slider_samples.pack(fill="x")

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")
        
        self.lbl_status = ctk.CTkLabel(bottom_frame, text="Status: Ready", text_color="gray", font=ctk.CTkFont(weight="bold"))
        self.lbl_status.pack(pady=5)

        self.progressbar = ctk.CTkProgressBar(bottom_frame, progress_color=CF_ORANGE)
        self.progressbar.pack(fill="x", pady=5)
        self.progressbar.set(0)

        action_btns = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        action_btns.pack(fill="x", pady=5)
        
        ctk.CTkButton(action_btns, text="🔄 Reset", width=80, fg_color="transparent", border_width=1, border_color="gray50", command=self.reset_defaults).pack(side="left", padx=5)
        
        self.btn_start = ctk.CTkButton(action_btns, text="▶ START", fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold"), command=self.start_scan)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=5)

        self.btn_stop = ctk.CTkButton(action_btns, text="⏹ STOP", fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(weight="bold"), state="disabled", command=self.stop_scan)
        self.btn_stop.pack(side="right", expand=True, fill="x", padx=5)

        self.refresh_cidr_ui()
        self.refresh_port_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.custom_cidrs = data.get("cidrs", self.default_cidrs.copy())
                    self.custom_ports = data.get("ports", self.default_ports.copy())
                    self.threads_val = data.get("threads", 50)
                    self.samples_val = data.get("samples", 20)
            except: pass

    def save_config(self):
        data = {"cidrs": self.custom_cidrs, "ports": self.custom_ports, "threads": int(self.slider_threads.get()), "samples": int(self.slider_samples.get())}
        try:
            with open(self.config_file, 'w') as f: json.dump(data, f)
        except: pass

    def on_close(self):
        self.save_config()
        self.stop_event.set()
        self.destroy()

    def reset_defaults(self):
        self.custom_cidrs = self.default_cidrs.copy()
        self.custom_ports = self.default_ports.copy()
        self.refresh_cidr_ui()
        self.refresh_port_ui()

    def refresh_cidr_ui(self):
        for widget in self.cidr_scroll.winfo_children(): widget.destroy()
        for cidr in self.custom_cidrs:
            row = ctk.CTkFrame(self.cidr_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=cidr, anchor="w").pack(side="left", padx=5)
            ctk.CTkButton(row, text="❌", width=25, fg_color="transparent", text_color="#EF5350", hover_color="#3A1D1D", command=lambda c=cidr: self.remove_cidr(c)).pack(side="right")

    def add_cidr(self):
        raw_input = self.entry_cidr.get().replace(",", " ").split()
        added = False
        for item in raw_input:
            item = item.strip()
            if not item: continue
            try:
                ipaddress.ip_network(item, strict=False)
                if item not in self.custom_cidrs:
                    self.custom_cidrs.append(item)
                    added = True
            except ValueError: pass
        if added:
            self.entry_cidr.delete(0, "end")
            self.refresh_cidr_ui()

    def remove_cidr(self, cidr):
        if cidr in self.custom_cidrs:
            self.custom_cidrs.remove(cidr)
            self.refresh_cidr_ui()

    def refresh_port_ui(self):
        for widget in self.port_scroll.winfo_children(): widget.destroy()
        for port in sorted(self.custom_ports):
            row = ctk.CTkFrame(self.port_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=str(port), anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkButton(row, text="❌", width=25, fg_color="transparent", text_color="#EF5350", hover_color="#3A1D1D", command=lambda p=port: self.remove_port(p)).pack(side="right")

    def add_port(self):
        raw_input = self.entry_port.get().replace(",", " ").split()
        added = False
        for item in raw_input:
            item = item.strip()
            if not item: continue
            try:
                p = int(item)
                if 0 < p < 65536 and p not in self.custom_ports:
                    self.custom_ports.append(p)
                    added = True
            except ValueError: pass
        if added:
            self.entry_port.delete(0, "end")
            self.refresh_port_ui()

    def remove_port(self, port):
        if port in self.custom_ports:
            self.custom_ports.remove(port)
            self.refresh_port_ui()

    def start_scan(self):
        if not self.custom_cidrs or not self.custom_ports:
            messagebox.showwarning("Warning", "Please add at least one IP/CIDR and one Port.")
            return

        self.save_config()
        self.stop_event.clear()
        
        self.btn_start.configure(state="disabled", text="⏳ SCANNING...")
        self.btn_stop.configure(state="normal", text="⏹ STOP")
        self.lbl_status.configure(text="Generating IP list...", text_color=CF_ORANGE)
        self.progressbar.set(0)
        
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def stop_scan(self):
        self.stop_event.set()
        self.btn_stop.configure(state="disabled", text="⏳ STOPPING...")
        self.lbl_status.configure(text="Halting scan... processing found IPs.", text_color="#FFA726")

    def _scan_thread(self):
        scan_ips =[]
        samples_count = int(self.slider_samples.get())
        
        for cidr in self.custom_cidrs:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                if net.num_addresses <= samples_count:
                    scan_ips.extend([str(ip) for ip in net])
                else:
                    selected = set()
                    while len(selected) < samples_count:
                        selected.add(str(net[random.randint(0, net.num_addresses - 1)]))
                    scan_ips.extend(list(selected))
            except: pass

        endpoints_to_test =[(ip, port) for ip in scan_ips for port in self.custom_ports]
        total_tasks = len(endpoints_to_test)
        
        if total_tasks == 0:
            self.after(0, lambda: self.lbl_status.configure(text="No valid IPs to scan!", text_color="#EF5350"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="▶ START SCAN"))
            self.after(0, lambda: self.btn_stop.configure(state="disabled"))
            return

        self.after(0, lambda: self.lbl_status.configure(text=f"Scanning {total_tasks} Endpoints...", text_color=CF_ORANGE))
        
        results =[]
        completed = 0
        max_threads = int(self.slider_threads.get())

        def ping_endpoint(ip, port):
            if self.stop_event.is_set():
                return None
            try:
                start_time = time.time()
                # پینگ روی پورت 443 انجام میشه تا آی‌پی های زنده کلودفلر (بدون درگیری با بلاک UDP) پیدا بشن
                with socket.create_connection((ip, 443), timeout=1.5):
                    latency = int((time.time() - start_time) * 1000)
                    return (f"{ip}:{port}", latency)
            except:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures =[executor.submit(ping_endpoint, ep[0], ep[1]) for ep in endpoints_to_test]
            for future in concurrent.futures.as_completed(futures):
                if self.stop_event.is_set():
                    break
                
                completed += 1
                res = future.result()
                if res:
                    results.append(res)
                
                pct = completed / total_tasks
                self.after(0, lambda p=pct, c=completed, t=total_tasks, f=len(results): 
                           (self.progressbar.set(p), self.lbl_status.configure(text=f"Progress: {c}/{t} | Found: {f}")))

        if results:
            results.sort(key=lambda x: x[1])
            top_endpoints = [r[0] for r in results[:20]] 
            best_ping = results[0][1]

            self.after(0, lambda: self.combo_endpoint.configure(values=top_endpoints))
            self.after(0, lambda: self.combo_endpoint.set(top_endpoints[0]))
            
            try:
                if os.path.exists(self.profile_path):
                    with open(self.profile_path, 'r') as f: data = json.load(f)
                    data["endpoint"] = top_endpoints[0]
                    with open(self.profile_path, 'w') as f: json.dump(data, f)
            except: pass

            status_msg = f"✅ Stopped manually! Best Ping: {best_ping}ms." if self.stop_event.is_set() else f"✅ Done! Best Ping: {best_ping}ms."
            self.after(0, lambda m=status_msg: self.lbl_status.configure(text=m, text_color="#66BB6A"))
            
            if not self.stop_event.is_set():
                self.after(0, lambda: messagebox.showinfo("Scan Complete", f"Successfully found {len(results)} active endpoints.\n\nBest Endpoint ({top_endpoints[0]}) with {best_ping}ms ping has been auto-selected!"))
        else:
            msg = "❌ Stopped. No endpoints found." if self.stop_event.is_set() else "❌ Scan Failed. No endpoints are reachable."
            self.after(0, lambda m=msg: self.lbl_status.configure(text=m, text_color="#EF5350"))

        self.after(0, lambda: self.btn_start.configure(state="normal", text="▶ START SCAN"))
        self.after(0, lambda: self.btn_stop.configure(state="disabled", text="⏹ STOP"))


# ==========================================
# فریم اصلی تب WARP
# ==========================================
class WarpFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.is_connected = False
        self.tunnel_name = "nettools_warp"
        
        self.profile_path = os.path.join(DIRS["settings"], "warp_profile.json")
        self.temp_conf_path = os.path.join(DIRS["settings"], f"{self.tunnel_name}.conf")

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🌪️ WARP (Amnezia Anti-DPI)", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        self.status_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.status_frame.grid(row=1, column=0, padx=40, pady=20, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Status: Disconnected", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.btn_connect = ctk.CTkButton(self.status_frame, text="▶ CONNECT", width=160, fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14), command=self.toggle_warp)
        self.btn_connect.grid(row=0, column=2, padx=20, pady=20, sticky="e")

        box_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        box_frame.grid(row=2, column=0, padx=40, pady=10, sticky="nsew")
        box_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(box_frame, text="🚀 WARP Configuration", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        ctk.CTkLabel(box_frame, text="1. Scan or Select an Endpoint  2. Connect. (If nothing opens, try another Port from the list)", text_color="gray").grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="w")

        ctk.CTkLabel(box_frame, text="Assigned IP:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.lbl_ip = ctk.CTkLabel(box_frame, text="Not Generated Yet", text_color="#29B6F6", font=ctk.CTkFont(family="Consolas", size=14))
        self.lbl_ip.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        ep_frame = ctk.CTkFrame(box_frame, fg_color="transparent")
        ep_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        ctk.CTkLabel(ep_frame, text="Endpoint (IP:Port):", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        self.combo_endpoint = ctk.CTkComboBox(ep_frame, width=220, font=ctk.CTkFont(family="Consolas"), dropdown_fg_color="#18181B")
        self.combo_endpoint.pack(side="left", padx=(0, 10))
        
        self.btn_open_scanner = ctk.CTkButton(ep_frame, text="⚙️ Advanced Scanner", width=140, fg_color="transparent", border_width=1, border_color="#29B6F6", text_color="#29B6F6", hover_color="#0D47A1", command=self.open_advanced_scanner)
        self.btn_open_scanner.pack(side="left", padx=10)

        self.btn_generate = ctk.CTkButton(box_frame, text="🔄 Generate New Identity", width=180, fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.generate_new_warp)
        self.btn_generate.grid(row=4, column=0, columnspan=2, padx=20, pady=30, sticky="w")

        self.load_default_endpoints()
        self.load_profile()

    def load_default_endpoints(self):
        default_eps =[
            "188.114.97.170:1701", "162.159.192.73:854", 
            "188.114.98.222:500", "162.159.193.11:4500", "162.159.192.1:2408"
        ]
        self.combo_endpoint.configure(values=default_eps)
        self.combo_endpoint.set(default_eps[0])

    def open_advanced_scanner(self):
        if self.is_connected:
            messagebox.showwarning("Warning", "Please Disconnect WARP before running the scanner.")
            return
        WarpScannerWindow(self, self.combo_endpoint, self.profile_path)

    def load_profile(self):
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r') as f:
                    data = json.load(f)
                    self.lbl_ip.configure(text=f"{data.get('v4', 'Unknown')}")
                    if "endpoint" in data and data["endpoint"]:
                        current_vals = self.combo_endpoint.cget("values")
                        if data["endpoint"] not in current_vals:
                            current_vals.append(data["endpoint"])
                            self.combo_endpoint.configure(values=current_vals)
                        self.combo_endpoint.set(data["endpoint"])
            except: pass

    def generate_new_warp(self):
        if self.is_connected:
            messagebox.showwarning("Warning", "Please Disconnect WARP before generating a new identity!")
            return
        self.btn_generate.configure(state="disabled", text="⏳ Generating...")
        self.lbl_ip.configure(text="Communicating with API...", text_color="gray")
        threading.Thread(target=self._generate_thread, daemon=True).start()

    def _generate_thread(self):
        try:
            wg_exe = get_core_path(os.path.join("cores", "wireguard", "wg.exe"))
            if not os.path.exists(wg_exe):
                self.after(0, lambda: messagebox.showerror("Error", "wg.exe not found in 'cores/wireguard/'"))
                return

            priv_proc = subprocess.run([wg_exe, "genkey"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            private_key = priv_proc.stdout.strip()

            pub_proc = subprocess.run([wg_exe, "pubkey"], input=private_key, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            public_key = pub_proc.stdout.strip()

            url = "https://api.cloudflareclient.com/v0a884/reg"
            headers = {"Content-Type": "application/json; charset=UTF-8", "User-Agent": "okhttp/3.12.1"}
            payload = {"key": public_key, "install_id": "", "fcm_token": "", "tos": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "model": "Windows", "locale": "en_US"}

            resp = requests.post(url, json=payload, headers=headers, timeout=15, verify=False)
            resp.raise_for_status()
            result = resp.json()

            v4 = result['config']['interface']['addresses']['v4']
            v6 = result['config']['interface']['addresses']['v6']
            peer_pub = result['config']['peers'][0]['public_key']

            profile_data = {
                "private_key": private_key, "v4": v4, "v6": v6,
                "peer_pub": peer_pub, "endpoint": self.combo_endpoint.get()
            }

            with open(self.profile_path, 'w') as f:
                json.dump(profile_data, f)

            self.after(0, lambda: self.lbl_ip.configure(text=v4, text_color="#66BB6A"))
            self.after(0, lambda: messagebox.showinfo("Success", "New WARP Identity generated successfully!"))
        except Exception as e:
            self.after(0, lambda: self.lbl_ip.configure(text="Failed to generate", text_color="#EF5350"))
            self.after(0, lambda: messagebox.showerror("API Error", f"Failed to generate WARP account:\n{str(e)}"))
        finally:
            self.after(0, lambda: self.btn_generate.configure(state="normal", text="🔄 Generate New Identity"))

    def toggle_warp(self):
        if not self.is_connected: self.start_warp()
        else: self.stop_warp()

    def start_warp(self):
        if not is_admin():
            messagebox.showerror("Admin Required", "AmneziaWG needs Administrator privileges.\nPlease Run the app as Administrator.")
            return

        if not os.path.exists(self.profile_path):
            messagebox.showinfo("Wait", "Generating your first WARP Identity... Please wait.")
            self.btn_connect.configure(state="disabled")
            def gen_and_connect():
                self._generate_thread()
                if os.path.exists(self.profile_path): self.after(0, self._proceed_connection)
                else: self.after(0, lambda: self.btn_connect.configure(state="normal"))
            threading.Thread(target=gen_and_connect, daemon=True).start()
            return

        self._proceed_connection()

    def _proceed_connection(self):
        try:
            with open(self.profile_path, 'r') as f: data = json.load(f)
        except:
            self.btn_connect.configure(state="normal")
            return

        endpoint = self.combo_endpoint.get().strip()
        if not endpoint: endpoint = "188.114.97.170:1701"

        data["endpoint"] = endpoint
        with open(self.profile_path, 'w') as f: json.dump(data, f)

        # 🚀 تغییرات طلایی (Golden Config) برای دور زدن فیلترینگ اینترنت ایران
        # 1. اضافه شدن v6 به روتینگ برای جلوگیری از Blackhole شدن ترافیک مرورگرها
        # 2. تنظیم مقادیر Jc و سایزهای مجاز برای گول زدن DPI بدون مسدود شدن در کلودفلر
        conf_content = f"""[Interface]
PrivateKey = {data['private_key']}
Address = {data['v4']}/32, {data['v6']}/128
DNS = 1.1.1.1, 1.0.0.1, 8.8.8.8
MTU = 1120
Jc = 4
Jmin = 40
Jmax = 70
S1 = 0
S2 = 0
H1 = 1
H2 = 2
H3 = 3
H4 = 4

[Peer]
PublicKey = {data['peer_pub']}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {endpoint}
PersistentKeepalive = 15
"""
        with open(self.temp_conf_path, "w") as f: f.write(conf_content)

        awg_exe = get_core_path(os.path.join("cores", "wireguard", "amneziawg.exe"))
        if not os.path.exists(awg_exe):
            messagebox.showerror("Error", "amneziawg.exe not found!")
            return

        self.lbl_status.configure(text="Status: Creating AWG Tunnel...", text_color=CF_ORANGE)
        self.btn_connect.configure(state="disabled")
        self.combo_endpoint.configure(state="disabled")
        self.btn_open_scanner.configure(state="disabled")
        self.btn_generate.configure(state="disabled")
        
        threading.Thread(target=self._run_awg_background, args=(awg_exe,), daemon=True).start()

    def _run_awg_background(self, awg_exe):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            tunnel_service = f"AmneziaWGTunnel${self.tunnel_name}"

            check_sc = subprocess.run(["sc", "query", tunnel_service], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            if check_sc.returncode == 0:
                subprocess.run([awg_exe, "/uninstalltunnelservice", self.tunnel_name], creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
                time.sleep(1) 

            cmd =[awg_exe, "/installtunnelservice", self.temp_conf_path]
            res = subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            
            if res.returncode == 0:
                self.is_connected = True
                self.after(0, lambda: self.lbl_status.configure(text="Status: Connected (AmneziaWG TUN)", text_color="#66BB6A"))
                self.after(0, lambda: self.btn_connect.configure(text="⏹ DISCONNECT", fg_color="#C62828", hover_color="#8E0000", state="normal"))
            else:
                self.after(0, lambda: self.lbl_status.configure(text="Status: Failed to establish tunnel", text_color="#EF5350"))
                self.after(0, self._reset_ui_state)
        except Exception as e:
            self.after(0, self._reset_ui_state)

    def _reset_ui_state(self):
        self.btn_connect.configure(state="normal")
        self.combo_endpoint.configure(state="normal")
        self.btn_open_scanner.configure(state="normal")
        self.btn_generate.configure(state="normal")

    def stop_warp(self):
        awg_exe = get_core_path(os.path.join("cores", "wireguard", "amneziawg.exe"))
        tunnel_service = f"AmneziaWGTunnel${self.tunnel_name}"
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            check_sc = subprocess.run(["sc", "query", tunnel_service], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            if check_sc.returncode == 0:
                subprocess.run([awg_exe, "/uninstalltunnelservice", self.tunnel_name], creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
                time.sleep(0.5)
                subprocess.run(["sc", "stop", tunnel_service], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
            
        self.is_connected = False
        self.lbl_status.configure(text="Status: Disconnected", text_color="#EF5350")
        self.btn_connect.configure(text="▶ CONNECT", fg_color="#2E7D32", hover_color="#1B5E20")
        self._reset_ui_state()

    def stop_connection(self):
        self.stop_warp()