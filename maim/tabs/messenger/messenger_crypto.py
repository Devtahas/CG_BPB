# tabs/messenger/messenger_crypto.py
import ssl
import ipaddress
import secrets
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import os


class MessengerCrypto:
    """مدیریت رمزنگاری E2E و TLS 1.3"""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.peer_public_key = None
        self.session_key = None
        self._generate_keypair()
    
    def _generate_keypair(self):
        """تولید جفت کلید RSA برای هر کاربر"""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
    
    def get_public_key_pem(self):
        """دریافت کلید عمومی به صورت PEM برای انتقال"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def load_peer_public_key(self, pem_data):
        """بارگذاری کلید عمومی طرف مقابل"""
        self.peer_public_key = serialization.load_pem_public_key(
            pem_data.encode('utf-8'),
            backend=default_backend()
        )
    
    def encrypt_message(self, message):
        """رمزنگاری پیام با کلید عمومی طرف مقابل (RSA)"""
        if not self.peer_public_key:
            raise Exception("Peer public key not loaded")
        
        ciphertext = self.peer_public_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(ciphertext).decode('utf-8')
    
    def decrypt_message(self, encrypted_message):
        """رمزگشایی پیام با کلید خصوصی خود"""
        ciphertext = base64.b64decode(encrypted_message.encode('utf-8'))
        plaintext = self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext.decode('utf-8')
    
    @staticmethod
    def create_tls_context(cert_path=None, key_path=None):
        """ایجاد context TLS 1.3 برای امنیت ارتباط"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if cert_path else ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        if cert_path and key_path:
            context.load_cert_chain(cert_path, key_path)
        
        return context
    
    @staticmethod
    def generate_self_signed_cert(common_name="localhost"):
        """تولید گواهی خودامضا برای TLS (در محیط LAN)"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"IR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Tehran"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Tehran"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"NetTools"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem.decode('utf-8'), key_pem.decode('utf-8')
