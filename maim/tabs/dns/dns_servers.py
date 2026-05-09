# tabs/dns/dns_servers.py
import os
import json
import shutil
from typing import List, Dict, Optional, Any
from config import DIRS, storage_crypto
from tabs.crypto_manager import storage_crypto

# لیست پیش‌فرض DNS سرورها
DEFAULT_DNS_LIST: List[Dict[str, Any]] = [
    {"name": "Google", "primary": "8.8.8.8", "secondary": "8.8.4.4", "type": "IPv4"},
    {"name": "Google (DoH)", "primary": "https://dns.google/dns-query", "secondary": "", "type": "DoH"},
    {"name": "Google (DoT)", "primary": "dns.google", "port": 853, "type": "DoT"},
    {"name": "Cloudflare", "primary": "1.1.1.1", "secondary": "1.0.0.1", "type": "IPv4"},
    {"name": "Cloudflare (DoH)", "primary": "https://cloudflare-dns.com/dns-query", "secondary": "", "type": "DoH"},
    {"name": "Cloudflare (DoT)", "primary": "1dot1dot1dot1.cloudflare-dns.com", "port": 853, "type": "DoT"},
    {"name": "Quad9", "primary": "9.9.9.9", "secondary": "149.112.112.112", "type": "IPv4"},
    {"name": "Quad9 (DoH)", "primary": "https://dns.quad9.net/dns-query", "secondary": "", "type": "DoH"},
    {"name": "Quad9 (DoT)", "primary": "dns.quad9.net", "port": 853, "type": "DoT"},
    {"name": "OpenDNS", "primary": "208.67.222.222", "secondary": "208.67.220.220", "type": "IPv4"},
    {"name": "AdGuard", "primary": "94.140.14.14", "secondary": "94.140.15.15", "type": "IPv4"},
    {"name": "Electro (IR)", "primary": "78.157.42.100", "secondary": "78.157.42.101", "type": "IPv4"},
    {"name": "Shecan (IR)", "primary": "178.22.122.100", "secondary": "185.51.200.2", "type": "IPv4"},
    {"name": "Radar Game (IR)", "primary": "10.202.10.10", "secondary": "10.202.10.11", "type": "IPv4"},
    {"name": "🚀 Cloudflare Localhost", "primary": "localhost", "secondary": "", "type": "LocalCF", "cf_only": True}
]


class DNSServersManager:
    """
    مدیریت لیست DNS سرورها (لود، ذخیره، اضافه، حذف) با پشتیبانی از رمزنگاری
    """

    def __init__(self):
        self.dns_file = os.path.join(DIRS["settings"], "NetTools_DNS.json")
        self.backup_file = os.path.join(DIRS["settings"], "NetTools_DNS.backup.json")
        self.servers = self.load()

    # ------------------------------------------------------------------
    # عملیات فایل (با رمزنگاری)
    # ------------------------------------------------------------------
    def load(self) -> List[Dict[str, Any]]:
        """بارگذاری لیست DNS از فایل JSON (رمزنگاری شده یا معمولی)"""
        # ابتدا تلاش برای بارگذاری با رمزنگاری
        data = storage_crypto.load_json(self.dns_file)
        if data is not None:
            # اطمینان از وجود کلید type برای سازگاری با نسخه‌های قدیمی
            for d in data:
                if "type" not in d:
                    d["type"] = "DoH" if str(d.get("primary", "")).startswith("http") else "IPv4"
            return data

        # اگر فایل رمزنگاری شده وجود نداشت، تلاش برای بارگذاری فایل معمولی (برای مهاجرت)
        if os.path.exists(self.dns_file):
            try:
                with open(self.dns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for d in data:
                        if "type" not in d:
                            d["type"] = "DoH" if str(d.get("primary", "")).startswith("http") else "IPv4"
                    # رمزنگاری و ذخیره مجدد برای مهاجرت
                    storage_crypto.save_json(self.dns_file, data)
                    return data
            except (json.JSONDecodeError, IOError):
                pass

        # تلاش برای بارگذاری از نسخه پشتیبان رمزنگاری شده
        backup_data = storage_crypto.load_json(self.backup_file)
        if backup_data is not None:
            return backup_data

        # تلاش برای بارگذاری از نسخه پشتیبان معمولی
        if os.path.exists(self.backup_file):
            try:
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        # بازگشت به لیست پیش‌فرض
        return [dict(s) for s in DEFAULT_DNS_LIST]

    def save(self) -> bool:
        """ذخیره لیست DNS در فایل JSON (رمزنگاری شده)"""
        try:
            # تهیه نسخه پشتیبان قبل از ذخیره (در صورت وجود فایل اصلی)
            if os.path.exists(self.dns_file) or os.path.exists(self.dns_file + '.enc'):
                # اگر فایل اصلی (رمزنگاری شده یا معمولی) وجود دارد، سعی می‌کنیم از آن بکاپ بگیریم
                current_data = self.load()
                if current_data:
                    storage_crypto.save_json(self.backup_file, current_data)
                elif os.path.exists(self.dns_file):
                    shutil.copy2(self.dns_file, self.backup_file)

            # ذخیره با رمزنگاری
            return storage_crypto.save_json(self.dns_file, self.servers)
        except Exception:
            # fallback به ذخیره معمولی در صورت خطا
            try:
                with open(self.dns_file, 'w', encoding='utf-8') as f:
                    json.dump(self.servers, f, indent=4, ensure_ascii=False)
                return True
            except:
                return False

    def reset_to_default(self) -> None:
        """بازنشانی لیست به حالت پیش‌فرض"""
        self.servers = [dict(s) for s in DEFAULT_DNS_LIST]
        self.save()

    # ------------------------------------------------------------------
    # مدیریت لیست
    # ------------------------------------------------------------------
    def add(self, server_info: Dict[str, Any]) -> bool:
        """
        اضافه کردن یک DNS جدید
        برمی‌گرداند: True در صورت موفقیت، False اگر تکراری باشد
        """
        # بررسی تکراری نبودن (بر اساس نام)
        if self.find_by_name(server_info.get("name", "")):
            return False
        self.servers.append(server_info)
        self.save()
        return True

    def update(self, name: str, new_info: Dict[str, Any]) -> bool:
        """به‌روزرسانی یک DNS موجود"""
        for i, s in enumerate(self.servers):
            if s.get("name") == name:
                self.servers[i] = new_info
                self.save()
                return True
        return False

    def delete(self, name: str) -> bool:
        """حذف یک DNS بر اساس نام"""
        original_len = len(self.servers)
        self.servers = [s for s in self.servers if s.get("name") != name]
        if len(self.servers) < original_len:
            self.save()
            return True
        return False

    def delete_by_index(self, index: int) -> bool:
        """حذف یک DNS بر اساس ایندکس"""
        if 0 <= index < len(self.servers):
            self.servers.pop(index)
            self.save()
            return True
        return False

    # ------------------------------------------------------------------
    # جستجو و دسترسی
    # ------------------------------------------------------------------
    def get_all(self) -> List[Dict[str, Any]]:
        """دریافت تمام DNSها"""
        return self.servers

    def get_names(self) -> List[str]:
        """دریافت لیست نام تمام DNSها"""
        return [s.get("name", "Unnamed") for s in self.servers]

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """یافتن DNS بر اساس نام"""
        for s in self.servers:
            if s.get("name") == name:
                return s
        return None

    def find_by_primary(self, primary: str) -> Optional[Dict[str, Any]]:
        """یافتن DNS بر اساس آدرس primary"""
        for s in self.servers:
            if s.get("primary") == primary:
                return s
        return None

    def filter_by_type(self, dns_type: str) -> List[Dict[str, Any]]:
        """فیلتر DNSها بر اساس نوع (IPv4, DoH, DoT, LocalCF)"""
        return [s for s in self.servers if s.get("type") == dns_type]

    def count(self) -> int:
        """تعداد DNSهای موجود"""
        return len(self.servers)

    def move_up(self, index: int) -> bool:
        """جابجایی یک DNS به بالا در لیست"""
        if 0 < index < len(self.servers):
            self.servers[index], self.servers[index-1] = self.servers[index-1], self.servers[index]
            self.save()
            return True
        return False

    def move_down(self, index: int) -> bool:
        """جابجایی یک DNS به پایین در لیست"""
        if 0 <= index < len(self.servers) - 1:
            self.servers[index], self.servers[index+1] = self.servers[index+1], self.servers[index]
            self.save()
            return True
        return False

    # ------------------------------------------------------------------
    # اعتبارسنجی
    # ------------------------------------------------------------------
    @staticmethod
    def validate_ipv4(ip: str) -> bool:
        """بررسی معتبر بودن فرمت IPv4"""
        if not ip:
            return False
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False

    @staticmethod
    def validate_doh_url(url: str) -> bool:
        """بررسی معتبر بودن URL برای DoH"""
        return url.startswith("https://") and len(url) > 8

    @staticmethod
    def validate_server_info(info: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        اعتبارسنجی یک رکورد DNS
        برمی‌گرداند: (is_valid, error_message)
        """
        name = info.get("name", "").strip()
        if not name:
            return False, "Name is required"

        dns_type = info.get("type", "IPv4")
        primary = info.get("primary", "").strip()

        if not primary:
            return False, "Primary address is required"

        if dns_type == "IPv4":
            if not DNSServersManager.validate_ipv4(primary):
                return False, f"Invalid IPv4 address: {primary}"
            secondary = info.get("secondary", "").strip()
            if secondary and not DNSServersManager.validate_ipv4(secondary):
                return False, f"Invalid secondary IPv4 address: {secondary}"
        elif dns_type == "DoH":
            if not DNSServersManager.validate_doh_url(primary):
                return False, "DoH URL must start with https://"
        elif dns_type == "DoT":
            # DoT hostname باید یک دامنه معتبر باشد (بررسی ساده)
            if not primary or '.' not in primary:
                return False, "Invalid DoT hostname"
        elif dns_type == "LocalCF":
            # برای LocalCF نیاز به اعتبارسنجی خاصی نیست
            pass

        return True, None

    # ------------------------------------------------------------------
    # import / export
    # ------------------------------------------------------------------
    def export_to_file(self, filepath: str, format: str = "json") -> bool:
        """
        صادرات لیست DNS به فایل (بدون رمزنگاری - خروجی معمولی)
        format: "json" یا "csv"
        """
        try:
            if format == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.servers, f, indent=2, ensure_ascii=False)
            elif format == "csv":
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    if self.servers:
                        fieldnames = ["name", "primary", "secondary", "type", "port"]
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(self.servers)
            else:
                return False
            return True
        except Exception:
            return False

    def import_from_file(self, filepath: str, replace: bool = False) -> tuple[int, List[str]]:
        """
        واردات DNS از فایل JSON (معمولی یا رمزنگاری شده)
        replace: اگر True باشد، لیست فعلی جایگزین می‌شود
        برمی‌گرداند: (تعداد اضافه شده, لیست خطاها)
        """
        try:
            # ابتدا تلاش برای بارگذاری با رمزنگاری
            imported = storage_crypto.load_json(filepath)
            if imported is None:
                # تلاش برای بارگذاری معمولی
                with open(filepath, 'r', encoding='utf-8') as f:
                    imported = json.load(f)

            if not isinstance(imported, list):
                return 0, ["File must contain a JSON array"]

            errors = []
            added = 0

            if replace:
                new_servers = []
                for item in imported:
                    is_valid, err = self.validate_server_info(item)
                    if is_valid:
                        new_servers.append(item)
                    else:
                        errors.append(f"{item.get('name', 'Unknown')}: {err}")
                self.servers = new_servers
                self.save()
                added = len(new_servers)
            else:
                existing_names = {s.get("name") for s in self.servers}
                for item in imported:
                    is_valid, err = self.validate_server_info(item)
                    if not is_valid:
                        errors.append(f"{item.get('name', 'Unknown')}: {err}")
                        continue
                    if item.get("name") in existing_names:
                        errors.append(f"{item.get('name')}: already exists")
                        continue
                    self.servers.append(item)
                    existing_names.add(item.get("name"))
                    added += 1
                self.save()

            return added, errors
        except Exception as e:
            return 0, [str(e)]

    def import_from_text_list(self, text: str, server_type: str = "IPv4") -> tuple[int, List[str]]:
        """
        واردات DNS از یک لیست متنی (هر خط یک IP یا URL)
        """
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith('#')]
        added = 0
        errors = []
        existing_names = {s.get("name") for s in self.servers}

        for i, line in enumerate(lines):
            # استخراج نام (اگر بعد از IP با فاصله آمده باشد)
            parts = line.split(maxsplit=1)
            addr = parts[0]
            custom_name = parts[1] if len(parts) > 1 else None

            # ساخت نام پیش‌فرض
            base_name = custom_name or f"Custom_{server_type}_{i+1}"
            name = base_name
            counter = 1
            while name in existing_names:
                name = f"{base_name}_{counter}"
                counter += 1

            server_info = {"name": name, "primary": addr, "secondary": "", "type": server_type}

            if server_type == "DoT" and ":" in addr:
                host, port = addr.split(":", 1)
                server_info["primary"] = host
                try:
                    server_info["port"] = int(port)
                except:
                    pass

            is_valid, err = self.validate_server_info(server_info)
            if is_valid:
                self.servers.append(server_info)
                existing_names.add(name)
                added += 1
            else:
                errors.append(f"Line {i+1}: {err}")

        if added > 0:
            self.save()
        return added, errors
