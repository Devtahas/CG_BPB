# tab_antifilter.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import concurrent.futures
import subprocess
import socket
import time
import os
import sys
import ctypes
import winreg

from config import CF_ORANGE, BG_PANEL, DIRS

def get_core_path(relative_path):
    if hasattr(sys, '_MEIPASS'): return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

MASSIVE_DNS_LIST = [
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9", "149.112.112.112", 
    "208.67.222.222", "208.67.220.220", "8.26.56.26", "8.20.247.20", 
    "94.140.14.14", "94.140.15.15", "1.1.1.2", "1.0.0.2", "76.76.19.19",
    "76.223.122.150", "185.228.168.9", "185.228.169.9", "198.101.242.72",
    "23.253.163.53", "178.22.122.100", "185.51.200.2", "78.157.42.100", 
    "78.157.42.101", "10.202.10.10", "10.202.10.11", "209.244.0.3", 
    "209.244.0.4", "64.6.64.6", "64.6.65.6", "84.200.69.80", "84.200.70.40",
    "1.1.1.3", "1.0.0.3", "114.114.114.114", "223.5.5.5", "180.76.76.76"
]

class AntiFilterFrame(ctk.CTkFrame):
    # دریافت app_controller برای سوئیچ کردن تب ها
    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.is_running = False
        self.current_process = None
        self.stop_event = threading.Event()
        self.active_interface = self.get_active_interface()

        # --- UI Setup ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🆘 Panic Button (Anti-Filter)", font=ctk.CTkFont(size=24, weight="bold"), text_color="#EF5350").pack(side="left", padx=40)

        desc = "Survival Mode: Chains multiple bypass protocols (DNS -> Tor -> Psiphon -> WARP).\nIf all fail, it acts as a Last Resort by auto-redirecting to the Deep CF Scanner."
        ctk.CTkLabel(self, text=desc, text_color="gray", justify="left").grid(row=1, column=0, padx=40, sticky="w")

        # --- Main Control Panel ---
        control_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        control_frame.grid(row=2, column=0, padx=40, pady=20, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_rowconfigure(1, weight=1)

        # Status Tracker
        self.tracker_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        self.tracker_frame.grid(row=0, column=0, pady=20, sticky="ew")
        
        self.lbl_step_dns = self.create_step_label(self.tracker_frame, "1. DNS", 0)
        self.lbl_step_tor = self.create_step_label(self.tracker_frame, "2. Tor", 1)
        self.lbl_step_psi = self.create_step_label(self.tracker_frame, "3. Psiphon", 2)
        self.lbl_step_wg  = self.create_step_label(self.tracker_frame, "4. WARP", 3)
        self.lbl_step_scan = self.create_step_label(self.tracker_frame, "5. Scanner", 4) # مرحله جدید

        # Console Output
        self.console = ctk.CTkTextbox(control_frame, height=200, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#121212", border_color="gray30", border_width=1)
        self.console.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Big Button
        self.btn_power = ctk.CTkButton(control_frame, text="🔥 INITIATE SURVIVAL MODE", height=60, fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(size=18, weight="bold"), command=self.toggle_mode)
        self.btn_power.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

    def create_step_label(self, parent, text, col):
        lbl = ctk.CTkLabel(parent, text=text, text_color="gray", font=ctk.CTkFont(weight="bold"))
        lbl.grid(row=0, column=col, padx=10)
        parent.grid_columnconfigure(col, weight=1)
        return lbl

    def log(self, text, color="white"):
        self.after(0, lambda: self.console.insert("end", text + "\n"))
        self.after(0, lambda: self.console.see("end"))

    def update_step(self, step_lbl, status):
        colors = {"wait": "gray", "active": CF_ORANGE, "success": "#66BB6A", "fail": "#EF5350"}
        self.after(0, lambda: step_lbl.configure(text_color=colors[status]))

    def get_active_interface(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.address == local_ip: return interface
        except: pass
        return "Wi-Fi"

    def set_windows_proxy(self, enable=True, server="127.0.0.1:9052"):
        try:
            internet_settings = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings', 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, server)
            else:
                winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(internet_settings)
            internet_set_option = ctypes.windll.wininet.InternetSetOptionW
            internet_set_option(0, 37, 0, 0)
            internet_set_option(0, 39, 0, 0)
        except Exception: pass

    def toggle_mode(self):
        if not is_admin():
            messagebox.showerror("Admin Required", "Survival Mode needs Administrator privileges.\nPlease restart the app as Administrator.")
            return

        if not self.is_running: self.start_engine()
        else: self.stop_engine()

    def start_engine(self):
        self.is_running = True
        self.stop_event.clear()
        self.console.delete("1.0", "end")
        self.btn_power.configure(text="⏹ ABORT OPERATION", fg_color="#424242", hover_color="#212121")
        
        [self.update_step(lbl, "wait") for lbl in [self.lbl_step_dns, self.lbl_step_tor, self.lbl_step_psi, self.lbl_step_wg, self.lbl_step_scan]]
        
        threading.Thread(target=self._survival_chain, daemon=True).start()

    def _survival_chain(self):
        # ---------------- PHASE 1: DNS ----------------
        self.update_step(self.lbl_step_dns, "active")
        self.log("[*] Phase 1: Initiating DNS Hunter...")
        best_dns = self._hunt_best_dns()
        
        if self.stop_event.is_set(): return
        if best_dns:
            self.log(f"[+] Best DNS Found: {best_dns['ip']} ({best_dns['ping']}ms)")
            self._apply_dns(best_dns['ip'])
            self.update_step(self.lbl_step_dns, "success")
        else:
            self.log("[-] All DNS failed. Using fallback 8.8.8.8")
            self._apply_dns("8.8.8.8")
            self.update_step(self.lbl_step_dns, "fail")

        # ---------------- PHASE 2: TOR ----------------
        if self.stop_event.is_set(): return
        self.update_step(self.lbl_step_tor, "active")
        self.log("\n[*] Phase 2: Starting Tor Engine...")
        tor_success = self._run_tor()
        if tor_success:
            self.log("[+] Tor connected successfully! System traffic routed.")
            self.update_step(self.lbl_step_tor, "success")
            self.after(0, lambda: self.btn_power.configure(text="✅ CONNECTED (Click to Disconnect)", fg_color="#2E7D32", hover_color="#1B5E20"))
            return
        
        self.update_step(self.lbl_step_tor, "fail")
        self._kill_process(self.current_process, "tor.exe")
        
        # ---------------- PHASE 3: PSIPHON ----------------
        if self.stop_event.is_set(): return
        self.update_step(self.lbl_step_psi, "active")
        self.log("\n[*] Phase 3: Tor Blocked. Trying Psiphon Fallback...")
        psi_success = self._run_psiphon()
        if psi_success:
            self.log("[+] Psiphon connected successfully! System traffic routed.")
            self.update_step(self.lbl_step_psi, "success")
            self.after(0, lambda: self.btn_power.configure(text="✅ CONNECTED (Click to Disconnect)", fg_color="#2E7D32", hover_color="#1B5E20"))
            return
            
        self.update_step(self.lbl_step_psi, "fail")
        self._kill_process(self.current_process, "psiphon3.exe")

        # ---------------- PHASE 4: WIREGUARD ----------------
        if self.stop_event.is_set(): return
        self.update_step(self.lbl_step_wg, "active")
        self.log("\n[*] Phase 4: Psiphon Blocked. Trying AmneziaWG (Warp)...")
        wg_success = self._run_wireguard()
        if wg_success:
            self.log("[+] WireGuard TUN connected successfully!")
            self.update_step(self.lbl_step_wg, "success")
            self.after(0, lambda: self.btn_power.configure(text="✅ CONNECTED (Click to Disconnect)", fg_color="#2E7D32", hover_color="#1B5E20"))
            return
            
        self.update_step(self.lbl_step_wg, "fail")
        
        # ---------------- PHASE 5: SCANNER FALLBACK ----------------
        if self.stop_event.is_set(): return
        self.update_step(self.lbl_step_scan, "active")
        self.log("\n❌ CRITICAL: All protocols failed. National Internet detected!")
        self.log("\n[*] Phase 5: Redirecting to Deep CF Scanner to hunt for live endpoints...")
        time.sleep(2) # کاربر متن را بخواند
        
        self.update_step(self.lbl_step_scan, "success")
        self.stop_engine(switch_to_scanner=True)

    def _hunt_best_dns(self):
        best = {"ip": None, "ping": 9999}
        lock = threading.Lock()
        def ping(ip):
            if self.stop_event.is_set(): return
            try:
                start = time.time()
                with socket.create_connection((ip, 53), timeout=1.5):
                    ms = int((time.time() - start) * 1000)
                    with lock:
                        if ms < best["ping"]:
                            best["ip"] = ip
                            best["ping"] = ms
            except: pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(ping, ip) for ip in MASSIVE_DNS_LIST]
            concurrent.futures.wait(futures)
        return best if best["ip"] else None

    def _apply_dns(self, ip):
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{self.active_interface}" source=static address="{ip}" primary'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.log(f"[*] Set Windows DNS to {ip}")
        except: pass

    def _run_tor(self):
        tor_exe = get_core_path(os.path.join("cores", "tor", "tor.exe"))
        tor_data = os.path.join(DIRS["settings"], "TorPanicData")
        os.makedirs(tor_data, exist_ok=True)
        cmd = [tor_exe, "DataDirectory", tor_data, "SocksPort", "9050", "HTTPTunnelPort", "9052", "Log", "notice stdout"]
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            start_wait = time.time()
            while time.time() - start_wait < 180:
                if self.stop_event.is_set(): return False
                line = self.current_process.stdout.readline()
                if not line: break
                txt = line.decode('utf-8', errors='ignore').strip()
                if "Bootstrapped" in txt:
                    import re
                    match = re.search(r'Bootstrapped (\d+)%', txt)
                    if match:
                        pct = int(match.group(1))
                        self.log(f"  -> Tor: {pct}%...")
                        if pct == 100:
                            self.set_windows_proxy(True, "127.0.0.1:9052")
                            return True
            return False
        except: return False

    def _run_psiphon(self):
        psi_exe = get_core_path(os.path.join("cores", "psiphon", "psiphon3.exe"))
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.current_process = subprocess.Popen([psi_exe], creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            ShowWindow = ctypes.windll.user32.ShowWindow
            def foreach_window(hwnd, lParam):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buff, length + 1)
                        if "Psiphon" in buff.value: ShowWindow(hwnd, 0)
                return True
            for _ in range(15):
                if self.stop_event.is_set(): return False
                EnumWindows(EnumWindowsProc(foreach_window), 0)
                time.sleep(1)
            return True 
        except: return False

    def _run_wireguard(self):
        awg_exe = get_core_path(os.path.join("cores", "wireguard", "amneziawg.exe"))
        conf_path = os.path.join(DIRS["settings"], "nettools_warp.conf")
        if not os.path.exists(conf_path): return False
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run([awg_exe, "/installtunnelservice", conf_path], creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            time.sleep(3)
            return True
        except: return False

    def _kill_process(self, proc, name):
        if proc:
            try: proc.terminate()
            except: pass
        os.system(f"taskkill /f /im {name} >nul 2>&1")
        time.sleep(1)

    def stop_engine(self, switch_to_scanner=False):
        self.is_running = False
        self.stop_event.set()
        
        self.log("\n[*] Halting Operation and cleaning up System Configuration...")
        self.set_windows_proxy(False)
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{self.active_interface}" source=dhcp'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except: pass
        
        self._kill_process(self.current_process, "tor.exe")
        self._kill_process(None, "psiphon3.exe")
        
        # --- حل ارور پاپ آپ مزاحم WireGuard ---
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            tunnel_service = "AmneziaWGTunnel$nettools_warp"
            
            # اول در پس‌زمینه چک میکنیم که آیا سرویس نصب شده یا نه
            check_sc = subprocess.run(["sc", "query", tunnel_service], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            
            # اگر نصب بود (کد 0 یعنی وجود داره)، اونوقت بدون ارور پاکش میکنیم
            if check_sc.returncode == 0:
                awg_exe = get_core_path(os.path.join("cores", "wireguard", "amneziawg.exe"))
                subprocess.run([awg_exe, "/uninstalltunnelservice", "nettools_warp"], creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
        except: pass

        self.btn_power.configure(text="🔥 INITIATE SURVIVAL MODE", fg_color="#C62828", hover_color="#8E0000")
        
        if switch_to_scanner and self.app_controller:
            self.after(500, self._trigger_auto_scan)

    def _trigger_auto_scan(self):
        # تغییر تب به تب اسکنر
        self.app_controller.select_frame_by_name("scanner")
        
        # چک میکنیم که اسکنر دیتای UUID را داشته باشد تا مستقیم استارت بخورد
        scanner = self.app_controller.scanner_frame
        if scanner.entry_uuid.get() and scanner.entry_host.get():
            scanner.start_scan()
        else:
            messagebox.showinfo("Panic Mode Fallback", "Switched to Scanner Mode.\nPlease enter UUID and Worker Host to begin deep scanning for a VLESS connection.")

    def stop_connection(self):
        self.stop_engine()