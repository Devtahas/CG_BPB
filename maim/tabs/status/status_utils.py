# tabs/status/status_utils.py
import time
import socket
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading


class StatusUtils:
    """توابع کمکی برای تب Status"""
    
    @staticmethod
    def get_public_ip():
        """دریافت IP عمومی و اطلاعات کشور"""
        try:
            resp = requests.get('http://ip-api.com/json/', timeout=5)
            data = resp.json()
            return {
                "ip": data.get('query', 'Unknown'),
                "country": data.get('country', 'Unknown'),
                "countryCode": data.get('countryCode', 'UN'),
                "isp": data.get('isp', 'Unknown'),
                "city": data.get('city', 'Unknown'),
                "lat": data.get('lat', 0),
                "lon": data.get('lon', 0)
            }
        except:
            return {"ip": "Unknown", "country": "Unknown", "countryCode": "UN", "isp": "Unknown"}
    
    @staticmethod
    def get_flag_emoji(country_code):
        if not country_code or len(country_code) != 2:
            return "🌍"
        return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)
    
    @staticmethod
    def get_current_ping(host="8.8.8.8", count=4):
        """دریافت میانگین پینگ"""
        try:
            import subprocess
            import re
            result = subprocess.run(
                ["ping", "-n", str(count), host],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # فرمت ویندوز
            match = re.search(r"Average = (\d+)ms", result.stdout)
            if match:
                return int(match.group(1))
            match = re.search(r"متوسط = (\d+)ms", result.stdout)
            if match:
                return int(match.group(1))
            return 0
        except:
            return 0
    
    @staticmethod
    def get_packet_loss(host="8.8.8.8", count=10):
        """دریافت درصد پکت لاس"""
        try:
            import subprocess
            import re
            result = subprocess.run(
                ["ping", "-n", str(count), host],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            match = re.search(r"Lost = (\d+)", result.stdout)
            if match:
                lost = int(match.group(1))
                return (lost / count) * 100
            return 0
        except:
            return 0
    
    @staticmethod
    def get_current_speed():
        """دریافت سرعت دانلود/آپلود لحظه‌ای (از طریق psutil)"""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return {
                "download": net_io.bytes_recv,
                "upload": net_io.bytes_sent
            }
        except:
            return {"download": 0, "upload": 0}
    
    @staticmethod
    def create_traffic_graph(parent_frame, width=500, height=200):
        """ایجاد نمودار ترافیک لحظه‌ای با matplotlib"""
        fig, ax = plt.subplots(figsize=(width/100, height/100), facecolor='#1a1a1a')
        ax.set_facecolor('#2a2a2a')
        ax.set_xlabel('Time', color='white')
        ax.set_ylabel('Speed (KB/s)', color='white')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('gray')
        canvas = FigureCanvasTkAgg(fig, parent_frame)
        canvas.draw()
        return fig, ax, canvas
    
    @staticmethod
    def update_traffic_graph(ax, canvas, data_points, max_points=30):
        """به‌روزرسانی نمودار ترافیک"""
        if len(data_points) > max_points:
            data_points.pop(0)
        ax.clear()
        ax.plot(data_points, color='#F38020', linewidth=2)
        ax.fill_between(range(len(data_points)), data_points, alpha=0.3, color='#F38020')
        ax.set_xlabel('Time (s)', color='white')
        ax.set_ylabel('Speed (KB/s)', color='white')
        ax.set_ylim(0, max(data_points + [100]) * 1.2)
        ax.tick_params(colors='white')
        canvas.draw()
