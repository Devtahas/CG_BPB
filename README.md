
🚀 اسکنر چندپورته Cloudflare و تولید خودکار کانفیگ VLESS

ابزار پیشرفته و چندنخی برای شناسایی آی‌پی‌های سالم Cloudflare، تست پورت و کیفیت اتصال و تولید کانفیگ‌های VLESS آماده استفاده در کلاینت‌های Xray/Karing و ایجاد لینک سابسکریپشن.

🌟 معرفی

این پروژه یک اسکنر هوشمند Cloudflare است که به‌صورت خودکار:

آی‌پی‌های Cloudflare را نمونه‌برداری می‌کند

پورت‌های فعال را تشخیص می‌دهد

کیفیت اتصال (پینگ و سرعت) را می‌سنجد

بهترین ترکیب IP/DNS را انتخاب می‌کند

کانفیگ JSON بهینه و لینک سابسکریپشن base64 تولید می‌کند

هدف پروژه، ساده‌سازی فرآیند پیدا کردن IP مناسب و ساخت کانفیگ بهینه برای کاربران حرفه‌ای و توسعه‌دهندگان است.

✨ ویژگی‌ها

⚡ اسکن سریع و چندتردی

🎯 تشخیص خودکار پورت فعال

🤝 بررسی هندشیک Cloudflare

📶 پینگ دو مرحله‌ای برای دقت بالا

🚀 تست سرعت دانلود و آپلود واقعی

🧠 انتخاب هوشمند بهترین IP و DNS

🔒 تشخیص خودکار TLS و Non-TLS

🧪 بهینه‌سازی Fragment برای پایداری بهتر

📦 تولید کانفیگ JSON آماده استفاده

🔗 ساخت لینک سابسکریپشن base64

🧩 پشتیبانی از چند DNS

⛔ امکان توقف فوری اسکن (Ctrl + M / Enter)

🎨 خروجی رنگی و خوانا در ترمینال

🗂 پاکسازی خودکار پوشه خروجی

🧱 ساختار ماژولار و قابل توسعه

🖥️ پیش‌نیازها (برای اجرای سورس‌کد)

اگر قصد استفاده از نسخه نرم‌افزاری (.exe) را دارید، نیازی به نصب هیچ پیش‌نیازی ندارید! اما برای اجرای اسکریپت پایتون:

Python 3.9+

اینترنت پایدار

📦 نصب وابستگی‌ها
code
Bash
download
content_copy
expand_less
pip install requests colorama urllib3
⚙️ تنظیمات اولیه

قبل از اجرای اسکنر، مقادیر زیر را در فایل اسکنر ویرایش کنید:

code
Python
download
content_copy
expand_less
WORKER_HOST = "your-worker.workers.dev"
WS_PATH = "/your-websocket-path"
USER_UUID = "یک-UUID-رندوم-اینجا"

⚠️ UUID رندوم بسازید: https://www.uuidgenerator.net/

🔧 تنظیمات قابل شخصی‌سازی
متغیر	توضیح
HTTP_PORTS	پورت‌هایی که تست می‌شوند
CLOUDFLARE_CIDRS	رنج‌های آی‌پی Cloudflare
SAMPLES_PER_CIDR	تعداد نمونه‌برداری از هر رنج
MAX_WORKERS	تعداد تردهای همزمان
TIMEOUT	تایم‌اوت اتصال
DNS_SERVERS	لیست DNSهای مورد استفاده
🚀 نحوه اجرا

شما می‌توانید این اسکنر را به دو روش مختلف اجرا کنید:

🌟 روش اول: استفاده از نرم‌افزار (آسان‌ترین روش - مخصوص ویندوز)

نیازی به نصب پایتون و پیش‌نیازها ندارید! تنها کافیست فایل اجرایی نرم‌افزار را دانلود کرده و با یک کلیک اسکن را شروع کنید.

📥 دانلود نرم‌افزار از بخش Releases

![alt text](اینجا_لینک_عکس_اسکرین_شات_از_برنامه_رو_بذار)

💻 روش دوم: اجرای اسکریپت پایتون (برای سورس‌کد و توسعه‌دهندگان)

اگر پایتون روی سیستم شما نصب است، می‌توانید اسکریپت را مستقیماً از طریق ترمینال اجرا کنید:

code
Bash
download
content_copy
expand_less
python ultra_global3.py
🎯 حالت‌های اجرا
1️⃣ حالت پیش‌فرض (Default Scanner)

اسکن خودکار رنج‌های رسمی و مخفی (BGP) Cloudflare

مناسب برای پیدا کردن IP سالم و تمیز به صورت انبوه

2️⃣ حالت سفارشی (Custom Scanner)

وارد کردن IP دلخواه (با کاما یا فاصله)

مناسب برای تست هدفمند و محدود آی‌پی‌های خاص

📝 آموزش بدست آوردن مقادیر WORKER_HOST و WS_PATH
1️⃣ ساخت پنل BPB و دریافت کانفیگ‌ها

وارد پنل BPB شوید

کانفیگ‌ها را دانلود کنید

یک کانفیگ انتخاب و باز کنید

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/config-sample.png.jpg)

2️⃣ پیدا کردن WORKER_HOST و WS_PATH

کانفیگ موردنظر را در کلاینت باز کنید و روی ویرایش کلیک کنید

دنبال path بگردید

WORKER_HOST: آدرس ورکر (مثال: test.sajdgsh.workers.dev)

WS_PATH: رشته WebSocket path (مثال: /NEJEJDHDVBDJDJDVHDIDHjdvhdksovQS5PTkxJTkURJKEJEHV0=?ed=2560)

3️⃣ جایگذاری در اسکنر
code
Python
download
content_copy
expand_less
WORKER_HOST = "test.sajdgsh.workers.dev"
WS_PATH = "/NEJEJDHDVBDJDJDVHDIDHjdvhdksovQS5PTkxJTkURJKEJEHV0=?ed=2560"
USER_UUID = "یک-UUID-رندوم-اینجا"
4️⃣ اجرای اسکنر

اطمینان از عدم اتصال به VPN

شروع اسکن:

اگر نرم‌افزار .exe را دانلود کرده‌اید: روی فایل دابل‌کلیک کنید تا برنامه باز شود.

اگر از ترمینال استفاده می‌کنید: دستور python ultra_global3.py را وارد کنید.

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(487).png)

منتظر بمانید تا اسکن کامل شود و جدول گزارش نهایی به همراه پیام DONE! نمایش داده شود. (هر زمان که خواستید می‌توانید با فشردن کلید Enter اسکن را متوقف کرده و کانفیگ‌ها را دریافت کنید).

5️⃣ پیدا کردن فایل خروجی

مسیر: D:\allconfigs\ (یا C:\Temp در صورت نبودن درایو D)

فایل‌ها:

code
Text
download
content_copy
expand_less
Configs/             # کانفیگ‌های JSON تفکیک شده با نام کشور و پورت
scan_log.txt         # گزارش متنی کامل اسکن
Verified_IPs.txt     # لیست IPهای سالم و تمیز
sub.txt              # لینک سابسکریپشن کدگذاری شده (Base64)

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(488).png)

6️⃣ آپلود سابسکریپشن در GitHub

وارد GitHub شوید

ریپو بسازید و sub.txt را آپلود کنید

روی گزینه Raw کلیک کنید تا لینک مستقیم دریافت شود

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(489).png)


![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/photo_2026-02-20_18-31-16.jpg)

7️⃣ استفاده در کلاینت‌ها

لینک Raw را کپی کنید

در کلاینت Karing یا v2rayNG، گزینه Import Subscription را بزنید

لینک را پیست کنید و Update کنید ✅

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(490).png)

8️⃣ نکته مهم

اگر بعد از چند روز سرعت کند شد:

دوباره اسکنر را اجرا کنید

فایل جدید sub.txt را آپلود کنید و قبلی را حذف کنید

لینک سابسکریپشن در کلاینت شما (با یکبار Update کردن) به‌صورت خودکار آپدیت می‌شود

📱 کلاینت‌های پیشنهادی
کلاینت	لینک دانلود
Karing	اندروید/ویندوز/لینوکس
v2rayNG	اندروید
v2rayN	ویندوز
Hiddify Next	اندروید/iOS
⚡ نکات افزایش سرعت

افزایش MAX_WORKERS در کد (بسته به قدرت سیستم شما)

کاهش SAMPLES_PER_CIDR

کوتاه نگه داشتن لیست DNS

🔐 نکات امنیتی و مهم

بهترین عملکرد روی پورت‌های TLS به خصوص با پروتکل H2 (HTTP/2) است.

کیفیت شبکه و ISP بر نتایج تاثیرگذار است.

این ابزار برای اهداف آموزشی و تحقیقاتی منتشر شده است.

❗ سلب مسئولیت

استفاده نادرست از این ابزار بر عهده کاربر است.

⭐ حمایت

⭐ ستاره دادن به ریپو

🐛 ثبت Issue برای باگ‌ها

🔧 ارسال Pull Request برای بهبود
