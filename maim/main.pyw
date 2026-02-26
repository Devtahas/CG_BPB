# main.pyw
import customtkinter as ctk
from tab_scanner import ScannerFrame
from tab_telegram import TelegramFrame
from tab_tools import ToolsFrame
from tab_speedtest import SpeedtestFrame
from tab_storage import StorageFrame
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

        # برای دسترسی اسکنر به تابع تغییر تب، خود app را به آن پاس می‌دهیم
        self.scanner_frame = ScannerFrame(self, app_controller=self, fg_color="transparent")
        self.speed_frame = SpeedtestFrame(self, fg_color="transparent")
        self.telegram_frame = TelegramFrame(self, fg_color="transparent")
        self.tools_frame = ToolsFrame(self, fg_color="transparent")
        self.storage_frame = StorageFrame(self, fg_color="transparent")

        self.select_frame_by_name("scanner")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=BG_PANEL)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="☁️ NetTools Pro", font=ctk.CTkFont(size=22, weight="bold"), text_color=CF_ORANGE)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        btn_font = ctk.CTkFont(size=14, weight="bold")
        
        self.btn_scanner = ctk.CTkButton(self.sidebar_frame, text="⚡ CF Scanner", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("scanner"))
        self.btn_scanner.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_speed = ctk.CTkButton(self.sidebar_frame, text="🚀 IP Speedtest", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("speed"))
        self.btn_speed.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_telegram = ctk.CTkButton(self.sidebar_frame, text="✈️ Telegram Proxy", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("telegram"))
        self.btn_telegram.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_tools = ctk.CTkButton(self.sidebar_frame, text="🛠️ Generators", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("tools"))
        self.btn_tools.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_storage = ctk.CTkButton(self.sidebar_frame, text="💾 Storage (Memory)", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("storage"))
        self.btn_storage.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

    def select_frame_by_name(self, name):
        self.btn_scanner.configure(fg_color=CF_ORANGE if name == "scanner" else "transparent", text_color="black" if name == "scanner" else "gray90")
        self.btn_speed.configure(fg_color=CF_ORANGE if name == "speed" else "transparent", text_color="black" if name == "speed" else "gray90")
        self.btn_telegram.configure(fg_color=CF_ORANGE if name == "telegram" else "transparent", text_color="black" if name == "telegram" else "gray90")
        self.btn_tools.configure(fg_color=CF_ORANGE if name == "tools" else "transparent", text_color="black" if name == "tools" else "gray90")
        self.btn_storage.configure(fg_color=CF_ORANGE if name == "storage" else "transparent", text_color="black" if name == "storage" else "gray90")

        self.scanner_frame.grid(row=0, column=1, sticky="nsew") if name == "scanner" else self.scanner_frame.grid_forget()
        self.speed_frame.grid(row=0, column=1, sticky="nsew") if name == "speed" else self.speed_frame.grid_forget()
        self.telegram_frame.grid(row=0, column=1, sticky="nsew") if name == "telegram" else self.telegram_frame.grid_forget()
        self.tools_frame.grid(row=0, column=1, sticky="nsew") if name == "tools" else self.tools_frame.grid_forget()
        
        if name == "storage":
            self.storage_frame.refresh_data() # رفرش خودکار تب حافظه هنگام باز شدن
            self.storage_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.storage_frame.grid_forget()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = App()
    app.mainloop()