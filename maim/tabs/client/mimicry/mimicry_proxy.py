# tabs/client/mimicry/mimicry_proxy.py
import asyncio
import socket
import struct
import threading
import time
import random
import ssl
from typing import Optional, Tuple, Dict, Any

# تلاش برای ایمپورت uTLS (اختیاری – برای JA3 دقیق)
try:
    from utls import UTLSClientHelloSpec
    HAS_UTLS = True
except ImportError:
    HAS_UTLS = False

from .mimicry_profile import MimicryProfile


class MimicryProxy:
    """
    پروکسی SOCKS5 محلی که ترافیک را طبق پروفایل شبیه‌سازی می‌کند.
    اکنون با TLS Fingerprint واقعی (JA3) از طریق تنظیمات پیشرفته‌ی SSL.
    پشتیبانی از upstream SOCKS5 برای زنجیره‌سازی (SOCKS5 → upstream proxy → target).
    """

    SOCKS_VERSION = 0x05
    SOCKS_CMD_CONNECT = 0x01
    SOCKS_ATYP_IPV4 = 0x01
    SOCKS_ATYP_DOMAIN = 0x03
    SOCKS_ATYP_IPV6 = 0x04

    # روش‌های auth
    SOCKS_AUTH_NONE = 0x00
    SOCKS_AUTH_USERPASS = 0x02

    def __init__(self, profile: MimicryProfile,
                 listen_host: str = '127.0.0.1',
                 listen_port: int = 10810,
                 upstream_proxy: Optional[str] = None):
        """
        Args:
            profile: پروفایل شبیه‌سازی
            listen_host: آدرس گوش دادن برای SOCKS5
            listen_port: پورت گوش دادن
            upstream_proxy: (اختیاری) آدرس پروکسی SOCKS5 بالادست به فرمت host:port
                            (مثلاً "127.0.0.1:10811")
        """
        self.profile = profile
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.upstream_proxy = upstream_proxy
        self.upstream_host = None
        self.upstream_port = None
        if upstream_proxy:
            parts = upstream_proxy.split(':')
            if len(parts) == 2:
                self.upstream_host = parts[0]
                self.upstream_port = int(parts[1])
            else:
                raise ValueError("upstream_proxy must be in format host:port")

        self.server: Optional[asyncio.Server] = None
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

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

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await self._socks_handshake(reader, writer)
            target_host, target_port = await self._socks_request(reader, writer)
            # اگر upstream_proxy فعال باشد، اتصال از طریق آن برقرار می‌شود
            if self.upstream_proxy:
                remote_reader, remote_writer = await self._connect_via_upstream(
                    target_host, target_port
                )
            else:
                remote_reader, remote_writer = await self._connect_to_target(
                    target_host, target_port
                )
            await self._socks_response(writer, 0x00, target_host, target_port)
            await self._relay_traffic(reader, writer, remote_reader, remote_writer)
        except Exception as e:
            print(f"[MimicryProxy] Error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _socks_handshake(self, reader, writer):
        version = await reader.readexactly(1)
        if version[0] != self.SOCKS_VERSION:
            raise ValueError("Invalid SOCKS version")
        nmethods = await reader.readexactly(1)
        methods = await reader.readexactly(nmethods[0])
        writer.write(bytes([self.SOCKS_VERSION, 0x00]))
        await writer.drain()

    async def _socks_request(self, reader, writer) -> Tuple[str, int]:
        header = await reader.readexactly(4)
        ver, cmd, rsv, atyp = header
        if ver != self.SOCKS_VERSION or cmd != self.SOCKS_CMD_CONNECT:
            raise ValueError("Invalid SOCKS request")
        if atyp == self.SOCKS_ATYP_IPV4:
            addr_bytes = await reader.readexactly(4)
            host = socket.inet_ntoa(addr_bytes)
        elif atyp == self.SOCKS_ATYP_DOMAIN:
            length = await reader.readexactly(1)
            addr_bytes = await reader.readexactly(length[0])
            host = addr_bytes.decode('utf-8')
        elif atyp == self.SOCKS_ATYP_IPV6:
            addr_bytes = await reader.readexactly(16)
            host = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            raise ValueError("Unsupported address type")
        port_bytes = await reader.readexactly(2)
        port = struct.unpack('>H', port_bytes)[0]
        return host, port

    async def _socks_response(self, writer, rep, host, port):
        response = bytearray([self.SOCKS_VERSION, rep, 0x00, self.SOCKS_ATYP_IPV4])
        response.extend(socket.inet_aton('0.0.0.0'))
        response.extend(struct.pack('>H', port))
        writer.write(response)
        await writer.drain()

    # -----------------------------------------------------------------
    # upstream SOCKS5 connection
    # -----------------------------------------------------------------
    async def _connect_via_upstream(self, host: str, port: int
                                   ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        اتصال به مقصد از طریق upstream SOCKS5.
        """
        # 1. اتصال به upstream proxy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        loop = asyncio.get_event_loop()
        await loop.sock_connect(sock, (self.upstream_host, self.upstream_port))
        reader_proxy, writer_proxy = await asyncio.open_connection(sock=sock)

        # 2. انجام SOCKS5 handshake (auth none)
        writer_proxy.write(bytes([self.SOCKS_VERSION, 1, self.SOCKS_AUTH_NONE]))
        await writer_proxy.drain()
        resp = await reader_proxy.readexactly(2)
        if resp[0] != self.SOCKS_VERSION or resp[1] != 0x00:
            raise RuntimeError("SOCKS5 upstream handshake failed")

        # 3. ارسال درخواست CONNECT به مقصد
        req = bytearray([self.SOCKS_VERSION, self.SOCKS_CMD_CONNECT, 0x00])
        # استفاده از domain name
        req.append(self.SOCKS_ATYP_DOMAIN)
        host_bytes = host.encode()
        req.append(len(host_bytes))
        req.extend(host_bytes)
        req.extend(struct.pack('>H', port))
        writer_proxy.write(req)
        await writer_proxy.drain()

        # 4. دریافت پاسخ
        resp = await reader_proxy.readexactly(4)
        if resp[0] != self.SOCKS_VERSION or resp[1] != 0x00:
            raise RuntimeError(f"SOCKS5 upstream connection failed: {resp[1]}")

        atyp = resp[3]
        # خواندن bind addr و port (بسته به نوع آدرس) – داده را می‌خوانیم اما ذخیره نمی‌کنیم
        if atyp == self.SOCKS_ATYP_IPV4:
            await reader_proxy.readexactly(4)
        elif atyp == self.SOCKS_ATYP_DOMAIN:
            length = await reader_proxy.readexactly(1)
            await reader_proxy.readexactly(length[0])
        elif atyp == self.SOCKS_ATYP_IPV6:
            await reader_proxy.readexactly(16)
        else:
            raise RuntimeError("Unknown address type in SOCKS5 response")
        await reader_proxy.readexactly(2)  # port

        # اکنون می‌توانیم TLS (در صورت نیاز) روی این سوکت SOCKS5 شده اعمال کنیم
        if port == 443 and self.profile.tls.server_name:
            server_name = self.profile.tls.server_name or host
            context = self._create_tls_context(server_name)
            try:
                wrapped_sock = context.wrap_socket(
                    sock, server_hostname=server_name
                )
            except Exception as e:
                print(f"[MimicryProxy] TLS handshake via upstream failed: {e}")
                sock.close()
                raise
            # ساخت reader/writer از سوکت SSL شده
            remote_reader, remote_writer = await asyncio.open_connection(sock=wrapped_sock)
        else:
            # بدون TLS – reader/writer فعلی از سوکت upstream (قبلاً در writer/reader باز بوده)
            remote_reader, remote_writer = reader_proxy, writer_proxy
        return remote_reader, remote_writer

    # -----------------------------------------------------------------
    # اتصال مستقیم (بدون upstream)
    # -----------------------------------------------------------------
    def _create_tls_context(self, server_hostname: str) -> ssl.SSLContext:
        tls_config = self.profile.tls

        if HAS_UTLS:
            client_hello_spec = UTLSClientHelloSpec(
                tls_config.ja3_fingerprint or "chrome_133",
            )
            return client_hello_spec.create_ssl_context()

        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        if tls_config.cipher_suites:
            cipher_string = ':'.join(tls_config.cipher_suites)
            try:
                ctx.set_ciphers(cipher_string)
            except ssl.SSLError:
                pass

        if tls_config.alpn_protocols:
            ctx.set_alpn_protocols(tls_config.alpn_protocols)

        if "TLSv1.3" in tls_config.supported_versions:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            ctx.maximum_version = ssl.TLSVersion.TLSv1_3
        elif "TLSv1.2" in tls_config.supported_versions:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2

        return ctx

    async def _connect_to_target(self, host: str, port: int
                                ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        loop = asyncio.get_event_loop()
        await loop.sock_connect(sock, (host, port))

        if port == 443 and self.profile.tls.server_name:
            server_name = self.profile.tls.server_name or host
            context = self._create_tls_context(server_name)
            try:
                wrapped_sock = context.wrap_socket(sock, server_hostname=server_name)
            except Exception as e:
                print(f"[MimicryProxy] TLS handshake failed: {e}")
                sock.close()
                raise
            reader, writer = await asyncio.open_connection(sock=wrapped_sock)
        else:
            reader, writer = await asyncio.open_connection(sock=sock)
        return reader, writer

    async def _relay_traffic(self, client_reader, client_writer,
                            remote_reader, remote_writer):
        async def forward(src, dst, direction):
            try:
                while self.running:
                    data = await src.read(8192)
                    if not data:
                        break
                    if direction == 'out' and self.profile.traffic.padding_max_bytes > 0:
                        padding = self.profile.get_padding_bytes()
                        if padding:
                            data += padding
                    if self.profile.traffic.jitter_enabled:
                        delay = self.profile.sample_delay_ms() / 1000.0
                        await asyncio.sleep(delay)
                    dst.write(data)
                    await dst.drain()
                    if self.profile.should_burst():
                        burst_size = self.profile.get_burst_size()
                        for _ in range(burst_size - 1):
                            if not self.running:
                                break
                            extra = await src.read(8192)
                            if not extra:
                                break
                            dst.write(extra)
                            await dst.drain()
                            await asyncio.sleep(self.profile.sample_delay_ms() / 1000.0)
                    silence_ms = self.profile.get_silence_ms()
                    if silence_ms > 0 and random.random() < 0.1:
                        await asyncio.sleep(silence_ms / 1000.0)
            except Exception:
                pass
            finally:
                dst.close()
                await dst.wait_closed()

        task1 = asyncio.create_task(forward(client_reader, remote_writer, 'out'))
        task2 = asyncio.create_task(forward(remote_reader, client_writer, 'in'))
        done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
