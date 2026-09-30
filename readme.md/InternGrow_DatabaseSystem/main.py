"""Database Management System (SQLite): auth, roles, CRUD, search, filters, reports."""
import getpass
import hashlib
import os
import shutil
import sqlite3
from datetime import datetime

DB = "company.db"


def connect():
    return sqlite3.connect(DB)


def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS employees(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            department TEXT NOT NULL, salary REAL NOT NULL, email TEXT)""")


def hash_pw(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000).hex()


def register(username, password, role=None):
    with connect() as c:
        if role is None:  # first user becomes admin
            n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            role = "admin" if n == 0 else "user"
        salt = os.urandom(16).hex()
        try:
            c.execute("INSERT INTO users(username,salt,password_hash,role) VALUES(?,?,?,?)",
                      (username, salt, hash_pw(password, salt), role))
        except sqlite3.IntegrityError:
            return None
    return role


def login(username, password):
    with connect() as c:
        row = c.execute("SELECT salt,password_hash,role FROM users WHERE username=?",
                        (username,)).fetchone()
    if row and hash_pw(password, row[0]) == row[1]:
        return row[2]
    return None


# ---- CRUD ----
def add_employee(name, dept, salary, email):
    with connect() as c:
        c.execute("INSERT INTO employees(name,department,salary,email) VALUES(?,?,?,?)",
                  (name, dept, salary, email))


def update_employee(eid, name, dept, salary, email):
    with connect() as c:
        return c.execute("UPDATE employees SET name=?,department=?,salary=?,email=? WHERE id=?",
                         (name, dept, salary, email, eid)).rowcount


def delete_employee(eid):
    with connect() as c:
        return c.execute("DELETE FROM employees WHERE id=?", (eid,)).rowcount


def list_employees(search="", dept="", min_salary=0):
    q = "SELECT * FROM employees WHERE (name LIKE ? OR email LIKE ?) AND salary>=?"
    p = [f"%{search}%", f"%{search}%", min_salary]
    if dept:
        q += " AND department=?"
        p.append(dept)
    with connect() as c:
        return c.execute(q + " ORDER BY id", p).fetchall()


def report():
    with connect() as c:
        total = c.execute("SELECT COUNT(*), IFNULL(AVG(salary),0), IFNULL(SUM(salary),0) "
                          "FROM employees").fetchone()
        by_dept = c.execute("SELECT department, COUNT(*), AVG(salary) FROM employees "
                            "GROUP BY department").fetchall()
    print(f"Employees: {total[0]} | Avg salary: {total[1]:.0f} | Payroll: {total[2]:.0f}")
    for d, n, a in by_dept:
        print(f"  {d}: {n} employees, avg salary {a:.0f}")


def backup_db():
    os.makedirs("backups", exist_ok=True)
    dest = f"backups/company_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(DB, dest)
    return dest


def show(rows):
    if not rows:
        print("No records.")
    for r in rows:
        print(f"#{r[0]} {r[1]} | {r[2]} | {r[3]:.0f} | {r[4]}")


def number(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Enter a valid number.")


def app(role):
    admin = role == "admin"
    while True:
        print(f"\n--- Employee Manager (role: {role}) ---")
        print("1.List/Search  2.Filter  3.Add  4.Report")
        if admin:
            print("5.Update  6.Delete  7.Backup database")
        print("0.Logout")
        ch = input("Choose: ").strip()
        if ch == "1":
            show(list_employees(input("Search text (blank=all): ")))
        elif ch == "2":
            show(list_employees(dept=input("Department (blank=any): "),
                                min_salary=number("Minimum salary: ")))
        elif ch == "3":
            add_employee(input("Name: "), input("Department: "), number("Salary: "), input("Email: "))
            print("Added.")
        elif ch == "4":
            report()
        elif ch == "5" and admin:
            eid = int(number("Employee ID: "))
            n = update_employee(eid, input("Name: "), input("Department: "),
                                number("Salary: "), input("Email: "))
            print("Updated." if n else "ID not found.")
        elif ch == "6" and admin:
            print("Deleted." if delete_employee(int(number("Employee ID: "))) else "ID not found.")
        elif ch == "7" and admin:
            print("Backup saved:", backup_db())
        elif ch == "0":
            break
        else:
            print("Invalid choice or permission denied.")


def main():
    init_db()
    while True:
        print("\n===== Database Management System =====")
        print("1.Register  2.Login  0.Exit")
        ch = input("Choose: ").strip()
        if ch == "1":
            u = input("Username: ").strip()
            p = getpass.getpass("Password (min 6 chars): ")
            if not u or len(p) < 6:
                print("Invalid username or password too short.")
                continue
            r = register(u, p)
            print(f"Registered as {r}." if r else "Username already exists.")
        elif ch == "2":
            r = login(input("Username: ").strip(), getpass.getpass("Password: "))
            if r:
                app(r)
            else:
                print("Wrong username or password.")
        elif ch == "0":
            break


if __name__ == "__main__":
    main()
