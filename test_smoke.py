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


# first run bootstraps an administrator; staff accounts are then created from the admin menu
run("ann", "pw", "KL", "5", "30", "3")
run("1", "ann", "pw", "5", "tom", "pw", "2", "KL", "5", "30", "5", "lee", "pw", "3", "KL", "5", "30", "7", "3")
# self-registration only creates students (no role prompt)
run("2", "sam", "pw", "KL", "Foundation", "30", "3")
assert {u["username"]: u["role"] for u in ts.load()["users"]} == {
    "ann": "Administrator", "tom": "Trainer", "lee": "Lecturer", "sam": "Student"}

# admin makes a module for tom; tom names the class and sets charges and schedule
run("1", "ann", "pw", "2", "Maths", "tom", "L1", "7", "3")
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
run("1", "ann", "pw", "3", "tom", "Maths", "L1", "A", "7", "3")
# wrong password is rejected three times and returns to the main menu
run("1", "ann", "x", "ann", "x", "ann", "x", "3")
print("smoke test passed")
