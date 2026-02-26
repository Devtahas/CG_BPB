# main.pyw
import customtkinter as ctk
from tab_scanner import ScannerFrame
from tab_telegram import TelegramFrame
from tab_tools import ToolsFrame
from tab_speedtest import SpeedtestFrame
from tab_storage import StorageFrame
from tab_client import ClientFrame
from tab_dns import DNSChangerFrame  # ایمپورت تب جدید DNS
from config import CF_ORANGE, BG_DARK, BG_PANEL

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NetTools Pro - Cloudflare Edition")
        self.geometry("1000x700")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.create_sidebar()

        # مقداردهی فرم‌های مختلف برنامه
        self.scanner_frame = ScannerFrame(self, app_controller=self, fg_color="transparent")
        self.speed_frame = SpeedtestFrame(self, fg_color="transparent")
        self.telegram_frame = TelegramFrame(self, fg_color="transparent")
        self.tools_frame = ToolsFrame(self, fg_color="transparent")
        self.storage_frame = StorageFrame(self, fg_color="transparent")
        self.client_frame = ClientFrame(self, fg_color="transparent")
        self.dns_frame = DNSChangerFrame(self, fg_color="transparent") # فریم DNS Changer

        # تب پیش‌فرض هنگام باز شدن برنامه
        self.select_frame_by_name("scanner")
        
        # مدیریت بسته شدن پنجره اصلی
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=BG_PANEL)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # تغییر وزن ردیف 8 برای هل دادن دکمه‌ها به بالا (چون یک دکمه اضافه شده است)
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="☁️ NetTools Pro", font=ctk.CTkFont(size=22, weight="bold"), text_color=CF_ORANGE)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        btn_font = ctk.CTkFont(size=14, weight="bold")
        
        self.btn_client = ctk.CTkButton(self.sidebar_frame, text="🛡️ VPN Client", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("client"))
        self.btn_client.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_scanner = ctk.CTkButton(self.sidebar_frame, text="⚡ CF Scanner", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("scanner"))
        self.btn_scanner.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_speed = ctk.CTkButton(self.sidebar_frame, text="🚀 IP Speedtest", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("speed"))
        self.btn_speed.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_telegram = ctk.CTkButton(self.sidebar_frame, text="✈️ Telegram Proxy", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("telegram"))
        self.btn_telegram.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_dns = ctk.CTkButton(self.sidebar_frame, text="🌍 DNS Changer", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("dns"))
        self.btn_dns.grid(row=5, column=0, padx=20, pady=10, sticky="ew") # اضافه شدن دکمه DNS

        self.btn_tools = ctk.CTkButton(self.sidebar_frame, text="🛠️ Generators", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("tools"))
        self.btn_tools.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        self.btn_storage = ctk.CTkButton(self.sidebar_frame, text="💾 Storage (Memory)", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("storage"))
        self.btn_storage.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

    def select_frame_by_name(self, name):
        # تغییر رنگ دکمه‌های منو بر اساس انتخاب کاربر
        self.btn_client.configure(fg_color=CF_ORANGE if name == "client" else "transparent", text_color="black" if name == "client" else "gray90")
        self.btn_scanner.configure(fg_color=CF_ORANGE if name == "scanner" else "transparent", text_color="black" if name == "scanner" else "gray90")
        self.btn_speed.configure(fg_color=CF_ORANGE if name == "speed" else "transparent", text_color="black" if name == "speed" else "gray90")
        self.btn_telegram.configure(fg_color=CF_ORANGE if name == "telegram" else "transparent", text_color="black" if name == "telegram" else "gray90")
        self.btn_dns.configure(fg_color=CF_ORANGE if name == "dns" else "transparent", text_color="black" if name == "dns" else "gray90")
        self.btn_tools.configure(fg_color=CF_ORANGE if name == "tools" else "transparent", text_color="black" if name == "tools" else "gray90")
        self.btn_storage.configure(fg_color=CF_ORANGE if name == "storage" else "transparent", text_color="black" if name == "storage" else "gray90")

        # نمایش یا مخفی کردن فریم‌ها
        self.client_frame.grid(row=0, column=1, sticky="nsew") if name == "client" else self.client_frame.grid_forget()
        self.scanner_frame.grid(row=0, column=1, sticky="nsew") if name == "scanner" else self.scanner_frame.grid_forget()
        self.speed_frame.grid(row=0, column=1, sticky="nsew") if name == "speed" else self.speed_frame.grid_forget()
        self.telegram_frame.grid(row=0, column=1, sticky="nsew") if name == "telegram" else self.telegram_frame.grid_forget()
        self.dns_frame.grid(row=0, column=1, sticky="nsew") if name == "dns" else self.dns_frame.grid_forget()
        self.tools_frame.grid(row=0, column=1, sticky="nsew") if name == "tools" else self.tools_frame.grid_forget()
        
        # رفرش دیتا برای استوریج
        if name == "storage":
            self.storage_frame.refresh_data()
            self.storage_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.storage_frame.grid_forget()
            
        # رفرش کانفیگ‌ها برای کلاینت
        if name == "client":
            self.client_frame.load_configs()

    def on_closing(self):
        """هنگام بستن برنامه، مطمئن می‌شویم که تنظیمات سیستم به حالت عادی برگردد"""
        # خاموش کردن VPN و پروکسی سیستم
        if hasattr(self, 'client_frame'):
            self.client_frame.on_closing()
            
        # خاموش کردن دی‌ان‌اس (ریست به حالت اتوماتیک) تا اینترنت کاربر قطع نماند
        if hasattr(self, 'dns_frame') and getattr(self.dns_frame, 'is_connected', False):
            try:
                self.dns_frame.disconnect_dns(update_ui=False)
            except Exception:
                pass
                
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = App()
    app.mainloop()
