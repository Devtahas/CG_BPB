# tabs/tools/fastly_scanner.py

import customtkinter as ctk
from tkinter import messagebox
import asyncio
import threading
import ipaddress
import json
import time
import random
import base64
import urllib.parse
import os
import socket
import ssl
import struct                       # ★ برای SOCKS5
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

try:
    import dns.resolver
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

from config import CF_ORANGE, BG_PANEL, DIRS
from tabs.crypto_manager import storage_crypto

# ---------- ثابت‌های SOCKS5 ----------
SOCKS_VERSION = 0x05
SOCKS_CMD_CONNECT = 0x01
SOCKS_ATYP_IPV4 = 0x01
SOCKS_ATYP_DOMAIN = 0x03
SOCKS_ATYP_IPV6 = 0x04
SOCKS_AUTH_NONE = 0x00

# ==========================================
# لیست‌های پیش‌فرض Fastly (fallback)
# ==========================================
DEFAULT_FASTLY_CIDRS = [
    "23.235.32.0/20",
    "43.249.72.0/22",
    "103.244.50.0/24",
    "103.244.51.0/24",
    "104.156.80.0/20",
    "146.75.0.0/17",
    "151.101.0.0/16",
    "157.52.64.0/18",
    "167.82.0.0/17",
    "167.82.128.0/17",
    "172.111.64.0/18",
    "185.31.16.0/22",
    "199.27.72.0/21",
    "199.232.0.0/16",
    "202.21.128.0/17",
    "203.57.145.0/24",
    "23.235.33.0/24",
    "23.235.34.0/23",
    "104.156.81.0/24",
    "146.75.0.0/17",
]

DEFAULT_CF_PORTS = [443, 2053, 2083, 2087, 2096, 8443]

FINGERPRINTS = ["chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq"]

BROWSER_HEADERS = {
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DEFAULT_WORKER_HOST = "vless-worker.pages.dev"
DEFAULT_WORKER_PATH = "/ws"
MAIN_SOCKS_PORT = 10808
MAX_CONCURRENT_TASKS = 500


class FastlyScanner(ctk.CTkFrame):
    """اسکنر Fastly: یافتن IPهای تمیز Fastly و ساخت کانفیگ VLESS"""

    def __init__(self, parent, tabview, asset_manager=None):
        self.parent = parent
        self.tab = tabview.add("🌩️ Fastly Scanner")
        self.asset_manager = asset_manager
        self.setup_ui()
        self.scan_stop_flag = False
        self.results = []
        self.best_dns = None
        self.enabled_ports = DEFAULT_CF_PORTS.copy()
        self.found_ips = []
        self.proxy_address = None            # ★ تنظیم خودکار هنگام شروع اسکن

    # ======================== UI ========================
    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        header_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(header_frame, text="🌩️ Fastly Clean IP Scanner",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 5))
        ctk.CTkLabel(header_frame, text="Scan Fastly edge IPs that can reach your Cloudflare Worker",
                     text_color="gray").pack(pady=(0, 15))

        # Fastly CIDRs
        ctk.CTkLabel(scroll, text="🎯 Fastly IP Ranges (CIDRs):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.cidr_text = ctk.CTkTextbox(scroll, height=150, font=ctk.CTkFont(size=11))
        self.cidr_text.pack(fill="x", padx=20, pady=5)

        if self.asset_manager:
            cidrs = self.asset_manager.get_ip_list("fastly")
            if not cidrs:
                cidrs = DEFAULT_FASTLY_CIDRS
        else:
            cidrs = DEFAULT_FASTLY_CIDRS
        self.cidr_text.insert("1.0", "\n".join(cidrs))

        # Worker Host & Path
        worker_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        worker_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(worker_frame, text="🌐 Worker Host (Real SNI):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.real_host_entry = ctk.CTkEntry(worker_frame, placeholder_text="vless-worker.pages.dev")
        self.real_host_entry.pack(fill="x", padx=20, pady=5)
        self.real_host_entry.insert(0, DEFAULT_WORKER_HOST)

        path_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        path_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(path_frame, text="📁 Worker Path:",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.worker_path = ctk.CTkEntry(path_frame, placeholder_text="/ws")
        self.worker_path.pack(fill="x", padx=20, pady=5)
        self.worker_path.insert(0, DEFAULT_WORKER_PATH)

        # Ports
        ports_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ports_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(ports_frame, text="🔌 Scan Ports (comma-separated):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.ports_entry = ctk.CTkEntry(ports_frame, placeholder_text="443,2053,2083,2087,2096,8443")
        self.ports_entry.pack(fill="x", padx=20, pady=5)
        self.ports_entry.insert(0, ",".join(map(str, DEFAULT_CF_PORTS)))

        # Fragment Settings
        frag_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        frag_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(frag_frame, text="🧩 Fragment (Anti-DPI):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        frag_inner = ctk.CTkFrame(frag_frame, fg_color="transparent")
        frag_inner.pack(fill="x", padx=20, pady=5)
        self.frag_enable = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frag_inner, text="Enable", variable=self.frag_enable).pack(side="left")
        ctk.CTkLabel(frag_inner, text="Packets:").pack(side="left", padx=(20, 2))
        self.frag_packets = ctk.CTkEntry(frag_inner, width=60)
        self.frag_packets.insert(0, "1-1")
        self.frag_packets.pack(side="left", padx=2)
        ctk.CTkLabel(frag_inner, text="Length:").pack(side="left", padx=(10, 2))
        self.frag_length = ctk.CTkEntry(frag_inner, width=70)
        self.frag_length.insert(0, "10-20")
        self.frag_length.pack(side="left", padx=2)
        ctk.CTkLabel(frag_inner, text="Interval:").pack(side="left", padx=(10, 2))
        self.frag_interval = ctk.CTkEntry(frag_inner, width=60)
        self.frag_interval.insert(0, "5")
        self.frag_interval.pack(side="left", padx=2)

        # VLESS UUID
        ctk.CTkLabel(scroll, text="🔑 VLESS UUID:",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.uuid_entry = ctk.CTkEntry(scroll, placeholder_text="Your VLESS UUID")
        self.uuid_entry.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(scroll, text="Generate Random UUID", fg_color="transparent", border_width=1,
                      border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.generate_uuid).pack(anchor="w", padx=20, pady=(0, 15))

        # DNS Servers
        ctk.CTkLabel(scroll, text="📡 DNS Servers to Test:",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.dns_text = ctk.CTkTextbox(scroll, height=100, font=ctk.CTkFont(size=11))
        self.dns_text.pack(fill="x", padx=20, pady=5)

        if self.asset_manager:
            dns_list = self.asset_manager.get_dns_list()
        else:
            dns_list = [
                "178.22.122.100",  # Shecan
                "185.51.200.2",
                "78.157.42.100",   # Electro
                "78.157.42.101",
            ]
        self.dns_text.insert("1.0", "\n".join(dns_list))

        # Sliders
        self.lbl_threads = ctk.CTkLabel(scroll, text="Max Connections: 500")
        self.lbl_threads.pack(anchor="w", padx=20)
        self.threads_slider = ctk.CTkSlider(scroll, from_=100, to=2000, progress_color=CF_ORANGE,
                                            command=lambda v: self.lbl_threads.configure(text=f"Max Connections: {int(v)}"))
        self.threads_slider.set(MAX_CONCURRENT_TASKS)
        self.threads_slider.pack(fill="x", padx=20, pady=5)

        self.lbl_timeout = ctk.CTkLabel(scroll, text="Timeout: 5.0s")
        self.lbl_timeout.pack(anchor="w", padx=20)
        self.timeout_slider = ctk.CTkSlider(scroll, from_=2.0, to=15.0, progress_color="#29B6F6",
                                            command=lambda v: self.lbl_timeout.configure(text=f"Timeout: {float(v):.1f}s"))
        self.timeout_slider.set(5.0)
        self.timeout_slider.pack(fill="x", padx=20, pady=5)

        self.lbl_samples = ctk.CTkLabel(scroll, text="Samples per CIDR: 100")
        self.lbl_samples.pack(anchor="w", padx=20)
        self.samples_slider = ctk.CTkSlider(scroll, from_=10, to=500, progress_color="#AB47BC",
                                            command=lambda v: self.lbl_samples.configure(text=f"Samples per CIDR: {int(v)}"))
        self.samples_slider.set(100)
        self.samples_slider.pack(fill="x", padx=20, pady=5)

        # Action Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.start_btn = ctk.CTkButton(btn_frame, text="▶ START SCAN", fg_color=CF_ORANGE, text_color="black",
                                       command=self.start_scan)
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ STOP", fg_color="#C62828", state="disabled",
                                      command=self.stop_scan)
        self.stop_btn.grid(row=0, column=1, padx=5, sticky="ew")
        self.export_btn = ctk.CTkButton(btn_frame, text="📁 Export", fg_color="#2E7D32",
                                        command=self.export_configs)
        self.export_btn.grid(row=0, column=2, padx=5, sticky="ew")
        self.copy_sub_btn = ctk.CTkButton(btn_frame, text="🔗 Copy Sub", fg_color="#1565C0",
                                          command=self.copy_subscription)
        self.copy_sub_btn.grid(row=0, column=3, padx=5, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(scroll, progress_color=CF_ORANGE)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.status_label = ctk.CTkLabel(scroll, text="Ready", text_color="gray")
        self.status_label.pack(pady=5)
        self.results_text = ctk.CTkTextbox(scroll, height=250, font=ctk.CTkFont(family="Consolas", size=11))
        self.results_text.pack(fill="both", expand=True, pady=10)

    def generate_uuid(self):
        import uuid
        self.uuid_entry.delete(0, "end")
        self.uuid_entry.insert(0, str(uuid.uuid4()))

    def parse_cidrs(self):
        text = self.cidr_text.get("1.0", "end-1c").strip()
        cidrs = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    ipaddress.ip_network(line, strict=False)
                    cidrs.append(line)
                except:
                    self.log(f"⚠️ Invalid CIDR: {line}")
        return cidrs

    def parse_dns_list(self):
        text = self.dns_text.get("1.0", "end-1c").strip()
        dns_list = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                dns_list.append(line.split()[0])
        return dns_list

    def parse_ports_list(self):
        text = self.ports_entry.get().strip()
        ports = []
        for part in text.replace(" ", "").split(","):
            if part.isdigit():
                p = int(part)
                if 1 <= p <= 65535 and p not in ports:
                    ports.append(p)
        return ports if ports else DEFAULT_CF_PORTS

    def log(self, msg):
        self.parent.after(0, lambda: self.results_text.insert("end", msg + "\n"))
        self.parent.after(0, lambda: self.results_text.see("end"))

    # ======================== DNS Testing ========================
    def test_dns(self, dns_ip, domain="aparat.com", timeout=3):
        if not HAS_DNSPYTHON:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((dns_ip, 53))
                sock.close()
                return {"dns": dns_ip, "latency": 0, "valid": True}
            except:
                return {"dns": dns_ip, "latency": 9999, "valid": False}
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_ip]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            start = time.time()
            answers = resolver.resolve(domain, 'A')
            latency = int((time.time() - start) * 1000)
            if answers:
                return {"dns": dns_ip, "latency": latency, "valid": True}
            return {"dns": dns_ip, "latency": 9999, "valid": False}
        except:
            return {"dns": dns_ip, "latency": 9999, "valid": False}

    def find_best_dns(self, dns_list):
        self.log("🔍 Testing DNS (Real Query)...")
        test_domain = "aparat.com"
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.test_dns, dns, test_domain): dns for dns in dns_list}
            for future in as_completed(futures):
                res = future.result()
                if res['valid']:
                    results.append(res)
                    self.log(f"  ✅ DNS {res['dns']} - {res['latency']}ms")
        if not results:
            self.log("⚠️ No working DNS found! Falling back to Shecan DNS")
            return "178.22.122.100"
        best = min(results, key=lambda x: x['latency'])
        self.log(f"🏆 Best DNS: {best['dns']} ({best['latency']}ms)")
        return best['dns']

    # ======================== شروع اسکن ========================
    def start_scan(self):
        cidrs = self.parse_cidrs()
        uuid = self.uuid_entry.get().strip()
        real_host = self.real_host_entry.get().strip()
        path = self.worker_path.get().strip()
        dns_list = self.parse_dns_list()
        self.enabled_ports = self.parse_ports_list()

        if not cidrs or not uuid or not real_host or not dns_list:
            messagebox.showerror("Error", "Fill all required fields!")
            return
        if not path.startswith('/'):
            path = '/' + path

        # ★ هماهنگی با Pre‑Processor
        app = self.parent.master
        if hasattr(app, 'preprocessor') and app.preprocessor.is_running():
            self.proxy_address = f"socks5://127.0.0.1:{app.preprocessor.listen_port}"
            self.log("[*] Pre‑Processor proxy active. All traffic will be routed through it.")
        else:
            self.proxy_address = None

        self.scan_stop_flag = False
        self.results = []
        self.best_dns = None
        self.found_ips = []
        self.results_text.delete("1.0", "end")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)

        threading.Thread(target=self._scan_thread,
                         args=(cidrs, dns_list, real_host, path),
                         daemon=True).start()

    def _scan_thread(self, cidrs, dns_list, real_host, path):
        self.best_dns = self.find_best_dns(dns_list)
        samples = int(self.samples_slider.get())
        max_concurrent = int(self.threads_slider.get())
        timeout = self.timeout_slider.get()

        all_ips = []
        for cidr in cidrs:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                total = net.num_addresses
                sample_count = min(samples, total)
                if total <= sample_count:
                    ips = [str(ip) for ip in net]
                else:
                    ips = list({str(net[random.randint(0, total - 1)]) for _ in range(sample_count)})
                all_ips.extend(ips)
                self.log(f"📡 {cidr} -> {len(ips)} IPs")
            except Exception as e:
                self.log(f"❌ Error parsing {cidr}: {str(e)}")

        all_ips = list(set(all_ips))
        total_ips = len(all_ips)
        self.log(f"\n🔍 Testing {total_ips} IPs on ports {self.enabled_ports} ...")

        asyncio.run(self._async_scan(all_ips, timeout, real_host, path, max_concurrent, total_ips))

    async def _async_scan(self, all_ips, timeout, real_host, path, max_concurrent, total_ips):
        sem = asyncio.Semaphore(max_concurrent)
        scanned = 0
        tasks = []

        async def worker(ip, port):
            nonlocal scanned
            async with sem:
                if self.scan_stop_flag:
                    return
                success, latency = await self._async_test_ip(ip, port, timeout, real_host, path)
                scanned += 1
                self.parent.after(0, lambda s=scanned, t=total_ips: self.progress_bar.set(s / t if t else 0))
                self.parent.after(0, lambda s=scanned, t=total_ips, f=len(self.found_ips):
                                  self.status_label.configure(text=f"Progress: {s}/{t} | Found: {f}"))
                if success:
                    if not any(r['ip'] == ip for r in self.found_ips):
                        self.found_ips.append({
                            "ip": ip,
                            "port": port,
                            "latency": latency
                        })
                        self.log(f"✅ CLEAN IP: {ip}:{port} - {latency}ms")

        for ip in all_ips:
            for port in self.enabled_ports:
                tasks.append(asyncio.create_task(worker(ip, port)))

        await asyncio.gather(*tasks, return_exceptions=True)

        self.found_ips.sort(key=lambda x: x['latency'])
        self.results = self.found_ips
        self.log(f"\n🎉 Found {len(self.found_ips)} clean Fastly IPs.")
        if self.found_ips:
            self.generate_configs()

        self.parent.after(0, lambda: self.start_btn.configure(state="normal"))
        self.parent.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.parent.after(0, lambda: self.status_label.configure(text="Scan completed", text_color="#66BB6A"))

    # ======================== Async SOCKS5 Helper ========================
    async def _async_connect_with_proxy(self, host, port, timeout):
        """برقراری اتصال از طریق پروکسی SOCKS5 یا مستقیم"""
        if not self.proxy_address:
            return await asyncio.wait_for(asyncio.open_connection(host=host, port=port), timeout=timeout)

        proxy_url = self.proxy_address
        if proxy_url.startswith("socks5://"):
            proxy_url = proxy_url[9:]
        proxy_host, _, proxy_port_str = proxy_url.partition(':')
        proxy_port = int(proxy_port_str) if proxy_port_str else 1080

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=proxy_host, port=proxy_port), timeout=timeout
        )

        # Handshake
        writer.write(bytes([SOCKS_VERSION, 1, SOCKS_AUTH_NONE]))
        await writer.drain()
        resp = await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
        if resp[0] != SOCKS_VERSION or resp[1] != 0:
            writer.close()
            raise ConnectionError("SOCKS5 handshake failed")

        # Connect request
        try:
            ip_bytes = socket.inet_pton(socket.AF_INET, host)
            addr_type = SOCKS_ATYP_IPV4
            addr_data = ip_bytes
        except socket.error:
            addr_type = SOCKS_ATYP_DOMAIN
            domain_bytes = host.encode()
            addr_data = len(domain_bytes).to_bytes(1, 'big') + domain_bytes

        port_bytes = struct.pack('>H', port)
        request = bytes([SOCKS_VERSION, SOCKS_CMD_CONNECT, 0, addr_type]) + addr_data + port_bytes
        writer.write(request)
        await writer.drain()

        resp = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
        if resp[0] != SOCKS_VERSION or resp[1] != 0:
            writer.close()
            raise ConnectionError("SOCKS5 connect request failed")

        atyp = resp[3]
        if atyp == SOCKS_ATYP_IPV4:
            await reader.readexactly(4)
        elif atyp == SOCKS_ATYP_DOMAIN:
            length = await reader.readexactly(1)
            await reader.readexactly(ord(length))
        elif atyp == SOCKS_ATYP_IPV6:
            await reader.readexactly(16)
        await reader.readexactly(2)  # bind port

        return reader, writer

    async def _async_test_ip(self, ip, port, timeout, real_host, path):
        """تست TLS+WebSocket به سمت IP فستلی با SNI دامنه worker"""
        try:
            start = time.time()
            reader, writer = await self._async_connect_with_proxy(ip, port, timeout)

            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            tls_transport = await asyncio.wait_for(
                asyncio.start_tls(
                    reader, writer,
                    ssl_context=ssl_ctx,
                    server_hostname=real_host   # SNI = worker host
                ),
                timeout=timeout
            )
            tls_reader, tls_writer = tls_transport

            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {real_host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                + "".join(f"{k}: {v}\r\n" for k, v in BROWSER_HEADERS.items()) +
                "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            ).encode()

            tls_writer.write(request)
            await tls_writer.drain()

            response = await asyncio.wait_for(tls_reader.read(4096), timeout=timeout)
            total_time = int((time.time() - start) * 1000)
            response_text = response.decode(errors='ignore')

            tls_writer.close()
            await tls_writer.wait_closed()

            if "101 Switching Protocols" in response_text or "upgrade: websocket" in response_text.lower():
                return True, total_time
            if "Upgrade" in response_text and "websocket" in response_text:
                return True, total_time
            return False, total_time
        except Exception:
            return False, 0

    # ======================== Config Generation ========================
    def _get_recommended_fragment(self):
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5).json()
            isp = resp.get("isp", "").lower()
            org = resp.get("org", "").lower()
        except:
            isp, org = "", ""
        if any(kw in isp or kw in org for kw in ['mci', 'hamrah']):
            return {"packets": "1-1", "length": "10-20", "interval": "5"}
        elif any(kw in isp or kw in org for kw in ['mtn', 'irancell']):
            return {"packets": "1-1", "length": "1-3", "interval": "10"}
        elif 'rightel' in isp:
            return {"packets": "1-1", "length": "20-40", "interval": "5"}
        else:
            return {"packets": "1-1", "length": "100-200", "interval": "1"}

    def generate_configs(self):
        if not self.found_ips:
            return

        uuid = self.uuid_entry.get().strip()
        real_host = self.real_host_entry.get().strip()
        path = self.worker_path.get().strip()
        best_dns = self.best_dns or "178.22.122.100"

        frag_params = None
        if self.frag_enable.get():
            frag_params = self._get_recommended_fragment()
            self.log(f"🧩 Auto Fragment applied: {frag_params}")

        if not path.startswith('/'):
            path = '/' + path

        configs_dir = DIRS["configs"]
        subs_dir = DIRS["subs"]
        os.makedirs(configs_dir, exist_ok=True)
        os.makedirs(subs_dir, exist_ok=True)

        vless_links = []
        for result in self.found_ips:
            ip = result['ip']
            port = result['port']
            latency = result['latency']
            selected_fp = random.choice(FINGERPRINTS)

            ws_headers = {"Host": real_host, **BROWSER_HEADERS}

            outbound = {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": ip,
                        "port": port,
                        "users": [{"id": uuid, "encryption": "none"}]
                    }]
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "tls",
                    "tlsSettings": {
                        "serverName": real_host,
                        "alpn": ["h2", "http/1.1"],
                        "fingerprint": selected_fp,
                        "utls": {
                            "enabled": True,
                            "fingerprint": selected_fp
                        }
                    },
                    "wsSettings": {
                        "path": path,
                        "headers": ws_headers
                    },
                    "sockopt": {
                        "tcpFastOpen": True,
                        "tcpKeepAliveInterval": 30,
                        "domainStrategy": "UseIP"
                    }
                }
            }

            if frag_params:
                outbound["streamSettings"]["sockopt"]["fragment"] = frag_params

            config = {
                "remarks": f"[Fastly] {ip}:{port} ({latency}ms)",
                "log": {"loglevel": "warning"},
                "dns": {
                    "servers": [{"address": best_dns, "tag": "remote-dns"}]
                },
                "inbounds": [
                    {
                        "listen": "127.0.0.1",
                        "port": MAIN_SOCKS_PORT,
                        "protocol": "socks",
                        "settings": {"auth": "noauth", "udp": True},
                        "sniffing": {"destOverride": ["http", "tls"], "enabled": True, "routeOnly": True}
                    }
                ],
                "outbounds": [
                    outbound,
                    {"protocol": "dns", "tag": "dns-out"},
                    {"protocol": "freedom", "tag": "direct"}
                ],
                "routing": {
                    "domainStrategy": "IPIfNonMatch",
                    "rules": [
                        {"inboundTag": ["remote-dns"], "outboundTag": "proxy", "type": "field"},
                        {"network": "tcp", "outboundTag": "proxy", "type": "field"}
                    ]
                }
            }

            filename = f"[Fastly] WS_{ip}_{port}.json"
            filepath = os.path.join(configs_dir, filename)
            storage_crypto.save_json(filepath, config)

            alias = urllib.parse.quote(f"Fastly {ip}:{port} ({latency}ms)")
            vless_link = (f"vless://{uuid}@{ip}:{port}?encryption=none&security=tls"
                          f"&sni={real_host}&type=ws&host={real_host}&path={urllib.parse.quote(path)}"
                          f"&fp={selected_fp}&alpn=h2,http/1.1#{alias}")
            if frag_params:
                vless_link += f"&fragment={frag_params['packets']},{frag_params['length']},{frag_params['interval']}"
            vless_links.append(vless_link)

        sub_content = base64.b64encode("\n".join(vless_links).encode()).decode()
        sub_path = os.path.join(subs_dir, "fastly_sub.txt")
        with storage_crypto.safe_open(sub_path, 'w', encoding='utf-8') as f:
            f.write(sub_content)

        self.log(f"✅ Generated {len(vless_links)} Fastly configs with correct SNI")
        self.log(f"🔗 Subscription saved to {sub_path}")

    def export_configs(self):
        if not self.found_ips:
            messagebox.showwarning("Warning", "No configs to export.")
            return
        os.startfile(DIRS["configs"])

    def copy_subscription(self):
        sub_path = os.path.join(DIRS["subs"], "fastly_sub.txt")
        try:
            with storage_crypto.safe_open(sub_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.parent.clipboard_clear()
            self.parent.clipboard_append(content)
            messagebox.showinfo("Copied", "Subscription copied!")
        except:
            if os.path.exists(sub_path):
                with open(sub_path, 'r') as f:
                    content = f.read()
                self.parent.clipboard_clear()
                self.parent.clipboard_append(content)
                messagebox.showinfo("Copied", "Subscription copied!")
            else:
                messagebox.showwarning("Warning", "No subscription file found.")

    def stop_scan(self):
        self.scan_stop_flag = True
        self.status_label.configure(text="Stopping...", text_color="#FFA726")
