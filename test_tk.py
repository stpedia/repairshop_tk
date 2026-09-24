"""
تست‌های واحد اختصاصی برای نسخه جدید Tkinter سامانه مدیریت تعمیرگاه (tk_*)
"""
import unittest
import os
import sys
from pathlib import Path

from tk_config import DB_FILE, STATUSES, PAYMENT_METHODS, CUSTOMER_STATUSES
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

    def test_customer_statuses_and_editing(self):
        cid = self.db.add_customer({
            "full_name": "احمد رضایی",
            "mobile": "09121111111",
            "status": "بد حساب"
        })
        c = self.db.get_customer(cid)
        self.assertEqual(c["status"], "بد حساب")

        self.db.update_customer(cid, {
            "full_name": "احمد رضایی تغییر یافته",
            "mobile": "09121111111",
            "status": "لیست سیاه",
            "national_code": "1234567890",
            "address": "تهران"
        })
        updated_c = self.db.get_customer(cid)
        self.assertEqual(updated_c["full_name"], "احمد رضایی تغییر یافته")
        self.assertEqual(updated_c["status"], "لیست سیاه")

    def test_customer_debtor_creditor_and_history(self):
        cid = self.db.add_customer({"full_name": "مشتری بدهکار", "mobile": "09122222222"})
        rid = self.db.add_repair({"customer_id": cid, "device_type": "موبایل", "service_cost": 500000})

        c = self.db.get_customer(cid)
        self.assertEqual(c["balance"], 500000) # بدهکار 500000

        accs = self.db.get_accounts()
        self.db.add_payment({
            "repair_id": rid,
            "customer_id": cid,
            "account_id": accs[0]["id"],
            "amount": 200000,
            "payment_method": "نقدی"
        })

        c2 = self.db.get_customer(cid)
        self.assertEqual(c2["balance"], 300000) # مانده بدهی 300000

        hist = self.db.get_customer_payments_and_receipts(cid)
        self.assertEqual(len(hist["repairs"]), 1)
        self.assertEqual(len(hist["payments"]), 1)

    def test_subcategories(self):
        parent_id = self.db.add_category("خازن")
        sub_id = self.db.add_category("الکترولیت", parent_id=parent_id)

        cats = self.db.get_categories()
        sub_cat = next((c for c in cats if c["id"] == sub_id), None)
        self.assertIsNotNone(sub_cat)
        self.assertEqual(sub_cat["parent_name"], "خازن")

    def test_backup_and_restore(self):
        backup_file = "test_backup.db"
        if os.path.exists(backup_file):
            os.remove(backup_file)

        self.db.add_customer({"full_name": "تست پشتیبان", "mobile": "09120000000"})
        self.db.backup_database(backup_file)
        self.assertTrue(os.path.exists(backup_file))

        ok = self.db.restore_database(backup_file)
        self.assertTrue(ok)

        custs = self.db.get_customers()
        self.assertTrue(any(c["full_name"] == "تست پشتیبان" for c in custs))

        if os.path.exists(backup_file):
            os.remove(backup_file)


if __name__ == "__main__":
    unittest.main()
