# tabs/browser/browser_utils.py
import random
import string
import platform
import json
import os
import subprocess


class BrowserUtils:
    """توابع کمکی برای مرورگر سفارشی"""
    
    # لیست User-Agentهای معروف برای تغییر
    USER_AGENTS = {
        "Chrome (Windows)": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Chrome (Linux)": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Firefox (Windows)": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Firefox (Linux)": "Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Edge (Windows)": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Safari (Mac)": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mobile (Android)": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mobile (iPhone)": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    }
    
    @staticmethod
    def random_user_agent():
        """بازگرداندن یک User-Agent تصادفی از لیست"""
        return random.choice(list(BrowserUtils.USER_AGENTS.values()))
    
    @staticmethod
    def get_current_platform_ua():
        """بازگرداندن User-Agent پیش‌فرض برای سیستم عامل فعلی"""
        system = platform.system()
        if system == "Windows":
            return BrowserUtils.USER_AGENTS["Chrome (Windows)"]
        elif system == "Linux":
            return BrowserUtils.USER_AGENTS["Chrome (Linux)"]
        else:
            return BrowserUtils.USER_AGENTS["Firefox (Windows)"]
    
    @staticmethod
    def generate_random_fingerprint():
        """تولید یک اثر انگشت تصادفی (شامل مقادیر تصادفی برای مشخصه‌های مختلف)"""
        return {
            "languages": random.choice([["en-US", "en"], ["fa-IR", "fa"], ["en-GB", "en"], ["fr-FR", "fr"], ["de-DE", "de"]]),
            "screen_resolution": random.choice(["1920x1080", "1366x768", "1536x864", "1440x900", "2560x1440"]),
            "timezone": random.choice(["UTC", "Asia/Tehran", "Europe/London", "America/New_York", "Asia/Tokyo"]),
            "platform": random.choice(["Win32", "Linux x86_64", "MacIntel", "iPhone", "Android"]),
            "do_not_track": random.choice([True, False]),
            "color_depth": random.choice([24, 30, 48]),
            "pixel_ratio": round(random.uniform(1, 3), 1)
        }
    
    @staticmethod
    def check_tor_installed():
        """بررسی نصب بودن Tor (tor.exe در مسیر یا سرویس)"""
        # بررسی در مسیرهای معمول
        possible_paths = [
            "C:\\Program Files\\Tor\\tor.exe",
            "C:\\Program Files (x86)\\Tor\\tor.exe",
            os.path.expanduser("~\\Desktop\\Tor Browser\\Browser\\TorBrowser\\Tor\\tor.exe"),
            "/usr/bin/tor",
            "/usr/local/bin/tor"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return True
        # بررسی در PATH
        try:
            subprocess.run(["tor", "--version"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except:
            pass
        return False
    
    @staticmethod
    def get_adblock_rules():
        """بازگرداندن لیست قوانین مسدودسازی تبلیغات (ساده)"""
        return [
            "*://*.doubleclick.net/*",
            "*://*.googleadservices.com/*",
            "*://*.googlesyndication.com/*",
            "*://*.google-analytics.com/*",
            "*://*.facebook.com/tr/*",
            "*://*.amazon-adsystem.com/*",
            "*://*.scorecardresearch.com/*",
            "*://*.outbrain.com/*",
            "*://*.taboola.com/*",
            "*://*.criteo.com/*",
            "*://*.adnxs.com/*",
            "*://*.adsrvr.org/*",
            "*://*.adservice.google.com/*",
            "*://*.pagead2.googlesyndication.com/*"
        ]
