"""
ماژول لایه داده SQLite همراه با پشتیبانی از تراکنش‌ها، هش کلمه عبور و تولید شماره قبض خودکار
"""
import sqlite3
import hashlib
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from tk_config import DB_FILE, BACKUP_DIR
from tk_utils import jalali_today


def hash_password(password: str) -> str:
    """هش کردن رمز عبور با ترکیب الگوریتم SHA-256 و نمک ثابت"""
    salt = "repair_shop_tk_salt_2025"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """بررسی صحت رمز عبور"""
    return hash_password(password) == hashed


class Database:
    def __init__(self, db_path=None):
        self.db_path = str(db_path) if db_path else str(DB_FILE)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        """ایجاد جدول‌ها و داده‌های اولیه در صورت عدم وجود"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. کاربران
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'اپراتور',
                is_active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. تنظیمات
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)

            # 3. مشتریان
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                mobile TEXT NOT NULL,
                phone TEXT,
                national_code TEXT,
                address TEXT,
                status TEXT NOT NULL DEFAULT 'عادی',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # ارتقای ستون status در صورت عدم وجود در دیتابیس قدیمی
            try:
                cursor.execute("ALTER TABLE customers ADD COLUMN status TEXT NOT NULL DEFAULT 'عادی'")
            except sqlite3.OperationalError:
                pass

            # 4. تکنسین‌ها
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS technicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                mobile TEXT,
                specialty TEXT,
                commission_rate REAL DEFAULT 0,
                notes TEXT
            )
            """)

            # 5. همکاران
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS colleagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                mobile TEXT,
                shop_name TEXT,
                address TEXT,
                current_balance REAL DEFAULT 0,
                notes TEXT
            )
            """)

            # 6. دسته‌بندی قطعات انبار
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
            )
            """)

            try:
                cursor.execute("ALTER TABLE categories ADD COLUMN parent_id INTEGER")
            except sqlite3.OperationalError:
                pass

            # 7. قطعات انبار
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                serial TEXT,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                min_quantity INTEGER DEFAULT 2,
                buy_price REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                location TEXT,
                notes TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
            """)

            # 8. پرونده‌های تعمیر
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                technician_id INTEGER,
                device_type TEXT NOT NULL,
                brand_model TEXT,
                serial_number TEXT,
                accessories TEXT,
                reported_defect TEXT,
                technician_report TEXT,
                status TEXT NOT NULL DEFAULT 'پذیرش شده',
                service_cost REAL DEFAULT 0,
                parts_cost REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                final_cost REAL DEFAULT 0,
                paid REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (technician_id) REFERENCES technicians(id) ON DELETE SET NULL
            )
            """)

            # 9. قطعات مصرفی در تعمیر
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS repair_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repair_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY (repair_id) REFERENCES repairs(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE RESTRICT
            )
            """)

            # 10. حساب‌های مالی
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                account_type TEXT NOT NULL,
                bank_name TEXT,
                account_number TEXT,
                current_balance REAL DEFAULT 0
            )
            """)

            # 11. تراکنش‌های مالی و دریافتی‌ها
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repair_id INTEGER,
                customer_id INTEGER,
                account_id INTEGER,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                reference_no TEXT,
                payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (repair_id) REFERENCES repairs(id) ON DELETE SET NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
            )
            """)

            # 12. هزینه‌ها
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                account_id INTEGER,
                amount REAL NOT NULL,
                expense_date TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
            )
            """)

            # 13. چک‌ها
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cheques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL DEFAULT 'دریافتی',
                cheque_number TEXT NOT NULL,
                person_name TEXT NOT NULL,
                bank_name TEXT,
                amount REAL NOT NULL,
                issue_date TEXT,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'در جریان',
                notes TEXT
            )
            """)

            # ایجاد کاربر پیش‌فرض admin / admin
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                    ("admin", hash_password("admin"), "مدیر سیستم", "مدیر کل")
                )

            # تنظیمات پیش‌فرض
            default_settings = [
                ("shop_name", "تعمیرگاه تخصصی الکترونیک"),
                ("shop_phone", "02112345678"),
                ("shop_address", "تهران، خیابان جمهوری"),
                ("terms", "تحویل دستگاه فقط با ارائه قبض امکان‌پذیر است. قطعات تعویضی تا ۴۸ ساعت مهلت تست دارند.")
            ]
            for key, val in default_settings:
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

            cursor.execute("SELECT COUNT(*) FROM accounts")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO accounts (title, account_type, bank_name, account_number, current_balance) VALUES (?, ?, ?, ?, ?)",
                    ("صندوق اصلی", "صندوق نقد", "-", "-", 0)
                )

            cursor.execute("SELECT COUNT(*) FROM categories")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", ("قطعات عمومی", "قطعات و لوازم مصرفی عمومی"))

            conn.commit()

    # --- احراز هویت و کاربران ---
    def authenticate_user(self, username, password) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
            row = cursor.fetchone()
            if row and verify_password(password, row["password_hash"]):
                return dict(row)
            return None

    def change_user_password(self, user_id: int, new_password: str):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                (hash_password(new_password), user_id)
            )

    def get_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT id, username, full_name, role, is_active FROM users").fetchall()]

    def add_user(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                (data["username"], hash_password(data["password"]), data["full_name"], data.get("role", "اپراتور"))
            )
            return cur.lastrowid

    # --- تنظیمات ---
    def get_setting(self, key: str, default: str = "") -> str:
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    # --- تولید شماره قبض روزانه ---
    def generate_receipt_number(self, date_prefix: str = None) -> str:
        if not date_prefix:
            date_prefix = jalali_today().replace("/", "")

        prefix_pattern = f"REC-{date_prefix}-%"
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT receipt_no FROM repairs WHERE receipt_no LIKE ? ORDER BY id DESC LIMIT 1",
                (prefix_pattern,)
            ).fetchone()

            if row and row["receipt_no"]:
                last_num_str = row["receipt_no"].split("-")[-1]
                try:
                    seq = int(last_num_str) + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1

            return f"REC-{date_prefix}-{seq:03d}"

    # --- مشتریان ---
    def add_customer(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO customers (full_name, mobile, phone, national_code, address, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data["full_name"], data["mobile"], data.get("phone", ""), data.get("national_code", ""), data.get("address", ""), data.get("status", "عادی"), data.get("notes", "")))
            return cur.lastrowid

    def update_customer(self, customer_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE customers SET full_name=?, mobile=?, phone=?, national_code=?, address=?, status=?, notes=?
            WHERE id=?
            """, (data["full_name"], data["mobile"], data.get("phone", ""), data.get("national_code", ""), data.get("address", ""), data.get("status", "عادی"), data.get("notes", ""), customer_id))

    def get_customers(self, search: str = "", filter_status: str = "") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            sql = "SELECT * FROM customers WHERE 1=1"
            params = []
            if search:
                s = f"%{search}%"
                sql += " AND (full_name LIKE ? OR mobile LIKE ? OR national_code LIKE ?)"
                params.extend([s, s, s])
            if filter_status:
                sql += " AND status = ?"
                params.append(filter_status)
            sql += " ORDER BY id DESC"
            rows = conn.execute(sql, params).fetchall()

            result = []
            for r in rows:
                d = dict(r)
                # محاسبه مانده بدهی/طلبکاری مشتری
                rep_sums = conn.execute("SELECT COALESCE(SUM(final_cost), 0), COALESCE(SUM(paid), 0) FROM repairs WHERE customer_id = ?", (d["id"],)).fetchone()
                total_cost = rep_sums[0]
                total_paid = rep_sums[1]
                d["total_cost"] = total_cost
                d["total_paid"] = total_paid
                d["balance"] = total_cost - total_paid # مثبت یعنی بدهکار، منفی یعنی طلبکار
                result.append(d)
            return result

    def get_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            rep_sums = conn.execute("SELECT COALESCE(SUM(final_cost), 0), COALESCE(SUM(paid), 0) FROM repairs WHERE customer_id = ?", (d["id"],)).fetchone()
            d["total_cost"] = rep_sums[0]
            d["total_paid"] = rep_sums[1]
            d["balance"] = rep_sums[0] - rep_sums[1]
            return d

    def get_customer_payments_and_receipts(self, customer_id: int) -> Dict[str, Any]:
        """دریافت لیست پرونده‌ها و پرداخت‌های یک مشتری"""
        with self.get_connection() as conn:
            repairs = [dict(r) for r in conn.execute("SELECT * FROM repairs WHERE customer_id = ? ORDER BY id DESC", (customer_id,)).fetchall()]
            payments = [dict(r) for r in conn.execute("SELECT * FROM payments WHERE customer_id = ? ORDER BY id DESC", (customer_id,)).fetchall()]
            return {"repairs": repairs, "payments": payments}

    # --- تکنسین‌ها ---
    def add_technician(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO technicians (full_name, mobile, specialty, commission_rate, notes)
            VALUES (?, ?, ?, ?, ?)
            """, (data["full_name"], data.get("mobile", ""), data.get("specialty", ""), data.get("commission_rate", 0), data.get("notes", "")))
            return cur.lastrowid

    def update_technician(self, tech_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE technicians SET full_name=?, mobile=?, specialty=?, commission_rate=?, notes=?
            WHERE id=?
            """, (data["full_name"], data.get("mobile", ""), data.get("specialty", ""), data.get("commission_rate", 0), data.get("notes", ""), tech_id))

    def get_technicians(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM technicians ORDER BY id DESC").fetchall()]

    # --- همکاران ---
    def add_colleague(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO colleagues (full_name, mobile, shop_name, address, current_balance, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (data["full_name"], data.get("mobile", ""), data.get("shop_name", ""), data.get("address", ""), data.get("current_balance", 0), data.get("notes", "")))
            return cur.lastrowid

    def update_colleague(self, colleague_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE colleagues SET full_name=?, mobile=?, shop_name=?, address=?, current_balance=?, notes=?
            WHERE id=?
            """, (data["full_name"], data.get("mobile", ""), data.get("shop_name", ""), data.get("address", ""), data.get("current_balance", 0), data.get("notes", ""), colleague_id))

    def get_colleagues(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM colleagues ORDER BY id DESC").fetchall()]

    # --- انبار و دسته‌بندی با زیردسته ---
    def get_categories(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
            SELECT c.*, p.name as parent_name
            FROM categories c
            LEFT JOIN categories p ON c.parent_id = p.id
            ORDER BY c.id ASC
            """).fetchall()
            return [dict(r) for r in rows]

    def add_category(self, name: str, parent_id: Optional[int] = None, description: str = "") -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO categories (name, parent_id, description) VALUES (?, ?, ?)", (name, parent_id, description))
            return cur.lastrowid

    def update_category(self, cat_id: int, name: str, parent_id: Optional[int] = None, description: str = ""):
        with self.get_connection() as conn:
            conn.execute("UPDATE categories SET name=?, parent_id=?, description=? WHERE id=?", (name, parent_id, description, cat_id))

    def add_part(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO parts (category_id, serial, name, quantity, min_quantity, buy_price, unit_price, location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data.get("category_id"), data.get("serial", ""), data["name"], data.get("quantity", 0), data.get("min_quantity", 2), data.get("buy_price", 0), data.get("unit_price", 0), data.get("location", ""), data.get("notes", "")))
            return cur.lastrowid

    def update_part(self, part_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE parts SET category_id=?, serial=?, name=?, quantity=?, min_quantity=?, buy_price=?, unit_price=?, location=?, notes=?
            WHERE id=?
            """, (data.get("category_id"), data.get("serial", ""), data["name"], data.get("quantity", 0), data.get("min_quantity", 2), data.get("buy_price", 0), data.get("unit_price", 0), data.get("location", ""), data.get("notes", ""), part_id))

    def get_parts(self, search: str = "") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if search:
                s = f"%{search}%"
                rows = conn.execute("""
                SELECT p.*, c.name as category_name
                FROM parts p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.name LIKE ? OR p.serial LIKE ?
                ORDER BY p.id DESC
                """, (s, s)).fetchall()
            else:
                rows = conn.execute("""
                SELECT p.*, c.name as category_name
                FROM parts p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.id DESC
                """).fetchall()
            return [dict(r) for r in rows]

    def get_part(self, part_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()
            return dict(row) if row else None

    def get_low_stock_parts(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM parts WHERE quantity <= min_quantity ORDER BY quantity ASC").fetchall()
            return [dict(r) for r in rows]

    # --- پرونده‌های تعمیر و فاکتورها همراه تاریخ دلخواه ---
    def add_repair(self, data: dict) -> int:
        receipt_no = data.get("receipt_no") or self.generate_receipt_number()
        service_cost = float(data.get("service_cost", 0))
        parts_cost = float(data.get("parts_cost", 0))
        discount = float(data.get("discount", 0))
        tax = float(data.get("tax", 0))
        final_cost = max(0.0, (service_cost + parts_cost + tax) - discount)
        created_at = data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO repairs (
                receipt_no, customer_id, technician_id, device_type, brand_model,
                serial_number, accessories, reported_defect, technician_report,
                status, service_cost, parts_cost, discount, tax, final_cost, paid, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                receipt_no, data["customer_id"], data.get("technician_id"),
                data["device_type"], data.get("brand_model", ""),
                data.get("serial_number", ""), data.get("accessories", ""),
                data.get("reported_defect", ""), data.get("technician_report", ""),
                data.get("status", "پذیرش شده"), service_cost, parts_cost,
                discount, tax, final_cost, data.get("paid", 0), created_at
            ))
            return cur.lastrowid

    def update_repair(self, repair_id: int, data: dict):
        service_cost = float(data.get("service_cost", 0))
        parts_cost = float(data.get("parts_cost", 0))
        discount = float(data.get("discount", 0))
        tax = float(data.get("tax", 0))
        final_cost = max(0.0, (service_cost + parts_cost + tax) - discount)

        with self.get_connection() as conn:
            if "created_at" in data and data["created_at"]:
                conn.execute("""
                UPDATE repairs SET
                    customer_id=?, technician_id=?, device_type=?, brand_model=?,
                    serial_number=?, accessories=?, reported_defect=?, technician_report=?,
                    status=?, service_cost=?, parts_cost=?, discount=?, tax=?, final_cost=?,
                    created_at=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """, (
                    data["customer_id"], data.get("technician_id"),
                    data["device_type"], data.get("brand_model", ""),
                    data.get("serial_number", ""), data.get("accessories", ""),
                    data.get("reported_defect", ""), data.get("technician_report", ""),
                    data.get("status", "پذیرش شده"), service_cost, parts_cost,
                    discount, tax, final_cost, data["created_at"], repair_id
                ))
            else:
                conn.execute("""
                UPDATE repairs SET
                    customer_id=?, technician_id=?, device_type=?, brand_model=?,
                    serial_number=?, accessories=?, reported_defect=?, technician_report=?,
                    status=?, service_cost=?, parts_cost=?, discount=?, tax=?, final_cost=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """, (
                    data["customer_id"], data.get("technician_id"),
                    data["device_type"], data.get("brand_model", ""),
                    data.get("serial_number", ""), data.get("accessories", ""),
                    data.get("reported_defect", ""), data.get("technician_report", ""),
                    data.get("status", "پذیرش شده"), service_cost, parts_cost,
                    discount, tax, final_cost, repair_id
                ))

    def get_repairs(self, search: str = "", status: str = "") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            sql = """
            SELECT r.*, c.full_name, c.mobile, t.full_name as technician_name
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
            LEFT JOIN technicians t ON r.technician_id = t.id
            WHERE 1=1
            """
            params = []
            if search:
                s = f"%{search}%"
                sql += " AND (r.receipt_no LIKE ? OR c.full_name LIKE ? OR c.mobile LIKE ? OR r.device_type LIKE ? OR r.brand_model LIKE ?)"
                params.extend([s, s, s, s, s])
            if status:
                sql += " AND r.status = ?"
                params.append(status)

            sql += " ORDER BY r.id DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_repair(self, repair_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            sql = """
            SELECT r.*, c.full_name as customer_name, c.mobile as customer_mobile, c.address as customer_address, t.full_name as technician_name
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
            LEFT JOIN technicians t ON r.technician_id = t.id
            WHERE r.id = ?
            """
            row = conn.execute(sql, (repair_id,)).fetchone()
            return dict(row) if row else None

    # --- قطعات مصرفی تعمیر با کسر خودکار از انبار ---
    def add_part_to_repair(self, repair_id: int, part_id: int, qty: int = 1) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            part = cursor.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()
            if not part or part["quantity"] < qty:
                return False

            unit_price = part["unit_price"]
            total_price = unit_price * qty

            cursor.execute("""
            INSERT INTO repair_parts (repair_id, part_id, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
            """, (repair_id, part_id, qty, unit_price, total_price))

            cursor.execute("UPDATE parts SET quantity = quantity - ? WHERE id = ?", (qty, part_id))

            cursor.execute("""
            UPDATE repairs SET parts_cost = (
                SELECT COALESCE(SUM(total_price), 0) FROM repair_parts WHERE repair_id = ?
            ) WHERE id = ?
            """, (repair_id, repair_id))

            rep = cursor.execute("SELECT * FROM repairs WHERE id = ?", (repair_id,)).fetchone()
            service_cost = rep["service_cost"]
            parts_cost = rep["parts_cost"]
            discount = rep["discount"]
            tax = rep["tax"]
            final_cost = max(0.0, (service_cost + parts_cost + tax) - discount)
            cursor.execute("UPDATE repairs SET final_cost = ? WHERE id = ?", (final_cost, repair_id))

            conn.commit()
            return True

    def get_repair_parts(self, repair_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
            SELECT rp.*, p.name as part_name, p.serial as part_serial
            FROM repair_parts rp
            JOIN parts p ON rp.part_id = p.id
            WHERE rp.repair_id = ?
            """, (repair_id,)).fetchall()
            return [dict(r) for r in rows]

    # --- حساب‌های مالی و تراکنش‌ها همراه تاریخ دلخواه ---
    def get_accounts(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM accounts ORDER BY id ASC").fetchall()]

    def add_account(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO accounts (title, account_type, bank_name, account_number, current_balance)
            VALUES (?, ?, ?, ?, ?)
            """, (data["title"], data["account_type"], data.get("bank_name", ""), data.get("account_number", ""), data.get("current_balance", 0)))
            return cur.lastrowid

    def update_account(self, account_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE accounts SET title=?, account_type=?, bank_name=?, account_number=?, current_balance=?
            WHERE id=?
            """, (data["title"], data["account_type"], data.get("bank_name", ""), data.get("account_number", ""), data.get("current_balance", 0), account_id))

    def transfer_funds(self, from_account_id: int, to_account_id: int, amount: float, notes: str = "") -> bool:
        if from_account_id == to_account_id or amount <= 0:
            return False
        with self.get_connection() as conn:
            cur = conn.cursor()
            from_acc = cur.execute("SELECT current_balance FROM accounts WHERE id = ?", (from_account_id,)).fetchone()
            if not from_acc or from_acc["current_balance"] < amount:
                return False

            cur.execute("UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?", (amount, from_account_id))
            cur.execute("UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?", (amount, to_account_id))

            cur.execute("""
            INSERT INTO expenses (category, title, account_id, amount, notes)
            VALUES ('انتقال وجه', ?, ?, ?, ?)
            """, (f"انتقال به حساب {to_account_id}", from_account_id, amount, notes))

            cur.execute("""
            INSERT INTO payments (account_id, amount, payment_method, notes)
            VALUES (?, ?, 'انتقال داخلی', ?)
            """, (to_account_id, amount, f"دریافت از حساب {from_account_id} - {notes}"))

            conn.commit()
            return True

    def add_payment(self, data: dict) -> int:
        payment_date = data.get("payment_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cur = conn.cursor()
            amount = float(data["amount"])
            account_id = data.get("account_id")

            cur.execute("""
            INSERT INTO payments (repair_id, customer_id, account_id, amount, payment_method, reference_no, payment_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data.get("repair_id"), data.get("customer_id"), account_id, amount, data["payment_method"], data.get("reference_no", ""), payment_date, data.get("notes", "")))
            pay_id = cur.lastrowid

            if account_id:
                cur.execute("UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?", (amount, account_id))

            if data.get("repair_id"):
                cur.execute("""
                UPDATE repairs SET paid = paid + ? WHERE id = ?
                """, (amount, data["repair_id"]))

            conn.commit()
            return pay_id

    # --- هزینه‌ها همراه تاریخ دلخواه و ویرایش ---
    def add_expense(self, data: dict) -> int:
        expense_date = data.get("expense_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cur = conn.cursor()
            amount = float(data["amount"])
            account_id = data.get("account_id")

            cur.execute("""
            INSERT INTO expenses (category, title, account_id, amount, expense_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (data["category"], data["title"], account_id, amount, expense_date, data.get("notes", "")))
            exp_id = cur.lastrowid

            if account_id:
                cur.execute("UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?", (amount, account_id))

            conn.commit()
            return exp_id

    def update_expense(self, expense_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE expenses SET category=?, title=?, amount=?, expense_date=?, notes=?
            WHERE id=?
            """, (data["category"], data["title"], float(data["amount"]), data.get("expense_date"), data.get("notes", ""), expense_id))

    def get_expenses(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM expenses ORDER BY id DESC").fetchall()]

    # --- چک‌ها همراه ویرایش ---
    def add_cheque(self, data: dict) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO cheques (type, cheque_number, person_name, bank_name, amount, issue_date, due_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data.get("type", "دریافتی"), data["cheque_number"], data["person_name"], data.get("bank_name", ""), float(data["amount"]), data.get("issue_date", ""), data["due_date"], data.get("status", "در جریان"), data.get("notes", "")))
            return cur.lastrowid

    def update_cheque(self, cheque_id: int, data: dict):
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE cheques SET type=?, cheque_number=?, person_name=?, bank_name=?, amount=?, issue_date=?, due_date=?, status=?, notes=?
            WHERE id=?
            """, (data.get("type", "دریافتی"), data["cheque_number"], data["person_name"], data.get("bank_name", ""), float(data["amount"]), data.get("issue_date", ""), data["due_date"], data.get("status", "در جریان"), data.get("notes", ""), cheque_id))

    def get_overdue_cheques(self) -> List[Dict[str, Any]]:
        today = jalali_today()
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM cheques WHERE due_date <= ? AND status = 'در جریان'", (today,)).fetchall()
            return [dict(r) for r in rows]

    def get_upcoming_cheques(self) -> List[Dict[str, Any]]:
        today = jalali_today()
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM cheques WHERE due_date > ? AND status = 'در جریان' ORDER BY due_date ASC LIMIT 5", (today,)).fetchall()
            return [dict(r) for r in rows]

    # --- اطلاعات آمار داشبورد ---
    def dashboard_info(self) -> tuple:
        with self.get_connection() as conn:
            active_repairs = conn.execute("SELECT COUNT(*) FROM repairs WHERE status NOT IN ('تحویل داده شد', 'کنسل شده', 'مرجوعی')").fetchone()[0]
            ready_repairs = conn.execute("SELECT COUNT(*) FROM repairs WHERE status = 'تعمیر شد (آماده تحویل)'").fetchone()[0]
            total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_income = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE DATE(payment_date) = ?", (today_str,)).fetchone()[0]
            return active_repairs, ready_repairs, total_customers, today_income

    # --- پشتیبان‌گیری و بازیابی دیتابیس ---
    def backup_database(self, dest_path: str = None) -> str:
        if not dest_path:
            filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            dest_path = str(BACKUP_DIR / filename)
        shutil.copy2(self.db_path, dest_path)
        return dest_path

    def restore_database(self, source_path: str) -> bool:
        if not os.path.exists(source_path):
            return False
        shutil.copy2(source_path, self.db_path)
        self.init_db()
        return True
