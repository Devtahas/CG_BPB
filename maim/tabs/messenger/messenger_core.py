# tabs/messenger/messenger_core.py
import socket
import threading
import json
import time
from .messenger_crypto import MessengerCrypto
from .messenger_utils import MessengerUtils


class MessengerServer:
    """سرور پیام‌رسان (Hoster)"""
    
    def __init__(self, host='0.0.0.0', port=8888, log_callback=None):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {conn: (username, crypto)}
        self.running = False
        self.log_callback = log_callback
        self.room_password = None  # رمز اتاق برای اتصال
    
    def start(self, room_password=None):
        """شروع سرور"""
        self.room_password = room_password
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        self.log(f"🚀 Server started on {self.host}:{self.port}")
        if self.room_password:
            self.log(f"🔑 Room password: {self.room_password}")
        
        threading.Thread(target=self._accept_connections, daemon=True).start()
        return True
    
    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                self.log(f"📡 New connection from {addr}")
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except:
                break
    
    def _handle_client(self, conn, addr):
        # ابتدا احراز هویت با رمز اتاق (اگر تنظیم شده باشد)
        if self.room_password:
            try:
                auth_msg = conn.recv(1024).decode('utf-8')
                auth_data = json.loads(auth_msg)
                if auth_data.get('password') != self.room_password:
                    conn.send(json.dumps({"status": "error", "message": "Invalid password"}).encode())
                    conn.close()
                    return
                conn.send(json.dumps({"status": "ok"}).encode())
            except:
                conn.close()
                return
        
        # تبادل کلیدهای عمومی برای E2E
        crypto = MessengerCrypto()
        # ارسال کلید عمومی خود به کلاینت
        conn.send(crypto.get_public_key_pem().encode())
        # دریافت کلید عمومی کلاینت
        peer_key_pem = conn.recv(4096).decode()
        crypto.load_peer_public_key(peer_key_pem)
        
        # دریافت نام کاربری
        username_data = conn.recv(1024).decode()
        username = json.loads(username_data).get('username', 'Anonymous')
        
        self.clients[conn] = (username, crypto, addr)
        self.log(f"✅ {username} joined the room")
        
        # اطلاع به سایر کاربران
        self._broadcast({"type": "join", "username": username, "message": f"{username} joined the chat"}, conn)
        
        # حلقه دریافت پیام
        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                msg_data = json.loads(data.decode())
                
                if msg_data.get('type') == 'message':
                    encrypted_msg = msg_data.get('content')
                    decrypted = crypto.decrypt_message(encrypted_msg)
                    self._broadcast({
                        "type": "message",
                        "username": username,
                        "content": decrypted,
                        "timestamp": time.time()
                    }, conn)
                elif msg_data.get('type') == 'private':
                    target_username = msg_data.get('target')
                    encrypted_msg = msg_data.get('content')
                    decrypted = crypto.decrypt_message(encrypted_msg)
                    self._send_private(target_username, {
                        "type": "private",
                        "from": username,
                        "content": decrypted,
                        "timestamp": time.time()
                    })
            except:
                break
        
        # خروج کاربر
        self.clients.pop(conn, None)
        conn.close()
        self._broadcast({"type": "leave", "username": username, "message": f"{username} left the chat"})
        self.log(f"👋 {username} disconnected")
    
    def _broadcast(self, message, exclude_conn=None):
        for conn in list(self.clients.keys()):
            if conn != exclude_conn:
                try:
                    conn.send(json.dumps(message).encode())
                except:
                    pass
    
    def _send_private(self, target_username, message):
        for conn, (username, crypto, addr) in self.clients.items():
            if username == target_username:
                try:
                    conn.send(json.dumps(message).encode())
                except:
                    pass
                break
    
    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
    
    def stop(self):
        self.running = False
        for conn in list(self.clients.keys()):
            try:
                conn.close()
            except:
                pass
        if self.server_socket:
            self.server_socket.close()
        self.log("🛑 Server stopped")


class MessengerClient:
    """کلاینت پیام‌رسان"""
    
    def __init__(self, log_callback=None, message_callback=None):
        self.socket = None
        self.crypto = None
        self.username = None
        self.room_id = None
        self.running = False
        self.log_callback = log_callback
        self.message_callback = message_callback
        self.receive_thread = None
    
    def connect(self, host, port, username, room_password=None):
        """اتصال به سرور"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.username = username
            
            # ارسال رمز اتاق (اگر نیاز باشد)
            if room_password:
                auth_msg = json.dumps({"password": room_password})
                self.socket.send(auth_msg.encode())
                response = json.loads(self.socket.recv(1024).decode())
                if response.get('status') != 'ok':
                    self.log("❌ Invalid room password")
                    return False
            
            # تبادل کلیدهای عمومی
            self.crypto = MessengerCrypto()
            # دریافت کلید عمومی سرور
            server_key_pem = self.socket.recv(4096).decode()
            self.crypto.load_peer_public_key(server_key_pem)
            # ارسال کلید عمومی خود
            self.socket.send(self.crypto.get_public_key_pem().encode())
            
            # ارسال نام کاربری
            self.socket.send(json.dumps({"username": username}).encode())
            
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            self.log(f"✅ Connected to {host}:{port} as {username}")
            return True
        except Exception as e:
            self.log(f"❌ Connection failed: {str(e)}")
            return False
    
    def _receive_loop(self):
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                message = json.loads(data.decode())
                if message.get('type') == 'message':
                    decrypted = self.crypto.decrypt_message(message.get('content', ''))
                    if self.message_callback:
                        self.message_callback(message.get('username'), decrypted, message.get('timestamp'))
                elif message.get('type') == 'private':
                    decrypted = self.crypto.decrypt_message(message.get('content', ''))
                    if self.message_callback:
                        self.message_callback(f"[PV] {message.get('from')}", decrypted, message.get('timestamp'))
                elif message.get('type') == 'join':
                    if self.message_callback:
                        self.message_callback("🔔 SYSTEM", message.get('message'), None)
                elif message.get('type') == 'leave':
                    if self.message_callback:
                        self.message_callback("🔔 SYSTEM", message.get('message'), None)
            except:
                break
        self.running = False
    
    def send_message(self, message, target=None):
        """ارسال پیام عمومی یا خصوصی"""
        if not self.socket or not self.running:
            return False
        
        try:
            encrypted = self.crypto.encrypt_message(message)
            if target:
                payload = {"type": "private", "target": target, "content": encrypted}
            else:
                payload = {"type": "message", "content": encrypted}
            self.socket.send(json.dumps(payload).encode())
            return True
        except:
            return False
    
    def disconnect(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.log("👋 Disconnected")
