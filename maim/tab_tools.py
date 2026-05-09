# tab_tools.py
import customtkinter as ctk
import random
import os
import threading
from config import CF_ORANGE, CF_ORANGE_HOVER
from tabs.tools import (
    GeneratorsTab, ExtractorTab, PortScannerTab,
    ProfileMakerTab, DatacenterScanner, DNSScanner, FastlyScanner
)
from tabs.tools.preprocessor import PreProcessorProxy      # فقط برای ارجاع نوع
from tabs.tools.whitelist_profiler import WhitelistProfiler
from tabs.client.mimicry.mimicry_profile import MimicryProfile   # برای لود پروفایل


class ToolsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        asset_manager = kwargs.pop('asset_manager', None)

        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="🛠️ Tools & Generators",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, pady=(30, 10))

        self.tabview = ctk.CTkTabview(
            self,
            segmented_button_selected_color=CF_ORANGE,
            segmented_button_selected_hover_color=CF_ORANGE_HOVER
        )
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # تب‌های اصلی
        self.generators = GeneratorsTab(self, self.tabview)
        self.extractor = ExtractorTab(self, self.tabview)
        self.port_scanner = PortScannerTab(self, self.tabview)
        self.profile_maker = ProfileMakerTab(self, self.tabview)
        self.datacenter_scanner = DatacenterScanner(self, self.tabview, asset_manager=asset_manager)
        self.fastly_scanner = FastlyScanner(self, self.tabview, asset_manager=asset_manager)
        self.dns_scanner = DNSScanner(self, self.tabview)

        # تب جدید پیش‌پردازشگر
        self.setup_preprocessor_tab()

        # پلاگین‌ها
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("tools")

    # ======================== تب Pre‑Processor ========================
    def setup_preprocessor_tab(self):
        self.pre_tab = self.tabview.add("🛡️ Pre‑Processor")
        scroll = ctk.CTkScrollableFrame(self.pre_tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # توضیح
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🛡️ Local Traffic Pre‑Processor",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(anchor="w")
        ctk.CTkLabel(header, text="Shape all scanner/network traffic before it leaves your device, "
                                  "making it look like a normal website. No external server needed.",
                     text_color="gray", wraplength=600).pack(anchor="w", pady=(5, 0))

        # وضعیت و کنترل
        control_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        control_frame.pack(fill="x", pady=(0, 15))

        self.pre_status_label = ctk.CTkLabel(control_frame, text="Status: Stopped", text_color="#EF5350",
                                             font=ctk.CTkFont(weight="bold"))
        self.pre_status_label.pack(side="left", padx=(0, 15))

        self.btn_toggle = ctk.CTkButton(control_frame, text="▶ Start Proxy",
                                       fg_color="#2E7D32", hover_color="#1B5E20",
                                       command=self.toggle_preprocessor)
        self.btn_toggle.pack(side="left")

        # پروفایل
        profile_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        profile_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(profile_frame, text="🎭 Active Whitelist Profile:",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w")

        select_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        select_frame.pack(fill="x", pady=5)

        self.profile_combo = ctk.CTkComboBox(select_frame, values=["No profiles"],
                                             width=250, state="readonly",
                                             command=self.on_profile_selected)
        self.profile_combo.pack(side="left", padx=(0, 10))
        self.btn_load_profile = ctk.CTkButton(select_frame, text="Load Selected",
                                             fg_color="transparent", border_width=1,
                                             border_color=CF_ORANGE, text_color=CF_ORANGE,
                                             command=self.load_selected_profile)
        self.btn_load_profile.pack(side="left", padx=(0, 5))

        # دکمه‌های خودکار
        auto_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        auto_frame.pack(fill="x", pady=10)
        self.btn_auto_profile = ctk.CTkButton(auto_frame, text="🔍 Auto-Detect Best Site & Create Profile",
                                              fg_color="#1565C0", hover_color="#0D47A1",
                                              command=self.auto_create_profile)
        self.btn_auto_profile.pack(side="left", padx=(0, 10))

        self.auto_status = ctk.CTkLabel(auto_frame, text="", text_color="gray")
        self.auto_status.pack(side="left")

        # نوار پیشرفت
        self.auto_progress = ctk.CTkProgressBar(scroll, progress_color=CF_ORANGE)
        self.auto_progress.pack(fill="x", pady=10)
        self.auto_progress.set(0)

        # لاگ
        self.pre_log = ctk.CTkTextbox(scroll, height=120, font=ctk.CTkFont(size=11))
        self.pre_log.pack(fill="both", expand=True)

        # لود اولیه لیست پروفایل‌ها
        self.refresh_profile_list()
        self.update_pre_ui()

    def refresh_profile_list(self):
        """لیست پروفایل‌های موجود در پوشه mimicry_profiles را می‌خواند."""
        profiles_dir = os.path.join(os.path.dirname(__file__), "..", "..", "settings", "mimicry_profiles")
        if not os.path.exists(profiles_dir):
            # fallback
            profiles_dir = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data", "Settings", "mimicry_profiles")
        if not os.path.exists(profiles_dir):
            self.profile_combo.configure(values=["No profiles"])
            return
        names = [f.replace('.json', '') for f in os.listdir(profiles_dir) if f.endswith('.json')]
        if not names:
            self.profile_combo.configure(values=["No profiles"])
            return
        self.profile_combo.configure(values=names)
        if names:
            self.profile_combo.set(names[0])

    def on_profile_selected(self, choice):
        """فقط انتخاب UI – هیچ کاری نمی‌کند."""
        pass

    def load_selected_profile(self):
        """پروفایل انتخاب‌شده را در Pre‑Processor بارگذاری می‌کند."""
        choice = self.profile_combo.get()
        if not choice or choice == "No profiles":
            return
        profiles_dir = os.path.join(os.path.dirname(__file__), "..", "..", "settings", "mimicry_profiles")
        if not os.path.exists(profiles_dir):
            profiles_dir = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data", "Settings", "mimicry_profiles")
        path = os.path.join(profiles_dir, f"{choice}.json")
        if not os.path.exists(path):
            self.log_pre("❌ Profile file not found.", "#EF5350")
            return
        try:
            profile = MimicryProfile()
            profile.load(path)
            app = self.master  # App instance
            if hasattr(app, 'preprocessor'):
                app.preprocessor.profile = profile
                self.log_pre(f"✅ Profile '{choice}' loaded into Pre‑Processor.", "#66BB6A")
        except Exception as e:
            self.log_pre(f"❌ Failed to load profile: {str(e)}", "#EF5350")

    def toggle_preprocessor(self):
        """شروع/توقف پروکسی محلی"""
        app = self.master
        if not hasattr(app, 'preprocessor'):
            return
        if app.preprocessor.is_running():
            app.preprocessor.stop()
            self.log_pre("Pre‑Processor stopped.", "gray")
        else:
            # اگر پروفایل ست نشده، سعی کن از کامبو بارگذاری کن
            if app.preprocessor.profile is None or app.preprocessor.profile.name == "Default":
                choice = self.profile_combo.get()
                if choice and choice != "No profiles":
                    self.load_selected_profile()
            success = app.preprocessor.start()
            if success:
                self.log_pre(f"✅ Pre‑Processor started on 127.0.0.1:{app.preprocessor.listen_port}", "#66BB6A")
            else:
                self.log_pre("❌ Failed to start Pre‑Processor (port busy?)", "#EF5350")
        self.update_pre_ui()

    def update_pre_ui(self):
        """به‌روزرسانی دکمه و وضعیت بر اساس وضعیت پروکسی"""
        app = self.master
        running = False
        if hasattr(app, 'preprocessor'):
            running = app.preprocessor.is_running()
        if running:
            self.btn_toggle.configure(text="⏹ Stop Proxy", fg_color="#C62828", hover_color="#8E0000")
            self.pre_status_label.configure(text=f"Running on 127.0.0.1:10815", text_color="#66BB6A")
        else:
            self.btn_toggle.configure(text="▶ Start Proxy", fg_color="#2E7D32", hover_color="#1B5E20")
            self.pre_status_label.configure(text="Status: Stopped", text_color="#EF5350")

    def auto_create_profile(self):
        """در بک‌گراند بهترین سایت لیست‌سفید را پیدا کرده و پروفایل می‌سازد."""
        self.btn_auto_profile.configure(state="disabled", text="Working...")
        self.auto_status.configure(text="Testing websites...", text_color=CF_ORANGE)
        self.auto_progress.set(0.1)
        threading.Thread(target=self._run_auto_profiling, daemon=True).start()

    def _run_auto_profiling(self):
        profiler = WhitelistProfiler()
        try:
            self.log_pre("🔍 Searching for best whitelist domain...")
            best = profiler.find_best_whitelist_domain()
            if not best:
                self.master.after(0, lambda: self.auto_status.configure(text="No site reachable!", text_color="#EF5350"))
                self.master.after(0, lambda: self.btn_auto_profile.configure(state="normal", text="Auto-Detect..."))
                return
            domain = best['domain']
            self.log_pre(f"🏆 Best site: {domain} ({best['latency_ms']:.0f}ms)")
            self.master.after(0, lambda: self.auto_status.configure(text=f"Capturing {domain}...", text_color=CF_ORANGE))
            self.master.after(0, lambda: self.auto_progress.set(0.5))
            self.log_pre("📹 Creating mimicry profile (this may take a minute)...")
            profile = profiler.create_profile_for_domain(domain, use_recorder=True, record_duration=30)
            if profile:
                self.log_pre(f"✅ Profile '{profile.name}' created successfully!", "#66BB6A")
                # بارگذاری خودکار در پراکسی
                app = self.master
                if hasattr(app, 'preprocessor'):
                    app.preprocessor.profile = profile
                self.master.after(0, lambda: self.auto_progress.set(1.0))
                self.master.after(0, lambda: self.auto_status.configure(text="Profile ready & loaded", text_color="#66BB6A"))
                self.master.after(0, self.refresh_profile_list)
                self.master.after(500, lambda: self.profile_combo.set(profile.name))
            else:
                self.log_pre("❌ Failed to create profile.", "#EF5350")
                self.master.after(0, lambda: self.auto_status.configure(text="Creation failed", text_color="#EF5350"))
        except Exception as e:
            self.log_pre(f"❌ Error: {str(e)}", "#EF5350")
        finally:
            self.master.after(0, lambda: self.btn_auto_profile.configure(state="normal", text="Auto-Detect..."))

    def log_pre(self, message, color="white"):
        """لاگ در Textbox تب Pre‑Processor"""
        self.pre_log.insert("end", message + "\n")
        self.pre_log.see("end")

    # ======================== پلاگین‌ها ========================
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
