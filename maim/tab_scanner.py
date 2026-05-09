# tab_scanner.py - فایل مرکزی اسکنر (فقط فراخوانی)
# تمام قابلیت‌های اسکنر به صورت ماژولار در پوشه tabs/scanner/ قرار دارد

import customtkinter as ctk
from tabs.scanner.scanner_ui import ScannerUI


# برای سازگاری با کدهای قبلی که از ScannerFrame استفاده می‌کردند
# و همچنین برای حفظ یکپارچگی با main.pyw
class ScannerFrame(ScannerUI):
    """کلاس اسکنر - سازگار با نسخه قبلی"""
    pass


# اگر بخواهید مستقیم از ScannerUI استفاده کنید:
# ScannerFrame = ScannerUI
