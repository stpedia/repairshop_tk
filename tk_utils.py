"""
توابع کمکی تاریخ شمسی، فرمت مالی، مدیریت فایل‌ها و تولید فاکتور/قبض
"""
import os
import sys
import subprocess
from datetime import datetime
from tk_config import RECEIPTS_DIR


def gregorian_to_jalali(gy, gm, gd):
    """تبدیل تاریخ میلادی به شمسی"""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = (365 * gy) + (int((gy2 + 3) / 4)) - (int((gy2 + 99) / 100)) + (int((gy2 + 399) / 400)) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (int(days / 12053))
    days %= 12053
    jy += 4 * (int(days / 1461))
    days %= 1461
    if days > 365:
        jy += int((days - 1) / 365)
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + int(days / 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + int((days - 186) / 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_today() -> str:
    """دریافت تاریخ امروز شمسی"""
    now = datetime.now()
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def iso_to_jalali(iso_str: str) -> str:
    """تبدیل فرمت تاریخ ISO به تاریخ شمسی"""
    if not iso_str:
        return "-"
    try:
        if " " in iso_str:
            iso_str = iso_str.split(" ")[0]
        parts = iso_str.split("-")
        if len(parts) == 3:
            jy, jm, jd = gregorian_to_jalali(int(parts[0]), int(parts[1]), int(parts[2]))
            return f"{jy:04d}/{jm:02d}/{jd:02d}"
        return iso_str
    except Exception:
        return iso_str


def money(val) -> str:
    """فرمت‌دهی مبالغ مالی به صورت ۳ رقم ۳ رقم"""
    try:
        val = float(val)
        return f"{val:,.0f}"
    except (ValueError, TypeError):
        return "۰"


def open_folder(path):
    """باز کردن پوشه سیستم‌عامل"""
    path_str = str(path)
    if not os.path.exists(path_str):
        os.makedirs(path_str, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(path_str)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path_str])
    else:
        subprocess.Popen(["xdg-open", path_str])


def generate_receipt_html(repair: dict, shop_info: dict) -> str:
    """تولید قبض/فاکتور شکیل به صورت فایل HTML قابل چاپ جهت مرورگر یا پرینتر"""
    receipt_no = repair.get("receipt_no", "")
    customer_name = repair.get("customer_name", repair.get("full_name", "-"))
    customer_mobile = repair.get("customer_mobile", repair.get("mobile", "-"))
    device_type = repair.get("device_type", "-")
    brand_model = repair.get("brand_model", "-")
    defect = repair.get("reported_defect", "-")
    final_cost = money(repair.get("final_cost", 0))
    paid = money(repair.get("paid", 0))
    date_str = iso_to_jalali(repair.get("created_at", ""))

    html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <title>قبض پذیرش {receipt_no}</title>
    <style>
        body {{ font-family: 'Tahoma', sans-serif; font-size: 13px; margin: 20px; direction: rtl; line-height: 1.6; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 15px; }}
        .title {{ font-size: 18px; font-weight: bold; margin-bottom: 5px; }}
        .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
        .info-table td {{ padding: 6px; border: 1px solid #ccc; }}
        .info-title {{ font-weight: bold; background-color: #f5f5f5; width: 25%; }}
        .terms {{ font-size: 11px; margin-top: 15px; border-top: 1px dashed #aaa; padding-top: 8px; color: #555; }}
        .footer {{ margin-top: 30px; display: flex; justify-content: space-between; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{shop_info.get('shop_name', 'تعمیرگاه تخصصی الکترونیک')}</div>
        <div>تلفن: {shop_info.get('shop_phone', '-')} | آدرس: {shop_info.get('shop_address', '-')}</div>
    </div>

    <h3 style="text-align: center;">قبض پذیرش و تحویل دستگاه</h3>

    <table class="info-table">
        <tr>
            <td class="info-title">شماره قبض:</td>
            <td>{receipt_no}</td>
            <td class="info-title">تاریخ پذیرش:</td>
            <td>{date_str}</td>
        </tr>
        <tr>
            <td class="info-title">نام مشتری:</td>
            <td>{customer_name}</td>
            <td class="info-title">شماره همراه:</td>
            <td>{customer_mobile}</td>
        </tr>
        <tr>
            <td class="info-title">نوع دستگاه:</td>
            <td>{device_type}</td>
            <td class="info-title">برند و مدل:</td>
            <td>{brand_model}</td>
        </tr>
        <tr>
            <td class="info-title">شرح ایراد:</td>
            <td colspan="3">{defect}</td>
        </tr>
        <tr>
            <td class="info-title">برآورد هزینه:</td>
            <td>{final_cost} تومان</td>
            <td class="info-title">پرداختی پیش‌پرداخت:</td>
            <td>{paid} تومان</td>
        </tr>
    </table>

    <div class="terms">
        <strong>شرایط پذیرش:</strong><br>
        {shop_info.get('terms', 'تحویل دستگاه فقط با ارائه این قبض امکان‌پذیر است.')}
    </div>

    <div class="footer">
        <div>امضاء مشتری</div>
        <div>مهر و امضاء تعمیرگاه</div>
    </div>
</body>
</html>
"""
    file_path = RECEIPTS_DIR / f"{receipt_no}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return str(file_path)
