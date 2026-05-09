# tabs/gaming/gaming_utils.py
import psutil
import threading
import time
import subprocess
import re
import platform

# GPUtil را با try/except ایمپورت می‌کنیم (اختیاری)
try:
    import GPUtil
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

# wmi و pythoncom فقط برای ویندوز و در صورت نیاز
if platform.system() == "Windows":
    try:
        import wmi
        import pythoncom
        HAS_WMI = True
    except ImportError:
        HAS_WMI = False
else:
    HAS_WMI = False


class GamingUtils:
    """توابع کمکی برای بخش گیمینگ"""
    
    @staticmethod
    def get_cpu_usage():
        """دریافت مصرف CPU"""
        return psutil.cpu_percent(interval=0.5)
    
    @staticmethod
    def get_ram_usage():
        """دریافت مصرف RAM"""
        ram = psutil.virtual_memory()
        return {
            "percent": ram.percent,
            "used": ram.used // (1024**3),  # GB
            "total": ram.total // (1024**3),
            "available": ram.available // (1024**3)
        }
    
    @staticmethod
    def get_gpu_usage():
        """دریافت مصرف GPU (با استفاده از GPUtil)"""
        if not HAS_GPU:
            return {"percent": 0, "temp": 0, "memory_used": 0, "memory_total": 0}
        
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    "percent": gpu.load * 100,
                    "temp": gpu.temperature,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal
                }
        except:
            pass
        return {"percent": 0, "temp": 0, "memory_used": 0, "memory_total": 0}
    
    @staticmethod
    def get_top_processes(n=5):
        """دریافت پر مصرف‌ترین فرآیندها"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                # اطمینان از وجود مقادیر
                if info.get('cpu_percent') is None:
                    info['cpu_percent'] = 0
                if info.get('memory_percent') is None:
                    info['memory_percent'] = 0
                processes.append(info)
            except:
                pass
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return processes[:n]
    
    @staticmethod
    def kill_process(pid):
        """بستن یک فرآیند"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return True
        except:
            return False
    
    @staticmethod
    def set_process_priority(pid, priority="high"):
        """تنظیم اولویت فرآیند (فقط ویندوز)"""
        if platform.system() != "Windows":
            return False
        
        try:
            proc = psutil.Process(pid)
            priority_map = {
                "low": psutil.IDLE_PRIORITY_CLASS,
                "normal": psutil.NORMAL_PRIORITY_CLASS,
                "high": psutil.HIGH_PRIORITY_CLASS,
                "realtime": psutil.REALTIME_PRIORITY_CLASS
            }
            proc.nice(priority_map.get(priority, psutil.NORMAL_PRIORITY_CLASS))
            return True
        except:
            return False
    
    @staticmethod
    def get_network_latency(host="8.8.8.8", count=4):
        """دریافت پینگ به سرور"""
        try:
            # تعیین پارامتر count بر اساس سیستم‌عامل
            if platform.system() == "Windows":
                cmd = ["ping", "-n", str(count), host]
            else:
                cmd = ["ping", "-c", str(count), host]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            # استخراج میانگین پینگ
            # فرمت ویندوز: Average = 45ms
            match = re.search(r"Average = (\d+)ms", result.stdout)
            if match:
                return int(match.group(1))
            # فرمت فارسی ویندوز
            match = re.search(r"متوسط = (\d+)ms", result.stdout)
            if match:
                return int(match.group(1))
            # فرمت لینوکس: rtt min/avg/max/mdev = 10.123/12.456/15.789/1.234 ms
            match = re.search(r"rtt.*=.*/(\d+\.?\d*)/", result.stdout)
            if match:
                return int(float(match.group(1)))
            return 0
        except:
            return 0
    
    @staticmethod
    def get_packet_loss(host="8.8.8.8", count=10):
        """دریافت درصد پکت لاس"""
        try:
            # تعیین پارامتر count بر اساس سیستم‌عامل
            if platform.system() == "Windows":
                cmd = ["ping", "-n", str(count), host]
            else:
                cmd = ["ping", "-c", str(count), host]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # استخراج درصد loss
            # فرمت ویندوز: Lost = 0
            match = re.search(r"Lost = (\d+)", result.stdout)
            if match:
                lost = int(match.group(1))
                return (lost / count) * 100
            
            # فرمت لینوکس: 0% packet loss
            match = re.search(r"(\d+)% packet loss", result.stdout)
            if match:
                return float(match.group(1))
            
            return 0
        except:
            return 0

