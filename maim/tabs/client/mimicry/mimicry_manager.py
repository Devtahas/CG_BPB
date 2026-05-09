# tabs/client/mimicry/mimicry_manager.py
import os
import threading
import json
from typing import Optional, List, Dict, Any

from config import DIRS, storage_crypto
from .mimicry_profile import MimicryProfile, TLSConfig, HTTP2Config, TrafficPattern, HTTPHeaders
from .mimicry_proxy import MimicryProxy


class MimicryManager:
    """
    مدیریت چرخه حیات پراکسی Traffic Mimicry
    - بارگذاری/ذخیره پروفایل‌ها
    - اجرا/توقف پراکسی
    - یکپارچه‌سازی با ClientCore
    - تولید خودکار پروفایل از URL (Auto-Profile)
    """

    def __init__(self):
        self.profiles_dir = os.path.join(DIRS["settings"], "mimicry_profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)

        self.current_profile: Optional[MimicryProfile] = None
        self.proxy: Optional[MimicryProxy] = None
        self.enabled = False
        self.proxy_host = "127.0.0.1"
        self.proxy_port = 10810
        self._lock = threading.Lock()

        # ایجاد پروفایل‌های پیش‌فرض در صورت عدم وجود
        self._create_default_profiles()

    def _create_default_profiles(self) -> None:
        """ایجاد پروفایل‌های پیش‌فرض (آپارات، یوتیوب، دیسکورد) با تمام جزئیات"""
        defaults: Dict[str, Dict[str, Any]] = {
            "aparat.json": {
                "name": "Aparat",
                "description": "Mimic Aparat video streaming traffic - Persian video sharing",
                "tls": {
                    "ja3": "",
                    "ja4": "",
                    "cipher_suites": [
                        "TLS_AES_128_GCM_SHA256",
                        "TLS_AES_256_GCM_SHA384",
                        "TLS_CHACHA20_POLY1305_SHA256"
                    ],
                    "extensions": [
                        "server_name", "supported_groups", "key_share",
                        "signature_algorithms", "supported_versions", "psk_key_exchange_modes"
                    ],
                    "alpn": ["h2", "http/1.1"],
                    "supported_versions": ["TLSv1.3", "TLSv1.2"],
                    "grease": True,
                    "record_size_limit": 16384,
                    "server_name": "www.aparat.com"
                },
                "http2": {
                    "header_table_size": 4096,
                    "enable_push": 0,
                    "max_concurrent_streams": 100,
                    "initial_window_size": 65535,
                    "max_frame_size": 16384,
                    "max_header_list_size": 65536,
                    "header_order": [
                        ":method", ":path", ":authority", ":scheme",
                        "user-agent", "accept", "accept-language", "accept-encoding"
                    ],
                    "priority_frames": False
                },
                "traffic": {
                    "packet_sizes": {},
                    "inter_arrival_min_ms": 10,
                    "inter_arrival_max_ms": 80,
                    "burst_probability": 0.4,
                    "burst_size_min": 4,
                    "burst_size_max": 12,
                    "silence_min_ms": 200,
                    "silence_max_ms": 1000,
                    "jitter": True,
                    "padding_min": 0,
                    "padding_max": 256,
                    "bidirectional": True
                },
                "headers": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "accept_language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
                    "accept_encoding": "gzip, deflate, br",
                    "sec_fetch_site": "none",
                    "sec_fetch_mode": "navigate",
                    "sec_fetch_dest": "document",
                    "connection": "keep-alive",
                    "dnt": ""
                }
            },
            "youtube.json": {
                "name": "YouTube",
                "description": "Mimic YouTube video streaming traffic",
                "tls": {
                    "ja3": "",
                    "ja4": "",
                    "cipher_suites": [
                        "TLS_AES_128_GCM_SHA256",
                        "TLS_AES_256_GCM_SHA384"
                    ],
                    "extensions": [
                        "server_name", "supported_groups", "key_share",
                        "signature_algorithms", "supported_versions", "alpn",
                        "application_layer_protocol_negotiation"
                    ],
                    "alpn": ["h2", "http/1.1"],
                    "supported_versions": ["TLSv1.3"],
                    "grease": True,
                    "record_size_limit": 16384,
                    "server_name": "www.youtube.com"
                },
                "http2": {
                    "header_table_size": 4096,
                    "enable_push": 0,
                    "max_concurrent_streams": 100,
                    "initial_window_size": 65535,
                    "max_frame_size": 16384,
                    "max_header_list_size": 65536,
                    "header_order": [
                        ":method", ":path", ":authority", ":scheme",
                        "user-agent", "accept", "accept-language", "accept-encoding"
                    ],
                    "priority_frames": True
                },
                "traffic": {
                    "packet_sizes": {},
                    "inter_arrival_min_ms": 5,
                    "inter_arrival_max_ms": 40,
                    "burst_probability": 0.5,
                    "burst_size_min": 5,
                    "burst_size_max": 15,
                    "silence_min_ms": 100,
                    "silence_max_ms": 500,
                    "jitter": True,
                    "padding_min": 0,
                    "padding_max": 128,
                    "bidirectional": True
                },
                "headers": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "accept_language": "en-US,en;q=0.9",
                    "accept_encoding": "gzip, deflate, br",
                    "sec_fetch_site": "none",
                    "sec_fetch_mode": "navigate",
                    "sec_fetch_dest": "document",
                    "connection": "keep-alive",
                    "dnt": ""
                }
            },
            "discord.json": {
                "name": "Discord",
                "description": "Mimic Discord voice/chat traffic - WebSocket & HTTP/2",
                "tls": {
                    "ja3": "",
                    "ja4": "",
                    "cipher_suites": [
                        "TLS_AES_128_GCM_SHA256",
                        "TLS_AES_256_GCM_SHA384",
                        "TLS_CHACHA20_POLY1305_SHA256"
                    ],
                    "extensions": [
                        "server_name", "supported_groups", "key_share",
                        "signature_algorithms", "supported_versions"
                    ],
                    "alpn": ["h2", "http/1.1"],
                    "supported_versions": ["TLSv1.3", "TLSv1.2"],
                    "grease": True,
                    "record_size_limit": 16384,
                    "server_name": "discord.com"
                },
                "http2": {
                    "header_table_size": 4096,
                    "enable_push": 0,
                    "max_concurrent_streams": 100,
                    "initial_window_size": 65535,
                    "max_frame_size": 16384,
                    "max_header_list_size": 65536,
                    "header_order": [
                        ":method", ":path", ":authority", ":scheme",
                        "user-agent", "accept", "accept-language", "accept-encoding"
                    ],
                    "priority_frames": False
                },
                "traffic": {
                    "packet_sizes": {},
                    "inter_arrival_min_ms": 20,
                    "inter_arrival_max_ms": 60,
                    "burst_probability": 0.2,
                    "burst_size_min": 2,
                    "burst_size_max": 5,
                    "silence_min_ms": 500,
                    "silence_max_ms": 2000,
                    "jitter": True,
                    "padding_min": 0,
                    "padding_max": 64,
                    "bidirectional": True
                },
                "headers": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "accept": "application/json, text/plain, */*",
                    "accept_language": "en-US,en;q=0.9",
                    "accept_encoding": "gzip, deflate, br",
                    "sec_fetch_site": "none",
                    "sec_fetch_mode": "cors",
                    "sec_fetch_dest": "empty",
                    "connection": "keep-alive",
                    "dnt": ""
                }
            }
        }

        for filename, data in defaults.items():
            path = os.path.join(self.profiles_dir, filename)
            if not os.path.exists(path):
                profile = self._dict_to_profile(data)
                profile.save(path)

    def _dict_to_profile(self, data: Dict[str, Any]) -> MimicryProfile:
        """تبدیل دیکشنری به نمونه MimicryProfile با تمام جزئیات"""
        profile = MimicryProfile()
        profile.name = data.get("name", "Unnamed")
        profile.description = data.get("description", "")

        # TLS
        tls_data = data.get("tls", {})
        profile.tls = TLSConfig(
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
        http2_data = data.get("http2", {})
        profile.http2 = HTTP2Config(
            settings_header_table_size=http2_data.get("header_table_size", 4096),
            settings_enable_push=http2_data.get("enable_push", 0),
            settings_max_concurrent_streams=http2_data.get("max_concurrent_streams", 100),
            settings_initial_window_size=http2_data.get("initial_window_size", 65535),
            settings_max_frame_size=http2_data.get("max_frame_size", 16384),
            settings_max_header_list_size=http2_data.get("max_header_list_size", 65536),
            header_order=http2_data.get("header_order", [
                ":method", ":path", ":authority", ":scheme",
                "user-agent", "accept", "accept-language", "accept-encoding"
            ]),
            priority_frames_enabled=http2_data.get("priority_frames", False)
        )

        # Traffic
        traffic_data = data.get("traffic", {})
        profile.traffic = TrafficPattern(
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

        # Headers
        headers_data = data.get("headers", {})
        profile.headers = HTTPHeaders(
            user_agent=headers_data.get("user_agent", profile.headers.user_agent),
            accept=headers_data.get("accept", profile.headers.accept),
            accept_language=headers_data.get("accept_language", profile.headers.accept_language),
            accept_encoding=headers_data.get("accept_encoding", profile.headers.accept_encoding),
            sec_fetch_site=headers_data.get("sec_fetch_site", "none"),
            sec_fetch_mode=headers_data.get("sec_fetch_mode", "navigate"),
            sec_fetch_dest=headers_data.get("sec_fetch_dest", "document"),
            connection=headers_data.get("connection", "keep-alive"),
            dnt=headers_data.get("dnt", "")
        )

        return profile

    def get_available_profiles(self) -> List[str]:
        """دریافت لیست نام پروفایل‌های موجود"""
        profiles = []
        if not os.path.exists(self.profiles_dir):
            return profiles
        for f in os.listdir(self.profiles_dir):
            if f.endswith('.json'):
                profiles.append(f[:-5])  # حذف پسوند .json
        return sorted(profiles)

    def load_profile(self, name: str) -> Optional[MimicryProfile]:
        """بارگذاری پروفایل با نام مشخص"""
        path = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.exists(path):
            return None
        try:
            profile = MimicryProfile()
            profile.load(path)
            return profile
        except Exception as e:
            print(f"[MimicryManager] Error loading profile {name}: {e}")
            return None

    def save_profile(self, profile: MimicryProfile) -> None:
        """ذخیره پروفایل در فایل JSON"""
        path = os.path.join(self.profiles_dir, f"{profile.name}.json")
        profile.save(path)

    def delete_profile(self, name: str) -> bool:
        """حذف پروفایل با نام مشخص"""
        path = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception:
                pass
        return False

    def set_active_profile(self, name: str) -> bool:
        """تنظیم پروفایل فعال"""
        profile = self.load_profile(name)
        if profile:
            with self._lock:
                self.current_profile = profile
            return True
        return False

    def start(self) -> bool:
        """اجرای پراکسی با پروفایل فعال"""
        with self._lock:
            if not self.current_profile:
                print("[MimicryManager] No active profile set.")
                return False
            if self.proxy and self.proxy.running:
                return True

            self.proxy = MimicryProxy(self.current_profile, self.proxy_host, self.proxy_port)
            if self.proxy.start():
                self.enabled = True
                print(f"[MimicryManager] Proxy started on {self.proxy_host}:{self.proxy_port} with profile '{self.current_profile.name}'")
                return True
            else:
                self.proxy = None
                return False

    def stop(self) -> None:
        """توقف پراکسی"""
        with self._lock:
            if self.proxy:
                self.proxy.stop()
                self.proxy = None
                print("[MimicryManager] Proxy stopped.")
            self.enabled = False

    def is_running(self) -> bool:
        return self.enabled and self.proxy is not None and self.proxy.running

    def get_proxy_address(self) -> str:
        """دریافت آدرس پراکسی محلی (برای استفاده در Xray-core)"""
        return f"socks5://{self.proxy_host}:{self.proxy_port}"

    # ------------------------------------------------------------------
    # Auto-Profile Generation
    # ------------------------------------------------------------------
    def generate_profile_from_url(self, url: str, profile_name: Optional[str] = None) -> Optional[MimicryProfile]:
        """
        تولید خودکار پروفایل شبیه‌سازی از یک URL.
        این متد از ماژول auto_profile (در صورت وجود) استفاده می‌کند.
        """
        try:
            from .auto_profile import AutoProfileGenerator
            generator = AutoProfileGenerator()
            profile = generator.generate_from_url(url, profile_name)
            if profile:
                self.save_profile(profile)
                return profile
        except ImportError:
            print("[MimicryManager] AutoProfileGenerator not available. Please install required dependencies.")
        except Exception as e:
            print(f"[MimicryManager] Auto-profile generation failed: {e}")
        return None
