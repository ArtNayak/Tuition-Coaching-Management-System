"""Tuition & coaching centre management system (command line).

Roles: Administrator, Trainer, Lecturer, Student. Data lives in za.json next to this
script and is created on first run. Passwords are stored as salted PBKDF2 hashes.
"""
import hashlib
import hmac
import json
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "za.json")
ROLES = ("Administrator", "Trainer", "Lecturer", "Student")
TABLES = ("users", "moduleinfo", "feedback", "trainer_list", "studentlist", "trainer_profile",
          "student_profile", "administrator_profile", "lecturer_profile", "request_status",
          "enroll_student", "trainerview")
TBU = "To be updated"  # placeholder until a trainer fills in class name / charges / schedule


# ---------- storage ----------
def load():
    try:
        with open(DB_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    for table in TABLES:
        data.setdefault(table, [])
    return data


def save(data):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, DB_FILE)  # atomic, so a crash never leaves a half-written file


# ---------- passwords ----------
def hash_pw(password, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def check_pw(password, stored):
    if not stored.startswith("pbkdf2$"):
        return hmac.compare_digest(password, stored)  # legacy plain-text entry
    return hmac.compare_digest(hash_pw(password, stored.split("$")[1]), stored)


def migrate():
    """Hash any plain-text passwords and drop the password copies kept in profiles."""
    data = load()
    changed = False
    for user in data["users"]:
        if not user["password"].startswith("pbkdf2$"):
            user["password"] = hash_pw(user["password"])
            changed = True
    for role in ROLES:
        for profile in data[role.lower() + "_profile"]:
            changed |= profile.pop("password", None) is not None
    if changed:
        save(data)


# ---------- input helpers ----------
def ask(prompt):
    return input(prompt).strip()


def ask_int(prompt, valid):
    while True:
        text = ask(prompt)
        if text.isdigit() and int(text) in valid:
            return int(text)
        print(f"Please enter one of: {', '.join(map(str, valid))}")


def ask_amount(prompt):
    while True:
        try:
            value = float(ask(prompt))
            if value >= 0:
                return value
        except ValueError:
            pass
        print("Please enter a valid amount (number, 0 or more).")


def menu(title, options, header=None):
    """Show a numbered menu until the user picks the last option (logout/back)."""
    while True:
        if header:
            header()
        print(f"\n***** {title} *****")
        for i, (label, _) in enumerate(options, 1):
            print(f"{i}. {label}")
        action = options[ask_int("Choose: ", range(1, len(options) + 1)) - 1][1]
        if action is None:
            return
        action()


def find_class(data, module, level, class_name):
    return next((m for m in data["moduleinfo"] if m["module_name"] == module
                 and m["level"] == level and m["class_name"] == class_name), None)


def show_module(m, with_trainer=False):
    print(f"Module: {m['module_name']}\nLevel: {m['level']}\nClass: {m['class_name']}\n"
          f"Schedule: {m['schedule']}\nCharges: {m['charges']}")
    if with_trainer:
        print(f"Trainer: {m['trainer_name']}")
    print("------------")


# ---------- accounts ----------
def create_account():
    data = load()
    username = ask("\nUsername: ")
    if not username:
        return print("Username cannot be empty.")
    if any(u["username"] == username for u in data["users"]):
        return print("Username already exists. Choose a different username.")
    password = ask("Password: ")
    if not password:
        return print("Password cannot be empty.")
    for i, role in enumerate(ROLES, 1):
        print(f"{i}. {role}")
    role = ROLES[ask_int("Role: ", range(1, len(ROLES) + 1)) - 1]

    print("\nCreate your profile:")
    profile = {"Username": username, "role": role, "address": ask("Address: ")}
    if role == "Student":
        profile["level"] = ask("Level (Foundation, degree level 1, 2 or 3): ")
    else:
        profile["years of experience"] = ask("Years of experience: ")
    profile["age"] = ask("Age: ")

    data["users"].append({"username": username, "password": hash_pw(password), "role": role})
    data[role.lower() + "_profile"].append(profile)
    save(data)
    print("Account created successfully.")


def login():
    data = load()
    for _ in range(3):
        username, password = ask("\nUsername: "), ask("Password: ")
        user = next((u for u in data["users"] if u["username"] == username), None)
        if user and check_pw(password, user["password"]):
            return user
        print("Wrong username or password")
    print("Maximum number of attempts reached")


def update_profile(user):
    data = load()
    profile = next((p for p in data[user["role"].lower() + "_profile"]
                    if p["Username"] == user["username"]), None)
    if profile is None:
        return print("No profile found for this account.")
    editable = [k for k in profile if k not in ("Username", "role")] + ["password"]
    print("Current profile:\n" + json.dumps(profile, indent=4))
    print("Editable fields: " + ", ".join(editable))
    key = ask("Field to update: ")
    if key not in editable:
        return print("Invalid field.")
    value = ask(f"New value for {key}: ")
    if key == "password":
        if not value:
            return print("Password cannot be empty.")
        next(u for u in data["users"] if u["username"] == user["username"])["password"] = hash_pw(value)
    else:
        profile[key] = value
    save(data)
    print("Profile updated successfully.")


# ---------- administrator ----------
def manage_trainers():
    print("1. Register trainer\n2. Delete trainer\n3. Back")
    choice = ask_int("Choose: ", (1, 2, 3))
    if choice == 3:
        return
    data = load()
    name = ask("Trainer username: ")
    if choice == 1:
        if not any(u["username"] == name and u["role"] == "Trainer" for u in data["users"]):
            return print("No Trainer account with that username.")
        if any(t["trainer_name"] == name for t in data["trainer_list"]):
            return print("Trainer is already registered.")
        data["trainer_list"].append({"trainer_name": name})
        print("Trainer registered.")
    else:
        known = any(m["trainer_name"] == name for m in data["moduleinfo"]) or \
            any(t["trainer_name"] == name for t in data["trainer_list"])
        if not known:
            return print("Trainer name not found.")
        data["moduleinfo"] = [m for m in data["moduleinfo"] if m["trainer_name"] != name]
        data["trainer_list"] = [t for t in data["trainer_list"] if t["trainer_name"] != name]
        print(f"Trainer '{name}' deleted along with their modules.")
    save(data)


def create_module():
    data = load()
    module, trainer, level = ask("Module name: "), ask("Trainer username: "), ask("Level: ")
    if not (module and level):
        return print("Module name and level are required.")
    if not any(u["username"] == trainer and u["role"] == "Trainer" for u in data["users"]):
        return print("No Trainer account with that username.")
    data["moduleinfo"].append({"module_name": module, "trainer_name": trainer, "level": level,
                               "class_name": TBU, "schedule": TBU, "charges": TBU})
    save(data)
    print("The trainer has been assigned the module.")


def view_monthly_income():
    data = load()
    trainer, module = ask("Trainer name: "), ask("Module name: ")
    level, class_name = ask("Level: "), ask("Class name: ")
    entry = find_class(data, module, level, class_name)
    if entry is None or entry["trainer_name"] != trainer:
        return print("Record not found.")
    if entry["charges"] == TBU:
        return print("The charges haven't been set by the trainer.")
    count = sum(1 for t in data["trainerview"] if t["trainer_name"] == trainer
                and t["module_name"] == module and t["class_name"] == class_name and t["level"] == level)
    print(f"Students who paid for this class: {count}\nMonthly income: {float(entry['charges']) * count:,.2f}")


def read_feedback():
    feedback = load()["feedback"]
    if not feedback:
        return print("No feedback yet.")
    for f in feedback:
        print(f"Trainer: {f['trainer_name']}\nModule: {f['module']}\nClass: {f['class']}\n"
              f"Student: {f['student']}\nFeedback: {f['feedback']}\n------------")


def administrator(user):
    menu("Admin Menu", [
        ("Register or delete a trainer", manage_trainers),
        ("Create a module and assign a trainer", create_module),
        ("View monthly income", view_monthly_income),
        ("View feedback sent by trainers", read_feedback),
        ("Update profile", lambda: update_profile(user)),
        ("Logout", None)])


# ---------- trainer ----------
def edit_class(user, field, adding):
    """Add (placeholder only) or update class_name / charges / schedule on one of the trainer's classes."""
    data = load()
    module, level = ask("Module name: "), ask("Level: ")
    class_name = None if (field == "class_name" and adding) else ask("Class name: ")
    for m in data["moduleinfo"]:
        if m["trainer_name"] != user["username"] or m["module_name"] != module or m["level"] != level:
            continue
        if class_name is not None and m["class_name"] != class_name:
            continue
        if adding and m[field] != TBU:
            continue
        if field == "charges":
            m[field] = str(ask_amount("Charges: "))
        elif field == "schedule":
            m[field] = ask("Schedule ('Day: Timing, Day: Timing, ...'): ")
        else:
            m[field] = ask("Class name: ")
        save(data)
        return print("Saved.")
    print("No matching class assigned to you, or it was already set (use update instead).")


def class_info_menu(user, adding):
    verb = "Add" if adding else "Update"
    menu(f"{verb} class info", [
        (f"{verb} class name", lambda: edit_class(user, "class_name", adding)),
        (f"{verb} charges", lambda: edit_class(user, "charges", adding)),
        (f"{verb} schedule", lambda: edit_class(user, "schedule", adding)),
        ("Back", None)])


def view_students(user):
    data = load()
    module, level, class_name = ask("Module name: "), ask("Level: "), ask("Class name: ")
    names = [t["Student Name"] for t in data["trainerview"] if t["trainer_name"] == user["username"]
             and t["module_name"] == module and t["level"] == level and t["class_name"] == class_name]
    if not names:
        return print("No paid students found for that class.")
    print("Students who paid for this class:")
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")


def add_class(user):
    data = load()
    module, level = ask("Module name: "), ask("Level: ")
    if not any(m["trainer_name"] == user["username"] and m["module_name"] == module
               and m["level"] == level for m in data["moduleinfo"]):
        return print("That module and level are not assigned to you.")
    data["moduleinfo"].append({"trainer_name": user["username"], "module_name": module, "level": level,
                               "class_name": ask("New class name: "), "schedule": TBU, "charges": TBU})
    save(data)
    print("New class added.")


def send_feedback(user):
    data = load()
    data["feedback"].append({
        "trainer_name": user["username"],
        "feedback": ask("Feedback: "),
        "module": ask("Module the feedback is about: "),
        "class": ask("Class name: "),
        "student": ask("Student name (or 'all' for the whole class): ")})
    save(data)
    print("Your feedback has been recorded.")


def trainer(user):
    def header():
        print("\nYour modules:\n")
        mine = [m for m in load()["moduleinfo"] if m["trainer_name"] == user["username"]]
        for m in mine:
            show_module(m)
        if not mine:
            print("You haven't been assigned any module.")

    menu("Trainer Menu", [
        ("Add class info", lambda: class_info_menu(user, True)),
        ("Update class info", lambda: class_info_menu(user, False)),
        ("View students who paid for a class", lambda: view_students(user)),
        ("Send feedback to the administrator", lambda: send_feedback(user)),
        ("Update profile", lambda: update_profile(user)),
        ("Add a class within a module", lambda: add_class(user)),
        ("Logout", None)], header)


# ---------- lecturer ----------
def manage_student_list():
    print("1. Add student to the list\n2. Delete student from the list\n3. Back")
    choice = ask_int("Choose: ", (1, 2, 3))
    if choice == 3:
        return
    data = load()
    name = ask("Student name: ")
    if choice == 1:
        if not name:
            return print("Name cannot be empty.")
        data["studentlist"].append({"student_name": name})
        print("Student added to the list.")
    else:
        if not any(s["student_name"] == name for s in data["studentlist"]):
            return print("That student is not in the list.")
        data["studentlist"] = [s for s in data["studentlist"] if s["student_name"] != name]
        print("Student deleted from the list.")
    save(data)


def enroll_student():
    data = load()
    name = ask("Student username: ")
    module, level, class_name = ask("Module: "), ask("Level: "), ask("Class name: ")
    entry = find_class(data, module, level, class_name)
    if entry is None:
        return print("That module/level/class does not exist.")
    data["enroll_student"].append({
        "student_name": name, "module_name": module, "level": level,
        "tp number": ask("TP number: "), "class_name": class_name, "gmail": ask("Student's gmail: "),
        "contact": ask("Contact number: "), "month_of_enrollement": ask("Month of enrolment: "),
        "fees": "unpaid", "trainer_name": entry["trainer_name"]})
    save(data)
    print("The student has been enrolled.")


def update_enrollment():
    data = load()
    name = ask("Student username: ")
    rows = [e for e in data["enroll_student"] if e["student_name"] == name]
    if not rows:
        return print("The student record doesn't exist.")
    for i, e in enumerate(rows, 1):
        print(f"{i}. {e['module_name']} | level {e['level']} | class {e['class_name']}")
    n = ask_int("Which enrolment to change (0 to cancel): ", range(0, len(rows) + 1))
    if n == 0:
        return
    row = rows[n - 1]
    module, level, class_name = ask("New module: "), ask("New level: "), ask("New class name: ")
    entry = find_class(data, module, level, class_name)
    if entry is None:
        return print("That module/level/class does not exist.")
    row.update(module_name=module, level=level, class_name=class_name, trainer_name=entry["trainer_name"])
    save(data)
    print("The enrolment has been updated.")


def review_requests():
    data = load()
    requests = data["request_status"]
    if not requests:
        return print("No requests.")
    for i, r in enumerate(requests, 1):
        print(f"{i}. {r['Student_name']} | {r['module_name']} | level {r['level']} | {r['Status']}")
    n = ask_int("Request to review (0 to cancel): ", range(0, len(requests) + 1))
    if n == 0:
        return
    decision = ask_int("1 approve, 2 reject: ", (1, 2))
    requests[n - 1]["Status"] = "approved" if decision == 1 else "rejected"
    save(data)
    print(f"Request {requests[n - 1]['Status']}.")


def delete_enrolment_by_tp():
    data = load()
    tp = ask("TP number of the student to remove: ")
    kept = [e for e in data["enroll_student"] if e["tp number"] != tp]
    if len(kept) == len(data["enroll_student"]):
        return print("The TP number doesn't exist.")
    data["enroll_student"] = kept
    save(data)
    print("The student has been removed from their enrolments.")


def lecturer(user):
    def header():
        print("\nAll modules:\n")
        for m in load()["moduleinfo"]:
            show_module(m, with_trainer=True)

    menu("Lecturer Menu", [
        ("Add or delete a student in the student list", manage_student_list),
        ("Enroll a student into a module", enroll_student),
        ("Update a student's enrolment", update_enrollment),
        ("Approve or reject coaching requests", review_requests),
        ("Remove a student's enrolment by TP number", delete_enrolment_by_tp),
        ("Update profile", lambda: update_profile(user)),
        ("Logout", None)], header)


# ---------- student ----------
def send_request(user):
    data = load()
    module, level = ask("Module to request: "), ask("Level: ")
    if not any(m["module_name"] == module and m["level"] == level for m in data["moduleinfo"]):
        return print("That module/level does not exist.")
    if any(r["Student_name"] == user["username"] and r["module_name"] == module and r["level"] == level
           and r["Status"] == "pending" for r in data["request_status"]):
        return print("You already have a pending request for that module.")
    data["request_status"].append({"Student_name": user["username"], "module_name": module,
                                   "level": level, "Status": "pending"})
    save(data)
    print("Your request has been registered; the lecturer may or may not enrol you.")


def view_request_status(user):
    mine = [r for r in load()["request_status"] if r["Student_name"] == user["username"]]
    if not mine:
        return print("No requests found.")
    for r in mine:
        print(f"{r['module_name']} (level {r['level']}): {r['Status']}")


def delete_request(user):
    data = load()
    module, level = ask("Module of the request: "), ask("Level: ")
    for r in data["request_status"]:
        if r["Student_name"] == user["username"] and r["module_name"] == module and r["level"] == level:
            if r["Status"] != "pending":
                return print("The request is not pending; it was already approved or rejected.")
            data["request_status"].remove(r)
            save(data)
            return print("The request has been deleted.")
    print("Request not found.")


def my_enrolments(data, user):
    return [e for e in data["enroll_student"] if e["student_name"] == user["username"]]


def view_schedule(user):
    data = load()
    rows = my_enrolments(data, user)
    if not rows:
        return print(f"{user['username']} is not enrolled in any modules.")
    for e in rows:
        m = find_class(data, e["module_name"], e["level"], e["class_name"])
        print(f"{e['module_name']} - {e['class_name']}: {m['schedule'] if m else 'class no longer exists'}")


def view_invoice(user):
    data = load()
    rows = my_enrolments(data, user)
    if not rows:
        return print(f"{user['username']} is not enrolled in any modules.")
    due, total = [], 0.0
    for e in rows:
        m = find_class(data, e["module_name"], e["level"], e["class_name"])
        charges = m["charges"] if m else TBU
        print(f"{e['module_name']} - {e['class_name']}: {charges} ({e['fees']})")
        if e["fees"] != "paid" and charges != TBU:
            due.append(e)
            total += float(charges)
    print(f"Total due: {total:,.2f}")
    if not due or ask_int("1 to pay now, 2 to go back: ", (1, 2)) == 2:
        return
    print("----- INVOICE -----\nBank: Maybank, Pavilion Bukit Jalil, Kuala Lumpur\n"
          f"Payer: {user['username']}\nReceiver: Asia Pacific University")
    if ask_int("1 to confirm payment, 2 to cancel: ", (1, 2)) == 2:
        return print("Payment cancelled.")
    for e in due:  # only unpaid classes, so paying twice never double-counts income
        e["fees"] = "paid"
        data["trainerview"].append({"Student Name": user["username"], "module_name": e["module_name"],
                                    "level": e["level"], "class_name": e["class_name"],
                                    "trainer_name": e["trainer_name"]})
    save(data)
    print("Your fees have been paid successfully.")


def student(user):
    menu("Student Menu", [
        ("Send a request", lambda: send_request(user)),
        ("View request status", lambda: view_request_status(user)),
        ("Delete a pending request", lambda: delete_request(user)),
        ("View schedule", lambda: view_schedule(user)),
        ("View invoice and pay", lambda: view_invoice(user)),
        ("Update profile", lambda: update_profile(user)),
        ("Logout", None)])


ROLE_MENUS = {"administrator": administrator, "trainer": trainer, "lecturer": lecturer, "student": student}


def main():
    migrate()
    try:
        while True:
            print("\n1. Login\n2. Create account\n3. Quit")
            choice = ask_int("Choose: ", (1, 2, 3))
            if choice == 3:
                break
            if choice == 2:
                create_account()
            else:
                user = login()
                if user:
                    ROLE_MENUS[user["role"].lower()](user)
    except (EOFError, KeyboardInterrupt):
        print()
    print("Goodbye.")


if __name__ == "__main__":
    main()
