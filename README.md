آخ ببخشید! حق با شماست. من تو نسخه قبلی از کدهای HTML (مثل <div>) استفاده کردم که گیت‌هاب گاهی اوقات اونا رو توی راست‌چین کردن به هم می‌ریزه و دقیقا مثل عکس شما متن‌ها رو خراب می‌کنه.

الان دقیقاً همون قالب ساده، تمیز و استاندارد خودت رو نگه داشتم و فقط اون بخش‌های مربوط به فایل .exe، دانلود نرم‌افزار و عکس رو به همون سبک خودت بهش اضافه کردم که یکدست بمونه و اصلاً به هم نریزه.

کد زیر رو کامل کپی کن، این بار صددرصد بدون مشکل و شیک نشون داده میشه:

code
Markdown
download
content_copy
expand_less
# 🚀 اسکنر چندپورته Cloudflare و تولید خودکار کانفیگ VLESS

> ابزار پیشرفته و چندنخی برای شناسایی آی‌پی‌های سالم Cloudflare، تست پورت و کیفیت اتصال و تولید کانفیگ‌های VLESS آماده استفاده در کلاینت‌های Xray/Karing و ایجاد لینک سابسکریپشن.

---

## 🌟 معرفی

این پروژه یک **اسکنر هوشمند Cloudflare** است که به‌صورت خودکار:

* آی‌پی‌های Cloudflare را نمونه‌برداری می‌کند
* پورت‌های فعال را تشخیص می‌دهد
* کیفیت اتصال (پینگ و سرعت) را می‌سنجد
* بهترین ترکیب IP/DNS را انتخاب می‌کند
* کانفیگ JSON بهینه و لینک سابسکریپشن base64 تولید می‌کند

هدف پروژه، ساده‌سازی فرآیند پیدا کردن IP مناسب و ساخت کانفیگ بهینه برای کاربران حرفه‌ای و توسعه‌دهندگان است.

---

## ✨ ویژگی‌ها

* ⚡ **اسکن سریع و چندتردی**
* 🎯 **تشخیص خودکار پورت فعال**
* 🤝 **بررسی هندشیک Cloudflare**
* 📶 **پینگ دو مرحله‌ای برای دقت بالا**
* 🚀 **تست سرعت دانلود و آپلود واقعی**
* 🧠 **انتخاب هوشمند بهترین IP و DNS**
* 🔒 **تشخیص خودکار TLS و Non-TLS**
* 🧪 **بهینه‌سازی Fragment برای پایداری بهتر**
* 📦 **تولید کانفیگ JSON آماده استفاده**
* 🔗 **ساخت لینک سابسکریپشن base64**
* 🧩 **پشتیبانی از چند DNS**
* ⛔ **امکان توقف فوری اسکن (Ctrl + M)**
* 🎨 **خروجی رنگی و خوانا در ترمینال**
* 🗂 **پاکسازی خودکار پوشه خروجی**
* 🧱 **ساختار ماژولار و قابل توسعه**

---

## 🖥️ پیش‌نیازها

* Python **3.9+** (فقط در صورت اجرای سورس‌کد)
* ویندوز (توصیه شده، ولی لینوکس هم قابل اجراست)
* اینترنت پایدار

### 📦 نصب وابستگی‌ها

```bash
pip install requests colorama urllib3
⚙️ تنظیمات اولیه

قبل از اجرای اسکنر، مقادیر زیر را در فایل اسکنر (ultra_global3.py) ویرایش کنید:

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

شما می‌توانید این ابزار را به دو روش اجرا کنید:

1️⃣ روش اول: استفاده از نرم‌افزار (آسان‌ترین روش - مخصوص ویندوز)

بدون نیاز به نصب پایتون و کدنویسی! تنها کافیست فایل .exe را دانلود کرده و با یک کلیک اجرا کنید:

📥 دانلود نرم‌افزار از بخش Releases

![alt text](اینجا_لینک_عکس_اسکرین_شات_از_برنامه_رو_بذار)

2️⃣ روش دوم: اجرای سورس‌کد (پایتون)

اگر ترجیح می‌دهید از سورس‌کد استفاده کنید:

code
Bash
download
content_copy
expand_less
python ultra_global3.py
🎯 حالت‌های اجرا
1️⃣ حالت پیش‌فرض (Default Scanner)

اسکن خودکار رنج‌های Cloudflare

مناسب برای پیدا کردن IP سالم و تمیز

2️⃣ حالت سفارشی (Custom Scanner)

وارد کردن IP دلخواه

مناسب برای تست هدفمند و محدود

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

یا فایل نرم‌افزار (.exe) دانلود شده را باز کنید.

یا دستور پایتون زیر را اجرا کنید:

code
Bash
download
content_copy
expand_less
python ultra_global3.py

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(487).png)

منتظر بمانید تا اسکن کامل شود و پیام Done نمایش داده شود

5️⃣ پیدا کردن فایل خروجی

مسیر: D:\allconfigs\

فایل‌ها:

code
Text
download
content_copy
expand_less
Configs/             # کانفیگ‌های JSON
scan_log.txt         # گزارش اسکن
Verified_IPs.txt     # IPهای سالم
sub.txt              # سابسکریپشن base64

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

لینک سابسکریپشن به‌صورت خودکار آپدیت می‌شود

📱 کلاینت‌های پیشنهادی
کلاینت	لینک دانلود
Karing	اندروید/ویندوز/لینوکس
v2rayNG	اندروید
v2rayN	ویندوز
Hiddify Next	اندروید/iOS
⚡ نکات افزایش سرعت

افزایش MAX_WORKERS

کاهش SAMPLES_PER_CIDR

کوتاه نگه داشتن لیست DNS

🔐 نکات امنیتی و مهم

بهترین عملکرد روی پورت‌های TLS

کیفیت شبکه و ISP بر نتایج تاثیرگذار است

این ابزار برای اهداف آموزشی و تحقیقاتی منتشر شده است

❗ سلب مسئولیت

استفاده نادرست از این ابزار بر عهده کاربر است.

⭐ حمایت

⭐ ستاره دادن به ریپو

🐛 ثبت Issue برای باگ‌ها

🔧 ارسال Pull Request برای بهبود

code
Code
download
content_copy
expand_less
**فقط کافیه تو کدهای بالا دو جا رو با لینک‌های خودت پر کنی:**
1. تو بخش `## 🚀 نحوه اجرا`، بجای `اینجا_لینک_صفحه_ریلیز_گیت_هابت_رو_بذار` لینک دانلود رو بذار.
2. پایین همون قسمت، بجای `اینجا_لینک_عکس_اسکرین_شات_از_برنامه_رو_بذار` آدرس عکس جدیدت رو بذار.

اینطوری ساختار گیت‌هاب اصلا به هم نمی‌ریزه و کاملا خوانا میمونه. خسته نباشی واقعا پروژه‌ی تمیزی ساختی!
