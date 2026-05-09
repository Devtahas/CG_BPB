# tab_storage.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from config import CF_ORANGE, BG_PANEL, DIRS, BASE_DIR, storage_crypto
from tabs.setting.asset_manager import AssetManager

class StorageFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        self.asset_manager = kwargs.pop('asset_manager', None)
        if self.asset_manager is None:
            self.asset_manager = AssetManager()

        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.target_dir = BASE_DIR
        self.configs_dir = DIRS["configs"]
        self.subs_dir = DIRS["subs"]

        self.setup_ui()

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="💾 Storage & Assets", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        # Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # تب Storage Path
        self.tab_storage = self.tabview.add("📁 Storage Path")
        self.setup_storage_tab_ui(self.tab_storage)

        # تب IP & DNS Assets
        self.tab_assets = self.tabview.add("🗂️ IP & DNS Assets")
        self.setup_asset_tab_ui(self.tab_assets)

    # ===================== تب مسیر =====================
    def setup_storage_tab_ui(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        path_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        path_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(path_frame, text="📁 Storage Location", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(15, 5))
        ctk.CTkLabel(path_frame, text="All configuration files, subscriptions, and settings are stored here.",
                    text_color="gray").pack()

        current_path_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        current_path_frame.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(current_path_frame, text="Current Path:", font=ctk.CTkFont(weight="bold"), width=100).pack(side="left")
        self.current_path_label = ctk.CTkLabel(current_path_frame, text=BASE_DIR, text_color="#29B6F6", wraplength=400)
        self.current_path_label.pack(side="left", padx=10)

        btn_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="📂 Change Location", fg_color=CF_ORANGE, text_color="black",
                     command=self.change_storage_path).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Reset to Default", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.reset_storage_path_to_default).pack(side="left", padx=5)

        info_text = """
        📌 Note:
        • Changing the storage location will NOT move existing files automatically.
        • You may manually copy the contents from the old location to the new one if needed.
        • The application will create necessary subfolders in the new location.
        • A restart is recommended after changing the storage path.
        """
        ctk.CTkLabel(path_frame, text=info_text, justify="left", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 15))

    # ===================== تب مدیریت منابع =====================
    def setup_asset_tab_ui(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # --- IP Range ---
        ip_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ip_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(ip_frame, text="🌐 IP Range Lists", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(15, 10))

        select_frame = ctk.CTkFrame(ip_frame, fg_color="transparent")
        select_frame.pack(fill="x", padx=20, pady=5)
        self.ip_list_var = ctk.StringVar(value="cloudflare")
        ctk.CTkLabel(select_frame, text="List:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        # ★ اصلاح: اضافه شدن "fastly" به لیست انتخاب
        self.ip_list_combo = ctk.CTkComboBox(select_frame, values=["cloudflare", "datacenter", "fastly"],
                                             variable=self.ip_list_var, command=self.display_ip_list)
        self.ip_list_combo.pack(side="left", padx=10)

        self.ip_textbox = ctk.CTkTextbox(ip_frame, height=200, font=ctk.CTkFont(size=11))
        self.ip_textbox.pack(fill="x", padx=20, pady=5)

        ip_btn_frame = ctk.CTkFrame(ip_frame, fg_color="transparent")
        ip_btn_frame.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkButton(ip_btn_frame, text="💾 Save", fg_color=CF_ORANGE, text_color="black", command=self.save_ip_list).pack(side="left", padx=5)
        ctk.CTkButton(ip_btn_frame, text="➕ Add Single", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.add_ip_dialog).pack(side="left", padx=5)

        # --- DNS ---
        dns_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        dns_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(dns_frame, text="📡 DNS Server List", font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#29B6F6").pack(pady=(15, 10))

        self.dns_textbox = ctk.CTkTextbox(dns_frame, height=200, font=ctk.CTkFont(size=11))
        self.dns_textbox.pack(fill="x", padx=20, pady=5)

        dns_btn_frame = ctk.CTkFrame(dns_frame, fg_color="transparent")
        dns_btn_frame.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkButton(dns_btn_frame, text="💾 Save", fg_color="#29B6F6", text_color="black", command=self.save_dns_list).pack(side="left", padx=5)
        ctk.CTkButton(dns_btn_frame, text="➕ Add", fg_color="transparent", border_width=1,
                     border_color="#29B6F6", text_color="#29B6F6", command=self.add_dns_dialog).pack(side="left", padx=5)

        self.display_ip_list()
        self.display_dns_list()

    # ===================== IP helpers =====================
    def display_ip_list(self, *args):
        list_name = self.ip_list_var.get()
        ips = self.asset_manager.get_ip_list(list_name)
        self.ip_textbox.delete("1.0", "end")
        self.ip_textbox.insert("1.0", "\n".join(ips))

    def save_ip_list(self):
        list_name = self.ip_list_var.get()
        content = self.ip_textbox.get("1.0", "end").strip()
        new_list = [ip for ip in content.splitlines() if ip.strip()]
        self.asset_manager.update_ip_list(list_name, new_list)
        messagebox.showinfo("Success", f"IP list '{list_name}' saved successfully!")

    def add_ip_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter IP or CIDR:", title="Add IP")
        ip = dialog.get_input()
        if ip:
            list_name = self.ip_list_var.get()
            self.asset_manager.add_ip(list_name, ip.strip())
            self.display_ip_list()

    # ===================== DNS helpers =====================
    def display_dns_list(self):
        dns_list = self.asset_manager.get_dns_list()
        self.dns_textbox.delete("1.0", "end")
        self.dns_textbox.insert("1.0", "\n".join(dns_list))

    def save_dns_list(self):
        content = self.dns_textbox.get("1.0", "end").strip()
        new_list = [dns for dns in content.splitlines() if dns.strip()]
        self.asset_manager.update_dns_list(new_list)
        messagebox.showinfo("Success", "DNS list saved successfully!")

    def add_dns_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter DNS IP:", title="Add DNS")
        dns = dialog.get_input()
        if dns:
            self.asset_manager.add_dns(dns.strip())
            self.display_dns_list()

    # ===================== Storage Path helpers =====================
    def change_storage_path(self):
        from config import save_storage_path, update_dirs
        new_path = filedialog.askdirectory(title="Select New Storage Location", initialdir=BASE_DIR)
        if not new_path:
            return
        if save_storage_path(new_path):
            update_dirs(new_path)
            from config import BASE_DIR as updated_base
            self.current_path_label.configure(text=updated_base)
            messagebox.showinfo("Success", f"Storage location changed to:\n{new_path}\n\nPlease restart the application.")
        else:
            messagebox.showerror("Error", "Failed to save new storage path.")

    def reset_storage_path_to_default(self):
        from config import reset_storage_path, update_dirs
        if reset_storage_path():
            update_dirs(BASE_DIR)
            self.current_path_label.configure(text=BASE_DIR)
            messagebox.showinfo("Success", f"Storage location reset to default:\n{BASE_DIR}\n\nPlease restart the application.")
        else:
            messagebox.showerror("Error", "Failed to reset storage path.")

    def refresh_data(self):
        count = 0
        if os.path.exists(self.configs_dir):
            seen = set()
            for f in os.listdir(self.configs_dir):
                if f.endswith('.json'):
                    base = f[:-5]
                    seen.add(base)
                elif f.endswith('.json.enc'):
                    base = f[:-9]
                    seen.add(base)
            count = len(seen)
        if hasattr(self, 'lbl_cfg_count'):
            self.lbl_cfg_count.configure(text=f"Total Configs Saved: {count}")

        sub_file = os.path.join(self.subs_dir, "sub.txt")
        if hasattr(self, 'sub_textbox'):
            self.sub_textbox.delete("1.0", "end")
            try:
                with storage_crypto.safe_open(sub_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.sub_textbox.insert("1.0", content)
            except:
                if os.path.exists(sub_file):
                    try:
                        with open(sub_file, 'r', encoding='utf-8') as f:
                            self.sub_textbox.insert("1.0", f.read())
                    except:
                        self.sub_textbox.insert("1.0", "Error reading subscription file.")
                else:
                    self.sub_textbox.insert("1.0", "No subscription generated yet.")
