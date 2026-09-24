"""
سامانه جامع مدیریت تعمیرگاه الکترونیک (نسخه کامل و ماژولار Tkinter / ttk)
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import webbrowser
from pathlib import Path

from tk_config import STATUSES, EXPENSE_CATEGORIES, PAYMENT_METHODS, ACCOUNT_TYPES, DATA_DIR, BACKUP_DIR, RECEIPTS_DIR
from tk_database import Database, hash_password, verify_password
from tk_utils import jalali_today, iso_to_jalali, money, open_folder, generate_receipt_html


class LoginDialogTk(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.authenticated_user = None

        self.title("🔐 ورود به سامانه مدیریت تعمیرگاه")
        self.geometry("380x280")
        self.resizable(False, False)

        # Do NOT call transient(parent) while parent is withdrawn!
        # Doing so makes the Toplevel hidden or invisible on Windows / Thonny / X11.
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.setup_ui()

        self.lift()
        self.focus_force()

        self.after(100, self.safe_grab)

    def safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    def on_close(self):
        self.authenticated_user = None
        self.destroy()

    def setup_ui(self):
        pad = {'padx': 15, 'pady': 8}

        lbl_title = ttk.Label(self, text="ورود به حساب کاربری", font=("Tahoma", 14, "bold"))
        lbl_title.pack(pady=15)

        frm_user = ttk.Frame(self)
        frm_user.pack(fill="x", **pad)
        ttk.Label(frm_user, text="نام کاربری:", font=("Tahoma", 10)).pack(side="right", padx=5)
        self.ent_user = ttk.Entry(frm_user, justify="right", font=("Tahoma", 10))
        self.ent_user.pack(side="right", fill="x", expand=True)

        frm_pass = ttk.Frame(self)
        frm_pass.pack(fill="x", **pad)
        ttk.Label(frm_pass, text="رمز عبور:", font=("Tahoma", 10)).pack(side="right", padx=5)
        self.ent_pass = ttk.Entry(frm_pass, show="*", justify="right", font=("Tahoma", 10))
        self.ent_pass.pack(side="right", fill="x", expand=True)
        self.ent_pass.bind("<Return>", lambda e: self.login())

        btn_login = ttk.Button(self, text="🔑 ورود به سیستم", command=self.login)
        btn_login.pack(pady=15)

    def login(self):
        u = self.ent_user.get().strip()
        p = self.ent_pass.get()

        if not u or not p:
            messagebox.showwarning("خطا", "لطفاً نام کاربری و رمز عبور را وارد نمایید.", parent=self)
            return

        user = self.db.authenticate_user(u, p)
        if user:
            self.authenticated_user = user
            self.destroy()
        else:
            messagebox.showerror("خطای ورود", "نام کاربری یا رمز عبور اشتباه است یا حساب غیرفعال می‌باشد.", parent=self)


class ChangePasswordDialogTk(tk.Toplevel):
    def __init__(self, parent, db, user_id, force=False):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.force = force

        self.title("⚠️ تغییر اجباری رمز عبور" if force else "🔑 تغییر رمز عبور")
        self.geometry("380x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        pad = {'padx': 15, 'pady': 8}

        if self.force:
            ttk.Label(self, text="جهت ارتقای امنیت باید رمز عبور خود را تغییر دهید.", foreground="red", font=("Tahoma", 10, "bold")).pack(pady=10)

        frm1 = ttk.Frame(self)
        frm1.pack(fill="x", **pad)
        ttk.Label(frm1, text="رمز جدید:", font=("Tahoma", 10)).pack(side="right", padx=5)
        self.ent_pw1 = ttk.Entry(frm1, show="*", justify="right", font=("Tahoma", 10))
        self.ent_pw1.pack(side="right", fill="x", expand=True)

        frm2 = ttk.Frame(self)
        frm2.pack(fill="x", **pad)
        ttk.Label(frm2, text="تکرار رمز جدید:", font=("Tahoma", 10)).pack(side="right", padx=5)
        self.ent_pw2 = ttk.Entry(frm2, show="*", justify="right", font=("Tahoma", 10))
        self.ent_pw2.pack(side="right", fill="x", expand=True)

        btn = ttk.Button(self, text="💾 ذخیره رمز جدید", command=self.save)
        btn.pack(pady=15)

    def save(self):
        p1 = self.ent_pw1.get()
        p2 = self.ent_pw2.get()

        if len(p1) < 4:
            messagebox.showwarning("خطا", "رمز عبور جدید باید حداقل ۴ کاراکتر باشد.", parent=self)
            return

        if p1 != p2:
            messagebox.showwarning("خطا", "تکرار رمز عبور مطابقت ندارد.", parent=self)
            return

        self.db.change_user_password(self.user_id, p1)
        messagebox.showinfo("موفق", "رمز عبور با موفقیت تغییر یافت.", parent=self)
        self.destroy()


class MainAppTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_user = None

        self.title("سامانه مدیریت تعمیرگاه الکترونیک (نسخه Tkinter / ttk)")
        self.geometry("1150x720")

        # اجرای دیالوگ لاگین
        self.withdraw()
        login_dlg = LoginDialogTk(self, self.db)
        self.wait_window(login_dlg)

        if not login_dlg.authenticated_user:
            self.destroy()
            return

        self.current_user = login_dlg.authenticated_user
        self.deiconify()

        # بررسی تغییر اجباری رمز عبور
        if self.current_user.get("must_change_password") == 1:
            cp_dlg = ChangePasswordDialogTk(self, self.db, self.current_user["id"], force=True)
            self.wait_window(cp_dlg)

        shop_title = self.db.get_setting("shop_name", "تعمیرگاه تخصصی الکترونیک")
        self.title(f"مدیریت تعمیرگاه - {shop_title} | کاربر: {self.current_user['full_name']} ({self.current_user['role']})")

        self.setup_ui()
        self.refresh_all()

    def setup_ui(self):
        # نوار بالای صفحه
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", padx=10, pady=5)

        lbl_user = ttk.Label(top_bar, text=f"👤 {self.current_user['full_name']} [{self.current_user['role']}]", font=("Tahoma", 10, "bold"))
        lbl_user.pack(side="right", padx=10)

        btn_ch_pw = ttk.Button(top_bar, text="🔑 تغییر رمز عبور", command=self.change_password)
        btn_ch_pw.pack(side="left", padx=5)

        btn_backup = ttk.Button(top_bar, text="💾 پشتیبان‌گیری", command=self.backup)
        btn_backup.pack(side="left", padx=5)

        btn_folder = ttk.Button(top_bar, text="📁 پوشه داده‌ها", command=lambda: open_folder(DATA_DIR))
        btn_folder.pack(side="left", padx=5)

        # تب‌های ناوبری اصلی
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_dash = ttk.Frame(self.notebook)
        self.tab_repairs = ttk.Frame(self.notebook)
        self.tab_inventory = ttk.Frame(self.notebook)
        self.tab_accounts = ttk.Frame(self.notebook)
        self.tab_colleagues = ttk.Frame(self.notebook)
        self.tab_techs = ttk.Frame(self.notebook)
        self.tab_custs = ttk.Frame(self.notebook)
        self.tab_accounting = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dash, text="📊 داشبورد و آمار")
        self.notebook.add(self.tab_repairs, text="🛠️ پرونده‌های تعمیر")
        self.notebook.add(self.tab_inventory, text="📦 انبار و فروش")
        self.notebook.add(self.tab_accounts, text="💳 حساب‌های مالی")
        self.notebook.add(self.tab_colleagues, text="🤝 همکاران")
        self.notebook.add(self.tab_techs, text="👨‍🔧 تکنسین‌ها")
        self.notebook.add(self.tab_custs, text="👥 مشتریان")
        self.notebook.add(self.tab_accounting, text="💰 حسابداری و هزینه‌ها")

        # ایجاد محتوای تب‌ها
        self.setup_dash_tab()
        self.setup_repairs_tab()
        self.setup_inventory_tab()
        self.setup_accounts_tab()
        self.setup_colleagues_tab()
        self.setup_techs_tab()
        self.setup_custs_tab()
        self.setup_accounting_tab()

    def change_password(self):
        ChangePasswordDialogTk(self, self.db, self.current_user["id"])

    def backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite Files", "*.db")])
        if path:
            self.db.backup_database(path)
            messagebox.showinfo("موفق", "نسخه پشتیبان با موفقیت تهیه شد.")

    # --- 1. داشبورد ---
    def setup_dash_tab(self):
        cards_frame = ttk.Frame(self.tab_dash)
        cards_frame.pack(fill="x", padx=10, pady=10)

        self.lbl_active = ttk.Label(cards_frame, text="تعمیرات جاری: ۰", font=("Tahoma", 11, "bold"), relief="groove", padding=10)
        self.lbl_active.pack(side="right", fill="x", expand=True, padx=5)

        self.lbl_ready = ttk.Label(cards_frame, text="آماده تحویل: ۰", font=("Tahoma", 11, "bold"), relief="groove", padding=10)
        self.lbl_ready.pack(side="right", fill="x", expand=True, padx=5)

        self.lbl_custs = ttk.Label(cards_frame, text="کل مشتریان: ۰", font=("Tahoma", 11, "bold"), relief="groove", padding=10)
        self.lbl_custs.pack(side="right", fill="x", expand=True, padx=5)

        self.lbl_income = ttk.Label(cards_frame, text="درآمد امروز: ۰", font=("Tahoma", 11, "bold"), relief="groove", padding=10)
        self.lbl_income.pack(side="right", fill="x", expand=True, padx=5)

        # جدول چک‌ها
        ttk.Label(self.tab_dash, text="🔔 هشدار چک‌ها و تعهدات سررسیدشده:", font=("Tahoma", 10, "bold"), foreground="red").pack(anchor="e", padx=10, pady=5)
        self.tree_dash_cheques = ttk.Treeview(self.tab_dash, columns=("type", "num", "person", "amount", "due"), show="headings", height=4)
        for col, h in [("type", "نوع"), ("num", "شماره چک"), ("person", "طرف حساب"), ("amount", "مبلغ (تومان)"), ("due", "سررسید")]:
            self.tree_dash_cheques.heading(col, text=h)
        self.tree_dash_cheques.pack(fill="x", padx=10, pady=5)

        # جدول کسری انبار
        ttk.Label(self.tab_dash, text="⚠️ قطعات دارای کسری موجودی در انبار:", font=("Tahoma", 10, "bold")).pack(anchor="e", padx=10, pady=5)
        self.tree_low_stock = ttk.Treeview(self.tab_dash, columns=("serial", "name", "qty", "min_qty"), show="headings", height=4)
        for col, h in [("serial", "کد/سریال"), ("name", "نام قطعه"), ("qty", "موجودی"), ("min_qty", "حداقل مجاز")]:
            self.tree_low_stock.heading(col, text=h)
        self.tree_low_stock.pack(fill="x", padx=10, pady=5)

    def refresh_dashboard(self):
        active, ready, custs, today_money = self.db.dashboard_info()
        self.lbl_active.config(text=f"تعمیرات جاری: {active}")
        self.lbl_ready.config(text=f"آماده تحویل: {ready}")
        self.lbl_custs.config(text=f"کل مشتریان: {custs}")
        self.lbl_income.config(text=f"درآمد امروز: {money(today_money)} تومان")

        for row in self.tree_dash_cheques.get_children():
            self.tree_dash_cheques.delete(row)
        for ch in self.db.get_overdue_cheques() + self.db.get_upcoming_cheques():
            self.tree_dash_cheques.insert("", "end", values=(ch.get("type"), ch.get("cheque_number"), ch.get("person_name"), money(ch.get("amount")), ch.get("due_date")))

        for row in self.tree_low_stock.get_children():
            self.tree_low_stock.delete(row)
        for p in self.db.get_low_stock_parts():
            self.tree_low_stock.insert("", "end", values=(p.get("serial"), p.get("name"), p.get("quantity"), p.get("min_quantity")))

    # --- 2. تعمیرات ---
    def setup_repairs_tab(self):
        top_bar = ttk.Frame(self.tab_repairs)
        top_bar.pack(fill="x", padx=10, pady=5)

        ttk.Label(top_bar, text="جستجو:").pack(side="right", padx=5)
        self.ent_rep_search = ttk.Entry(top_bar, justify="right")
        self.ent_rep_search.pack(side="right", padx=5)
        self.ent_rep_search.bind("<KeyRelease>", lambda e: self.refresh_repairs())

        btn_new_rep = ttk.Button(top_bar, text="➕ پذیرش جدید", command=self.new_repair)
        btn_new_rep.pack(side="left", padx=5)

        btn_edit_rep = ttk.Button(top_bar, text="✏️ ویرایش/تغییر وضعیت", command=self.edit_repair)
        btn_edit_rep.pack(side="left", padx=5)

        btn_part_rep = ttk.Button(top_bar, text="⚙️ ثبت قطعه مصرفی", command=self.add_repair_part_dlg)
        btn_part_rep.pack(side="left", padx=5)

        btn_pay_rep = ttk.Button(top_bar, text="💳 ثبت دریافتی", command=self.add_repair_payment_dlg)
        btn_pay_rep.pack(side="left", padx=5)

        btn_print = ttk.Button(top_bar, text="🖨️ چاپ قبض", command=self.print_receipt)
        btn_print.pack(side="left", padx=5)

        self.tree_repairs = ttk.Treeview(self.tab_repairs, columns=("id", "receipt", "cust", "device", "tech", "status", "cost", "paid", "date"), show="headings")
        for col, h in [("id", "شناسه"), ("receipt", "قبض"), ("cust", "مشتری"), ("device", "دستگاه/مدل"), ("tech", "تکنسین"), ("status", "وضعیت"), ("cost", "هزینه کل"), ("paid", "پرداختی"), ("date", "تاریخ")]:
            self.tree_repairs.heading(col, text=h)
        self.tree_repairs.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh_repairs(self):
        for row in self.tree_repairs.get_children():
            self.tree_repairs.delete(row)
        q = self.ent_rep_search.get().strip()
        for r in self.db.get_repairs(search=q):
            self.tree_repairs.insert("", "end", values=(r["id"], r.get("receipt_no"), r.get("full_name"), f"{r.get('device_type')} {r.get('brand_model')}", r.get("technician_name") or "-", r.get("status"), money(r.get("final_cost")), money(r.get("paid")), iso_to_jalali(r.get("created_at"))))

    def get_selected_repair_id(self):
        selected = self.tree_repairs.selection()
        if not selected:
            messagebox.showwarning("هشدار", "لطفاً یک پرونده تعمیر را از جدول انتخاب کنید.")
            return None
        return int(self.tree_repairs.item(selected[0])["values"][0])

    def new_repair(self):
        dlg = tk.Toplevel(self)
        dlg.title("پذیرش دستگاه جدید")
        dlg.geometry("450x480")
        dlg.grab_set()

        ttk.Label(dlg, text="انتخاب مشتری:").pack(pady=2)
        cmb_cust = ttk.Combobox(dlg, justify="right")
        custs = self.db.get_customers()
        cmb_cust['values'] = [f"{c['id']}: {c['full_name']} ({c['mobile']})" for c in custs]
        if custs:
            cmb_cust.current(0)
        cmb_cust.pack(fill="x", padx=15)

        ttk.Label(dlg, text="نوع دستگاه (مثلا آیفون/لپ‌تاپ):").pack(pady=2)
        ent_dev = ttk.Entry(dlg, justify="right")
        ent_dev.pack(fill="x", padx=15)

        ttk.Label(dlg, text="برند و مدل:").pack(pady=2)
        ent_model = ttk.Entry(dlg, justify="right")
        ent_model.pack(fill="x", padx=15)

        ttk.Label(dlg, text="شرح ایراد:").pack(pady=2)
        ent_defect = ttk.Entry(dlg, justify="right")
        ent_defect.pack(fill="x", padx=15)

        ttk.Label(dlg, text="برآورد هزینه اجرت (تومان):").pack(pady=2)
        ent_cost = ttk.Entry(dlg, justify="right")
        ent_cost.insert(0, "0")
        ent_cost.pack(fill="x", padx=15)

        def save():
            if not cmb_cust.get() or not ent_dev.get().strip():
                messagebox.showwarning("خطا", "مشتری و نوع دستگاه الزامی است.", parent=dlg)
                return
            c_id = int(cmb_cust.get().split(":")[0])
            rec_no = self.db.generate_receipt_number()
            self.db.add_repair({
                "receipt_no": rec_no,
                "customer_id": c_id,
                "device_type": ent_dev.get().strip(),
                "brand_model": ent_model.get().strip(),
                "reported_defect": ent_defect.get().strip(),
                "service_cost": float(ent_cost.get() or 0)
            })
            messagebox.showinfo("موفق", f"پرونده پذیرش با شماره قبض {rec_no} ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_all()

        ttk.Button(dlg, text="💾 ثبت پذیرش", command=save).pack(pady=15)

    def edit_repair(self):
        rep_id = self.get_selected_repair_id()
        if not rep_id:
            return
        rep = self.db.get_repair(rep_id)
        if not rep:
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"ویرایش پرونده {rep['receipt_no']}")
        dlg.geometry("450x500")
        dlg.grab_set()

        ttk.Label(dlg, text="وضعیت پرونده:").pack(pady=2)
        cmb_status = ttk.Combobox(dlg, values=STATUSES, justify="right")
        cmb_status.set(rep["status"])
        cmb_status.pack(fill="x", padx=15)

        ttk.Label(dlg, text="تکنسین مربوطه:").pack(pady=2)
        cmb_tech = ttk.Combobox(dlg, justify="right")
        techs = self.db.get_technicians()
        cmb_tech['values'] = ["0: عدم تخصیص"] + [f"{t['id']}: {t['full_name']}" for t in techs]
        if rep.get("technician_id"):
            for idx, t in enumerate(techs):
                if t["id"] == rep["technician_id"]:
                    cmb_tech.current(idx + 1)
                    break
        else:
            cmb_tech.current(0)
        cmb_tech.pack(fill="x", padx=15)

        ttk.Label(dlg, text="گزارش فنی / اقدامات انجام شده:").pack(pady=2)
        ent_report = ttk.Entry(dlg, justify="right")
        ent_report.insert(0, rep.get("technician_report") or "")
        ent_report.pack(fill="x", padx=15)

        ttk.Label(dlg, text="هزینه اجرت خدمات (تومان):").pack(pady=2)
        ent_cost = ttk.Entry(dlg, justify="right")
        ent_cost.insert(0, str(int(rep.get("service_cost", 0))))
        ent_cost.pack(fill="x", padx=15)

        ttk.Label(dlg, text="تخفیف (تومان):").pack(pady=2)
        ent_disc = ttk.Entry(dlg, justify="right")
        ent_disc.insert(0, str(int(rep.get("discount", 0))))
        ent_disc.pack(fill="x", padx=15)

        def save():
            tech_val = cmb_tech.get().split(":")[0] if cmb_tech.get() else "0"
            tech_id = int(tech_val) if int(tech_val) > 0 else None

            data = {
                "customer_id": rep["customer_id"],
                "technician_id": tech_id,
                "device_type": rep["device_type"],
                "brand_model": rep["brand_model"],
                "serial_number": rep.get("serial_number", ""),
                "accessories": rep.get("accessories", ""),
                "reported_defect": rep.get("reported_defect", ""),
                "technician_report": ent_report.get().strip(),
                "status": cmb_status.get(),
                "service_cost": float(ent_cost.get() or 0),
                "parts_cost": rep["parts_cost"],
                "discount": float(ent_disc.get() or 0),
                "tax": rep.get("tax", 0)
            }
            self.db.update_repair(rep_id, data)
            messagebox.showinfo("موفق", "تغییرات پرونده ذخیره شد.", parent=dlg)
            dlg.destroy()
            self.refresh_all()

        ttk.Button(dlg, text="💾 ذخیره تغییرات", command=save).pack(pady=15)

    def add_repair_part_dlg(self):
        rep_id = self.get_selected_repair_id()
        if not rep_id:
            return

        dlg = tk.Toplevel(self)
        dlg.title("ثبت قطعه مصرفی برای تعمیر")
        dlg.geometry("400x250")
        dlg.grab_set()

        parts = self.db.get_parts()
        if not parts:
            messagebox.showwarning("هشدار", "هیچ قطعه‌ای در انبار تعریف نشده است.", parent=dlg)
            dlg.destroy()
            return

        ttk.Label(dlg, text="انتخاب قطعه از انبار:").pack(pady=5)
        cmb_part = ttk.Combobox(dlg, justify="right")
        cmb_part['values'] = [f"{p['id']}: {p['name']} (موجودی: {p['quantity']})" for p in parts]
        cmb_part.current(0)
        cmb_part.pack(fill="x", padx=15)

        ttk.Label(dlg, text="تعداد:").pack(pady=5)
        ent_qty = ttk.Entry(dlg, justify="right")
        ent_qty.insert(0, "1")
        ent_qty.pack(fill="x", padx=15)

        def save():
            p_id = int(cmb_part.get().split(":")[0])
            qty = int(ent_qty.get() or 1)
            ok = self.db.add_part_to_repair(rep_id, p_id, qty)
            if ok:
                messagebox.showinfo("موفق", "قطعه با موفقیت در پرونده اضافه و از انبار کسر شد.", parent=dlg)
                dlg.destroy()
                self.refresh_all()
            else:
                messagebox.showerror("خطا", "موجودی انبار برای این قطعه کافی نیست.", parent=dlg)

        ttk.Button(dlg, text="💾 افزودن قطعه", command=save).pack(pady=15)

    def add_repair_payment_dlg(self):
        rep_id = self.get_selected_repair_id()
        if not rep_id:
            return
        rep = self.db.get_repair(rep_id)

        dlg = tk.Toplevel(self)
        dlg.title(f"ثبت دریافتی بابت قبض {rep['receipt_no']}")
        dlg.geometry("400x320")
        dlg.grab_set()

        accounts = self.db.get_accounts()
        ttk.Label(dlg, text="حساب واریزی:").pack(pady=2)
        cmb_acc = ttk.Combobox(dlg, justify="right")
        cmb_acc['values'] = [f"{a['id']}: {a['title']}" for a in accounts]
        if accounts:
            cmb_acc.current(0)
        cmb_acc.pack(fill="x", padx=15)

        ttk.Label(dlg, text="روش پرداخت:").pack(pady=2)
        cmb_method = ttk.Combobox(dlg, values=PAYMENT_METHODS, justify="right")
        cmb_method.current(0)
        cmb_method.pack(fill="x", padx=15)

        ttk.Label(dlg, text="مبلغ دریافتی (تومان):").pack(pady=2)
        rem = max(0.0, rep["final_cost"] - rep["paid"])
        ent_amt = ttk.Entry(dlg, justify="right")
        ent_amt.insert(0, str(int(rem)))
        ent_amt.pack(fill="x", padx=15)

        ttk.Label(dlg, text="شماره پیگیری/مرجع:").pack(pady=2)
        ent_ref = ttk.Entry(dlg, justify="right")
        ent_ref.pack(fill="x", padx=15)

        def save():
            acc_id = int(cmb_acc.get().split(":")[0]) if cmb_acc.get() else None
            amt = float(ent_amt.get() or 0)
            if amt <= 0:
                messagebox.showwarning("خطا", "مبلغ دریافتی باید معتبر باشد.", parent=dlg)
                return
            self.db.add_payment({
                "repair_id": rep_id,
                "customer_id": rep["customer_id"],
                "account_id": acc_id,
                "amount": amt,
                "payment_method": cmb_method.get(),
                "reference_no": ent_ref.get().strip()
            })
            messagebox.showinfo("موفق", "پرداخت با موفقیت ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_all()

        ttk.Button(dlg, text="💳 ثبت تراکنش", command=save).pack(pady=15)

    def print_receipt(self):
        rep_id = self.get_selected_repair_id()
        if not rep_id:
            return
        rep = self.db.get_repair(rep_id)
        shop_info = {
            "shop_name": self.db.get_setting("shop_name", "تعمیرگاه تخصصی الکترونیک"),
            "shop_phone": self.db.get_setting("shop_phone", "-"),
            "shop_address": self.db.get_setting("shop_address", "-"),
            "terms": self.db.get_setting("terms", "")
        }
        file_path = generate_receipt_html(rep, shop_info)
        webbrowser.open(f"file://{os.path.abspath(file_path)}")

    # --- 3. انبار و فروش ---
    def setup_inventory_tab(self):
        top_bar = ttk.Frame(self.tab_inventory)
        top_bar.pack(fill="x", padx=10, pady=5)

        ttk.Label(top_bar, text="جستجو:").pack(side="right", padx=5)
        self.ent_part_search = ttk.Entry(top_bar, justify="right")
        self.ent_part_search.pack(side="right", padx=5)
        self.ent_part_search.bind("<KeyRelease>", lambda e: self.refresh_inventory())

        btn_new_part = ttk.Button(top_bar, text="➕ قطعه جدید", command=self.new_part)
        btn_new_part.pack(side="left", padx=5)

        btn_new_cat = ttk.Button(top_bar, text="📁 دسته‌بندی جدید", command=self.new_category)
        btn_new_cat.pack(side="left", padx=5)

        self.tree_parts = ttk.Treeview(self.tab_inventory, columns=("id", "serial", "name", "cat", "qty", "buy", "sell", "loc"), show="headings")
        for col, h in [("id", "شناسه"), ("serial", "سریال"), ("name", "نام قطعه"), ("cat", "دسته"), ("qty", "موجودی"), ("buy", "قیمت خرید"), ("sell", "قیمت فروش"), ("loc", "موقعیت")]:
            self.tree_parts.heading(col, text=h)
        self.tree_parts.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh_inventory(self):
        for row in self.tree_parts.get_children():
            self.tree_parts.delete(row)
        q = self.ent_part_search.get().strip()
        for p in self.db.get_parts(search=q):
            self.tree_parts.insert("", "end", values=(p["id"], p.get("serial") or "-", p.get("name"), p.get("category_name") or "-", p.get("quantity"), money(p.get("buy_price")), money(p.get("unit_price")), p.get("location") or "-"))

    def new_category(self):
        dlg = tk.Toplevel(self)
        dlg.title("ایجاد دسته‌بندی انبار")
        dlg.geometry("350x200")
        dlg.grab_set()

        ttk.Label(dlg, text="نام دسته:").pack(pady=5)
        ent = ttk.Entry(dlg, justify="right")
        ent.pack(fill="x", padx=15)

        def save():
            if ent.get().strip():
                self.db.add_category(ent.get().strip())
                messagebox.showinfo("موفق", "دسته‌بندی ثبت شد.", parent=dlg)
                dlg.destroy()
                self.refresh_inventory()

        ttk.Button(dlg, text="💾 ذخیره", command=save).pack(pady=15)

    def new_part(self):
        dlg = tk.Toplevel(self)
        dlg.title("تعریف قطعه جدید")
        dlg.geometry("400x380")
        dlg.grab_set()

        cats = self.db.get_categories()
        ttk.Label(dlg, text="دسته‌بندی:").pack(pady=2)
        cmb_cat = ttk.Combobox(dlg, justify="right")
        cmb_cat['values'] = [f"{c['id']}: {c['name']}" for c in cats]
        if cats:
            cmb_cat.current(0)
        cmb_cat.pack(fill="x", padx=15)

        ttk.Label(dlg, text="نام قطعه:").pack(pady=2)
        ent_name = ttk.Entry(dlg, justify="right")
        ent_name.pack(fill="x", padx=15)

        ttk.Label(dlg, text="موجودی اولیه:").pack(pady=2)
        ent_qty = ttk.Entry(dlg, justify="right")
        ent_qty.insert(0, "10")
        ent_qty.pack(fill="x", padx=15)

        ttk.Label(dlg, text="قیمت خرید (تومان):").pack(pady=2)
        ent_buy = ttk.Entry(dlg, justify="right")
        ent_buy.insert(0, "0")
        ent_buy.pack(fill="x", padx=15)

        ttk.Label(dlg, text="قیمت فروش (تومان):").pack(pady=2)
        ent_sell = ttk.Entry(dlg, justify="right")
        ent_sell.insert(0, "100000")
        ent_sell.pack(fill="x", padx=15)

        def save():
            if not ent_name.get().strip():
                messagebox.showwarning("خطا", "نام قطعه الزامی است.", parent=dlg)
                return
            cat_id = int(cmb_cat.get().split(":")[0]) if cmb_cat.get() else None
            self.db.add_part({
                "category_id": cat_id,
                "name": ent_name.get().strip(),
                "quantity": int(ent_qty.get() or 0),
                "buy_price": float(ent_buy.get() or 0),
                "unit_price": float(ent_sell.get() or 0)
            })
            messagebox.showinfo("موفق", "قطعه ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_all()

        ttk.Button(dlg, text="💾 ذخیره قطعه", command=save).pack(pady=15)

    # --- 4. حساب‌ها ---
    def setup_accounts_tab(self):
        top_bar = ttk.Frame(self.tab_accounts)
        top_bar.pack(fill="x", padx=10, pady=5)

        btn_acc = ttk.Button(top_bar, text="➕ تعریف حساب مالی جدید", command=self.new_account)
        btn_acc.pack(side="left", padx=5)

        self.tree_accounts = ttk.Treeview(self.tab_accounts, columns=("id", "title", "type", "bank", "num", "bal"), show="headings")
        for col, h in [("id", "شناسه"), ("title", "عنوان حساب"), ("type", "نوع"), ("bank", "بانک"), ("num", "شماره کارت/حساب"), ("bal", "موجودی (تومان)")]:
            self.tree_accounts.heading(col, text=h)
        self.tree_accounts.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_accounts(self):
        for row in self.tree_accounts.get_children():
            self.tree_accounts.delete(row)
        for a in self.db.get_accounts():
            self.tree_accounts.insert("", "end", values=(a["id"], a.get("title"), a.get("account_type"), a.get("bank_name") or "-", a.get("account_number") or "-", money(a.get("current_balance"))))

    def new_account(self):
        dlg = tk.Toplevel(self)
        dlg.title("افزودن حساب مالی")
        dlg.geometry("380x300")
        dlg.grab_set()

        ttk.Label(dlg, text="عنوان حساب:").pack(pady=2)
        ent_title = ttk.Entry(dlg, justify="right")
        ent_title.pack(fill="x", padx=15)

        ttk.Label(dlg, text="نوع حساب:").pack(pady=2)
        cmb_type = ttk.Combobox(dlg, values=ACCOUNT_TYPES, justify="right")
        cmb_type.current(0)
        cmb_type.pack(fill="x", padx=15)

        ttk.Label(dlg, text="نام بانک:").pack(pady=2)
        ent_bank = ttk.Entry(dlg, justify="right")
        ent_bank.pack(fill="x", padx=15)

        ttk.Label(dlg, text="موجودی اولیه (تومان):").pack(pady=2)
        ent_bal = ttk.Entry(dlg, justify="right")
        ent_bal.insert(0, "0")
        ent_bal.pack(fill="x", padx=15)

        def save():
            if not ent_title.get().strip():
                messagebox.showwarning("خطا", "عنوان حساب الزامی است.", parent=dlg)
                return
            self.db.add_account({
                "title": ent_title.get().strip(),
                "account_type": cmb_type.get(),
                "bank_name": ent_bank.get().strip(),
                "current_balance": float(ent_bal.get() or 0)
            })
            messagebox.showinfo("موفق", "حساب مالی ایجاد شد.", parent=dlg)
            dlg.destroy()
            self.refresh_accounts()

        ttk.Button(dlg, text="💾 ذخیره حساب", command=save).pack(pady=15)

    # --- 5. همکاران ---
    def setup_colleagues_tab(self):
        top_bar = ttk.Frame(self.tab_colleagues)
        top_bar.pack(fill="x", padx=10, pady=5)

        btn_coll = ttk.Button(top_bar, text="➕ تعریف همکار جدید", command=self.new_colleague)
        btn_coll.pack(side="left", padx=5)

        self.tree_colls = ttk.Treeview(self.tab_colleagues, columns=("id", "name", "mobile", "shop", "bal"), show="headings")
        for col, h in [("id", "شناسه"), ("name", "نام همکار"), ("mobile", "همراه"), ("shop", "فروشگاه/کارگاه"), ("bal", "مانده حساب (تومان)")]:
            self.tree_colls.heading(col, text=h)
        self.tree_colls.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_colleagues(self):
        for row in self.tree_colls.get_children():
            self.tree_colls.delete(row)
        for c in self.db.get_colleagues():
            self.tree_colls.insert("", "end", values=(c["id"], c.get("full_name"), c.get("mobile") or "-", c.get("shop_name") or "-", money(c.get("current_balance"))))

    def new_colleague(self):
        dlg = tk.Toplevel(self)
        dlg.title("ثبت همکار جدید")
        dlg.geometry("380x280")
        dlg.grab_set()

        ttk.Label(dlg, text="نام و نام خانوادگی:").pack(pady=2)
        ent_name = ttk.Entry(dlg, justify="right")
        ent_name.pack(fill="x", padx=15)

        ttk.Label(dlg, text="شماره همراه:").pack(pady=2)
        ent_mob = ttk.Entry(dlg, justify="right")
        ent_mob.pack(fill="x", padx=15)

        ttk.Label(dlg, text="نام فروشگاه / کارگاه:").pack(pady=2)
        ent_shop = ttk.Entry(dlg, justify="right")
        ent_shop.pack(fill="x", padx=15)

        def save():
            if not ent_name.get().strip():
                messagebox.showwarning("خطا", "نام همکار الزامی است.", parent=dlg)
                return
            self.db.add_colleague({
                "full_name": ent_name.get().strip(),
                "mobile": ent_mob.get().strip(),
                "shop_name": ent_shop.get().strip()
            })
            messagebox.showinfo("موفق", "همکار جدید ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_colleagues()

        ttk.Button(dlg, text="💾 ذخیره همکار", command=save).pack(pady=15)

    # --- 6. تکنسین‌ها ---
    def setup_techs_tab(self):
        top_bar = ttk.Frame(self.tab_techs)
        top_bar.pack(fill="x", padx=10, pady=5)

        btn_tech = ttk.Button(top_bar, text="➕ تعریف تکنسین جدید", command=self.new_technician)
        btn_tech.pack(side="left", padx=5)

        self.tree_techs = ttk.Treeview(self.tab_techs, columns=("id", "name", "mobile", "spec", "comm"), show="headings")
        for col, h in [("id", "شناسه"), ("name", "نام تکنسین"), ("mobile", "همراه"), ("spec", "تخصص"), ("comm", "درصد پورسانت")]:
            self.tree_techs.heading(col, text=h)
        self.tree_techs.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_techs(self):
        for row in self.tree_techs.get_children():
            self.tree_techs.delete(row)
        for t in self.db.get_technicians():
            self.tree_techs.insert("", "end", values=(t["id"], t.get("full_name"), t.get("mobile") or "-", t.get("specialty") or "-", f"{t.get('commission_rate', 0)}%"))

    def new_technician(self):
        dlg = tk.Toplevel(self)
        dlg.title("ثبت تکنسین جدید")
        dlg.geometry("380x300")
        dlg.grab_set()

        ttk.Label(dlg, text="نام و نام خانوادگی:").pack(pady=2)
        ent_name = ttk.Entry(dlg, justify="right")
        ent_name.pack(fill="x", padx=15)

        ttk.Label(dlg, text="شماره همراه:").pack(pady=2)
        ent_mob = ttk.Entry(dlg, justify="right")
        ent_mob.pack(fill="x", padx=15)

        ttk.Label(dlg, text="تخصص (مثلا سخت‌افزار/موبایل):").pack(pady=2)
        ent_spec = ttk.Entry(dlg, justify="right")
        ent_spec.pack(fill="x", padx=15)

        ttk.Label(dlg, text="درصد پورسانت (٪):").pack(pady=2)
        ent_comm = ttk.Entry(dlg, justify="right")
        ent_comm.insert(0, "0")
        ent_comm.pack(fill="x", padx=15)

        def save():
            if not ent_name.get().strip():
                messagebox.showwarning("خطا", "نام تکنسین الزامی است.", parent=dlg)
                return
            self.db.add_technician({
                "full_name": ent_name.get().strip(),
                "mobile": ent_mob.get().strip(),
                "specialty": ent_spec.get().strip(),
                "commission_rate": float(ent_comm.get() or 0)
            })
            messagebox.showinfo("موفق", "تکنسین جدید ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_techs()

        ttk.Button(dlg, text="💾 ذخیره تکنسین", command=save).pack(pady=15)

    # --- 7. مشتریان ---
    def setup_custs_tab(self):
        top_bar = ttk.Frame(self.tab_custs)
        top_bar.pack(fill="x", padx=10, pady=5)

        ttk.Label(top_bar, text="جستجو:").pack(side="right", padx=5)
        self.ent_cust_search = ttk.Entry(top_bar, justify="right")
        self.ent_cust_search.pack(side="right", padx=5)
        self.ent_cust_search.bind("<KeyRelease>", lambda e: self.refresh_custs())

        btn_cust = ttk.Button(top_bar, text="➕ تعریف مشتری جدید", command=self.new_customer)
        btn_cust.pack(side="left", padx=5)

        self.tree_custs = ttk.Treeview(self.tab_custs, columns=("id", "name", "mobile", "phone", "addr"), show="headings")
        for col, h in [("id", "شناسه"), ("name", "نام و نام خانوادگی"), ("mobile", "شماره همراه"), ("phone", "تلفن ثابت"), ("addr", "آدرس")]:
            self.tree_custs.heading(col, text=h)
        self.tree_custs.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_custs(self):
        for row in self.tree_custs.get_children():
            self.tree_custs.delete(row)
        q = self.ent_cust_search.get().strip()
        for c in self.db.get_customers(search=q):
            self.tree_custs.insert("", "end", values=(c["id"], c.get("full_name"), c.get("mobile"), c.get("phone") or "-", c.get("address") or "-"))

    def new_customer(self):
        dlg = tk.Toplevel(self)
        dlg.title("ثبت مشتری جدید")
        dlg.geometry("380x320")
        dlg.grab_set()

        ttk.Label(dlg, text="نام و نام خانوادگی:").pack(pady=2)
        ent_name = ttk.Entry(dlg, justify="right")
        ent_name.pack(fill="x", padx=15)

        ttk.Label(dlg, text="شماره همراه:").pack(pady=2)
        ent_mob = ttk.Entry(dlg, justify="right")
        ent_mob.pack(fill="x", padx=15)

        ttk.Label(dlg, text="کد ملی:").pack(pady=2)
        ent_nat = ttk.Entry(dlg, justify="right")
        ent_nat.pack(fill="x", padx=15)

        ttk.Label(dlg, text="آدرس:").pack(pady=2)
        ent_addr = ttk.Entry(dlg, justify="right")
        ent_addr.pack(fill="x", padx=15)

        def save():
            if not ent_name.get().strip() or not ent_mob.get().strip():
                messagebox.showwarning("خطا", "نام و شماره همراه الزامی است.", parent=dlg)
                return
            self.db.add_customer({
                "full_name": ent_name.get().strip(),
                "mobile": ent_mob.get().strip(),
                "national_code": ent_nat.get().strip(),
                "address": ent_addr.get().strip()
            })
            messagebox.showinfo("موفق", "مشتری جدید ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_custs()

        ttk.Button(dlg, text="💾 ذخیره مشتری", command=save).pack(pady=15)

    # --- 8. حسابداری ---
    def setup_accounting_tab(self):
        top_bar = ttk.Frame(self.tab_accounting)
        top_bar.pack(fill="x", padx=10, pady=5)

        btn_exp = ttk.Button(top_bar, text="➕ ثبت هزینه جدید", command=self.new_expense)
        btn_exp.pack(side="left", padx=5)

        self.tree_expenses = ttk.Treeview(self.tab_accounting, columns=("id", "cat", "title", "amount", "date"), show="headings")
        for col, h in [("id", "شناسه"), ("cat", "دسته"), ("title", "عنوان هزینه"), ("amount", "مبلغ (تومان)"), ("date", "تاریخ")]:
            self.tree_expenses.heading(col, text=h)
        self.tree_expenses.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_accounting(self):
        for row in self.tree_expenses.get_children():
            self.tree_expenses.delete(row)
        for e in self.db.get_expenses():
            self.tree_expenses.insert("", "end", values=(e["id"], e.get("category"), e.get("title"), money(e.get("amount")), iso_to_jalali(e.get("expense_date"))))

    def new_expense(self):
        dlg = tk.Toplevel(self)
        dlg.title("ثبت هزینه کارگاه")
        dlg.geometry("400x320")
        dlg.grab_set()

        ttk.Label(dlg, text="دسته هزینه:").pack(pady=2)
        cmb_cat = ttk.Combobox(dlg, values=EXPENSE_CATEGORIES, justify="right")
        cmb_cat.current(0)
        cmb_cat.pack(fill="x", padx=15)

        ttk.Label(dlg, text="عنوان هزینه:").pack(pady=2)
        ent_title = ttk.Entry(dlg, justify="right")
        ent_title.pack(fill="x", padx=15)

        accounts = self.db.get_accounts()
        ttk.Label(dlg, text="پرداخت از حساب:").pack(pady=2)
        cmb_acc = ttk.Combobox(dlg, justify="right")
        cmb_acc['values'] = [f"{a['id']}: {a['title']}" for a in accounts]
        if accounts:
            cmb_acc.current(0)
        cmb_acc.pack(fill="x", padx=15)

        ttk.Label(dlg, text="مبلغ هزینه (تومان):").pack(pady=2)
        ent_amt = ttk.Entry(dlg, justify="right")
        ent_amt.pack(fill="x", padx=15)

        def save():
            if not ent_title.get().strip() or not ent_amt.get().strip():
                messagebox.showwarning("خطا", "عنوان و مبلغ هزینه الزامی است.", parent=dlg)
                return
            acc_id = int(cmb_acc.get().split(":")[0]) if cmb_acc.get() else None
            self.db.add_expense({
                "category": cmb_cat.get(),
                "title": ent_title.get().strip(),
                "account_id": acc_id,
                "amount": float(ent_amt.get())
            })
            messagebox.showinfo("موفق", "هزینه ثبت شد.", parent=dlg)
            dlg.destroy()
            self.refresh_all()

        ttk.Button(dlg, text="💾 ثبت هزینه", command=save).pack(pady=15)

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_repairs()
        self.refresh_inventory()
        self.refresh_accounts()
        self.refresh_colleagues()
        self.refresh_techs()
        self.refresh_custs()
        self.refresh_accounting()


if __name__ == "__main__":
    app = MainAppTk()
    app.mainloop()
