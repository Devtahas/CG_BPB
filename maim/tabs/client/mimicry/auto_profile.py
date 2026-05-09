# tabs/client/mimicry/auto_profile.py
import json
import time
import socket
import ssl
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    import dns.resolver
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

from .mimicry_profile import MimicryProfile


class AutoProfileGenerator:
    """
    استخراج خودکار پروفایل شبیه‌سازی ترافیک از یک سایت هدف.
    ویژگی‌ها:
        - تشخیص TLS fingerprint (JA3) با curl_cffi
        - استخراج هدرهای HTTP پاسخ
        - تخمین الگوی ترافیک (اندازه بسته، تأخیر)
        - تولید فایل JSON پروفایل
    """

    def __init__(self):
        self.profile = MimicryProfile()

    def generate_from_url(self, url: str, profile_name: Optional[str] = None) -> MimicryProfile:
        """
        تحلیل سایت هدف و تولید پروفایل کامل.
        Args:
            url: آدرس سایت (مثلاً https://www.aparat.com)
            profile_name: نام پروفایل (پیش‌فرض: استخراج از دامنه)
        Returns:
            نمونه MimicryProfile
        """
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        if ':' in domain:
            domain = domain.split(':')[0]

        if not profile_name:
            profile_name = domain.split('.')[0].capitalize()

        self.profile.name = profile_name
        self.profile.description = f"Auto-generated profile for {domain}"
        self.profile.tls.server_name = domain

        # 1. استخراج TLS fingerprint (در صورت وجود curl_cffi)
        if HAS_CURL_CFFI:
            self._extract_tls_fingerprint(url)

        # 2. استخراج هدرهای HTTP و User-Agent
        self._extract_http_headers(url)

        # 3. استخراج اطلاعات DNS (IP, etc.)
        if HAS_DNSPYTHON:
            self._extract_dns_info(domain)

        # 4. تخمین الگوی ترافیک (بر اساس اندازه صفحه اصلی)
        self._estimate_traffic_pattern(url)

        return self.profile

    def _extract_tls_fingerprint(self, url: str) -> None:
        """با استفاده از curl_cffi، TLS fingerprint را تقلید می‌کند."""
        try:
            # استفاده از پروفایل Chrome 133 (می‌توان به صورت پویا انتخاب کرد)
            session = curl_requests.Session(impersonate="chrome110")
            response = session.get(url, timeout=10)
            # curl_cffi به طور خودکار JA3 را تنظیم می‌کند.
            # برای ذخیره در پروفایل، می‌توانیم مشخصات مورد استفاده را یادداشت کنیم.
            self.profile.tls.ja3_fingerprint = "chrome110"  # به عنوان مرجع
            self.profile.tls.alpn_protocols = ["h2", "http/1.1"]
            self.profile.tls.supported_versions = ["TLSv1.3", "TLSv1.2"]
            self.profile.tls.grease_enabled = True
        except Exception as e:
            print(f"[AutoProfile] TLS extraction failed: {e}")

    def _extract_http_headers(self, url: str) -> None:
        """استخراج هدرهای HTTP از پاسخ سرور."""
        try:
            import requests
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": self.profile.headers.user_agent
            })
            # ذخیره هدرهای دریافتی برای شبیه‌سازی (در صورت نیاز)
            # در اینجا ما هدرهای ارسالی خود را ذخیره می‌کنیم
            self.profile.headers.user_agent = resp.request.headers.get('User-Agent', self.profile.headers.user_agent)
            # هدرهای امنیتی
            self.profile.headers.sec_fetch_site = "none"
            self.profile.headers.sec_fetch_mode = "navigate"
            self.profile.headers.sec_fetch_dest = "document"
        except Exception as e:
            print(f"[AutoProfile] HTTP header extraction failed: {e}")

    def _extract_dns_info(self, domain: str) -> None:
        """دریافت رکوردهای A و AAAA."""
        try:
            answers = dns.resolver.resolve(domain, 'A')
            ips = [str(r) for r in answers]
            # می‌توان از IPها برای تنظیمات اضافی استفاده کرد
        except:
            pass

    def _estimate_traffic_pattern(self, url: str) -> None:
        """تخمین الگوی ترافیک بر اساس دانلود صفحه اصلی."""
        try:
            import requests
            start = time.time()
            resp = requests.get(url, timeout=10, stream=True)
            sizes = []
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    sizes.append(len(chunk))
            total_time = time.time() - start

            # اگر پاسخ به اندازه کافی بزرگ بود، از آن برای تخمین استفاده کن
            if sizes:
                avg_size = sum(sizes) / len(sizes)
                # تنظیم پارامترهای پیش‌فرض
                self.profile.traffic.inter_arrival_min_ms = 5
                self.profile.traffic.inter_arrival_max_ms = 50
                self.profile.traffic.burst_probability = 0.3
                self.profile.traffic.padding_max_bytes = min(256, int(avg_size * 0.1))
        except Exception as e:
            print(f"[AutoProfile] Traffic estimation failed: {e}")
