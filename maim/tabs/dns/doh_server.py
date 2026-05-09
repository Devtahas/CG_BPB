# tabs/dns/doh_server.py
import socket
import threading
import requests
import base64
from typing import Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor


class LocalDoHServer:
    """
    سرور محلی DNS-over-HTTPS (DoH)
    این سرور روی localhost اجرا می‌شود و کوئری‌های DNS سنتی (UDP port 53) را
    دریافت کرده و آن‌ها را از طریق HTTPS به یک سرور DoH ارسال می‌کند.

    ویژگی‌ها:
        - پشتیبانی از هر سرور DoH (Cloudflare, Google, Quad9, ...)
        - پردازش همزمان با ThreadPoolExecutor
        - مدیریت session برای استفاده مجدد از connection
        - قابلیت تنظیم timeout و retry
    """

    def __init__(self, doh_url: str, timeout: float = 5.0, max_workers: int = 20):
        """
        Args:
            doh_url: آدرس کامل سرور DoH (مثلاً https://cloudflare-dns.com/dns-query)
            timeout: زمان timeout برای هر درخواست (ثانیه)
            max_workers: حداکثر تعداد threadهای همزمان
        """
        self.doh_url = doh_url
        self.timeout = timeout
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.bound_ip: Optional[str] = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/dns-message',
            'Content-Type': 'application/dns-message',
            'User-Agent': 'NetTools-DoH-Proxy/1.0'
        })
        self.stats: Dict[str, Any] = {
            "queries_processed": 0,
            "queries_failed": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0
        }

    def start(self) -> bool:
        """
        راه‌اندازی سرور DoH محلی
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

        threading.Thread(target=self._listen_loop, daemon=True).start()
        return True

    def stop(self) -> None:
        """توقف سرور DoH محلی"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.executor.shutdown(wait=False)
        self.session.close()

    def _listen_loop(self) -> None:
        """حلقه اصلی گوش دادن به درخواست‌های UDP"""
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(4096)  # حداکثر سایز پاسخ DNS
                if data:
                    self.executor.submit(self._handle_request, data, addr)
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    break

    def _handle_request(self, data: bytes, addr: tuple) -> None:
        """
        پردازش یک کوئری DNS و ارسال آن به سرور DoH
        """
        try:
            self.stats["queries_processed"] += 1
            self.stats["total_bytes_sent"] += len(data)

            # ارسال درخواست به سرور DoH
            response = self.session.post(
                self.doh_url,
                data=data,
                timeout=self.timeout
            )

            if response.status_code == 200 and self.running and self.sock:
                self.stats["total_bytes_received"] += len(response.content)
                self.sock.sendto(response.content, addr)
            else:
                self.stats["queries_failed"] += 1
        except Exception:
            self.stats["queries_failed"] += 1

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        تست اتصال به سرور DoH با ارسال یک کوئری ساده
        Returns:
            (success, error_message)
        """
        try:
            # یک کوئری DNS ساده برای google.com
            query = base64.b64decode("AAABAAABAAAAAAAAA2NvbQAAAQAB")
            response = self.session.post(
                self.doh_url,
                data=query,
                timeout=self.timeout
            )
            return response.status_code == 200, None
        except Exception as e:
            return False, str(e)

    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار سرور"""
        return {
            "is_running": self.running,
            "bound_ip": self.bound_ip,
            "doh_url": self.doh_url,
            **self.stats
        }

    def reset_stats(self) -> None:
        """بازنشانی آمار"""
        self.stats["queries_processed"] = 0
        self.stats["queries_failed"] = 0
        self.stats["total_bytes_sent"] = 0
        self.stats["total_bytes_received"] = 0

    def is_running(self) -> bool:
        return self.running

    def get_bound_ip(self) -> Optional[str]:
        return self.bound_ip
