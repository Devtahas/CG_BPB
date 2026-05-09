# tabs/setting/storage_crypto.py
import os
import sys
import json
import base64
import hashlib
import shutil
from typing import Optional, Union, Any

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class StorageCrypto:
    """
    مدیریت رمزنگاری فایل‌های ذخیره‌سازی (AES-256-GCM)
    ویژگی‌ها:
        - رمزنگاری/رمزگشایی فایل‌های JSON و متنی
        - استفاده از PBKDF2 برای تولید کلید از رمز عبور
        - قابلیت فعال/غیرفعال شدن
        - ذخیره‌سازی امن Salt و IV به همراه فایل رمز شده
    """

    SALT_SIZE = 16
    IV_SIZE = 12
    KEY_LENGTH = 32
    ITERATIONS = 100000

    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self._enabled = False
        self._password = None
        self._key = None
        self.config_file = os.path.join(storage_dir, "crypto_config.json")
        self.quarantine_dir = os.path.join(storage_dir, "quarantine")

        self._load_config()

    # ------------------------------------------------------------------
    # مدیریت وضعیت و رمز عبور
    # ------------------------------------------------------------------
    def _load_config(self) -> None:
        """بارگذاری تنظیمات رمزنگاری (فعال/غیرفعال)"""
        if not CRYPTO_AVAILABLE:
            self._enabled = False
            return

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._enabled = config.get('enabled', False)
            except:
                self._enabled = False

    def _save_config(self) -> None:
        """ذخیره تنظیمات رمزنگاری"""
        try:
            config = {'enabled': self._enabled}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f)
        except:
            pass

    @property
    def enabled(self) -> bool:
        return self._enabled and CRYPTO_AVAILABLE

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._save_config()

    def is_available(self) -> bool:
        return CRYPTO_AVAILABLE

    def set_password(self, password: str) -> bool:
        """
        تنظیم رمز عبور اصلی و تولید کلید رمزنگاری
        Returns: True در صورت موفقیت
        """
        if not CRYPTO_AVAILABLE:
            return False

        self._password = password
        # تولید کلید از رمز عبور (در زمان نیاز با salt انجام می‌شود)
        return True

    def _derive_key(self, salt: bytes) -> bytes:
        """تولید کلید ۳۲ بایتی از رمز عبور و salt"""
        if not self._password:
            raise ValueError("Password not set")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(self._password.encode('utf-8'))

    def _encrypt_data(self, data: bytes) -> bytes:
        """
        رمزنگاری داده‌ها
        خروجی: salt + iv + ciphertext + tag
        """
        salt = os.urandom(self.SALT_SIZE)
        iv = os.urandom(self.IV_SIZE)
        key = self._derive_key(salt)

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()

        # ترکیب: salt (16) + iv (12) + ciphertext + tag (16)
        return salt + iv + ciphertext + encryptor.tag

    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """
        رمزگشایی داده‌ها
        ورودی: salt + iv + ciphertext + tag
        """
        salt = encrypted_data[:self.SALT_SIZE]
        iv = encrypted_data[self.SALT_SIZE:self.SALT_SIZE + self.IV_SIZE]
        tag = encrypted_data[-16:]
        ciphertext = encrypted_data[self.SALT_SIZE + self.IV_SIZE:-16]

        key = self._derive_key(salt)

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    # ------------------------------------------------------------------
    # عملیات فایل
    # ------------------------------------------------------------------
    def _get_encrypted_path(self, original_path: str) -> str:
        """مسیر فایل رمزنگاری شده (با پسوند .enc)"""
        return original_path + '.enc'

    def _quarantine_file(self, filepath: str):
        """فایل معیوب را به پوشه قرنطینه منتقل می‌کند (در صورت امکان)"""
        try:
            os.makedirs(self.quarantine_dir, exist_ok=True)
            dest = os.path.join(self.quarantine_dir, os.path.basename(filepath))
            counter = 1
            base, ext = os.path.splitext(dest)
            while os.path.exists(dest):
                dest = f"{base}_{counter}{ext}"
                counter += 1
            shutil.move(filepath, dest)
            return True
        except Exception:
            try:
                os.rename(filepath, filepath + '.bak')
            except:
                pass
            return False

    def encrypt_file(self, filepath: str) -> bool:
        """
        رمزنگاری یک فایل و جایگزینی آن با نسخه رمز شده
        """
        if not self.enabled or not self._password:
            return False

        try:
            with open(filepath, 'rb') as f:
                data = f.read()

            encrypted = self._encrypt_data(data)
            enc_path = self._get_encrypted_path(filepath)

            with open(enc_path, 'wb') as f:
                f.write(encrypted)

            # حذف فایل اصلی (اختیاری - می‌توان نسخه اصلی را نگه داشت)
            # os.remove(filepath)
            return True
        except Exception:
            return False

    def decrypt_file(self, enc_filepath: str, output_path: Optional[str] = None) -> Optional[bytes]:
        """
        رمزگشایی یک فایل رمزنگاری شده
        اگر output_path داده شود، فایل رمزگشایی شده در آن مسیر ذخیره می‌شود
        در غیر این صورت داده‌های رمزگشایی شده برگردانده می‌شوند
        """
        if not self.enabled or not self._password:
            return None

        try:
            with open(enc_filepath, 'rb') as f:
                encrypted = f.read()

            decrypted = self._decrypt_data(encrypted)

            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(decrypted)
            return decrypted
        except Exception:
            # در صورت شکست، فایل را قرنطینه می‌کنیم تا از دست نرود
            self._quarantine_file(enc_filepath)
            return None

    def safe_open(self, filepath: str, mode: str = 'r', encoding: str = 'utf-8') -> Any:
        """
        جایگزین امن برای open() که به صورت شفاف رمزگشایی می‌کند
        """
        enc_path = self._get_encrypted_path(filepath)

        if 'r' in mode:
            if self.enabled and os.path.exists(enc_path):
                data = self.decrypt_file(enc_path)
                if data is not None:
                    if 'b' in mode:
                        import io
                        return io.BytesIO(data)
                    else:
                        import io
                        return io.StringIO(data.decode(encoding))
                else:
                    # fallback به فایل اصلی (فایل enc قبلاً به قرنطینه رفته)
                    return open(filepath, mode, encoding=encoding) if os.path.exists(filepath) else None
            else:
                return open(filepath, mode, encoding=encoding)
        else:  # write mode
            if self.enabled:
                # برای نوشتن، ابتدا در حافظه ذخیره می‌کنیم
                import io
                buffer = io.BytesIO() if 'b' in mode else io.StringIO()
                return _CryptoWriteWrapper(self, filepath, buffer, mode, encoding)
            else:
                return open(filepath, mode, encoding=encoding)

    def load_json(self, filepath: str) -> Optional[Any]:
        """بارگذاری امن فایل JSON (رمزگشایی خودکار)"""
        enc_path = self._get_encrypted_path(filepath)

        if self.enabled and os.path.exists(enc_path):
            data = self.decrypt_file(enc_path)
            if data is not None:
                try:
                    return json.loads(data.decode('utf-8'))
                except Exception:
                    # داده رمزگشایی شد ولی JSON معتبر نیست – فایل قرنطینه
                    self._quarantine_file(enc_path)
                    return None
            # اگر decrypt_file شکست خورد قبلاً قرنطینه شده، فقط برگرد None
            return None
        else:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return None
            return None

    def save_json(self, filepath: str, data: Any) -> bool:
        """ذخیره امن فایل JSON (رمزنگاری خودکار)"""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            json_bytes = json_str.encode('utf-8')

            if self.enabled and self._password:
                encrypted = self._encrypt_data(json_bytes)
                enc_path = self._get_encrypted_path(filepath)
                with open(enc_path, 'wb') as f:
                    f.write(encrypted)
                # ذخیره همزمان نسخه غیررمز (اختیاری)
                # with open(filepath, 'w', encoding='utf-8') as f:
                #     f.write(json_str)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(json_str)
            return True
        except Exception:
            return False

    def encrypt_all_existing(self) -> int:
        """
        رمزنگاری تمام فایل‌های JSON/TXT موجود در storage_dir
        Returns: تعداد فایل‌های رمزنگاری شده
        """
        if not self.enabled or not self._password:
            return 0

        count = 0
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                if file.endswith(('.json', '.txt')) and not file.endswith('.enc'):
                    filepath = os.path.join(root, file)
                    if self.encrypt_file(filepath):
                        count += 1
        return count

    def decrypt_all(self, output_dir: Optional[str] = None) -> int:
        """
        رمزگشایی تمام فایل‌های .enc و ذخیره نسخه اصلی
        """
        if not self.enabled or not self._password:
            return 0

        count = 0
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                if file.endswith('.enc'):
                    enc_path = os.path.join(root, file)
                    orig_path = enc_path[:-4]
                    if self.decrypt_file(enc_path, orig_path):
                        count += 1
        return count


class _CryptoWriteWrapper:
    """Wrapper برای نوشتن فایل رمزنگاری شده"""
    def __init__(self, crypto: StorageCrypto, filepath: str, buffer, mode: str, encoding: str):
        self.crypto = crypto
        self.filepath = filepath
        self.buffer = buffer
        self.mode = mode
        self.encoding = encoding

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._finalize()

    def _finalize(self):
        try:
            if 'b' in self.mode:
                data = self.buffer.getvalue()
            else:
                data = self.buffer.getvalue().encode(self.encoding)

            encrypted = self.crypto._encrypt_data(data)
            enc_path = self.crypto._get_encrypted_path(self.filepath)
            with open(enc_path, 'wb') as f:
                f.write(encrypted)

            # همچنین ذخیره نسخه اصلی (اختیاری)
            # with open(self.filepath, 'w', encoding=self.encoding) as f:
            #     if 'b' not in self.mode:
            #         f.write(self.buffer.getvalue())
        except Exception:
            pass

    def write(self, s):
        self.buffer.write(s)

    def writelines(self, lines):
        self.buffer.writelines(lines)

    def flush(self):
        pass
