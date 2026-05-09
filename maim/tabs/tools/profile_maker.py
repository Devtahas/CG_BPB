# tabs/tools/profile_maker.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import time
import json
import os
import random
import requests
from datetime import datetime
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


class ProfileMakerTab:
    """تب پروفایل میکر - ضبط و بازپخش رفتار وب‌سایت"""
    
    def __init__(self, parent, tabview):
        self.parent = parent
        self.tab = tabview.add("Profile Maker")
        self.profiles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)
        self.is_recording = False
        self.is_simulating = False
        self.sim_stop_flag = False
        self.active_profile = None
        self.setup_ui()
        
    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        scroll.grid_columnconfigure(0, weight=1)
        
        # Recording Section
        record_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        record_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        record_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(record_frame, text="📹 1. Capture Website Traffic", font=ctk.CTkFont(size=15, weight="bold"), 
                    text_color="#29B6F6").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")
        
        ctk.CTkLabel(record_frame, text="Target URL:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.entry_url = ctk.CTkEntry(record_frame, placeholder_text="https://www.aparat.com")
        self.entry_url.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(record_frame, text="Profile Name:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.entry_name = ctk.CTkEntry(record_frame, placeholder_text="aparat_homepage")
        self.entry_name.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(record_frame, text="Browser:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.browser_profile = ctk.StringVar(value="chrome")
        browser_menu = ctk.CTkOptionMenu(record_frame, values=["chrome", "chrome_120", "chrome_133", "firefox", "safari", "edge"], 
                                        variable=self.browser_profile, fg_color=BG_PANEL, button_color=CF_ORANGE)
        browser_menu.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        
        self.var_duration = ctk.StringVar(value="30")
        ctk.CTkLabel(record_frame, text="Duration (sec):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkEntry(record_frame, textvariable=self.var_duration, width=80).grid(row=4, column=1, padx=10, pady=10, sticky="w")
        
        self.btn_record = ctk.CTkButton(record_frame, text="🔴 START RECORDING", fg_color="#C62828", hover_color="#8E0000", 
                                       font=ctk.CTkFont(weight="bold"), command=self.start_recording)
        self.btn_record.grid(row=5, column=0, columnspan=3, padx=20, pady=(5, 20), sticky="ew")
        
        # Profiles List
        profiles_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        profiles_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        profiles_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(profiles_frame, text="📁 Saved Profiles", font=ctk.CTkFont(size=15, weight="bold"), 
                    text_color=CF_ORANGE).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.profiles_container = ctk.CTkScrollableFrame(profiles_frame, height=150, fg_color="#121212", corner_radius=10)
        self.profiles_container.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkButton(profiles_frame, text="🔄 Refresh List", fg_color="transparent", border_width=1, 
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.refresh_list).grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Simulation Section
        sim_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        sim_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        sim_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(sim_frame, text="🎮 2. Replay Traffic", font=ctk.CTkFont(size=15, weight="bold"), 
                    text_color="#AB47BC").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")
        
        ctk.CTkLabel(sim_frame, text="Select Profile:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.combo_profiles = ctk.CTkComboBox(sim_frame, values=["No profiles found"], width=250, 
                                             state="readonly", dropdown_fg_color="#18181B")
        self.combo_profiles.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(sim_frame, text="Loop Count:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.entry_loop = ctk.CTkEntry(sim_frame, placeholder_text="1 (0 = forever)", width=150)
        self.entry_loop.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.entry_loop.insert(0, "1")
        
        self.var_jitter = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sim_frame, text="Add Random Jitter", variable=self.var_jitter, fg_color=CF_ORANGE).grid(row=2, column=2, padx=20, pady=10, sticky="w")
        
        btn_frame = ctk.CTkFrame(sim_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=3, padx=20, pady=(5, 15), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.btn_play = ctk.CTkButton(btn_frame, text="▶ START SIMULATION", fg_color="#2E7D32", hover_color="#1B5E20", 
                                     font=ctk.CTkFont(weight="bold"), command=self.start_simulation)
        self.btn_play.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.btn_stop = ctk.CTkButton(btn_frame, text="⏹ STOP", fg_color="#C62828", hover_color="#8E0000", 
                                     font=ctk.CTkFont(weight="bold"), state="disabled", command=self.stop_simulation)
        self.btn_stop.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.sim_status = ctk.CTkLabel(scroll, text="", text_color="gray")
        self.sim_status.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        
        # Import/Export
        ie_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ie_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        ie_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(ie_frame, text="📦 Import / Export", font=ctk.CTkFont(size=14, weight="bold"), 
                    text_color="#66BB6A").grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="w")
        ctk.CTkButton(ie_frame, text="📤 Export", fg_color="#1565C0", hover_color="#0D47A1", command=self.export_profile).grid(row=1, column=0, padx=20, pady=(5, 15), sticky="ew")
        ctk.CTkButton(ie_frame, text="📥 Import", fg_color="#1565C0", hover_color="#0D47A1", command=self.import_profile).grid(row=1, column=1, padx=20, pady=(5, 15), sticky="ew")
        
        self.refresh_list()
        
    def refresh_list(self):
        for widget in self.profiles_container.winfo_children():
            widget.destroy()
        profiles = [f.replace('.json', '') for f in os.listdir(self.profiles_dir) if f.endswith('.json')]
        if not profiles:
            ctk.CTkLabel(self.profiles_container, text="No profiles found", text_color="gray").pack(pady=20)
            self.combo_profiles.configure(values=["No profiles found"])
            return
        self.combo_profiles.configure(values=profiles)
        if profiles:
            self.combo_profiles.set(profiles[0])
        for profile in profiles:
            frame = ctk.CTkFrame(self.profiles_container, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(frame, text=profile, anchor="w").pack(side="left", padx=10, pady=5)
            btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(btn_frame, text="📋", width=30, fg_color="transparent", text_color=CF_ORANGE, 
                         command=lambda p=profile: self.copy_info(p)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="🗑️", width=30, fg_color="transparent", text_color="#EF5350", 
                         command=lambda p=profile: self.delete_profile(p)).pack(side="left", padx=2)
            
    def copy_info(self, profile_name):
        path = os.path.join(self.profiles_dir, f"{profile_name}.json")
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            info = f"Profile: {profile_name}\nURL: {data.get('url', 'N/A')}\nBrowser: {data.get('browser_profile', 'N/A')}\nRequests: {data.get('total_requests', 0)}\nCreated: {data.get('created', 'N/A')}"
            self.parent.clipboard_clear()
            self.parent.clipboard_append(info)
            messagebox.showinfo("Copied", "Profile info copied!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def delete_profile(self, profile_name):
        if messagebox.askyesno("Confirm", f"Delete '{profile_name}'?"):
            try:
                os.remove(os.path.join(self.profiles_dir, f"{profile_name}.json"))
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
    def start_recording(self):
        url = self.entry_url.get().strip()
        name = self.entry_name.get().strip()
        if not url or not name:
            messagebox.showerror("Error", "Please enter URL and Profile Name!")
            return
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            duration = int(self.var_duration.get())
        except:
            duration = 30
        self.is_recording = True
        self.btn_record.configure(text="⏹ STOP RECORDING", state="normal")
        self.sim_status.configure(text=f"Recording {url}...", text_color=CF_ORANGE)
        threading.Thread(target=self._record, args=(url, name, duration), daemon=True).start()
        
    def _record(self, url, name, duration):
        recorded = {"name": name, "url": url, "browser_profile": self.browser_profile.get(), 
                   "created": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "duration": duration, 
                   "requests": [], "total_requests": 0}
        start_time = time.time()
        try:
            if CURL_CFFI_AVAILABLE:
                session = curl_requests.Session(impersonate=self.browser_profile.get())
            else:
                session = requests.Session()
                session.headers.update({'User-Agent': 'Mozilla/5.0'})
            start_req = time.time()
            resp = session.get(url, timeout=15)
            req_time = int((time.time() - start_req) * 1000)
            recorded["requests"].append({"type": "http_request", "method": "GET", "url": url, 
                                        "status": resp.status_code, "duration_ms": req_time})
            end_time = time.time() + duration
            while time.time() < end_time and self.is_recording:
                delay = random.uniform(0.5, 1.5)
                time.sleep(delay)
                recorded["requests"].append({"type": "delay", "duration_ms": int(delay * 1000)})
        except Exception as e:
            recorded["requests"].append({"type": "error", "message": str(e)})
        recorded["total_requests"] = len(recorded["requests"])
        with open(os.path.join(self.profiles_dir, f"{name}.json"), 'w') as f:
            json.dump(recorded, f, indent=2)
        self.parent.after(0, lambda: self.sim_status.configure(text=f"✅ Saved! {recorded['total_requests']} events", text_color="#66BB6A"))
        self.parent.after(0, self.refresh_list)
        self.parent.after(0, lambda: self.btn_record.configure(text="🔴 START RECORDING"))
        self.is_recording = False
        
    def start_simulation(self):
        profile_name = self.combo_profiles.get()
        if not profile_name or profile_name == "No profiles found":
            messagebox.showerror("Error", "Select a profile!")
            return
        path = os.path.join(self.profiles_dir, f"{profile_name}.json")
        if not os.path.exists(path):
            messagebox.showerror("Error", "Profile not found!")
            return
        with open(path, 'r') as f:
            self.active_profile = json.load(f)
        loop_str = self.entry_loop.get().strip()
        max_loops = None if loop_str == "0" or loop_str.lower() == "infinite" else (int(loop_str) if loop_str.isdigit() else 1)
        self.is_simulating = True
        self.sim_stop_flag = False
        self.btn_play.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.sim_status.configure(text=f"🎭 Simulating {profile_name}...", text_color="#AB47BC")
        threading.Thread(target=self._simulate, args=(max_loops,), daemon=True).start()
        
    def _simulate(self, max_loops):
        import time, random
        loop_count = 0
        url = self.active_profile.get('url', '')
        browser = self.active_profile.get('browser_profile', 'chrome')
        def log(msg):
            self.parent.after(0, lambda: self.sim_status.configure(text=msg, text_color=CF_ORANGE))
        while not self.sim_stop_flag:
            if max_loops is not None and loop_count >= max_loops:
                break
            loop_count += 1
            log(f"Loop {loop_count}/{max_loops if max_loops else '∞'} - {self.active_profile.get('name')}")
            try:
                if CURL_CFFI_AVAILABLE:
                    session = curl_requests.Session(impersonate=browser)
                else:
                    session = requests.Session()
                for req in self.active_profile.get('requests', []):
                    if self.sim_stop_flag:
                        break
                    if req.get('type') == 'http_request':
                        expected = req.get('duration_ms', 100) / 1000
                        start = time.time()
                        try:
                            session.get(req.get('url', url), timeout=5)
                            remaining = expected - (time.time() - start)
                            if remaining > 0:
                                time.sleep(remaining * random.uniform(0.9, 1.1))
                        except:
                            time.sleep(expected)
                    elif req.get('type') == 'delay':
                        time.sleep((req.get('duration_ms', 1000) / 1000) * random.uniform(0.9, 1.1))
                log(f"✅ Loop {loop_count} completed")
            except Exception as e:
                log(f"❌ Error: {str(e)[:50]}")
        self.is_simulating = False
        self.parent.after(0, lambda: self.btn_play.configure(state="normal"))
        self.parent.after(0, lambda: self.btn_stop.configure(state="disabled"))
        self.parent.after(0, lambda: self.sim_status.configure(text="✅ Finished" if not self.sim_stop_flag else "⏹ Stopped", text_color="#66BB6A"))
        
    def stop_simulation(self):
        self.sim_stop_flag = True
        self.sim_status.configure(text="Stopping...", text_color="#FFA726")
        self.btn_stop.configure(state="disabled")
        
    def export_profile(self):
        profile = self.combo_profiles.get()
        if not profile or profile == "No profiles found":
            messagebox.showerror("Error", "Select a profile!")
            return
        src = os.path.join(self.profiles_dir, f"{profile}.json")
        if not os.path.exists(src):
            messagebox.showerror("Error", "Profile not found!")
            return
        dst = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"{profile}.json", filetypes=[("JSON files", "*.json")])
        if dst:
            import shutil
            shutil.copy(src, dst)
            messagebox.showinfo("Success", f"Exported to {dst}")
            
    def import_profile(self):
        src = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if src:
            import shutil
            shutil.copy(src, os.path.join(self.profiles_dir, os.path.basename(src)))
            self.refresh_list()
            messagebox.showinfo("Success", "Profile imported!")
