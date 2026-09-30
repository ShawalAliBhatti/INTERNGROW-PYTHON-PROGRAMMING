"""File & Data Processing System with logging, backup and PDF reports."""
import csv
import logging
import os
import shutil
from datetime import datetime

import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BACKUP_DIR = "backups"
logging.basicConfig(filename="app.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


def backup(path):
    """Automatic backup before modifying/deleting a file."""
    if os.path.exists(path):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"{os.path.basename(path)}.{stamp}.bak")
        shutil.copy2(path, dest)
        logging.info("Backup created: %s", dest)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        logging.info("Read file %s", path)
        return content
    except FileNotFoundError:
        logging.error("File not found: %s", path)
        return None


def write_text(path, text):
    backup(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    logging.info("Wrote file %s", path)


def update_text(path, text):
    if not os.path.exists(path):
        logging.error("Cannot update, missing: %s", path)
        return False
    backup(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + text)
    logging.info("Updated file %s", path)
    return True


def delete_file(path):
    if not os.path.exists(path):
        logging.error("Cannot delete, missing: %s", path)
        return False
    backup(path)
    os.remove(path)
    logging.info("Deleted file %s", path)
    return True


def process_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    logging.info("Processed CSV %s (%d rows)", path, len(rows))
    return rows


def csv_summary(rows):
    print(f"Rows: {len(rows)}")
    if not rows:
        return
    print("Columns:", ", ".join(rows[0].keys()))
    for col in rows[0]:
        try:
            vals = [float(r[col]) for r in rows]
            print(f"  {col}: total={sum(vals):.2f} avg={sum(vals)/len(vals):.2f} "
                  f"min={min(vals)} max={max(vals)}")
        except ValueError:
            pass


def read_excel(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    data = {}
    for ws in wb.worksheets:
        data[ws.title] = [list(r) for r in ws.iter_rows(values_only=True)]
    logging.info("Read Excel %s", path)
    return data


def generate_pdf(rows, out="report.pdf"):
    c = canvas.Canvas(out, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Data Report")
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(50, y, f"Generated: {datetime.now():%Y-%m-%d %H:%M}   Rows: {len(rows)}")
    y -= 30
    if rows:
        cols = list(rows[0].keys())
        step = (w - 100) / len(cols)
        c.setFont("Helvetica-Bold", 10)
        for i, col in enumerate(cols):
            c.drawString(50 + i * step, y, col)
        y -= 15
        c.setFont("Helvetica", 10)
        for r in rows:
            if y < 50:
                c.showPage()
                y = h - 50
                c.setFont("Helvetica", 10)
            for i, col in enumerate(cols):
                c.drawString(50 + i * step, y, str(r[col])[:18])
            y -= 15
    c.save()
    logging.info("PDF report generated: %s", out)
    return out


def create_samples():
    with open("sample.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["name", "department", "salary"])
        wr.writerows([["Ali", "IT", 50000], ["Sara", "HR", 45000],
                      ["Ahmed", "IT", 60000], ["Zoya", "Sales", 40000]])
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Product", "Qty", "Price"])
    for row in [["Pen", 100, 20], ["Book", 50, 150], ["Bag", 10, 900]]:
        ws.append(row)
    wb.save("sample.xlsx")
    write_text("sample.txt", "Hello from InternGrow!")
    print("Sample files created: sample.txt, sample.csv, sample.xlsx")


def menu():
    while True:
        print("\n===== File & Data Processing System =====")
        print("1. Create sample files\n2. Read text file\n3. Write text file")
        print("4. Update (append) text file\n5. Delete file\n6. Process CSV")
        print("7. Read Excel\n8. Generate PDF report from CSV\n9. Manual backup\n0. Exit")
        ch = input("Choose: ").strip()
        try:
            if ch == "1":
                create_samples()
            elif ch == "2":
                t = read_text(input("File path: "))
                print(t if t is not None else "File not found.")
            elif ch == "3":
                write_text(input("File path: "), input("Text: "))
                print("Saved.")
            elif ch == "4":
                ok = update_text(input("File path: "), input("Text to add: "))
                print("Updated." if ok else "File not found.")
            elif ch == "5":
                ok = delete_file(input("File path: "))
                print("Deleted (backup kept)." if ok else "File not found.")
            elif ch == "6":
                csv_summary(process_csv(input("CSV path: ")))
            elif ch == "7":
                for sheet, rows in read_excel(input("Excel path: ")).items():
                    print("Sheet:", sheet)
                    for r in rows:
                        print("  ", r)
            elif ch == "8":
                print("Created", generate_pdf(process_csv(input("CSV path: "))))
            elif ch == "9":
                backup(input("File path: "))
                print("Backup done.")
            elif ch == "0":
                break
            else:
                print("Invalid choice.")
        except (OSError, KeyError, ValueError) as e:
            logging.error("Error: %s", e)
            print("Error:", e)
        except Exception as e:
            logging.exception("Unexpected error")
            print("Unexpected error:", e)


if __name__ == "__main__":
    menu()
