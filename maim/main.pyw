# main.pyw
import customtkinter as ctk
import threading
import pystray
from PIL import Image, ImageDraw
import sys

from tab_scanner import ScannerFrame
from tab_telegram import TelegramFrame
from tab_tools import ToolsFrame
from tab_speedtest import SpeedtestFrame
from tab_storage import StorageFrame
from tab_client import ClientFrame
from tab_dns import DNSChangerFrame
from tab_warp import WarpFrame
from tab_psiphon import PsiphonFrame
from tab_tor import TorFrame
from tab_antifilter import AntiFilterFrame

from config import CF_ORANGE, BG_DARK, BG_PANEL

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NetTools Pro - Cloudflare Edition")
        self.geometry("1000x750")
        self.minsize(950, 650)
        self.resizable(True, True) 
        self.center_window(1000, 750)

        self.configure(fg_color=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.tray_icon = None

        self.create_sidebar()

        self.scanner_frame = ScannerFrame(self, app_controller=self, fg_color="transparent")
        self.speed_frame = SpeedtestFrame(self, fg_color="transparent")
        self.telegram_frame = TelegramFrame(self, fg_color="transparent")
        self.tools_frame = ToolsFrame(self, fg_color="transparent")
        self.storage_frame = StorageFrame(self, fg_color="transparent")
        self.client_frame = ClientFrame(self, fg_color="transparent")
        self.dns_frame = DNSChangerFrame(self, fg_color="transparent")
        
        self.warp_frame = WarpFrame(self, fg_color="transparent")
        self.psiphon_frame = PsiphonFrame(self, fg_color="transparent")
        self.tor_frame = TorFrame(self, fg_color="transparent")
        
        # مقداردهی فریم آنتی فیلتر همراه با app_controller برای دسترسی به سوئیچ تب
        self.antifilter_frame = AntiFilterFrame(self, app_controller=self, fg_color="transparent")

        self.select_frame_by_name("scanner")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=BG_PANEL)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(12, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="☁️ NetTools Pro", font=ctk.CTkFont(size=22, weight="bold"), text_color=CF_ORANGE)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        btn_font = ctk.CTkFont(size=14, weight="bold")
        
        self.btn_client = ctk.CTkButton(self.sidebar_frame, text="🛡️ VPN Client (v2ray)", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("client"))
        self.btn_client.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.btn_antifilter = ctk.CTkButton(self.sidebar_frame, text="🆘 Anti-Filter (Panic)", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#8E0000", anchor="w", command=lambda: self.select_frame_by_name("antifilter"))
        self.btn_antifilter.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.btn_warp = ctk.CTkButton(self.sidebar_frame, text="🌪️ WARP / WireGuard", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("warp"))
        self.btn_warp.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.btn_psiphon = ctk.CTkButton(self.sidebar_frame, text="🅿️ Psiphon Network", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("psiphon"))
        self.btn_psiphon.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.btn_tor = ctk.CTkButton(self.sidebar_frame, text="🧅 Tor Network", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("tor"))
        self.btn_tor.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        self.btn_scanner = ctk.CTkButton(self.sidebar_frame, text="⚡ CF Scanner", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("scanner"))
        self.btn_scanner.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        self.btn_speed = ctk.CTkButton(self.sidebar_frame, text="🚀 IP Speedtest", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("speed"))
        self.btn_speed.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        self.btn_telegram = ctk.CTkButton(self.sidebar_frame, text="✈️ Telegram Proxy", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("telegram"))
        self.btn_telegram.grid(row=8, column=0, padx=20, pady=5, sticky="ew")

        self.btn_dns = ctk.CTkButton(self.sidebar_frame, text="🌍 DNS Changer", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("dns"))
        self.btn_dns.grid(row=9, column=0, padx=20, pady=5, sticky="ew")

        self.btn_tools = ctk.CTkButton(self.sidebar_frame, text="🛠️ Generators", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("tools"))
        self.btn_tools.grid(row=10, column=0, padx=20, pady=5, sticky="ew")

        self.btn_storage = ctk.CTkButton(self.sidebar_frame, text="💾 Storage (Memory)", font=btn_font, fg_color="transparent", text_color="gray90", hover_color="#332015", anchor="w", command=lambda: self.select_frame_by_name("storage"))
        self.btn_storage.grid(row=11, column=0, padx=20, pady=5, sticky="ew")

    def select_frame_by_name(self, name):
        buttons = {
            "client": self.btn_client, "scanner": self.btn_scanner, "speed": self.btn_speed,
            "telegram": self.btn_telegram, "dns": self.btn_dns, "tools": self.btn_tools,
            "storage": self.btn_storage, "warp": self.btn_warp, "psiphon": self.btn_psiphon, 
            "tor": self.btn_tor, "antifilter": self.btn_antifilter
        }
        
        for btn_name, btn in buttons.items():
            if btn_name == "antifilter":
                btn.configure(fg_color="#C62828" if name == btn_name else "transparent", 
                              text_color="white" if name == btn_name else "gray90")
            else:
                btn.configure(fg_color=CF_ORANGE if name == btn_name else "transparent", 
                              text_color="black" if name == btn_name else "gray90")

        frames = {
            "client": self.client_frame, "scanner": self.scanner_frame, "speed": self.speed_frame,
            "telegram": self.telegram_frame, "dns": self.dns_frame, "tools": self.tools_frame,
            "storage": self.storage_frame, "warp": self.warp_frame, "psiphon": self.psiphon_frame, 
            "tor": self.tor_frame, "antifilter": self.antifilter_frame
        }

        for frame_name, frame in frames.items():
            if name == frame_name:
                frame.grid(row=0, column=1, sticky="nsew")
            else:
                frame.grid_forget()
        
        if name == "storage": self.storage_frame.refresh_data()
        if name == "client": self.client_frame.load_configs()

    def create_tray_image(self):
        image = Image.new('RGB', (64, 64), color=(24, 24, 27))
        dc = ImageDraw.Draw(image)
        dc.rectangle((8, 8, 56, 56), fill=(243, 128, 32)) 
        return image

    def on_closing(self):
        is_vpn_on = getattr(self.client_frame, 'is_connected', False)
        is_dns_on = getattr(self.dns_frame, 'is_connected', False)
        is_warp_on = getattr(self.warp_frame, 'is_connected', False)
        is_tor_on = getattr(self.tor_frame, 'is_connected', False)
        is_psiphon_on = getattr(self.psiphon_frame, 'is_connected', False)
        is_antifilter_on = getattr(self.antifilter_frame, 'is_running', False)

        if any([is_vpn_on, is_dns_on, is_warp_on, is_tor_on, is_psiphon_on, is_antifilter_on]):
            self.withdraw()
            self.show_tray_icon()
        else:
            self.force_quit()

    def show_tray_icon(self):
        if self.tray_icon is not None: return 
        menu = pystray.Menu(
            pystray.MenuItem('🌐 Open NetTools', self.restore_window, default=True), 
            pystray.MenuItem('⏹ Disconnect & Exit', self.force_quit)
        )
        self.tray_icon = pystray.Icon("NetTools", self.create_tray_image(), "NetTools Pro (Running...)", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore_window(self, icon, item):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.deiconify) 

    def force_quit(self, icon=None, item=None):
        if self.tray_icon: self.tray_icon.stop()
        
        if hasattr(self, 'client_frame'): self.client_frame.stop_connection()
        if hasattr(self, 'warp_frame'): self.warp_frame.stop_connection()
        if hasattr(self, 'tor_frame'): self.tor_frame.stop_connection()
        if hasattr(self, 'psiphon_frame'): self.psiphon_frame.stop_connection()
        if hasattr(self, 'antifilter_frame'): self.antifilter_frame.stop_connection()
        if hasattr(self, 'dns_frame') and getattr(self.dns_frame, 'is_connected', False):
            try: self.dns_frame.disconnect_dns(update_ui=False)
            except: pass
            
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = App()
    app.mainloop()
    