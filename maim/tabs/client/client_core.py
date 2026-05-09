# tabs/client/client_core.py
import os
import subprocess
import winreg
import ctypes
import json
import time
import threading
import zipfile
import io
import requests
import sys
import socket
from tkinter import messagebox

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from .mimicry.mimicry_proxy import MimicryProxy  # برای زنجیره سه‌لایه

PREVPN_PORT = 10811          # پورت inbound کانفیگ Pre‑VPN (لایه دوم)
MAIN_SOCKS_PORT = 10812      # پورت inbound کانفیگ Main (لایه سوم)
MIMICRY_PORT = 10810         # پورت پراکسی Mimicry (لایه اول)

# ثابت‌های Pre‑Processor (از config.py نیز تعریف می‌شود، اینجا برای اطمینان)
PREPROCESSOR_PORT = 10815


class ClientCore:
    """
    هسته اصلی کلاینت VPN
    مسئولیت‌ها:
        - اجرای Xray-core با کانفیگ انتخابی (Main)
        - اجرای Pre‑VPN (Xray) در صورت فعال بودن
        - مدیریت زنجیره سه‌لایه (Mimicry → Pre‑VPN → Main)
        - دانلود خودکار Xray-core در صورت عدم وجود
        - اعمال تنظیمات DPI Bypass (Fragment، FakeSNI، REALITY و ...)
        - مدیریت پروکسی سیستم (ویندوز)
        - Kill Switch با Windows Firewall
        - مانیتورینگ ترافیک
        - یکپارچگی با Pre‑Processor محلی
    """

    PREVPN_PORT = 10811          # پورت inbound SOCKS کانفیگ Pre‑VPN

    def __init__(self):
        self.xray_process = None       # پروسه اصلی Xray (Main config)
        self.prevpn_process = None     # پروسه Pre‑VPN Xray
        self.mimicry_proxy = None      # پراکسی Mimicry (در زنجیره سه‌لایه)
        self.is_connected = False
        self.status_callback = None
        self.traffic_callback = None
        self.proxy_callback = None
        self.selected_config_path = None
        self.var_tun = None

        # تنظیمات DPI Bypass
        self.dpi_settings = {}
        self.dpi_engine = None

        # Traffic Mimicry Manager (اختیاری)
        self.mimicry_manager = None
        self.app_controller = None     # ★ ارجاع به App اصلی (در صورت نیاز)

    # ========== Callback Setters ==========
    def set_callbacks(self, status_callback, traffic_callback, proxy_callback):
        self.status_callback = status_callback
        self.traffic_callback = traffic_callback
        self.proxy_callback = proxy_callback

    def set_dpi_settings(self, settings):
        self.dpi_settings = settings
        if settings:
            self.log_dpi_status("تنظیمات DPI Bypass دریافت شد")

    def set_mimicry_manager(self, mimicry_manager):
        self.mimicry_manager = mimicry_manager

    def log_status(self, text, color):
        if self.status_callback:
            self.status_callback(text, color)

    def log_dpi_status(self, msg):
        if self.status_callback:
            self.status_callback(f"🛡️ {msg}", "#F38020")

    def update_traffic(self, dl, ul):
        if self.traffic_callback:
            self.traffic_callback(dl, ul)

    # ========== Proxy Windows ==========
    def set_windows_proxy(self, enable=True, server="127.0.0.1:10809"):
        try:
            internet_settings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                0, winreg.KEY_ALL_ACCESS
            )
            if enable:
                winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, server)
            else:
                winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(internet_settings)
            internet_set_option = ctypes.windll.wininet.InternetSetOptionW
            internet_set_option(0, 37, 0, 0)
            internet_set_option(0, 39, 0, 0)
        except Exception as e:
            print(f"Proxy Error: {e}")

    # ========== Kill Switch (Windows Firewall) ==========
    def _resolve_host(self, host):
        try:
            socket.inet_aton(host)
            return [host]
        except Exception:
            try:
                ips = [addr[4][0] for addr in socket.getaddrinfo(host, None, socket.AF_INET)]
                return list(set(ips)) if ips else [host]
            except Exception:
                return [host]

    def _extract_remote_ips(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            outbounds = config.get('outbounds', [])
            for out in outbounds:
                if out.get('protocol') in ['vless', 'vmess']:
                    vnext = out.get('settings', {}).get('vnext', [{}])[0]
                    addr = vnext.get('address', '')
                    if addr:
                        return self._resolve_host(addr)
                elif out.get('protocol') in ['shadowsocks', 'trojan']:
                    server = out.get('settings', {}).get('servers', [{}])[0]
                    addr = server.get('address', '')
                    if addr:
                        return self._resolve_host(addr)
                elif out.get('protocol') == 'wireguard':
                    addr = out.get('settings', {}).get('address', '')
                    if addr:
                        return self._resolve_host(addr.split(',')[0].split('/')[0])
            return ["127.0.0.1"]
        except Exception:
            return ["127.0.0.1"]

    def _enable_kill_switch(self, remote_ips):
        try:
            self._disable_kill_switch()
            subprocess.run(
                'netsh advfirewall firewall add rule name="A_NetTools KS Allow Loopback" dir=out action=allow remoteip=127.0.0.1 protocol=any',
                shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            remote_ip_str = ','.join(remote_ips)
            subprocess.run(
                f'netsh advfirewall firewall add rule name="A_NetTools KS Allow VPN" dir=out action=allow remoteip={remote_ip_str} protocol=any',
                shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                'netsh advfirewall firewall add rule name="B_NetTools KS Block All" dir=out action=block protocol=any',
                shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.log_status("🛡️ Kill Switch فعال شد (فقط VPN و localhost مجازند)", "#66BB6A")
        except Exception as e:
            self.log_status(f"⚠️ خطا در فعال‌سازی Kill Switch: {e}", "#EF5350")

    def _disable_kill_switch(self):
        rules = [
            "A_NetTools KS Allow Loopback",
            "A_NetTools KS Allow VPN",
            "B_NetTools KS Block All"
        ]
        for rule in rules:
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{rule}"',
                shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

    # ========== پیدا کردن Xray ==========
    def find_xray_path(self, base_dir):
        possible_paths = [
            os.path.join(base_dir, "xray", "xray.exe"),
            os.path.join(base_dir, "xray.exe"),
            os.path.join(os.path.dirname(base_dir), "xray", "xray.exe"),
            os.path.join(os.path.dirname(os.path.dirname(base_dir)), "xray", "xray.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    # ========== دانلود خودکار Xray ==========
    def check_and_download_xray(self, base_dir, log_callback, status_callback):
        existing_xray = self.find_xray_path(base_dir)
        if existing_xray:
            return True

        xray_dir = os.path.join(base_dir, "xray")
        ans = messagebox.askyesno(
            "Xray-core یافت نشد",
            "Xray-core برای اتصال لازم است.\nآیا می‌خواهید آن را به طور خودکار دانلود کنید؟ (حدود ۲۰ مگابایت)"
        )
        if not ans:
            return False

        status_callback("⏳ در حال دانلود Xray...")
        threading.Thread(target=self._download_xray_thread, args=(xray_dir, log_callback, status_callback), daemon=True).start()
        return "DOWNLOADING"

    def _download_xray_thread(self, xray_dir, log_callback, status_callback):
        try:
            os.makedirs(xray_dir, exist_ok=True)
            log_callback("دریافت آخرین نسخه Xray...", "#F38020")
            api_url = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
            rel_info = requests.get(api_url, timeout=10).json()
            download_url = None
            for asset in rel_info.get("assets", []):
                if "windows-64.zip" in asset["name"]:
                    download_url = asset["browser_download_url"]
                    break
            if not download_url:
                raise Exception("نسخه ویندوز ۶۴ بیتی در آخرین ریلیز یافت نشد.")
            log_callback("در حال دانلود Xray-core... لطفاً صبر کنید", "#F38020")
            r = requests.get(download_url, stream=True, timeout=20)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(xray_dir)
            messagebox.showinfo("موفقیت", "Xray-core با موفقیت دانلود شد. اکنون می‌توانید متصل شوید.")
            log_callback("وضعیت: آماده اتصال", "gray")
        except Exception as e:
            messagebox.showerror("خطا در دانلود", f"دانلود خودکار انجام نشد:\n{str(e)}\n\nلطفاً Xray-core را دستی دانلود کرده و در پوشه 'xray' قرار دهید.")
            log_callback("وضعیت: قطع", "#EF5350")
        finally:
            status_callback("▶ CONNECT")

    # ========== اعمال Pre‑Processor در کانفیگ ==========
    def _apply_preprocessor_proxy(self, config_data, proxy_address):
        """اگر Pre‑Processor فعال باشد، یک outbound پروکسی SOCKS5 به کانفیگ اضافه می‌کند
        و تمام outboundهای اصلی (VLESS, VMess و ...) را از طریق آن هدایت می‌کند."""
        if not proxy_address:
            return config_data

        # پارس آدرس پروکسی
        if proxy_address.startswith("socks5://"):
            proxy_addr = proxy_address[9:]
        else:
            proxy_addr = proxy_address
        proxy_host, proxy_port_str = proxy_addr.split(":")
        proxy_port = int(proxy_port_str)

        # بررسی اینکه آیا از قبل پروکسی Pre‑Processor در کانفیگ وجود دارد
        existing_tags = {out.get("tag", "") for out in config_data.get("outbounds", [])}
        proxy_tag = "preprocessor_proxy"
        if proxy_tag not in existing_tags:
            # اضافه کردن outbound جدید برای Pre‑Processor
            proxy_outbound = {
                "tag": proxy_tag,
                "protocol": "socks",
                "settings": {
                    "servers": [{
                        "address": proxy_host,
                        "port": proxy_port
                    }]
                }
            }
            config_data.setdefault("outbounds", []).append(proxy_outbound)

        # اعمال proxySettings روی تمام outboundهای اصلی (VLESS, VMess, Trojan, Shadowsocks)
        for out in config_data.get("outbounds", []):
            if out.get("protocol") in ["vless", "vmess", "shadowsocks", "trojan"]:
                out["proxySettings"] = {"tag": proxy_tag}

        return config_data

    # ========== اعمال کامل DPI Bypass ==========
    def _apply_dpi_settings(self, config_path):
        if not self.dpi_settings or not os.path.exists(config_path):
            return

        self.log_dpi_status("اعمال تنظیمات DPI Bypass...")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            for outbound in config.get('outbounds', []):
                if 'streamSettings' not in outbound:
                    outbound['streamSettings'] = {}

                # TLS 1.3
                if self.dpi_settings.get('tls13'):
                    if 'tlsSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings'] = {}
                    outbound['streamSettings']['tlsSettings']['minVersion'] = '1.3'
                    outbound['streamSettings']['tlsSettings']['maxVersion'] = '1.3'
                    self.log_dpi_status("✅ TLS 1.3 فعال شد")

                # SNI Spoofing
                if self.dpi_settings.get('sni_spoof'):
                    fake_sni = self.dpi_settings.get('sni_target', 'www.google.com')
                    if 'tlsSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings'] = {}
                    outbound['streamSettings']['tlsSettings']['serverName'] = fake_sni
                    self.log_dpi_status(f"✅ SNI Spoofing فعال (جعلی: {fake_sni})")

                # REALITY
                if self.dpi_settings.get('reality'):
                    outbound['streamSettings']['security'] = 'reality'
                    if 'realitySettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['realitySettings'] = {}
                    outbound['streamSettings']['realitySettings']['serverName'] = self.dpi_settings.get('reality_sni', 'www.google.com')
                    outbound['streamSettings']['realitySettings']['fingerprint'] = 'chrome'
                    pubkey = self.dpi_settings.get('reality_pubkey', '')
                    if pubkey:
                        outbound['streamSettings']['realitySettings']['publicKey'] = pubkey
                    self.log_dpi_status(f"✅ REALITY فعال (سرور: {self.dpi_settings.get('reality_sni')})")

                # Packet Fragmentation
                if self.dpi_settings.get('fragment'):
                    if 'sockopt' not in outbound['streamSettings']:
                        outbound['streamSettings']['sockopt'] = {}
                    outbound['streamSettings']['sockopt']['fragment'] = {
                        "packets": self.dpi_settings.get('frag_packets', '1-1'),
                        "length": self.dpi_settings.get('frag_length', '10-20'),
                        "interval": self.dpi_settings.get('frag_interval', '5')
                    }
                    self.log_dpi_status(f"✅ Fragment فعال (packets: {self.dpi_settings.get('frag_packets')})")

                # FakeTLS
                if self.dpi_settings.get('fake_tls'):
                    if 'tlsSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings'] = {}
                    outbound['streamSettings']['tlsSettings']['fingerprint'] = 'chrome'
                    outbound['streamSettings']['tlsSettings']['alpn'] = ['h2', 'http/1.1']
                    self.log_dpi_status("✅ FakeTLS فعال (اثر انگشت Chrome)")

                # FakeHTTP
                if self.dpi_settings.get('fake_http'):
                    if 'httpSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['httpSettings'] = {}
                    outbound['streamSettings']['httpSettings']['method'] = 'GET'
                    outbound['streamSettings']['httpSettings']['host'] = [self.dpi_settings.get('fake_target', 'www.google.com')]
                    outbound['streamSettings']['httpSettings']['path'] = ['/']
                    self.log_dpi_status(f"✅ FakeHTTP فعال (target: {self.dpi_settings.get('fake_target', 'www.google.com')})")

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.log_dpi_status("✅ همه تنظیمات DPI Bypass اعمال شد.")

        except Exception as e:
            self.log_dpi_status(f"❌ خطا در اعمال DPI: {str(e)}")

    # ========== اعمال Traffic Mimicry در کانفیگ ==========
    def _apply_mimicry_to_config(self, config_data):
        if not self.mimicry_manager or not self.mimicry_manager.enabled:
            return config_data

        proxy_addr = self.mimicry_manager.get_proxy_address()
        proxy_host = "127.0.0.1"
        proxy_port = 10810
        if proxy_addr.startswith("socks5://"):
            addr_part = proxy_addr[9:]
            if ':' in addr_part:
                proxy_host, port_str = addr_part.split(':', 1)
                proxy_port = int(port_str)

        outbounds = config_data.get('outbounds', [])
        main_index = -1
        main_tag = None
        for i, ob in enumerate(outbounds):
            if ob.get('protocol') in ['vless', 'vmess', 'shadowsocks', 'trojan']:
                main_index = i
                main_tag = ob.get('tag', 'proxy')
                break

        if main_index == -1:
            self.log_dpi_status("❌ Outbound اصلی برای Traffic Mimicry یافت نشد.")
            return config_data

        mimicry_outbound = {
            "tag": main_tag,
            "protocol": "socks",
            "settings": {
                "servers": [{
                    "address": proxy_host,
                    "port": proxy_port
                }]
            }
        }
        outbounds[main_index] = mimicry_outbound
        config_data['outbounds'] = outbounds
        self.log_dpi_status(f"✅ Traffic Mimicry فعال شد - پراکسی محلی: {proxy_host}:{proxy_port}")
        return config_data

    # ========== Pre‑VPN Chain ==========
    def _start_pre_vpn(self, pre_vpn_config_path):
        if not pre_vpn_config_path or not os.path.exists(pre_vpn_config_path):
            self.log_status("Pre‑VPN config not found.", "#EF5350")
            return False

        xray_exe = self.find_xray_path(os.path.dirname(pre_vpn_config_path))
        if not xray_exe:
            xray_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "xray", "xray.exe")
            if not os.path.exists(xray_exe):
                self.log_status("Xray-core not found for Pre‑VPN.", "#EF5350")
                return False

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.prevpn_process = subprocess.Popen(
                [xray_exe, "-c", pre_vpn_config_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            time.sleep(1)
            if self.prevpn_process.poll() is not None:
                err = self.prevpn_process.stderr.read().decode('utf-8', errors='ignore')
                self.log_status(f"Pre‑VPN failed to start: {err[:200]}", "#EF5350")
                self.prevpn_process = None
                return False

            self.log_status(f"✅ Pre‑VPN started on port {self.PREVPN_PORT}", "#66BB6A")
            return True
        except Exception as e:
            self.log_status(f"Pre‑VPN error: {str(e)}", "#EF5350")
            return False

    def _stop_pre_vpn(self):
        if self.prevpn_process:
            self.prevpn_process.terminate()
            for _ in range(10):
                if self.prevpn_process.poll() is not None:
                    break
                time.sleep(0.1)
            if self.prevpn_process.poll() is None:
                self.prevpn_process.kill()
            self.prevpn_process.wait()
            self.prevpn_process = None
            self.log_status("Pre‑VPN stopped.", "gray")

    def _apply_prevpn_to_config(self, config_data):
        if not self.prevpn_process:
            return config_data

        outbounds = config_data.get('outbounds', [])
        main_index = -1
        main_tag = None
        for i, ob in enumerate(outbounds):
            if ob.get('protocol') in ['vless', 'vmess', 'shadowsocks', 'trojan']:
                main_index = i
                main_tag = ob.get('tag', 'proxy')
                break

        if main_index == -1:
            self.log_status("Main outbound not found for Pre‑VPN chaining.", "#EF5350")
            return config_data

        prevpn_outbound = {
            "tag": main_tag,
            "protocol": "socks",
            "settings": {
                "servers": [{
                    "address": "127.0.0.1",
                    "port": self.PREVPN_PORT
                }]
            }
        }
        outbounds[main_index] = prevpn_outbound
        config_data['outbounds'] = outbounds

        self.log_dpi_status(f"✅ Pre‑VPN Chain فعال شد: Main → 127.0.0.1:{self.PREVPN_PORT}")
        return config_data

    def _build_chain_pre_vpn_config(self, temp_path: str):
        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "listen": "127.0.0.1",
                "port": PREVPN_PORT,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True}
            }],
            "outbounds": [{
                "protocol": "socks",
                "tag": "chain_to_main",
                "settings": {
                    "servers": [{"address": "127.0.0.1", "port": MAIN_SOCKS_PORT}]
                }
            }]
        }
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    # ========== ابزار دقیق برای آزادسازی پورت ==========
    def _get_process_using_port(self, port):
        try:
            result = subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True, text=True)
            if not result.stdout.strip():
                return None, None
            for line in result.stdout.strip().split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit():
                        task = subprocess.run(f'tasklist /FI "PID eq {pid}" /FO CSV', shell=True, capture_output=True, text=True)
                        if task.stdout and len(task.stdout.split('\n')) >= 2:
                            name = task.stdout.split('\n')[1].split(',')[0].strip('"')
                            return pid, name
                        return pid, f"PID {pid}"
            return None, None
        except Exception:
            return None, None

    def _ensure_ports_free(self):
        messages = []
        all_ok = True
        for port in [10808, 10809, self.PREVPN_PORT, MIMICRY_PORT, MAIN_SOCKS_PORT, PREPROCESSOR_PORT]:
            pid, name = self._get_process_using_port(port)
            if pid:
                self.log_status(f"⚠️ پورت {port} توسط {name} (PID {pid}) اشغال شده.", "#FFA726")
                try:
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True, check=True)
                    messages.append(f"✅ {name} (PID {pid}) که پورت {port} را گرفته بود، بسته شد.")
                except subprocess.CalledProcessError:
                    messages.append(f"❌ نمی‌توان {name} (PID {pid}) را بست. لطفاً دستی ببندید یا برنامه را به عنوان Administrator اجرا کنید.")
                    all_ok = False
            else:
                messages.append(f"پورت {port} آزاد است.")
        return all_ok, "\n".join(messages)

    # ========== اتصال اصلی ==========
    def start_connection(self, selected_config_path, var_tun, base_dir, configs_dir,
                        mimicry_manager=None, pre_vpn_config_path=None, preprocessor_address=None):
        """
        پارامتر جدید:
            preprocessor_address: آدرس SOCKS5 پراکسی Pre‑Processor (مثلاً socks5://127.0.0.1:10815)
        """
        if not selected_config_path:
            messagebox.showerror("خطا", "لطفاً ابتدا یک کانفیگ را انتخاب کنید.")
            return False

        if mimicry_manager is not None:
            self.mimicry_manager = mimicry_manager

        # 1. آزادسازی پورت‌ها
        ports_ok, ports_msg = self._ensure_ports_free()
        if not ports_ok:
            messagebox.showerror(
                "پورت‌های مورد نیاز اشغال شده",
                f"پورت‌های لازم برای سرویس‌ها اشغال هستند.\n\n{ports_msg}\n\n"
                "لطفاً برنامه‌های مزاحم را ببندید یا برنامه را به عنوان Administrator اجرا کنید."
            )
            return False
        self.log_status("✅ پورت‌های مورد نیاز آزاد هستند.", "#66BB6A")

        # 2. اعمال DPI Bypass
        self._apply_dpi_settings(selected_config_path)

        # 3. پیدا کردن / دانلود Xray
        xray_exe = self.find_xray_path(base_dir)
        if not xray_exe:
            status = self.check_and_download_xray(base_dir, self.log_status, self.update_connect_button)
            if status == "DOWNLOADING":
                return False
            if not status:
                messagebox.showerror("Xray یافت نشد", f"فایل xray.exe در مسیر {os.path.join(base_dir, 'xray', 'xray.exe')} پیدا نشد.\nلطفاً آن را به صورت دستی قرار دهید.")
                return False
            xray_exe = self.find_xray_path(base_dir)
            if not xray_exe:
                return False
        self.log_status(f"✅ Xray پیدا شد: {xray_exe}", "#66BB6A")
        self.var_tun = var_tun

        # تشخیص زنجیره سه‌لایه (Mimicry فعال + Pre‑VPN انتخاب شده)
        three_layer_chain = (self.mimicry_manager and self.mimicry_manager.enabled
                            and pre_vpn_config_path is not None)

        # 4. آماده‌سازی لایه‌ها
        if three_layer_chain:
            profile = self.mimicry_manager.current_profile
            if not profile:
                self.log_status("❌ Mimicry profile not found.", "#EF5350")
                return False
            self.mimicry_proxy = MimicryProxy(
                profile,
                listen_host="127.0.0.1",
                listen_port=MIMICRY_PORT,
                upstream_proxy=f"127.0.0.1:{PREVPN_PORT}"
            )
            if not self.mimicry_proxy.start():
                self.log_status("❌ Could not start Mimicry proxy.", "#EF5350")
                return False
            self.log_status("✅ Mimicry proxy started (Layer 1)", "#66BB6A")

            temp_pre_vpn_path = os.path.join(configs_dir, "..", "Settings", "pre_vpn_chain_temp.json")
            os.makedirs(os.path.dirname(temp_pre_vpn_path), exist_ok=True)
            self._build_chain_pre_vpn_config(temp_pre_vpn_path)
            if not self._start_pre_vpn(temp_pre_vpn_path):
                self.log_status("❌ Could not start Pre‑VPN layer.", "#EF5350")
                self.mimicry_proxy.stop()
                self.mimicry_proxy = None
                return False
            self.log_status("✅ Pre‑VPN chain layer started (Layer 2)", "#66BB6A")
        else:
            if pre_vpn_config_path:
                if not self._start_pre_vpn(pre_vpn_config_path):
                    self.log_status("⚠️ Pre‑VPN راه‌اندازی نشد، ادامه با Main config.", "#FFA726")

        # 5. لود و پچ کردن کانفیگ Main
        backup_path = selected_config_path + ".backup"
        try:
            with open(selected_config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # ★ اعمال Pre‑Processor (قبل از زنجیره‌های دیگر)
            config_data = self._apply_preprocessor_proxy(config_data, preprocessor_address)

            if three_layer_chain:
                has_chain_socks = any(
                    ib.get('protocol') == 'socks' and ib.get('port') == MAIN_SOCKS_PORT
                    for ib in config_data.get('inbounds', [])
                )
                if not has_chain_socks:
                    config_data.setdefault('inbounds', []).append({
                        "listen": "127.0.0.1",
                        "port": MAIN_SOCKS_PORT,
                        "protocol": "socks",
                        "settings": {"auth": "noauth", "udp": True},
                        "tag": "main_chain_in"
                    })
                    self.log_dpi_status(f"✅ Main inbound added on port {MAIN_SOCKS_PORT}")
            else:
                if self.prevpn_process:
                    config_data = self._apply_prevpn_to_config(config_data)
                else:
                    if self.mimicry_manager and self.mimicry_manager.enabled:
                        config_data = self._apply_mimicry_to_config(config_data)

            # افزودن inboundهای استاندارد
            has_socks = any(ib.get('protocol') == 'socks' and ib.get('port') == 10808 for ib in config_data.get('inbounds', []))
            has_http = any(ib.get('protocol') == 'http' and ib.get('port') == 10809 for ib in config_data.get('inbounds', []))

            if not has_socks or not has_http:
                config_data['inbounds'] = [ib for ib in config_data.get('inbounds', [])
                                           if ib.get('protocol') not in ["socks", "http", "tun"]]

                config_data['inbounds'].extend([
                    {"listen": "127.0.0.1", "port": 10808, "protocol": "socks",
                     "settings": {"auth": "noauth", "udp": True},
                     "sniffing": {"destOverride": ["http", "tls"], "enabled": True}},
                    {"listen": "127.0.0.1", "port": 10809, "protocol": "http",
                     "settings": {"allowTransparent": False},
                     "sniffing": {"destOverride": ["http", "tls"], "enabled": True}}
                ])
            else:
                self.log_status("ℹ️ کانفیگ از قبل دارای inboundهای مورد نیاز است. پچ انجام نشد.", "#FFA726")

            # TUN Mode
            is_tun_enabled = var_tun.get()
            if is_tun_enabled:
                has_tun = any(ib.get('protocol') == 'tun' for ib in config_data.get('inbounds', []))
                if not has_tun:
                    config_data['inbounds'].append({
                        "tag": "tun-in",
                        "port": 10899,
                        "protocol": "tun",
                        "settings": {"autoRoute": True, "strictRoute": True, "stack": "system"}
                    })
                else:
                    self.log_status("ℹ️ TUN Mode قبلاً در کانفیگ وجود دارد.", "#FFA726")

            test_json = json.dumps(config_data, indent=2)
            json.loads(test_json)

            if not os.path.exists(backup_path):
                with open(backup_path, 'w', encoding='utf-8') as bf:
                    json.dump(config_data, bf, indent=2)

            with open(selected_config_path, 'w', encoding='utf-8') as f:
                f.write(test_json)

        except Exception as e:
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as bf:
                        original = json.load(bf)
                    with open(selected_config_path, 'w', encoding='utf-8') as f:
                        json.dump(original, f, indent=2)
                except:
                    pass
            messagebox.showerror("خطا در پچ کانفیگ",
                                 f"کانفیگ معتبر نیست یا ساختار آن قابل اصلاح نمی‌باشد.\n\n"
                                 f"خطا: {str(e)}\n\n"
                                 f"فایل اصلی به حالت اول برگردانده شد.")
            self._cleanup_layers()
            return False

        # Kill Switch
        remote_ips = self._extract_remote_ips(selected_config_path)
        self._enable_kill_switch(remote_ips)

        # 6. اجرای Xray Main
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.xray_process = subprocess.Popen(
                [xray_exe, "-c", selected_config_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            time.sleep(1)
            if self.xray_process.poll() is not None:
                err = self.xray_process.stderr.read().decode('utf-8', errors='ignore')
                self._disable_kill_switch()
                self._cleanup_layers()
                if "address already in use" in err.lower() or "bind" in err.lower():
                    _, msg = self._ensure_ports_free()
                    messagebox.showerror(
                        "خطای اشغال پورت",
                        f"Xray نتوانست پورت‌های مورد نیاز را باز کند.\n\n{msg}\n\n"
                        "لطفاً برنامه‌های مزاحم را ببندید و دوباره اتصال را امتحان کنید."
                    )
                elif "requires elevation" in err.lower() or "administrator" in err.lower():
                    messagebox.showerror("نیاز به دسترسی ادمین",
                        "حالت TUN Mode نیاز به دسترسی Administrator دارد.\n"
                        "لطفاً برنامه را با راست کلیک و Run as administrator اجرا کنید.")
                else:
                    messagebox.showerror("خطای Xray",
                                         f"Xray نتوانست با کانفیگ {os.path.basename(selected_config_path)} کار کند.\n\n"
                                         f"--- خطای Xray ---\n{err[:800]}\n\n"
                                         f"--- راهنمایی ---\n"
                                         f"1. مطمئن شوید کانفیگ معتبر است.\n"
                                         f"2. اگر کانفیگ از TLS استفاده می‌کند، گزینه 'security=none' را امتحان کنید.\n"
                                         f"3. فایل کانفیگ را در پوشهٔ configs به صورت دستی بررسی کنید.")
                self.xray_process = None
                return False

            # تنظیم پروکسی سیستم
            if three_layer_chain:
                self.set_windows_proxy(enable=True, server=f"127.0.0.1:{MIMICRY_PORT}")
                status_msg = "Connected (3-Layer Chain: Mimicry → Pre‑VPN → Main)"
            elif not is_tun_enabled:
                proxy_port = "10809"
                if preprocessor_address:
                    _, _, p = preprocessor_address.rpartition(":")
                    proxy_port = p if p else "10809"
                self.set_windows_proxy(enable=True, server=f"127.0.0.1:{proxy_port}")
                status_msg = f"Connected (System Proxy Routed{', via Pre‑Processor' if preprocessor_address else ''})"
            else:
                self.set_windows_proxy(enable=False)
                status_msg = "Connected (TUN Global Mode)"

            self.is_connected = True
            self.log_status(f"Status: {status_msg}", "#66BB6A")
            threading.Thread(target=self._traffic_monitor, daemon=True).start()

            if self.dpi_settings:
                self.log_dpi_status("DPI Bypass is active - your traffic is optimized")
            if three_layer_chain:
                profile_name = self.mimicry_manager.current_profile.name if self.mimicry_manager.current_profile else "Custom"
                self.log_dpi_status(f"3-Layer Chain active - Profile: {profile_name}")
            elif self.mimicry_manager and self.mimicry_manager.enabled:
                profile_name = self.mimicry_manager.current_profile.name if self.mimicry_manager.current_profile else "Custom"
                self.log_dpi_status(f"Traffic Mimicry active - Profile: {profile_name}")
            if self.prevpn_process:
                self.log_dpi_status("Pre‑VPN Chain is active")
            if preprocessor_address:
                self.log_dpi_status("Pre‑Processor is active - traffic shaped before leaving")

            return True

        except Exception as e:
            self._disable_kill_switch()
            self._cleanup_layers()
            messagebox.showerror("خطا در اتصال", f"خطا هنگام راه‌اندازی Xray:\n{str(e)}")
            return False

    def _cleanup_layers(self):
        if self.mimicry_proxy:
            self.mimicry_proxy.stop()
            self.mimicry_proxy = None

    # ========== مانیتورینگ ترافیک ==========
    def _traffic_monitor(self):
        if not HAS_PSUTIL:
            return
        last_io = psutil.net_io_counters()
        while self.is_connected:
            try:
                time.sleep(1)
                current_io = psutil.net_io_counters()
                dl_speed = (current_io.bytes_recv - last_io.bytes_recv) / 1024
                ul_speed = (current_io.bytes_sent - last_io.bytes_sent) / 1024
                last_io = current_io
                dl_str = f"{dl_speed:.1f} KB/s" if dl_speed < 1024 else f"{dl_speed/1024:.2f} MB/s"
                ul_str = f"{ul_speed:.1f} KB/s" if ul_speed < 1024 else f"{ul_speed/1024:.2f} MB/s"
                self.update_traffic(dl_str, ul_str)
            except Exception:
                time.sleep(1)
                continue

    # ========== قطع اتصال ==========
    def stop_connection(self):
        self._disable_kill_switch()

        if self.xray_process:
            self.xray_process.terminate()
            for _ in range(10):
                if self.xray_process.poll() is not None:
                    break
                time.sleep(0.1)
            if self.xray_process.poll() is None:
                self.xray_process.kill()
            self.xray_process.wait()
            self.xray_process = None

        self._stop_pre_vpn()

        if self.mimicry_proxy:
            self.mimicry_proxy.stop()
            self.mimicry_proxy = None

        self.set_windows_proxy(enable=False)
        self.is_connected = False
        self.log_status("Status: Disconnected", "#EF5350")
        self.update_traffic("0.0 KB/s", "0.0 KB/s")

        self._ensure_ports_free()

    # ========== به‌روزرسانی دکمه اتصال ==========
    def update_connect_button(self, text):
        if self.proxy_callback:
            self.proxy_callback(text)
