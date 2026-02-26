# tab_telegram.py
import customtkinter as ctk
import threading
import requests
import socket
import time
import random
import concurrent.futures
import urllib3

# غیرفعال کردن اخطارهای SSL برای جلوگیری از خطاهای فیلترینگ
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

# آدرس وب‌سرویس شما در Render
RENDER_API_URL = "https://test-oz77.onrender.com/api/proxies"

class TelegramFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header_frame, text="✈️ MTProto Proxies", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=(40, 20), sticky="w")
        
        self.entry_channel = ctk.CTkEntry(header_frame, placeholder_text="Channel Username", width=200)
        self.entry_channel.insert(0, "ProxyMTProto") 
        self.entry_channel.grid(row=0, column=1, sticky="e", padx=10)

        self.btn_fetch = ctk.CTkButton(header_frame, text="🔄 Fetch & Ping", fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.fetch_proxies)
        self.btn_fetch.grid(row=0, column=2, padx=(0, 40), sticky="e")

        self.lbl_status = ctk.CTkLabel(self, text="Smart Fetch Engine: Attempts Render API, fallbacks to Anti-Filter Github Mirrors.", text_color="gray")
        self.lbl_status.grid(row=1, column=0, pady=(0, 10))

        # Scrollable Cards Area
        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.scroll_area.grid_columnconfigure(0, weight=1)

    def fetch_proxies(self):
        channel_id = self.entry_channel.get().strip()
        if not channel_id:
            self.lbl_status.configure(text="❌ Please enter a channel username.", text_color="#EF5350")
            return

        self.btn_fetch.configure(state="disabled", text="⏳ Scraping...")
        self.lbl_status.configure(text=f"Connecting to Render API (May take 30s)...", text_color=CF_ORANGE)
        
        for widget in self.scroll_area.winfo_children():
            widget.destroy()

        threading.Thread(target=self._process_proxies, args=(channel_id,), daemon=True).start()

    def _process_proxies(self, channel_id):
        proxies_to_test =[]
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            # 1. تلاش برای گرفتن دیتا از سرور رندر (استفاده از verify=False برای دور زدن خطای SSL مخابرات)
            resp = requests.get(f"{RENDER_API_URL}?channel={channel_id}", headers=headers, timeout=40, verify=False)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("success") and data.get("proxies"):
                        proxies_to_test = data["proxies"]
                    else:
                        raise Exception("No valid proxies found in Render response.")
                except ValueError:
                    raise Exception("Render returned Invalid JSON (Likely blocked by ISP).")
            else:
                try: err_msg = resp.json().get("error", f"HTTP {resp.status_code}")
                except: err_msg = f"Backend Error {resp.status_code}"
                raise Exception(err_msg)

        except Exception as e:
            # 2. سیستم Fallback هوشمند: استفاده از لینک‌های بدون فیلتر گیت‌هاب (Mirrors)
            self.after(0, lambda: self.lbl_status.configure(text=f"API Down/Blocked. Trying Anti-Filter Mirrors...", text_color="#FFA726"))
            
            # دامنه‌های اصلی گیت‌هاب فیلتر هستند، این لینک‌ها از پروکسی‌های بین‌المللی رد می‌شوند:
            fallback_urls =[
                "https://ghproxy.net/https://raw.githubusercontent.com/hookzof/socks5_list/master/tg/mtproto.json",
                "https://fastly.jsdelivr.net/gh/hookzof/socks5_list@master/tg/mtproto.json",
                "https://raw.gitmirror.com/hookzof/socks5_list/master/tg/mtproto.json"
            ]
            
            success = False
            for fb_url in fallback_urls:
                try:
                    fb_resp = requests.get(fb_url, headers=headers, timeout=15, verify=False)
                    if fb_resp.status_code == 200:
                        all_proxies = fb_resp.json() # اگر JSON نباشد به Except میپرد و میرور بعدی را تست میکند
                        random.shuffle(all_proxies)
                        proxies_to_test = all_proxies[:50] # 50 پراکسی رندوم رو جدا می‌کنیم که سریع لود بشه
                        success = True
                        break
                except Exception:
                    continue
            
            if not success:
                self.after(0, lambda: self.lbl_status.configure(text=f"❌ All methods failed. Check internet connection or use VPN.", text_color="#EF5350"))
                self.after(0, lambda: self.btn_fetch.configure(state="normal", text="🔄 Fetch & Ping"))
                return

        # 3. شروع عملیات پینگ زدن زنده
        self.after(0, lambda: self.lbl_status.configure(text=f"Testing {len(proxies_to_test)} extracted proxies... please wait.", text_color=CF_ORANGE))
        valid_proxies =[]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures =[executor.submit(self._ping_proxy, p) for p in proxies_to_test]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    valid_proxies.append(res)

        # 4. سورت کردن بر اساس بهترین پینگ و رندر روی صفحه
        valid_proxies.sort(key=lambda x: x['ping'])
        self.after(0, self._render_cards, valid_proxies)

    def _ping_proxy(self, proxy):
        host = proxy.get('host', '')
        try: port = int(proxy.get('port', 443))
        except: return None
        secret = proxy.get('secret', '')

        if not host or not secret:
            return None

        start_time = time.time()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((host, port))
            
            ping_ms = int((time.time() - start_time) * 1000)
            return {"host": host, "port": port, "secret": secret, "ping": ping_ms}
        except:
            return None

    def _render_cards(self, proxies_list):
        if not proxies_list:
            self.lbl_status.configure(text="❌ Evaluated all proxies, but none are responding (Ping Timeout).", text_color="#EF5350")
            self.btn_fetch.configure(state="normal", text="🔄 Fetch & Ping")
            return

        self.lbl_status.configure(text=f"✅ Finished! Found {len(proxies_list)} fast working proxies.", text_color="#66BB6A")

        for p in proxies_list:
            self._create_proxy_card(p)

        self.btn_fetch.configure(state="normal", text="🔄 Fetch & Ping")

    def _create_proxy_card(self, proxy):
        card = ctk.CTkFrame(self.scroll_area, fg_color=BG_PANEL, corner_radius=10)
        card.pack(fill="x", padx=10, pady=5)
        card.grid_columnconfigure(1, weight=1)

        ping_val = proxy['ping']
        if ping_val < 150: ping_color = "#66BB6A"
        elif ping_val < 300: ping_color = "#FFA726"
        else: ping_color = "#EF5350"

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        ctk.CTkLabel(info_frame, text=f"{proxy['host']}", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"Port: {proxy['port']}", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w")

        ctk.CTkLabel(card, text=f"{ping_val} ms", font=ctk.CTkFont(size=14, weight="bold"), text_color=ping_color).grid(row=0, column=1, padx=10, pady=10)

        tg_link = f"tg://proxy?server={proxy['host']}&port={proxy['port']}&secret={proxy['secret']}"

        btn_copy = ctk.CTkButton(card, text="📋 Copy", width=80, fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015")
        btn_copy.grid(row=0, column=2, padx=15, pady=10)
        
        btn_copy.configure(command=lambda l=tg_link, b=btn_copy: self._copy_to_clipboard(l, b))

    def _copy_to_clipboard(self, text, button):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

        button.configure(text="✅ Copied!", fg_color="#2E7D32", text_color="white", border_color="#2E7D32")
        self.after(1500, lambda: button.configure(text="📋 Copy", fg_color="transparent", text_color=CF_ORANGE, border_color=CF_ORANGE))