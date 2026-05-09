# tabs/scanner/scanner_ui.py
import customtkinter as ctk
from tkinter import messagebox
import os
import shutil
import threading
import json
import random
from config import (
    CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, DIRS, BASE_DIR,
    CLOUDFLARE_CIDRS, DEFAULT_DNS, STANDARD_PORTS
)
from .scanner_core import ScannerCore
from .scanner_config import ScannerConfig
from .scanner_utils import ScannerUtils
from .scanner_managers import ScannerManagers
# ایمپورت MimicryManager برای دسترسی به پراکسی شبیه‌سازی
from tabs.client.mimicry import MimicryManager


class ScannerUI(ctk.CTkFrame):
    """کلاس اصلی UI اسکنر - فقط چیدمان و رویدادها"""

    def __init__(self, master, app_controller=None, asset_manager=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.asset_manager = asset_manager
        self.grid_columnconfigure(0, weight=1)

        # هسته اصلی اسکنر
        self.core = ScannerCore()
        self.core.set_callbacks(self.log, self.update_progress_callback)

        # مدیریت‌ها
        self.managers = ScannerManagers(self)

        # مسیرها
        self.target_dir = BASE_DIR
        self.configs_dir = DIRS["configs"]
        self.subs_dir = DIRS["subs"]

        # متغیرهای UI
        self.var_tls = ctk.IntVar(value=1)
        self.var_none = ctk.IntVar(value=1)
        self.var_h2 = ctk.IntVar(value=1)
        self.var_http1 = ctk.IntVar(value=1)
        self.var_ws = ctk.IntVar(value=1)
        self.var_grpc = ctk.IntVar(value=0)
        self.var_tcp = ctk.IntVar(value=0)
        self.var_frag_enable = ctk.IntVar(value=1)
        self.frag_mode = ctk.StringVar(value="Auto")
        self.ip_source = ctk.StringVar(value="Default List")
        self.scan_mode = ctk.StringVar(value="Standard Ports")

        # دیکشنری‌ها و لیست‌ها — از منبع مرکزی یا پیش‌فرض
        if self.asset_manager:
            self.dns_list = self.asset_manager.get_dns_list()
            self.custom_cidrs = self.asset_manager.get_ip_list("cloudflare")
        else:
            self.dns_list = DEFAULT_DNS.copy()
            self.custom_cidrs = CLOUDFLARE_CIDRS.copy()
        self.custom_ports = STANDARD_PORTS.copy()
        self.fragment_settings = {"packets": "1-1", "length": "100-200", "interval": "1"}

        # دریافت نمونه mimicry_manager از app_controller
        self.mimicry_manager = None
        if self.app_controller and hasattr(self.app_controller, 'client_frame'):
            if hasattr(self.app_controller.client_frame, 'mimicry_manager'):
                self.mimicry_manager = self.app_controller.client_frame.mimicry_manager

        # ایجاد UI
        self.setup_ui()
        self.load_config()

        # اتصال به core
        self.core.dns_list = self.dns_list
        self.core.custom_ports = self.custom_ports
        self.core.custom_cidrs = self.custom_cidrs
        self.core.var_tls = self.var_tls
        self.core.var_none = self.var_none
        self.core.var_h2 = self.var_h2
        self.core.var_http1 = self.var_http1
        self.core.var_ws = self.var_ws
        self.core.var_grpc = self.var_grpc
        self.core.var_tcp = self.var_tcp
        self.core.fragment_settings = self.fragment_settings

        # ★ پشتیبانی از پلاگین‌های دسته "scanner"
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("scanner")

    def setup_ui(self):
        config_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        config_frame.grid(row=0, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(config_frame, text="UUID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_uuid = ctk.CTkEntry(config_frame, width=220, placeholder_text="VLESS UUID")
        self.entry_uuid.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkLabel(config_frame, text="WS/gRPC Path:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entry_path = ctk.CTkEntry(config_frame, width=120, placeholder_text="/path")
        self.entry_path.grid(row=0, column=3, padx=10, pady=10)

        ctk.CTkLabel(config_frame, text="Worker Host:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_host = ctk.CTkEntry(config_frame, width=220, placeholder_text="app.workers.dev")
        self.entry_host.grid(row=1, column=1, padx=10, pady=10)

        perf_frame = ctk.CTkFrame(self, fg_color="transparent")
        perf_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        perf_frame.grid_columnconfigure((0, 1), weight=1)

        thread_frame = ctk.CTkFrame(perf_frame, fg_color=BG_PANEL, corner_radius=10)
        thread_frame.grid(row=0, column=0, padx=5, sticky="ew")
        self.lbl_threads = ctk.CTkLabel(thread_frame, text="Threads: 50")
        self.lbl_threads.pack(pady=(5, 0))
        self.slider_threads = ctk.CTkSlider(thread_frame, from_=10, to=200, number_of_steps=19,
                                            progress_color=CF_ORANGE, command=self.update_thread_lbl)
        self.slider_threads.set(50)
        self.slider_threads.pack(pady=10, padx=10, fill="x")

        ip_frame = ctk.CTkFrame(perf_frame, fg_color=BG_PANEL, corner_radius=10)
        ip_frame.grid(row=0, column=1, padx=5, sticky="ew")
        self.lbl_ips = ctk.CTkLabel(ip_frame, text="IPs per Range: 100")
        self.lbl_ips.pack(pady=(5, 0))
        self.slider_ips = ctk.CTkSlider(ip_frame, from_=10, to=500, number_of_steps=49, progress_color=CF_ORANGE,
                                        command=self.update_ip_lbl)
        self.slider_ips.set(100)
        self.slider_ips.pack(pady=10, padx=10, fill="x")

        opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        opt_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        opt_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.ip_source = ctk.StringVar(value="Default List")
        self.seg_source = ctk.CTkSegmentedButton(opt_frame, values=["Default List", "Fetch API IPs"],
                                                 variable=self.ip_source, selected_color=CF_ORANGE,
                                                 selected_hover_color=CF_ORANGE_HOVER)
        self.seg_source.grid(row=0, column=0, padx=2, sticky="ew")

        self.scan_mode = ctk.StringVar(value="Standard Ports")
        self.seg_ports = ctk.CTkSegmentedButton(opt_frame, values=["Standard Ports", "Deep Scan (All)"],
                                                variable=self.scan_mode, selected_color=CF_ORANGE,
                                                selected_hover_color=CF_ORANGE_HOVER)
        self.seg_ports.grid(row=0, column=1, padx=2, sticky="ew")

        btn_dns = ctk.CTkButton(opt_frame, text="⚙️ DNS", fg_color="transparent", border_width=1,
                                border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015",
                                command=self.open_dns_manager)
        btn_dns.grid(row=0, column=2, padx=2, sticky="ew")

        btn_cidrs = ctk.CTkButton(opt_frame, text="🌐 IP Ranges", fg_color="transparent", border_width=1,
                                  border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015",
                                  command=self.open_cidr_manager)
        btn_cidrs.grid(row=0, column=3, padx=2, sticky="ew")

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(filter_frame, text="⚙️ Config Types:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(filter_frame, text="TLS", variable=self.var_tls, fg_color=CF_ORANGE,
                        hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)
        ctk.CTkCheckBox(filter_frame, text="None", variable=self.var_none, fg_color=CF_ORANGE,
                        hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)
        ctk.CTkCheckBox(filter_frame, text="H2", variable=self.var_h2, fg_color=CF_ORANGE,
                        hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)
        ctk.CTkCheckBox(filter_frame, text="HTTP/1.1", variable=self.var_http1, fg_color=CF_ORANGE,
                        hover_color=CF_ORANGE_HOVER).pack(side="left", padx=10)

        btn_ports = ctk.CTkButton(filter_frame, text="🔌 Ports & Network", fg_color="transparent", border_width=1,
                                  border_color="#29B6F6", text_color="#29B6F6", hover_color="#0D47A1",
                                  command=self.open_ports_manager)
        btn_ports.pack(side="right", padx=0)

        # ================= FRAGMENT FRAME =================
        frag_frame = ctk.CTkFrame(self, fg_color="transparent")
        frag_frame.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.chk_frag = ctk.CTkCheckBox(frag_frame, text="🧩 Enable Fragment", font=ctk.CTkFont(weight="bold"),
                                        variable=self.var_frag_enable, fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER,
                                        command=self.toggle_frag_ui)
        self.chk_frag.pack(side="left", padx=(0, 10))

        self.frag_mode = ctk.StringVar(value="Auto")
        self.seg_frag = ctk.CTkSegmentedButton(frag_frame, values=["Auto", "Manual"], variable=self.frag_mode,
                                               selected_color=CF_ORANGE, selected_hover_color=CF_ORANGE_HOVER,
                                               command=self.toggle_frag_ui)
        self.seg_frag.pack(side="left", padx=10)

        ctk.CTkLabel(frag_frame, text="Packets:").pack(side="left", padx=(10, 2))
        self.entry_frag_packets = ctk.CTkEntry(frag_frame, width=70, placeholder_text="1-1")
        self.entry_frag_packets.pack(side="left", padx=2)

        ctk.CTkLabel(frag_frame, text="Length:").pack(side="left", padx=(10, 2))
        self.entry_frag_length = ctk.CTkEntry(frag_frame, width=80, placeholder_text="100-200")
        self.entry_frag_length.pack(side="left", padx=2)

        ctk.CTkLabel(frag_frame, text="Interval:").pack(side="left", padx=(10, 2))
        self.entry_frag_interval = ctk.CTkEntry(frag_frame, width=60, placeholder_text="1")
        self.entry_frag_interval.pack(side="left", padx=2)

        self.toggle_frag_ui()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.btn_start = ctk.CTkButton(btn_frame, text="▶ START ADVANCED SCAN", fg_color=CF_ORANGE,
                                       hover_color=CF_ORANGE_HOVER, text_color="black",
                                       font=ctk.CTkFont(weight="bold", size=14), command=self.start_scan)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=5, ipady=5)

        self.btn_stop = ctk.CTkButton(btn_frame, text="⏹ STOP & GENERATE", fg_color="#C62828", hover_color="#8E0000",
                                      font=ctk.CTkFont(weight="bold", size=14), state="disabled",
                                      command=self.stop_scan)
        self.btn_stop.pack(side="right", expand=True, fill="x", padx=5, ipady=5)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Ready", text_color=CF_ORANGE, font=ctk.CTkFont(weight="bold"))
        self.lbl_status.grid(row=6, column=0, padx=20, sticky="w")

        self.progressbar = ctk.CTkProgressBar(self, progress_color=CF_ORANGE)
        self.progressbar.grid(row=7, column=0, padx=20, pady=5, sticky="ew")
        self.progressbar.set(0)

        self.log_box = ctk.CTkTextbox(self, height=110, font=ctk.CTkFont(family="Consolas", size=12),
                                      fg_color=BG_PANEL, border_color="gray20", border_width=1)
        self.log_box.grid(row=8, column=0, padx=20, pady=5, sticky="nsew")

    # ==========================================
    # متدهای کمکی UI
    # ==========================================
    def update_thread_lbl(self, val):
        self.lbl_threads.configure(text=f"Threads: {int(val)}")

    def update_ip_lbl(self, val):
        self.lbl_ips.configure(text=f"IPs per Range: {int(val)}")

    def toggle_frag_ui(self, *args):
        is_enabled = self.var_frag_enable.get() == 1
        mode = self.frag_mode.get()

        if not is_enabled:
            self.seg_frag.configure(state="disabled")
            self.entry_frag_packets.configure(state="disabled", fg_color=BG_PANEL)
            self.entry_frag_length.configure(state="disabled", fg_color=BG_PANEL)
            self.entry_frag_interval.configure(state="disabled", fg_color=BG_PANEL)
        else:
            self.seg_frag.configure(state="normal")
            if mode == "Manual":
                self.entry_frag_packets.configure(state="normal", fg_color="#121212")
                self.entry_frag_length.configure(state="normal", fg_color="#121212")
                self.entry_frag_interval.configure(state="normal", fg_color="#121212")
            else:
                self.entry_frag_packets.configure(state="disabled", fg_color=BG_PANEL)
                self.entry_frag_length.configure(state="disabled", fg_color=BG_PANEL)
                self.entry_frag_interval.configure(state="disabled", fg_color=BG_PANEL)

    # ==========================================
    # مدیریت‌ها (متصل به AssetManager مرکزی)
    # ==========================================
    def open_cidr_manager(self):
        # استفاده از callback برای به‌روزرسانی همزمان asset_manager
        def on_cidr_update():
            if self.asset_manager:
                self.asset_manager.update_ip_list("cloudflare", self.custom_cidrs)
            self.save_config()  # تنظیمات دیگر را همچنان ذخیره کن
        self.managers.open_cidr_manager(
            self.custom_cidrs,
            on_cidr_update,
            lambda: None
        )

    def open_dns_manager(self):
        def on_dns_update():
            if self.asset_manager:
                self.asset_manager.update_dns_list(self.dns_list)
            self.save_config()
        self.managers.open_dns_manager(
            self.dns_list,
            on_dns_update,
            lambda: None
        )

    def open_ports_manager(self):
        # پورت‌ها هنوز در asset_manager مرکزی ذخیره نمی‌شوند، فقط محلی
        self.managers.open_ports_manager(
            self.custom_ports,
            self.var_ws,
            self.var_grpc,
            self.var_tcp,
            self.save_config
        )

    # ==========================================
    # متدهای اصلی اسکن
    # ==========================================
    def start_scan(self):
        """شروع اسکن"""
        if not self.entry_uuid.get() or not self.entry_host.get():
            messagebox.showerror("Error", "Please fill UUID and Host fields!")
            return

        # ★ بررسی انتخاب حداقل یک نوع کانفیگ
        if self.var_tls.get() == 0 and self.var_none.get() == 0:
            messagebox.showerror("Error", "Please enable at least one config type (TLS or None).")
            return

        # تنظیم core
        self.core.entry_host = self.entry_host.get()
        self.core.entry_path = self.entry_path.get()
        self.core.stop_event.clear()
        self.core.best_pairs = []
        self.core.completed_tasks = 0

        # === بخش Traffic Mimicry برای اسکنر ===
        if self.mimicry_manager and self.mimicry_manager.enabled:
            proxy_address = self.mimicry_manager.get_proxy_address()
            self.core.proxy_address = proxy_address
            self.log(f"[*] Traffic Mimicry is active. Using proxy: {proxy_address}")
        else:
            self.core.proxy_address = None
            self.log("[*] Traffic Mimicry is disabled. Scanning directly.")

        # همگام‌سازی لیست‌های نهایی قبل از اسکن (کاربر ممکن است از managers تغییر داده باشد)
        self.core.dns_list = self.dns_list
        self.core.custom_cidrs = self.custom_cidrs

        # آماده‌سازی پوشه‌ها
        if os.path.exists(self.configs_dir):
            try:
                shutil.rmtree(self.configs_dir)
            except:
                pass
        os.makedirs(self.configs_dir, exist_ok=True)
        os.makedirs(self.subs_dir, exist_ok=True)

        # تشخیص Fragment
        self.fragment_settings = ScannerUtils.detect_isp_and_adjust_fragment(
            self.var_frag_enable.get(), self.frag_mode.get(),
            self.entry_frag_packets.get(), self.entry_frag_length.get(),
            self.entry_frag_interval.get(), self.log
        )
        self.core.fragment_settings = self.fragment_settings

        # شروع اسکن در ترد جداگانه
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal", text="⏹ STOP & GENERATE")
        self.log_box.delete("1.0", "end")

        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        """اجرای اسکن در ترد جداگانه"""
        result = self.core.scan_engine(
            self.ip_source.get(),
            int(self.slider_ips.get()),
            int(self.slider_threads.get()),
            self.scan_mode.get()
        )

        # تولید کانفیگ نهایی
        config_gen = ScannerConfig(self.configs_dir, self.subs_dir)
        vless_links, ips_found = config_gen.generate_final_configs(
            self.core.best_pairs, self.var_tls, self.var_none, self.var_h2, self.var_http1,
            self.var_ws, self.var_grpc, self.var_tcp, self.var_frag_enable, self.fragment_settings,
            self.entry_uuid.get(), self.entry_host.get(), self.entry_path.get(), self.log
        )

        self.after(0, lambda: self.btn_start.configure(state="normal"))
        self.after(0, lambda: self.btn_stop.configure(state="disabled", text="⏹ STOP & GENERATE"))
        self.after(0, lambda: self.lbl_status.configure(text="Status: Finished & Saved!"))
        self.after(0, lambda: self.show_summary_popup(ips_found, len(vless_links)))

    def stop_scan(self):
        """توقف اسکن"""
        self.core.stop_event.set()
        self.btn_stop.configure(state="disabled", text="⏳ GENERATING...")
        self.log("\n[!] STOP PRESSED! Halting scanner...")

    def log(self, text):
        """لاگ کردن در UI (thread-safe)"""
        self.after(0, lambda: self.log_box.insert("end", text + "\n"))
        self.after(0, lambda: self.log_box.see("end"))

    def update_progress_callback(self, completed, total, found):
        """به‌روزرسانی پروگرس بار"""
        pct = completed / total if total > 0 else 0
        self.after(0, lambda: self.progressbar.set(pct))
        self.after(0, lambda: self.lbl_status.configure(text=f"Scanning: {completed}/{total} | Found: {found}"))

    # ==========================================
    # پاپ‌آپ خلاصه
    # ==========================================
    def show_summary_popup(self, ips_found, configs_generated):
        """نمایش خلاصه اسکن"""
        popup = ctk.CTkToplevel(self)
        popup.title("Generation Report")
        popup.geometry("350x250")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=BG_PANEL)

        if ips_found == 0 or configs_generated == 0:
            ctk.CTkLabel(popup, text="⚠️", font=ctk.CTkFont(size=40)).pack(pady=(20, 0))
            ctk.CTkLabel(popup, text="No configs were generated!", font=ctk.CTkFont(size=16, weight="bold"),
                         text_color="red").pack(pady=10)
        else:
            ctk.CTkLabel(popup, text="✅", font=ctk.CTkFont(size=40)).pack(pady=(20, 0))
            ctk.CTkLabel(popup, text="Success!", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack()

            ctk.CTkLabel(popup, text=f"Clean IPs Found: {ips_found}", font=ctk.CTkFont(size=14)).pack(pady=(10, 2))
            ctk.CTkLabel(popup, text=f"Configs Generated: {configs_generated} (Top 15 IPs)",
                         font=ctk.CTkFont(size=14)).pack(pady=(2, 10))

            ctk.CTkButton(popup, text="📂 Go to Storage", fg_color=CF_ORANGE, text_color="black",
                          hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold"),
                          command=lambda: self.go_to_storage(popup)).pack(pady=10)

    def go_to_storage(self, popup_window):
        """رفتن به تب استوریج"""
        popup_window.destroy()
        if self.app_controller:
            self.app_controller.select_frame_by_name("storage")

    # ==========================================
    # بارگذاری و ذخیره تنظیمات (فقط غیر از IP و DNS)
    # ==========================================
    def load_config(self):
        path = os.path.join(DIRS["settings"], "Scanner_Config.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.entry_uuid.delete(0, 'end')
                self.entry_uuid.insert(0, data.get('UUID', ''))
                self.entry_path.delete(0, 'end')
                self.entry_path.insert(0, data.get('PATH', ''))
                self.entry_host.delete(0, 'end')
                self.entry_host.insert(0, data.get('HOST', ''))

                # DNS و CIDR دیگر از اینجا لود نمی‌شوند (از asset_manager)
                if 'PORTS' in data:
                    self.custom_ports = data['PORTS']
                if 'TLS' in data:
                    self.var_tls.set(data['TLS'])
                if 'NONE' in data:
                    self.var_none.set(data['NONE'])
                if 'H2' in data:
                    self.var_h2.set(data['H2'])
                if 'HTTP1' in data:
                    self.var_http1.set(data['HTTP1'])
                if 'WS' in data:
                    self.var_ws.set(data['WS'])
                if 'GRPC' in data:
                    self.var_grpc.set(data['GRPC'])
                if 'TCP' in data:
                    self.var_tcp.set(data['TCP'])

                if 'FRAG_ENABLE' in data:
                    self.var_frag_enable.set(data['FRAG_ENABLE'])
                if 'FRAG_MODE' in data:
                    self.frag_mode.set(data['FRAG_MODE'])
                if 'FRAG_PACKETS' in data:
                    self.entry_frag_packets.delete(0, 'end')
                    self.entry_frag_packets.insert(0, data['FRAG_PACKETS'])
                if 'FRAG_LENGTH' in data:
                    self.entry_frag_length.delete(0, 'end')
                    self.entry_frag_length.insert(0, data['FRAG_LENGTH'])
                if 'FRAG_INTERVAL' in data:
                    self.entry_frag_interval.delete(0, 'end')
                    self.entry_frag_interval.insert(0, data['FRAG_INTERVAL'])
            except Exception:
                pass

        self.toggle_frag_ui()

    def save_config(self):
        path = os.path.join(DIRS["settings"], "Scanner_Config.json")
        data = {
            'UUID': self.entry_uuid.get(),
            'PATH': self.entry_path.get(),
            'HOST': self.entry_host.get(),
            'PORTS': self.custom_ports,
            'TLS': self.var_tls.get(),
            'NONE': self.var_none.get(),
            'H2': self.var_h2.get(),
            'HTTP1': self.var_http1.get(),
            'WS': self.var_ws.get(),
            'GRPC': self.var_grpc.get(),
            'TCP': self.var_tcp.get(),
            'FRAG_ENABLE': self.var_frag_enable.get(),
            'FRAG_MODE': self.frag_mode.get(),
            'FRAG_PACKETS': self.entry_frag_packets.get(),
            'FRAG_LENGTH': self.entry_frag_length.get(),
            'FRAG_INTERVAL': self.entry_frag_interval.get()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ★ متد بارگذاری پلاگین‌ها
    def load_category_plugins(self, category: str):
        """پلاگین‌های اسکنر را در پنجره‌های مجزا باز می‌کند، زیرا ScannerUI تب‌ویو ندارد."""
        app = self.master
        if not hasattr(app, "plugin_manager"):
            return

        pm = app.plugin_manager
        for p in pm.get_plugins_by_category(category):
            plugin_id = p["id"]
            manifest = p["manifest"]
            instance = pm.get_plugin_instance(plugin_id)
            if instance:
                panel = instance.get_ui_panel(None)
                if panel:
                    win = ctk.CTkToplevel(self)
                    win.title(f"Scanner Plugin: {manifest.get('name', plugin_id)}")
                    win.geometry("500x400")
                    win.configure(fg_color=BG_PANEL)
                    panel.pack(fill="both", expand=True, padx=10, pady=10)
