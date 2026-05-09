# tab_dns.py
from tabs.dns.dns_ui import DNSChangerUI

class DNSChangerFrame(DNSChangerUI):
    """کلاس پوششی برای DNS Changer که asset_manager مخصوص main.pyw را مدیریت می‌کند."""
    def __init__(self, master, app_controller=None, **kwargs):
        # asset_manager را از kwargs بیرون می‌کشد تا به کلاس اصلی نرسد
        asset_manager = kwargs.pop('asset_manager', None)
        
        # حالا کلاس اصلی DNSChangerUI را فراخوانی کن
        super().__init__(master, app_controller=app_controller, **kwargs)
        
        # اگر لازم شد می‌توانی asset_manager را اینجا ذخیره کنی
        self.asset_manager = asset_manager
