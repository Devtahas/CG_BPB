# tabs/status/status_ui.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import random
import tkinter as tk
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK

from .status_utils import StatusUtils
from .status_core import StatusCore


class StatusUI(ctk.CTkFrame):
    """داشبورد حرفه‌ای با اطلاعات و نمودارهای زنده"""

    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.core = StatusCore(app_controller)
        self.core.start_monitoring()

        self.setup_ui()

        # بروزرسانی دوره‌ای (هر ۲ ثانیه)
        self.after(2000, self._periodic_update)

        # پلاگین‌ها
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("status")

    def _periodic_update(self):
        if self.core.running:
            data = self.core.get_data()
            quality = self.core.get_quality()
            self.update_ui(data, quality)
            self.after(2000, self._periodic_update)

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="📊 Dashboard & Status",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        self.btn_refresh = ctk.CTkButton(header_frame, text="🔄 Refresh", width=80,
                                         fg_color="transparent", border_width=1,
                                         border_color=CF_ORANGE, text_color=CF_ORANGE,
                                         command=self.manual_refresh)
        self.btn_refresh.pack(side="right", padx=40)

        # تب‌ها
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE,
                                      segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.tab_overview = self.tabview.add("📡 Overview")
        self.tab_network = self.tabview.add("🌐 Network")
        self.tab_services = self.tabview.add("🔌 Services")
        self.tab_packet = self.tabview.add("📦 Packet Path")

        self.setup_overview_tab()
        self.setup_network_tab()
        self.setup_services_tab()
        self.setup_packet_tab()

    # ======================== تب Overview ========================
    def setup_overview_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_overview, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # کارت کیفیت شبکه
        quality_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        quality_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(quality_frame, text="📶 Network Quality Index",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(15,5))
        self.quality_label = ctk.CTkLabel(quality_frame, text="--",
                                         font=ctk.CTkFont(size=48, weight="bold"))
        self.quality_label.pack(pady=5)
        self.quality_bar = ctk.CTkProgressBar(quality_frame, width=350, progress_color=CF_ORANGE)
        self.quality_bar.pack(pady=10)
        self.quality_desc = ctk.CTkLabel(quality_frame, text="", font=ctk.CTkFont(size=14))
        self.quality_desc.pack(pady=(0,15))

        # خلاصه سرویس‌های فعال
        services_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        services_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(services_frame, text="✅ Active Services",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15,5))
        self.active_text = ctk.CTkTextbox(services_frame, height=120, font=ctk.CTkFont(size=12))
        self.active_text.pack(fill="x", padx=20, pady=10)
        self.active_text.configure(state="disabled")

        # IP عمومی و ISP
        ip_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ip_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(ip_frame, text="🌍 Public IP & Location",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#AB47BC").pack(pady=(15,5))
        self.ip_label = ctk.CTkLabel(ip_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.ip_label.pack(pady=5)
        self.location_label = ctk.CTkLabel(ip_frame, text="", text_color="gray")
        self.location_label.pack(pady=(0,15))

    # ======================== تب Network ========================
    def setup_network_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_network, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # پینگ و پکت لاس
        ping_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ping_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(ping_frame, text="📡 Ping & Packet Loss",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(15,5))

        stats_frame = ctk.CTkFrame(ping_frame, fg_color="transparent")
        stats_frame.pack(pady=10)
        ctk.CTkLabel(stats_frame, text="Ping:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5)
        self.ping_label = ctk.CTkLabel(stats_frame, text="-- ms", font=ctk.CTkFont(size=15))
        self.ping_label.grid(row=0, column=1, padx=10, pady=5)
        ctk.CTkLabel(stats_frame, text="Packet Loss:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=5)
        self.loss_label = ctk.CTkLabel(stats_frame, text="--%", font=ctk.CTkFont(size=15))
        self.loss_label.grid(row=1, column=1, padx=10, pady=5)

        # سرعت فعلی
        speed_info = ctk.CTkFrame(ping_frame, fg_color="transparent")
        speed_info.pack(pady=5)
        self.dl_label = ctk.CTkLabel(speed_info, text="⬇️ 0.0 KB/s", font=ctk.CTkFont(size=13, weight="bold"))
        self.dl_label.pack(side="left", padx=15)
        self.ul_label = ctk.CTkLabel(speed_info, text="⬆️ 0.0 KB/s", font=ctk.CTkFont(size=13, weight="bold"))
        self.ul_label.pack(side="left", padx=15)

        # نمودار سرعت (زنده)
        speed_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        speed_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(speed_frame, text="📈 Live Speed Graph",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15,5))
        self.speed_canvas_frame = ctk.CTkFrame(speed_frame, fg_color="transparent")
        self.speed_canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.dl_history = []
        self.ul_history = []
        self.speed_fig = None
        self.speed_ax = None
        self.speed_canvas = None
        self.init_speed_graph()

        # ISP
        isp_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        isp_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(isp_frame, text="🏢 ISP Info",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#AB47BC").pack(pady=(15,5))
        self.isp_label = ctk.CTkLabel(isp_frame, text="", text_color="gray", font=ctk.CTkFont(size=13))
        self.isp_label.pack(pady=(0,15))

    # ======================== تب Services ========================
    def setup_services_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_services, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        services = [
            ("🛡️ VPN Client", "vpn"),
            ("🌍 DNS Changer", "dns"),
            ("🌪️ WARP", "warp"),
            ("🧅 Tor", "tor"),
            ("🅿️ Psiphon", "psiphon"),
            ("🆘 Anti-Filter", "antifilter"),
            ("🎮 Gaming", "gaming"),
            ("💬 Messenger", "messenger"),
            ("🌐 Browser Tor", "browser"),
        ]
        self.service_cards = {}
        for name, key in services:
            card = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=10)
            card.pack(fill="x", pady=5)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=20, pady=12, sticky="w")
            status_lbl = ctk.CTkLabel(card, text="⚪ Inactive", text_color="gray", font=ctk.CTkFont(size=13))
            status_lbl.grid(row=0, column=1, padx=20, pady=12, sticky="e")
            self.service_cards[key] = status_lbl

    # ======================== تب Packet Path ========================
    def setup_packet_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_packet, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        packet_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        packet_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(packet_frame, text="📦 Packet Path Simulation",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(15,5))
        ctk.CTkLabel(packet_frame, text="Visual representation of your data journey", text_color="gray").pack()

        self.packet_canvas = tk.Canvas(packet_frame, width=600, height=200, bg=BG_DARK, highlightthickness=0)
        self.packet_canvas.pack(pady=20, padx=20)
        self.draw_packet_path()

        dpi_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        dpi_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(dpi_frame, text="🛡️ DPI & Anti-Filter Actions",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15,5))
        self.dpi_label = ctk.CTkLabel(dpi_frame, text="No DPI bypass active", text_color="gray")
        self.dpi_label.pack(pady=10)

        route_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        route_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(route_frame, text="🧠 Smart Route Suggestion",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#AB47BC").pack(pady=(15,5))
        self.route_suggestion = ctk.CTkLabel(route_frame, text="", text_color="gray", font=ctk.CTkFont(size=13))
        self.route_suggestion.pack(pady=10)
        ctk.CTkButton(route_frame, text="Apply Suggestion", fg_color=CF_ORANGE, text_color="black",
                      command=self.apply_suggestion).pack(pady=(0,15))

    # ======================== نمودار سرعت ========================
    def init_speed_graph(self):
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            self.speed_fig = Figure(figsize=(5, 2), facecolor='#1a1a1a')
            self.speed_ax = self.speed_fig.add_subplot(111)
            self.speed_ax.set_facecolor('#2a2a2a')
            self.speed_ax.set_xlabel('Time', color='white')
            self.speed_ax.set_ylabel('KB/s', color='white')
            self.speed_ax.tick_params(colors='white')
            for spine in self.speed_ax.spines.values():
                spine.set_color('gray')
            self.speed_canvas = FigureCanvasTkAgg(self.speed_fig, self.speed_canvas_frame)
            self.speed_canvas.draw()
            self.speed_canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception:
            ctk.CTkLabel(self.speed_canvas_frame, text="📉 Install matplotlib for live graph", text_color="gray").pack()

    def update_speed_graph(self, dl_speed, ul_speed):
        if self.speed_ax is None or self.speed_canvas is None:
            return
        self.dl_history.append(dl_speed)
        self.ul_history.append(ul_speed)
        max_len = 30
        if len(self.dl_history) > max_len:
            self.dl_history.pop(0)
            self.ul_history.pop(0)
        self.speed_ax.clear()
        x = range(len(self.dl_history))
        self.speed_ax.plot(x, self.dl_history, color=CF_ORANGE, linewidth=2, label='Download')
        self.speed_ax.plot(x, self.ul_history, color="#29B6F6", linewidth=2, label='Upload')
        self.speed_ax.legend(loc='upper left', fontsize=8, facecolor='#2a2a2a', edgecolor='white', labelcolor='white')
        max_y = max(max(self.dl_history, default=0), max(self.ul_history, default=0)) * 1.2 or 100
        self.speed_ax.set_ylim(0, max_y)
        self.speed_ax.set_xlabel('Time (s)', color='white')
        self.speed_ax.set_ylabel('KB/s', color='white')
        self.speed_ax.tick_params(colors='white')
        self.speed_canvas.draw()

    # ======================== مسیر پکت ========================
    def draw_packet_path(self):
        self.packet_canvas.delete("all")
        points = [(50, 100), (200, 80), (350, 120), (500, 100), (550, 100)]
        for i in range(len(points)-1):
            self.packet_canvas.create_line(points[i][0], points[i][1],
                                           points[i+1][0], points[i+1][1],
                                           fill=CF_ORANGE, width=2, arrow="last")
        self.packet_canvas.create_oval(40, 90, 60, 110, fill="#29B6F6", outline="")
        self.packet_canvas.create_text(50, 125, text="You", fill="white", font=("Arial", 10))
        self.packet_canvas.create_oval(190, 70, 210, 90, fill="#AB47BC", outline="")
        self.packet_canvas.create_text(200, 105, text="VPN", fill="white", font=("Arial", 10))
        self.packet_canvas.create_oval(340, 110, 360, 130, fill="#EF5350", outline="")
        self.packet_canvas.create_text(350, 145, text="Internet", fill="white", font=("Arial", 10))
        self.packet_canvas.create_oval(490, 90, 510, 110, fill="#66BB6A", outline="")
        self.packet_canvas.create_text(500, 125, text="Server", fill="white", font=("Arial", 10))
        self.animate_packet(points)

    def animate_packet(self, points):
        self.packet_dot = self.packet_canvas.create_oval(45, 95, 55, 105, fill=CF_ORANGE, outline="")
        self.packet_index = 0
        self.move_packet(points)

    def move_packet(self, points):
        if self.packet_index < len(points):
            x, y = points[self.packet_index]
            self.packet_canvas.coords(self.packet_dot, x-5, y-5, x+5, y+5)
            self.packet_index += 1
            self.after(500, lambda: self.move_packet(points))
        else:
            self.packet_index = 0
            self.after(500, lambda: self.move_packet(points))

    # ======================== بروزرسانی UI ========================
    def update_ui(self, data, quality):
        # کیفیت
        self.after(0, lambda: self.quality_label.configure(text=f"{quality}"))
        self.after(0, lambda: self.quality_bar.set(quality/100.0))
        if quality >= 80:
            desc, color = "Excellent", "#66BB6A"
        elif quality >= 50:
            desc, color = "Good", "#29B6F6"
        elif quality >= 25:
            desc, color = "Fair", "#FFA726"
        else:
            desc, color = "Poor", "#EF5350"
        self.after(0, lambda: self.quality_desc.configure(text=desc, text_color=color))

        # سرویس‌های فعال (لیست خلاصه)
        active_list = []
        if data["vpn"]["connected"]:
            active_list.append("VPN Client")
        if data["dns"]["connected"]:
            active_list.append("DNS Changer")
        if data["warp"]["connected"]:
            active_list.append("WARP")
        if data["tor"]["connected"]:
            active_list.append("Tor")
        if data["psiphon"]["connected"]:
            active_list.append("Psiphon")
        if data["antifilter"]["running"]:
            active_list.append("Anti-Filter")
        if data["gaming"]["accelerator"] or data["gaming"]["ping_stab"]:
            active_list.append("Gaming Mode")
        if data["messenger"]["hosting"] or data["messenger"]["connected"]:
            active_list.append("Messenger")
        active_text = "\n".join(active_list) if active_list else "No active services"
        self.after(0, lambda: self.active_text.configure(state="normal"))
        self.after(0, lambda: self.active_text.delete("1.0", "end"))
        self.after(0, lambda: self.active_text.insert("1.0", active_text))
        self.after(0, lambda: self.active_text.configure(state="disabled"))

        # IP و ISP
        flag = StatusUtils.get_flag_emoji(data["network"]["countryCode"])
        self.after(0, lambda: self.ip_label.configure(text=f"{flag} {data['network']['public_ip']}"))
        self.after(0, lambda: self.location_label.configure(
            text=f"{data['network']['country']} — {data['network']['isp']}"))

        # پینگ و لاس
        ping = data["network"]["ping"]
        loss = data["network"]["packet_loss"]
        self.after(0, lambda: self.ping_label.configure(text=f"{ping} ms"))
        self.after(0, lambda: self.loss_label.configure(text=f"{loss:.1f}%"))

        # سرعت لحظه‌ای
        dl = data["network"]["download_speed"]
        ul = data["network"]["upload_speed"]
        self.after(0, lambda: self.dl_label.configure(text=f"⬇️ {dl:.1f} KB/s"))
        self.after(0, lambda: self.ul_label.configure(text=f"⬆️ {ul:.1f} KB/s"))
        self.update_speed_graph(dl, ul)

        # ISP
        self.after(0, lambda: self.isp_label.configure(text=data['network']['isp']))

        # کارت‌های سرویس
        service_map = {
            "vpn": data["vpn"]["connected"],
            "dns": data["dns"]["connected"],
            "warp": data["warp"]["connected"],
            "tor": data["tor"]["connected"],
            "psiphon": data["psiphon"]["connected"],
            "antifilter": data["antifilter"]["running"],
            "gaming": data["gaming"]["accelerator"] or data["gaming"]["ping_stab"],
            "messenger": data["messenger"]["hosting"] or data["messenger"]["connected"],
            "browser": data["browser"]["tor_mode"],
        }
        for key, active in service_map.items():
            if active:
                self.after(0, lambda k=key: self.service_cards[k].configure(
                    text="🟢 Active", text_color="#66BB6A"))
            else:
                self.after(0, lambda k=key: self.service_cards[k].configure(
                    text="⚪ Inactive", text_color="gray"))

        # پیشنهاد مسیر
        if ping > 150 and loss > 5:
            suggestion = "High latency & loss — try VPN or Anti-Filter."
        elif ping > 100:
            suggestion = "High latency — consider Gaming Mode or Tor."
        elif loss > 2:
            suggestion = "Packet loss detected — enable Ping Stabilizer in Gaming tab."
        else:
            suggestion = "Network quality is good. No action needed."
        self.after(0, lambda: self.route_suggestion.configure(text=suggestion))

        # DPI Info
        if data["antifilter"]["running"]:
            dpi_text = "Anti-Filter active: Multi-layer bypass engaged."
        elif data["vpn"]["connected"]:
            dpi_text = "VPN active: Traffic encrypted & tunneled."
        elif data["tor"]["connected"]:
            dpi_text = "Tor active: Traffic anonymized via 3 relays."
        else:
            dpi_text = "No DPI bypass active — traffic may be filtered."
        self.after(0, lambda: self.dpi_label.configure(text=dpi_text))

    def manual_refresh(self):
        self.core._collect_services_status()
        self.core._update_network_quality()
        self.core._update_public_ip()
        self.core._calculate_quality_index()
        self.update_ui(self.core.get_data(), self.core.get_quality())

    def apply_suggestion(self):
        if self.app_controller:
            self.app_controller.select_frame_by_name("antifilter")
            messagebox.showinfo("Smart Route", "Anti-Filter tab opened.")

    def load_category_plugins(self, category: str):
        app = self.master
        if not hasattr(app, "plugin_manager"):
            return
        pm = app.plugin_manager
        for p in pm.get_plugins_by_category(category):
            plugin_id = p["id"]
            manifest = p["manifest"]
            tab_name = manifest.get("name", plugin_id)[:25]
            try:
                new_tab = self.tabview.add(tab_name)
            except Exception:
                new_tab = self.tabview.add(f"{tab_name}_{random.randint(0, 999)}")
            instance = pm.get_plugin_instance(plugin_id)
            if instance:
                panel = instance.get_ui_panel(new_tab)
                if panel:
                    panel.pack(fill="both", expand=True, padx=10, pady=10)
