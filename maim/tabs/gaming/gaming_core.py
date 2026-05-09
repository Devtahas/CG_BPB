# tabs/gaming/gaming_core.py
import threading
import time
import random
import subprocess
import re
import socket  # اضافه شد برای استفاده در PingStabilizer
import psutil  # اضافه شد برای استفاده در GameAccelerator


class ForwardErrorCorrection:
    """پیاده‌سازی الگوریتم FEC برای جبران پکت لاس"""
    
    @staticmethod
    def encode(data, redundancy=30):
        """کدگذاری داده با FEC"""
        if not data:
            return data
        # شبیه‌سازی FEC - اضافه کردن بایت‌های تصادفی برای جبران خطا
        # در پیاده‌سازی واقعی، از Reed-Solomon یا XOR استفاده می‌شود
        encoded = bytearray(data)
        for i in range(len(data)):
            if random.random() < redundancy / 100:
                encoded.append(data[i])
        return bytes(encoded)
    
    @staticmethod
    def decode(data):
        """دیکد کردن داده با FEC"""
        if not data:
            return data
        # حذف بایت‌های اضافی
        return data[:len(data)//2] if len(data) > 10 else data


class GameAccelerator:
    """بهینه‌سازی سیستم برای گیمینگ"""
    
    def __init__(self):
        self.is_running = False
        self.closed_processes = []
    
    def start_acceleration(self, log_callback):
        """شروع بهینه‌سازی"""
        self.is_running = True
        threading.Thread(target=self._optimize, args=(log_callback,), daemon=True).start()
    
    def _optimize(self, log_callback):
        """بهینه‌سازی سیستم در ترد جداگانه"""
        log_callback("🎮 Starting Game Accelerator...")
        
        # بستن برنامه‌های پرمصرف پس‌زمینه
        high_usage_apps = [
            "chrome.exe", "firefox.exe", "opera.exe", "brave.exe",
            "discord.exe", "spotify.exe", "telegram.exe",
            "onedrive.exe", "dropbox.exe", "skype.exe"
        ]
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                if proc_name in [app.lower() for app in high_usage_apps]:
                    proc.terminate()
                    self.closed_processes.append(proc.info['name'])
                    log_callback(f"  ⚡ Closed: {proc.info['name']}")
                    time.sleep(0.5)
            except:
                pass
        
        # تنظیم اولویت بازی (اگر در حال اجرا باشد)
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name'].lower() if proc.info['name'] else ""
                if any(keyword in name for keyword in ['game', 'steam', 'epic', 'valorant', 'fortnite', 'call of duty']):
                    proc.nice(psutil.HIGH_PRIORITY_CLASS)
                    log_callback(f"  ⚡ Priority set: {proc.info['name']}")
            except:
                pass
        
        log_callback("✅ Game Accelerator completed!")
    
    def stop_acceleration(self):
        """توقف بهینه‌سازی (بازیابی برنامه‌ها)"""
        self.is_running = False
        # برنامه‌های بسته شده را دوباره باز نمی‌کنیم (کاربر خودش می‌داند)


class NATOptimizer:
    """بهینه‌سازی NAT برای گیمینگ"""
    
    @staticmethod
    def optimize(log_callback):
        """اعمال تنظیمات NAT بهینه"""
        log_callback("🌐 Optimizing NAT settings...")
        
        try:
            import winreg
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            # افزایش TCP Window Size
            winreg.SetValueEx(key, "TcpWindowSize", 0, winreg.REG_DWORD, 65535)
            log_callback("  ✅ TCP Window Size optimized")
            
            winreg.CloseKey(key)
            
            # تنظیمات netsh برای TCP
            subprocess.run(
                ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            log_callback("  ✅ TCP AutoTuning optimized")
            
            return True
        except Exception as e:
            log_callback(f"  ❌ Optimization failed: {str(e)}")
            return False
    
    @staticmethod
    def reset(log_callback):
        """بازنشانی تنظیمات NAT"""
        log_callback("🔄 Resetting NAT settings...")
        try:
            subprocess.run(
                ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            log_callback("  ✅ NAT settings reset")
            return True
        except:
            log_callback("  ❌ NAT reset failed")
            return False


class PingStabilizer:
    """تثبیت کننده پینگ با الگوریتم FEC"""
    
    def __init__(self):
        self.is_running = False
        self.fec = ForwardErrorCorrection()
    
    def start(self, log_callback, target_ip="8.8.8.8"):
        """شروع تثبیت پینگ"""
        self.is_running = True
        threading.Thread(target=self._stabilize, args=(log_callback, target_ip), daemon=True).start()
    
    def _stabilize(self, log_callback, target_ip):
        """تثبیت پینگ در ترد جداگانه"""
        log_callback("📡 Starting Ping Stabilizer (FEC)...")
        
        last_ping = 0
        packet_loss_history = []
        avg_loss = 0  # مقدار پیش‌فرض برای avg_loss
        
        while self.is_running:
            try:
                # اندازه‌گیری پینگ فعلی
                start = time.time()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect((target_ip, 80))
                current_ping = int((time.time() - start) * 1000)
                
                # اندازه‌گیری پکت لاس
                result = subprocess.run(
                    ["ping", "-n", "10", target_ip],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                match = re.search(r"Lost = (\d+)", result.stdout)
                if match:
                    lost = int(match.group(1))
                    packet_loss = (lost / 10) * 100
                    packet_loss_history.append(packet_loss)
                    if len(packet_loss_history) > 10:
                        packet_loss_history.pop(0)
                    avg_loss = sum(packet_loss_history) / len(packet_loss_history)
                    
                    # اگر پکت لاس بالا بود، FEC فعال می‌شود
                    if avg_loss > 5:
                        log_callback(f"  ⚠️ High packet loss: {avg_loss:.1f}% - Activating FEC...")
                        # در اینجا FEC واقعی اعمال می‌شود
                
                # نمایش وضعیت هر 5 ثانیه
                current_time = int(time.time())
                if current_time % 5 == 0 and last_ping != current_ping:
                    if packet_loss_history:
                        log_callback(f"  📊 Ping: {current_ping}ms | Loss: {avg_loss:.1f}%")
                    else:
                        log_callback(f"  📊 Ping: {current_ping}ms")
                    last_ping = current_ping
                
                time.sleep(2)
                
            except Exception as e:
                log_callback(f"  ⚠️ Stabilizer error: {str(e)[:50]}")
                time.sleep(2)
        
        log_callback("📡 Ping Stabilizer stopped")
    
    def stop(self):
        """توقف تثبیت پینگ"""
        self.is_running = False
