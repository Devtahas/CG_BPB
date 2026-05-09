# tabs/client/mimicry/mimicry_profile.py
import json
import os
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TLSConfig:
    """تنظیمات لایه TLS"""
    ja3_fingerprint: str = ""                    # رشته JA3 کامل (در صورت استفاده از uTLS)
    ja4_fingerprint: str = ""                    # رشته JA4
    cipher_suites: List[str] = field(default_factory=list)
    extensions: List[str] = field(default_factory=list)
    alpn_protocols: List[str] = field(default_factory=lambda: ["h2", "http/1.1"])
    supported_versions: List[str] = field(default_factory=lambda: ["TLSv1.3", "TLSv1.2"])
    grease_enabled: bool = True
    record_size_limit: int = 16384               # حداکثر اندازه رکورد TLS
    server_name: str = ""                        # SNI


@dataclass
class HTTP2Config:
    """تنظیمات لایه HTTP/2"""
    settings_header_table_size: int = 4096
    settings_enable_push: int = 0
    settings_max_concurrent_streams: int = 100
    settings_initial_window_size: int = 65535
    settings_max_frame_size: int = 16384
    settings_max_header_list_size: int = 65536
    header_order: List[str] = field(default_factory=lambda: [
        ":method", ":path", ":authority", ":scheme",
        "user-agent", "accept", "accept-language", "accept-encoding"
    ])
    priority_frames_enabled: bool = False


@dataclass
class TrafficPattern:
    """تنظیمات الگوی ترافیک و تایمینگ"""
    packet_size_distribution: Dict[int, float] = field(default_factory=dict)  # size -> probability
    inter_arrival_min_ms: int = 5
    inter_arrival_max_ms: int = 50
    burst_probability: float = 0.3                 # احتمال ارسال خوشه‌ای
    burst_size_min: int = 3
    burst_size_max: int = 8
    silence_min_ms: int = 100
    silence_max_ms: int = 500
    jitter_enabled: bool = True
    padding_min_bytes: int = 0
    padding_max_bytes: int = 128
    bidirectional: bool = False                    # ترافیک همزمان رفت و برگشت


@dataclass
class HTTPHeaders:
    """تنظیمات هدرهای HTTP"""
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    accept_language: str = "en-US,en;q=0.5"
    accept_encoding: str = "gzip, deflate, br"
    sec_fetch_site: str = "none"
    sec_fetch_mode: str = "navigate"
    sec_fetch_dest: str = "document"
    connection: str = "keep-alive"
    dnt: str = ""                                  # "1" اگر فعال باشد


class MimicryProfile:
    """
    مدیریت پروفایل شبیه‌سازی ترافیک
    شامل تمام تنظیمات چهار لایه (TLS، HTTP/2، ترافیک، هدرها)
    """

    def __init__(self, profile_path: Optional[str] = None):
        self.name: str = "Default"
        self.description: str = ""
        self.tls: TLSConfig = TLSConfig()
        self.http2: HTTP2Config = HTTP2Config()
        self.traffic: TrafficPattern = TrafficPattern()
        self.headers: HTTPHeaders = HTTPHeaders()

        if profile_path:
            self.load(profile_path)

    def load(self, path: str) -> None:
        """بارگذاری پروفایل از فایل JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.name = data.get("name", os.path.basename(path))
        self.description = data.get("description", "")

        # TLS
        tls_data = data.get("tls", {})
        self.tls = TLSConfig(
            ja3_fingerprint=tls_data.get("ja3", ""),
            ja4_fingerprint=tls_data.get("ja4", ""),
            cipher_suites=tls_data.get("cipher_suites", []),
            extensions=tls_data.get("extensions", []),
            alpn_protocols=tls_data.get("alpn", ["h2", "http/1.1"]),
            supported_versions=tls_data.get("supported_versions", ["TLSv1.3", "TLSv1.2"]),
            grease_enabled=tls_data.get("grease", True),
            record_size_limit=tls_data.get("record_size_limit", 16384),
            server_name=tls_data.get("server_name", "")
        )

        # HTTP/2
        h2_data = data.get("http2", {})
        self.http2 = HTTP2Config(
            settings_header_table_size=h2_data.get("header_table_size", 4096),
            settings_enable_push=h2_data.get("enable_push", 0),
            settings_max_concurrent_streams=h2_data.get("max_concurrent_streams", 100),
            settings_initial_window_size=h2_data.get("initial_window_size", 65535),
            settings_max_frame_size=h2_data.get("max_frame_size", 16384),
            settings_max_header_list_size=h2_data.get("max_header_list_size", 65536),
            header_order=h2_data.get("header_order", [
                ":method", ":path", ":authority", ":scheme",
                "user-agent", "accept", "accept-language", "accept-encoding"
            ]),
            priority_frames_enabled=h2_data.get("priority_frames", False)
        )

        # Traffic Pattern
        traffic_data = data.get("traffic", {})
        self.traffic = TrafficPattern(
            packet_size_distribution=traffic_data.get("packet_sizes", {}),
            inter_arrival_min_ms=traffic_data.get("inter_arrival_min_ms", 5),
            inter_arrival_max_ms=traffic_data.get("inter_arrival_max_ms", 50),
            burst_probability=traffic_data.get("burst_probability", 0.3),
            burst_size_min=traffic_data.get("burst_size_min", 3),
            burst_size_max=traffic_data.get("burst_size_max", 8),
            silence_min_ms=traffic_data.get("silence_min_ms", 100),
            silence_max_ms=traffic_data.get("silence_max_ms", 500),
            jitter_enabled=traffic_data.get("jitter", True),
            padding_min_bytes=traffic_data.get("padding_min", 0),
            padding_max_bytes=traffic_data.get("padding_max", 128),
            bidirectional=traffic_data.get("bidirectional", False)
        )

        # HTTP Headers
        headers_data = data.get("headers", {})
        self.headers = HTTPHeaders(
            user_agent=headers_data.get("user_agent", self.headers.user_agent),
            accept=headers_data.get("accept", self.headers.accept),
            accept_language=headers_data.get("accept_language", self.headers.accept_language),
            accept_encoding=headers_data.get("accept_encoding", self.headers.accept_encoding),
            sec_fetch_site=headers_data.get("sec_fetch_site", "none"),
            sec_fetch_mode=headers_data.get("sec_fetch_mode", "navigate"),
            sec_fetch_dest=headers_data.get("sec_fetch_dest", "document"),
            connection=headers_data.get("connection", "keep-alive"),
            dnt=headers_data.get("dnt", "")
        )

    def save(self, path: str) -> None:
        """ذخیره پروفایل در فایل JSON"""
        data = {
            "name": self.name,
            "description": self.description,
            "tls": {
                "ja3": self.tls.ja3_fingerprint,
                "ja4": self.tls.ja4_fingerprint,
                "cipher_suites": self.tls.cipher_suites,
                "extensions": self.tls.extensions,
                "alpn": self.tls.alpn_protocols,
                "supported_versions": self.tls.supported_versions,
                "grease": self.tls.grease_enabled,
                "record_size_limit": self.tls.record_size_limit,
                "server_name": self.tls.server_name
            },
            "http2": {
                "header_table_size": self.http2.settings_header_table_size,
                "enable_push": self.http2.settings_enable_push,
                "max_concurrent_streams": self.http2.settings_max_concurrent_streams,
                "initial_window_size": self.http2.settings_initial_window_size,
                "max_frame_size": self.http2.settings_max_frame_size,
                "max_header_list_size": self.http2.settings_max_header_list_size,
                "header_order": self.http2.header_order,
                "priority_frames": self.http2.priority_frames_enabled
            },
            "traffic": {
                "packet_sizes": self.traffic.packet_size_distribution,
                "inter_arrival_min_ms": self.traffic.inter_arrival_min_ms,
                "inter_arrival_max_ms": self.traffic.inter_arrival_max_ms,
                "burst_probability": self.traffic.burst_probability,
                "burst_size_min": self.traffic.burst_size_min,
                "burst_size_max": self.traffic.burst_size_max,
                "silence_min_ms": self.traffic.silence_min_ms,
                "silence_max_ms": self.traffic.silence_max_ms,
                "jitter": self.traffic.jitter_enabled,
                "padding_min": self.traffic.padding_min_bytes,
                "padding_max": self.traffic.padding_max_bytes,
                "bidirectional": self.traffic.bidirectional
            },
            "headers": {
                "user_agent": self.headers.user_agent,
                "accept": self.headers.accept,
                "accept_language": self.headers.accept_language,
                "accept_encoding": self.headers.accept_encoding,
                "sec_fetch_site": self.headers.sec_fetch_site,
                "sec_fetch_mode": self.headers.sec_fetch_mode,
                "sec_fetch_dest": self.headers.sec_fetch_dest,
                "connection": self.headers.connection,
                "dnt": self.headers.dnt
            }
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_headers_dict(self) -> Dict[str, str]:
        """تبدیل هدرها به دیکشنری برای استفاده در درخواست HTTP"""
        headers = {
            "User-Agent": self.headers.user_agent,
            "Accept": self.headers.accept,
            "Accept-Language": self.headers.accept_language,
            "Accept-Encoding": self.headers.accept_encoding,
            "Sec-Fetch-Site": self.headers.sec_fetch_site,
            "Sec-Fetch-Mode": self.headers.sec_fetch_mode,
            "Sec-Fetch-Dest": self.headers.sec_fetch_dest,
            "Connection": self.headers.connection
        }
        if self.headers.dnt:
            headers["DNT"] = self.headers.dnt
        return headers

    def sample_packet_size(self) -> int:
        """نمونه‌گیری از توزیع اندازه بسته (در صورت تعریف)"""
        if not self.traffic.packet_size_distribution:
            return random.randint(512, 1500)  # مقدار پیش‌فرض
        sizes = list(self.traffic.packet_size_distribution.keys())
        probs = list(self.traffic.packet_size_distribution.values())
        return int(random.choices(sizes, weights=probs, k=1)[0])

    def sample_delay_ms(self) -> int:
        """نمونه‌گیری از توزیع تأخیر بین بسته‌ها"""
        return random.randint(self.traffic.inter_arrival_min_ms, self.traffic.inter_arrival_max_ms)

    def should_burst(self) -> bool:
        return random.random() < self.traffic.burst_probability

    def get_burst_size(self) -> int:
        return random.randint(self.traffic.burst_size_min, self.traffic.burst_size_max)

    def get_silence_ms(self) -> int:
        return random.randint(self.traffic.silence_min_ms, self.traffic.silence_max_ms)

    def get_padding_bytes(self) -> bytes:
        if self.traffic.padding_min_bytes >= self.traffic.padding_max_bytes:
            return b''
        size = random.randint(self.traffic.padding_min_bytes, self.traffic.padding_max_bytes)
        return os.urandom(size)
