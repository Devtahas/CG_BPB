# tabs/messenger/messenger_utils.py
import secrets
import string
import hashlib
import base64


class MessengerUtils:
    """توابع کمکی برای پیام‌رسان"""
    
    @staticmethod
    def generate_connection_password(length=12):
        """تولید رمز عبور یکبار مصرف برای اتصال به اتاق"""
        chars = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(chars) for _ in range(length))
        return password
    
    @staticmethod
    def generate_room_id(length=8):
        """تولید شناسه یکتا برای اتاق"""
        chars = string.ascii_uppercase + string.digits
        room_id = ''.join(secrets.choice(chars) for _ in range(length))
        return room_id
    
    @staticmethod
    def hash_password(password):
        """هش کردن رمز عبور با SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()[:16]
    
    @staticmethod
    def get_local_ip():
        """دریافت IP محلی دستگاه"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
