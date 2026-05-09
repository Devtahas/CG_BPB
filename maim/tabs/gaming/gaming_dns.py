# tabs/gaming/gaming_dns.py
import subprocess
import socket
import time


class GamingDNS:
    """مدیریت DNS مخصوص گیمینگ"""
    
    # DNS های مخصوص گیمینگ
    GAMING_DNS = {
        "Cloudflare Gaming": {"primary": "1.1.1.1", "secondary": "1.0.0.1"},
        "Google Gaming": {"primary": "8.8.8.8", "secondary": "8.8.4.4"},
        "Quad9 Gaming": {"primary": "9.9.9.9", "secondary": "149.112.112.112"},
        "OpenDNS Gaming": {"primary": "208.67.222.222", "secondary": "208.67.220.220"},
        "Shecan (IR)": {"primary": "178.22.122.100", "secondary": "185.51.200.2"},
        "Electro (IR)": {"primary": "78.157.42.100", "secondary": "78.157.42.101"},
    }
    
    def __init__(self):
        self.current_dns = None
        self.interface = self.get_active_interface()
    
    def get_active_interface(self):
        """دریافت نام رابط شبکه فعال"""
        try:
            import psutil
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address == local_ip:
                        return interface
        except:
            pass
        return "Wi-Fi"
    
    def set_dns(self, dns_name, log_callback):
        """تنظیم DNS مخصوص گیمینگ"""
        if dns_name not in self.GAMING_DNS:
            log_callback(f"❌ Unknown DNS: {dns_name}")
            return False
        
        dns = self.GAMING_DNS[dns_name]
        self.current_dns = dns_name
        
        try:
            # تنظیم DNS اصلی
            cmd1 = f'netsh interface ipv4 set dnsservers name="{self.interface}" source=static address="{dns["primary"]}" primary'
            subprocess.run(cmd1, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            
            # تنظیم DNS ثانویه
            cmd2 = f'netsh interface ipv4 add dnsservers name="{self.interface}" address="{dns["secondary"]}" index=2'
            subprocess.run(cmd2, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            log_callback(f"✅ Gaming DNS set to: {dns_name} ({dns['primary']})")
            return True
            
        except Exception as e:
            log_callback(f"❌ Failed to set DNS: {str(e)}")
            return False
    
    def reset_dns(self, log_callback):
        """بازنشانی DNS به حالت خودکار"""
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{self.interface}" source=dhcp'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.current_dns = None
            log_callback("✅ DNS reset to automatic")
            return True
        except Exception as e:
            log_callback(f"❌ Failed to reset DNS: {str(e)}")
            return False
    
    def get_current_dns(self):
        """دریافت DNS فعلی"""
        if self.current_dns:
            return self.current_dns
        return "Automatic (DHCP)"
    
    def test_dns_latency(self, dns_name):
        """تست latency DNS"""
        if dns_name not in self.GAMING_DNS:
            return 9999
        
        dns = self.GAMING_DNS[dns_name]
        try:
            start = time.time()
            socket.create_connection((dns["primary"], 53), timeout=2).close()
            return int((time.time() - start) * 1000)
        except:
            return 9999
