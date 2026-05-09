# tabs/client/mimicry/profile_recorder.py
import os
import time
import threading
import random
import json
import hashlib
import struct
from collections import defaultdict
from typing import Optional, Dict, Any, List, Tuple

# ---------- وابستگی‌های اصلی ----------
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from scapy.all import sniff, IP, TCP, Raw, conf, AsyncSniffer
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from .mimicry_profile import MimicryProfile, TrafficPattern, TLSConfig, HTTPHeaders, HTTP2Config


class ProfileRecorder:
    """
    ضبط کننده حرفه‌ای ترافیک برای ساخت پروفایل شبیه‌سازی دقیق.
    مدت زمان پیش‌فرض ۶۰۰ ثانیه (۱۰ دقیقه) با مرورگر واقعی Chrome.
    تمام ویژگی‌های ترافیک (اندازه بسته، زمانبندی، JA3 و ...) استخراج می‌شود.
    """

    # ---------- تنظیمات پیش‌فرض ----------
    DEFAULT_DURATION = 600                # ۱۰ دقیقه
    DEFAULT_SCROLL_INTERVAL = (3, 8)      # محدوده تصادفی اسکرول (ثانیه)
    MAX_BURST_INTERVAL = 0.1              # حداکثر فاصله برای تشخیص burst (ثانیه)
    MIN_SILENCE = 0.2                     # حداقل سکوت برای ثبت (ثانیه)
    PACKET_BIN_SIZE = 512                 # اندازه هر bin برای توزیع بسته‌ها

    def __init__(self):
        self.running = False
        self.packets = []                  # بسته‌های ضبط شده
        self.capture_thread = None
        self.target_host = None

    # -----------------------------------------------------------------
    # متد اصلی ضبط
    # -----------------------------------------------------------------
    def record(self,
               url: str,
               profile_name: str,
               output_dir: str,
               duration: int = DEFAULT_DURATION) -> Optional[MimicryProfile]:
        """
        شروع ضبط ۱۰ دقیقه‌ای از یک سایت.

        Args:
            url: آدرس کامل سایت (با http/https)
            profile_name: نام پروفایل خروجی
            output_dir: پوشه مقصد برای ذخیره فایل JSON پروفایل
            duration: مدت زمان ضبط به ثانیه (پیش‌فرض ۶۰۰)

        Returns:
            نمونه MimicryProfile کامل یا None در صورت خطا
        """
        if not SELENIUM_AVAILABLE or not SCAPY_AVAILABLE:
            print("[ProfileRecorder] Missing dependencies (selenium/scapy).")
            return None

        # استخراج hostname برای فیلتر sniff
        from urllib.parse import urlparse
        parsed = urlparse(url)
        self.target_host = parsed.hostname
        if not self.target_host:
            print("[ProfileRecorder] Invalid URL.")
            return None

        # راه‌اندازی مرورگر
        driver = self._create_driver()
        if not driver:
            return None

        # شروع ضبط ترافیک در thread جدا
        self.packets = []
        capture_stopper = threading.Event()
        sniff_thread = threading.Thread(
            target=self._start_capture,
            args=(capture_stopper,),
            daemon=True
        )
        sniff_thread.start()
        time.sleep(1)   # کمی صبر برای شروع اسنیفر

        # شبیه‌سازی رفتار کاربر به مدت duration ثانیه
        start_time = time.time()
        try:
            driver.get(url)
            while time.time() - start_time < duration:
                self._human_like_interaction(driver)
                time.sleep(random.uniform(*self.DEFAULT_SCROLL_INTERVAL))
        except Exception as e:
            print(f"[ProfileRecorder] Browser error: {e}")
            driver.quit()
            capture_stopper.set()
            sniff_thread.join(timeout=5)
            return None

        # اتمام ضبط
        driver.quit()
        capture_stopper.set()
        sniff_thread.join(timeout=10)

        # تحلیل بسته‌های ضبط شده
        return self._analyze_and_build_profile(profile_name, url, output_dir)

    # -----------------------------------------------------------------
    # راه‌اندازی Chrome headless با گزینه‌های مناسب
    # -----------------------------------------------------------------
    def _create_driver(self):
        options = Options()
        options.add_argument("--headless=new")        # مخفی
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # تنظیم User-Agent واقعی Chrome 133
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    # -----------------------------------------------------------------
    # ضبط بسته‌ها با Scapy (غیرهمزمان)
    # -----------------------------------------------------------------
    def _start_capture(self, stop_event: threading.Event):
        """در یک thread جداگانه بسته‌ها را ضبط می‌کند"""
        try:
            # sniff تا زمانی که stop_event فعال شود
            sniff(
                filter=f"host {self.target_host}",
                prn=self._store_packet,
                store=False,
                stop_filter=lambda x: stop_event.is_set()
            )
        except Exception as e:
            print(f"[ProfileRecorder] Capture error: {e}")

    def _store_packet(self, pkt):
        """ذخیره بسته برای تحلیل بعدی (فقط IP/TCP)"""
        if IP in pkt and TCP in pkt:
            self.packets.append(pkt)

    # -----------------------------------------------------------------
    # تعاملات شبیه انسان (اسکرول، کلیک، توقف)
    # -----------------------------------------------------------------
    def _human_like_interaction(self, driver):
        """شبیه‌سازی رفتار کاربر: اسکرول تصادفی، کلیک روی لینک‌ها"""
        try:
            # اسکرول تصادفی
            scroll_y = random.randint(100, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")

            # کلیک تصادفی روی یک لینک معتبر
            if random.random() < 0.3:  # ۳۰٪ احتمال
                links = driver.find_elements(By.TAG_NAME, "a")
                if links:
                    link = random.choice(links)
                    try:
                        # کلیک با ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(link).click().perform()
                        driver.back()  # برگرد به صفحه اصلی
                    except:
                        pass

            # توقف کوتاه تصادفی (شبیه خواندن محتوا)
            if random.random() < 0.1:
                time.sleep(random.uniform(2, 5))
        except Exception:
            pass

    # -----------------------------------------------------------------
    # تحلیل بسته‌ها و ساخت MimicryProfile
    # -----------------------------------------------------------------
    def _analyze_and_build_profile(self,
                                   name: str,
                                   url: str,
                                   output_dir: str) -> MimicryProfile:
        """استخراج تمام ویژگی‌های ترافیکی از بسته‌های ضبط شده"""
        profile = MimicryProfile()
        profile.name = name
        profile.description = f"10-minute recorded profile for {url}"

        # فیلتر بسته‌های خروجی (از ما به سرور)
        out_packets = [p for p in self.packets
                       if p[IP].src != self.target_host]
        if not out_packets:
            print("[ProfileRecorder] No outgoing packets captured.")
            return profile

        # ---- ۱. توزیع اندازه بسته ----
        sizes = [len(p) for p in out_packets]
        bins = range(0, max(sizes) + 2, self.PACKET_BIN_SIZE)
        hist, _ = np.histogram(sizes, bins=bins)
        total = len(sizes)
        dist = {}
        for i, count in enumerate(hist):
            if count > 0:
                bin_center = (bins[i] + bins[i+1]) // 2
                dist[int(bin_center)] = round(count / total, 4)
        profile.traffic.packet_size_distribution = dist

        # ---- ۲. زمان‌بندی بین بسته‌ها (Inter-arrival) ----
        times = [p.time for p in out_packets]
        deltas = [times[i+1] - times[i] for i in range(len(times)-1)]
        if deltas:
            profile.traffic.inter_arrival_min_ms = int(min(deltas) * 1000)
            profile.traffic.inter_arrival_max_ms = int(max(deltas) * 1000)

        # ---- ۳. تشخیص Burst ----
        bursts = self._detect_bursts(times, self.MAX_BURST_INTERVAL)
        if bursts:
            burst_sizes = [len(b) for b in bursts]
            profile.traffic.burst_probability = len(bursts) / len(out_packets)
            profile.traffic.burst_size_min = min(burst_sizes)
            profile.traffic.burst_size_max = max(burst_sizes)
        else:
            # پیش‌فرض
            profile.traffic.burst_probability = 0.0
            profile.traffic.burst_size_min = 1
            profile.traffic.burst_size_max = 1

        # ---- ۴. دوره‌های سکوت ----
        silences = [d for d in deltas if d >= self.MIN_SILENCE]
        if silences:
            profile.traffic.silence_min_ms = int(min(silences) * 1000)
            profile.traffic.silence_max_ms = int(max(silences) * 1000)
        else:
            profile.traffic.silence_min_ms = 200
            profile.traffic.silence_max_ms = 1000

        # ---- ۵. استخراج JA3 از ClientHello ----
        ja3 = self._extract_ja3()
        profile.tls.ja3_fingerprint = ja3 if ja3 else ""

        # ---- ۶. تنظیم TLS server_name ----
        profile.tls.server_name = self.target_host

        # ---- ۷. هدرهای HTTP پیش‌فرض Chrome ----
        profile.headers = HTTPHeaders(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            accept_language="en-US,en;q=0.9",
            accept_encoding="gzip, deflate, br",
            sec_fetch_site="none",
            sec_fetch_mode="navigate",
            sec_fetch_dest="document",
            connection="keep-alive",
            dnt=""
        )

        # ذخیره در فایل
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{name}.json")
        profile.save(path)
        return profile

    # -----------------------------------------------------------------
    # تشخیص Burst (توالی بسته‌های نزدیک‌به‌هم)
    # -----------------------------------------------------------------
    def _detect_bursts(self, timestamps, max_interval):
        bursts = []
        current_burst = [timestamps[0]]
        for i in range(1, len(timestamps)):
            if timestamps[i] - timestamps[i-1] <= max_interval:
                current_burst.append(timestamps[i])
            else:
                if len(current_burst) >= 2:
                    bursts.append(current_burst)
                current_burst = [timestamps[i]]
        if len(current_burst) >= 2:
            bursts.append(current_burst)
        return bursts

    # -----------------------------------------------------------------
    # استخراج JA3 از اولین ClientHello در بسته‌های ضبط شده
    # -----------------------------------------------------------------
    def _extract_ja3(self) -> Optional[str]:
        """
        جستجوی بسته TLS ClientHello و محاسبه JA3.
        بر اساس مشخصات JA3: MD5(SSLVersion,Ciphers,Extensions,EllipticCurves,EllipticCurvePointFormats)
        """
        for pkt in self.packets:
            if TCP in pkt and Raw in pkt:
                payload = bytes(pkt[Raw])
                if len(payload) < 50:
                    continue
                # TLS record header: ContentType (1 byte) | Version (2) | Length (2)
                if payload[0] == 0x16:     # Handshake
                    # TLS version و طول رکورد
                    record_len = struct.unpack('!H', payload[3:5])[0]
                    if len(payload) - 5 < record_len:
                        continue
                    handshake = payload[5:5+record_len]
                    if handshake[0] == 0x01:   # ClientHello
                        return self._compute_ja3(handshake)
        # fallback: fingerprint Chrome 133 اگر پیدا نشد
        return None

    def _compute_ja3(self, client_hello: bytes) -> str:
        """
        تجزیه ClientHello و تولید هش JA3.
        ساختار ساده شده:
          - skip Handshake Type (1) + Length (3)
          - Version (2)
          - Random (32)
          - Session ID length (1) + Session ID
          - Cipher Suites length (2) + Cipher Suites
          - Compression Methods length (1) + Compression Methods
          - Extensions Length (2) + Extensions
        """
        offset = 44   # بعد از Session ID (فرض می‌کنیم Session ID خالی است)
        # Cipher Suites
        cs_len = struct.unpack('!H', client_hello[offset:offset+2])[0]
        offset += 2
        ciphers = client_hello[offset:offset+cs_len]
        offset += cs_len
        # Compression Methods
        comp_len = client_hello[offset]
        offset += 1 + comp_len
        # Extensions
        ext_len = struct.unpack('!H', client_hello[offset:offset+2])[0]
        offset += 2
        extensions_data = client_hello[offset:offset+ext_len]

        # استخراج cipher suite IDs (هر کدام ۲ بایت)
        cipher_list = []
        for i in range(0, cs_len, 2):
            cipher_list.append(str(struct.unpack('!H', ciphers[i:i+2])[0]))

        # استخراج extension types (هر extension: type(2) + length(2) + data)
        ext_types = []
        ext_pos = 0
        while ext_pos < len(extensions_data):
            if ext_pos + 4 > len(extensions_data):
                break
            ext_type = struct.unpack('!H', extensions_data[ext_pos:ext_pos+2])[0]
            ext_len = struct.unpack('!H', extensions_data[ext_pos+2:ext_pos+4])[0]
            ext_types.append(str(ext_type))
            ext_pos += 4 + ext_len

        # Elliptic Curves و Point Formats (اختیاری، برای سادگی نادیده می‌گیریم)
        ja3_str = f"771,{','.join(cipher_list)},{','.join(ext_types)},,"
        ja3_hash = hashlib.md5(ja3_str.encode()).hexdigest()
        return ja3_hash
