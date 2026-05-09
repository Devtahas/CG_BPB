# tabs/setting/asset_manager.py

import os
import json
from config import DIRS
from tabs.crypto_manager import storage_crypto

class AssetManager:
    """
    مدیریت مرکزی منابع (IP Ranges و DNS Servers)
    تمام بخش‌های برنامه از این کلاس برای دریافت لیست‌های معتبر تغذیه می‌کنند.
    """

    def __init__(self):
        self.settings_dir = DIRS.get("settings", "Settings")
        os.makedirs(self.settings_dir, exist_ok=True)

        # نام فایل‌های ذخیره‌سازی
        self.IP_LISTS_FILE = "ip_lists.json"
        self.DNS_LIST_FILE = "dns_list.json"

        # بارگذاری اولیه
        self.ip_lists = self._load_json(self.IP_LISTS_FILE, {})
        self.dns_list = self._load_json(self.DNS_LIST_FILE, [])

        # اطمینان از وجود لیست‌های پیش‌فرض
        self._ensure_defaults()

    def _load_json(self, filename, default):
        filepath = os.path.join(self.settings_dir, filename)
        data = storage_crypto.load_json(filepath)
        return data if data is not None else default

    def _save_json(self, filename, data):
        filepath = os.path.join(self.settings_dir, filename)
        storage_crypto.save_json(filepath, data)

    def _ensure_defaults(self):
        """لیست‌های پیش‌فرض را در صورت خالی بودن ایجاد می‌کند."""
        # IP های پیش‌فرض کلادفلر
        default_cloudflare_cidrs = [
            "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "104.16.0.0/13",
            "104.24.0.0/14", "108.162.192.0/18", "131.0.72.0/22", "141.101.64.0/18",
            "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
            "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17"
        ]
        if "cloudflare" not in self.ip_lists:
            self.ip_lists["cloudflare"] = default_cloudflare_cidrs
            self._save_json(self.IP_LISTS_FILE, self.ip_lists)

        # IP های پیش‌فرض دیتاسنتر (خالی)
        if "datacenter" not in self.ip_lists:
            self.ip_lists["datacenter"] = []
            self._save_json(self.IP_LISTS_FILE, self.ip_lists)

        # IP های پیش‌فرض Fastly
        default_fastly_cidrs = [
            "23.235.32.0/20",
            "43.249.72.0/22",
            "103.244.50.0/24",
            "103.244.51.0/24",
            "104.156.80.0/20",
            "146.75.0.0/17",
            "151.101.0.0/16",
            "157.52.64.0/18",
            "167.82.0.0/17",
            "167.82.128.0/17",
            "172.111.64.0/18",
            "185.31.16.0/22",
            "199.27.72.0/21",
            "199.232.0.0/16",
            "202.21.128.0/17",
            "203.57.145.0/24",
            "23.235.33.0/24",
            "23.235.34.0/23",
            "104.156.81.0/24",
        ]
        if "fastly" not in self.ip_lists:
            self.ip_lists["fastly"] = default_fastly_cidrs
            self._save_json(self.IP_LISTS_FILE, self.ip_lists)

        # DNS های پیش‌فرض
        if not self.dns_list:
            self.dns_list = [
                "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1",
                "9.9.9.9", "149.112.112.112", "208.67.222.222", "208.67.220.220",
                "94.140.14.14", "94.140.15.15", "178.22.122.100", "185.51.200.2",
                "78.157.42.100", "78.157.42.101", "10.202.10.10", "10.202.10.11"
            ]
            self._save_json(self.DNS_LIST_FILE, self.dns_list)

    # --- API برای دریافت لیست‌ها ---
    def get_ip_list(self, list_name):
        """یک کپی از لیست آی‌پی برای استفاده در اسکنرها برمی‌گرداند."""
        return list(self.ip_lists.get(list_name, []))

    def get_dns_list(self):
        """یک کپی از لیست DNS برمی‌گرداند."""
        return list(self.dns_list)

    # --- API برای مدیریت ---
    def update_ip_list(self, list_name, new_list):
        """کل لیست آی‌پی را جایگزین می‌کند."""
        self.ip_lists[list_name] = list(set(new_list)) # حذف تکراری‌ها
        self._save_json(self.IP_LISTS_FILE, self.ip_lists)

    def update_dns_list(self, new_list):
        """کل لیست DNS را جایگزین می‌کند."""
        self.dns_list = list(set(new_list)) # حذف تکراری‌ها
        self._save_json(self.DNS_LIST_FILE, self.dns_list)

    def add_ip(self, list_name, ip):
        if ip not in self.ip_lists.get(list_name, []):
            self.ip_lists[list_name].append(ip)
            self._save_json(self.IP_LISTS_FILE, self.ip_lists)
            return True
        return False

    def remove_ip(self, list_name, ip):
        if ip in self.ip_lists.get(list_name, []):
            self.ip_lists[list_name].remove(ip)
            self._save_json(self.IP_LISTS_FILE, self.ip_lists)
            return True
        return False

    def add_dns(self, dns):
        if dns not in self.dns_list:
            self.dns_list.append(dns)
            self._save_json(self.DNS_LIST_FILE, self.dns_list)
            return True
        return False

    def remove_dns(self, dns):
        if dns in self.dns_list:
            self.dns_list.remove(dns)
            self._save_json(self.DNS_LIST_FILE, self.dns_list)
            return True
        return False
