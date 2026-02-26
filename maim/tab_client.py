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

from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

class ClientFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.configs_dir = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Results", "Configs")
        os.makedirs(self.configs_dir, exist_ok=True)
        
        self.xray_process = None
        self.is_connected = False

        # Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        
        ctk.CTkLabel(header_frame, text="🛡️ VPN Client", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)
        
        # دکمه‌های هدر (اضافه شدن دکمه Sub Link)
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

        # Connection Status Frame
        self.status_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.status_frame.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Status: Disconnected", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        # لیبل مانیتورینگ زنده ترافیک
        self.lbl_traffic = ctk.CTkLabel(self.status_frame, text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s", font=ctk.CTkFont(size=14, weight="bold"), text_color="#29B6F6")
        self.lbl_traffic.grid(row=0, column=1, padx=10)

        self.btn_connect = ctk.CTkButton(self.status_frame, text="▶ CONNECT", fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14), command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=2, padx=20, pady=15, sticky="e")

        # Configs List (Scrollable)
        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.scroll_area.grid_columnconfigure(0, weight=1)

        self.selected_config_path = None
        self.config_buttons =[]

        self.load_configs()

    # ==========================================
    # بخش جدید 1: دانلود سابسکریپشن (Sub Importer)
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
            # حل مشکل پدینگ در Base64
            content += "=" * ((4 - len(content) % 4) % 4)
            try:
                decoded_data = base64.b64decode(content).decode('utf-8')
            except Exception:
                decoded_data = content # در صورتی که لینک رمزنگاری نشده باشد

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
                    except Exception:
                        continue
            
            self.after(0, lambda: messagebox.showinfo("Success", f"🎉 Successfully imported {imported_count} VLESS configs!"))
            self.after(0, self.load_configs)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Sub Error", f"Failed to fetch subscription:\n{str(e)}"))
        finally:
            self.after(0, lambda: self.btn_sub.configure(state="normal", text="🔗 Sub Link"))

    # ==========================================
    # بخش جدید 2: مانیتورینگ زنده ترافیک شبکه (Live Traffic)
    # ==========================================
    def _traffic_monitor(self):
        if not HAS_PSUTIL:
            self.after(0, lambda: self.lbl_traffic.configure(text="Please install 'psutil' package"))
            return

        last_io = psutil.net_io_counters()
        while self.is_connected:
            time.sleep(1)
            current_io = psutil.net_io_counters()
            
            # محاسبه سرعت بر اساس مابه‌التفاوت در یک ثانیه
            dl_speed = (current_io.bytes_recv - last_io.bytes_recv) / 1024  # KB/s
            ul_speed = (current_io.bytes_sent - last_io.bytes_sent) / 1024  # KB/s
            last_io = current_io
            
            # قالب‌بندی نمایش (تبدیل به مگابایت در صورت نیاز)
            dl_str = f"{dl_speed:.1f} KB/s" if dl_speed < 1024 else f"{dl_speed/1024:.2f} MB/s"
            ul_str = f"{ul_speed:.1f} KB/s" if ul_speed < 1024 else f"{ul_speed/1024:.2f} MB/s"
            
            self.after(0, lambda d=dl_str, u=ul_str: self.lbl_traffic.configure(text=f"⬇️ {d}   |   ⬆️ {u}"))
            
        # ریست کردن مانیتور هنگام دیسکانکت
        self.after(0, lambda: self.lbl_traffic.configure(text="⬇️ 0.0 KB/s   |   ⬆️ 0.0 KB/s"))

    # ==========================================
    # اتصال و قطع اتصال (ادغام مانیتورینگ)
    # ==========================================
    def toggle_connection(self):
        if not self.is_connected: self.start_connection()
        else: self.stop_connection()

    def start_connection(self):
        if not self.selected_config_path:
            messagebox.showerror("Error", "Please select a configuration from the list first!")
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        xray_path = os.path.join(base_dir, "xray", "xray.exe")
        
        if not os.path.exists(xray_path):
            messagebox.showerror("Error", "xray.exe not found!\nPlease create an 'xray' folder next to the app and put xray.exe in it.")
            return

        try:
            with open(self.selected_config_path, 'r', encoding='utf-8') as f: config_data = json.load(f)
            modified = False
            if 'tag' not in config_data['outbounds'][0]:
                config_data['outbounds'][0]['tag'] = "proxy"
                modified = True
            has_http = any(ib.get('port') == 10809 for ib in config_data.get('inbounds',[]))
            if not has_http:
                config_data['inbounds'].append({"listen": "127.0.0.1", "port": 10809, "protocol": "http", "settings": {"allowTransparent": False}, "sniffing": {"destOverride": ["http", "tls"], "enabled": True}})
                modified = True
            if modified:
                with open(self.selected_config_path, 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to patch config:\n{str(e)}")
            return

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.xray_process = subprocess.Popen([xray_path, "-c", self.selected_config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)

            time.sleep(0.5) 
            if self.xray_process.poll() is not None:
                err = self.xray_process.stderr.read().decode('utf-8', errors='ignore')
                messagebox.showerror("Crash Report", f"Xray Engine Failed to Start!\nEnsure Port 10808/10809 is free (close other VPNs).\n\nDetails:\n{err}")
                self.xray_process = None
                return

            self.set_windows_proxy(enable=True, server="127.0.0.1:10809")
            self.is_connected = True
            self.lbl_status.configure(text="Status: Connected (Traffic Routed)", text_color="#66BB6A")
            self.btn_connect.configure(text="⏹ DISCONNECT", fg_color="#C62828", hover_color="#8E0000")
            
            # شروع مانیتورینگ ترافیک در ترد پس‌زمینه
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

    # ==========================================
    # تنظیمات پروکسی ویندوز
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
    # بقیه توابع پارسر و لودر (اسکن QR، Paste، Pings)
    # ==========================================
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
            self.lbl_status.configure(text="Status: Disconnected" if not self.is_connected else "Status: Connected (Traffic Routed)", text_color="#EF5350" if not self.is_connected else "#66BB6A")

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
            "inbounds":[
                {"listen": "127.0.0.1", "port": 10808, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}, "sniffing": {"destOverride":["http", "tls"], "enabled": True}},
                {"listen": "127.0.0.1", "port": 10809, "protocol": "http", "settings": {"allowTransparent": False}, "sniffing": {"destOverride": ["http", "tls"], "enabled": True}}
            ],
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
        if "Sub" not in filename: # اگه از طریق سابسکریپشن نیومده بود پیام بده
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