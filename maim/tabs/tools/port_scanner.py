# tabs/tools/port_scanner.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import concurrent.futures
import socket
import time
import json
import random
import ipaddress
from datetime import datetime
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

try:
    from scapy.all import IP, TCP, sr1, ICMP, UDP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


class PortScannerTab:
    """تب پورت اسکنر حرفه‌ای با تشخیص سرویس، دستگاه و سیستم‌عامل (غیرهمزمان)"""

    # ---------- نگاشت پورت به نوع دستگاه ----------
    PORT_DEVICE_MAP = {
        554:   "Camera / DVR (RTSP)",
        80:    "Web Server / Device HTTP",
        443:   "Web Server / Device HTTPS",
        21:    "FTP Server",
        22:    "SSH Server",
        23:    "Telnet / IoT Device",
        25:    "SMTP Server",
        53:    "DNS Server",
        110:   "POP3 Server",
        143:   "IMAP Server",
        993:   "IMAPS Server",
        995:   "POP3S Server",
        3306:  "MySQL Database",
        5432:  "PostgreSQL Database",
        3389:  "Remote Desktop (RDP)",
        5900:  "VNC Server",
        8080:  "HTTP Proxy / Alt Web Server",
        8443:  "HTTPS Alt Web Server",
        9100:  "Printer (JetDirect)",
        161:   "SNMP Agent (Network Device)",
        502:   "Modbus (PLC/Industrial)",
        1883:  "MQTT (IoT Broker)",
    }

    TTL_OS_GUESS = {
        64:   "Linux / Unix / BSD",
        128:  "Windows",
        255:  "Network Device (Cisco, etc.)",
    }

    def __init__(self, parent, tabview):
        self.parent = parent
        self.tab = tabview.add("Port Scanner")
        self.scan_stop_flag = False
        self.scan_results = []
        self.device_hints = set()
        self.os_guess = None
        self.setup_ui()

    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        scroll.grid_columnconfigure(0, weight=1)

        # Mode Selection
        mode_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        mode_frame.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="ew")

        ctk.CTkLabel(mode_frame, text="🔧 Scan Mode:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=15)

        self.scan_mode = ctk.StringVar(value="TCP Connect")
        mode_seg = ctk.CTkSegmentedButton(mode_frame, values=["TCP Connect", "SYN Scan (Stealth)", "UDP Scan"],
                                         variable=self.scan_mode, selected_color=CF_ORANGE, selected_hover_color=CF_ORANGE_HOVER)
        mode_seg.pack(side="left", padx=10)

        if not SCAPY_AVAILABLE:
            mode_seg.configure(state="disabled")
            ctk.CTkLabel(mode_frame, text="⚠️ Scapy not installed! Only TCP Connect available.",
                        text_color="#EF5350", font=ctk.CTkFont(size=12)).pack(side="left", padx=15)

        # Target Input
        target_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        target_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        target_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(target_frame, text="🎯 Target (IP or Domain):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.entry_target = ctk.CTkEntry(target_frame, placeholder_text="e.g. 1.1.1.1, google.com, or 192.168.1.1-192.168.1.10")
        self.entry_target.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ew")

        # Port Range
        port_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        port_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        port_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(port_frame, text="📡 Port Range:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")

        preset_frame = ctk.CTkFrame(port_frame, fg_color="transparent")
        preset_frame.grid(row=0, column=1, padx=15, pady=15, sticky="e")

        ctk.CTkButton(preset_frame, text="Common", width=80, fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE,
                     command=lambda: self.set_port_range("21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,3306,3389,5432,5900,6379,8080,8443,27017")).pack(side="left", padx=5)
        ctk.CTkButton(preset_frame, text="Web", width=80, fg_color="transparent", border_width=1,
                     border_color="#29B6F6", text_color="#29B6F6",
                     command=lambda: self.set_port_range("80,443,8080,8443,2052,2082,2083,2086,2087,2095,2096")).pack(side="left", padx=5)
        ctk.CTkButton(preset_frame, text="All", width=80, fg_color="transparent", border_width=1,
                     border_color="#EF5350", text_color="#EF5350",
                     command=lambda: self.set_port_range("1-65535")).pack(side="left", padx=5)

        self.entry_port_range = ctk.CTkEntry(port_frame, placeholder_text="e.g. 1-1000 or 22,80,443")
        self.entry_port_range.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")
        self.entry_port_range.insert(0, "1-1024")

        # Settings
        settings_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        settings_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(settings_frame, text="⚙️ Settings:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.lbl_threads = ctk.CTkLabel(settings_frame, text="Threads: 100")
        self.lbl_threads.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="w")
        self.slider_threads = ctk.CTkSlider(settings_frame, from_=10, to=500, number_of_steps=49,
                                           progress_color=CF_ORANGE,
                                           command=lambda v: self.lbl_threads.configure(text=f"Threads: {int(v)}"))
        self.slider_threads.set(100)
        self.slider_threads.grid(row=0, column=2, padx=15, pady=(15, 5), sticky="ew")

        self.lbl_timeout = ctk.CTkLabel(settings_frame, text="Timeout: 1.0s")
        self.lbl_timeout.grid(row=1, column=1, padx=10, pady=(5, 15), sticky="w")
        self.slider_timeout = ctk.CTkSlider(settings_frame, from_=0.3, to=5.0, number_of_steps=47,
                                           progress_color="#29B6F6",
                                           command=lambda v: self.lbl_timeout.configure(text=f"Timeout: {float(v):.1f}s"))
        self.slider_timeout.set(1.0)
        self.slider_timeout.grid(row=1, column=2, padx=15, pady=(5, 15), sticky="ew")

        check_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        check_frame.grid(row=0, column=3, rowspan=2, padx=15, pady=10, sticky="nsew")

        self.var_ping = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(check_frame, text="🔍 Live Host Discovery", variable=self.var_ping,
                       fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER).pack(anchor="w", pady=5)
        self.var_banner = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(check_frame, text="📝 Service Detection", variable=self.var_banner,
                       fg_color="#29B6F6", hover_color="#0D47A1").pack(anchor="w", pady=5)
        self.var_os = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(check_frame, text="💻 OS Detection (Basic)", variable=self.var_os,
                       fg_color="#AB47BC", hover_color="#6A1B9A").pack(anchor="w", pady=5)

        # Action Buttons
        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        action_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_start = ctk.CTkButton(action_frame, text="▶ START SCAN", fg_color=CF_ORANGE, text_color="black",
                                      hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold", size=14),
                                      command=self.start_scan)
        self.btn_start.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        self.btn_stop = ctk.CTkButton(action_frame, text="⏹ STOP", fg_color="#C62828", hover_color="#8E0000",
                                     font=ctk.CTkFont(weight="bold", size=14), state="disabled",
                                     command=self.stop_scan)
        self.btn_stop.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkButton(action_frame, text="📋 Copy Results", fg_color="#2E7D32", hover_color="#1B5E20",
                     font=ctk.CTkFont(weight="bold"), command=self.copy_results).grid(row=0, column=2, padx=5, pady=10, sticky="ew")
        ctk.CTkButton(action_frame, text="💾 Export (JSON/CSV)", fg_color="#1565C0", hover_color="#0D47A1",
                     font=ctk.CTkFont(weight="bold"), command=self.export_results).grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        # Status
        self.scan_status = ctk.CTkLabel(scroll, text="Ready", text_color="gray")
        self.scan_status.grid(row=5, column=0, padx=20, pady=5, sticky="w")

        self.scan_progress = ctk.CTkProgressBar(scroll, progress_color=CF_ORANGE)
        self.scan_progress.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        self.scan_progress.set(0)

        ctk.CTkLabel(scroll, text="Scan Results:", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, padx=20, pady=(15, 5), sticky="w")

        self.results_text = ctk.CTkTextbox(scroll, height=300, font=ctk.CTkFont(family="Consolas", size=12),
                                          fg_color="#121212", border_color="gray30", border_width=1)
        self.results_text.grid(row=8, column=0, padx=20, pady=(0, 20), sticky="ew")

    # ======================== Helpers ========================
    def set_port_range(self, range_str):
        self.entry_port_range.delete(0, "end")
        self.entry_port_range.insert(0, range_str)

    def parse_port_range(self, range_str):
        ports = set()
        parts = range_str.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    start, end = max(1, min(start, 65535)), max(1, min(end, 65535))
                    if start <= end:
                        ports.update(range(start, end + 1))
                except ValueError:
                    pass
            else:
                try:
                    port = int(part)
                    if 1 <= port <= 65535:
                        ports.add(port)
                except ValueError:
                    pass
        return sorted(ports)

    def parse_targets(self, target_str):
        targets = []
        target_str = target_str.strip()
        if '-' in target_str and '.' in target_str:
            parts = target_str.split('-')
            if len(parts) == 2:
                try:
                    start_ip, end_ip = parts[0].strip(), parts[1].strip()
                    start_parts = list(map(int, start_ip.split('.')))
                    end_parts = list(map(int, end_ip.split('.')))
                    if len(start_parts) == 4 and len(end_parts) == 4:
                        start_num = (start_parts[0] << 24) + (start_parts[1] << 16) + (start_parts[2] << 8) + start_parts[3]
                        end_num = (end_parts[0] << 24) + (end_parts[1] << 16) + (end_parts[2] << 8) + end_parts[3]
                        for num in range(start_num, end_num + 1):
                            targets.append(f"{(num >> 24) & 255}.{(num >> 16) & 255}.{(num >> 8) & 255}.{num & 255}")
                except ValueError:
                    pass
        elif ',' in target_str:
            for item in target_str.split(','):
                item = item.strip()
                if item:
                    targets.append(item)
        else:
            targets.append(target_str)
        resolved_targets = []
        for target in targets:
            try:
                socket.inet_aton(target)
                resolved_targets.append(target)
            except socket.error:
                try:
                    resolved_targets.append(socket.gethostbyname(target))
                except socket.gaierror:
                    self.log(f"⚠️ Could not resolve: {target}")
        return resolved_targets

    def ping_host(self, ip, timeout=2):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                return s.connect_ex((ip, 443)) == 0
        except:
            return False

    # ======================== Scan functions ========================
    def tcp_connect_scan(self, ip, port, timeout):
        if self.scan_stop_flag:
            return None
        try:
            start = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                elapsed = int((time.time() - start) * 1000)
                return {"ip": ip, "port": port, "status": "OPEN" if result == 0 else "CLOSED", "time": elapsed}
        except:
            return {"ip": ip, "port": port, "status": "FILTERED", "time": 0}

    def _syn_scan(self, ip, port, timeout):
        if self.scan_stop_flag or not SCAPY_AVAILABLE:
            return None
        try:
            start = time.time()
            pkt = sr1(IP(dst=ip)/TCP(dport=port, flags="S"), timeout=timeout, verbose=0)
            elapsed = int((time.time() - start) * 1000)
            if pkt and pkt.haslayer(TCP):
                flags = pkt.getlayer(TCP).flags
                if flags == 0x12:
                    sr1(IP(dst=ip)/TCP(dport=port, flags="R"), timeout=1, verbose=0)
                    ttl = pkt.getlayer(IP).ttl if pkt.haslayer(IP) else None
                    return {"ip": ip, "port": port, "status": "OPEN", "time": elapsed, "ttl": ttl}
                elif flags == 0x14:
                    return {"ip": ip, "port": port, "status": "CLOSED", "time": elapsed, "ttl": None}
            return {"ip": ip, "port": port, "status": "FILTERED", "time": elapsed, "ttl": None}
        except Exception:
            return {"ip": ip, "port": port, "status": "ERROR", "time": 0, "ttl": None}

    def _udp_scan(self, ip, port, timeout):
        if self.scan_stop_flag or not SCAPY_AVAILABLE:
            return None
        try:
            start = time.time()
            pkt = sr1(IP(dst=ip)/UDP(dport=port), timeout=timeout, verbose=0)
            elapsed = int((time.time() - start) * 1000)
            if pkt is None:
                return {"ip": ip, "port": port, "status": "OPEN|FILTERED", "time": elapsed, "ttl": None}
            if pkt.haslayer(ICMP):
                icmp_type = pkt.getlayer(ICMP).type
                icmp_code = pkt.getlayer(ICMP).code
                if icmp_type == 3 and icmp_code == 3:
                    ttl = pkt.getlayer(IP).ttl if pkt.haslayer(IP) else None
                    return {"ip": ip, "port": port, "status": "CLOSED", "time": elapsed, "ttl": ttl}
            return {"ip": ip, "port": port, "status": "UNKNOWN", "time": elapsed, "ttl": None}
        except Exception:
            return {"ip": ip, "port": port, "status": "ERROR", "time": 0, "ttl": None}

    # ======================== Banner & Service (Async) ========================
    def _grab_banner_tcp(self, ip: str, port: int, timeout: float = 1.5) -> str:
        """بنر TCP سریع (timeout کمتر)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            if port in (80, 8080):
                sock.send(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
            elif port == 25:
                sock.send(b"EHLO test\r\n")
            banner = sock.recv(256)
            sock.close()
            return banner.decode('utf-8', errors='ignore').strip().replace('\r\n', ' | ')
        except:
            return ""

    def _identify_service(self, port: int, banner: str) -> str:
        if port == 21 or "FTP" in banner.upper():
            return "FTP"
        if port == 22 or "SSH" in banner:
            return "SSH"
        if port == 23 or "Telnet" in banner:
            return "Telnet"
        if port == 25 or "SMTP" in banner.upper():
            return "SMTP"
        if port in (80, 8080):
            if "HTTP" in banner or banner.startswith("HTTP"):
                for line in banner.split('|'):
                    if line.lower().startswith("server:"):
                        return f"HTTP ({line.split(':',1)[1].strip()})"
                return "HTTP"
        if port in (443, 8443):
            return "HTTPS"
        if port == 3306:
            return "MySQL"
        if port == 5432:
            return "PostgreSQL"
        if port == 3389:
            return "RDP"
        if port == 554:
            return "RTSP (Camera/DVR)"
        if port == 161:
            return "SNMP"
        if port == 502:
            return "Modbus"
        if banner:
            return banner[:60]
        return "Unknown"

    def _guess_device(self, port: int, service: str, banner: str) -> str:
        if port in self.PORT_DEVICE_MAP:
            return self.PORT_DEVICE_MAP[port]
        banner_lower = banner.lower()
        if "camera" in banner_lower or "nvr" in banner_lower or "dvr" in banner_lower:
            return "Camera / DVR / NVR"
        if "router" in banner_lower or "switch" in banner_lower or "cisco" in banner_lower:
            return "Network Device (Router/Switch)"
        if "printer" in banner_lower or "ipp" in banner_lower:
            return "Printer"
        if "linux" in banner_lower or "ubuntu" in banner_lower or "debian" in banner_lower:
            return "Linux Server"
        if "windows" in banner_lower:
            return "Windows Host"
        if "telnet" in banner_lower:
            return "IoT / Embedded Device"
        if "HTTP" in service:
            return "Web Server"
        if "SSH" in service:
            return "Linux / Network Device"
        if "RDP" in service:
            return "Windows Host"
        return "Unknown"

    def _guess_os(self, ttl: int) -> str:
        if ttl is None:
            return ""
        for ttl_range, os_name in self.TTL_OS_GUESS.items():
            if abs(ttl - ttl_range) <= 2:
                return os_name
        return ""

    # ======================== Logging ========================
    def log(self, text):
        def _log():
            self.results_text.insert("end", text + "\n")
            self.results_text.see("end")
        self.parent.after(0, _log)

    # ======================== Scan Control ========================
    def start_scan(self):
        target_input = self.entry_target.get().strip()
        port_input = self.entry_port_range.get().strip()
        if not target_input or not port_input:
            messagebox.showerror("Error", "Please enter target and port range!")
            return
        ports = self.parse_port_range(port_input)
        targets = self.parse_targets(target_input)
        if not ports or not targets:
            messagebox.showerror("Error", "Invalid ports or targets!")
            return
        if self.var_ping.get():
            self.log(f"\n🔍 Checking which hosts are alive...")
            alive_targets = []
            for ip in targets:
                if self.ping_host(ip):
                    alive_targets.append(ip)
                    self.log(f"  ✅ {ip} is alive")
                else:
                    self.log(f"  ❌ {ip} is down or unreachable")
            if not alive_targets:
                self.log("\n❌ No alive hosts found! Scan aborted.")
                return
            targets = alive_targets
        self.scan_stop_flag = False
        self.scan_results = []
        self.device_hints = set()
        self.os_guess = None
        self.results_text.delete("1.0", "end")
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.scan_progress.set(0)
        total_scans = len(targets) * len(ports)
        self.scan_status.configure(text=f"Scanning {len(targets)} target(s) x {len(ports)} ports...", text_color=CF_ORANGE)
        threading.Thread(target=self._run_scan, args=(targets, ports, total_scans), daemon=True).start()

    def _run_scan(self, targets, ports, total_scans):
        timeout = self.slider_timeout.get()
        max_workers = int(self.slider_threads.get())
        scan_mode = self.scan_mode.get()
        do_banner = self.var_banner.get()
        do_os = self.var_os.get()

        if scan_mode == "SYN Scan (Stealth)":
            if not SCAPY_AVAILABLE:
                self.log("\n❌ Scapy is required for SYN Scan. Install Scapy and try again.")
                self._finish_scan(0)
                return
            scan_func = self._syn_scan
            self.log(f"\n🛡️ Starting SYN Stealth Scan...")
        elif scan_mode == "UDP Scan":
            if not SCAPY_AVAILABLE:
                self.log("\n❌ Scapy is required for UDP Scan. Install Scapy and try again.")
                self._finish_scan(0)
                return
            scan_func = self._udp_scan
            self.log(f"\n📡 Starting UDP Scan...")
        else:
            scan_func = self.tcp_connect_scan
            self.log(f"\n🔗 Starting TCP Connect Scan...")

        # Thread pool برای بنرگیری (جداگانه، حداکثر ۱۰ همزمان)
        banner_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        banner_futures = []   # لیست (ip, port, future)

        scanned = 0
        for ip in targets:
            self.log(f"\n🌐 Scanning {ip}...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(scan_func, ip, port, timeout): port for port in ports}
                for future in concurrent.futures.as_completed(futures):
                    if self.scan_stop_flag:
                        executor.shutdown(wait=False, cancel_futures=True)
                        banner_executor.shutdown(wait=False, cancel_futures=True)
                        self.log("\n⚠️ Scan stopped by user!")
                        self._finish_scan(0)
                        return
                    scanned += 1
                    result = future.result()
                    if result and "OPEN" in result.get("status", ""):
                        # ذخیره موقت بدون بنر
                        self.scan_results.append({
                            "ip": ip, "port": result['port'], "status": result['status'],
                            "time": result['time'], "ttl": result.get('ttl'),
                            "service": "", "banner": "", "device_hint": "", "os_hint": ""
                        })
                        # درخواست بنرگیری async (اگر فعال باشد و UDP نباشد)
                        if do_banner and scan_mode != "UDP Scan":
                            fut = banner_executor.submit(self._grab_banner_tcp, ip, result['port'], 1.5)
                            banner_futures.append((len(self.scan_results)-1, result['port'], fut))
                        # لاگ اولیه (فقط پورت)
                        self.log(f"  ✅ Port {result['port']} - OPEN ({result['time']}ms)")
                    progress = scanned / total_scans
                    self.parent.after(0, lambda p=progress: self.scan_progress.set(p))
                    self.parent.after(0, lambda s=scanned, t=total_scans: self.scan_status.configure(text=f"Progress: {s}/{t}"))

        # منتظر ماندن برای بنرها (حداکثر ۳ ثانیه اضافه)
        if do_banner and banner_futures:
            self.log("\n⏳ Collecting service banners...")
            for idx, port, fut in banner_futures:
                try:
                    banner = fut.result(timeout=2.0)
                except:
                    banner = ""
                if idx < len(self.scan_results):
                    entry = self.scan_results[idx]
                    entry['banner'] = banner
                    entry['service'] = self._identify_service(port, banner)
                    entry['device_hint'] = self._guess_device(port, entry['service'], banner)
                    entry['os_hint'] = self._guess_os(entry.get('ttl')) if do_os and entry.get('ttl') else ""
                    # جمع‌آوری حدس دستگاه
                    if entry['device_hint']:
                        self.device_hints.add(entry['device_hint'])
                    if entry['os_hint']:
                        self.os_guess = entry['os_hint']
                    # به‌روزرسانی لاگ
                    display = f"  ✅ Port {port} - OPEN ({entry['time']}ms)"
                    if entry['service']:
                        display += f" → {entry['service']}"
                    if entry['device_hint']:
                        display += f" | Device: {entry['device_hint']}"
                    if entry['os_hint']:
                        display += f" | OS: {entry['os_hint']}"
                    self.log(display)
        banner_executor.shutdown(wait=False)

        # خلاصه نهایی
        self.log("-" * 50)
        if self.device_hints:
            self.log(f"\n🔎 Device Detection Summary:")
            for dev in self.device_hints:
                self.log(f"  • {dev}")
        if self.os_guess:
            self.log(f"\n💻 OS Guess: {self.os_guess}")
        self._finish_scan(len(self.scan_results))

    def _finish_scan(self, count: int):
        if count > 0:
            self.log(f"\n✅ Scan completed! Found {count} open port(s).")
        else:
            self.log(f"\n✅ Scan completed. No open ports found.")
        self.parent.after(0, lambda: self.scan_status.configure(text="Scan completed!", text_color="#66BB6A"))
        self.parent.after(0, lambda: self.btn_start.configure(state="normal"))
        self.parent.after(0, lambda: self.btn_stop.configure(state="disabled"))

    def stop_scan(self):
        self.scan_stop_flag = True
        self.scan_status.configure(text="Stopping scan...", text_color="#FFA726")

    def copy_results(self):
        results = self.results_text.get("1.0", "end-1c").strip()
        if results:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(results)
            messagebox.showinfo("Success", "Results copied to clipboard!")

    def export_results(self):
        if not self.scan_results:
            messagebox.showwarning("Warning", "No scan results to export!")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv")])
        if file_path:
            if file_path.endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(self.scan_results, f, indent=2)
            else:
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=["ip", "port", "status", "time", "service", "banner", "device_hint", "os_hint"])
                    writer.writeheader()
                    writer.writerows(self.scan_results)
            messagebox.showinfo("Success", f"Results exported to:\n{file_path}")
