# tabs/tools/generators.py
import customtkinter as ctk
from tkinter import messagebox
import uuid
import secrets
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL


class GeneratorsTab:
    """تب تولید UUID و پسورد امن"""
    
    def __init__(self, parent, tabview):
        self.parent = parent
        self.tab = tabview.add("Generators")
        self.setup_ui()
        
    def setup_ui(self):
        # ایجاد اسکرول فریم
        scroll = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        scroll.grid_columnconfigure(0, weight=1)
        
        # بخش UUID
        uuid_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        uuid_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        uuid_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(uuid_frame, text="UUID Generator", 
                    font=ctk.CTkFont(weight="bold", size=16), 
                    text_color=CF_ORANGE).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.lbl_uuid = ctk.CTkEntry(uuid_frame, font=ctk.CTkFont(family="Consolas", size=14), 
                                     border_width=1, border_color="gray30")
        self.lbl_uuid.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        btn_frame1 = ctk.CTkFrame(uuid_frame, fg_color="transparent")
        btn_frame1.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        btn_frame1.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(btn_frame1, text="Generate UUID", fg_color=CF_ORANGE, 
                     hover_color=CF_ORANGE_HOVER, text_color="black", 
                     font=ctk.CTkFont(weight="bold"), command=self.generate_uuid).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame1, text="Copy", fg_color="transparent", border_width=2, 
                     border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", 
                     command=lambda: self.copy_to_clip(self.lbl_uuid.get())).grid(row=0, column=1, padx=5, sticky="ew")
        
        # بخش Password
        pass_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        pass_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        pass_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(pass_frame, text="Secure Password Generator", 
                    font=ctk.CTkFont(weight="bold", size=16), 
                    text_color=CF_ORANGE).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.lbl_pass = ctk.CTkEntry(pass_frame, font=ctk.CTkFont(family="Consolas", size=14), 
                                     border_width=1, border_color="gray30")
        self.lbl_pass.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        btn_frame2 = ctk.CTkFrame(pass_frame, fg_color="transparent")
        btn_frame2.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        btn_frame2.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(btn_frame2, text="Generate Password", fg_color=CF_ORANGE, 
                     hover_color=CF_ORANGE_HOVER, text_color="black", 
                     font=ctk.CTkFont(weight="bold"), command=self.generate_pass).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame2, text="Copy", fg_color="transparent", border_width=2, 
                     border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", 
                     command=lambda: self.copy_to_clip(self.lbl_pass.get())).grid(row=0, column=1, padx=5, sticky="ew")
        
        self.generate_uuid()
        self.generate_pass()
        
    def generate_uuid(self):
        self.lbl_uuid.delete(0, "end")
        self.lbl_uuid.insert(0, str(uuid.uuid4()))
        
    def generate_pass(self):
        secure_pass = secrets.token_urlsafe(16)[:16]
        self.lbl_pass.delete(0, "end")
        self.lbl_pass.insert(0, secure_pass)
        
    def copy_to_clip(self, text):
        if text:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
            messagebox.showinfo("Success", "Copied to clipboard!")
