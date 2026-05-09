# tabs/plugins/plugin_manager.py

import os
import sys
import json
import shutil
import zipfile
import threading
import importlib
import requests
from typing import Dict, List, Optional, Any
from config import DIRS, CF_ORANGE  # برای مسیرها و رنگ‌ها (در صورت نیاز برای لاگ)
from .plugin_base import BasePlugin


class PluginManager:
    """
    مدیریت نصب، بارگذاری، غیرفعال‌سازی و حذف پلاگین‌ها.
    پلاگین‌ها در پوشه plugins/ داخل دایرکتوری settings ذخیره می‌شوند.
    """

    PLUGINS_DIR_NAME = "plugins"

    def __init__(self):
        self.plugins_dir = os.path.join(DIRS["settings"], self.PLUGINS_DIR_NAME)
        os.makedirs(self.plugins_dir, exist_ok=True)

        self.loaded_plugins: Dict[str, BasePlugin] = {}  # plugin_id: instance
        self._config_path = os.path.join(self.plugins_dir, "plugins_config.json")
        self._config: Dict[str, Dict[str, bool]] = self._load_config()

        # آدرس Worker پیش‌فرض (بعداً قابل تنظیم توسط کاربر)
        self.worker_base_url = "https://your-worker-worker-name.workers.dev"

    # =================================================================
    # مدیریت فایل پیکربندی (enabled/disabled)
    # =================================================================
    def _load_config(self) -> dict:
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"[PluginManager] Error saving config: {e}")

    def _is_enabled(self, plugin_id: str) -> bool:
        return self._config.get(plugin_id, {}).get("enabled", True)

    def set_enabled(self, plugin_id: str, enabled: bool, auto_load: bool = True):
        if plugin_id not in self._config:
            self._config[plugin_id] = {}
        self._config[plugin_id]["enabled"] = enabled
        self._save_config()
        if auto_load:
            if enabled:
                self.load_plugin(plugin_id)
            else:
                self.unload_plugin(plugin_id)

    # =================================================================
    # کشف پلاگین‌های نصب‌شده
    # =================================================================
    def discover_plugins(self) -> List[dict]:
        """بازگرداندن لیست تمام پلاگین‌های معتبر نصب‌شده به همراه اطلاعات آنها"""
        discovered = []
        if not os.path.exists(self.plugins_dir):
            return discovered

        for name in os.listdir(self.plugins_dir):
            folder = os.path.join(self.plugins_dir, name)
            manifest_path = os.path.join(folder, 'manifest.json')
            if os.path.isdir(folder) and os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    plugin_id = name
                    discovered.append({
                        "id": plugin_id,
                        "folder": folder,
                        "manifest": manifest,
                        "enabled": self._is_enabled(plugin_id),
                        "loaded": plugin_id in self.loaded_plugins
                    })
                except Exception:
                    continue
        # مرتب‌سازی بر اساس نام
        discovered.sort(key=lambda p: p["manifest"].get("name", p["id"]))
        return discovered

    # =================================================================
    # بارگذاری / توقف پلاگین‌ها
    # =================================================================
    def load_plugin(self, plugin_id: str) -> bool:
        """بارگذاری و فعال‌سازی یک پلاگین (فقط اگر فعال باشد)"""
        if plugin_id in self.loaded_plugins:
            return True
        plugins = self.discover_plugins()
        for p in plugins:
            if p["id"] == plugin_id:
                if not p["enabled"]:
                    return False  # غیرفعال است، بارگذاری نمی‌کنیم
                manifest = p["manifest"]
                entry_point = manifest.get("entry_point", "main:Plugin")
                if ":" not in entry_point:
                    entry_point = "main:" + entry_point
                module_path, class_name = entry_point.split(":")
                folder = p["folder"]

                # ★ اطمینان از وجود مسیر اصلی پروژه در sys.path
                # این کار باعث می‌شود که import های داخل پلاگین (مثل from tabs.plugins.plugin_base import ...)
                # به درستی کار کنند
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)

                # اضافه کردن مسیر پوشه پلاگین برای import ماژول اصلی آن
                sys.path.insert(0, folder)
                try:
                    module = importlib.import_module(module_path)
                    plugin_class = getattr(module, class_name)
                    instance = plugin_class(app_context=None)  # می‌توانید اپ اصلی را پاس دهید
                    instance.manifest = manifest
                    instance.on_load()
                    self.loaded_plugins[plugin_id] = instance
                    return True
                except Exception as e:
                    print(f"[PluginManager] Error loading plugin {plugin_id}: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # پاکسازی مسیرها
                    if folder in sys.path:
                        sys.path.remove(folder)
        return False

    def unload_plugin(self, plugin_id: str):
        """توقف و آزادسازی پلاگین"""
        if plugin_id in self.loaded_plugins:
            try:
                self.loaded_plugins[plugin_id].on_unload()
            except Exception as e:
                print(f"[PluginManager] Error unloading plugin {plugin_id}: {e}")
            del self.loaded_plugins[plugin_id]

    # =================================================================
    # نصب پلاگین از فایل ZIP
    # =================================================================
    def install_from_zip(self, zip_path: str) -> Optional[str]:
        """
        نصب پلاگین از یک فایل ZIP.
        برمی‌گرداند plugin_id در صورت موفقیت، در غیر این صورت None.
        """
        try:
            # خواندن فایل ZIP و بررسی manifest.json در ریشه آن
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # یافتن manifest.json (ممکن است داخل یک پوشه باشد)
                manifest_filename = None
                for fname in zf.namelist():
                    if fname.endswith('manifest.json') and '/' not in fname.replace('\\', '/').split('/')[0]:
                        manifest_filename = fname
                        break
                    elif fname.endswith('manifest.json') and fname.count('/') == 1:
                        manifest_filename = fname
                        break
                if not manifest_filename:
                    raise Exception("manifest.json not found in zip root")
                manifest_data = json.loads(zf.read(manifest_filename).decode('utf-8'))
                plugin_name = manifest_data.get("name", "Unknown")
                # ساخت یک ID یکتا بر اساس نام پوشه (از نام فایل زیپ یا نام پلاگین)
                plugin_id = self._sanitize_id(plugin_name)
                if os.path.exists(os.path.join(self.plugins_dir, plugin_id)):
                    # اگر وجود داشت، پسوند اضافه کن
                    import time
                    plugin_id = f"{plugin_id}_{int(time.time())}"
                target_dir = os.path.join(self.plugins_dir, plugin_id)
                os.makedirs(target_dir, exist_ok=True)
                # استخراج تمام فایل‌ها
                for member in zf.namelist():
                    # اگر manifest.json داخل یک پوشه بود، مسیر را اصلاح کن
                    if manifest_filename != 'manifest.json' and member.startswith(os.path.dirname(manifest_filename)):
                        arcname = member[len(os.path.dirname(manifest_filename))+1:]
                        if not arcname:
                            continue
                        target_path = os.path.join(target_dir, arcname)
                    else:
                        target_path = os.path.join(target_dir, member)
                    if member.endswith('/'):  # دایرکتوری
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with zf.open(member) as source, open(target_path, 'wb') as dest:
                            shutil.copyfileobj(source, dest)
                # تنظیم enabled = True به صورت پیش‌فرض
                self.set_enabled(plugin_id, True, auto_load=False)
                return plugin_id
        except Exception as e:
            print(f"[PluginManager] install_from_zip error: {e}")
            import traceback
            traceback.print_exc()
            return None

    # =================================================================
    # نصب پلاگین از Worker
    # =================================================================
    def install_from_worker(self, plugin_store_id: str, worker_url: Optional[str] = None) -> Optional[str]:
        """
        دانلود و نصب پلاگین از یک کلودفلر ورکر.
        plugin_store_id: شناسه پلاگین در فروشگاه.
        worker_url: آدرس ورکر (اگر None باشد از worker_base_url استفاده می‌شود).
        """
        if worker_url is None:
            worker_url = self.worker_base_url
        download_url = f"{worker_url}/api/plugins/{plugin_store_id}/download"
        try:
            resp = requests.get(download_url, timeout=30)
            resp.raise_for_status()
            # ذخیره موقت فایل ZIP
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            plugin_id = self.install_from_zip(tmp_path)
            os.unlink(tmp_path)
            return plugin_id
        except Exception as e:
            print(f"[PluginManager] install_from_worker error: {e}")
            return None

    # =================================================================
    # حذف پلاگین
    # =================================================================
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """حذف کامل پلاگین (پوشه و اطلاعات)"""
        if plugin_id in self.loaded_plugins:
            self.unload_plugin(plugin_id)
        folder = os.path.join(self.plugins_dir, plugin_id)
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"[PluginManager] Error deleting folder for {plugin_id}: {e}")
                return False
        # حذف از کانفیگ
        if plugin_id in self._config:
            del self._config[plugin_id]
            self._save_config()
        return True

    # =================================================================
    # ابزارهای کمکی
    # =================================================================
    def _sanitize_id(self, name: str) -> str:
        """تبدیل نام پلاگین به یک ID مجاز برای نام پوشه"""
        import re
        name = re.sub(r'[^a-zA-Z0-9_\- ]', '', name)
        name = re.sub(r'\s+', '_', name.strip().lower())
        if not name:
            name = "unknown_plugin"
        return name

    def get_plugin_instance(self, plugin_id: str) -> Optional[BasePlugin]:
        """دریافت نمونه پلاگین، در صورت نیاز بارگذاری خودکار"""
        if plugin_id not in self.loaded_plugins:
            # تلاش برای بارگذاری (اگر فعال باشد)
            self.load_plugin(plugin_id)
        return self.loaded_plugins.get(plugin_id)

    # =================================================================
    # دسته‌بندی پلاگین‌ها
    # =================================================================
    def get_plugins_by_category(self, category: str) -> List[dict]:
        """
        بازگرداندن پلاگین‌های فعال که به یک دسته‌بندی خاص تعلق دارند.
        مثال: category = "tools" → تمام پلاگین‌های مربوط به بخش Tools.
        """
        result = []
        for p in self.discover_plugins():
            manifest = p.get("manifest", {})
            if manifest.get("category") == category and p["enabled"]:
                result.append(p)
        return result

    # =================================================================
    # راه‌اندازی اولیه همه پلاگین‌های فعال
    # =================================================================
    def load_all_enabled(self):
        for plugin in self.discover_plugins():
            if plugin["enabled"]:
                self.load_plugin(plugin["id"])
