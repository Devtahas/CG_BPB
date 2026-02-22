

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

* Python **3.9+**
* ویندوز (توصیه شده، ولی لینوکس هم قابل اجراست)
* اینترنت پایدار

### 📦 نصب وابستگی‌ها

```bash
pip install requests colorama urllib3
```

---

## ⚙️ تنظیمات اولیه

قبل از اجرای اسکنر، مقادیر زیر را در فایل اسکنر (`ultra_global3.py`) ویرایش کنید:

```python
WORKER_HOST = "your-worker.workers.dev"
WS_PATH = "/your-websocket-path"
USER_UUID = "یک-UUID-رندوم-اینجا"
```

> ⚠️ UUID رندوم بسازید: [https://www.uuidgenerator.net/](https://www.uuidgenerator.net/)

---

## 🔧 تنظیمات قابل شخصی‌سازی

| متغیر              | توضیح                        |
| ------------------ | ---------------------------- |
| `HTTP_PORTS`       | پورت‌هایی که تست می‌شوند     |
| `CLOUDFLARE_CIDRS` | رنج‌های آی‌پی Cloudflare     |
| `SAMPLES_PER_CIDR` | تعداد نمونه‌برداری از هر رنج |
| `MAX_WORKERS`      | تعداد تردهای همزمان          |
| `TIMEOUT`          | تایم‌اوت اتصال               |
| `DNS_SERVERS`      | لیست DNSهای مورد استفاده     |

---

## 🚀 نحوه اجرا البته میتوانید از بخش release نرم افزار را دانلود کنید بدون نیاز به ران کردن و اجرای هیچ نوع کدی

```bash
python ultra_global3.py
```

---

## 🎯 حالت‌های اجرا

### 1️⃣ حالت پیش‌فرض (Default Scanner)

* اسکن خودکار رنج‌های Cloudflare
* مناسب برای پیدا کردن IP سالم و تمیز

### 2️⃣ حالت سفارشی (Custom Scanner)

* وارد کردن IP دلخواه
* مناسب برای تست هدفمند و محدود

---

## 📝 آموزش بدست آوردن مقادیر WORKER_HOST و WS_PATH

### 1️⃣ ساخت پنل BPB و دریافت کانفیگ‌ها

1. وارد پنل BPB شوید
2. کانفیگ‌ها را دانلود کنید
3. یک کانفیگ انتخاب و باز کنید

> ![نمونه کانفیگ](https://github.com/Devtahas/config-generator-/blob/main/assets/config-sample.png.jpg)

---

### 2️⃣ پیدا کردن WORKER_HOST و WS_PATH

1. کانفیگ موردنظر را در کلاینت باز کنید و روی **ویرایش** کلیک کنید
2. دنبال **path** بگردید
3. **WORKER_HOST**: آدرس ورکر (مثال: `test.sajdgsh.workers.dev`)
4. **WS_PATH**: رشته WebSocket path (مثال: `/NEJEJDHDVBDJDJDVHDIDHjdvhdksovQS5PTkxJTkURJKEJEHV0=?ed=2560`)



---

### 3️⃣ جایگذاری در اسکنر

```python
WORKER_HOST = "test.sajdgsh.workers.dev"
WS_PATH = "/NEJEJDHDVBDJDJDVHDIDHjdvhdksovQS5PTkxJTkURJKEJEHV0=?ed=2560"
USER_UUID = "یک-UUID-رندوم-اینجا"
```

---

### 4️⃣ اجرای اسکنر

1. اطمینان از عدم اتصال به VPN
2. اجرای دستور:

```bash
python ultra_global3.py
```

> ![اجرای اسکنر](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(487).png)

3. منتظر بمانید تا اسکن کامل شود و پیام **Done** نمایش داده شود

---

### 5️⃣ پیدا کردن فایل خروجی

1. مسیر: `D:\allconfigs\`
2. فایل‌ها:

```
Configs/            # کانفیگ‌های JSON
scan_log.txt         # گزارش اسکن
Verified_IPs.txt     # IPهای سالم
sub.txt              # سابسکریپشن base64
```

> ![پوشه خروجی](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(488).png)

---

### 6️⃣ آپلود سابسکریپشن در GitHub

1. وارد [GitHub](http://github.com/) شوید
2. ریپو بسازید و `sub.txt` را آپلود کنید
3. روی گزینه **Raw** کلیک کنید تا لینک مستقیم دریافت شود

> ![آپلود در گیت‌هاب](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(489).png)

> ![raw لینک](https://github.com/Devtahas/config-generator-/blob/main/assets/photo_2026-02-20_18-31-16.jpg)
---

### 7️⃣ استفاده در کلاینت‌ها

1. لینک Raw را کپی کنید
2. در کلاینت Karing یا v2rayNG، گزینه **Import Subscription** را بزنید
3. لینک را پیست کنید و Update کنید ✅

> ![نمونه Karing](https://github.com/Devtahas/config-generator-/blob/main/assets/Screenshot%20(490).png)

---

### 8️⃣ نکته مهم

اگر بعد از چند روز سرعت کند شد:

* دوباره اسکنر را اجرا کنید
* فایل جدید `sub.txt` را آپلود کنید و قبلی را حذف کنید
* لینک سابسکریپشن به‌صورت خودکار آپدیت می‌شود

---

## 📱 کلاینت‌های پیشنهادی

| کلاینت           | لینک دانلود                                                         |
| ---------------- | ------------------------------------------------------------------- |
| **Karing**       | [اندروید/ویندوز/لینوکس](https://github.com/KaringX/karing/releases) |
| **v2rayNG**      | [اندروید](https://github.com/2dust/v2rayNG/releases)                |
| **v2rayN**       | [ویندوز](https://github.com/2dust/v2rayN/releases)                  |
| **Hiddify Next** | [اندروید/iOS](https://github.com/hiddify/hiddify-next/releases)     |

---

## ⚡ نکات افزایش سرعت

* افزایش `MAX_WORKERS`
* کاهش `SAMPLES_PER_CIDR`
* کوتاه نگه داشتن لیست DNS

---

## 🔐 نکات امنیتی و مهم

* بهترین عملکرد روی پورت‌های TLS
* کیفیت شبکه و ISP بر نتایج تاثیرگذار است
* این ابزار برای اهداف آموزشی و تحقیقاتی منتشر شده است

---

## ❗ سلب مسئولیت

استفاده نادرست از این ابزار بر عهده کاربر است.

---

## ⭐ حمایت

* ⭐ ستاره دادن به ریپو
* 🐛 ثبت Issue برای باگ‌ها
* 🔧 ارسال Pull Request برای بهبود

--
