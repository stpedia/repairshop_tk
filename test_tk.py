"""
تست‌های واحد اختصاصی برای نسخه جدید Tkinter سامانه مدیریت تعمیرگاه (tk_*)
"""
import unittest
import os
import sys
from pathlib import Path

from tk_config import DB_FILE, STATUSES, PAYMENT_METHODS
from tk_database import Database, hash_password, verify_password
from tk_utils import gregorian_to_jalali, jalali_today, money, generate_receipt_html


class TestTkinterApp(unittest.TestCase):
    def setUp(self):
        self.db_filename = "test_repair_shop.db"
        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)
        self.db = Database(self.db_filename)

    def tearDown(self):
        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)

    def test_auth_and_admin(self):
        user = self.db.authenticate_user("admin", "admin")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["role"], "مدیر کل")

        # تست تغییر رمز عبور
        self.db.change_user_password(user["id"], "newpass123")
        self.assertIsNone(self.db.authenticate_user("admin", "admin"))
        updated_user = self.db.authenticate_user("admin", "newpass123")
        self.assertIsNotNone(updated_user)

    def test_daily_receipt_number(self):
        rec1 = self.db.generate_receipt_number("20250101")
        self.assertEqual(rec1, "REC-20250101-001")

        cust_id = self.db.add_customer({
            "full_name": "مشتری تست شماره قبض",
            "mobile": "09120000000"
        })

        self.db.add_repair({
            "receipt_no": rec1,
            "customer_id": cust_id,
            "device_type": "موبایل"
        })

        rec2 = self.db.generate_receipt_number("20250101")
        self.assertEqual(rec2, "REC-20250101-002")

        # تاریخ متفاوت باید از 001 شروع شود
        rec_diff_date = self.db.generate_receipt_number("20250102")
        self.assertEqual(rec_diff_date, "REC-20250102-001")

    def test_customer_repair_and_part_deduction(self):
        cust_id = self.db.add_customer({
            "full_name": "رضا محمدی",
            "mobile": "09121112233",
            "phone": "02188888888",
            "national_code": "0011223344",
            "address": "تهران",
            "notes": "مشتری VIP"
        })
        self.assertIsNotNone(cust_id)

        rep_id = self.db.add_repair({
            "customer_id": cust_id,
            "device_type": "لپ‌تاپ",
            "brand_model": "Asus ROG",
            "reported_defect": "روشن نمی‌شود",
            "service_cost": 500000
        })
        self.assertIsNotNone(rep_id)

        cats = self.db.get_categories()
        p_id = self.db.add_part({
            "category_id": cats[0]["id"],
            "serial": "RAM-16G",
            "name": "رم ۱۶ گیگ DDR4",
            "quantity": 10,
            "min_quantity": 2,
            "buy_price": 1000000,
            "unit_price": 1500000
        })

        # مصرف قطعه در تعمیر
        ok = self.db.add_part_to_repair(rep_id, p_id, 2)
        self.assertTrue(ok)

        # چک کردن کسر از انبار
        part = self.db.get_part(p_id)
        self.assertEqual(part["quantity"], 8)

        # چک کردن هزینه پرونده
        rep = self.db.get_repair(rep_id)
        self.assertEqual(rep["parts_cost"], 3000000)
        self.assertEqual(rep["final_cost"], 3500000)

    def test_payments_expenses_and_accounts(self):
        accounts = self.db.get_accounts()
        acc_id = accounts[0]["id"]

        cust_id = self.db.add_customer({"full_name": "علی حسینی", "mobile": "09123334455"})
        rep_id = self.db.add_repair({"customer_id": cust_id, "device_type": "تبلت", "service_cost": 200000})

        # دریافت وجه
        self.db.add_payment({
            "repair_id": rep_id,
            "customer_id": cust_id,
            "account_id": acc_id,
            "amount": 200000,
            "payment_method": "نقدی"
        })

        # ثبت هزینه
        self.db.add_expense({
            "category": "اجاره مغازه/کارگاه",
            "title": "اجاره ماهانه",
            "account_id": acc_id,
            "amount": 50000
        })

        accs = self.db.get_accounts()
        # موجودی اولیه 0 + 200000 - 50000 = 150000
        self.assertEqual(accs[0]["current_balance"], 150000)

    def test_utils(self):
        self.assertEqual(money(1000000), "1,000,000")
        jy, jm, jd = gregorian_to_jalali(2025, 1, 1)
        self.assertEqual((jy, jm, jd), (1403, 10, 11))

        # html receipt test
        repair = {
            "receipt_no": "REC-TEST-001",
            "customer_name": "تست",
            "customer_mobile": "0912",
            "device_type": "تست",
            "brand_model": "تست",
            "reported_defect": "تست",
            "final_cost": 100000,
            "paid": 50000,
            "created_at": "2025-01-01"
        }
        shop_info = {"shop_name": "تست", "shop_phone": "123", "shop_address": "آدرس"}
        html_path = generate_receipt_html(repair, shop_info)
        self.assertTrue(os.path.exists(html_path))
        if os.path.exists(html_path):
            os.remove(html_path)


if __name__ == "__main__":
    unittest.main()
