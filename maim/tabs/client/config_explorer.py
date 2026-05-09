# tabs/client/config_explorer.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import json
import time
import threading
import re
from config import CF_ORANGE, BG_PANEL, DIRS
from tabs.crypto_manager import storage_crypto

class ConfigExplorerTab(ctk.CTkFrame):
    """تب مدیریت پیشرفته فایل‌های کانفیگ JSON"""

    def __init__(self, parent, configs_dir, **kwargs):
        super().__init__(parent, **kwargs)
        self.configs_dir = configs_dir
        self.selected_file = None
        self.check_vars = {}  # نگهداری checkboxها برای حذف گروهی

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=2)

        # ===== نوار بالایی =====
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        ctk.CTkButton(top_frame, text="🔄 Refresh List", fg_color="transparent",
                      border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                      command=self.refresh_file_list).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(top_frame, text="📥 Import JSON", fg_color="transparent",
                      border_width=1, border_color="#29B6F6", text_color="#29B6F6",
                      command=self.import_json_file).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(top_frame, text="🗑️ Delete Selected", fg_color="transparent",
                      border_width=1, border_color="#EF5350", text_color="#EF5350",
                      command=self.delete_selected).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.sort_var = ctk.StringVar(value="Name")
        ctk.CTkComboBox(top_frame, values=["Name", "Date Modified"], variable=self.sort_var,
                        command=self.refresh_file_list, width=130).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(top_frame, text=f"📁 {self.configs_dir}", text_color="gray",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # ===== لیست فایل‌ها (چپ) و پیش‌نمایش/ویرایش (راست) =====
        paned = ctk.CTkFrame(self, fg_color="transparent")
        paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        paned.grid_columnconfigure(0, weight=1)
        paned.grid_columnconfigure(1, weight=3)
        paned.grid_rowconfigure(0, weight=1)

        # --- لیست فایل‌ها ---
        list_frame = ctk.CTkFrame(paned, fg_color=BG_PANEL, corner_radius=10)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(list_frame, text="Config Files", font=ctk.CTkFont(weight="bold"),
                     text_color=CF_ORANGE).grid(row=0, column=0, padx=10, pady=(10, 5))
        self.file_scroll = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.file_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # --- پیش‌نمایش و ویرایش سریع ---
        edit_frame = ctk.CTkFrame(paned, fg_color=BG_PANEL, corner_radius=10)
        edit_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        edit_frame.grid_columnconfigure(0, weight=1)
        edit_frame.grid_rowconfigure(0, weight=0)
        edit_frame.grid_rowconfigure(1, weight=1)
        edit_frame.grid_rowconfigure(2, weight=0)

        # هدر بخش ویرایش
        ctk.CTkLabel(edit_frame, text="Preview & Quick Edit", font=ctk.CTkFont(weight="bold"),
                     text_color="#29B6F6").grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        # ناحیه نمایش JSON
        self.json_textbox = ctk.CTkTextbox(edit_frame, font=ctk.CTkFont(family="Consolas", size=12),
                                           fg_color="#121212", border_color="gray30", border_width=1)
        self.json_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.json_textbox.bind("<KeyRelease>", self._on_json_edit)

        # ورودی‌های ویرایش سریع
        quick_edit = ctk.CTkFrame(edit_frame, fg_color="transparent")
        quick_edit.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        quick_edit.grid_columnconfigure((0,1,2), weight=1)

        self.entry_uuid = ctk.CTkEntry(quick_edit, placeholder_text="UUID")
        self.entry_uuid.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.entry_host = ctk.CTkEntry(quick_edit, placeholder_text="Host")
        self.entry_host.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.entry_path = ctk.CTkEntry(quick_edit, placeholder_text="Path")
        self.entry_path.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(quick_edit, text="💾 Save Quick Edit", fg_color=CF_ORANGE, text_color="black",
                      command=self.save_quick_edit).grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # ===== نوار پایین: عملیات روی فایل =====
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        bottom_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        ctk.CTkButton(bottom_frame, text="📝 Rename", fg_color="transparent",
                      border_width=1, border_color="#AB47BC", text_color="#AB47BC",
                      command=self.rename_file).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(bottom_frame, text="📋 Copy to Clipboard", fg_color="transparent",
                      border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                      command=self.copy_to_clipboard).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(bottom_frame, text="🗑️ Delete This", fg_color="transparent",
                      border_width=1, border_color="#EF5350", text_color="#EF5350",
                      command=self.delete_current).grid(row=0, column=2, padx=5, sticky="ew")
        ctk.CTkButton(bottom_frame, text="📂 Open Folder", fg_color="transparent",
                      border_width=1, border_color="#66BB6A", text_color="#66BB6A",
                      command=lambda: os.startfile(self.configs_dir)).grid(row=0, column=3, padx=5, sticky="ew")
        ctk.CTkButton(bottom_frame, text="🔄 Load Full JSON", fg_color="transparent",
                      border_width=1, border_color="#29B6F6", text_color="#29B6F6",
                      command=self.load_selected_file).grid(row=0, column=4, padx=5, sticky="ew")

        # بارگذاری اولیه لیست
        self.refresh_file_list()

    # ========================
    # مدیریت لیست فایل‌ها
    # ========================
    def refresh_file_list(self, choice=None):
        for w in self.file_scroll.winfo_children():
            w.destroy()
        self.check_vars.clear()

        if not os.path.exists(self.configs_dir):
            return

        files = [f for f in os.listdir(self.configs_dir) if f.endswith('.json')]
        if self.sort_var.get() == "Date Modified":
            files.sort(key=lambda f: os.path.getmtime(os.path.join(self.configs_dir, f)), reverse=True)
        else:
            files.sort()

        for fname in files:
            full_path = os.path.join(self.configs_dir, fname)
            row = ctk.CTkFrame(self.file_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            var = ctk.BooleanVar(value=False)
            self.check_vars[fname] = var

            ctk.CTkCheckBox(row, text="", variable=var, width=20).pack(side="left", padx=(5, 0))
            btn = ctk.CTkButton(row, text=fname, anchor="w", fg_color="transparent",
                               text_color="gray90", hover_color="#332015",
                               command=lambda p=full_path, n=fname: self.select_file(p, n))
            btn.pack(side="left", fill="x", expand=True)

    def select_file(self, path, name):
        self.selected_file = path
        self.json_textbox.delete("1.0", "end")
        try:
            data = storage_crypto.load_json(path)
            if data is None and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            if data:
                # نمایش زیبا
                pretty = json.dumps(data, indent=2, ensure_ascii=False)
                self.json_textbox.insert("1.0", pretty)
                # استخراج UUID, Host, Path برای Quick Edit
                outbound = data.get("outbounds", [{}])[0]
                if outbound.get("protocol") == "vless":
                    vnext = outbound.get("settings", {}).get("vnext", [{}])[0]
                    uuid = vnext.get("users", [{}])[0].get("id", "")
                    stream = outbound.get("streamSettings", {})
                    ws_settings = stream.get("wsSettings", {})
                    host = ws_settings.get("host", "")
                    path_val = ws_settings.get("path", "")
                else:
                    uuid = host = path_val = ""
                self.entry_uuid.delete(0, "end")
                self.entry_uuid.insert(0, uuid)
                self.entry_host.delete(0, "end")
                self.entry_host.insert(0, host)
                self.entry_path.delete(0, "end")
                self.entry_path.insert(0, path_val)
            else:
                self.json_textbox.insert("1.0", "{}")
        except Exception as e:
            self.json_textbox.insert("1.0", f"Error loading file:\n{str(e)}")

    def load_selected_file(self):
        if self.selected_file:
            self.select_file(self.selected_file, os.path.basename(self.selected_file))

    # ========================
    # Quick Edit
    # ========================
    def _on_json_edit(self, event=None):
        """در صورت تغییر JSON توسط کاربر، دکمه Load Full JSON ظاهر شود"""
        pass

    def save_quick_edit(self):
        if not self.selected_file:
            messagebox.showerror("Error", "No file selected.")
            return
        uuid = self.entry_uuid.get().strip()
        host = self.entry_host.get().strip()
        path = self.entry_path.get().strip()
        if not any([uuid, host, path]):
            messagebox.showinfo("No Change", "No values entered for quick edit.")
            return

        try:
            data = storage_crypto.load_json(self.selected_file)
            if data is None and os.path.exists(self.selected_file):
                with open(self.selected_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            if not data:
                messagebox.showerror("Error", "Could not load JSON data.")
                return

            outbound = data.get("outbounds", [{}])[0]
            if outbound.get("protocol") == "vless":
                vnext = outbound.setdefault("settings", {}).setdefault("vnext", [{}])[0]
                users = vnext.setdefault("users", [{}])[0]
                if uuid:
                    users["id"] = uuid
                stream = outbound.setdefault("streamSettings", {})
                net = stream.get("network", "ws")
                if net == "ws":
                    ws = stream.setdefault("wsSettings", {})
                    if host:
                        ws["host"] = host
                    if path:
                        ws["path"] = path
                elif net == "grpc":
                    grpc = stream.setdefault("grpcSettings", {})
                    if path:
                        grpc["serviceName"] = path.lstrip("/")
                elif net == "tcp":
                    tcp = stream.setdefault("tcpSettings", {})
                    header = tcp.setdefault("header", {})
                    request = header.setdefault("request", {})
                    if host:
                        request.setdefault("headers", {})["Host"] = [host]
                    if path:
                        request["path"] = [path]

                storage_crypto.save_json(self.selected_file, data)
                messagebox.showinfo("Saved", "Quick edit applied successfully.")
                self.load_selected_file()
            else:
                messagebox.showwarning("Not Supported", "Quick edit only works for VLESS configs currently.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    # ========================
    # عملیات فایل
    # ========================
    def import_json_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                dest = os.path.join(self.configs_dir, os.path.basename(file_path))
                storage_crypto.save_json(dest, data)
                self.refresh_file_list()
                messagebox.showinfo("Imported", f"File '{os.path.basename(file_path)}' imported.")
            except Exception as e:
                messagebox.showerror("Error", f"Import failed: {str(e)}")

    def delete_current(self):
        if not self.selected_file:
            messagebox.showerror("Error", "No file selected.")
            return
        if messagebox.askyesno("Confirm", f"Delete '{os.path.basename(self.selected_file)}'?"):
            try:
                os.remove(self.selected_file)
                enc = self.selected_file + '.enc'
                if os.path.exists(enc):
                    os.remove(enc)
                self.selected_file = None
                self.json_textbox.delete("1.0", "end")
                self.refresh_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {str(e)}")

    def delete_selected(self):
        to_delete = [f for f, var in self.check_vars.items() if var.get()]
        if not to_delete:
            messagebox.showwarning("No Selection", "Please check at least one file.")
            return
        if messagebox.askyesno("Confirm", f"Delete {len(to_delete)} selected file(s)?"):
            for fname in to_delete:
                path = os.path.join(self.configs_dir, fname)
                try:
                    os.remove(path)
                    enc = path + '.enc'
                    if os.path.exists(enc):
                        os.remove(enc)
                except Exception:
                    pass
            self.selected_file = None
            self.json_textbox.delete("1.0", "end")
            self.refresh_file_list()

    def rename_file(self):
        if not self.selected_file:
            messagebox.showerror("Error", "No file selected.")
            return
        dialog = ctk.CTkInputDialog(text="New name:", title="Rename Config")
        new_name = dialog.get_input()
        if new_name:
            if not new_name.endswith('.json'):
                new_name += '.json'
            new_path = os.path.join(self.configs_dir, new_name)
            if os.path.exists(new_path):
                messagebox.showerror("Error", "File already exists.")
                return
            try:
                os.rename(self.selected_file, new_path)
                self.refresh_file_list()
                self.selected_file = new_path
                messagebox.showinfo("Renamed", f"File renamed to {new_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Rename failed: {str(e)}")

    def copy_to_clipboard(self):
        content = self.json_textbox.get("1.0", "end-1c").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()
            messagebox.showinfo("Copied", "JSON content copied to clipboard.")
