# tabs/client/client_dpi.py
import subprocess
import threading
import time
import os
import sys
import tempfile
import requests
import json
from datetime import datetime


class DPIBypassEngine:
    """هسته اصلی DPI Bypass - مدیریت تکنیک‌های مختلف"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.running = False
        self.current_methods = []
        self.processes = []
        self.config_dir = None
        self.xray_config_path = None
        
    def log(self, msg, level="INFO"):
        if self.log_callback:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_callback(f"[{timestamp}] [{level}] {msg}")
    
    def set_xray_config(self, config_path):
        """مسیر فایل کانفیگ Xray-core را تنظیم می‌کند"""
        self.xray_config_path = config_path
    
    def apply_fragment(self, enabled=True, **params):
        """
        تکنیک Fragment - تکه‌تکه کردن بسته اول
        پارامترها:
        - packets: تعداد بسته‌ها (مثال: "1-1")
        - length: طول هر بسته (مثال: "10-20")
        - interval: فاصله بین بسته‌ها (مثال: "5")
        """
        if not enabled:
            self.log("Fragment: Disabled")
            return False
        
        packets = params.get('packets', '1-1')
        length = params.get('length', '10-20')
        interval = params.get('interval', '5')
        
        # در Xray-core از طریق sockopt fragment پشتیبانی می‌شود
        # باید کانفیگ Xray را patch کنیم
        if self.xray_config_path and os.path.exists(self.xray_config_path):
            try:
                with open(self.xray_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # اضافه کردن fragment به outbounds
                for outbound in config.get('outbounds', []):
                    if 'streamSettings' not in outbound:
                        outbound['streamSettings'] = {}
                    if 'sockopt' not in outbound['streamSettings']:
                        outbound['streamSettings']['sockopt'] = {}
                    
                    outbound['streamSettings']['sockopt']['fragment'] = {
                        "packets": packets,
                        "length": length,
                        "interval": interval
                    }
                
                with open(self.xray_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                self.log(f"Fragment applied: packets={packets}, length={length}, interval={interval}")
                return True
            except Exception as e:
                self.log(f"Fragment error: {str(e)}", "ERROR")
                return False
        return False
    
    def apply_fake_tls(self, enabled=True, target_host="www.google.com"):
        """
        تکنیک FakeTLS - جعل ترافیک به عنوان HTTPS عادی
        از طریق GoodbyeDPI یا ابزار مشابه
        """
        if not enabled:
            self.log("FakeTLS: Disabled")
            return False
        
        # در اینجا می‌توانیم GoodbyeDPI را راه‌اندازی کنیم
        # یا از تکنیک‌های داخلی Xray استفاده کنیم
        try:
            # روش اول: استفاده از GoodbyeDPI (اگر نصب باشد)
            goodbye_path = self._find_goodbyedpi()
            if goodbye_path:
                self._run_goodbyedpi(goodbye_path, target_host)
                self.log(f"FakeTLS enabled via GoodbyeDPI (target: {target_host})")
                return True
            else:
                # روش دوم: شبیه‌سازی داخلی
                self.log("FakeTLS: GoodbyeDPI not found, using internal method")
                return self._apply_internal_fake_tls(target_host)
        except Exception as e:
            self.log(f"FakeTLS error: {str(e)}", "ERROR")
            return False
    
    def _find_goodbyedpi(self):
        """پیدا کردن فایل اجرایی GoodbyeDPI"""
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), "goodbyedpi.exe"),
            os.path.join(os.getcwd(), "goodbyedpi.exe"),
            "C:\\Program Files\\GoodbyeDPI\\goodbyedpi.exe",
            "goodbyedpi.exe"  # در PATH
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        # بررسی با which
        import shutil
        return shutil.which("goodbyedpi.exe")
    
    def _run_goodbyedpi(self, exe_path, target_host):
        """اجرای GoodbyeDPI در پس‌زمینه"""
        # پارامترهای معمول GoodbyeDPI برای FakeTLS
        cmd = [
            exe_path,
            "-1",  # حالت Passive DPI
            "--fake-tls",  # فعال کردن FakeTLS
            "--fake-http",  # فعال کردن FakeHTTP
            "--dns-addr", "1.1.1.1",  # DNS
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        self.processes.append(proc)
    
    def _apply_internal_fake_tls(self, target_host):
        """شبیه‌سازی داخلی FakeTLS با استفاده از پارامترهای Xray"""
        if self.xray_config_path and os.path.exists(self.xray_config_path):
            try:
                with open(self.xray_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # تنظیمات برای شبیه‌سازی TLS
                for outbound in config.get('outbounds', []):
                    if 'streamSettings' not in outbound:
                        outbound['streamSettings'] = {}
                    
                    # تنظیم TLS با Fingerprint شبیه مرورگر
                    outbound['streamSettings']['security'] = 'tls'
                    if 'tlsSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings'] = {}
                    
                    outbound['streamSettings']['tlsSettings']['serverName'] = target_host
                    outbound['streamSettings']['tlsSettings']['fingerprint'] = 'chrome'
                    outbound['streamSettings']['tlsSettings']['alpn'] = ['h2', 'http/1.1']
                
                with open(self.xray_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                return True
            except Exception as e:
                self.log(f"Internal FakeTLS error: {str(e)}", "ERROR")
        return False
    
    def apply_fake_http(self, enabled=True):
        """تکنیک FakeHTTP - ارسال بسته‌های جعلی HTTP قبل از درخواست اصلی"""
        if not enabled:
            self.log("FakeHTTP: Disabled")
            return False
        
        try:
            # می‌توانیم از ابزارهای خارجی مثل GoodbyeDPI یا ByeDPI استفاده کنیم
            goodbye_path = self._find_goodbyedpi()
            if goodbye_path:
                # GoodbyeDPI به صورت خودکار FakeHTTP را اعمال می‌کند
                self.log("FakeHTTP enabled via GoodbyeDPI")
                return True
            else:
                self.log("FakeHTTP: GoodbyeDPI not found", "WARNING")
                return False
        except Exception as e:
            self.log(f"FakeHTTP error: {str(e)}", "ERROR")
            return False
    
    def apply_sni_spoofing(self, enabled=True, fake_sni="www.google.com"):
        """تکنیک SNI Spoofing - جعل نام سرور"""
        if not enabled:
            self.log("SNI Spoofing: Disabled")
            return False
        
        if self.xray_config_path and os.path.exists(self.xray_config_path):
            try:
                with open(self.xray_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for outbound in config.get('outbounds', []):
                    if 'streamSettings' not in outbound:
                        outbound['streamSettings'] = {}
                    
                    # تنظیم SNI جعلی در TLS settings
                    if 'tlsSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings'] = {}
                    
                    outbound['streamSettings']['tlsSettings']['serverName'] = fake_sni
                    
                    # همچنین می‌توانیم sni را در تنظیمات اصلی اضافه کنیم
                    if 'settings' in outbound and 'vnext' in outbound['settings']:
                        for vnext in outbound['settings']['vnext']:
                            vnext['sni'] = fake_sni
                
                with open(self.xray_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                self.log(f"SNI Spoofing applied: {fake_sni}")
                return True
            except Exception as e:
                self.log(f"SNI Spoofing error: {str(e)}", "ERROR")
        return False
    
    def apply_tls13(self, enabled=True):
        """فعال‌سازی TLS 1.3 برای امنیت بیشتر"""
        if not enabled:
            self.log("TLS 1.3: Disabled")
            return False
        
        if self.xray_config_path and os.path.exists(self.xray_config_path):
            try:
                with open(self.xray_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for outbound in config.get('outbounds', []):
                    if 'streamSettings' not in outbound:
                        outbound['streamSettings'] = {}
                    
                    if 'tlsSettings' not in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings'] = {}
                    
                    # فعال‌سازی TLS 1.3
                    outbound['streamSettings']['tlsSettings']['allowInsecure'] = False
                    # تنظیمات TLS 1.3
                    if 'tlsSettings' in outbound['streamSettings']:
                        outbound['streamSettings']['tlsSettings']['minVersion'] = '1.3'
                        outbound['streamSettings']['tlsSettings']['maxVersion'] = '1.3'
                
                with open(self.xray_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                self.log("TLS 1.3 enabled")
                return True
            except Exception as e:
                self.log(f"TLS 1.3 error: {str(e)}", "ERROR")
        return False
    
    def apply_reality(self, enabled=True, server_name="www.google.com", public_key="", short_id=""):
        """
        پروتکل REALITY - پیشرفته‌ترین روش ضد فیلترینگ
        نیاز به سرور REALITY در سمت دیگر دارد
        """
        if not enabled:
            self.log("REALITY: Disabled")
            return False
        
        self.log("REALITY: This requires a REALITY-enabled server side", "WARNING")
        self.log("REALITY: Configure your server with REALITY protocol first")
        
        if self.xray_config_path and os.path.exists(self.xray_config_path):
            try:
                with open(self.xray_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for outbound in config.get('outbounds', []):
                    if outbound.get('protocol') == 'vless':
                        if 'streamSettings' not in outbound:
                            outbound['streamSettings'] = {}
                        
                        outbound['streamSettings']['security'] = 'reality'
                        if 'realitySettings' not in outbound['streamSettings']:
                            outbound['streamSettings']['realitySettings'] = {}
                        
                        outbound['streamSettings']['realitySettings']['serverName'] = server_name
                        outbound['streamSettings']['realitySettings']['fingerprint'] = 'chrome'
                        
                        if public_key:
                            outbound['streamSettings']['realitySettings']['publicKey'] = public_key
                        if short_id:
                            outbound['streamSettings']['realitySettings']['shortId'] = short_id
                
                with open(self.xray_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                self.log(f"REALITY configured: {server_name}")
                return True
            except Exception as e:
                self.log(f"REALITY error: {str(e)}", "ERROR")
        return False
    
    def apply_ech(self, enabled=True, ech_config=""):
        """
        تکنیک ECH (Encrypted ClientHello) - رمزنگاری کامل ClientHello
        """
        if not enabled:
            self.log("ECH: Disabled")
            return False
        
        # ECH در Xray-core به صورت مستقیم پشتیبانی نمی‌شود
        # می‌توانیم از پروکسی‌های جانبی استفاده کنیم
        self.log("ECH: Requires additional proxy configuration", "WARNING")
        return False
    
    def stop_all(self):
        """توقف همه پروسه‌های جانبی و پاکسازی"""
        self.running = False
        for proc in self.processes:
            try:
                proc.terminate()
            except:
                pass
        self.processes.clear()
        self.log("All DPI bypass engines stopped")
