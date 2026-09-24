"""
تنظیمات و ثوابت سراسری سامانه مدیریت تعمیرگاه الکترونیک (نسخه Tkinter / ttk)
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
RECEIPTS_DIR = DATA_DIR / "receipts"
EXPORTS_DIR = DATA_DIR / "exports"
DB_FILE = DATA_DIR / "repair_shop.db"

# ایجاد پوشه‌های مورد نیاز
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# وضعیت‌های پرونده تعمیر
STATUSES = [
    "پذیرش شده",
    "در حال عیب‌یابی و بررسی",
    "در انتظار قطعه",
    "در انتظار تایید مشتری",
    "در حال تعمیر",
    "تعمیر شد (آماده تحویل)",
    "غیرقابل تعمیر",
    "تحویل داده شد",
    "کنسل شده",
    "مرجوعی",
]

# روش‌های پرداخت
PAYMENT_METHODS = [
    "کارت‌خوان (POS)",
    "کارت به کارت",
    "نقدی",
    "چک",
    "سایر",
]

# دسته‌بندی هزینه‌ها
EXPENSE_CATEGORIES = [
    "اجاره مغازه/کارگاه",
    "قبوض (برق، آب، گاز، تلفن، اینترنت)",
    "خرید ابزار و تجهیزات کارگاه",
    "حقوق و دستمزد ثابت",
    "ایاب و ذهاب و پیک",
    "پذیرایی و ملزومات مصرفی",
    "تبلیغات و بازاریابی",
    "سایر هزینه‌ها",
]

# انواع حساب مالی
ACCOUNT_TYPES = [
    "کارت/حساب بانکی",
    "صندوق نقد",
    "تنخواه‌گردان",
]
