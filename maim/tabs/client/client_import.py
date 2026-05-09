# tabs/client/client_import.py
import os
import json
import time
import base64
import urllib.parse
import threading
import requests
from tkinter import messagebox
import customtkinter as ctk
from config import CF_ORANGE, storage_crypto
from tabs.crypto_manager import storage_crypto

try:
    from PIL import ImageGrab
    from pyzbar.pyzbar import decode
    HAS_QR_SCANNER = True
except ImportError:
    HAS_QR_SCANNER = False

from .client_utils import ClientUtils


class ClientImport:
    """مدیریت import کانفیگ‌ها - ساب، QR، کلیپ‌بورد، JSON"""

    def __init__(self, parent, configs_dir, load_configs_callback):
        self.parent = parent
        self.configs_dir = configs_dir
        self.load_configs_callback = load_configs_callback
        self.status_callback = None

    def set_status_callback(self, callback):
        self.status_callback = callback

    def import_sub_link(self, url):
        """import از سابسکریپشن لینک"""
        if not url:
            dialog = ctk.CTkInputDialog(text="Paste your Subscription URL here:", title="Import Subscription")
            url = dialog.get_input()
        if not url:
            return

        threading.Thread(target=self._fetch_sub_thread, args=(url,), daemon=True).start()

    def _fetch_sub_thread(self, url):
        """دریافت و پردازش سابسکریپشن در ترد جداگانه"""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            content = resp.text.strip()
            content += "=" * ((4 - len(content) % 4) % 4)
            try:
                decoded_data = base64.b64decode(content).decode('utf-8')
            except Exception:
                decoded_data = content

            lines = [line.strip() for line in decoded_data.splitlines() if line.strip()]
            imported_count = 0
            skipped_count = 0

            for line in lines:
                protocol = ClientUtils.detect_protocol(line)
                if protocol != "unknown":
                    try:
                        config_dict = ClientUtils.convert_to_json(line)
                        filename = f"{protocol.upper()}_{int(time.time()*1000)}_{imported_count}.json"
                        filepath = os.path.join(self.configs_dir, filename)
                        # استفاده از ذخیره‌سازی رمزنگاری شده
                        storage_crypto.save_json(filepath, config_dict)
                        imported_count += 1
                    except Exception as e:
                        skipped_count += 1
                        print(f"Failed to import: {line[:50]}... Error: {e}")
                else:
                    skipped_count += 1

            msg = f"🎉 Successfully imported {imported_count} configs!"
            if skipped_count > 0:
                msg += f"\n⚠️ Skipped {skipped_count} unsupported configs."
            self.parent.after(0, lambda: messagebox.showinfo("Success", msg))
            self.parent.after(0, self.load_configs_callback)
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Sub Error", f"Failed to fetch subscription:\n{str(e)}"))

    def import_from_clipboard(self):
        """import از کلیپ‌بورد"""
        try:
            clipboard_text = self.parent.clipboard_get().strip()
            if not clipboard_text:
                return
            self.process_imported_link(clipboard_text)
        except Exception:
            pass

    def import_from_qr(self):
        """import از QR code روی صفحه"""
        if not HAS_QR_SCANNER:
            messagebox.showerror("Error", "Please install required libraries:\npip install pillow pyzbar")
            return
        try:
            if self.status_callback:
                self.status_callback("Scanning screen...", CF_ORANGE)
            self.parent.update()
            screen = ImageGrab.grab()
            decoded_objects = decode(screen)
            if decoded_objects:
                self.process_imported_link(decoded_objects[0].data.decode('utf-8').strip())
            else:
                messagebox.showwarning("Not Found", "No QR Code found on the screen!")
        except Exception as e:
            messagebox.showerror("Scan Error", f"Failed to scan screen:\n{str(e)}")

    def process_imported_link(self, data):
        """پردازش لینک import شده (هر پروتکلی)"""
        data = data.strip()

        # اگر JSON مستقیم بود
        if data.startswith("{") and data.endswith("}"):
            try:
                parsed_json = json.loads(data)
                self.save_json_config(parsed_json)
                return
            except:
                pass

        # تشخیص پروتکل
        protocol = ClientUtils.detect_protocol(data)

        if protocol != "unknown":
            try:
                parsed_json = ClientUtils.convert_to_json(data)
                self.save_json_config(parsed_json)
            except Exception as e:
                messagebox.showerror("Parse Error", f"Failed to parse {protocol.upper()} link:\n{str(e)}")
        else:
            messagebox.showerror("Unsupported",
                "Unsupported protocol format.\n\n"
                "Supported protocols:\n"
                "• VLESS, VMESS, Shadowsocks, Trojan\n"
                "• Hysteria2, TUIC, WireGuard\n"
                "• SOCKS4/5, HTTP/HTTPS Proxy")

    def save_json_config(self, config_dict):
        """ذخیره کانفیگ JSON (رمزنگاری شده)"""
        remarks = config_dict.get('remarks', 'config')
        filename = f"Imported_{int(time.time()*100)}_{urllib.parse.quote(remarks[:10])}.json"
        filepath = os.path.join(self.configs_dir, filename)
        # ذخیره با رمزنگاری
        storage_crypto.save_json(filepath, config_dict)
        self.load_configs_callback()
        if "Sub" not in filename:
            messagebox.showinfo("Success", f"Config imported successfully!\nProtocol: {remarks[:50]}")
