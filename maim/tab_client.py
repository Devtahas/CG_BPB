# tab_client.py
import customtkinter as ctk
from tkinter import messagebox
import os
import subprocess
import winreg
import ctypes
import json
import urllib.parse
import time
import socket
import threading
import concurrent.futures
import base64
import requests
import zipfile
import io

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from PIL import ImageGrab
    from pyzbar.pyzbar import decode
    HAS_QR_SCANNER = True
except ImportError:
    HAS_QR_SCANNER = False

from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK, DIRS

class ClientFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # تغییر ایندکس ردیف به خاطر اضافه شدن فریم جدید

        self.configs_dir = DIRS["configs"]
        os.makedirs(self.configs_dir, exist_ok=True)
        
        self.xray_process = None
        self.is_connected = False

        # ---------------- HEADER FRAME ----------------
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 5), sticky="ew")
        
        ctk.CTkLabel(header_frame, text="🛡️ VPN Client", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)
        
        self.btn_refresh = ctk.CTkButton(header_frame, text="🔄", width=30, fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.load_configs)
        self.btn_refresh.pack(side="right", padx=(5, 40))

        self.btn_ping_all = ctk.CTkButton(header_frame, text="⚡ Pings", width=60, fg_color="#F9A825", hover_color="#F57F17", text_color="black", font=ctk.CTkFont(weight="bold"), command=self.test_all_pings)
        self.btn_ping_all.pack(side="right", padx=5)

        self.btn_sub = ctk.CTkButton(header_frame, text="🔗 Sub Link", width=80, fg_color="#8E24AA", hover_color="#6A1B9A", font=ctk.CTkFont(weight="bold"), command=self.import_sub_link)
        self.btn_sub.pack(side="right", padx=5)

        self.btn_qr = ctk.CTkButton(header_frame, text="🔳 QR", width=60, fg_color="#1565C0", hover_color="#0D47A1", font=ctk.CTkFont(weight="bold"), command=self.import_from_qr)
        self.btn_qr.pack(side="right", padx=5)

        self.btn_paste = ctk.CTkButton(header_frame, text="📋 Paste", width=70, fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), command=self.import_from_clipboard)
        self.btn_paste.pack(side="right", padx=5)

        # ---------------- CONNECTION STATUS FRAME ----------------
        # ---------------- CONNECTION STATUS FRAME ----------------
        self.status_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.status_frame.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1) # ایجاد فضای خالی در وسط برای هل دادن دکمه‌ها به راست

        # ردیف اول: وضعیت (سمت چپ)
        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Status: Disconnected", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # ردیف دوم: مانیتورینگ ترافیک (سمت چپ - زیر وضعیت)
        self.lbl_traffic = ctk.CTkLabel(self.status_frame, text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s", font=ctk.CTkFont(size=14, weight="bold"), text_color="#29B6F6")
        self.lbl_traffic.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")

        # سوییچ TUN Mode (سمت راست - وسط‌چین بین دو ردیف)
        self.var_tun = ctk.BooleanVar(value=False)
        self.switch_tun = ctk.CTkSwitch(self.status_frame, text="TUN Mode", variable=self.var_tun, progress_color=CF_ORANGE, font=ctk.CTkFont(weight="bold"), command=self.on_tun_toggle)
        self.switch_tun.grid(row=0, column=2, rowspan=2, padx=15, sticky="e")

        # دکمه اتصال (سمت راست - وسط‌چین بین دو ردیف)
        self.btn_connect = ctk.CTkButton(self.status_frame, text="▶ CONNECT", fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14), command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=3, rowspan=2, padx=20, pady=15, sticky="e")
        

        # ---------------- IP & COUNTRY CHECKER FRAME ----------------
        self.ip_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ip_frame.grid(row=2, column=0, padx=40, pady=0, sticky="ew")
        
        self.btn_check_ip = ctk.CTkButton(self.ip_frame, text="🌍 Check My IP", width=120, fg_color="transparent", border_width=1, border_color="#29B6F6", text_color="#29B6F6", command=self.check_my_ip)
        self.btn_check_ip.pack(side="left", padx=0)
        
        self.lbl_ip_info = ctk.CTkLabel(self.ip_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_ip_info.pack(side="left", padx=15)

        # ---------------- CONFIGS LIST (Scrollable) ----------------
        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=3, column=0, padx=30, pady=10, sticky="nsew")
        self.scroll_area.grid_columnconfigure(0, weight=1)

        self.selected_config_path = None
        self.config_buttons = []

        self.load_configs()

    # ==========================================
    # بخش IP Checker و پرچم کشور
    # ==========================================
    def on_tun_toggle(self):
        if self.var_tun.get():
            messagebox.showinfo("TUN Mode", "TUN Mode routes ALL Windows traffic through the VPN.\n\n⚠️ Note: You must Run the App as Administrator for this to work!")

    def _get_flag_emoji(self, country_code):
        if not country_code or len(country_code) != 2: return "🌍"
        return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)

    def check_my_ip(self):
        self.btn_check_ip.configure(state="disabled", text="⏳ Checking...")
        self.lbl_ip_info.configure(text="")
        threading.Thread(target=self._check_ip_thread, daemon=True).start()

    def _check_ip_thread(self):
        try:
            # استفاده از پروکسی ویندوز در صورت روشن بودن VPN (کتابخانه requests اتوماتیک آن را می‌خواند)
            resp = requests.get("http://ip-api.com/json/", timeout=5).json()
            ip = resp.get("query", "Unknown")
            isp = resp.get("isp", "Unknown")
            cc = resp.get("countryCode", "UN")
            flag = self._get_flag_emoji(cc)
            
            info_text = f"{flag} {ip}  |  ISP: {isp}"
            color = "#66BB6A" if self.is_connected else "gray"
            self.after(0, lambda: self.lbl_ip_info.configure(text=info_text, text_color=color))
        except Exception:
            self.after(0, lambda: self.lbl_ip_info.configure(text="❌ Failed to fetch IP", text_color="#EF5350"))
        finally:
            self.after(0, lambda: self.btn_check_ip.configure(state="normal", text="🌍 Check My IP"))

    # ==========================================
    # دانلودر خودکار Xray-Core
    # ==========================================
    def check_and_download_xray(self, base_dir):
        xray_dir = os.path.join(base_dir, "xray")
        xray_exe = os.path.join(xray_dir, "xray.exe")
        
        if os.path.exists(xray_exe):
            return True # فایل وجود دارد، ادامه اتصال
            
        ans = messagebox.askyesno("Missing Xray Core", "Xray-Core is required but not found.\nDo you want to download it automatically now? (approx 20MB)")
        if not ans:
            return False

        self.btn_connect.configure(state="disabled", text="⏳ DOWNLOADING XRAY...")
        threading.Thread(target=self._download_xray_thread, args=(xray_dir,), daemon=True).start()
        return "DOWNLOADING" # متوقف کردن اتصال تا پایان دانلود

    def _download_xray_thread(self, xray_dir):
        try:
            os.makedirs(xray_dir, exist_ok=True)
            self.after(0, lambda: self.lbl_status.configure(text="Fetching latest Xray release...", text_color=CF_ORANGE))
            
            # پیدا کردن آخرین نسخه از گیت هاب
            api_url = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
            rel_info = requests.get(api_url, timeout=10).json()
            
            download_url = None
            for asset in rel_info.get("assets", []):
                if "windows-64.zip" in asset["name"]:
                    download_url = asset["browser_download_url"]
                    break
                    
            if not download_url:
                raise Exception("Windows 64-bit build not found in latest release.")

            self.after(0, lambda: self.lbl_status.configure(text="Downloading Xray core... Please wait", text_color=CF_ORANGE))
            
            # دانلود و اکسترکت مستقیم در حافظه (بدون ساخت فایل زیپ اضافی)
            r = requests.get(download_url, stream=True, timeout=20)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(xray_dir)
            
            self.after(0, lambda: messagebox.showinfo("Success", "Xray Core downloaded successfully! You can now Connect."))
            self.after(0, lambda: self.lbl_status.configure(text="Status: Ready to Connect", text_color="gray"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Download Failed", f"Failed to download Xray automatically:\n{str(e)}\n\nPlease download it manually and put it in the 'xray' folder."))
            self.after(0, lambda: self.lbl_status.configure(text="Status: Disconnected", text_color="#EF5350"))
        finally:
            self.after(0, lambda: self.btn_connect.configure(state="normal", text="▶ CONNECT"))

    # ==========================================
    # مدیریت اتصال (اجرای Xray و ادغام TUN)
    # ==========================================
    def toggle_connection(self):
        if not self.is_connected: self.start_connection()
        else: self.stop_connection()

    def start_connection(self):
        if not self.selected_config_path:
            messagebox.showerror("Error", "Please select a configuration from the list first!")
            return

        import sys
        if getattr(sys, 'frozen', False): base_dir = os.path.dirname(sys.executable)
        else: base_dir = os.path.dirname(os.path.abspath(__file__))
            
        # چک کردن وضعیت دانلود خودکار
        status = self.check_and_download_xray(base_dir)
        if status == "DOWNLOADING": return
        if not status: return

        xray_path = os.path.join(base_dir, "xray", "xray.exe")
        
        # ویرایش و آماده‌سازی کانفیگ
        try:
            with open(self.selected_config_path, 'r', encoding='utf-8') as f: config_data = json.load(f)
            
            # اطمینان از وجود تگ proxy برای روتینگ
            if 'tag' not in config_data['outbounds'][0]:
                config_data['outbounds'][0]['tag'] = "proxy"
            
            # حذف Inbound های قدیمی (Socks/HTTP/TUN) برای جایگذاری جدید
            config_data['inbounds'] = [ib for ib in config_data.get('inbounds', []) if ib.get('protocol') not in ["socks", "http", "tun"]]
            
            # ساخت Inbound های پایه (Socks و HTTP)
            config_data['inbounds'].extend([
                {"listen": "127.0.0.1", "port": 10808, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}, "sniffing": {"destOverride":["http", "tls"], "enabled": True}},
                {"listen": "127.0.0.1", "port": 10809, "protocol": "http", "settings": {"allowTransparent": False}, "sniffing": {"destOverride": ["http", "tls"], "enabled": True}}
            ])

            # اگر حالت TUN روشن باشد، Inbound مخصوص کارت شبکه مجازی را اضافه می‌کنیم
            is_tun_enabled = self.var_tun.get()
            if is_tun_enabled:
                config_data['inbounds'].append({
                    "tag": "tun-in",
                    "port": 10899,
                    "protocol": "tun",
                    "settings": {
                        "autoRoute": True,
                        "strictRoute": True,
                        "stack": "system"
                    }
                })

            with open(self.selected_config_path, 'w', encoding='utf-8') as f: 
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to patch config:\n{str(e)}")
            return

        # اجرای هسته
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.xray_process = subprocess.Popen([xray_path, "-c", self.selected_config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)

            time.sleep(0.8) 
            if self.xray_process.poll() is not None:
                err = self.xray_process.stderr.read().decode('utf-8', errors='ignore')
                if "requires elevation" in err.lower() or "administrator" in err.lower():
                    messagebox.showerror("Admin Rights Required", "TUN Mode requires Administrator privileges!\n\nPlease close the app, right-click and select 'Run as Administrator'.")
                else:
                    messagebox.showerror("Crash Report", f"Xray Engine Failed to Start!\nEnsure Port 10808/10809 is free.\n\nDetails:\n{err}")
                self.xray_process = None
                return

            # تنظیم پروکسی ویندوز فقط در حالتی که TUN خاموش باشد
            if not is_tun_enabled:
                self.set_windows_proxy(enable=True, server="127.0.0.1:10809")
                status_msg = "Connected (System Proxy Routed)"
            else:
                self.set_windows_proxy(enable=False) # اطمینان از خاموش بودن پروکسی
                status_msg = "Connected (TUN Global Mode)"

            self.is_connected = True
            self.lbl_status.configure(text=f"Status: {status_msg}", text_color="#66BB6A")
            self.btn_connect.configure(text="⏹ DISCONNECT", fg_color="#C62828", hover_color="#8E0000")
            
            threading.Thread(target=self._traffic_monitor, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to start Xray:\n{str(e)}")

    def stop_connection(self):
        if self.xray_process:
            self.xray_process.terminate()
            self.xray_process.wait()
            self.xray_process = None

        self.set_windows_proxy(enable=False)
        self.is_connected = False
        self.lbl_status.configure(text="Status: Disconnected", text_color="#EF5350")
        self.btn_connect.configure(text="▶ CONNECT", fg_color="#2E7D32", hover_color="#1B5E20")
        self.lbl_traffic.configure(text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s")

    # ==========================================
    # مانیتورینگ ترافیک (بدون تغییر)
    # ==========================================
    def _traffic_monitor(self):
        if not HAS_PSUTIL: return
        last_io = psutil.net_io_counters()
        while self.is_connected:
            time.sleep(1)
            current_io = psutil.net_io_counters()
            dl_speed = (current_io.bytes_recv - last_io.bytes_recv) / 1024
            ul_speed = (current_io.bytes_sent - last_io.bytes_sent) / 1024
            last_io = current_io
            dl_str = f"{dl_speed:.1f} KB/s" if dl_speed < 1024 else f"{dl_speed/1024:.2f} MB/s"
            ul_str = f"{ul_speed:.1f} KB/s" if ul_speed < 1024 else f"{ul_speed/1024:.2f} MB/s"
            self.after(0, lambda d=dl_str, u=ul_str: self.lbl_traffic.configure(text=f"⬇️ {d}   |   ⬆️ {u}"))

    # ==========================================
    # تنظیمات پروکسی ویندوز (بدون تغییر)
    # ==========================================
    def set_windows_proxy(self, enable=True, server="127.0.0.1:10809"):
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
        except Exception as e:
            print(f"Proxy Error: {e}")

    def on_closing(self):
        self.stop_connection()

    # ==========================================
    # توابع Sub Link، QR و ساخت لیست دکمه‌ها (بدون تغییر)
    # ==========================================
    def import_sub_link(self):
        dialog = ctk.CTkInputDialog(text="Paste your Subscription URL here:", title="Import Subscription")
        url = dialog.get_input()
        if not url: return
        self.btn_sub.configure(state="disabled", text="⏳ Fetching...")
        threading.Thread(target=self._fetch_sub_thread, args=(url,), daemon=True).start()

    def _fetch_sub_thread(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            content = resp.text.strip()
            content += "=" * ((4 - len(content) % 4) % 4)
            try: decoded_data = base64.b64decode(content).decode('utf-8')
            except Exception: decoded_data = content 

            lines =[line.strip() for line in decoded_data.splitlines() if line.strip()]
            imported_count = 0
            for line in lines:
                if line.startswith("vless://"):
                    try:
                        config_dict = self.convert_vless_to_json(line)
                        filename = f"Sub_{int(time.time()*1000)}_{imported_count}.json"
                        filepath = os.path.join(self.configs_dir, filename)
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(config_dict, f, indent=2, ensure_ascii=False)
                        imported_count += 1
                    except Exception: continue
            
            self.after(0, lambda: messagebox.showinfo("Success", f"🎉 Successfully imported {imported_count} VLESS configs!"))
            self.after(0, self.load_configs)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Sub Error", f"Failed to fetch subscription:\n{str(e)}"))
        finally:
            self.after(0, lambda: self.btn_sub.configure(state="normal", text="🔗 Sub Link"))

    def test_all_pings(self):
        if not self.config_buttons: return
        self.btn_ping_all.configure(state="disabled", text="⏳ Testing...")
        threading.Thread(target=self._run_ping_tests, daemon=True).start()

    def _run_ping_tests(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(self.ping_single_config, item["path"], item["lbl_ping"]) for item in self.config_buttons]
            concurrent.futures.wait(futures)
        self.after(0, lambda: self.btn_ping_all.configure(state="normal", text="⚡ Pings"))

    def ping_single_config(self, path, lbl_widget):
        self.after(0, lambda: lbl_widget.configure(text="...", text_color="gray"))
        try:
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            outbound = data.get("outbounds", [])[0]
            if outbound.get("protocol") != "vless":
                self.after(0, lambda: lbl_widget.configure(text="Skip", text_color="gray"))
                return
            vnext = outbound.get("settings", {}).get("vnext", [])[0]
            address = vnext.get("address", "")
            port = int(vnext.get("port", 443))
            
            start_time = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.5)
                s.connect((address, port))
            ping_ms = int((time.time() - start_time) * 1000)
            
            color = "#66BB6A" if ping_ms < 200 else "#FFA726" if ping_ms < 500 else "#EF5350"
            self.after(0, lambda: lbl_widget.configure(text=f"{ping_ms} ms", text_color=color))
        except socket.timeout:
            self.after(0, lambda: lbl_widget.configure(text="Timeout", text_color="#EF5350"))
        except Exception:
            self.after(0, lambda: lbl_widget.configure(text="Error", text_color="#EF5350"))

    def import_from_clipboard(self):
        try:
            clipboard_text = self.clipboard_get().strip()
            if not clipboard_text: return
            self.process_imported_link(clipboard_text)
        except Exception: pass

    def import_from_qr(self):
        if not HAS_QR_SCANNER:
            messagebox.showerror("Error", "Please install required libraries:\npip install pillow pyzbar")
            return
        try:
            self.lbl_status.configure(text="Scanning screen...", text_color=CF_ORANGE)
            self.update()
            screen = ImageGrab.grab()
            decoded_objects = decode(screen)
            if decoded_objects:
                self.process_imported_link(decoded_objects[0].data.decode('utf-8').strip())
            else:
                messagebox.showwarning("Not Found", "No QR Code found on the screen!")
        except Exception as e:
            messagebox.showerror("Scan Error", f"Failed to scan screen:\n{str(e)}")
        finally:
            self.lbl_status.configure(text="Status: Disconnected" if not self.is_connected else "Status: Connected", text_color="#EF5350" if not self.is_connected else "#66BB6A")

    def process_imported_link(self, data):
        data = data.strip()
        if data.startswith("{") and data.endswith("}"):
            try:
                parsed_json = json.loads(data)
                self.save_json_config(parsed_json)
                return
            except: pass

        if data.startswith("vless://"):
            try:
                parsed_json = self.convert_vless_to_json(data)
                self.save_json_config(parsed_json)
            except Exception as e: messagebox.showerror("Parse Error", str(e))
        else:
            messagebox.showerror("Unsupported", "Only VLESS links are supported currently.")

    def convert_vless_to_json(self, link):
        rest = link[8:]
        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else: remarks = "Imported VLESS Config"
            
        if "?" in rest:
            rest, query_str = rest.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))
        else: params = {}
            
        uuid_str, server_port = rest.split("@", 1)
        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 443

        config = {
            "remarks": f"📥 {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds":[],
            "outbounds":[
                {
                    "tag": "proxy", "protocol": "vless",
                    "settings": {"vnext":[{"address": server, "port": port, "users":[{"id": uuid_str, "encryption": "none", "flow": params.get("flow", "")}]}]},
                    "streamSettings": {"network": params.get("type", "tcp"), "security": params.get("security", "none")}
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules":[{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        net_type = params.get("type", "tcp")
        if net_type == "ws": config["outbounds"][0]["streamSettings"]["wsSettings"] = {"path": params.get("path", "/"), "headers": {"Host": params.get("host", server)}}
        elif net_type == "grpc": config["outbounds"][0]["streamSettings"]["grpcSettings"] = {"serviceName": params.get("serviceName", ""), "multiMode": params.get("mode", "multi") == "multi"}

        sec_type = params.get("security", "none")
        if sec_type == "tls":
            alpn = params.get("alpn", "").split(",") if params.get("alpn") else []
            config["outbounds"][0]["streamSettings"]["tlsSettings"] = {"serverName": params.get("sni", server), "fingerprint": params.get("fp", "chrome"), "alpn":[a for a in alpn if a]}
        elif sec_type == "reality":
            config["outbounds"][0]["streamSettings"]["realitySettings"] = {"publicKey": params.get("pbk", ""), "shortId": params.get("sid", ""), "serverName": params.get("sni", server), "fingerprint": params.get("fp", "chrome"), "spiderX": params.get("spx", "/")}

        return config

    def save_json_config(self, config_dict):
        filename = f"Imported_{int(time.time()*100)}_{urllib.parse.quote(config_dict['remarks'][:5])}.json"
        filepath = os.path.join(self.configs_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        self.load_configs()
        if "Sub" not in filename:
            messagebox.showinfo("Success", "Config Imported Successfully!")

    def load_configs(self):
        for widget in self.scroll_area.winfo_children(): widget.destroy()
        self.config_buttons.clear()

        if not os.path.exists(self.configs_dir): return
        files =[f for f in os.listdir(self.configs_dir) if f.endswith('.json')]
        if not files: return

        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.configs_dir, x)))

        for file in files:
            path = os.path.join(self.configs_dir, file)
            remark_name = file
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    remark_name = data.get('remarks', file)
            except: pass

            row_frame = ctk.CTkFrame(self.scroll_area, fg_color=BG_PANEL, corner_radius=8)
            row_frame.pack(fill="x", padx=10, pady=5)
            row_frame.grid_columnconfigure(0, weight=1)

            btn = ctk.CTkButton(row_frame, text=remark_name, fg_color="transparent", text_color="white", hover_color="#332015", anchor="w", command=lambda p=path, rf=row_frame: self.select_config(p, rf))
            btn.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
            
            lbl_ping = ctk.CTkLabel(row_frame, text="-- ms", width=60, text_color="gray", font=ctk.CTkFont(weight="bold"))
            lbl_ping.grid(row=0, column=1, padx=10, pady=5)

            btn_del = ctk.CTkButton(row_frame, text="🗑️", width=30, fg_color="transparent", text_color="#EF5350", hover_color="#3A1D1D", command=lambda p=path: self.delete_config(p))
            btn_del.grid(row=0, column=2, padx=5, pady=5)

            self.config_buttons.append({"frame": row_frame, "path": path, "lbl_ping": lbl_ping})

    def delete_config(self, path):
        if self.is_connected and self.selected_config_path == path:
            messagebox.showwarning("Warning", "Cannot delete active config.\nDisconnect first!")
            return
        if messagebox.askyesno("Delete", "Delete this config?"):
            os.remove(path)
            self.load_configs()

    def select_config(self, path, frame_widget):
        if self.is_connected:
            messagebox.showwarning("Warning", "Disconnect first before changing the server.")
            return
        self.selected_config_path = path
        for item in self.config_buttons:
            item["frame"].configure(border_width=2, border_color=CF_ORANGE) if item["path"] == path else item["frame"].configure(border_width=0)
