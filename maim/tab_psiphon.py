# tab_psiphon.py
import customtkinter as ctk
import subprocess
import os
import sys
import threading
import time
import ctypes
from config import CF_ORANGE, BG_PANEL

def get_core_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class PsiphonFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        self.psiphon_process = None
        self.is_connected = False

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🅿️ Psiphon Network", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)

        # Status Bar
        self.status_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.status_frame.grid(row=1, column=0, padx=40, pady=20, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Status: Disconnected", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350")
        self.lbl_status.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.btn_connect = ctk.CTkButton(self.status_frame, text="▶ LAUNCH PSIPHON", width=160, fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold", size=14), command=self.toggle_psiphon)
        self.btn_connect.grid(row=0, column=2, padx=20, pady=20, sticky="e")

        # Progress Box
        self.prog_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=15)
        self.prog_frame.grid(row=2, column=0, padx=40, pady=0, sticky="ew")
        self.prog_frame.grid_columnconfigure(0, weight=1)

        self.progressbar = ctk.CTkProgressBar(self.prog_frame, progress_color=CF_ORANGE)
        self.progressbar.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.progressbar.set(0)

        # Info Description
        desc_text = "Psiphon connects automatically in the background.\nAll connections will be encrypted and system proxy will be set automatically."
        ctk.CTkLabel(self, text=desc_text, justify="left", text_color="gray", font=ctk.CTkFont(size=14)).grid(row=3, column=0, padx=40, pady=20, sticky="w")

    def toggle_psiphon(self):
        if not self.is_connected:
            self.start_psiphon()
        else:
            self.stop_psiphon()

    def start_psiphon(self):
        psiphon_exe = get_core_path(os.path.join("cores", "psiphon", "psiphon3.exe"))
        
        if not os.path.exists(psiphon_exe):
            ctk.messagebox.showerror("Error", "psiphon3.exe not found in 'cores/psiphon/psiphon3.exe'")
            return

        self.is_connected = True
        self.lbl_status.configure(text="Status: Bootstrapping...", text_color=CF_ORANGE)
        self.btn_connect.configure(state="disabled")
        
        # اجرای سایفون
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        self.psiphon_process = subprocess.Popen([psiphon_exe], creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
        
        # اجرای ترفند جادویی نامرئی کردن پنجره گرافیکی سایفون در یک Thread جداگانه
        threading.Thread(target=self._window_hider_and_progress, daemon=True).start()

    def _window_hider_and_progress(self):
        """این تابع همزمان هم پنجره سایفون را مخفی می‌کند و هم نوار پیشرفت را پر می‌کند"""
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        ShowWindow = ctypes.windll.user32.ShowWindow

        def foreach_window(hwnd, lParam):
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    # اگر اسم پنجره Psiphon بود، آن را نامرئی کن
                    if "Psiphon" in buff.value:
                        ShowWindow(hwnd, 0) # 0 = SW_HIDE
            return True

        # پر کردن نوار پیشرفت (سایفون حدودا 10 ثانیه طول میکشه تا وصل شه)
        for i in range(1, 101):
            if not self.is_connected: break
            
            # در طول این 10 ثانیه، مدام چک میکند تا پنجره سایفون باز نشود
            EnumWindows(EnumWindowsProc(foreach_window), 0)
            
            self.after(0, lambda val=i: self.progressbar.set(val / 100.0))
            time.sleep(0.1) # مجموعا حدود 10 ثانیه زمان میبرد

        if self.is_connected:
            self.after(0, lambda: self.lbl_status.configure(text="Status: Connected & Hidden", text_color="#66BB6A"))
            self.after(0, lambda: self.btn_connect.configure(text="⏹ DISCONNECT", fg_color="#C62828", hover_color="#8E0000", state="normal"))

    def stop_psiphon(self):
        # برای بستن سایفون بدون به هم ریختن سیستم پروکسی، باید درخواست بسته شدن پنجره را به آن بفرستیم
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        PostMessage = ctypes.windll.user32.PostMessageW

        def foreach_window(hwnd, lParam):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                if "Psiphon" in buff.value:
                    PostMessage(hwnd, 0x0010, 0, 0) # کد 0x0010 یعنی دستور WM_CLOSE به پنجره
            return True
            
        EnumWindows(EnumWindowsProc(foreach_window), 0)
        
        # محکم کاری: اگر بعد از 1.5 ثانیه بسته نشد، اجباری میبندیمش
        time.sleep(1.5)
        os.system("taskkill /f /im psiphon3.exe >nul 2>&1")
        
        if self.psiphon_process:
            self.psiphon_process = None
            
        self.is_connected = False
        self.progressbar.set(0)
        self.lbl_status.configure(text="Status: Disconnected", text_color="#EF5350")
        self.btn_connect.configure(text="▶ LAUNCH PSIPHON", fg_color="#2E7D32", hover_color="#1B5E20")
    def stop_connection(self):
         self.stop_psiphon()