# tabs/dns/dns_utils.py
import time
import socket
import ssl
import requests
import base64
import random
from typing import Dict, List, Tuple, Optional, Any

try:
    import dns.resolver
    import dns.flags
    import dns.edns
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

# لیست DNS های پیش‌فرض برای اسکن
DNS_SCAN_LIST = [
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9", "149.112.112.112",
    "208.67.222.222", "208.67.220.220", "94.140.14.14", "94.140.15.15",
    "76.76.19.19", "185.228.168.9", "185.228.169.9", "178.22.122.100",
    "185.51.200.2", "78.157.42.100", "78.157.42.101", "10.202.10.10", "10.202.10.11",
    "209.244.0.3", "209.244.0.4", "64.6.64.6", "64.6.65.6", "84.200.69.80",
    "84.200.70.40", "114.114.114.114", "223.5.5.5", "180.76.76.76",
    "45.90.28.0", "45.90.30.0", "185.228.168.10", "185.228.169.11",
    "156.154.70.1", "156.154.71.1", "208.67.222.123", "208.67.220.123"
]


class DNSUtils:
    """توابع کمکی برای DNS (پینگ، تست DoH/DoT، DNSSEC، CNAME و ...)"""

    @staticmethod
    def ping_dns(dns_ip: str, timeout: float = 2.0) -> int:
        """
        اندازه‌گیری latency یک DNS Server از طریق TCP port 53
        برمی‌گرداند: latency به میلی‌ثانیه، یا 9999 در صورت timeout/error
        """
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((dns_ip, 53))
            sock.close()
            return int((time.time() - start) * 1000)
        except Exception:
            return 9999

    @staticmethod
    def ping_dns_udp(dns_ip: str, timeout: float = 2.0, query_domain: str = "google.com") -> Tuple[int, bool]:
        """
        اندازه‌گیری latency از طریق UDP (ارسال یک کوئری واقعی DNS)
        برمی‌گرداند: (latency_ms, success)
        """
        if not HAS_DNSPYTHON:
            return 9999, False
        start = time.time()
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_ip]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            resolver.resolve(query_domain, 'A')
            return int((time.time() - start) * 1000), True
        except Exception:
            return 9999, False

    @staticmethod
    def test_doh(url: str, timeout: float = 5.0) -> bool:
        """
        تست اینکه یک DoH endpoint معتبر است یا خیر
        """
        try:
            headers = {
                'Accept': 'application/dns-message',
                'Content-Type': 'application/dns-message'
            }
            # یک کوئری ساده برای google.com
            query = base64.b64decode("AAABAAABAAAAAAAAA2NvbQAAAQAB")
            resp = requests.post(url, data=query, headers=headers, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def test_dot(host: str, port: int = 853, timeout: float = 5.0) -> bool:
        """
        تست اینکه یک DoT server در دسترس است
        """
        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    # فقط handshake موفق کافی است
                    return True
        except Exception:
            return False

    @staticmethod
    def test_dns_query(dns_ip: str, domain: str = "google.com", record_type: str = "A", timeout: float = 3.0) -> Dict[str, Any]:
        """
        ارسال یک کوئری DNS واقعی و برگرداندن نتیجه کامل
        برمی‌گرداند: دیکشنری شامل success, latency, answers, error
        """
        if not HAS_DNSPYTHON:
            return {"success": False, "error": "dnspython not installed"}

        start = time.time()
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_ip]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            answers = resolver.resolve(domain, record_type)
            latency = int((time.time() - start) * 1000)
            result_list = [str(r) for r in answers]
            return {
                "success": True,
                "latency": latency,
                "answers": result_list,
                "error": None
            }
        except dns.resolver.NXDOMAIN:
            return {"success": False, "latency": 9999, "answers": [], "error": "NXDOMAIN"}
        except dns.resolver.Timeout:
            return {"success": False, "latency": 9999, "answers": [], "error": "Timeout"}
        except Exception as e:
            return {"success": False, "latency": 9999, "answers": [], "error": str(e)}

    @staticmethod
    def check_dnssec(domain: str) -> Tuple[bool, str]:
        """
        بررسی اعتبار DNSSEC برای یک دامنه
        برمی‌گرداند: (is_valid, message)
        """
        if not HAS_DNSPYTHON:
            return False, "dnspython not installed"
        try:
            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, payload=4096, options=[dns.edns.GenericOption(b'1234', b'')])
            answers = resolver.resolve(domain, 'A', want_dnssec=True)
            if answers.response.flags & dns.flags.AD:
                return True, "DNSSEC validated"
            return False, "DNSSEC not validated"
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def unmask_cname(domain: str) -> Dict[str, Any]:
        """
        دنبال کردن زنجیره CNAME تا رسیدن به رکورد A نهایی
        برمی‌گرداند:
            {
                "chain": [list of CNAMEs],
                "final_domain": str,
                "ips": [list of IPs],
                "behind_cdn": bool
            }
        """
        if not HAS_DNSPYTHON:
            return {"chain": [], "final_domain": domain, "ips": [], "behind_cdn": False, "error": "dnspython not installed"}
        try:
            results = []
            current = domain
            # حلقه CNAME
            while True:
                try:
                    answers = dns.resolver.resolve(current, 'CNAME')
                    for rdata in answers:
                        current = str(rdata.target).rstrip('.')
                        results.append(current)
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                    break
            # رکورد A نهایی
            a_records = dns.resolver.resolve(current, 'A')
            final_ips = [str(rdata) for rdata in a_records]
            behind_cdn = any(cdn in current.lower() for cdn in ['cloudflare', 'fastly', 'akamai', 'cloudfront'])
            return {
                "chain": results,
                "final_domain": current,
                "ips": final_ips,
                "behind_cdn": behind_cdn,
                "error": None
            }
        except Exception as e:
            return {"chain": [], "final_domain": domain, "ips": [], "behind_cdn": False, "error": str(e)}

    @staticmethod
    def get_flag_emoji(country_code: str) -> str:
        """تبدیل کد کشور به ایموجی پرچم"""
        if not country_code or len(country_code) != 2:
            return "🌍"
        try:
            return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)
        except:
            return "🌍"

    @staticmethod
    def get_public_ip() -> Dict[str, str]:
        """دریافت IP عمومی و اطلاعات ISP از ip-api.com"""
        try:
            resp = requests.get('http://ip-api.com/json/', timeout=5)
            data = resp.json()
            return {
                "ip": data.get('query', 'Unknown'),
                "country": data.get('country', 'Unknown'),
                "countryCode": data.get('countryCode', 'UN'),
                "isp": data.get('isp', 'Unknown'),
                "city": data.get('city', 'Unknown'),
                "region": data.get('regionName', 'Unknown')
            }
        except Exception:
            return {"ip": "Unknown", "country": "Unknown", "countryCode": "UN", "isp": "Unknown"}

    @staticmethod
    def is_ip_reachable(ip: str, port: int = 53, timeout: float = 2.0) -> bool:
        """بررسی اینکه IP از طریق TCP قابل دسترس است"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    @staticmethod
    def get_best_dns_from_list(dns_list: List[str], test_domain: str = "google.com", timeout: float = 2.0) -> Optional[str]:
        """
        پیدا کردن سریع‌ترین DNS از یک لیست
        برمی‌گرداند: IP بهترین DNS یا None
        """
        best_dns = None
        best_latency = 9999
        for dns in dns_list:
            latency = DNSUtils.ping_dns(dns, timeout)
            if latency < best_latency:
                best_latency = latency
                best_dns = dns
        return best_dns

    @staticmethod
    def validate_ip(ip: str) -> bool:
        """اعتبارسنجی فرمت IPv4"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for p in parts:
                if not 0 <= int(p) <= 255:
                    return False
            return True
        except:
            return False

    @staticmethod
    def generate_random_subdomain(base_domain: str = "example.com") -> str:
        """تولید یک زیردامنه تصادفی (برای تست DNS)"""
        import string
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{rand_str}.{base_domain}"
