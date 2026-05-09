# tabs/dns/dns_core.py
import subprocess
import ctypes
import socket
import threading
import time
import os
import sys

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from .local_cf_server import LocalCloudflareDNSServer
from .doh_server import LocalDoHServer
from .fake_dns import FakeDNSServer


class DNSCore:
    """
    هسته اصلی مدیریت DNS سیستم (اتصال، قطع، تغییر)
    مسئول:
        - اعمال DNS روی سیستم (netsh)
        - مدیریت سرویس‌های DNS محلی (Local CF, DoH, FakeDNS)
        - تشخیص اینترفیس فعال شبکه
        - بررسی دسترسی ادمین
    """

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.active_interface = self.get_active_network_interface()
        self.current_dns = None  # اطلاعات DNS فعلی
        self.local_cf_server = None
        self.doh_server = None
        self.fake_dns_server = None

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    @staticmethod
    def is_admin():
        """بررسی دسترسی Administrator (ویندوز)"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def get_active_network_interface(self):
        """تشخیص اینترفیس فعال شبکه (با اتصال به 8.8.8.8)"""
        if not HAS_PSUTIL:
            return "Wi-Fi"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address == local_ip:
                        return interface
        except:
            pass
        return "Wi-Fi"

    # ------------------------------------------------------------------
    # اعمال DNS روی سیستم
    # ------------------------------------------------------------------
    def apply_ipv4_dns(self, primary: str, secondary: str = "") -> tuple:
        """
        تنظیم DNS IPv4 روی سیستم (netsh)
        برمی‌گرداند: (success, error_message)
        """
        if not self.is_admin():
            return False, "Administrator privileges required."

        adapter = self.active_interface
        try:
            cmd1 = f'netsh interface ipv4 set dnsservers name="{adapter}" source=static address="{primary}" primary'
            subprocess.run(cmd1, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            if secondary:
                cmd2 = f'netsh interface ipv4 add dnsservers name="{adapter}" address="{secondary}" index=2'
                subprocess.run(cmd2, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.current_dns = {"primary": primary, "secondary": secondary, "type": "IPv4"}
            self.log(f"DNS set to {primary} (IPv4)")
            return True, None
        except subprocess.CalledProcessError as e:
            return False, f"netsh error: {e}"
        except Exception as e:
            return False, str(e)

    def apply_local_cf_dns(self) -> tuple:
        """
        راه‌اندازی Local Cloudflare DNS Server و تنظیم سیستم روی localhost
        برمی‌گرداند: (success, error_message, bound_ip)
        """
        if not self.is_admin():
            return False, "Administrator privileges required.", None

        self.local_cf_server = LocalCloudflareDNSServer()
        if not self.local_cf_server.start():
            return False, "Could not start Local Cloudflare DNS server (port 53 busy?)", None

        bound_ip = self.local_cf_server.bound_ip
        success, err = self.apply_ipv4_dns(bound_ip, "")
        if success:
            self.current_dns = {"primary": bound_ip, "secondary": "", "type": "LocalCF"}
            self.log(f"Local CF DNS active on {bound_ip}")
            return True, None, bound_ip
        else:
            self.local_cf_server.stop()
            self.local_cf_server = None
            return False, err, None

    def apply_doh_dns(self, doh_url: str) -> tuple:
        """
        راه‌اندازی Local DoH Server و تنظیم سیستم روی localhost
        برمی‌گرداند: (success, error_message, bound_ip)
        """
        if not self.is_admin():
            return False, "Administrator privileges required.", None

        self.doh_server = LocalDoHServer(doh_url)
        if not self.doh_server.start():
            return False, "Could not start Local DoH server (port 53 busy?)", None

        bound_ip = self.doh_server.bound_ip
        success, err = self.apply_ipv4_dns(bound_ip, "")
        if success:
            self.current_dns = {"primary": doh_url, "secondary": "", "type": "DoH"}
            self.log(f"DoH DNS active via {bound_ip} -> {doh_url}")
            return True, None, bound_ip
        else:
            self.doh_server.stop()
            self.doh_server = None
            return False, err, None

    def apply_dot_dns(self, host: str, port: int = 853) -> tuple:
        """
        تنظیم DNS بر روی DoT (نیازمند DNS سرور محلی یا پروکسی)
        برای سادگی، فعلاً فقط سیستم را روی یک DNS معمولی (مثلاً 1.1.1.1) تنظیم می‌کنیم
        چون DoT نیاز به پروکسی دارد (می‌توان بعداً با stubby یا dnscrypt-proxy ادغام کرد)
        """
        # TODO: پیاده‌سازی کامل DoT با استفاده از یک DNS-over-TLS proxy محلی
        # فعلاً یک پیام هشدار برمی‌گردانیم
        return False, "DoT direct system setting not supported yet. Use a local DoT proxy."

    def apply_dns_auto(self, dns_info: dict) -> tuple:
        """
        اعمال DNS بر اساس نوع (IPv4, DoH, LocalCF, DoT)
        dns_info: دیکشنری شامل name, primary, secondary, type, port, ...
        برمی‌گرداند: (success, error_message)
        """
        dns_type = dns_info.get("type", "IPv4")
        primary = dns_info.get("primary", "")
        secondary = dns_info.get("secondary", "")
        port = dns_info.get("port", 853)

        if dns_type == "IPv4":
            return self.apply_ipv4_dns(primary, secondary)
        elif dns_type == "LocalCF":
            success, err, _ = self.apply_local_cf_dns()
            return success, err
        elif dns_type == "DoH":
            success, err, _ = self.apply_doh_dns(primary)
            return success, err
        elif dns_type == "DoT":
            return self.apply_dot_dns(primary, port)
        else:
            return False, f"Unsupported DNS type: {dns_type}"

    # ------------------------------------------------------------------
    # قطع و پاکسازی
    # ------------------------------------------------------------------
    def reset_dns(self) -> tuple:
        """بازنشانی DNS سیستم به DHCP"""
        if not self.is_admin():
            return False, "Admin required"

        adapter = self.active_interface
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{adapter}" source=dhcp'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            self.current_dns = None
            self.log("DNS reset to DHCP")
            return True, None
        except Exception as e:
            return False, str(e)

    def stop_all_local_servers(self):
        """توقف تمام سرورهای DNS محلی"""
        if self.local_cf_server:
            self.local_cf_server.stop()
            self.local_cf_server = None
        if self.doh_server:
            self.doh_server.stop()
            self.doh_server = None
        if self.fake_dns_server:
            self.fake_dns_server.stop()
            self.fake_dns_server = None

    def disconnect(self) -> tuple:
        """
        قطع کامل اتصال DNS: بازنشانی سیستم + توقف سرورهای محلی
        برمی‌گرداند: (success, error_message)
        """
        success, err = self.reset_dns()
        self.stop_all_local_servers()
        return success, err

    # ------------------------------------------------------------------
    # مدیریت FakeDNS
    # ------------------------------------------------------------------
    def start_fake_dns(self, rules: dict = None) -> tuple:
        """
        راه‌اندازی FakeDNS Server (برای تست یا فریب)
        rules: دیکشنری {domain: fake_ip}
        """
        if self.fake_dns_server is None:
            self.fake_dns_server = FakeDNSServer()
        if rules:
            for domain, ip in rules.items():
                self.fake_dns_server.add_fake_rule(domain, ip)
        if self.fake_dns_server.start():
            self.log(f"FakeDNS started on {self.fake_dns_server.bound_ip}")
            return True, self.fake_dns_server.bound_ip
        return False, None

    def stop_fake_dns(self):
        if self.fake_dns_server:
            self.fake_dns_server.stop()
            self.fake_dns_server = None

    # ------------------------------------------------------------------
    # ابزارهای کمکی
    # ------------------------------------------------------------------
    def get_current_dns_info(self):
        """اطلاعات DNS فعلی سیستم را برمی‌گرداند (با خواندن از netsh)"""
        if not HAS_PSUTIL:
            return None
        try:
            adapter = self.active_interface
            cmd = f'netsh interface ipv4 show dnsservers name="{adapter}"'
            output = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW).stdout
            # پارس ساده خروجی
            servers = []
            for line in output.splitlines():
                if ":" in line and not "DHCP" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        addr = parts[-1].strip()
                        if addr and addr != "none":
                            servers.append(addr)
            return servers if servers else None
        except:
            return None

    def is_connected(self):
        """بررسی اینکه آیا DNS سفارشی فعال است (غیر از DHCP)"""
        servers = self.get_current_dns_info()
        return servers is not None and len(servers) > 0
