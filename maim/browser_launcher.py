# browser_launcher.py
import sys
import webview

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
    # تنظیم User-Agent در نسخه‌های جدید pywebview به صورت زیر امکان‌پذیر است:
    # webview.create_window(..., user_agent="...")
    # برای جلوگیری از خطا، فعلاً از پیش‌فرض استفاده می‌کنیم
    webview.create_window("NetTools Secure Browser", url, width=1024, height=768,
                          resizable=True, fullscreen=False, min_size=(800, 600),
                          confirm_close=False, easy_drag=False)
    webview.start(gui='edge', debug=False)

if __name__ == "__main__":
    main()
