# tabs/plugins/plugin_ui.py

import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import threading

from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK
from .plugin_manager import PluginManager


class PluginUI(ctk.CTkFrame):
    """تب پلاگین‌ها: مدیریت، نصب و حذف پلاگین‌ها"""

    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # ردیف لیست

        # ★ اگر app_controller از قبل plugin_manager دارد، از همان استفاده کن
        if self.app_controller and hasattr(self.app_controller, 'plugin_manager'):
            self.plugin_manager = self.app_controller.plugin_manager
        else:
            self.plugin_manager = PluginManager()
            if self.app_controller:
                self.app_controller.plugin_manager = self.plugin_manager

        self.setup_ui()
        self.refresh_list()
        # ★ بعد از ساخت UI، همهٔ پلاگین‌های فعال را یک بار بارگذاری می‌کنیم
        self.plugin_manager.load_all_enabled()

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🧩 Plugins", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        # دکمه‌های اصلی
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.btn_import = ctk.CTkButton(action_frame, text="📂 Import from ZIP", fg_color=CF_ORANGE,
                                        hover_color=CF_ORANGE_HOVER, text_color="black",
                                        font=ctk.CTkFont(weight="bold"), command=self.import_plugin_from_zip)
        self.btn_import.pack(side="left", padx=5)

        self.btn_store = ctk.CTkButton(action_frame, text="🌐 Install from Store", fg_color="#1565C0",
                                       hover_color="#0D47A1", text_color="white",
                                       font=ctk.CTkFont(weight="bold"), command=self.open_store_window)
        self.btn_store.pack(side="left", padx=5)

        self.btn_refresh = ctk.CTkButton(action_frame, text="🔄 Refresh", fg_color="transparent",
                                         border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                                         command=self.refresh_list)
        self.btn_refresh.pack(side="right", padx=5)

        # Scrollable Frame برای لیست پلاگین‌ها
        self.plugins_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.plugins_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.plugins_frame.grid_columnconfigure(0, weight=1)

    def refresh_list(self):
        """بازخوانی و نمایش لیست پلاگین‌های نصب شده"""
        for widget in self.plugins_frame.winfo_children():
            widget.destroy()

        plugins = self.plugin_manager.discover_plugins()
        if not plugins:
            ctk.CTkLabel(self.plugins_frame, text="No plugins installed.",
                         text_color="gray", font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        for p in plugins:
            self._create_plugin_card(p)

    def _create_plugin_card(self, plugin_info: dict):
        """ایجاد یک کارت برای یک پلاگین"""
        manifest = plugin_info["manifest"]
        plugin_id = plugin_info["id"]
        is_enabled = plugin_info["enabled"]
        is_loaded = plugin_info["loaded"]

        card = ctk.CTkFrame(self.plugins_frame, fg_color=BG_PANEL, corner_radius=10)
        card.pack(fill="x", padx=5, pady=4)
        card.grid_columnconfigure(1, weight=1)

        # اطلاعات اصلی
        name_label = ctk.CTkLabel(card, text=manifest.get("name", plugin_id),
                                  font=ctk.CTkFont(size=15, weight="bold"))
        name_label.grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")

        version_author = f"v{manifest.get('version', '0.0.0')} by {manifest.get('author', 'Unknown')}"
        info_label = ctk.CTkLabel(card, text=version_author, text_color="gray", font=ctk.CTkFont(size=12))
        info_label.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="w")

        # توضیحات (اگر موجود باشد)
        desc = manifest.get("description", "")
        if desc:
            desc_label = ctk.CTkLabel(card, text=desc, text_color="gray", font=ctk.CTkFont(size=11),
                                      wraplength=400, justify="left")
            desc_label.grid(row=2, column=0, padx=15, pady=(0, 5), sticky="w")

        # وضعیت
        status_text = "🟢 Active" if (is_enabled and is_loaded) else ("🟡 Enabled (inactive)" if is_enabled else "🔴 Disabled")
        status_color = "#66BB6A" if (is_enabled and is_loaded) else ("#FFA726" if is_enabled else "#EF5350")
        status_label = ctk.CTkLabel(card, text=status_text, text_color=status_color, font=ctk.CTkFont(size=12, weight="bold"))
        status_label.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="w")

        # دکمه‌های عملیات (ستون 1)
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=4, padx=10, pady=10, sticky="e")

        # فعال/غیرفعال
        toggle_text = "Disable" if is_enabled else "Enable"
        toggle_color = "#FFA726" if is_enabled else "#2E7D32"
        toggle_hover = "#F57F17" if is_enabled else "#1B5E20"
        btn_toggle = ctk.CTkButton(btn_frame, text=toggle_text, fg_color=toggle_color, hover_color=toggle_hover,
                                   width=80, font=ctk.CTkFont(size=12, weight="bold"),
                                   command=lambda pid=plugin_id, en=is_enabled: self.toggle_plugin(pid, not en))
        btn_toggle.pack(side="left", padx=2)

        # حذف
        btn_delete = ctk.CTkButton(btn_frame, text="🗑️ Delete", fg_color="#C62828", hover_color="#8E0000",
                                   width=80, font=ctk.CTkFont(size=12, weight="bold"),
                                   command=lambda pid=plugin_id: self.delete_plugin(pid))
        btn_delete.pack(side="left", padx=2)

        # اگر پلاگین پنل UI دارد، دکمه "Open" هم اضافه کنیم (اختیاری)
        if is_loaded:
            instance = self.plugin_manager.get_plugin_instance(plugin_id)
            if instance and instance.get_ui_panel is not None:
                btn_open = ctk.CTkButton(btn_frame, text="🔧 Open", fg_color="transparent",
                                         border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                                         width=80, font=ctk.CTkFont(size=12, weight="bold"),
                                         command=lambda pid=plugin_id: self.open_plugin_ui(pid))
                btn_open.pack(side="left", padx=2)

    def toggle_plugin(self, plugin_id: str, enable: bool):
        """فعال/غیرفعال کردن یک پلاگین"""
        self.plugin_manager.set_enabled(plugin_id, enable)
        self.refresh_list()
        # ★ بعد از تغییر وضعیت، باید UI تب‌های مقصد هم بروز شود
        if self.app_controller:
            self.app_controller.after(100, self._refresh_all_tabs)

    def _refresh_all_tabs(self):
        """همهٔ تب‌های اصلی را رفرش می‌کند تا پلاگین‌های جدید/حذف شده اعمال شوند."""
        if not self.app_controller:
            return
        # صدا زدن select_frame_by_name برای رفرش تب‌ها (در صورت نیاز)
        current_frame = None
        for attr in ['tools_frame', 'client_frame', 'dns_frame']:
            if hasattr(self.app_controller, attr):
                frame = getattr(self.app_controller, attr)
                if frame and frame.winfo_ismapped():
                    current_frame = attr
                    break
        if current_frame:
            self.app_controller.select_frame_by_name(current_frame.replace('_frame', ''))

    def delete_plugin(self, plugin_id: str):
        """حذف پلاگین با تأیید"""
        if messagebox.askyesno("Delete Plugin", f"Are you sure you want to delete '{plugin_id}'?\nThis action cannot be undone."):
            if self.plugin_manager.uninstall_plugin(plugin_id):
                self.refresh_list()
                if self.app_controller:
                    self.app_controller.after(100, self._refresh_all_tabs)
            else:
                messagebox.showerror("Error", "Failed to delete plugin.")

    def import_plugin_from_zip(self):
        """انتخاب فایل ZIP و نصب پلاگین از آن"""
        file_path = filedialog.askopenfilename(
            title="Select Plugin ZIP File",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if not file_path:
            return

        self.btn_import.configure(state="disabled", text="Installing...")
        threading.Thread(target=self._do_import_zip, args=(file_path,), daemon=True).start()

    def _do_import_zip(self, file_path):
        plugin_id = self.plugin_manager.install_from_zip(file_path)
        self.after(0, lambda: self._after_import(plugin_id, "ZIP"))

    def open_store_window(self):
        """باز کردن پنجره فروشگاه (دریافت شناسه پلاگین از Worker)"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Plugin Store")
        dialog.geometry("400x200")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text="🌐 Install Plugin from Store",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text="Enter Plugin ID from the marketplace",
                     text_color="gray").pack()

        entry = ctk.CTkEntry(dialog, placeholder_text="e.g., my-cool-plugin", width=250)
        entry.pack(pady=10)

        def install():
            plugin_id = entry.get().strip()
            if not plugin_id:
                messagebox.showerror("Error", "Please enter a Plugin ID.")
                return
            dialog.destroy()
            self._install_from_store(plugin_id)

        ctk.CTkButton(dialog, text="Install", fg_color=CF_ORANGE, text_color="black",
                      command=install).pack(pady=10)

    def _install_from_store(self, store_id: str):
        self.btn_store.configure(state="disabled", text="Downloading...")
        threading.Thread(target=self._do_install_store, args=(store_id,), daemon=True).start()

    def _do_install_store(self, store_id):
        plugin_id = self.plugin_manager.install_from_worker(store_id)
        self.after(0, lambda: self._after_import(plugin_id, "Store"))

    def _after_import(self, plugin_id, source):
        """پاکسازی UI پس از نصب"""
        self.btn_import.configure(state="normal", text="📂 Import from ZIP")
        self.btn_store.configure(state="normal", text="🌐 Install from Store")
        if plugin_id:
            self.refresh_list()
            # ★ بعد از نصب موفق، تب‌های مقصد را رفرش کن
            if self.app_controller:
                self.app_controller.after(100, self._refresh_all_tabs)
            messagebox.showinfo("Success", f"Plugin '{plugin_id}' installed successfully from {source}.")
        else:
            messagebox.showerror("Error", f"Failed to install plugin from {source}. Check logs for details.")

    def open_plugin_ui(self, plugin_id: str):
        """باز کردن پنل اختصاصی پلاگین در یک پنجره جدید"""
        instance = self.plugin_manager.get_plugin_instance(plugin_id)
        if not instance:
            messagebox.showwarning("Not Loaded", "Plugin is not currently loaded.")
            return

        # ایجاد پنجره جدید
        win = ctk.CTkToplevel(self)
        win.title(f"Plugin: {instance.name}")
        win.geometry("500x400")
        win.configure(fg_color=BG_DARK)

        # یک container میانی داخل پنجره
        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True)

        # دریافت پنل پلاگین با والد container
        panel = instance.get_ui_panel(container)
        if panel:
            panel.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            messagebox.showinfo("Plugin UI", "This plugin does not have a visual interface.")
