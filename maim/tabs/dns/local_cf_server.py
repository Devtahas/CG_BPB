# tabs/dns/local_cf_server.py
import socket
import threading
import time
import random
import struct
import ipaddress
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

# رنج‌های IP کلادفلر (بخشی از لیست کامل)
CLOUDFLARE_CIDRS = [
    "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "104.16.0.0/13",
    "104.24.0.0/14", "108.162.192.0/18", "131.0.72.0/22", "141.101.64.0/18",
    "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
    "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "8.238.64.0/18", "8.242.72.0/21", "8.243.216.0/21", "45.188.16.0/22",
]

# لیست دامنه‌های کلادفلر و سرویس‌های مرتبط
CLOUDFLARE_DOMAINS = [
    "cloudflare.com", "*.cloudflare.com",
    "workers.dev", "*.workers.dev",
    "pages.dev", "*.pages.dev",
    "cloudflare-dns.com",
    "speed.cloudflare.com",
    "cp.cloudflare.com",
    "cloudflareinsights.com",
    "cloudflare.net", "*.cloudflare.net",
]


class LocalCloudflareDNSServer:
    """
    سرور DNS محلی برای دامنه‌های کلادفلر
    ویژگی‌ها:
        - گوش دادن روی یک IP لوکال (127.0.0.x) روی پورت 53 UDP
        - تشخیص دامنه‌های کلادفلر (با پشتیبانی از wildcard)
        - برگرداندن IP تصادفی از رنج‌های کلادفلر
        - کش کردن پاسخ‌ها با TTL
        - قابلیت شروع و توقف
        - Thread-safe با ThreadPoolExecutor
    """

    def __init__(self, custom_cf_ips: Optional[List[str]] = None):
        """
        Args:
            custom_cf_ips: لیست IPهای سفارشی کلادفلر (اگر None باشد از رنج‌های پیش‌فرض استفاده می‌شود)
        """
        self.custom_cf_ips = custom_cf_ips or []
        self.cf_domains = CLOUDFLARE_DOMAINS.copy()
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.bound_ip: Optional[str] = None
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.cache: Dict[str, Tuple[float, bytes]] = {}  # domain -> (timestamp, response_bytes)
        self.cache_ttl = 300  # ثانیه

        # استخراج IPها از رنج‌ها
        self.cf_ip_pool = self._extract_ips_from_cidrs()

    def _extract_ips_from_cidrs(self) -> List[str]:
        """استخراج نمونه‌هایی از IPها از رنج‌های CIDR کلادفلر"""
        ips = []
        for cidr in CLOUDFLARE_CIDRS:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                # تعداد نمونه‌ها متناسب با اندازه رنج (حداکثر ۲۰)
                sample_count = min(20, max(5, net.num_addresses // 500))
                for i in range(sample_count):
                    if net.num_addresses > i:
                        ips.append(str(net[i]))
                    else:
                        ips.append(str(net[random.randint(0, net.num_addresses - 1)]))
            except Exception:
                pass

        # اضافه کردن IPهای معروف کلادفلر
        default_ips = [
            "188.114.96.0", "188.114.97.0", "188.114.98.0", "188.114.99.0",
            "162.159.192.0", "162.159.193.0", "162.159.195.0", "162.159.200.0",
            "104.16.0.0", "104.17.0.0", "104.18.0.0", "104.19.0.0",
            "172.64.0.0", "172.65.0.0", "172.66.0.0", "172.67.0.0"
        ]
        ips.extend(default_ips)

        # حذف تکراری‌ها
        return list(set(ips))

    def add_custom_ip(self, ip: str) -> None:
        """افزودن یک IP سفارشی به لیست"""
        if ip not in self.custom_cf_ips:
            self.custom_cf_ips.append(ip)

    def add_cf_domain(self, domain: str) -> None:
        """افزودن یک دامنه به لیست دامنه‌های کلادفلر (می‌تواند wildcard باشد)"""
        if domain not in self.cf_domains:
            self.cf_domains.append(domain)

    def is_cf_domain(self, domain: str) -> bool:
        """بررسی اینکه آیا دامنه مورد نظر کلادفلری است یا خیر"""
        domain_lower = domain.lower()
        for cf_domain in self.cf_domains:
            if cf_domain.startswith("*."):
                suffix = cf_domain[2:]
                if domain_lower.endswith(suffix):
                    return True
            elif domain_lower == cf_domain or domain_lower.endswith("." + cf_domain):
                return True
        return False

    def get_cf_ip(self) -> str:
        """برگرداندن یک IP تصادفی از لیست کلادفلر"""
        if self.custom_cf_ips:
            return random.choice(self.custom_cf_ips)
        if self.cf_ip_pool:
            return random.choice(self.cf_ip_pool)
        return "188.114.96.0"  # fallback

    def _build_dns_response(self, request_data: bytes, ip_to_return: str) -> bytes:
        """
        ساخت پاسخ DNS برای رکورد A
        Args:
            request_data: بسته DNS دریافتی
            ip_to_return: IP که باید برگردانده شود
        Returns:
            پاسخ DNS کامل
        """
        transaction_id = request_data[0:2]
        flags = b'\x81\x80'  # Standard query response, No error
        counts = struct.pack('>HHHH', 1, 1, 0, 0)  # QDCOUNT=1, ANCOUNT=1, NSCOUNT=0, ARCOUNT=0
        question = request_data[12:]  # بخش Question اصلی

        # ساخت Answer Section
        answer_name = b'\xc0\x0c'  # Pointer به نام دامنه در Question
        answer_type = struct.pack('>H', 1)  # Type A
        answer_class = struct.pack('>H', 1)  # Class IN
        ttl = struct.pack('>I', 300)  # TTL 300 ثانیه
        data_length = struct.pack('>H', 4)  # طول داده (4 بایت برای IPv4)
        ip_bytes = socket.inet_aton(ip_to_return)

        answer = answer_name + answer_type + answer_class + ttl + data_length + ip_bytes
        return transaction_id + flags + counts + question + answer

    def _build_error_response(self, request_data: bytes, rcode: int = 3) -> bytes:
        """
        ساخت پاسخ DNS خطا (NXDOMAIN)
        Args:
            request_data: بسته DNS دریافتی
            rcode: کد خطا (3 = NXDOMAIN)
        """
        transaction_id = request_data[0:2]
        flags = struct.pack('>H', 0x8180 | rcode)  # Response + rcode
        counts = struct.pack('>HHHH', 1, 0, 0, 0)
        question = request_data[12:]
        return transaction_id + flags + counts + question

    def _parse_domain(self, data: bytes) -> Optional[str]:
        """
        استخراج نام دامنه از بسته DNS
        Args:
            data: بسته DNS
        Returns:
            نام دامنه یا None در صورت خطا
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

    def _handle_query(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        پردازش یک کوئری DNS
        Args:
            data: بسته DNS دریافتی
            addr: آدرس فرستنده (IP, port)
        """
        try:
            domain = self._parse_domain(data)
            if not domain:
                return

            # بررسی کش
            if domain in self.cache:
                cached_time, cached_response = self.cache[domain]
                if time.time() - cached_time < self.cache_ttl:
                    if self.sock:
                        self.sock.sendto(cached_response, addr)
                    return

            # تشخیص دامنه کلادفلر
            if self.is_cf_domain(domain):
                cf_ip = self.get_cf_ip()
                response = self._build_dns_response(data, cf_ip)
                # ذخیره در کش
                self.cache[domain] = (time.time(), response)
                if self.sock:
                    self.sock.sendto(response, addr)
            else:
                # دامنه غیر کلادفلر -> NXDOMAIN
                response = self._build_error_response(data, 3)
                if self.sock:
                    self.sock.sendto(response, addr)
        except Exception:
            pass

    def _listen_loop(self) -> None:
        """حلقه اصلی گوش دادن به درخواست‌ها"""
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(512)  # حداکثر ۵۱۲ بایت برای DNS
                if data:
                    self.executor.submit(self._handle_query, data, addr)
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    break

    def start(self) -> bool:
        """
        راه‌اندازی سرور DNS محلی
        Returns:
            True در صورت موفقیت، False در غیر این صورت
        """
        if self.running:
            return True

        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)

        # تلاش برای bind روی پورت 53 روی IPهای 127.0.0.x
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

        # شروع ترد گوش‌دهنده
        threading.Thread(target=self._listen_loop, daemon=True).start()
        return True

    def stop(self) -> None:
        """توقف سرور DNS محلی"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.executor.shutdown(wait=False)
        self.cache.clear()

    def get_stats(self) -> Dict[str, any]:
        """
        دریافت آمار سرور
        Returns:
            دیکشنری شامل:
                - cf_ips_count: تعداد IPهای کلادفلر موجود
                - cache_size: تعداد رکوردهای کش
                - bound_ip: IP که سرور روی آن bind شده
                - is_running: وضعیت اجرا
                - custom_ips_count: تعداد IPهای سفارشی
        """
        return {
            "cf_ips_count": len(self.cf_ip_pool),
            "cache_size": len(self.cache),
            "bound_ip": self.bound_ip,
            "is_running": self.running,
            "custom_ips_count": len(self.custom_cf_ips),
        }

    def clear_cache(self) -> None:
        """پاکسازی کش"""
        self.cache.clear()

    def is_running(self) -> bool:
        return self.running
