# tabs/crypto_manager.py

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
    """مدیریت رمزنگاری فایل‌های ذخیره‌سازی (AES-256-GCM)"""

    SALT_SIZE = 16
    IV_SIZE = 12
    KEY_LENGTH = 32
    ITERATIONS = 100000

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.base_dir = storage_dir
        else:
            # مسیر پیش‌فرض: Desktop/NetTools_Data
            self.base_dir = os.path.join(os.path.expanduser("~"), "Desktop", "NetTools_Data")

        self._enabled = False
        self._password = None
        self._key = None
        self.config_file = os.path.join(self.base_dir, "crypto_config.json")
        self.quarantine_dir = os.path.join(self.base_dir, "quarantine")
        self._load_config()

    def set_base_dir(self, new_base_dir: str) -> None:
        """تغییر مسیر پایه ذخیره‌سازی فایل‌های رمزنگاری"""
        self.base_dir = new_base_dir
        self.config_file = os.path.join(self.base_dir, "crypto_config.json")
        self.quarantine_dir = os.path.join(self.base_dir, "quarantine")
        # بارگذاری مجدد وضعیت از مسیر جدید (در صورت وجود)
        self._load_config()

    # ------------------------------------------------------------------
    # مدیریت وضعیت و رمز عبور (بدون تغییر)
    # ------------------------------------------------------------------
    def _load_config(self):
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

    def _save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            config = {'enabled': self._enabled}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f)
        except:
            pass

    @property
    def enabled(self):
        return self._enabled and CRYPTO_AVAILABLE

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._save_config()

    def is_available(self):
        return CRYPTO_AVAILABLE

    def set_password(self, password: str):
        self._password = password
        return True

    def _derive_key(self, salt: bytes):
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

    def _encrypt_data(self, data: bytes):
        salt = os.urandom(self.SALT_SIZE)
        iv = os.urandom(self.IV_SIZE)
        key = self._derive_key(salt)
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return salt + iv + ciphertext + encryptor.tag

    def _decrypt_data(self, encrypted_data: bytes):
        salt = encrypted_data[:self.SALT_SIZE]
        iv = encrypted_data[self.SALT_SIZE:self.SALT_SIZE + self.IV_SIZE]
        tag = encrypted_data[-16:]
        ciphertext = encrypted_data[self.SALT_SIZE + self.IV_SIZE:-16]
        key = self._derive_key(salt)
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def _get_encrypted_path(self, original_path: str):
        return original_path + '.enc'

    def _quarantine_file(self, filepath: str):
        """فایل معیوب را به پوشه قرنطینه منتقل می‌کند (در صورت امکان)"""
        try:
            os.makedirs(self.quarantine_dir, exist_ok=True)
            dest = os.path.join(self.quarantine_dir, os.path.basename(filepath))
            # اگر فایلی با این نام در قرنطینه وجود داشت، یک شماره اضافه کن
            counter = 1
            base, ext = os.path.splitext(dest)
            while os.path.exists(dest):
                dest = f"{base}_{counter}{ext}"
                counter += 1
            shutil.move(filepath, dest)
            return True
        except Exception:
            # اگر نشد منتقل کرد، لااقل rename کن تا دوباره بازنویسی نشود
            try:
                os.rename(filepath, filepath + '.bak')
            except:
                pass
            return False

    # =================================================================
    # عملیات فایل (با اصلاح حذف فایل اصلی پس از رمزنگاری)
    # =================================================================
    def encrypt_file(self, filepath: str):
        if not self.enabled or not self._password:
            return False
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            encrypted = self._encrypt_data(data)
            enc_path = self._get_encrypted_path(filepath)
            with open(enc_path, 'wb') as f:
                f.write(encrypted)
            # حذف فایل اصلی
            try:
                os.remove(filepath)
            except Exception:
                pass
            return True
        except Exception:
            return False

    def decrypt_file(self, enc_filepath: str, output_path: Optional[str] = None):
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
            # **اصلاح:** فایل را حذف نمی‌کنیم؛ آن را قرنطینه می‌کنیم
            self._quarantine_file(enc_filepath)
            return None

    def safe_open(self, filepath: str, mode: str = 'r', encoding: str = 'utf-8'):
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
                    # خطا در رمزگشایی – فایل enc قبلاً به قرنطینه منتقل شده
                    return open(filepath, mode, encoding=encoding) if os.path.exists(filepath) else None
            else:
                return open(filepath, mode, encoding=encoding)
        else:
            if self.enabled:
                import io
                buffer = io.BytesIO() if 'b' in mode else io.StringIO()
                return _CryptoWriteWrapper(self, filepath, buffer, mode, encoding)
            else:
                return open(filepath, mode, encoding=encoding)

    # =================================================================
    # load_json / save_json (با اولویت فایل رمزنگاری شده)
    # =================================================================
    def load_json(self, filepath: str):
        enc_path = self._get_encrypted_path(filepath)
        if self.enabled and os.path.exists(enc_path):
            data = self.decrypt_file(enc_path)
            if data is not None:
                try:
                    return json.loads(data.decode('utf-8'))
                except Exception:
                    # محتوای رمزگشایی شده JSON معتبر نیست – فایل را قرنطینه کن
                    self._quarantine_file(enc_path)
            # اگر رمزگشایی شکست خورد (یا JSON نادرست بود)، تلاش کن فایل اصلی قدیمی را بخوانی
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
            return None
        else:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return None
            return None

    def save_json(self, filepath: str, data: Any):
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            json_bytes = json_str.encode('utf-8')
            if self.enabled and self._password:
                encrypted = self._encrypt_data(json_bytes)
                enc_path = self._get_encrypted_path(filepath)
                with open(enc_path, 'wb') as f:
                    f.write(encrypted)
                # حذف فایل اصلی (در صورت وجود) تا همیشه اولویت با .enc باشد
                if os.path.exists(filepath):
                    try: os.remove(filepath)
                    except: pass
            else:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(json_str)
            return True
        except:
            return False

    def encrypt_all_existing(self):
        if not self.enabled or not self._password:
            return 0
        count = 0
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith(('.json', '.txt')) and not file.endswith('.enc'):
                    filepath = os.path.join(root, file)
                    if self.encrypt_file(filepath):
                        count += 1
        return count

    def decrypt_all(self, output_dir: Optional[str] = None):
        if not self.enabled or not self._password:
            return 0
        count = 0
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith('.enc'):
                    enc_path = os.path.join(root, file)
                    orig_path = enc_path[:-4]
                    if self.decrypt_file(enc_path, orig_path):
                        count += 1
        return count


class _CryptoWriteWrapper:
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
            # حذف فایل اصلی (در صورت نوشتن و سپس رمزنگاری)
            if os.path.exists(self.filepath):
                try: os.remove(self.filepath)
                except: pass
        except:
            pass

    def write(self, s):
        self.buffer.write(s)

    def writelines(self, lines):
        self.buffer.writelines(lines)

    def flush(self):
        pass


# ==========================================================
# نمونه سراسری با مسیر پیش‌فرض
# ==========================================================
storage_crypto = StorageCrypto()
