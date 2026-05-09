# tabs/messenger/messenger_lan.py
import socket
import threading
import time
import json


class LANDiscovery:
    """کشف خودکار سرورهای Messenger در شبکه محلی"""
    
    # پورت پیش‌فرض برای broadcast discovery
    DISCOVERY_PORT = 8889
    DISCOVERY_MESSAGE = "NETTOOLS_MESSENGER_DISCOVERY"
    RESPONSE_MESSAGE = "NETTOOLS_MESSENGER_RESPONSE"
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.running = False
        self.sock = None
        self.found_servers = []
        self.server_info = None  # اطلاعات سرور خودمان (برای پاسخ به discovery)
    
    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
    
    def start_broadcast_listener(self):
        """شروع گوش دادن به درخواست‌های discovery (برای سرورها)"""
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.DISCOVERY_PORT))
        self.sock.settimeout(1.0)
        
        self.log(f"🔍 LAN Discovery listener started on port {self.DISCOVERY_PORT}")
        threading.Thread(target=self._listen_loop, daemon=True).start()
    
    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                message = data.decode('utf-8')
                
                if message == self.DISCOVERY_MESSAGE:
                    # دریافت درخواست discovery، پاسخ بده
                    self.log(f"📡 Discovery request from {addr[0]}")
                    if self.server_info:
                        response = json.dumps(self.server_info).encode()
                        self.sock.sendto(response, addr)
                
                elif message.startswith(self.RESPONSE_MESSAGE):
                    # دریافت پاسخ از یک سرور
                    try:
                        info_json = message[len(self.RESPONSE_MESSAGE):]
                        server_info = json.loads(info_json)
                        server_info['addr'] = addr[0]
                        if server_info not in self.found_servers:
                            self.found_servers.append(server_info)
                            self.log(f"✅ Found server: {server_info.get('name', 'Unknown')} at {addr[0]}:{server_info.get('port', 8888)}")
                    except:
                        pass
            except socket.timeout:
                continue
            except:
                break
    
    def broadcast_discovery(self, timeout=3):
        """ارسال درخواست discovery به شبکه محلی و جمع‌آوری پاسخ‌ها"""
        self.found_servers = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)
        
        # ارسال به broadcast آدرس
        broadcast_addr = '<broadcast>'
        message = self.DISCOVERY_MESSAGE.encode()
        sock.sendto(message, (broadcast_addr, self.DISCOVERY_PORT))
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                try:
                    server_info = json.loads(data.decode())
                    server_info['addr'] = addr[0]
                    if server_info not in self.found_servers:
                        self.found_servers.append(server_info)
                        self.log(f"✅ Found server: {server_info.get('name', 'Unknown')} at {addr[0]}:{server_info.get('port', 8888)}")
                except:
                    pass
            except socket.timeout:
                continue
            except:
                break
        
        sock.close()
        return self.found_servers
    
    def register_server(self, server_name, port, room_password=None):
        """ثبت اطلاعات سرور برای پاسخ به discovery"""
        self.server_info = {
            "name": server_name,
            "port": port,
            "has_password": room_password is not None,
            "timestamp": time.time()
        }
        self.log(f"📡 Server registered for LAN discovery: {server_name} on port {port}")
    
    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()


class LANHostHelper:
    """کمک‌کننده برای هاستینگ در شبکه محلی"""
    
    @staticmethod
    def get_local_ip():
        """دریافت IP محلی دستگاه"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    @staticmethod
    def get_all_local_ips():
        """دریافت تمام IPهای محلی دستگاه (شامل IPv4 و IPv6)"""
        ips = []
        try:
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                        ips.append(addr.address)
        except:
            # Fallback
            ips.append(LANHostHelper.get_local_ip())
        return ips
    
    @staticmethod
    def is_port_available(port):
        """بررسی اینکه پورت مورد نظر آزاد است یا نه"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except:
            return False
    
    @staticmethod
    def find_free_port(start_port=8888, end_port=8900):
        """پیدا کردن یک پورت آزاد در رنج مشخص"""
        for port in range(start_port, end_port + 1):
            if LANHostHelper.is_port_available(port):
                return port
        return None
    
    @staticmethod
    def get_connection_help_text(server_ip, port, room_password=None):
        """تولید متن راهنما برای اتصال به سرور"""
        text = f"📡 Connect to: {server_ip}:{port}\n"
        if room_password:
            text += f"🔑 Room password: {room_password}\n"
        text += "💡 In Join Room tab, enter these details."
        return text


class LANClientHelper:
    """کمک‌کننده برای اتصال خودکار به سرورهای LAN"""
    
    @staticmethod
    def auto_connect(discovery, callback):
        """اتصال خودکار به اولین سرور پیدا شده"""
        servers = discovery.broadcast_discovery(timeout=3)
        if servers:
            best_server = servers[0]  # ساده: اولین سرور
            callback(best_server['addr'], best_server['port'])
            return True
        return False
