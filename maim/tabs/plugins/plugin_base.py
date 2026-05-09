# tabs/plugins/plugin_base.py

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

class BasePlugin(ABC):
    """
    کلاس پایه برای همه پلاگین‌ها.
    هر پلاگین باید از این کلاس ارث‌بری کند و متدهای لازم را پیاده‌سازی نماید.
    """

    def __init__(self, app_context: Optional[Any] = None):
        """
        Args:
            app_context: شیء اصلی اپلیکیشن (مثلاً App از main.pyw) برای دسترسی به سرویس‌ها و تب‌ها.
                         در صورت نیاز می‌توانید متدهای خاصی را در app_context تعریف کنید.
        """
        self.app = app_context
        self.manifest: Dict[str, Any] = {}  # توسط PluginManager پر می‌شود
        self._loaded = False

    @abstractmethod
    def on_load(self) -> None:
        """
        هنگام بارگذاری پلاگین فراخوانی می‌شود.
        اینجا منابع لازم را تخصیص دهید، تردها را اجرا کنید و ...
        """
        pass

    @abstractmethod
    def on_unload(self) -> None:
        """
        هنگام غیرفعال‌سازی یا حذف پلاگین فراخوانی می‌شود.
        اینجا منابع را آزاد کنید، تردها را متوقف کنید و ...
        """
        pass

    def get_ui_panel(self, parent: Any) -> Optional[Any]:
        """
        اختیاری: یک ویجت customtkinter (مثلاً CTkFrame) برمی‌گرداند که در تب Plugin نمایش داده می‌شود.
        اگر None برگردانید، پلاگین فقط در پس‌زمینه عمل می‌کند.
        
        Args:
            parent: والد customtkinter که پنل باید در آن قرار گیرد.
        """
        return None

    @property
    def name(self) -> str:
        return self.manifest.get("name", "Unnamed Plugin")

    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.0.0")

    @property
    def author(self) -> str:
        return self.manifest.get("author", "Unknown")

    def __repr__(self):
        return f"<Plugin: {self.name} v{self.version} by {self.author}>"
