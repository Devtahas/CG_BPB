# tabs/client/__init__.py
from .client_ui import ClientUI
from .client_core import ClientCore
from .client_import import ClientImport
from .client_utils import ClientUtils
from .client_configs import ClientConfigs

# برای سازگاری با نسخه‌های قبلی
ClientFrame = ClientUI

__all__ = [
    'ClientCore',
    'ClientUI',
    'ClientFrame',
    'ClientImport',
    'ClientUtils',
    'ClientConfigs'
]
