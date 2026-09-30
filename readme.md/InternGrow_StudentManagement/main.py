"""Smart Student Management System - console based, JSON storage."""
import json
import os

DATA_FILE = "students.json"
SUBJECTS = ["Math", "English", "Science", "Computer"]


class Student:
    def __init__(self, sid, name, age, marks):
        self.sid = sid
        self.name = name
        self.age = age
        self.marks = marks  # dict: subject -> marks

    def average(self):
        return sum(self.marks.values()) / len(self.marks) if self.marks else 0

    def grade(self):
        avg = self.average()
        if avg >= 90: return "A+"
        if avg >= 80: return "A"
        if avg >= 70: return "B"
        if avg >= 60: return "C"
        if avg >= 50: return "D"
        return "F"

    def to_dict(self):
        return {"sid": self.sid, "name": self.name, "age": self.age, "marks": self.marks}

    @staticmethod
    def from_dict(d):
        return Student(d["sid"], d["name"], d["age"], d["marks"])

    def __str__(self):
        m = ", ".join(f"{k}:{v}" for k, v in self.marks.items())
        return (f"ID: {self.sid} | {self.name} | Age: {self.age} | {m} | "
                f"Avg: {self.average():.1f} | Grade: {self.grade()}")


class StudentManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.students = []
        self.load()

    def load(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self.students = [Student.from_dict(d) for d in json.load(f)]
        except FileNotFoundError:
            self.students = []
        except (json.JSONDecodeError, KeyError):
            print("Data file corrupted. Starting with empty list.")
            self.students = []

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in self.students], f, indent=4)
        except OSError as e:
            print("Could not save data:", e)

    def find(self, sid):
        return next((s for s in self.students if s.sid == sid), None)

    def add(self, student):
        if self.find(student.sid):
            raise ValueError("A student with this ID already exists.")
        self.students.append(student)
        self.save()

    def update(self, sid, name=None, age=None, marks=None):
        s = self.find(sid)
        if not s:
            raise ValueError("Student not found.")
        if name: s.name = name
        if age is not None: s.age = age
        if marks: s.marks = marks
        self.save()

    def delete(self, sid):
        s = self.find(sid)
        if not s:
            raise ValueError("Student not found.")
        self.students.remove(s)
        self.save()

    def search(self, keyword):
        k = keyword.lower()
        return [s for s in self.students if k in s.name.lower() or k == s.sid.lower()]


# ---------- input helpers (validation) ----------
def get_text(prompt, allow_empty=False):
    while True:
        v = input(prompt).strip()
        if v or allow_empty:
            return v
        print("Input cannot be empty.")


def get_int(prompt, lo, hi, allow_empty=False):
    while True:
        v = input(prompt).strip()
        if allow_empty and v == "":
            return None
        try:
            n = int(v)
            if lo <= n <= hi:
                return n
            print(f"Enter a number between {lo} and {hi}.")
        except ValueError:
            print("Please enter a valid number.")


def get_marks():
    return {sub: get_int(f"  Marks in {sub} (0-100): ", 0, 100) for sub in SUBJECTS}


def show(students):
    if not students:
        print("No records found.")
    for s in students:
        print(s)


def menu():
    mgr = StudentManager()
    while True:
        print("\n===== Student Management System =====")
        print("1. Add Student\n2. Update Student\n3. Delete Student\n4. Search Student")
        print("5. Calculate Grades\n6. Display All Records\n7. Exit")
        choice = input("Choose (1-7): ").strip()
        try:
            if choice == "1":
                sid = get_text("Student ID: ")
                name = get_text("Name: ")
                age = get_int("Age (5-100): ", 5, 100)
                mgr.add(Student(sid, name, age, get_marks()))
                print("Student added.")
            elif choice == "2":
                sid = get_text("ID of student to update: ")
                if not mgr.find(sid):
                    print("Student not found.")
                    continue
                name = get_text("New name (Enter to skip): ", True)
                age = get_int("New age (Enter to skip): ", 5, 100, True)
                change = input("Update marks? (y/n): ").lower() == "y"
                mgr.update(sid, name or None, age, get_marks() if change else None)
                print("Student updated.")
            elif choice == "3":
                mgr.delete(get_text("ID of student to delete: "))
                print("Student deleted.")
            elif choice == "4":
                show(mgr.search(get_text("Enter name or ID: ")))
            elif choice == "5":
                for s in mgr.students:
                    print(f"{s.name}: Average {s.average():.1f} -> Grade {s.grade()}")
                if not mgr.students:
                    print("No records found.")
            elif choice == "6":
                show(mgr.students)
            elif choice == "7":
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")
        except ValueError as e:
            print("Error:", e)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    menu()
