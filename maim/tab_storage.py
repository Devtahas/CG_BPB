# tab_storage.py
import customtkinter as ctk
from tkinter import messagebox
import os
import subprocess
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, DIRS, BASE_DIR

class StorageFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.target_dir = BASE_DIR
        self.configs_dir = DIRS["configs"]
        self.subs_dir = DIRS["subs"]

        # Title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        
        ctk.CTkLabel(header_frame, text="💾 Storage & Outputs", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)
        ctk.CTkButton(header_frame, text="🔄 Refresh Files", fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=self.refresh_data).pack(side="right", padx=40)

        # Content Frame
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=40, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure((0, 1), weight=1)

        # --- Section 1: JSON Configs ---
        cfg_box = ctk.CTkFrame(content_frame, fg_color=BG_PANEL, corner_radius=15)
        cfg_box.grid(row=0, column=0, padx=10, sticky="nsew")
        
        ctk.CTkLabel(cfg_box, text="⚙️ JSON Configs", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(20, 10))
        self.lbl_cfg_count = ctk.CTkLabel(cfg_box, text="Total Files: 0", font=ctk.CTkFont(size=14))
        self.lbl_cfg_count.pack(pady=5)
        
        ctk.CTkButton(cfg_box, text="📂 Open Configs Folder", fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), command=lambda: self.open_folder(self.configs_dir)).pack(pady=20, padx=20, fill="x")

        # --- Section 2: Subscription Link ---
        sub_box = ctk.CTkFrame(content_frame, fg_color=BG_PANEL, corner_radius=15)
        sub_box.grid(row=0, column=1, padx=10, sticky="nsew")
        
        ctk.CTkLabel(sub_box, text="🔗 Subscription Link", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(20, 10))
        
        self.sub_textbox = ctk.CTkTextbox(sub_box, height=80, font=ctk.CTkFont(family="Consolas", size=10), fg_color="#121212", border_color="gray30", border_width=1)
        self.sub_textbox.pack(padx=20, pady=5, fill="x")
        
        btn_sub_frame = ctk.CTkFrame(sub_box, fg_color="transparent")
        btn_sub_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkButton(btn_sub_frame, text="📋 Copy Sub", fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold"), command=self.copy_sub).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(btn_sub_frame, text="📂 Open Sub Folder", fg_color="#1565C0", hover_color="#0D47A1", font=ctk.CTkFont(weight="bold"), command=lambda: self.open_folder(self.subs_dir)).pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Initial Load
        self.refresh_data()

    def refresh_data(self):
        # Update Configs Count
        if os.path.exists(self.configs_dir):
            count = len([f for f in os.listdir(self.configs_dir) if f.endswith('.json')])
            self.lbl_cfg_count.configure(text=f"Total Configs Saved: {count}")
        else:
            self.lbl_cfg_count.configure(text="Total Configs Saved: 0")

        # Update Sub Textbox
        self.sub_textbox.delete("1.0", "end")
        sub_file = os.path.join(self.subs_dir, "sub.txt")
        if os.path.exists(sub_file):
            try:
                with open(sub_file, "r") as f:
                    content = f.read()
                    self.sub_textbox.insert("1.0", content)
            except:
                self.sub_textbox.insert("1.0", "Error reading sub.txt")
        else:
            self.sub_textbox.insert("1.0", "No subscription generated yet.")

    def copy_sub(self):
        content = self.sub_textbox.get("1.0", "end-1c").strip()
        if content and content != "No subscription generated yet.":
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Success", "Subscription link copied to clipboard!\nYou can now paste it in Hiddify, v2rayN, etc.")
        else:
            messagebox.showerror("Error", "No sub link to copy.")

    def open_folder(self, path):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        # Windows specific folder opener
        os.startfile(path)