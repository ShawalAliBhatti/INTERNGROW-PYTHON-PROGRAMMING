"""Expense Tracker - Tkinter + SQLite desktop application."""
import csv
import hashlib
import os
import sqlite3
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

DB = "expenses.db"
CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Health", "Other"]


class Database:
    def __init__(self, path=DB):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
            salt TEXT, pw TEXT)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT,
            category TEXT, amount REAL, date TEXT)""")
        self.conn.commit()

    @staticmethod
    def _hash(pw, salt):
        return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 100_000).hex()

    def register(self, u, p):
        salt = os.urandom(16).hex()
        try:
            self.conn.execute("INSERT INTO users(username,salt,pw) VALUES(?,?,?)",
                              (u, salt, self._hash(p, salt)))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, u, p):
        r = self.conn.execute("SELECT id,salt,pw FROM users WHERE username=?", (u,)).fetchone()
        return r[0] if r and self._hash(p, r[1]) == r[2] else None

    def add(self, uid, title, cat, amt, d):
        self.conn.execute("INSERT INTO expenses(user_id,title,category,amount,date) VALUES(?,?,?,?,?)",
                          (uid, title, cat, amt, d))
        self.conn.commit()

    def update(self, eid, title, cat, amt, d):
        self.conn.execute("UPDATE expenses SET title=?,category=?,amount=?,date=? WHERE id=?",
                          (title, cat, amt, d, eid))
        self.conn.commit()

    def delete(self, eid):
        self.conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
        self.conn.commit()

    def list(self, uid, search="", cat=""):
        q = "SELECT id,title,category,amount,date FROM expenses WHERE user_id=? AND title LIKE ?"
        p = [uid, f"%{search}%"]
        if cat and cat != "All":
            q += " AND category=?"
            p.append(cat)
        return self.conn.execute(q + " ORDER BY date DESC", p).fetchall()

    def by_category(self, uid):
        return self.conn.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? "
                                 "GROUP BY category", (uid,)).fetchall()


class LoginWindow(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("Expense Tracker - Login")
        self.geometry("320x230")
        self.resizable(False, False)
        ttk.Label(self, text="Expense Tracker", font=("Segoe UI", 16, "bold")).pack(pady=15)
        self.u, self.p = tk.StringVar(), tk.StringVar()
        ttk.Label(self, text="Username").pack()
        ttk.Entry(self, textvariable=self.u).pack()
        ttk.Label(self, text="Password").pack()
        ttk.Entry(self, textvariable=self.p, show="*").pack()
        f = ttk.Frame(self)
        f.pack(pady=15)
        ttk.Button(f, text="Login", command=self.do_login).grid(row=0, column=0, padx=5)
        ttk.Button(f, text="Register", command=self.do_register).grid(row=0, column=1, padx=5)

    def do_login(self):
        uid = self.db.login(self.u.get().strip(), self.p.get())
        if uid:
            self.destroy()
            Dashboard(self.db, uid, self.u.get().strip()).mainloop()
        else:
            messagebox.showerror("Error", "Invalid username or password")

    def do_register(self):
        if not self.u.get().strip() or len(self.p.get()) < 4:
            messagebox.showwarning("Invalid", "Username required, password min 4 chars")
        elif self.db.register(self.u.get().strip(), self.p.get()):
            messagebox.showinfo("Done", "Registered! Now login.")
        else:
            messagebox.showerror("Error", "Username already exists")


class Dashboard(tk.Tk):
    def __init__(self, db, uid, username):
        super().__init__()
        self.db, self.uid = db, uid
        self.title(f"Expense Tracker - {username}")
        self.geometry("900x600")
        self.selected = None
        self.total_var = tk.StringVar()

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, textvariable=self.total_var, font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side="right", padx=3)
        ttk.Button(top, text="Export PDF", command=self.export_pdf).pack(side="right", padx=3)

        form = ttk.LabelFrame(self, text="Expense", padding=10)
        form.pack(fill="x", padx=10)
        self.title_v, self.amt_v = tk.StringVar(), tk.StringVar()
        self.cat_v, self.date_v = tk.StringVar(value=CATEGORIES[0]), tk.StringVar(value=str(date.today()))
        for i, (lbl, w) in enumerate([("Title", ttk.Entry(form, textvariable=self.title_v)),
                                      ("Amount", ttk.Entry(form, textvariable=self.amt_v)),
                                      ("Category", ttk.Combobox(form, textvariable=self.cat_v,
                                                                values=CATEGORIES, state="readonly")),
                                      ("Date", ttk.Entry(form, textvariable=self.date_v))]):
            ttk.Label(form, text=lbl).grid(row=0, column=i * 2, padx=3)
            w.grid(row=0, column=i * 2 + 1, padx=3)
        btns = ttk.Frame(form)
        btns.grid(row=1, column=0, columnspan=8, pady=8)
        for t, c in [("Add", self.add), ("Update", self.update), ("Delete", self.delete),
                     ("Clear", self.clear)]:
            ttk.Button(btns, text=t, command=c).pack(side="left", padx=4)

        sf = ttk.Frame(self, padding=10)
        sf.pack(fill="x")
        self.search_v, self.filter_v = tk.StringVar(), tk.StringVar(value="All")
        ttk.Label(sf, text="Search").pack(side="left")
        e = ttk.Entry(sf, textvariable=self.search_v)
        e.pack(side="left", padx=5)
        e.bind("<KeyRelease>", lambda _: self.refresh())
        ttk.Label(sf, text="Category").pack(side="left")
        cb = ttk.Combobox(sf, textvariable=self.filter_v, values=["All"] + CATEGORIES, state="readonly")
        cb.pack(side="left", padx=5)
        cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        self.tree = ttk.Treeview(self, columns=("id", "title", "cat", "amt", "date"),
                                 show="headings", height=8)
        for c, t, w in [("id", "ID", 40), ("title", "Title", 250), ("cat", "Category", 120),
                        ("amt", "Amount", 100), ("date", "Date", 120)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(fill="x", padx=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.chart = tk.Canvas(self, height=200, bg="white", highlightthickness=1)
        self.chart.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh()

    def rows(self):
        return self.db.list(self.uid, self.search_v.get(), self.filter_v.get())

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.rows()
        for r in rows:
            self.tree.insert("", "end", values=r)
        self.total_var.set(f"Total: {sum(r[3] for r in rows):,.2f}")
        self.draw_chart()

    def draw_chart(self):
        self.chart.delete("all")
        data = self.db.by_category(self.uid)
        if not data:
            self.chart.create_text(200, 90, text="No data yet")
            return
        mx = max(v for _, v in data)
        colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948"]
        self.chart.create_text(10, 10, anchor="w", text="Spending by category",
                               font=("Segoe UI", 10, "bold"))
        for i, (cat, val) in enumerate(data):
            x = 60 + i * 110
            h = (val / mx) * 120
            self.chart.create_rectangle(x, 170 - h, x + 60, 170, fill=colors[i % 6])
            self.chart.create_text(x + 30, 180, text=cat)
            self.chart.create_text(x + 30, 165 - h, text=f"{val:,.0f}")

    def on_select(self, _):
        sel = self.tree.selection()
        if sel:
            v = self.tree.item(sel[0])["values"]
            self.selected = v[0]
            self.title_v.set(v[1]); self.cat_v.set(v[2])
            self.amt_v.set(v[3]); self.date_v.set(v[4])

    def read_form(self):
        title = self.title_v.get().strip()
        try:
            amt = float(self.amt_v.get())
            if amt <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Amount must be a positive number")
            return None
        if not title:
            messagebox.showwarning("Invalid", "Title is required")
            return None
        return title, self.cat_v.get(), amt, self.date_v.get()

    def add(self):
        d = self.read_form()
        if d:
            self.db.add(self.uid, *d)
            self.clear()

    def update(self):
        d = self.read_form()
        if d and self.selected:
            self.db.update(self.selected, *d)
            self.clear()
        elif not self.selected:
            messagebox.showinfo("Select", "Select a row first")

    def delete(self):
        if self.selected and messagebox.askyesno("Confirm", "Delete this expense?"):
            self.db.delete(self.selected)
            self.clear()

    def clear(self):
        self.selected = None
        self.title_v.set(""); self.amt_v.set("")
        self.date_v.set(str(date.today()))
        self.refresh()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ID", "Title", "Category", "Amount", "Date"])
                w.writerows(self.rows())
            messagebox.showinfo("Exported", "CSV saved.")

    def export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror("Missing", "Run: pip install reportlab")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        c = canvas.Canvas(path, pagesize=A4)
        y = 800
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "Expense Report")
        y -= 30
        c.setFont("Helvetica", 10)
        rows = self.rows()
        for r in rows:
            if y < 50:
                c.showPage(); y = 800; c.setFont("Helvetica", 10)
            c.drawString(50, y, f"{r[4]}   {r[1][:30]:30}   {r[2]:10}   {r[3]:,.2f}")
            y -= 15
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y - 10, f"Total: {sum(r[3] for r in rows):,.2f}")
        c.save()
        messagebox.showinfo("Exported", "PDF saved.")


if __name__ == "__main__":
    LoginWindow(Database()).mainloop()
