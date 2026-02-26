# tab_tools.py
import customtkinter as ctk
from tkinter import messagebox
import uuid
import string
import secrets
import json
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

class ToolsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="🛠️ Tools & Generators", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, pady=(30, 10))

        # ساخت تب‌ویو برای جدا کردن بخش‌ها
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE, segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, padx=40, pady=10, sticky="nsew")

        self.tab_gen = self.tabview.add("Generators")
        self.tab_ext = self.tabview.add("Config Extractor")

        self.setup_generator_tab()
        self.setup_extractor_tab()

    # ==========================================
    # بخش اول: تب ساخت UUID و پسورد
    # ==========================================
    def setup_generator_tab(self):
        self.tab_gen.grid_columnconfigure(0, weight=1)

        # UUID Section
        uuid_frame = ctk.CTkFrame(self.tab_gen, fg_color=BG_PANEL, corner_radius=15)
        uuid_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.lbl_uuid = ctk.CTkEntry(uuid_frame, width=350, font=ctk.CTkFont(family="Consolas", size=14), border_width=1, border_color="gray30")
        self.lbl_uuid.pack(side="left", padx=20, pady=20)
        
        ctk.CTkButton(uuid_frame, text="Generate UUID", fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.generate_uuid).pack(side="left", padx=10)
        ctk.CTkButton(uuid_frame, text="Copy", width=70, fg_color="transparent", border_width=2, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=lambda: self.copy_to_clip(self.lbl_uuid.get())).pack(side="left", padx=10)

        # Password Section
        pass_frame = ctk.CTkFrame(self.tab_gen, fg_color=BG_PANEL, corner_radius=15)
        pass_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.lbl_pass = ctk.CTkEntry(pass_frame, width=350, font=ctk.CTkFont(family="Consolas", size=14), border_width=1, border_color="gray30")
        self.lbl_pass.pack(side="left", padx=20, pady=20)

        ctk.CTkButton(pass_frame, text="Secure Pass", fg_color=CF_ORANGE, hover_color=CF_ORANGE_HOVER, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.generate_pass).pack(side="left", padx=10)
        ctk.CTkButton(pass_frame, text="Copy", width=70, fg_color="transparent", border_width=2, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=lambda: self.copy_to_clip(self.lbl_pass.get())).pack(side="left", padx=10)

        self.generate_uuid()
        self.generate_pass()

    def generate_uuid(self):
        self.lbl_uuid.delete(0, "end")
        self.lbl_uuid.insert(0, str(uuid.uuid4()))

    def generate_pass(self):
        chars = string.ascii_letters + string.digits + "@#%&*"
        secure_pass = ''.join(secrets.choice(chars) for _ in range(16))
        self.lbl_pass.delete(0, "end")
        self.lbl_pass.insert(0, secure_pass)

    def copy_to_clip(self, text):
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Success", "Copied to clipboard!")

    # ==========================================
    # بخش دوم: تب استخراج اطلاعات از JSON
    # ==========================================
    def setup_extractor_tab(self):
        self.tab_ext.grid_columnconfigure(0, weight=1)

        # Header Frame for Label and Action Buttons
        header_frame = ctk.CTkFrame(self.tab_ext, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(10, 5), sticky="ew", padx=20)
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Paste raw JSON config below to extract UUID, Host, and Path:", text_color="gray").grid(row=0, column=0, sticky="w")
        
        # دکمه‌های جدید اضافه شده برای پیست کردن و پاک کردن متن
        ctk.CTkButton(header_frame, text="📋 Paste", width=70, fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), command=self.paste_json).grid(row=0, column=1, padx=5)
        ctk.CTkButton(header_frame, text="🗑️ Clear", width=70, fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(weight="bold"), command=self.clear_json).grid(row=0, column=2, padx=(0,0))

        # Input Box
        self.json_textbox = ctk.CTkTextbox(self.tab_ext, height=180, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#121212", border_color="gray30", border_width=1)
        self.json_textbox.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # Action Button
        ctk.CTkButton(self.tab_ext, text="🔍 EXTRACT DATA", fg_color=CF_ORANGE, text_color="black", hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold"), command=self.extract_json).grid(row=2, column=0, pady=15)

        # Results Frame
        res_frame = ctk.CTkFrame(self.tab_ext, fg_color=BG_PANEL, corner_radius=15)
        res_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        res_frame.grid_columnconfigure(1, weight=1)

        # Result Rows (UUID, Host, Path)
        self.ext_uuid = self.create_result_row(res_frame, "UUID:", 0)
        self.ext_host = self.create_result_row(res_frame, "Host:", 1)
        self.ext_path = self.create_result_row(res_frame, "Path:", 2)

    def paste_json(self):
        try:
            # دریافت متن از حافظه کلیپ‌بورد ویندوز
            clipboard_text = self.clipboard_get()
            self.json_textbox.delete("1.0", "end")
            self.json_textbox.insert("1.0", clipboard_text)
        except Exception:
            messagebox.showerror("Error", "Clipboard is empty or contains invalid data!")

    def clear_json(self):
        self.json_textbox.delete("1.0", "end")
        self.ext_uuid.delete(0, "end")
        self.ext_host.delete(0, "end")
        self.ext_path.delete(0, "end")

    def create_result_row(self, parent, label_text, row_idx):
        ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(weight="bold", size=13), text_color=CF_ORANGE).grid(row=row_idx, column=0, padx=(20, 10), pady=10, sticky="w")
        
        entry = ctk.CTkEntry(parent, font=ctk.CTkFont(family="Consolas", size=12), border_width=1, border_color="gray30")
        entry.grid(row=row_idx, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(parent, text="Copy", width=60, fg_color="transparent", border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", command=lambda e=entry: self.copy_to_clip(e.get())).grid(row=row_idx, column=2, padx=(10, 20), pady=10)
        
        return entry

    def extract_json(self):
        raw_data = self.json_textbox.get("1.0", "end").strip()
        if not raw_data:
            messagebox.showwarning("Warning", "Please paste the JSON configuration first!")
            return

        try:
            config = json.loads(raw_data)
            
            found_uuid = ""
            found_host = ""
            found_path = ""
            
            # جستجو در بخش outbounds
            outbounds = config.get("outbounds",[])
            for out in outbounds:
                if out.get("protocol") == "vless":
                    # پیدا کردن UUID
                    try:
                        found_uuid = out["settings"]["vnext"][0]["users"][0]["id"]
                    except (KeyError, IndexError):
                        pass
                    
                    # پیدا کردن Host و Path بر اساس نوع شبکه
                    stream = out.get("streamSettings", {})
                    network = stream.get("network", "")
                    
                    if network == "ws":
                        ws_settings = stream.get("wsSettings", {})
                        found_host = ws_settings.get("host", "")
                        found_path = ws_settings.get("path", "")
                        
                    elif network == "grpc":
                        grpc_settings = stream.get("grpcSettings", {})
                        found_path = grpc_settings.get("serviceName", "")
                        
                    elif network == "tcp":
                        tcp_settings = stream.get("tcpSettings", {})
                        try:
                            found_host = tcp_settings["header"]["request"]["headers"]["Host"][0]
                            found_path = tcp_settings["header"]["request"]["path"][0]
                        except (KeyError, IndexError):
                            pass
                    
                    break 
            
            if not found_uuid and not found_host and not found_path:
                messagebox.showerror("Error", "Could not find valid VLESS data in this configuration.")
                return

            self.ext_uuid.delete(0, "end")
            self.ext_uuid.insert(0, found_uuid)

            self.ext_host.delete(0, "end")
            self.ext_host.insert(0, found_host)

            self.ext_path.delete(0, "end")
            self.ext_path.insert(0, found_path)

        except json.JSONDecodeError:
            messagebox.showerror("Invalid JSON", "The text you pasted is not a valid JSON format.\nPlease check and try again.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")