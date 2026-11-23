# Tuition & Coaching Centre Management System

A command-line system in Python for running a tuition/coaching centre, with four roles. Data is kept in a local JSON file, and passwords are stored as salted PBKDF2 hashes. It uses only the Python standard library (3.8+).

## Roles
- **Administrator** – register or delete trainers, create modules and assign trainers, view monthly income per class, read trainer feedback.
- **Trainer** – set and update class names, charges and schedules, add classes to a module, see which students paid, send feedback to the admin.
- **Lecturer** – manage the student list, enrol students into classes, change enrolments, approve or reject coaching requests, remove enrolments by TP number.
- **Student** – request a module, track or delete pending requests, view their schedule, view the invoice and pay.

Anyone can self-register, but only as a **Student**. The first run asks you to create the first Administrator, and administrators create Trainer, Lecturer and further Administrator accounts from their menu. Everyone can update their profile later (including their password).

## Run
```
python tuition_system.py
```
`za.json` is created on first run next to the script and is not committed (it holds user data). On first run you create the administrator, then log in and add a Trainer and a Lecturer from the admin menu, and register a Student from the main menu.

A student's enrolment is matched by username, so when a lecturer enrols a student, use the student's account username.

Run the end-to-end check (uses a temporary database): `python test_smoke.py`

## Notes
Originally a group assignment. The original version was a single script with plain-text passwords and recursive menus. This version uses loop-based menus, hashed passwords (an existing `za.json` with plain-text passwords is migrated automatically on first start), input validation and safer deletes. Paying an invoice twice no longer double-counts a trainer's income.
