# tabs/dns/fake_dns.py
import socket
import threading
import struct
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor


class FakeDNSServer:
    """
    سرور DNS محلی برای برگرداندن پاسخ‌های جعلی (FakeDNS)
    کاربردها:
        - تست امنیت و نفوذ
        - مسدودسازی دامنه‌های مخرب (با برگرداندن IP جعلی)
        - هدایت ترافیک به سرور محلی
    ویژگی‌ها:
        - گوش دادن روی پورت 53 UDP (روی یک IP لوکال)
        - قابلیت تعریف قوانین دامنه -> IP جعلی (پشتیبانی از wildcard)
        - پاسخ NXDOMAIN برای دامنه‌های بدون قانون
        - کش ساده برای بهبود عملکرد
        - Thread-safe با ThreadPoolExecutor
    """

    def __init__(self, fake_rules: Optional[Dict[str, str]] = None):
        """
        Args:
            fake_rules: دیکشنری اولیه قوانین {domain: fake_ip}
        """
        self.fake_rules = fake_rules or {}
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.bound_ip: Optional[str] = None
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.cache: Dict[str, Tuple[float, bytes]] = {}
        self.cache_ttl = 60  # ثانیه

    def add_rule(self, domain: str, fake_ip: str) -> None:
        """
        افزودن یک قانون جدید
        Args:
            domain: دامنه مورد نظر (می‌تواند wildcard باشد مثل *.example.com)
            fake_ip: IP جعلی که باید برگردانده شود
        """
        self.fake_rules[domain] = fake_ip
        # پاک کردن کش برای این دامنه (در صورت وجود)
        if domain in self.cache:
            del self.cache[domain]

    def remove_rule(self, domain: str) -> bool:
        """
        حذف یک قانون
        Returns:
            True اگر قانون وجود داشت و حذف شد
        """
        if domain in self.fake_rules:
            del self.fake_rules[domain]
            if domain in self.cache:
                del self.cache[domain]
            return True
        return False

    def get_rules(self) -> Dict[str, str]:
        """دریافت تمام قوانین فعال"""
        return self.fake_rules.copy()

    def clear_rules(self) -> None:
        """حذف تمام قوانین"""
        self.fake_rules.clear()
        self.cache.clear()

    def _match_domain(self, domain: str) -> Optional[str]:
        """
        بررسی می‌کند که آیا دامنه با یکی از قوانین مطابقت دارد
        Returns:
            IP جعلی یا None
        """
        domain_lower = domain.lower()
        # ابتدا تطابق دقیق
        if domain_lower in self.fake_rules:
            return self.fake_rules[domain_lower]

        # سپس wildcard
        for pattern, ip in self.fake_rules.items():
            if pattern.startswith("*."):
                suffix = pattern[2:].lower()
                if domain_lower.endswith(suffix):
                    return ip

        return None

    def _parse_domain(self, data: bytes) -> Optional[str]:
        """
        استخراج نام دامنه از بسته DNS
        """
        try:
            offset = 12
            domain_parts = []
            while True:
                length = data[offset]
                if length == 0:
                    break
                offset += 1
                domain_parts.append(data[offset:offset+length].decode('ascii', errors='ignore'))
                offset += length
            return '.'.join(domain_parts)
        except Exception:
            return None

    def _build_dns_response(self, request_data: bytes, ip_to_return: str) -> bytes:
        """
        ساخت پاسخ DNS برای رکورد A
        """
        transaction_id = request_data[0:2]
        flags = b'\x81\x80'  # Standard query response, No error
        counts = struct.pack('>HHHH', 1, 1, 0, 0)
        question = request_data[12:]

        answer_name = b'\xc0\x0c'
        answer_type = struct.pack('>H', 1)  # Type A
        answer_class = struct.pack('>H', 1)  # Class IN
        ttl = struct.pack('>I', 60)  # TTL 60 ثانیه
        data_length = struct.pack('>H', 4)
        ip_bytes = socket.inet_aton(ip_to_return)

        answer = answer_name + answer_type + answer_class + ttl + data_length + ip_bytes
        return transaction_id + flags + counts + question + answer

    def _build_error_response(self, request_data: bytes, rcode: int = 3) -> bytes:
        """
        ساخت پاسخ DNS خطا (NXDOMAIN)
        """
        transaction_id = request_data[0:2]
        flags = struct.pack('>H', 0x8180 | rcode)
        counts = struct.pack('>HHHH', 1, 0, 0, 0)
        question = request_data[12:]
        return transaction_id + flags + counts + question

    def _handle_query(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        پردازش یک کوئری DNS
        """
        try:
            domain = self._parse_domain(data)
            if not domain:
                return

            # بررسی کش
            import time
            if domain in self.cache:
                cached_time, cached_response = self.cache[domain]
                if time.time() - cached_time < self.cache_ttl:
                    if self.sock:
                        self.sock.sendto(cached_response, addr)
                    return

            fake_ip = self._match_domain(domain)
            if fake_ip:
                response = self._build_dns_response(data, fake_ip)
                self.cache[domain] = (time.time(), response)
                if self.sock:
                    self.sock.sendto(response, addr)
            else:
                # اگر قانونی وجود نداشت، NXDOMAIN برگردان
                response = self._build_error_response(data, 3)
                if self.sock:
                    self.sock.sendto(response, addr)
        except Exception:
            pass

    def _listen_loop(self) -> None:
        """حلقه اصلی گوش دادن"""
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(512)
                if data:
                    self.executor.submit(self._handle_query, data, addr)
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    break

    def start(self) -> bool:
        """
        راه‌اندازی سرور FakeDNS
        Returns:
            True در صورت موفقیت
        """
        if self.running:
            return True

        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)

        # تلاش برای bind روی پورت 53
        for i in range(1, 15):
            ip = f'127.0.0.{i}'
            try:
                self.sock.bind((ip, 53))
                self.bound_ip = ip
                break
            except OSError:
                continue

        if not self.bound_ip:
            self.running = False
            self.sock.close()
            self.sock = None
            return False

        threading.Thread(target=self._listen_loop, daemon=True).start()
        return True

    def stop(self) -> None:
        """توقف سرور"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.executor.shutdown(wait=False)
        self.cache.clear()

    def is_running(self) -> bool:
        return self.running

    def get_bound_ip(self) -> Optional[str]:
        """دریافت IP که سرور روی آن bind شده"""
        return self.bound_ip

    def get_stats(self) -> Dict[str, any]:
        """دریافت آمار سرور"""
        return {
            "is_running": self.running,
            "bound_ip": self.bound_ip,
            "rules_count": len(self.fake_rules),
            "cache_size": len(self.cache)
        }
