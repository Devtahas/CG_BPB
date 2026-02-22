

code
Markdown
download
content_copy
expand_less
<div align="center">

# 🚀 Cloudflare Multi-Port Scanner & VLESS Generator

**ابزار پیشرفته و چندنخی برای شناسایی آی‌پی‌های سالم کلودفلر، تست پورت، و تولید خودکار کانفیگ‌های بهینه VLESS**

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg?style=flat-square&logo=python)](#)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](#)

<br>

### 📥 دانلود و اجرای سریع (بدون نیاز به پایتون)
برای کاربران ویندوز، نیازی به نصب پایتون و کدنویسی نیست! برنامه را با یک کلیک اجرا کنید:

[![Download Release](https://img.shields.io/badge/⬇️_Download-.EXE_File-1f425f?style=for-the-badge)](لینک_صفحه_ریلیزهای_خود_را_اینجا_قرار_دهید)

<br>

### 📸 نمایی از محیط برنامه
> ![محیط ترمینال برنامه](لینک_عکس_اسکرین_شات_برنامه_خود_را_اینجا_قرار_دهید)

</div>

---

## ✨ ویژگی‌های برجسته

- ⚡ **اسکن مگا ماتریکسی:** بررسی همزمان رنج‌های رسمی و پنهان (BGP) کلودفلر.
- 🎯 **تشخیص هوشمند پورت:** یافتن پورت‌های باز HTTP و HTTPS.
- 📶 **سنجش دقیق پینگ و سرعت:** انجام تست‌های دانلود و آپلود واقعی روی هر آی‌پی.
- 🔒 **تولید کانفیگ HTTP/2:** دور زدن قدرتمند فیلترینگ (SNI Blocking) با پروتکل H2.
- 🌍 **تشخیص کشور خودکار:** استخراج لوکیشن آی‌پی‌های تمیز (Geolocation).
- 🔗 **سابسکریپشن خودکار:** ساخت خودکار فایل `sub.txt` با فرمت Base64.
- 🎨 **رابط کاربری جذاب:** نمایش جدول وضعیت اسکن در پایان کار به صورت رنگی.

---

## 💻 نحوه اجرا (برای توسعه‌دهندگان)

اگر قصد دارید سورس‌کد پایتون را اجرا کنید یا کدها را تغییر دهید:

```bash
# 1. Clone the repository
git clone https://github.com/YourUsername/YourRepo.git

# 2. Install requirements
pip install requests colorama urllib3

# 3. Run the scanner
python ultra_global3.py
⚙️ راهنمای تنظیمات و راه‌اندازی

برای اتصال اسکنر به ورکر (Worker) اختصاصی خود، باید ۳ متغیر اصلی را در فایل ultra_global3.py مقداردهی کنید:

۱. ساخت پنل BPB و دریافت کانفیگ

ابتدا وارد پنل BPB خود شوید و یک کانفیگ را برای استخراج اطلاعات باز کنید.

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/config-sample.png.jpg)

۲. استخراج مقادیر WORKER_HOST و WS_PATH

کانفیگ را در کلاینت خود ویرایش (Edit) کنید و اطلاعات زیر را کپی کنید:

WORKER_HOST: همان آدرس دامنه ورکر شماست (مثلاً test.sajdgsh.workers.dev)

WS_PATH: مسیر وب‌سوکت (مثلاً /NEJEJDHDVBDJDJDVHDIDHjdvhdksovQS5PTkxJTkURJKEJEHV0=?ed=2560)

⚠️ نکته: برای USER_UUID می‌توانید از سایت UUID Generator یک آیدی رندوم بسازید.

۳. جایگذاری در کد

این اطلاعات را در فایل اسکریپت ویرایش کنید:

code
Python
download
content_copy
expand_less
WORKER_HOST = "test.sajdgsh.workers.dev"
WS_PATH = "/NEJEJDHDVBDJDJDVHDIDHjdvhdksovQS5PTkxJTkURJKEJEHV0=?ed=2560"
USER_UUID = "یک-UUID-رندوم-اینجا"
🚀 شروع اسکن و دریافت خروجی

بدون VPN متصل شوید (فیلترشکن خود را خاموش کنید).

نرم‌افزار اجرایی (.exe) را باز کرده یا اسکریپت پایتون را اجرا کنید.

صبر کنید تا پروسه پایان یابد. هر زمان که خواستید می‌توانید با کلید Enter اسکن را متوقف کنید.

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(487).png)

📂 ساختار فایل‌های خروجی

پس از پایان اسکن، تمام فایل‌ها در درایو D:\allconfigs (یا C:\Temp) ذخیره می‌شوند:

code
Text
download
content_copy
expand_less
📦 allconfigs
 ┣ 📂 Configs/            # کانفیگ‌های JSON ساخته شده
 ┣ 📜 scan_log.txt        # لاگ کامل پروسه اسکن
 ┣ 📜 Verified_IPs.txt    # آی‌پی‌های تمیز و فعال
 ┗ 📜 sub.txt             # لینک سابسکریپشن کلاینت‌ها

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(488).png)

☁️ ساخت لینک سابسکریپشن همیشگی

در سایت GitHub یک ریپازیتوری عمومی (Public) بسازید.

فایل sub.txt را درون آن آپلود کنید.

وارد فایل شده و روی گزینه Raw کلیک کنید تا لینک مستقیم آن ساخته شود.

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(489).png)


![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/photo_2026-02-20_18-31-16.jpg)

این لینک Raw را کپی کرده و در بخش Import Subscription برنامه‌ی V2rayNG یا Karing قرار دهید و Update را بزنید.

![alt text](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(490).png)

📱 کلاینت‌های پیشنهادی
نام کلاینت	پلتفرم‌های پشتیبانی شده	لینک دانلود رسمی
Karing	اندروید / ویندوز / لینوکس / مک	دانلود از گیت‌هاب
v2rayNG	اندروید	دانلود از گیت‌هاب
v2rayN	ویندوز	دانلود از گیت‌هاب
Hiddify Next	تمام پلتفرم‌ها (کراس‌پلتفرم)	دانلود از گیت‌هاب
🛡️ سلب مسئولیت

این اسکریپت صرفاً با هدف آموزشی و تحقیقاتی برای تست کیفیت شبکه توسعه یافته است. هرگونه استفاده نادرست از آن بر عهده شخص کاربر می‌باشد.

<div align="center">
<b>اگر این پروژه برای شما مفید بود، لطفاً با دادن یک ⭐ (ستاره) از آن حمایت کنید!</b>
</div>
```


تغییراتی که اعمال کردم:

استفاده از تگ‌های <div align="center"> برای وسط‌چین کردن عناوین و عکس‌ها (دقیقاً مثل پروژه‌های معروف گیت‌هاب).

ساخت یک دکمه دانلود (Badge) گرافیکی برای فایل اجرایی .exe که کاربر با دیدنش سریعاً متوجه بشه.

اضافه کردن آیکون و نشان‌ها (مثل لایسنس و ورژن پایتون) در بالای صفحه برای حرفه‌ای‌تر شدن نما.

جدول‌بندی زیباتر کلاینت‌ها.

استفاده از قالب‌بندی درختی برای نمایش فایل‌های خروجی (📂 Configs).

همینو کپی کن توی فایل ریدمی‌ات، پیش‌نمایشش رو ببین؛ قطعا همون چیزیه که اون توسعه‌دهنده ازت انتظار داره! باز هم اگه تغییری لازم داشت بگو.
