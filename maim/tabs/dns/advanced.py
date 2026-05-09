# tabs/dns/advanced.py
import time
import socket
import ssl
import threading
import ipaddress
import random
import requests
import base64
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor

try:
    import dns.resolver
    import dns.flags
    import dns.edns
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

# غیرفعال کردن اخطارهای SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SplitDNSResolver:
    """
    سیستم Split DNS: مسیریابی دامنه‌های مختلف به DNS سرورهای متفاوت
    مثال: دامنه‌های *.google.com با 8.8.8.8 حل شوند و بقیه با 1.1.1.1
    """

    def __init__(self):
        self.rules: Dict[str, str] = {}  # pattern -> dns_server
        self.cache: Dict[str, Tuple[float, List[str]]] = {}
        self.cache_ttl = 300

    def add_rule(self, domain_pattern: str, dns_server: str) -> None:
        """
        افزودن یک قانون جدید
        Args:
            domain_pattern: الگوی دامنه (می‌تواند wildcard باشد مثل *.google.com)
            dns_server: IP سرور DNS
        """
        self.rules[domain_pattern] = dns_server
        keys_to_remove = [k for k in self.cache if self._match_pattern(k, domain_pattern)]
        for k in keys_to_remove:
            del self.cache[k]

    def remove_rule(self, domain_pattern: str) -> bool:
        if domain_pattern in self.rules:
            del self.rules[domain_pattern]
            return True
        return False

    def get_rules(self) -> Dict[str, str]:
        return self.rules.copy()

    def _match_pattern(self, domain: str, pattern: str) -> bool:
        if pattern.startswith("*."):
            suffix = pattern[2:].lower()
            return domain.lower().endswith(suffix)
        return domain.lower() == pattern.lower()

    def _get_dns_for_domain(self, domain: str) -> Optional[str]:
        domain_lower = domain.lower()
        if domain_lower in self.rules:
            return self.rules[domain_lower]
        for pattern, dns_server in self.rules.items():
            if pattern.startswith("*."):
                suffix = pattern[2:].lower()
                if domain_lower.endswith(suffix):
                    return dns_server
        return None

    def _query_dns(self, domain: str, dns_server: str, record_type: str = "A") -> List[str]:
        if not HAS_DNSPYTHON:
            return []
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            resolver.timeout = 2
            resolver.lifetime = 2
            answers = resolver.resolve(domain, record_type)
            return [str(rdata) for rdata in answers]
        except Exception:
            return []

    def resolve(self, domain: str, record_type: str = "A") -> Optional[List[str]]:
        cache_key = f"{domain}:{record_type}"
        if cache_key in self.cache:
            cached_time, result = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return result

        dns_server = self._get_dns_for_domain(domain)
        if not dns_server:
            return None

        result = self._query_dns(domain, dns_server, record_type)
        if result:
            self.cache[cache_key] = (time.time(), result)
        return result

    def clear_cache(self) -> None:
        self.cache.clear()


class DNSCache:
    """سیستم کش ساده برای نتایج DNS"""

    def __init__(self, ttl: int = 300):
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self.cache[key] = (time.time(), value)

    def clear(self) -> None:
        self.cache.clear()

    def size(self) -> int:
        return len(self.cache)

    def cleanup(self) -> int:
        now = time.time()
        expired = [k for k, (ts, _) in self.cache.items() if now - ts >= self.ttl]
        for k in expired:
            del self.cache[k]
        return len(expired)


class SmartDNS:
    """
    انتخاب هوشمند DNS بر اساس نوع محتوا
    """

    def __init__(self):
        self.rules = {
            "streaming": ["netflix.com", "hulu.com", "disneyplus.com", "hbomax.com", "youtube.com"],
            "social": ["instagram.com", "facebook.com", "twitter.com", "tiktok.com", "telegram.org"],
            "gaming": ["steam.com", "epicgames.com", "xbox.com", "playstation.com", "discord.com"],
            "cloudflare": ["workers.dev", "cloudflare.com", "pages.dev"]
        }
        self.dns_mapping = {
            "streaming": "8.8.8.8",
            "social": "1.1.1.1",
            "gaming": "9.9.9.9",
            "cloudflare": "localhost"
        }

    def add_rule(self, domain: str, category: str) -> None:
        if category not in self.rules:
            self.rules[category] = []
        if domain not in self.rules[category]:
            self.rules[category].append(domain)

    def set_dns_for_category(self, category: str, dns_server: str) -> None:
        self.dns_mapping[category] = dns_server

    def get_dns_for_domain(self, domain: str) -> str:
        domain_lower = domain.lower()
        for category, domains in self.rules.items():
            for d in domains:
                if d in domain_lower or domain_lower.endswith(d):
                    return self.dns_mapping.get(category, "8.8.8.8")
        return "8.8.8.8"

    def get_categories(self) -> List[str]:
        return list(self.rules.keys())

    def get_domains_for_category(self, category: str) -> List[str]:
        return self.rules.get(category, []).copy()


class CNAMEUnmasker:
    """دنبال کردن زنجیره CNAME تا رسیدن به رکورد A نهایی"""

    @staticmethod
    def unmask(domain: str) -> Dict[str, Any]:
        if not HAS_DNSPYTHON:
            return {"chain": [], "final_domain": domain, "ips": [], "behind_cdn": False, "error": "dnspython not installed"}

        try:
            results = []
            current = domain
            max_depth = 20

            for _ in range(max_depth):
                try:
                    answers = dns.resolver.resolve(current, 'CNAME')
                    for rdata in answers:
                        current = str(rdata.target).rstrip('.')
                        results.append(current)
                        break
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                    break
                except Exception:
                    break

            a_records = dns.resolver.resolve(current, 'A')
            final_ips = [str(rdata) for rdata in a_records]

            cdn_indicators = ['cloudflare', 'fastly', 'akamai', 'cloudfront', 'edgekey', 'edgesuite']
            behind_cdn = any(cdn in current.lower() for cdn in cdn_indicators)

            return {
                "chain": results,
                "final_domain": current,
                "ips": final_ips,
                "behind_cdn": behind_cdn,
                "error": None
            }
        except Exception as e:
            return {"chain": [], "final_domain": domain, "ips": [], "behind_cdn": False, "error": str(e)}


class DNSSECChecker:
    """بررسی اعتبار DNSSEC برای یک دامنه"""

    @staticmethod
    def check(domain: str) -> Tuple[bool, str]:
        if not HAS_DNSPYTHON:
            return False, "dnspython not installed"

        try:
            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, payload=4096, options=[dns.edns.GenericOption(b'1234', b'')])
            answers = resolver.resolve(domain, 'A', want_dnssec=True)

            if answers.response.flags & dns.flags.AD:
                return True, "DNSSEC validated"
            return False, "DNSSEC not validated"
        except dns.resolver.NXDOMAIN:
            return False, "Domain does not exist"
        except dns.resolver.Timeout:
            return False, "Query timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"


class DoTDoHTester:
    """تست اتصال به سرورهای DoH و DoT"""

    @staticmethod
    def test_doh(url: str, timeout: float = 5.0) -> bool:
        try:
            headers = {'Accept': 'application/dns-message', 'Content-Type': 'application/dns-message'}
            query = base64.b64decode("AAABAAABAAAAAAAAA2NvbQAAAQAB")
            resp = requests.post(url, data=query, headers=headers, timeout=timeout, verify=False)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def test_dot(host: str, port: int = 853, timeout: float = 5.0) -> bool:
        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    return True
        except Exception:
            return False

    @staticmethod
    def test_batch_doh(servers: List[str], timeout: float = 5.0) -> Dict[str, bool]:
        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(DoTDoHTester.test_doh, url, timeout): url for url in servers}
            for future in futures:
                url = futures[future]
                try:
                    results[url] = future.result()
                except Exception:
                    results[url] = False
        return results

    @staticmethod
    def test_batch_dot(servers: List[Tuple[str, int]], timeout: float = 5.0) -> Dict[str, bool]:
        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for host, port in servers:
                future = executor.submit(DoTDoHTester.test_dot, host, port, timeout)
                futures[future] = f"{host}:{port}"
            for future in futures:
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception:
                    results[key] = False
        return results


class DNSLeakTester:
    """تست نشت DNS"""

    @staticmethod
    def test_leak() -> Optional[Dict[str, str]]:
        services = [
            {
                "url": "https://ipleak.net/json/",
                "parser": lambda d: {"ip": d.get('ip'), "country": d.get('country_name'), "isp": d.get('isp')}
            },
            {
                "url": "http://ip-api.com/json/",
                "parser": lambda d: {"ip": d.get('query'), "country": d.get('country'), "isp": d.get('isp')}
            },
            {
                "url": "https://api.ipify.org?format=json",
                "parser": lambda d: {"ip": d.get('ip'), "country": "Unknown", "isp": "Unknown"}
            }
        ]

        for service in services:
            try:
                resp = requests.get(service["url"], timeout=10, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    return service["parser"](data)
            except Exception:
                continue

        return None

    @staticmethod
    def test_dns_servers_visible() -> List[str]:
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            return list(resolver.nameservers)
        except Exception:
            return []


class DNSScanner:
    """اسکنر DNS برای تست سرعت و سلامت"""

    @staticmethod
    def scan(dns_list: List[str], timeout: float = 2.0) -> List[Dict[str, Any]]:
        results = []

        def test_dns(dns_ip: str) -> Dict[str, Any]:
            start = time.time()
            try:
                socket.create_connection((dns_ip, 53), timeout=timeout).close()
                latency = int((time.time() - start) * 1000)
                return {"dns": dns_ip, "latency": latency, "status": "OK"}
            except Exception:
                return {"dns": dns_ip, "latency": 9999, "status": "FAILED"}

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(test_dns, dns) for dns in dns_list]
            for future in futures:
                results.append(future.result())

        results.sort(key=lambda x: x['latency'])
        return results

    @staticmethod
    def scan_with_query(dns_list: List[str], domain: str, timeout: float = 2.0) -> List[Dict[str, Any]]:
        if not HAS_DNSPYTHON:
            return []

        results = []

        def test_dns(dns_ip: str) -> Dict[str, Any]:
            start = time.time()
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_ip]
                resolver.timeout = timeout
                resolver.lifetime = timeout
                answers = resolver.resolve(domain, 'A')
                latency = int((time.time() - start) * 1000)
                return {
                    "dns": dns_ip,
                    "latency": latency,
                    "status": "OK",
                    "answers": [str(r) for r in answers]
                }
            except Exception:
                return {"dns": dns_ip, "latency": 9999, "status": "FAILED", "answers": []}

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(test_dns, dns) for dns in dns_list]
            for future in futures:
                results.append(future.result())

        results.sort(key=lambda x: x['latency'])
        return results
