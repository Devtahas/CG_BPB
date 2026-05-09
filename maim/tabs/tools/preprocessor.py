# tabs/tools/preprocessor.py

import asyncio
import socket
import struct
import threading
import time
import random
import ssl
import os
from typing import Optional, Tuple

# پروژه داخلی
from ..client.mimicry.mimicry_profile import MimicryProfile
from ..client.mimicry.mimicry_proxy import MimicryProxy  # برای الگوبرداری از ساختار SOCKS5

# تلاش برای ایمپورت uTLS برای فینگرپرینت دقیق
try:
    from utls import UTLSClientHelloSpec
    HAS_UTLS = True
except ImportError:
    HAS_UTLS = False

SOCKS_VERSION = 0x05
SOCKS_CMD_CONNECT = 0x01
SOCKS_ATYP_IPV4 = 0x01
SOCKS_ATYP_DOMAIN = 0x03
SOCKS_ATYP_IPV6 = 0x04
SOCKS_AUTH_NONE = 0x00

# اندازه بافر برای رله داده
BUFFER_SIZE = 8192


class PreProcessorProxy:
    """
    پیش‌پردازشگر ترافیک محلی (Local Traffic Pre‑Processor).
    یک پراکسی SOCKS5 روی localhost اجرا می‌کند که تمام اتصالات خروجی
    برنامه را از خود عبور می‌دهد. پیش از ارسال پکت به شبکه، موارد زیر اعمال می‌شود:

    - جعل TLS fingerprint مطابق پروفایل سایت لیست‌سفید (JA3/JA4)
    - اعمال padding تصادفی روی بسته‌های خروجی
    - تزریق تأخیرهای تصادفی (jitter) و الگوهای burst
    - تنظیم هدرهای HTTP/2 و ALPN مطابق پروفایل

    این لایه کاملاً محلی است و نیازی به سرور خارجی ندارد.
    """

    def __init__(self,
                 profile: Optional[MimicryProfile] = None,
                 listen_host: str = '127.0.0.1',
                 listen_port: int = 10815):
        self.profile = profile or MimicryProfile()
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.server: Optional[asyncio.Server] = None
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    # =================================================================
    # مدیریت چرخه حیات
    # =================================================================
    def start(self) -> bool:
        if self.running:
            return True
        self.running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self.running = False
        if self.loop and self.server:
            self.loop.call_soon_threadsafe(self.server.close)
        if self._thread:
            self._thread.join(timeout=2.0)

    def is_running(self) -> bool:
        return self.running

    def _run_event_loop(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start_server())
        except Exception:
            pass
        self.loop.close()

    async def _start_server(self) -> None:
        self.server = await asyncio.start_server(
            self._handle_client, self.listen_host, self.listen_port
        )
        await self.server.serve_forever()

    # =================================================================
    # مدیریت کلاینت SOCKS5
    # =================================================================
    async def _handle_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter) -> None:
        try:
            await self._socks_handshake(reader, writer)
            target_host, target_port = await self._socks_request(reader, writer)
            remote_reader, remote_writer = await self._connect_to_target(
                target_host, target_port
            )
            await self._socks_response(writer, 0x00, target_host, target_port)
            await self._relay_traffic(reader, writer, remote_reader, remote_writer)
        except Exception as e:
            print(f"[PreProcessor] Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _socks_handshake(self, reader, writer):
        version = await reader.readexactly(1)
        if version[0] != SOCKS_VERSION:
            raise ValueError("Invalid SOCKS version")
        nmethods = await reader.readexactly(1)
        methods = await reader.readexactly(nmethods[0])
        writer.write(bytes([SOCKS_VERSION, SOCKS_AUTH_NONE]))
        await writer.drain()

    async def _socks_request(self, reader, writer) -> Tuple[str, int]:
        header = await reader.readexactly(4)
        ver, cmd, rsv, atyp = header
        if ver != SOCKS_VERSION or cmd != SOCKS_CMD_CONNECT:
            raise ValueError("Invalid SOCKS request")
        if atyp == SOCKS_ATYP_IPV4:
            addr_bytes = await reader.readexactly(4)
            host = socket.inet_ntoa(addr_bytes)
        elif atyp == SOCKS_ATYP_DOMAIN:
            length = await reader.readexactly(1)
            addr_bytes = await reader.readexactly(length[0])
            host = addr_bytes.decode('utf-8')
        elif atyp == SOCKS_ATYP_IPV6:
            addr_bytes = await reader.readexactly(16)
            host = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            raise ValueError("Unsupported address type")
        port_bytes = await reader.readexactly(2)
        port = struct.unpack('>H', port_bytes)[0]
        return host, port

    async def _socks_response(self, writer, rep, host, port):
        response = bytearray([SOCKS_VERSION, rep, 0x00, SOCKS_ATYP_IPV4])
        response.extend(socket.inet_aton('0.0.0.0'))
        response.extend(struct.pack('>H', port))
        writer.write(response)
        await writer.drain()

    # =================================================================
    # اتصال به مقصد با اعمال فینگرپرینت و TLS
    # =================================================================
    def _create_tls_context(self, server_hostname: str) -> ssl.SSLContext:
        """ساخت SSLContext با مشخصات دقیق پروفایل برای جعل JA3"""
        tls_config = self.profile.tls

        if HAS_UTLS:
            # استفاده از uTLS برای فینگرپرینت بینقص
            client_hello_spec = UTLSClientHelloSpec(
                tls_config.ja3_fingerprint or "chrome_133",
            )
            return client_hello_spec.create_ssl_context()

        # راه‌حل جایگزین: سفارشی‌سازی SSLContext استاندارد (تا حد ممکن)
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        # تنظیم رمزها
        if tls_config.cipher_suites:
            cipher_string = ':'.join(tls_config.cipher_suites)
            try:
                ctx.set_ciphers(cipher_string)
            except ssl.SSLError:
                pass

        # تنظیم ALPN
        if tls_config.alpn_protocols:
            ctx.set_alpn_protocols(tls_config.alpn_protocols)

        # اعمال نسخه‌های TLS
        if "TLSv1.3" in tls_config.supported_versions:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            ctx.maximum_version = ssl.TLSVersion.TLSv1_3
        elif "TLSv1.2" in tls_config.supported_versions:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2

        return ctx

    async def _connect_to_target(self, host: str, port: int
                                ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        برقراری ارتباط با مقصد نهایی و اعمال TLS در صورت نیاز.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        loop = asyncio.get_event_loop()
        await loop.sock_connect(sock, (host, port))

        # فقط در پورت‌های HTTPS (پیش‌فرض ۴۴۳) TLS را فعال کن
        if port == 443:
            context = self._create_tls_context(host)
            try:
                wrapped_sock = context.wrap_socket(sock, server_hostname=host)
            except Exception as e:
                print(f"[PreProcessor] TLS handshake failed: {e}")
                sock.close()
                raise
            reader, writer = await asyncio.open_connection(sock=wrapped_sock)
        else:
            reader, writer = await asyncio.open_connection(sock=sock)
        return reader, writer

    # =================================================================
    # رله داده با Traffic Shaping (پدینگ، جیتر، برست)
    # =================================================================
    async def _relay_traffic(self, client_reader, client_writer,
                            remote_reader, remote_writer):
        """
        انتقال داده بین کلاینت و سرور همراه با اعمال پدینگ و جیتر روی
        بسته‌های خروجی (از کلاینت به سرور).
        """

        async def forward(src, dst, direction):
            try:
                while self.running:
                    data = await src.read(BUFFER_SIZE)
                    if not data:
                        break
                    # فقط روی جهت خروجی (client->server) پدینگ و جیتر اعمال کن
                    if direction == 'out' and self.profile.traffic.padding_max_bytes > 0:
                        padding = self.profile.get_padding_bytes()
                        if padding:
                            data += padding
                    if self.profile.traffic.jitter_enabled:
                        delay = self.profile.sample_delay_ms() / 1000.0
                        await asyncio.sleep(delay)
                    dst.write(data)
                    await dst.drain()
                    # گاهی پکت‌ها را به صورت burst ارسال کن
                    if direction == 'out' and self.profile.should_burst():
                        burst_size = self.profile.get_burst_size()
                        for _ in range(burst_size - 1):
                            if not self.running:
                                break
                            extra = await src.read(BUFFER_SIZE)
                            if not extra:
                                break
                            dst.write(extra)
                            await dst.drain()
                            await asyncio.sleep(self.profile.sample_delay_ms() / 1000.0)
                    # گاهی یک سکوت تصادفی ایجاد کن
                    if direction == 'out':
                        silence_ms = self.profile.get_silence_ms()
                        if silence_ms > 0 and random.random() < 0.1:
                            await asyncio.sleep(silence_ms / 1000.0)
            except Exception:
                pass
            finally:
                dst.close()
                await dst.wait_closed()

        # دو task همزمان برای رفت و برگشت
        task_out = asyncio.create_task(forward(client_reader, remote_writer, 'out'))
        task_in = asyncio.create_task(forward(remote_reader, client_writer, 'in'))
        done, pending = await asyncio.wait(
            [task_out, task_in], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
