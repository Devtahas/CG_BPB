# tabs/setting/setting_updater.py
import os
import sys
import subprocess
import threading
import requests
import zipfile
import io
import shutil
import time
from tkinter import messagebox
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class CoreUpdater:
    """
    مدیریت دانلود و آپدیت هسته‌های نرم‌افزار (Xray-core, GoodbyeDPI)
    با نمایش درصد پیشرفت، تحمل خطا و استفاده از mirrorها
    """

    def __init__(self, log_callback=None, progress_callback=None):
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.base_dir = None
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def set_base_dir(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def log(self, msg: str, color: str = "#F38020") -> None:
        if self.log_callback:
            self.log_callback(msg, color)

    def set_progress(self, percent: int, message: str = "") -> None:
        if self.progress_callback:
            self.progress_callback(percent, message)

    def _get_robust_session(self) -> requests.Session:
        """ایجاد یک نشست مقاوم با Retry خودکار"""
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        return session

    def get_latest_xray_version(self) -> tuple:
        """
        دریافت آخرین نسخه Xray-core از GitHub
        Returns:
            (version_tag, html_url) یا (None, None) در صورت خطا
        """
        try:
            session = self._get_robust_session()
            api_url = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
            resp = session.get(api_url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tag_name", ""), data.get("html_url", "")
        except Exception as e:
            self.log(f"خطا در دریافت نسخه Xray: {str(e)}", "#EF5350")
        return None, None

    def get_current_xray_version(self) -> str:
        """دریافت نسخه فعلی Xray-core نصب شده"""
        if not self.base_dir:
            return None
        xray_path = os.path.join(self.base_dir, "xray", "xray.exe")
        if not os.path.exists(xray_path):
            return None
        try:
            result = subprocess.run(
                [xray_path, "-version"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.stdout:
                import re
                match = re.search(r"Xray\s+([\d\.]+)", result.stdout)
                if match:
                    return match.group(1)
            return "Unknown"
        except:
            return "Unknown"

    def _get_working_download_url(self, asset_url: str) -> str:
        """
        تبدیل لینک اصلی asset به لینک قابل دانلود با استفاده از mirrorها
        """
        mirrors = [
            "https://mirror.ghproxy.com/",
            "https://ghproxy.net/",
            "https://gh.ddlc.top/",
            "https://gh-proxy.com/",
            "https://cf.ghproxy.cc/",
            "https://Scorpian.ir/",
        ]

        candidates = [asset_url]
        for mirror in mirrors:
            candidates.append(mirror + asset_url)

        for url in candidates:
            try:
                # بررسی دسترسی‌پذیری با HEAD
                resp = requests.head(url, timeout=5, allow_redirects=True)
                if resp.status_code < 400:
                    return url
            except:
                continue
        return asset_url

    def download_file_with_progress(self, url: str, dest_path: str) -> bool:
        """
        دانلود فایل با نمایش درصد پیشرفت و مقاوم در برابر قطعی
        """
        session = self._get_robust_session()
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                self.log(f"تلاش {attempt}: اتصال به {url[:50]}...", "#F38020")
                response = session.get(url, stream=True, timeout=30)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                last_percent = -1

                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                if percent != last_percent:
                                    self.set_progress(percent, f"Downloading: {percent}%")
                                    last_percent = percent
                self.log(f"✅ دانلود با موفقیت انجام شد (تلاش {attempt})", "#66BB6A")
                return True
            except Exception as e:
                self.log(f"⚠️ تلاش {attempt} ناموفق: {str(e)}", "#FFA726")
                if attempt == max_retries:
                    self.log(f"❌ همه تلاش‌ها ناموفق بود", "#EF5350")
                    return False
                time.sleep(3)  # صبر قبل از تلاش مجدد
        return False

    def download_xray(self, version: str, download_url: str, progress_callback=None) -> bool:
        """
        دانلود و نصب آخرین نسخه Xray-core با نمایش درصد و مقاوم در برابر قطعی
        """
        if not self.base_dir:
            self.log("مسیر پایه مشخص نشده است", "#EF5350")
            return False

        xray_dir = os.path.join(self.base_dir, "xray")
        backup_dir = os.path.join(self.base_dir, "xray_backup")
        zip_path = os.path.join(self.base_dir, f"xray_{version}.zip")

        try:
            self.set_progress(0, "دریافت لینک دانلود...")
            session = self._get_robust_session()
            assets_url = f"https://api.github.com/repos/XTLS/Xray-core/releases/tags/{version}"
            assets_resp = session.get(assets_url, timeout=15)
            if assets_resp.status_code != 200:
                raise Exception("خطا در دریافت لیست فایل‌ها")

            assets_data = assets_resp.json()
            download_file_url = None
            for asset in assets_data.get("assets", []):
                if "windows-64.zip" in asset.get("name", ""):
                    download_file_url = asset.get("browser_download_url")
                    break

            if not download_file_url:
                raise Exception("فایل ویندوز 64 بیتی یافت نشد")

            final_url = self._get_working_download_url(download_file_url)

            self.log(f"در حال دانلود Xray-core نسخه {version}...", "#F38020")
            success = self.download_file_with_progress(final_url, zip_path)
            if not success:
                raise Exception("دانلود ناموفق بود")

            self.set_progress(90, "Extracting files...")
            # ایجاد بکاپ
            if os.path.exists(xray_dir):
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.copytree(xray_dir, backup_dir)
                self.log("بکاپ از نسخه فعلی گرفته شد", "#29B6F6")

            # استخراج فایل ZIP
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(xray_dir)

            # حذف فایل ZIP
            os.remove(zip_path)

            # حذف بکاپ پس از نصب موفق
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

            self.set_progress(100, "Update completed!")
            self.log(f"✅ Xray-core نسخه {version} با موفقیت نصب شد", "#66BB6A")
            return True

        except Exception as e:
            self.log(f"❌ خطا در نصب Xray-core: {str(e)}", "#EF5350")
            # برگرداندن بکاپ در صورت وجود
            if os.path.exists(backup_dir):
                if os.path.exists(xray_dir):
                    shutil.rmtree(xray_dir)
                shutil.copytree(backup_dir, xray_dir)
                shutil.rmtree(backup_dir)
                self.log("نسخه قبلی بازیابی شد", "#FFA726")
            return False
        finally:
            self.set_progress(0, "")

    def check_goodbyedpi(self) -> str:
        """بررسی وجود GoodbyeDPI و بازگرداندن مسیر آن"""
        possible_paths = [
            os.path.join(self.base_dir, "goodbyedpi.exe") if self.base_dir else None,
            os.path.join(os.getcwd(), "goodbyedpi.exe"),
            "C:\\Program Files\\GoodbyeDPI\\goodbyedpi.exe",
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        return None

    def download_goodbyedpi(self) -> bool:
        """دانلود GoodbyeDPI با نمایش درصد و مقاوم در برابر قطعی"""
        try:
            self.log("در حال دانلود GoodbyeDPI...", "#F38020")
            url = "https://github.com/ValdikSS/GoodbyeDPI/releases/download/0.2.2/goodbyedpi-0.2.2-x86_64.zip"
            final_url = self._get_working_download_url(url)
            zip_path = os.path.join(self.base_dir, "goodbyedpi.zip")

            success = self.download_file_with_progress(final_url, zip_path)
            if not success:
                raise Exception("دانلود ناموفق")

            self.set_progress(90, "Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(self.base_dir)
            os.remove(zip_path)

            # تغییر نام فایل اصلی
            extracted_folder = os.path.join(self.base_dir, "goodbyedpi-0.2.2-x86_64")
            target_file = os.path.join(self.base_dir, "goodbyedpi.exe")

            if os.path.exists(extracted_folder):
                for f in os.listdir(extracted_folder):
                    if f.endswith(".exe"):
                        shutil.move(os.path.join(extracted_folder, f), target_file)
                        break
                shutil.rmtree(extracted_folder)

            self.set_progress(100, "Done!")
            self.log("✅ GoodbyeDPI با موفقیت نصب شد", "#66BB6A")
            return True
        except Exception as e:
            self.log(f"❌ خطا در دانلود GoodbyeDPI: {str(e)}", "#EF5350")
            return False
        finally:
            self.set_progress(0, "")
