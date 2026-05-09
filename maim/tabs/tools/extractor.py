# tabs/tools/extractor.py
import customtkinter as ctk
from tkinter import messagebox
import json
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL


class ExtractorTab:
    """تب استخراج اطلاعات از کانفیگ JSON"""
    
    def __init__(self, parent, tabview):
        self.parent = parent
        self.tab = tabview.add("Config Extractor")
        self.setup_ui()
        
    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        scroll.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(scroll, text="Extract UUID, Host, and Path from VLESS JSON config", 
                    text_color="gray").grid(row=0, column=0, padx=20, pady=(10, 5), sticky="w")
        
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(btn_frame, text="📋 Paste from Clipboard", fg_color="#2E7D32", 
                     hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), 
                     command=self.paste_json).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="🗑️ Clear All", fg_color="#C62828", 
                     hover_color="#8E0000", font=ctk.CTkFont(weight="bold"), 
                     command=self.clear_json).grid(row=0, column=1, padx=5, sticky="ew")
        
        ctk.CTkLabel(scroll, text="JSON Configuration:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.json_textbox = ctk.CTkTextbox(scroll, height=200, font=ctk.CTkFont(family="Consolas", size=11), 
                                           fg_color="#121212", border_color="gray30", border_width=1)
        self.json_textbox.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        ctk.CTkButton(scroll, text="🔍 EXTRACT DATA", fg_color=CF_ORANGE, text_color="black", 
                     hover_color=CF_ORANGE_HOVER, font=ctk.CTkFont(weight="bold", size=14), 
                     command=self.extract_json).grid(row=4, column=0, pady=15)
        
        res_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        res_frame.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        res_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(res_frame, text="Extracted Results:", font=ctk.CTkFont(weight="bold", size=14), 
                    text_color=CF_ORANGE).grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")
        
        self.ext_uuid = self.create_result_row(res_frame, "UUID:", 1)
        self.ext_host = self.create_result_row(res_frame, "Host:", 2)
        self.ext_path = self.create_result_row(res_frame, "Path:", 3)
        
    def create_result_row(self, parent, label_text, row_idx):
        ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(weight="bold", size=13), 
                    text_color=CF_ORANGE).grid(row=row_idx, column=0, padx=(20, 10), pady=10, sticky="w")
        
        entry = ctk.CTkEntry(parent, font=ctk.CTkFont(family="Consolas", size=12), 
                            border_width=1, border_color="gray30")
        entry.grid(row=row_idx, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(parent, text="Copy", width=60, fg_color="transparent", border_width=1, 
                     border_color=CF_ORANGE, text_color=CF_ORANGE, hover_color="#332015", 
                     command=lambda e=entry: self.copy_to_clip(e.get())).grid(row=row_idx, column=2, padx=(10, 20), pady=10)
        return entry
        
    def paste_json(self):
        try:
            clipboard_text = self.parent.clipboard_get()
            self.json_textbox.delete("1.0", "end")
            self.json_textbox.insert("1.0", clipboard_text)
        except Exception:
            messagebox.showerror("Error", "Clipboard is empty or contains invalid data!")
            
    def clear_json(self):
        self.json_textbox.delete("1.0", "end")
        self.ext_uuid.delete(0, "end")
        self.ext_host.delete(0, "end")
        self.ext_path.delete(0, "end")
        
    def copy_to_clip(self, text):
        if text:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
            messagebox.showinfo("Success", "Copied to clipboard!")
            
    def extract_json(self):
        raw_data = self.json_textbox.get("1.0", "end").strip()
        if not raw_data:
            messagebox.showwarning("Warning", "Please paste the JSON configuration first!")
            return
        try:
            config = json.loads(raw_data)
            found_uuid = found_host = found_path = ""
            outbounds = config.get("outbounds", [])
            for out in outbounds:
                if out.get("protocol") == "vless":
                    try:
                        found_uuid = out["settings"]["vnext"][0]["users"][0]["id"]
                    except (KeyError, IndexError):
                        pass
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
            messagebox.showerror("Invalid JSON", "The text you pasted is not a valid JSON format.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")
