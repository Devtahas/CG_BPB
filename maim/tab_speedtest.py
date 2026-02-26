# tab_speedtest.py
import customtkinter as ctk
import threading
import time
import requests
import os
import urllib3
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SpeedtestFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="🌍 Global Internet Speedtest", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, pady=(40, 10))
        ctk.CTkLabel(self, text="Measures your actual Ping, Download & Upload (Live Data via Cloudflare)", text_color="gray").grid(row=1, column=0, pady=(0, 20))

        # Dashboard Results Frame
        res_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=20)
        res_frame.grid(row=2, column=0, padx=50, pady=20, sticky="nsew")
        res_frame.grid_columnconfigure((0,1,2), weight=1)
        res_frame.grid_rowconfigure(0, weight=1)

        # Ping Box
        ping_box = ctk.CTkFrame(res_frame, fg_color="transparent")
        ping_box.grid(row=0, column=0, pady=40)
        ctk.CTkLabel(ping_box, text="PING", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").pack()
        self.lbl_ping = ctk.CTkLabel(ping_box, text="--", font=ctk.CTkFont(size=40, weight="bold"), text_color="#00E676")
        self.lbl_ping.pack()
        ctk.CTkLabel(ping_box, text="ms", font=ctk.CTkFont(size=14)).pack()

        # Download Box
        dl_box = ctk.CTkFrame(res_frame, fg_color="transparent")
        dl_box.grid(row=0, column=1, pady=40)
        ctk.CTkLabel(dl_box, text="DOWNLOAD", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").pack()
        self.lbl_dl = ctk.CTkLabel(dl_box, text="--", font=ctk.CTkFont(size=40, weight="bold"), text_color="#29B6F6")
        self.lbl_dl.pack()
        ctk.CTkLabel(dl_box, text="Mbps", font=ctk.CTkFont(size=14)).pack()

        # Upload Box
        ul_box = ctk.CTkFrame(res_frame, fg_color="transparent")
        ul_box.grid(row=0, column=2, pady=40)
        ctk.CTkLabel(ul_box, text="UPLOAD", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").pack()
        self.lbl_ul = ctk.CTkLabel(ul_box, text="--", font=ctk.CTkFont(size=40, weight="bold"), text_color="#AB47BC")
        self.lbl_ul.pack()
        ctk.CTkLabel(ul_box, text="Mbps", font=ctk.CTkFont(size=14)).pack()

        # Action Button
        self.btn_test = ctk.CTkButton(self, text="GO", width=120, height=120, corner_radius=60, 
                                      fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, 
                                      font=ctk.CTkFont(size=26, weight="bold"), command=self.run_test)
        self.btn_test.grid(row=3, column=0, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.lbl_status.grid(row=4, column=0, pady=(0,20))

    def run_test(self):
        # غیرفعال کردن دکمه و ریست کردن مقادیر قبلی
        self.btn_test.configure(state="disabled", fg_color="gray")
        self.lbl_ping.configure(text="--", text_color="#00E676")
        self.lbl_dl.configure(text="--", text_color="#29B6F6")
        self.lbl_ul.configure(text="--", text_color="#AB47BC")
        
        # اجرای فرایند در ترد جداگانه
        threading.Thread(target=self._logic, daemon=True).start()

    def _logic(self):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
        
        # 1. PING TEST
        self.after(0, lambda: self.lbl_status.configure(text="Testing Ping..."))
        try:
            total_ping = 0
            # گرفتن میانگین پینگ از 3 ریکوئست برای دقت بالاتر
            for _ in range(3):
                start = time.time()
                requests.get("https://cp.cloudflare.com/generate_204", headers=headers, timeout=5)
                total_ping += (time.time() - start) * 1000
            
            ping_val = int(total_ping / 3)
            self.after(0, lambda: self.lbl_ping.configure(text=str(ping_val)))
        except Exception:
            self.after(0, lambda: self.lbl_ping.configure(text="Err", text_color="red"))
            self.after(0, lambda: self.lbl_status.configure(text="Network Error!"))
            self.after(0, lambda: self.btn_test.configure(state="normal", fg_color=CF_ORANGE))
            return

        # 2. DOWNLOAD TEST (Live Update)
        self.after(0, lambda: self.lbl_status.configure(text="Testing Download Speed..."))
        try:
            st = time.time()
            # دانلود یک فایل 25 مگابایتی از نزدیک‌ترین سرور کلودفلر
            r = requests.get("https://speed.cloudflare.com/__down?bytes=25000000", headers=headers, stream=True, timeout=10)
            downloaded = 0
            last_update = st
            
            for chunk in r.iter_content(chunk_size=131072): # دانلود چانک‌های 128 کیلوبایتی
                if not chunk: break
                downloaded += len(chunk)
                now = time.time()
                
                # آپدیت کردن UI هر 0.2 ثانیه یکبار برای افکت زنده
                if now - last_update > 0.2:
                    elapsed = now - st
                    mbps = (downloaded * 8 / 1_000_000) / elapsed
                    self.after(0, lambda m=mbps: self.lbl_dl.configure(text=f"{m:.2f}"))
                    last_update = now
                    
            total_time = time.time() - st
            final_dl_mbps = round((downloaded * 8 / 1_000_000) / total_time, 2)
            self.after(0, lambda: self.lbl_dl.configure(text=str(final_dl_mbps)))
        except Exception:
            self.after(0, lambda: self.lbl_dl.configure(text="Err", text_color="red"))

        # 3. UPLOAD TEST (Live Update)
        self.after(0, lambda: self.lbl_status.configure(text="Testing Upload Speed..."))
        try:
            uploaded = 0
            st = time.time()
            
            # ارسال 5 فایل 2 مگابایتی به صورت متوالی (مجموعاً 10 مگابایت) برای تست آپلود
            for i in range(5):
                data = os.urandom(2_000_000)
                requests.post("https://speed.cloudflare.com/__up", data=data, headers=headers, timeout=10)
                uploaded += 2_000_000
                now = time.time()
                
                elapsed = now - st
                mbps = (uploaded * 8 / 1_000_000) / elapsed
                self.after(0, lambda m=mbps: self.lbl_ul.configure(text=f"{m:.2f}"))
                
            total_time = time.time() - st
            final_ul_mbps = round((uploaded * 8 / 1_000_000) / total_time, 2)
            self.after(0, lambda: self.lbl_ul.configure(text=str(final_ul_mbps)))
        except Exception:
            self.after(0, lambda: self.lbl_ul.configure(text="Err", text_color="red"))

        # FINISH
        self.after(0, lambda: self.lbl_status.configure(text="Test Completed Successfully!"))
        self.after(0, lambda: self.btn_test.configure(state="normal", fg_color=CF_ORANGE))