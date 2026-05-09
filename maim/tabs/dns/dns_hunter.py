# tabs/dns/dns_hunter.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import concurrent.futures
import time
import socket
import ssl
import json
import os
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Optional, Any

import requests
from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter
from tabs.crypto_manager import storage_crypto

from config import CF_ORANGE, BG_PANEL, DIRS

try:
    import dns.resolver
    import dns.exception
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


class TLSAdapter(HTTPAdapter):
    """
    Adapter سفارشی برای ارسال requests با IP مستقیم و SNI دستی
    """
    def __init__(self, ip: str, sni: str, *args, **kwargs):
        self._ip = ip
        self._sni = sni
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['assert_hostname'] = self._sni
        kwargs['server_hostname'] = self._sni
        super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        conn.assert_hostname = self._sni
        conn.ssl_context = ssl.create_default_context()
        conn.ssl_context.check_hostname = True
        conn.ssl_context.verify_mode = ssl.CERT_REQUIRED
        super().cert_verify(conn, url, verify, cert)


class DNSHunter:
    """
    اسکنر هوشمند DNS برای یافتن DNSهای کلین بر اساس دامنه هدف
    """

    # لیست پیش‌فرض فقط در صورت نبود AssetManager استفاده می‌شود
    DEFAULT_DNS_LIST_FALLBACK = [
        "1.1.1.1", "1.0.0.1",
        "8.8.8.8", "8.8.4.4",
        "9.9.9.9", "149.112.112.112",
        "208.67.222.222", "208.67.220.220",
        "94.140.14.14", "94.140.15.15",
        "185.228.168.9", "185.228.169.9",
        "8.26.56.26", "8.20.247.20",
        "64.6.64.6", "64.6.65.6",
        "84.200.69.80", "84.200.70.40",
        "77.88.8.8", "77.88.8.1",
        "209.244.0.3", "209.244.0.4",
        "156.154.70.1", "156.154.71.1",
        "76.76.19.19", "76.76.2.2",
        "78.157.42.100", "78.157.42.101",
        "178.22.122.100", "185.51.200.2",
        "10.202.10.10", "10.202.10.11",
        "185.55.226.26", "185.55.225.25",
        "217.218.127.10", "217.218.127.20",
        "114.114.114.114", "223.5.5.5", "180.76.76.76",
        "77.88.8.7", "77.88.8.3",
    ]

    def __init__(self, app_controller=None, asset_manager=None):
        self.app_controller = app_controller
        self.asset_manager = asset_manager          # ★ انبار مرکزی منابع
        self.results: List[Dict[str, Any]] = []
        self.stop_flag = False
        self.scan_history: List[Dict[str, Any]] = []
        self._pending_after_ids = []

        self.hunter_config_file = os.path.join(DIRS["settings"], "dns_hunter_config.json")
        self.hunter_list_file = os.path.join(DIRS["settings"], "dns_hunter_list.txt")
        self.history_file = os.path.join(DIRS["settings"], "dns_hunter_history.json")

        self.dns_list = self._load_dns_list()
        self.settings = self._load_settings()
        self._load_history()

        self.target_entry = None
        self.scan_btn = None
        self.stop_btn = None
        self.progress_bar = None
        self.status_label = None
        self.results_frame = None
        self.dns_count_label = None
        self.threads_slider = None
        self.timeout_slider = None
        self.lbl_threads = None
        self.lbl_timeout = None
        self.verify_service_var = None

    # =================================================================
    # مدیریت فایل‌ها و تنظیمات (هماهنگ با AssetManager)
    # =================================================================
    def _load_dns_list(self) -> List[str]:
        """بارگذاری لیست DNS از AssetManager یا فایل محلی"""
        if self.asset_manager:
            return self.asset_manager.get_dns_list()

        # رفتار قبلی برای زمانی که asset_manager وجود ندارد
        dns_servers = []
        try:
            with storage_crypto.safe_open(self.hunter_list_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        ip = parts[0]
                        if self._is_valid_ip(ip):
                            dns_servers.append(ip)
        except Exception:
            pass

        if not dns_servers and os.path.exists(self.hunter_list_file):
            try:
                with open(self.hunter_list_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            ip = parts[0]
                            if self._is_valid_ip(ip):
                                dns_servers.append(ip)
                if dns_servers:
                    self._save_dns_list()
            except Exception:
                pass

        if not dns_servers:
            dns_servers = self.DEFAULT_DNS_LIST_FALLBACK.copy()

        seen = set()
        unique_dns = []
        for dns in dns_servers:
            if dns not in seen:
                seen.add(dns)
                unique_dns.append(dns)
        return unique_dns

    def _save_dns_list(self) -> bool:
        """ذخیره لیست DNS در فایل محلی (فقط اگر AssetManager نباشد)"""
        if self.asset_manager:
            # اگر AssetManager هست، ذخیره‌سازی را به آن واگذار می‌کنیم
            self.asset_manager.update_dns_list(self.dns_list)
            return True

        try:
            content = "# DNS Hunter List - One IP per line\n"
            content += "# Lines starting with # are ignored\n"
            for dns in self.dns_list:
                content += f"{dns}\n"
            with storage_crypto.safe_open(self.hunter_list_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def _load_settings(self) -> Dict[str, Any]:
        default_settings = {
            "threads": 30,
            "timeout": 2.0,
            "test_tcp": True,
            "sync_to_scanner": True,
            "auto_save_results": True,
            "last_target": "telegram.org",
            "verify_service": False
        }
        data = storage_crypto.load_json(self.hunter_config_file)
        if data is not None:
            default_settings.update(data)
        return default_settings

    def save_settings(self) -> None:
        storage_crypto.save_json(self.hunter_config_file, self.settings)

    def _load_history(self) -> None:
        data = storage_crypto.load_json(self.history_file)
        if data is not None:
            self.scan_history = data
        else:
            self.scan_history = []

    def _save_history(self) -> None:
        try:
            if len(self.scan_history) > 50:
                self.scan_history = self.scan_history[-50:]
            storage_crypto.save_json(self.history_file, self.scan_history)
        except Exception:
            pass

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            return all(0 <= int(p) <= 255 for p in parts)
        except:
            return False

    def get_dns_count(self) -> int:
        return len(self.dns_list)

    def add_dns_to_list(self, dns_ip: str) -> bool:
        if self._is_valid_ip(dns_ip) and dns_ip not in self.dns_list:
            self.dns_list.append(dns_ip)
            self._save_dns_list()
            if self.dns_count_label:
                self.dns_count_label.configure(text=f"DNS Count: {len(self.dns_list)}")
            return True
        return False

    def remove_dns_from_list(self, dns_ip: str) -> bool:
        if dns_ip in self.dns_list:
            self.dns_list.remove(dns_ip)
            self._save_dns_list()
            if self.dns_count_label:
                self.dns_count_label.configure(text=f"DNS Count: {len(self.dns_list)}")
            return True
        return False

    def import_dns_from_file(self, filepath: str) -> tuple[int, List[str]]:
        try:
            added = 0
            errors = []
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    ip = parts[0]
                    if self._is_valid_ip(ip):
                        if ip not in self.dns_list:
                            self.dns_list.append(ip)
                            added += 1
                    else:
                        errors.append(f"Line {line_num}: Invalid IP '{ip}'")
            if added > 0:
                self._save_dns_list()
            return added, errors
        except Exception as e:
            return 0, [str(e)]

    # =================================================================
    # راه‌اندازی UI
    # =================================================================
    def setup_hunter_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        title_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(title_frame, text="🎯 DNS Hunter", font=ctk.CTkFont(size=20, weight="bold"),
                    text_color=CF_ORANGE).pack(side="left")
        ctk.CTkLabel(title_frame, text="Find clean DNS for specific target", text_color="gray").pack(side="left", padx=10)

        info_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 5))
        self.dns_count_label = ctk.CTkLabel(info_frame, text=f"DNS Count: {len(self.dns_list)}", text_color="gray")
        self.dns_count_label.pack(side="left")
        ctk.CTkButton(info_frame, text="📂 Import DNS List", width=120, fg_color="transparent",
                     border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                     command=self.import_dns_dialog).pack(side="right", padx=5)
        ctk.CTkButton(info_frame, text="📋 Manage List", width=120, fg_color="transparent",
                     border_width=1, border_color="#29B6F6", text_color="#29B6F6",
                     command=self.open_dns_manager).pack(side="right", padx=5)

        target_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=12)
        target_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(target_frame, text="🌐 Target Domain / URL:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 0))
        target_input_frame = ctk.CTkFrame(target_frame, fg_color="transparent")
        target_input_frame.pack(fill="x", padx=15, pady=10)
        self.target_entry = ctk.CTkEntry(target_input_frame, placeholder_text="e.g., telegram.org, chatgpt.com", height=35)
        self.target_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.target_entry.insert(0, self.settings.get("last_target", "telegram.org"))

        if self.scan_history:
            history_targets = list(set([h.get("target", "") for h in self.scan_history[-5:]]))
            if history_targets:
                self.history_combo = ctk.CTkComboBox(
                    target_input_frame, values=history_targets, width=150,
                    command=lambda v: self.target_entry.delete(0, "end") or self.target_entry.insert(0, v))
                self.history_combo.pack(side="right")
                self.history_combo.set("Recent")

        settings_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=12)
        settings_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(settings_frame, text="⚙️ Scan Settings", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5))

        thread_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        thread_frame.pack(fill="x", padx=15, pady=5)
        self.lbl_threads = ctk.CTkLabel(thread_frame, text=f"Threads: {self.settings['threads']}")
        self.lbl_threads.pack(side="left")
        self.threads_slider = ctk.CTkSlider(thread_frame, from_=5, to=100, width=200,
                                           progress_color=CF_ORANGE,
                                           command=lambda v: self.lbl_threads.configure(text=f"Threads: {int(v)}"))
        self.threads_slider.set(self.settings['threads'])
        self.threads_slider.pack(side="left", padx=15)

        timeout_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        timeout_frame.pack(fill="x", padx=15, pady=5)
        self.lbl_timeout = ctk.CTkLabel(timeout_frame, text=f"Timeout: {self.settings['timeout']}s")
        self.lbl_timeout.pack(side="left")
        self.timeout_slider = ctk.CTkSlider(timeout_frame, from_=1.0, to=10.0, width=200,
                                           progress_color="#29B6F6",
                                           command=lambda v: self.lbl_timeout.configure(text=f"Timeout: {float(v):.1f}s"))
        self.timeout_slider.set(self.settings['timeout'])
        self.timeout_slider.pack(side="left", padx=15)

        check_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        check_frame.pack(fill="x", padx=15, pady=(5, 10))
        self.test_tcp_var = ctk.BooleanVar(value=self.settings.get("test_tcp", True))
        ctk.CTkCheckBox(check_frame, text="Test TCP Connection (port 443)", variable=self.test_tcp_var,
                       fg_color=CF_ORANGE).pack(side="left", padx=10)
        self.sync_scanner_var = ctk.BooleanVar(value=self.settings.get("sync_to_scanner", True))
        ctk.CTkCheckBox(check_frame, text="Auto-sync to CF Scanner", variable=self.sync_scanner_var,
                       fg_color="#66BB6A").pack(side="left", padx=10)
        # **** چک‌باکس جدید برای تست سرویس واقعی ****
        self.verify_service_var = ctk.BooleanVar(value=self.settings.get("verify_service", False))
        ctk.CTkCheckBox(check_frame, text="Verify Service Access (HTTPS test)", variable=self.verify_service_var,
                        fg_color="#EF5350").pack(side="left", padx=10)

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=6)
        self.scan_btn = ctk.CTkButton(btn_frame, text="🔍 Start DNS Hunt", fg_color=CF_ORANGE, text_color="black",
                                     font=ctk.CTkFont(weight="bold"), command=self.start_hunt)
        self.scan_btn.pack(side="left", padx=5)
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ Stop", fg_color="#C62828", text_color="white",
                                     state="disabled", command=self.stop_hunt)
        self.stop_btn.pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📊 Export Results", fg_color="#1565C0", text_color="white",
                     command=self.export_results).pack(side="right", padx=5)

        self.progress_bar = ctk.CTkProgressBar(scroll, progress_color=CF_ORANGE)
        self.progress_bar.pack(fill="x", pady=6)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(scroll, text="Ready", text_color="gray")
        self.status_label.pack()

        result_header = ctk.CTkFrame(scroll, fg_color="transparent")
        result_header.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(result_header, text="✅ Clean DNS Found:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.sort_var = ctk.StringVar(value="Latency")
        sort_combo = ctk.CTkComboBox(result_header, values=["Latency", "Reachable First", "Service Verified First"],
                                    width=160, variable=self.sort_var, command=self._sort_results)
        sort_combo.pack(side="right")

        self.results_frame = ctk.CTkScrollableFrame(scroll, fg_color="transparent", height=300)
        self.results_frame.pack(fill="both", expand=True)

        bottom_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=10)
        ctk.CTkButton(bottom_frame, text="📋 Copy All Clean DNS", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.copy_all_results).pack(side="left", padx=5)
        ctk.CTkButton(bottom_frame, text="➕ Add to My DNS List", fg_color="transparent", border_width=1,
                     border_color="#29B6F6", text_color="#29B6F6", command=self.add_all_to_dns_list).pack(side="left", padx=5)

    # =================================================================
    # دیالوگ‌ها
    # =================================================================
    def import_dns_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Import DNS List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            added, errors = self.import_dns_from_file(filepath)
            if added > 0:
                messagebox.showinfo("Import Successful", f"Added {added} DNS servers.")
            if errors:
                messagebox.showwarning("Import Warnings", "\n".join(errors[:10]))
            self.dns_count_label.configure(text=f"DNS Count: {len(self.dns_list)}")

    def open_dns_manager(self):
        dialog = ctk.CTkToplevel()
        dialog.title("Manage DNS List")
        dialog.geometry("450x500")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_PANEL)

        ctk.CTkLabel(dialog, text="📋 DNS List Manager", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=CF_ORANGE).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent", height=300)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        def refresh_list():
            for w in scroll.winfo_children():
                w.destroy()
            for dns in self.dns_list:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=dns, width=150, anchor="w").pack(side="left", padx=5)
                ctk.CTkButton(row, text="🗑️", width=30, fg_color="transparent", text_color="#EF5350",
                             command=lambda d=dns: (self.remove_dns_from_list(d), refresh_list())).pack(side="right")

        refresh_list()

        add_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        add_frame.pack(fill="x", padx=20, pady=10)
        new_dns_entry = ctk.CTkEntry(add_frame, placeholder_text="Enter IP (e.g., 8.8.8.8)")
        new_dns_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(add_frame, text="Add", width=60, fg_color=CF_ORANGE, text_color="black",
                     command=lambda: (self.add_dns_to_list(new_dns_entry.get().strip()),
                                    new_dns_entry.delete(0, "end"), refresh_list(),
                                    self.dns_count_label.configure(text=f"DNS Count: {len(self.dns_list)}"))).pack(side="right")

        ctk.CTkButton(dialog, text="Close", fg_color="gray", command=dialog.destroy).pack(pady=15)

    # =================================================================
    # منطق اسکن
    # =================================================================
    def start_hunt(self):
        if not HAS_DNSPYTHON:
            messagebox.showerror("Error", "dnspython library is required. Please install it.")
            return

        target = self.target_entry.get().strip()
        if not target:
            messagebox.showerror("Error", "Please enter a target domain or URL.")
            return

        self.settings["threads"] = int(self.threads_slider.get())
        self.settings["timeout"] = self.timeout_slider.get()
        self.settings["test_tcp"] = self.test_tcp_var.get()
        self.settings["sync_to_scanner"] = self.sync_scanner_var.get()
        self.settings["last_target"] = target
        self.settings["verify_service"] = self.verify_service_var.get()
        self.save_settings()

        parsed = urlparse(target if '://' in target else f'http://{target}')
        domain = parsed.netloc if parsed.netloc else parsed.path
        if ':' in domain:
            domain = domain.split(':')[0]
        if not domain:
            messagebox.showerror("Error", "Invalid domain.")
            return

        for aid in self._pending_after_ids:
            try:
                self.results_frame.after_cancel(aid)
            except:
                pass
        self._pending_after_ids.clear()

        for w in self.results_frame.winfo_children():
            w.destroy()
        self.results = []
        self.stop_flag = False

        self.scan_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text=f"Testing {len(self.dns_list)} DNS against {domain}...", text_color=CF_ORANGE)
        self.progress_bar.set(0)

        threading.Thread(target=self._run_hunt, args=(domain,), daemon=True).start()

    def stop_hunt(self):
        self.stop_flag = True
        self.status_label.configure(text="Stopping...", text_color="#FFA726")

    def _verify_service_access(self, dns_ip: str, domain: str, timeout: float = 5.0) -> bool:
        """
        تست دسترسی واقعی به سرویس با استفاده از DNS داده شده
        """
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_ip]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            answers = resolver.resolve(domain, 'A')
            target_ip = str(answers[0])

            url = f"https://{target_ip}/"
            headers = {
                "Host": domain,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            }
            session = requests.Session()
            adapter = TLSAdapter(target_ip, domain)
            session.mount("https://", adapter)
            resp = session.get(url, headers=headers, timeout=timeout, verify=False)
            return resp.status_code < 400
        except Exception:
            return False

    def _run_hunt(self, domain: str):
        total = len(self.dns_list)
        completed = 0
        results = []
        timeout = self.settings["timeout"]
        test_tcp = self.settings["test_tcp"]

        def test_dns(dns_ip: str) -> Optional[Dict[str, Any]]:
            if self.stop_flag:
                return None
            try:
                start = time.time()
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_ip]
                resolver.timeout = timeout
                resolver.lifetime = timeout
                answers_a = resolver.resolve(domain, 'A')
                latency = int((time.time() - start) * 1000)
                resolved_ips = [str(r) for r in answers_a]

                has_ipv6 = False
                try:
                    answers_aaaa = resolver.resolve(domain, 'AAAA')
                    resolved_ips.extend([str(r) for r in answers_aaaa])
                    has_ipv6 = True
                except:
                    pass

                reachable = False
                if test_tcp and resolved_ips:
                    for ip in resolved_ips[:2]:
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(min(timeout, 2.0))
                            sock.connect((ip, 443))
                            sock.close()
                            reachable = True
                            break
                        except:
                            continue

                return {
                    "dns": dns_ip,
                    "latency": latency,
                    "ips": resolved_ips,
                    "has_ipv6": has_ipv6,
                    "reachable": reachable,
                    "status": "OK"
                }
            except dns.resolver.NXDOMAIN:
                return {"dns": dns_ip, "latency": 9999, "ips": [], "status": "NXDOMAIN", "reachable": False}
            except dns.resolver.Timeout:
                return {"dns": dns_ip, "latency": 9999, "ips": [], "status": "Timeout", "reachable": False}
            except dns.exception.DNSException:
                return {"dns": dns_ip, "latency": 9999, "ips": [], "status": "DNS Error", "reachable": False}
            except Exception:
                return {"dns": dns_ip, "latency": 9999, "ips": [], "status": "Failed", "reachable": False}

        max_workers = self.settings["threads"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(test_dns, dns): dns for dns in self.dns_list}
            for future in concurrent.futures.as_completed(futures):
                if self.stop_flag:
                    break
                res = future.result()
                completed += 1
                self._update_progress(completed / total, f"Progress: {completed}/{total}")
                if res and res.get("status") == "OK":
                    results.append(res)
                    self._add_result_card(res)

        # 🔧 اصلاح: ذخیره نتایج در متغیر سراسری (قبلاً جا افتاده بود)
        self.results = results

        # ================================================================
        # ** بخش تست تأیید سرویس **
        # ================================================================
        if self.settings.get("verify_service", False) and not self.stop_flag:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.after(0, lambda: self.status_label.configure(
                    text="Verifying service access...", text_color=CF_ORANGE))
            for res in results:
                if self.stop_flag:
                    break
                if res.get("reachable"):
                    if self._verify_service_access(res['dns'], domain):
                        res['service_ok'] = True
                    else:
                        res['service_ok'] = False
                        res['reachable'] = False
            # یکباره همه را مرتب و بازسازی کن
            self._sort_results()
        # ================================================================

        # همگام‌سازی با اسکنر (از طریق AssetManager اگر موجود باشد)
        if self.settings["sync_to_scanner"]:
            self._sync_to_scanner(results)

        self.scan_history.append({
            "timestamp": datetime.now().isoformat(),
            "target": domain,
            "total_tested": total,
            "found": len(results),
            "best_dns": results[0]["dns"] if results else None,
            "best_latency": results[0]["latency"] if results else None
        })
        self._save_history()

        self._update_ui_after_scan(len(results))

    def _update_progress(self, val: float, text: str):
        try:
            self.progress_bar.set(val)
            self.status_label.configure(text=text)
        except:
            pass

    def _add_result_card(self, result: Dict[str, Any]):
        def _add():
            if not hasattr(self, 'results_frame') or not self.results_frame.winfo_exists():
                return
            # حذف کارت قبلی برای این DNS (در صورت وجود)
            for child in self.results_frame.winfo_children():
                if hasattr(child, 'dns_ip') and child.dns_ip == result['dns']:
                    child.destroy()
                    break

            card = ctk.CTkFrame(self.results_frame, fg_color=BG_PANEL, corner_radius=8)
            card.dns_ip = result['dns']
            card.pack(fill="x", pady=3, padx=2)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(5, 0))
            ctk.CTkLabel(top, text=result['dns'], font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")
            latency_color = "#66BB6A" if result['latency'] < 150 else ("#FFA726" if result['latency'] < 300 else "#EF5350")
            ctk.CTkLabel(top, text=f"{result['latency']} ms", text_color=latency_color,
                        font=ctk.CTkFont(weight="bold")).pack(side="right")

            mid = ctk.CTkFrame(card, fg_color="transparent")
            mid.pack(fill="x", padx=10)
            ips = result.get('ips', [])
            ips_text = ", ".join(ips[:3]) + ("..." if len(ips) > 3 else "")
            ctk.CTkLabel(mid, text=f"Resolved: {ips_text}", text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left")

            bottom = ctk.CTkFrame(card, fg_color="transparent")
            bottom.pack(fill="x", padx=10, pady=(0, 5))

            status_text = ""
            if result.get('reachable'):
                status_text += "🟢 TCP "
            else:
                status_text += "🟡 "
            if result.get('has_ipv6'):
                status_text += "🌐 IPv6 "

            # نمایش وضعیت تأیید سرویس
            if result.get('service_ok'):
                status_text += "✅ Service "
            elif 'service_ok' in result and result['service_ok'] is False:
                status_text += "❌ Service "

            ctk.CTkLabel(bottom, text=status_text, text_color="gray", font=ctk.CTkFont(size=10)).pack(side="left")

            copy_btn = ctk.CTkButton(bottom, text="Copy", width=50, fg_color="transparent", border_width=1,
                                    border_color=CF_ORANGE, text_color=CF_ORANGE,
                                    command=lambda d=result['dns']: self._copy_to_clipboard(d))
            copy_btn.pack(side="right", padx=2)

            retest_btn = ctk.CTkButton(bottom, text="↻", width=30, fg_color="transparent", border_width=1,
                                      border_color="#29B6F6", text_color="#29B6F6",
                                      command=lambda d=result['dns']: self._retest_single(d))
            retest_btn.pack(side="right", padx=2)

        if hasattr(self, 'results_frame') and self.results_frame.winfo_exists():
            after_id = self.results_frame.after(0, _add)
            self._pending_after_ids.append(after_id)

    def _retest_single(self, dns_ip: str):
        target = self.target_entry.get().strip()
        if not target:
            return
        parsed = urlparse(target if '://' in target else f'http://{target}')
        domain = parsed.netloc if parsed.netloc else parsed.path
        if ':' in domain:
            domain = domain.split(':')[0]

        def _test():
            try:
                start = time.time()
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_ip]
                resolver.timeout = self.settings["timeout"]
                resolver.lifetime = self.settings["timeout"]
                answers = resolver.resolve(domain, 'A')
                latency = int((time.time() - start) * 1000)
                self.results_frame.after(0, lambda: messagebox.showinfo(
                    "Retest Result",
                    f"DNS: {dns_ip}\nLatency: {latency} ms\nResolved: {len(answers)} IPs"
                ))
            except Exception as e:
                self.results_frame.after(0, lambda: messagebox.showerror(
                    "Retest Failed",
                    f"DNS: {dns_ip}\nError: {str(e)}"
                ))
        threading.Thread(target=_test, daemon=True).start()

    def _sort_results(self, *args):
        if not self.results:
            return

        for aid in self._pending_after_ids:
            try:
                self.results_frame.after_cancel(aid)
            except:
                pass
        self._pending_after_ids.clear()

        sort_by = self.sort_var.get()
        if sort_by == "Latency":
            self.results.sort(key=lambda x: x.get('latency', 9999))
        elif sort_by == "Reachable First":
            self.results.sort(key=lambda x: (not x.get('reachable', False), x.get('latency', 9999)))
        elif sort_by == "Service Verified First":
            self.results.sort(key=lambda x: (
                not x.get('service_ok', False),
                not x.get('reachable', False),
                x.get('latency', 9999)
            ))

        for w in self.results_frame.winfo_children():
            w.destroy()
        for r in self.results:
            self._add_result_card(r)

    def _sync_to_scanner(self, results: List[Dict[str, Any]]):
        """همگام‌سازی با CF Scanner از طریق AssetManager مرکزی (یا مستقیم)"""
        good_dns = [r['dns'] for r in results if r.get('service_ok', r.get('reachable', False)) and r.get('latency', 9999) < 500][:10]
        if not good_dns:
            return

        # اگر AssetManager داریم، DNSهای خوب را مستقیماً به آن اضافه می‌کنیم
        if self.asset_manager:
            added = 0
            for dns in good_dns:
                if self.asset_manager.add_dns(dns):
                    added += 1
            if added > 0:
                self.status_label.configure(text=f"✅ Synced {added} DNS to global DNS list", text_color="#66BB6A")
            return

        # رفتار قبلی برای سازگاری با نسخه‌های بدون AssetManager
        if not self.app_controller:
            return
        scanner_frame = getattr(self.app_controller, 'scanner_frame', None)
        if not scanner_frame:
            return

        added = 0
        for dns in good_dns:
            if dns not in scanner_frame.dns_list:
                scanner_frame.dns_list.append(dns)
                added += 1
        if added > 0:
            scanner_frame.save_config()
            self.status_label.configure(text=f"✅ Synced {added} DNS to CF Scanner", text_color="#66BB6A")

    def _copy_to_clipboard(self, text: str):
        if hasattr(self, 'results_frame') and self.results_frame.winfo_exists():
            self.results_frame.clipboard_clear()
            self.results_frame.clipboard_append(text)
            messagebox.showinfo("Copied", f"DNS {text} copied to clipboard.")

    def copy_all_results(self):
        if not self.results:
            messagebox.showwarning("Warning", "No results to copy.")
            return
        all_dns = "\n".join([r['dns'] for r in self.results if r.get('service_ok', r.get('reachable', False))])
        self.results_frame.clipboard_clear()
        self.results_frame.clipboard_append(all_dns)
        messagebox.showinfo("Copied", f"{len(all_dns.splitlines())} DNS addresses copied.")

    def add_all_to_dns_list(self):
        if not self.results:
            messagebox.showwarning("Warning", "No results to add.")
            return
        added = 0
        for r in self.results:
            if r.get('service_ok', r.get('reachable', False)) and self.add_dns_to_list(r['dns']):
                added += 1
        self.dns_count_label.configure(text=f"DNS Count: {len(self.dns_list)}")
        messagebox.showinfo("Added", f"Added {added} DNS to the Hunter list.")

    def export_results(self):
        if not self.results:
            messagebox.showwarning("Warning", "No results to export.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("CSV files", "*.csv")]
        )
        if not filepath:
            return

        try:
            if filepath.endswith('.json'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump({
                        "target": self.target_entry.get().strip(),
                        "timestamp": datetime.now().isoformat(),
                        "results": self.results
                    }, f, indent=2, ensure_ascii=False)
            elif filepath.endswith('.csv'):
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=["dns", "latency", "ips", "reachable", "has_ipv6", "status", "service_ok"])
                    writer.writeheader()
                    for r in self.results:
                        writer.writerow({
                            "dns": r.get("dns"),
                            "latency": r.get("latency"),
                            "ips": ",".join(r.get("ips", [])),
                            "reachable": r.get("reachable"),
                            "has_ipv6": r.get("has_ipv6"),
                            "status": r.get("status"),
                            "service_ok": r.get("service_ok", False)
                        })
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# DNS Hunter Results\n")
                    f.write(f"# Target: {self.target_entry.get().strip()}\n")
                    f.write(f"# Date: {datetime.now().isoformat()}\n")
                    f.write("# DNS\tLatency\tReachable\tServiceOK\tIPs\n")
                    for r in self.results:
                        f.write(f"{r.get('dns')}\t{r.get('latency')}ms\t{r.get('reachable')}\t{r.get('service_ok', False)}\t{','.join(r.get('ips', []))}\n")
            messagebox.showinfo("Export Successful", f"Results exported to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _update_ui_after_scan(self, count: int):
        self.scan_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if count > 0 and self.results:
            best = self.results[0]
            status = f"✅ Found {count} clean DNS. Best: {best['dns']} ({best['latency']}ms)"
            if best.get('service_ok'):
                status += " [Service Verified]"
            self.status_label.configure(text=status, text_color="#66BB6A")
        else:
            self.status_label.configure(text="❌ No clean DNS found for this target.", text_color="#EF5350")
