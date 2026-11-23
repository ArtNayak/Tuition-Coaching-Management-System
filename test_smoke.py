"""End-to-end smoke test: python test_smoke.py (uses a temporary database, not za.json)."""
import builtins
import os
import tempfile

import tuition_system as ts

ts.DB_FILE = os.path.join(tempfile.mkdtemp(), "test.json")


def run(*answers):
    it = iter(answers)
    builtins.input = lambda prompt="": next(it)
    ts.main()


# create one account per role (role numbers: 1 admin, 2 trainer, 3 lecturer, 4 student)
for name, role, extra in [("ann", "1", "5"), ("tom", "2", "5"), ("lee", "3", "5"), ("sam", "4", "Foundation")]:
    run("2", name, "pw", role, "KL", extra, "30", "3")

# admin makes a module for tom; tom names the class and sets charges and schedule
run("1", "ann", "pw", "2", "Maths", "tom", "L1", "6", "3")
run("1", "tom", "pw", "1", "1", "Maths", "L1", "A", "2", "Maths", "L1", "A", "250",
    "3", "Maths", "L1", "A", "Mon: 5pm", "4", "7", "3")
# lecturer enrols sam; sam pays twice (second time nothing is due)
run("1", "lee", "pw", "2", "sam", "Maths", "L1", "A", "TP1", "s@x.com", "123", "Jan", "7", "3")
run("1", "sam", "pw", "5", "1", "1", "5", "7", "3")
# admin income must count sam once: 250.00
data = ts.load()
assert len(data["trainerview"]) == 1, data["trainerview"]
assert data["enroll_student"][0]["fees"] == "paid"
assert all(u["password"].startswith("pbkdf2$") for u in data["users"])
run("1", "ann", "pw", "3", "tom", "Maths", "L1", "A", "6", "3")
# wrong password is rejected three times and returns to the main menu
run("1", "ann", "x", "ann", "x", "ann", "x", "3")
print("smoke test passed")
