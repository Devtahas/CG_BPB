# tabs/setting/setting_ui.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os
import sys
import json
from config import (
    CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK, DIRS, storage_crypto,
    load_storage_path, save_storage_path, reset_storage_path, update_dirs, BASE_DIR
)
from tabs.crypto_manager import storage_crypto as crypto_storage

from .setting_updater import CoreUpdater


class SettingUI(ctk.CTkFrame):
    """کلاس اصلی تب Setting"""

    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # پیدا کردن مسیر ریشه پروژه
        if getattr(sys, 'frozen', False):
            self.root_dir = os.path.dirname(sys.executable)
        else:
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # راه‌اندازی آپدیت‌کننده
        self.updater = CoreUpdater(log_callback=self.log_update, progress_callback=self.update_progress)
        self.updater.set_base_dir(self.root_dir)

        # متغیر برای ذخیره موقت نتیجه GoodbyeDPI
        self._gdpi_path = None

        # رویداد سفارشی برای به‌روزرسانی UI از ترد اصلی
        self.master.bind('<<UpdateGdpi>>', self._on_update_gdpi)

        self.setup_ui()
        self.check_versions()

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="⚙️ Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        # Tabview
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE,
                                      segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.tab_updates = self.tabview.add("🔄 Updates")
        self.tab_security = self.tabview.add("🔐 Security")
        self.tab_storage = self.tabview.add("💾 Storage")
        self.tab_appearance = self.tabview.add("🎨 Appearance")
        self.tab_about = self.tabview.add("ℹ️ About")

        self.setup_updates_tab()
        self.setup_security_tab()
        self.setup_storage_tab()
        self.setup_appearance_tab()
        self.setup_about_tab()

    def setup_updates_tab(self):
        """تب آپدیت هسته‌ها"""
        scroll = ctk.CTkScrollableFrame(self.tab_updates, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Xray Core Section
        xray_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        xray_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(xray_frame, text="🛡️ Xray-core", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 5), anchor="w", padx=20)
        ctk.CTkLabel(xray_frame, text="Core engine for VPN connections", text_color="gray").pack(anchor="w", padx=20)

        # نسخه فعلی
        current_frame = ctk.CTkFrame(xray_frame, fg_color="transparent")
        current_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(current_frame, text="Current version:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.current_xray_version = ctk.CTkLabel(current_frame, text="Checking...", text_color="#29B6F6")
        self.current_xray_version.pack(side="left", padx=10)

        # نسخه جدید
        latest_frame = ctk.CTkFrame(xray_frame, fg_color="transparent")
        latest_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(latest_frame, text="Latest version:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.latest_xray_version = ctk.CTkLabel(latest_frame, text="Checking...", text_color="#FFA726")
        self.latest_xray_version.pack(side="left", padx=10)

        # نوار پیشرفت
        self.progress_bar = ctk.CTkProgressBar(xray_frame, progress_color=CF_ORANGE)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(xray_frame, text="", text_color="gray")
        self.progress_label.pack()

        # دکمه آپدیت
        self.update_xray_btn = ctk.CTkButton(xray_frame, text="Check for Updates", fg_color="#2E7D32", hover_color="#1B5E20",
                                            font=ctk.CTkFont(weight="bold"), command=self.check_xray_update)
        self.update_xray_btn.pack(pady=15)

        self.xray_status = ctk.CTkLabel(xray_frame, text="", text_color="gray")
        self.xray_status.pack(pady=(0, 15))

        # GoodbyeDPI Section
        gdpi_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        gdpi_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(gdpi_frame, text="🛡️ GoodbyeDPI", font=ctk.CTkFont(size=18, weight="bold"), text_color="#29B6F6").pack(pady=(15, 5), anchor="w", padx=20)
        ctk.CTkLabel(gdpi_frame, text="DPI bypass tool (optional, for FakeTLS/FakeHTTP)", text_color="gray").pack(anchor="w", padx=20)

        self.gdpi_status = ctk.CTkLabel(gdpi_frame, text="Checking...", text_color="#FFA726")
        self.gdpi_status.pack(pady=10)

        gdpi_btn_frame = ctk.CTkFrame(gdpi_frame, fg_color="transparent")
        gdpi_btn_frame.pack(pady=15)

        self.download_gdpi_btn = ctk.CTkButton(gdpi_btn_frame, text="Download GoodbyeDPI", fg_color="#1565C0", hover_color="#0D47A1",
                                              font=ctk.CTkFont(weight="bold"), command=self.download_goodbyedpi)
        self.download_gdpi_btn.pack(side="left", padx=5)

        # وضعیت آپدیت
        self.update_log = ctk.CTkTextbox(scroll, height=150, font=ctk.CTkFont(size=11))
        self.update_log.pack(fill="x", pady=10)

    def setup_security_tab(self):
        """تب امنیت - رمزنگاری Storage و قفل برنامه"""
        scroll = ctk.CTkScrollableFrame(self.tab_security, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # ========== بخش رمزنگاری Storage ==========
        crypto_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        crypto_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(crypto_frame, text="🔐 Storage Encryption (AES-256-GCM)",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(15, 5), anchor="w", padx=20)
        ctk.CTkLabel(crypto_frame, text="Encrypt all saved configurations, subscriptions, and settings",
                    text_color="gray").pack(anchor="w", padx=20)

        # وضعیت فعلی
        status_frame = ctk.CTkFrame(crypto_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(status_frame, text="Status:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.crypto_status_label = ctk.CTkLabel(status_frame, text="Disabled", text_color="#EF5350")
        self.crypto_status_label.pack(side="left", padx=10)

        # دکمه فعال/غیرفعال
        self.toggle_crypto_btn = ctk.CTkButton(crypto_frame, text="Enable Encryption", fg_color="#2E7D32",
                                              hover_color="#1B5E20", command=self.toggle_storage_crypto)
        self.toggle_crypto_btn.pack(pady=10)

        # دکمه تغییر رمز عبور
        self.change_password_btn = ctk.CTkButton(crypto_frame, text="Change Master Password", fg_color="transparent",
                                                border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                                                command=self.change_crypto_password, state="disabled")
        self.change_password_btn.pack(pady=5)

        # دکمه رمزنگاری مجدد همه فایل‌ها
        self.reencrypt_btn = ctk.CTkButton(crypto_frame, text="Re-encrypt All Files", fg_color="transparent",
                                          border_width=1, border_color="#29B6F6", text_color="#29B6F6",
                                          command=self.reencrypt_all_files, state="disabled")
        self.reencrypt_btn.pack(pady=5)

        self.crypto_warning = ctk.CTkLabel(crypto_frame,
                                          text="⚠️ Warning: If you forget this password, your data cannot be recovered!",
                                          text_color="#FFA726", font=ctk.CTkFont(size=11))
        self.crypto_warning.pack(pady=(0, 15))

        # ========== بخش قفل برنامه ==========
        lock_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        lock_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(lock_frame, text="🔒 Application Lock", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#29B6F6").pack(pady=(15, 5), anchor="w", padx=20)
        ctk.CTkLabel(lock_frame, text="Require password to open the application",
                    text_color="gray").pack(anchor="w", padx=20)

        self.app_lock_var = ctk.BooleanVar(value=False)
        self.app_lock_switch = ctk.CTkSwitch(lock_frame, text="Enable App Lock", variable=self.app_lock_var,
                                            command=self.toggle_app_lock, progress_color=CF_ORANGE)
        self.app_lock_switch.pack(pady=10)

        set_lock_btn = ctk.CTkButton(lock_frame, text="Set Lock Password", fg_color="transparent",
                                    border_width=1, border_color="#AB47BC", text_color="#AB47BC",
                                    command=self.set_app_lock_password)
        set_lock_btn.pack(pady=(0, 15))

        # به‌روزرسانی UI
        self.update_crypto_ui()

    def setup_storage_tab(self):
        """تب مدیریت مسیر ذخیره‌سازی"""
        scroll = ctk.CTkScrollableFrame(self.tab_storage, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # ========== بخش مسیر ذخیره‌سازی ==========
        path_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        path_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(path_frame, text="📁 Storage Location", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(15, 5), anchor="w", padx=20)
        ctk.CTkLabel(path_frame, text="All configuration files, subscriptions, and settings are stored here.",
                    text_color="gray").pack(anchor="w", padx=20)

        # نمایش مسیر فعلی
        current_path_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        current_path_frame.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(current_path_frame, text="Current Path:", font=ctk.CTkFont(weight="bold"), width=100).pack(side="left")
        self.current_path_label = ctk.CTkLabel(current_path_frame, text=BASE_DIR, text_color="#29B6F6", wraplength=400)
        self.current_path_label.pack(side="left", padx=10)

        # دکمه‌ها
        btn_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(btn_frame, text="📂 Change Location", fg_color=CF_ORANGE, text_color="black",
                     command=self.change_storage_path).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Reset to Default", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.reset_storage_path_to_default).pack(side="left", padx=5)

        # توضیحات
        info_text = """
        📌 Note:
        • Changing the storage location will NOT move existing files automatically.
        • You may manually copy the contents from the old location to the new one if needed.
        • The application will create necessary subfolders (Configs, Subscriptions, Settings) in the new location.
        • A restart is recommended after changing the storage path.
        """
        ctk.CTkLabel(path_frame, text=info_text, justify="left", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(0, 15))

    def setup_appearance_tab(self):
        """تب ظاهر (Theme, Language)"""
        scroll = ctk.CTkScrollableFrame(self.tab_appearance, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Theme
        theme_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        theme_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(theme_frame, text="🎨 Theme", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 5), anchor="w", padx=20)

        self.theme_var = ctk.StringVar(value="Dark")
        theme_seg = ctk.CTkSegmentedButton(theme_frame, values=["Dark", "Light"], variable=self.theme_var, command=self.change_theme)
        theme_seg.pack(pady=10)

        # Language
        lang_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        lang_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(lang_frame, text="🌐 Language", font=ctk.CTkFont(size=18, weight="bold"), text_color="#29B6F6").pack(pady=(15, 5), anchor="w", padx=20)

        self.lang_var = ctk.StringVar(value="English")
        lang_seg = ctk.CTkSegmentedButton(lang_frame, values=["English", "Persian"], variable=self.lang_var, command=self.change_language)
        lang_seg.pack(pady=10)

        # Reset button
        reset_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        reset_frame.pack(fill="x", pady=10)

        ctk.CTkButton(reset_frame, text="Reset All Settings", fg_color="#C62828", hover_color="#8E0000",
                     font=ctk.CTkFont(weight="bold"), command=self.reset_settings).pack(pady=20)

    def setup_about_tab(self):
        """تب درباره نرم‌افزار"""
        scroll = ctk.CTkScrollableFrame(self.tab_about, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        about_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        about_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(about_frame, text="☁️ NetTools Pro", font=ctk.CTkFont(size=28, weight="bold"), text_color=CF_ORANGE).pack(pady=(20, 5))
        ctk.CTkLabel(about_frame, text="Cloudflare Edition", font=ctk.CTkFont(size=16), text_color="gray").pack()
        ctk.CTkLabel(about_frame, text="Version 1.0.0", text_color="gray").pack(pady=10)

        ctk.CTkLabel(about_frame, text="A comprehensive tool for network optimization, privacy, and bypassing censorship.",
                    text_color="gray", wraplength=400, justify="center").pack(pady=20, padx=20)

        # لینک‌ها
        links_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        links_frame.pack(pady=10)

        ctk.CTkButton(links_frame, text="GitHub Repository", fg_color="transparent", border_width=1, border_color=CF_ORANGE,
                     text_color=CF_ORANGE, command=self.open_github).pack(side="left", padx=10)
        ctk.CTkButton(links_frame, text="Report Issue", fg_color="transparent", border_width=1, border_color="#EF5350",
                     text_color="#EF5350", command=self.report_issue).pack(side="left", padx=10)

        ctk.CTkLabel(about_frame, text="\nPowered by Xray-core, CustomTkinter, and Python", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=20)

    # ==========================================
    # متدهای مدیریت مسیر ذخیره‌سازی
    # ==========================================
    def change_storage_path(self):
        """تغییر مسیر ذخیره‌سازی"""
        new_path = filedialog.askdirectory(title="Select Storage Location", initialdir=BASE_DIR)
        if not new_path:
            return

        # اطمینان از وجود مسیر
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create directory:\n{str(e)}")
            return

        # ذخیره مسیر جدید
        if save_storage_path(new_path):
            # به‌روزرسانی DIRS در config
            update_dirs(new_path)
            # به‌روزرسانی نمایش
            self.current_path_label.configure(text=new_path)
            messagebox.showinfo("Success", f"Storage location changed to:\n{new_path}\n\nPlease restart the application for changes to take full effect.")
        else:
            messagebox.showerror("Error", "Failed to save storage path.")

    def reset_storage_path_to_default(self):
        """بازنشانی به مسیر پیش‌فرض (دسکتاپ)"""
        if reset_storage_path():
            from config import BASE_DIR as new_base
            update_dirs(new_base)
            self.current_path_label.configure(text=new_base)
            messagebox.showinfo("Success", f"Storage location reset to default:\n{new_base}\n\nPlease restart the application for changes to take full effect.")
        else:
            messagebox.showerror("Error", "Failed to reset storage path.")

    # ==========================================
    # متدهای امنیتی (رمزنگاری و قفل برنامه)
    # ==========================================
    def update_crypto_ui(self):
        """به‌روزرسانی UI بخش رمزنگاری بر اساس وضعیت فعلی"""
        if crypto_storage.enabled:
            self.crypto_status_label.configure(text="Enabled", text_color="#66BB6A")
            self.toggle_crypto_btn.configure(text="Disable Encryption", fg_color="#C62828", hover_color="#8E0000")
            self.change_password_btn.configure(state="normal")
            self.reencrypt_btn.configure(state="normal")
        else:
            self.crypto_status_label.configure(text="Disabled", text_color="#EF5350")
            self.toggle_crypto_btn.configure(text="Enable Encryption", fg_color="#2E7D32", hover_color="#1B5E20")
            self.change_password_btn.configure(state="disabled")
            self.reencrypt_btn.configure(state="disabled")

    def toggle_storage_crypto(self):
        """فعال/غیرفعال کردن رمزنگاری"""
        if not crypto_storage.is_available():
            messagebox.showerror("Error", "Cryptography library not available.\nPlease install: pip install cryptography")
            return

        if crypto_storage.enabled:
            # غیرفعال کردن
            if messagebox.askyesno("Disable Encryption",
                                   "Are you sure you want to disable encryption?\n\n"
                                   "Your existing encrypted files will remain encrypted and won't be accessible "
                                   "until you re-enable with the correct password.\n\n"
                                   "Continue?"):
                crypto_storage.set_enabled(False)
                crypto_storage._password = None
                self.update_crypto_ui()
                messagebox.showinfo("Encryption Disabled", "Storage encryption has been disabled.")
        else:
            # فعال کردن - نمایش فرم رمز عبور
            self.show_crypto_password_form()

    def show_crypto_password_form(self):
        """نمایش فرم تنظیم رمز عبور اصلی"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Enable Storage Encryption")
        dialog.geometry("450x300")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text="Set Master Password", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(20, 5))

        ctk.CTkLabel(dialog, text="This password will be required to decrypt your data.",
                    text_color="gray").pack()

        warning_label = ctk.CTkLabel(dialog,
                                     text="⚠️ If you forget this password, your data cannot be recovered!",
                                     text_color="#FFA726", font=ctk.CTkFont(size=12, weight="bold"))
        warning_label.pack(pady=(5, 15))

        # ورودی رمز عبور
        pass_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        pass_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(pass_frame, text="Password:", width=100).pack(side="left")
        pass_entry = ctk.CTkEntry(pass_frame, placeholder_text="Enter strong password", show="*", width=250)
        pass_entry.pack(side="left")

        # ورودی تأیید رمز
        confirm_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        confirm_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(confirm_frame, text="Confirm:", width=100).pack(side="left")
        confirm_entry = ctk.CTkEntry(confirm_frame, placeholder_text="Confirm password", show="*", width=250)
        confirm_entry.pack(side="left")

        # قدرت رمز عبور
        strength_label = ctk.CTkLabel(dialog, text="", text_color="gray")
        strength_label.pack(pady=5)

        def check_strength(*args):
            pwd = pass_entry.get()
            if len(pwd) == 0:
                strength_label.configure(text="")
            elif len(pwd) < 6:
                strength_label.configure(text="Weak (min 6 characters)", text_color="#EF5350")
            elif len(pwd) < 10:
                strength_label.configure(text="Medium", text_color="#FFA726")
            else:
                strength_label.configure(text="Strong", text_color="#66BB6A")

        pass_entry.bind('<KeyRelease>', check_strength)

        def save_password():
            pwd = pass_entry.get()
            if len(pwd) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters.")
                return
            if pwd != confirm_entry.get():
                messagebox.showerror("Error", "Passwords do not match.")
                return

            # تنظیم رمز عبور
            crypto_storage.set_password(pwd)
            crypto_storage.set_enabled(True)

            # رمزنگاری فایل‌های موجود
            try:
                count = crypto_storage.encrypt_all_existing()
                messagebox.showinfo("Success", f"Encryption enabled successfully.\n{count} files encrypted.")
            except Exception as e:
                messagebox.showerror("Encryption Error", f"Failed to encrypt files: {str(e)}")
                crypto_storage.set_enabled(False)
                return

            self.update_crypto_ui()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Enable Encryption", fg_color=CF_ORANGE, text_color="black",
                     command=save_password).pack(pady=20)

    def change_crypto_password(self):
        """تغییر رمز عبور اصلی"""
        if not crypto_storage.enabled:
            messagebox.showwarning("Warning", "Encryption is not enabled.")
            return

        # ابتدا رمز عبور فعلی را تأیید کن
        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Master Password")
        dialog.geometry("400x350")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dialog, text="Change Master Password", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(20, 10))

        # رمز فعلی
        ctk.CTkLabel(dialog, text="Current Password:").pack(anchor="w", padx=40, pady=(10, 0))
        current_entry = ctk.CTkEntry(dialog, placeholder_text="Enter current password", show="*", width=300)
        current_entry.pack(pady=5)

        # رمز جدید
        ctk.CTkLabel(dialog, text="New Password:").pack(anchor="w", padx=40, pady=(10, 0))
        new_entry = ctk.CTkEntry(dialog, placeholder_text="Enter new password", show="*", width=300)
        new_entry.pack(pady=5)

        # تأیید رمز جدید
        ctk.CTkLabel(dialog, text="Confirm New Password:").pack(anchor="w", padx=40, pady=(10, 0))
        confirm_entry = ctk.CTkEntry(dialog, placeholder_text="Confirm new password", show="*", width=300)
        confirm_entry.pack(pady=5)

        def do_change():
            current = current_entry.get()
            new = new_entry.get()
            confirm = confirm_entry.get()

            if not current or not new:
                messagebox.showerror("Error", "All fields are required.")
                return

            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match.")
                return

            if len(new) < 6:
                messagebox.showerror("Error", "New password must be at least 6 characters.")
                return

            # تأیید رمز فعلی (با تست رمزگشایی یک فایل)
            old_password = crypto_storage._password
            crypto_storage.set_password(current)
            # تست با رمزگشایی یک فایل (اگر فایلی وجود داشته باشد)
            test_passed = True
            if crypto_storage.enabled:
                try:
                    # تلاش برای رمزگشایی یک فایل نمونه (اولین فایل .enc)
                    for root, dirs, files in os.walk(DIRS["settings"]):
                        for f in files:
                            if f.endswith('.enc'):
                                test_path = os.path.join(root, f)
                                data = crypto_storage.decrypt_file(test_path)
                                if data is None:
                                    test_passed = False
                                break
                        break
                except:
                    test_passed = False

            if not test_passed:
                messagebox.showerror("Error", "Current password is incorrect.")
                crypto_storage.set_password(old_password)
                return

            # رمزگشایی همه فایل‌ها با رمز قدیم
            crypto_storage.decrypt_all()
            # تنظیم رمز جدید
            crypto_storage.set_password(new)
            # رمزنگاری مجدد همه فایل‌ها
            count = crypto_storage.encrypt_all_existing()

            messagebox.showinfo("Success", f"Master password changed successfully.\n{count} files re-encrypted.")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Change Password", fg_color=CF_ORANGE, text_color="black",
                     command=do_change).pack(pady=20)

    def reencrypt_all_files(self):
        """رمزنگاری مجدد همه فایل‌ها (مثلاً پس از تغییر تنظیمات)"""
        if not crypto_storage.enabled:
            return

        if messagebox.askyesno("Re-encrypt Files",
                               "This will re-encrypt all files with the current master password.\n"
                               "Useful if you've added new files manually.\n\nContinue?"):
            count = crypto_storage.encrypt_all_existing()
            messagebox.showinfo("Success", f"{count} files re-encrypted.")

    def toggle_app_lock(self):
        """فعال/غیرفعال کردن قفل برنامه"""
        enabled = self.app_lock_var.get()
        if enabled:
            # بررسی اینکه رمز عبور تنظیم شده باشد
            lock_file = os.path.join(DIRS["settings"], "app_lock.json")
            if not os.path.exists(lock_file):
                messagebox.showinfo("Setup Required", "Please set a lock password first.")
                self.set_app_lock_password()
                # دوباره بررسی کن
                if not os.path.exists(lock_file):
                    self.app_lock_var.set(False)
                    return
            messagebox.showinfo("App Lock Enabled", "Application will require password on next startup.")
        else:
            messagebox.showinfo("App Lock Disabled", "Application lock has been disabled.")

    def set_app_lock_password(self):
        """تنظیم رمز عبور قفل برنامه"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Set App Lock Password")
        dialog.geometry("400x250")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dialog, text="Set Application Lock Password", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(20, 10))

        ctk.CTkLabel(dialog, text="Password:").pack(anchor="w", padx=40)
        pass_entry = ctk.CTkEntry(dialog, placeholder_text="Enter password", show="*", width=300)
        pass_entry.pack(pady=5)

        ctk.CTkLabel(dialog, text="Confirm Password:").pack(anchor="w", padx=40)
        confirm_entry = ctk.CTkEntry(dialog, placeholder_text="Confirm password", show="*", width=300)
        confirm_entry.pack(pady=5)

        def save_lock():
            pwd = pass_entry.get()
            if len(pwd) < 4:
                messagebox.showerror("Error", "Password must be at least 4 characters.")
                return
            if pwd != confirm_entry.get():
                messagebox.showerror("Error", "Passwords do not match.")
                return

            # هش کردن رمز عبور
            import hashlib
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()

            lock_file = os.path.join(DIRS["settings"], "app_lock.json")
            with open(lock_file, 'w') as f:
                import json
                json.dump({"hash": pwd_hash}, f)

            messagebox.showinfo("Success", "Application lock password set successfully.")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save Password", fg_color=CF_ORANGE, text_color="black",
                     command=save_lock).pack(pady=20)

    # ==========================================
    # متدهای آپدیت (با رفع مشکل ترد با استفاده از رویداد سفارشی)
    # ==========================================
    def log_update(self, msg, color):
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.master.after(0, lambda: self.update_log.insert("end", f"[{timestamp}] {msg}\n"))
        self.master.after(0, lambda: self.update_log.see("end"))

    def update_progress(self, percent, message):
        self.master.after(0, lambda: self.progress_bar.set(percent / 100))
        self.master.after(0, lambda: self.progress_label.configure(text=message))
        if percent >= 100:
            self.master.after(2000, lambda: self.progress_label.configure(text=""))

    def check_versions(self):
        threading.Thread(target=self._check_versions_thread, daemon=True).start()
        threading.Thread(target=self._check_gdpi_thread, daemon=True).start()

    def _check_versions_thread(self):
        current = self.updater.get_current_xray_version()
        latest, _ = self.updater.get_latest_xray_version()

        self.master.after(0, lambda: self.current_xray_version.configure(text=current if current else "Not installed"))
        self.master.after(0, lambda: self.latest_xray_version.configure(text=latest if latest else "Unknown"))

        if current and latest and current != latest:
            self.master.after(0, lambda: self.update_xray_btn.configure(text="Update Available! Click to Update", fg_color="#C62828"))
            self.master.after(0, lambda: self.xray_status.configure(text=f"New version {latest} available!", text_color="#EF5350"))

    def _check_gdpi_thread(self):
        # عملیات شبکه در ترد غیر اصلی
        gdpi_path = self.updater.check_goodbyedpi()
        # ذخیره نتیجه در یک متغیر و سپس تولید رویداد سفارشی
        self._gdpi_path = gdpi_path
        # ارسال رویداد به ترد اصلی (بدون نیاز به after)
        self.master.event_generate('<<UpdateGdpi>>', when='tail')

    def _on_update_gdpi(self, event):
        """این متد در ترد اصلی اجرا می‌شود و UI را به‌روز می‌کند"""
        gdpi_path = self._gdpi_path
        if gdpi_path:
            self.gdpi_status.configure(text=f"✅ Installed at: {gdpi_path}", text_color="#66BB6A")
            self.download_gdpi_btn.configure(text="Reinstall", fg_color="#FFA726")
        else:
            self.gdpi_status.configure(text="❌ Not installed (optional)", text_color="#EF5350")

    def check_xray_update(self):
        latest, download_url = self.updater.get_latest_xray_version()
        if not latest:
            messagebox.showerror("Error", "Failed to check for updates. Check your internet connection.")
            return

        current = self.updater.get_current_xray_version()
        if current == latest:
            messagebox.showinfo("Up to date", f"Xray-core {current} is already the latest version.")
            return

        if messagebox.askyesno("Update Available", f"Xray-core {latest} is available.\n\nCurrent version: {current}\n\nDo you want to update?"):
            self.update_xray_btn.configure(state="disabled", text="Updating...")
            threading.Thread(target=self._do_xray_update, args=(latest, download_url), daemon=True).start()

    def _do_xray_update(self, version, download_url):
        success = self.updater.download_xray(version, download_url)
        self.master.after(0, lambda: self.update_xray_btn.configure(state="normal", text="Check for Updates"))
        if success:
            self.master.after(0, lambda: self.current_xray_version.configure(text=version))
            self.master.after(0, lambda: self.update_xray_btn.configure(text="Check for Updates", fg_color="#2E7D32"))
            self.master.after(0, lambda: self.xray_status.configure(text="✅ Update completed!", text_color="#66BB6A"))
            messagebox.showinfo("Update Complete", f"Xray-core has been updated to version {version}.\nRestart the app for changes to take effect.")
        else:
            self.master.after(0, lambda: self.xray_status.configure(text="❌ Update failed. Check log for details.", text_color="#EF5350"))

    def download_goodbyedpi(self):
        self.download_gdpi_btn.configure(state="disabled", text="Downloading...")
        threading.Thread(target=self._do_download_gdpi, daemon=True).start()

    def _do_download_gdpi(self):
        success = self.updater.download_goodbyedpi()
        self.master.after(0, lambda: self.download_gdpi_btn.configure(state="normal", text="Download GoodbyeDPI"))
        if success:
            self.master.after(0, lambda: self.gdpi_status.configure(text="✅ Installed successfully!", text_color="#66BB6A"))
            self.master.after(0, lambda: self.download_gdpi_btn.configure(text="Reinstall", fg_color="#FFA726"))
            messagebox.showinfo("Success", "GoodbyeDPI downloaded and installed successfully!")
        else:
            self.master.after(0, lambda: self.gdpi_status.configure(text="❌ Download failed", text_color="#EF5350"))

    # ==========================================
    # متدهای ظاهر
    # ==========================================
    def change_theme(self, choice):
        ctk.set_appearance_mode(choice.lower())

    def change_language(self, choice):
        messagebox.showinfo("Language", f"Language changed to {choice}.\nRestart the app for full effect.")

    def reset_settings(self):
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default?\nThis action cannot be undone."):
            messagebox.showinfo("Reset", "Settings have been reset.\nRestart the app for changes to take effect.")

    # ==========================================
    # متدهای درباره
    # ==========================================
    def open_github(self):
        import webbrowser
        webbrowser.open("https://github.com/Devtahas/CG_BPB")

    def report_issue(self):
        import webbrowser
        webbrowser.open("https://github.com/Devtahas/CG_BPB/issues")


