# tabs/setting/storage_manager.py
import os
import json
import shutil
from typing import Dict, Optional
from tkinter import messagebox

DEFAULT_BASE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data")

class StorageManager:
    """مدیریت مسیر ذخیره‌سازی و پوشه‌بندی دیتا"""
    
    CONFIG_FILE = "storage_path.json"  # در کنار executable
    
    def __init__(self):
        self.base_dir = self._load_path()
        self.dirs = self._build_dirs()
        self._ensure_dirs()
    
    def _get_config_path(self):
        """مسیر فایل تنظیمات مسیر ذخیره‌سازی (کنار فایل اجرایی)"""
        import sys
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(exe_dir, self.CONFIG_FILE)
    
    def _load_path(self) -> str:
        """بارگذاری مسیر ذخیره‌سازی از فایل کانفیگ"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    custom_path = data.get('base_dir', '').strip()
                    if custom_path and os.path.exists(os.path.dirname(custom_path)):
                        return custom_path
            except:
                pass
        return DEFAULT_BASE_DIR
    
    def save_path(self, new_path: str) -> bool:
        """ذخیره مسیر جدید در فایل کانفیگ"""
        config_path = self._get_config_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'base_dir': new_path}, f)
            return True
        except Exception as e:
            print(f"Failed to save storage path: {e}")
            return False
    
    def change_base_dir(self, new_base_dir: str, move_files: bool = False) -> bool:
        """تغییر مسیر پایه ذخیره‌سازی و در صورت نیاز انتقال فایل‌ها"""
        new_base_dir = os.path.abspath(new_base_dir)
        old_base_dir = self.base_dir
        
        if new_base_dir == old_base_dir:
            return True
        
        # بررسی وجود مسیر مقصد (والد آن باید وجود داشته باشد)
        parent_dir = os.path.dirname(new_base_dir)
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except:
                messagebox.showerror("Error", f"Cannot create parent directory:\n{parent_dir}")
                return False
        
        # انتقال فایل‌ها اگر کاربر درخواست داده باشد
        if move_files and os.path.exists(old_base_dir):
            if messagebox.askyesno("Move Files", 
                                   f"Do you want to move all existing data from:\n{old_base_dir}\nto:\n{new_base_dir}?"):
                try:
                    # اگر مسیر جدید وجود دارد و خالی نیست، خطا بدهیم
                    if os.path.exists(new_base_dir) and os.listdir(new_base_dir):
                        if not messagebox.askyesno("Warning", 
                                                   f"Destination folder is not empty.\nFiles may be overwritten.\nContinue?"):
                            return False
                    # انتقال کل پوشه
                    shutil.move(old_base_dir, new_base_dir)
                    messagebox.showinfo("Success", f"Data moved to:\n{new_base_dir}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to move data:\n{str(e)}")
                    return False
        
        # ذخیره مسیر جدید
        if self.save_path(new_base_dir):
            self.base_dir = new_base_dir
            self.dirs = self._build_dirs()
            self._ensure_dirs()
            return True
        return False
    
    def reset_to_default(self) -> bool:
        """بازنشانی به مسیر پیش‌فرض دسکتاپ"""
        return self.change_base_dir(DEFAULT_BASE_DIR, move_files=False)
    
    def _build_dirs(self) -> Dict[str, str]:
        """ساخت دیکشنری زیرپوشه‌ها"""
        return {
            "configs": os.path.join(self.base_dir, "Configs"),
            "subs": os.path.join(self.base_dir, "Subscriptions"),
            "settings": os.path.join(self.base_dir, "Settings")
        }
    
    def _ensure_dirs(self):
        """ایجاد پوشه‌ها در صورت عدم وجود"""
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
    
    def get_base_dir(self) -> str:
        return self.base_dir
    
    def get_dirs(self) -> Dict[str, str]:
        return self.dirs
