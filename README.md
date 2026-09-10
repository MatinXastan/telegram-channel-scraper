# 🚀 اسکرپر پیشرفته و حرفه‌ای کانال‌های تلگرام (Telegram Channel Web Scraper)

یک ابزار وب‌اسکرپینگ فوق‌حرفه‌ای و ماژولار با پایتون برای استخراج خودکار و کامل آخرین پست‌های هر کانال تلگرام به همراه تصاویر، ویدیوها، تعداد بازدیدها، ری‌اکشن‌ها و متادیتای کامل کانال.

---

## ✨ ویژگی‌های برجسته پروژه

- 🌐 **پشتیبانی از انواع آدرس‌ها**:
  - لینک وب: `https://t.me/s/channel_name`
  - لینک مستقیم: `https://t.me/channel_name`
  - شناسه با ادساین: `@channel_name`
  - نام کاربری خام: `channel_name`
- ⚙️ **دو موتور استخراج هوشمند (Dual-Engine)**:
  1. **موتور مرورگر واقعی (`browser` با Playwright Chromium)**: باز کردن کامل صفحه در مرورگر، اسکرول خودکار، گذر از بررسی‌های جاوا اسکریپت.
  2. **موتور سریع ناهمگام (`fast` با HTTPX & BeautifulSoup)**: سرعت مافوق صوت با مصرف حداقل رم و پردازنده.
- 📊 **استخراج همه‌جانبه جزئیات هر پست**:
  - شناسه پست (ID) و لینک مستقیم تلگرام
  - متن کامل با پشتیبانی کامل از زبان فارسی، RTL، هشتگ‌ها، منشن‌ها و اموجی‌ها
  - تاریخ و ساعت انتشار (فرمت ISO 8601)
  - تعداد دقیق بازدیدها، واکنش‌ها، فوروارد، رسانه‌ها، نظرسنجی‌ها
  - اطلاعات کامل پروفایل کانال
- 📁 **خروجی در فرمت‌های متنوع**:
  - **Excel (`.xlsx`)**: شیت مجزا برای پست‌ها و شیت اختصاصی برای اطلاعات کانال.
  - **JSON**: ساختاریافته، مرتب و خوانا با یونیکد استاندارد.
  - **CSV (UTF-8 with BOM)**: باز شدن مستقیم بدون به‌هم‌ریختگی فارسی در Excel.
- 📥 **دانلود مستقیم تصاویر و رسانه‌ها**
- 🛡️ **پشتیبانی از پروکسی** (SOCKS5 و HTTP/HTTPS)
- 🎨 **رابط گرافیکی مدرن PySide6 (GUI)** با تم تاریک، جدول تعاملی، نوار پیشرفت زنده
- 🖥️ **رابط کاربری ترمینال شکیل** با Interactive Wizard و Progress Bar

---

## 📋 پیش‌نیازها و نصب

پایتون نسخه **3.10 یا بالاتر** پیشنهاد می‌شود.

### ۱. نصب کتابخانه‌های مورد نیاز

```bash
pip install -r requirements.txt
```

### ۲. نصب مرورگر Playwright (برای حالت موتور مرورگر)

```bash
playwright install chromium
```

---

## 🎮 نحوه اجرا و استفاده

پروژه دارای **۳ روش اجرای متنوع** است:

---

### روش اول: رابط گرافیکی مدرن (GUI Desktop) — 🌟 پیشنهادی

```bash
python gui.py
```

در این محیط می‌توانید:
- آدرس یا نام کاربری کانال را وارد کنید.
- تعداد پست‌ها، نوع موتور، فرمت‌های خروجی و پروکسی را با موس تنظیم کنید.
- پیشرفت کار را به صورت زنده روی نوار پیشرفت مشاهده نمایید.
- پست‌های استخراج‌شده را در **جدول تعاملی** ببینید و با کلیک روی هر پست، متن کامل را بررسی کنید.
- با دکمه‌های مستقیم، فایل اکسل، JSON یا پوشه دانلودها را باز کنید.

---

### روش دوم: حالت تعاملی ترمینال (Terminal Wizard)

```bash
python main.py
```

برنامه به صورت مرحله‌به‌مرحله و با زبان فارسی موارد مورد نیاز را از شما می‌پرسد.

---

### روش سوم: خط فرمان مستقیم (CLI Arguments)

```bash
# مثال ۱: موتور سریع با خروجی Excel و JSON
python main.py -c durov -l 20 -e fast -f json,excel

# مثال ۲: مرورگر واقعی با نمایش زنده
python main.py -c telegram -l 10 -e browser --headed -f all

# مثال ۳: کانال فارسی با دانلود تصاویر
python main.py -c https://t.me/s/varzesh3 -l 15 -e fast -f excel -d

# مثال ۴: استفاده از پروکسی SOCKS5
python main.py -c durov -l 30 -p socks5://127.0.0.1:10808 -f all
```

---

## ⚙️ راهنمای پارامترهای خط فرمان

| پارامتر | نام کامل | توضیح | پیش‌فرض |
| :--- | :--- | :--- | :--- |
| `-c` | `--channel` | آدرس یا شناسه کانال | اجباری |
| `-l` | `--limit` | تعداد پست‌های درخواستی | `20` |
| `-e` | `--engine` | موتور (`browser` یا `fast`) | `browser` |
| `--headed` | — | نمایش پنجره مرورگر | Headless |
| `-f` | `--format` | فرمت خروجی (`json`, `excel`, `csv`, `all`) | `json,excel` |
| `-d` | `--download-media` | دانلود عکس‌ها و تامبنیل‌ها | غیرفعال |
| `-p` | `--proxy` | آدرس پروکسی | بدون پروکسی |
| `-o` | `--output-dir` | مسیر ذخیره‌سازی | `downloads` |

---

## 💻 استفاده به عنوان پکیج پایتون

```python
import asyncio
from telegram_scraper import ScraperConfig, FastTelegramScraper, DataExporter

async def run():
    config = ScraperConfig(channel="durov", limit=10, headless=True)
    scraper = FastTelegramScraper(config)
    result = await scraper.scrape()

    print(f"کانال: {result.channel.title}")
    print(f"تعداد پست‌های استخراج شده: {result.total_scraped}")

    for post in result.posts:
        print(f"[{post.id}] {post.date_formatted} - بازدید: {post.views}")
        print(f"متن: {post.text[:50]}...")

    exporter = DataExporter(result, output_dir="my_exports")
    exporter.export_json()
    exporter.export_excel()

if __name__ == "__main__":
    asyncio.run(run())
```

---

## 📂 ساختار فایل‌های پروژه

```
telegram-channel-scraper/
│
├── telegram_scraper/            # هسته اصلی اسکرپر
│   ├── __init__.py              # پکیج‌بندی و تعریف کلاس‌های عمومی
│   ├── config.py                # پیکربندی پیش‌فرض و تنظیمات
│   ├── models.py                # مدل‌های Pydantic برای پست و کانال
│   ├── parser.py                # پارسر دقیق HTML
│   ├── browser_engine.py        # موتور Playwright
│   ├── fast_engine.py           # موتور سریع HTTPX
│   ├── exporter.py              # صدور Excel, JSON, CSV و مدیا
│   └── utils.py                 # توابع کمکی
│
├── gui.py                       # رابط گرافیکی PySide6
├── main.py                      # فایل اصلی (CLI + Wizard)
├── requirements.txt             # لیست کتابخانه‌ها
└── README.md                    # مستندات پروژه
```

---

## ❓ پرسش‌های متداول

**۱. آیا به اکانت تلگرام یا API نیاز است؟**
> خیر! این اسکرپر مستقیماً از وب‌پیش‌نمایش عمومی تلگرام (`t.me/s`) اطلاعات را می‌خواند.

**۲. در صورت فیلتر بودن تلگرام چه کنیم؟**
> از فلگ `-p` استفاده کنید: `-p socks5://127.0.0.1:10808` یا `-p http://127.0.0.1:10809`

**۳. چرا فارسی در CSV اکسل درست نمایش داده می‌شود؟**
> فایل‌های CSV با استاندارد `utf-8-sig` (UTF-8 BOM) ذخیره می‌شوند.
