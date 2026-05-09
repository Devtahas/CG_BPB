# tabs/tools/whitelist_profiler.py

import asyncio
import socket
import time
import random
import ssl
import json
import os
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# ایمپورت‌های داخل پروژه (مسیرها رو چک کن)
from ..client.mimicry.mimicry_profile import MimicryProfile, TLSConfig, HTTPHeaders, HTTP2Config, TrafficPattern
from ..client.mimicry.mimicry_proxy import MimicryProxy  # فقط برای ارجاع، اینجا استفاده مستقیم نمیشه

# تلاش برای ایمپورت ابزارهای ضبط (Selenium + Scapy)
try:
    from ..client.mimicry.profile_recorder import ProfileRecorder
    RECORDER_AVAILABLE = True
except ImportError:
    RECORDER_AVAILABLE = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ========== لیست دامنه‌های معروف برای تست وایت‌لیست ==========
# ترکیبی از سایت‌های پربازدید ایرانی و خارجی که معمولاً در فیلترینگ وایت‌لیست هستند یا نیستند.
# هدف: پیدا کردن سایتی که واقعاً در شبکه کاربر بدون فیلتر باز می‌شود.
WHITELIST_CANDIDATES = [
    # سایت‌های داخلی پرمصرف
    "www.aparat.com",
    "www.digikala.com",
    "www.varzesh3.com",
    "www.namnak.com",
    "www.farsnews.ir",
    "www.yjc.ir",
    "www.isna.ir",
    "www.asriran.com",
    "www.tabnak.ir",
    # سایت‌های خارجی پراستفاده
    "www.google.com",
    "www.youtube.com",
    "www.wikipedia.org",
    "www.github.com",
    "www.stackoverflow.com",
    "www.amazon.com",
    "www.twitter.com",
    "www.instagram.com",
    "www.facebook.com",
    "www.cloudflare.com",
]

# پورت پیش‌فرض برای تست اتصال
DEFAULT_TEST_PORT = 443
# تایم‌اوت تست (ثانیه)
TEST_TIMEOUT = 3.0
# حداکثر تعداد کارگرهای همزمان برای تست
MAX_WORKERS = 15


class WhitelistProfiler:
    """
    دستیار هوشمند یافتن و ساخت پروفایل لیست‌سفید.
    این ابزار چند دامنهٔ معروف را تست می‌کند تا ببیند کدام‌ یک در شبکهٔ کاربر
    بدون فیلتر و با کمترین تأخیر در دسترس است، سپس یک MimicryProfile کامل
    از آن دامنه می‌سازد که برای PreProcessorProxy قابل استفاده است.
    """

    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: مسیر ذخیره پروفایل‌های ساخته‌شده. اگر None باشد،
                        از profiles_dir پیش‌فرض MimicryManager استفاده می‌شود.
        """
        if output_dir is None:
            # مسیر پیش‌فرض کنار سایر پروفایل‌ها
            from config import DIRS
            self.output_dir = os.path.join(DIRS["settings"], "mimicry_profiles")
        else:
            self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # تست اتصال ساده با TCP روی پورت ۴۴۳
    # ------------------------------------------------------------------
    def _test_reachability(self, domain: str, port: int = DEFAULT_TEST_PORT,
                           timeout: float = TEST_TIMEOUT) -> Tuple[bool, float]:
        """
        بررسی می‌کند که آیا یک دامنه در دسترس است یا خیر.
        برمی‌گرداند: (accessible, latency_ms)
        """
        try:
            # تبدیل دامنه به IP (برای جلوگیری از تأخیر DNS در تست)
            ip = socket.gethostbyname(domain)
            start = time.time()
            with socket.create_connection((ip, 443), timeout=timeout):
                latency = (time.time() - start) * 1000.0
            return True, latency
        except Exception:
            return False, 0.0

    # ------------------------------------------------------------------
    # پیدا کردن بهترین دامنهٔ در دسترس
    # ------------------------------------------------------------------
    def find_best_whitelist_domain(self, custom_domains: List[str] = None) -> Optional[Dict[str, any]]:
        """
        لیستی از دامنه‌ها (پیش‌فرض WHITELIST_CANDIDATES) را تست می‌کند و
        بهترین دامنهٔ در دسترس (کمترین پینگ) را برمی‌گرداند.

        Returns:
            {
                "domain": str,
                "latency_ms": float,
                "accessible": bool
            } یا None اگر هیچ دامنه‌ای در دسترس نباشد.
        """
        domains = custom_domains or WHITELIST_CANDIDATES
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self._test_reachability, d): d for d in domains}
            for future in as_completed(futures):
                domain = futures[future]
                try:
                    accessible, latency = future.result()
                    if accessible:
                        results.append({
                            "domain": domain,
                            "latency_ms": latency,
                            "accessible": True
                        })
                except Exception:
                    pass

        if not results:
            return None
        # مرتب‌سازی بر اساس کمترین تأخیر
        results.sort(key=lambda x: x["latency_ms"])
        return results[0]

    # ------------------------------------------------------------------
    # ساخت پروفایل از یک دامنه (با اولویت ضبط کامل)
    # ------------------------------------------------------------------
    def create_profile_for_domain(self, domain: str,
                                 profile_name: str = None,
                                 use_recorder: bool = True,
                                 record_duration: int = 30) -> Optional[MimicryProfile]:
        """
        یک MimicryProfile کامل برای دامنهٔ داده‌شده می‌سازد.
        اگر use_recorder=True و ابزارهای Selenium/Scapy در دسترس باشند،
        ابتدا سعی می‌کند یک ضبط کامل ۳۰ ثانیه‌ای (یا مدت دلخواه) انجام دهد.
        در غیر این صورت، با استفاده از AutoProfileGenerator (اگر موجود باشد)
        یا حداقل با استخراج TLS/HTTP Headers یک پروفایل پایه می‌سازد.

        Args:
            domain: مثلاً "www.aparat.com"
            profile_name: نام فایل پروفایل (بدون پسوند). اگر None باشد،
                         از خود domain استخراج می‌شود.
            use_recorder: آیا ابتدا ProfileRecorder امتحان شود؟
            record_duration: مدت زمان ضبط به ثانیه (فقط اگر recorder استفاده شود).

        Returns:
            نمونه MimicryProfile یا None در صورت شکست.
        """
        if not domain:
            return None

        if not profile_name:
            # تبدیل دامنه به یک نام مناسب
            profile_name = domain.replace("www.", "").split('.')[0].capitalize()

        # 1. تلاش برای ضبط کامل با Selenium+Scapy
        if use_recorder and RECORDER_AVAILABLE:
            try:
                recorder = ProfileRecorder()
                url = f"https://{domain}" if not domain.startswith("http") else domain
                profile = recorder.record(
                    url=url,
                    profile_name=profile_name,
                    output_dir=self.output_dir,
                    duration=record_duration
                )
                if profile:
                    return profile
            except Exception as e:
                print(f"[WhitelistProfiler] Recorder failed: {e}, falling back.")

        # 2. تلاش با AutoProfileGenerator (جایگزین سبک)
        try:
            from ..client.mimicry.auto_profile import AutoProfileGenerator
            gen = AutoProfileGenerator()
            return gen.generate_from_url(f"https://{domain}", profile_name)
        except ImportError:
            pass

        # 3. ساخت یک پروفایل حداقلی با اطلاعات TLS و HTTP Headers
        return self._build_minimal_profile(domain, profile_name)

    # ------------------------------------------------------------------
    # ساخت پروفایل حداقلی (بدون نیاز به کتابخانه‌های خارجی)
    # ------------------------------------------------------------------
    def _build_minimal_profile(self, domain: str, profile_name: str) -> Optional[MimicryProfile]:
        """یک MimicryProfile پایه با حداقل اطلاعات لازم می‌سازد."""
        profile = MimicryProfile()
        profile.name = profile_name
        profile.description = f"Minimal whitelist profile for {domain}"

        # استخراج اطلاعات TLS (در صورت امکان)
        tls_info = self._grab_tls_info(domain)
        if tls_info:
            profile.tls.ja3_fingerprint = ""  # در این حالت فینگرپرینت خودکار توسط uTLS تنظیم می‌شود
            profile.tls.server_name = domain
            profile.tls.alpn_protocols = tls_info.get("alpn", ["h2", "http/1.1"])
            profile.tls.supported_versions = tls_info.get("versions", ["TLSv1.3", "TLSv1.2"])
            profile.tls.cipher_suites = tls_info.get("ciphers", [])
        else:
            # تنظیمات پیش‌فرض منطبق بر Chrome
            profile.tls.ja3_fingerprint = ""
            profile.tls.server_name = domain
            profile.tls.alpn_protocols = ["h2", "http/1.1"]
            profile.tls.supported_versions = ["TLSv1.3", "TLSv1.2"]
            profile.tls.grease_enabled = True

        # هدرهای HTTP پیش‌فرض
        profile.headers = HTTPHeaders(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            accept_language="fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            accept_encoding="gzip, deflate, br",
            sec_fetch_site="none",
            sec_fetch_mode="navigate",
            sec_fetch_dest="document",
            connection="keep-alive"
        )

        # تنظیمات HTTP/2
        profile.http2 = HTTP2Config(
            settings_header_table_size=4096,
            settings_enable_push=0,
            settings_max_concurrent_streams=100,
            settings_initial_window_size=65535,
            settings_max_frame_size=16384,
            settings_max_header_list_size=65536,
            header_order=[
                ":method", ":path", ":authority", ":scheme",
                "user-agent", "accept", "accept-language", "accept-encoding"
            ],
            priority_frames_enabled=False
        )

        # الگوی ترافیک معقول
        profile.traffic = TrafficPattern(
            packet_size_distribution={},
            inter_arrival_min_ms=10,
            inter_arrival_max_ms=80,
            burst_probability=0.4,
            burst_size_min=3,
            burst_size_max=8,
            silence_min_ms=200,
            silence_max_ms=1000,
            jitter_enabled=True,
            padding_min_bytes=0,
            padding_max_bytes=128,
            bidirectional=False
        )

        # ذخیره پروفایل
        dest_path = os.path.join(self.output_dir, f"{profile_name}.json")
        try:
            profile.save(dest_path)
        except Exception:
            return None
        return profile

    # ------------------------------------------------------------------
    # استخراج اطلاعات TLS از دامنه (اختیاری، بدون کتابخانه خارجی)
    # ------------------------------------------------------------------
    def _grab_tls_info(self, domain: str) -> Optional[Dict[str, any]]:
        """با اتصال مستقیم TLS اطلاعات اولیه را جمع‌آوری می‌کند."""
        try:
            context = ssl.create_default_context()
            # غیرفعال کردن بررسی گواهی برای تست
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    # دریافت نسخه TLS استفاده شده
                    version = ssock.version()  # مثلاً 'TLSv1.3'
                    ciphers = [ssock.cipher()[0]] if ssock.cipher() else []
                    alpn = ssock.selected_alpn_protocol()
                    return {
                        "versions": [version] if version else ["TLSv1.3"],
                        "ciphers": ciphers,
                        "alpn": [alpn] if alpn else ["h2", "http/1.1"]
                    }
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # روند کامل: پیدا کردن بهترین دامنه و ساخت پروفایل
    # ------------------------------------------------------------------
    def run_full_profiling(self, profile_name: str = "AutoWhitelist") -> Optional[MimicryProfile]:
        """
        متد اصلی: بهترین دامنهٔ در دسترس را پیدا می‌کند و یک پروفایل کامل از آن می‌سازد.
        """
        best = self.find_best_whitelist_domain()
        if not best:
            return None
        return self.create_profile_for_domain(best["domain"], profile_name)
