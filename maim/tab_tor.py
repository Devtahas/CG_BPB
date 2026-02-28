# tab_tor.py
import customtkinter as ctk
import subprocess
import os
import sys
import threading
import re
import winreg
import ctypes
from config import CF_ORANGE, BG_PANEL, DIRS

def get_core_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# لیست کشورهای محبوب برای خروجی Tor (Exit Nodes)
COUNTRIES = {
    "🌍 Auto (Random)": "",
    "🇺🇸 United States": "{us}",
    "🇩🇪 Germany": "{de}",
    "🇬🇧 United Kingdom": "{gb}",
    "🇫🇷 France": "{fr}",
    "🇳🇱 Netherlands": "{nl}",
    "🇨🇦 Canada": "{ca}",
    "🇨🇭 Switzerland": "{ch}",
    "🇯🇵 Japan": "{jp}",
    "🇸🇬 Singapore": "{sg}",
    "🇦🇺 Australia": "{au}"
}

class TorFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        self.tor_process = None
        self.is_running = False

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🧅 Tor Network", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        # Control Panel (Country & Button)
        self.control_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.control_frame.grid(row=1, column=0, padx=40, pady=20, sticky="ew")
        self.control_frame.grid_columnconfigure(1, weight=1)

        # Country Selector
        country_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        country_frame.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        ctk.CTkLabel(country_frame, text="Target Country (Exit Node):", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        self.combo_country = ctk.CTkComboBox(country_frame, values=list(COUNTRIES.keys()), width=200, state="readonly", dropdown_fg_color="#18181B")
        self.combo_country.set("🌍 Auto (Random)")
        self.combo_country.pack(side="left")

        # Connect Button
        self.btn_connect = ctk.CTkButton(self.control_frame, text="▶ CONNECT TOR", width=160, fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14), command=self.toggle_tor)
        self.btn_connect.grid(row=0, column=2, padx=20, pady=20, sticky="e")

        # Progress Box
        self.prog_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.prog_frame.grid(row=2, column=0, padx=40, pady=0, sticky="ew")
        self.prog_frame.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(self.prog_frame, text="Status: Disconnected", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.progressbar = ctk.CTkProgressBar(self.prog_frame, progress_color=CF_ORANGE)
        self.progressbar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progressbar.set(0)

        self.lbl_detail = ctk.CTkLabel(self.prog_frame, text="Ready to connect...", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_detail.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")

        # Info Description
        desc_text = "Tor connects you anonymously to the internet.\n\nAll your traffic will be encrypted, bounced through 3 relays, and globally routed (System Proxy).\nIf a specific country is selected, the final exit node will be from that country."
        ctk.CTkLabel(self, text=desc_text, justify="left", text_color="gray", font=ctk.CTkFont(size=13)).grid(row=3, column=0, padx=40, pady=20, sticky="w")

    def set_windows_proxy(self, enable=True, server="127.0.0.1:9052"):
        """تنظیم پراکسی ویندوز برای هدایت کل ترافیک به سمت تور"""
        try:
            internet_settings = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings', 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, server)
            else:
                winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(internet_settings)
            
            # رفرش کردن تنظیمات ویندوز تا تغییرات بلافاصله اعمال شود
            internet_set_option = ctypes.windll.wininet.InternetSetOptionW
            internet_set_option(0, 37, 0, 0)
            internet_set_option(0, 39, 0, 0)
        except Exception:
            pass

    def toggle_tor(self):
        if not self.is_running:
            self.start_tor()
        else:
            self.stop_tor()

    def start_tor(self):
        tor_exe = get_core_path(os.path.join("cores", "tor", "tor.exe"))
        
        if not os.path.exists(tor_exe):
            ctk.messagebox.showerror("Error", "tor.exe not found!\nPlease ensure it is placed in 'cores/tor/tor.exe'")
            return

        tor_data_dir = os.path.join(DIRS["settings"], "TorData")
        os.makedirs(tor_data_dir, exist_ok=True)

        self.is_running = True
        self.combo_country.configure(state="disabled")
        self.btn_connect.configure(text="⏹ CANCEL", fg_color="#C62828", hover_color="#8E0000")
        self.lbl_status.configure(text="Status: Bootstrapping...", text_color=CF_ORANGE)
        self.progressbar.set(0.0)
        self.lbl_detail.configure(text="Starting Tor process...")

        selected_country = self.combo_country.get()
        country_code = COUNTRIES.get(selected_country, "")

        # اضافه شدن HTTPTunnelPort برای روت کردن کل ترافیک سیستم
        cmd =[
            tor_exe,
            "DataDirectory", tor_data_dir,
            "SocksPort", "9050",
            "HTTPTunnelPort", "9052",
            "Log", "notice stdout"
        ]

        if country_code:
            cmd.extend(["ExitNodes", country_code, "StrictNodes", "1"])

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self.tor_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            threading.Thread(target=self._monitor_tor_output, daemon=True).start()
            
        except Exception as e:
            self.is_running = False
            self.lbl_status.configure(text="Status: Error launching Tor", text_color="#EF5350")
            self.combo_country.configure(state="readonly")
            self.btn_connect.configure(text="▶ CONNECT TOR", fg_color="#2E7D32", hover_color="#1B5E20")

    def _monitor_tor_output(self):
        if not self.tor_process:
            return

        while self.tor_process and self.tor_process.poll() is None:
            line = self.tor_process.stdout.readline()
            if not line:
                break
                
            try:
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                if "Bootstrapped" in decoded_line:
                    match = re.search(r'Bootstrapped (\d+)%', decoded_line)
                    if match:
                        percent = int(match.group(1))
                        try: detail = decoded_line.split("): ")[1]
                        except: detail = decoded_line
                            
                        self.after(0, self._update_progress_ui, percent, detail)
                        if percent == 100: break
            except Exception: pass

    def _update_progress_ui(self, percent, detail):
        if not self.is_running:
            return
            
        self.progressbar.set(percent / 100.0)
        self.lbl_detail.configure(text=f"{percent}% - {detail}")

        if percent == 100:
            # اعمال پروکسی سیستم وقتی اتصال کامل شد
            self.set_windows_proxy(True, "127.0.0.1:9052")
            
            self.lbl_status.configure(text="Status: Connected (System Proxy Active)", text_color="#66BB6A")
            self.btn_connect.configure(text="⏹ DISCONNECT", fg_color="#C62828", hover_color="#8E0000")
            self.lbl_detail.configure(text="Tor circuit established successfully. All System traffic is routed.")

    def stop_tor(self):
        if self.tor_process:
            try:
                self.tor_process.terminate()
                os.system("taskkill /f /im tor.exe >nul 2>&1")
            except: pass
            self.tor_process = None
            
        # خاموش کردن پروکسی سیستم
        self.set_windows_proxy(False)
            
        self.is_running = False
        self.progressbar.set(0)
        self.combo_country.configure(state="readonly")
        self.lbl_status.configure(text="Status: Disconnected", text_color="#EF5350")
        self.lbl_detail.configure(text="Ready to connect...")
        self.btn_connect.configure(text="▶ CONNECT TOR", fg_color="#2E7D32", hover_color="#1B5E20")
        
    def stop_connection(self):
        self.stop_tor()