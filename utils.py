# ============================================================
# utils.py — Shared Helpers
# University Identity Management System
# ============================================================

import re
from datetime import date, datetime

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
TYPE_LABELS = {
    "STU": "Student",
    "PHD": "PhD Student",
    "FAC": "Faculty",
    "STF": "Staff",
    "TMP": "Temporary Staff",
}

ID_LIMITS = {"STU": 15000, "PHD": 1000, "FAC": 1200, "STF": 800, "TMP": 500}
MIN_AGE   = {"STU": 16, "PHD": 23, "FAC": 25, "STF": 18, "TMP": 18}

HIGH_SCHOOL_TYPES = [
    "Scientific", "Mathematics", "Technical",
    "Literature", "Foreign Languages", "Economics and Management",
]
HONORS_LIST       = ["None", "Passable", "Good", "Very Good", "Excellent"]
ACADEMIC_STATUSES = ["Active", "Suspended", "Graduated", "Expelled"]
FACULTIES         = [
    "Faculty of Computer Science", "Faculty of Engineering",
    "Faculty of Mathematics", "Faculty of Economics", "Faculty of Law",
]
DEPARTMENTS       = [
    "Computer Science", "Software Engineering", "Cyber Security",
    "Artificial Intelligence", "Data Science", "Networks",
]
GROUPS            = ["G1", "G2", "G3", "G4", "G5"]
FACULTY_RANKS     = [
    "Professor", "Associate Professor", "Assistant Professor",
    "Lecturer", "Teaching Assistant",
]
EMPLOYMENT_CATS   = ["Permanent", "Contractual", "Visiting", "Part-Time"]
CONTRACT_TYPES    = ["Permanent", "Fixed-Term", "Part-Time", "Temporary Mission"]
STAFF_GRADES      = ["Grade A", "Grade B", "Grade C", "Grade D"]

STATUS_TRANSITIONS = {
    "Pending":   ["Active"],
    "Active":    ["Suspended", "Inactive"],
    "Suspended": ["Active"],
    "Inactive":  ["Archived"],
    "Archived":  [],
}

STATUS_DESCRIPTIONS = {
    "Active":    "Operational account — full access",
    "Suspended": "Temporary block (incident, non-payment, etc.)",
    "Inactive":  "No longer affiliated (graduated, resigned, etc.)",
    "Archived":  "Legal retention — account closed",
}

# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────
def sep(char="─", length=60):
    return char * length

def header(title):
    line = sep("─", 54)
    print(f"\n{line}")
    print(f"  {title}")
    print(line)

def success_box(new_id, full_name=""):
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║   ✓  IDENTITY CREATED SUCCESSFULLY  ║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  Name         : {full_name:<21}║")
    print(f"  ║  Generated ID : {new_id:<21}║")
    print(f"  ║  Status       : {'Pending':<21}║")
    print("  ╚══════════════════════════════════════╝\n")

# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────
def is_valid_date(s):
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").date()
        return dt <= date.today()
    except ValueError:
        return False

def calc_age(dob_str):
    born  = datetime.strptime(dob_str, "%Y-%m-%d").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def generate_id(conn, type_code):
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM person WHERE type = ?", (type_code,)
    ).fetchone()
    count = row["cnt"] + 1
    if count > ID_LIMITS[type_code]:
        raise ValueError(f"ID limit reached for {type_code} (max: {ID_LIMITS[type_code]})")
    year = date.today().year
    return f"{type_code}{year}{count:05d}"

def log_history(conn, person_id, action, field=None, old_val=None, new_val=None, note=None):
    conn.execute(
        """INSERT INTO history (person_id, action, field_name, old_value, new_value, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (person_id, action, field, str(old_val) if old_val is not None else None,
         str(new_val) if new_val is not None else None, note),
    )

# ─────────────────────────────────────────────
# VALIDATORS
# ─────────────────────────────────────────────
def letters_only(v):
    """Allow letters (any language), spaces, hyphens, apostrophes only."""
    if not re.match(r"^[\w\s\-']+$", v, re.UNICODE) or v.isdigit():
        return "This field must contain letters only, no numbers."
    if any(c.isdigit() for c in v):
        return "This field must contain letters only, no numbers."
    return None

# ─────────────────────────────────────────────
# INPUT HELPERS
# ─────────────────────────────────────────────
def ask(prompt, validate=None, allow_empty=False):
    """Ask for text input with optional validation. Returns stripped string."""
    while True:
        raw = input(f"  {prompt}: ").strip()
        if not raw and not allow_empty:
            print("  ✗ This field is required.")
            continue
        if validate:
            err = validate(raw)
            if err:
                print(f"  ✗ {err}")
                continue
        return raw

def ask_optional(prompt):
    """Ask for optional input. Returns value or None."""
    raw = input(f"  {prompt} (press Enter to skip): ").strip()
    return raw if raw else None

def choose(title, items):
    """Show numbered list, return chosen item. No skip allowed."""
    print(f"\n  {title}:")
    for i, item in enumerate(items, 1):
        print(f"    {i:2}. {item}")
    while True:
        raw = input("  Choice: ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                print(f"  ✓ {items[idx]}")
                return items[idx]
        except ValueError:
            pass
        print("  ✗ Invalid selection.")

def choose_optional(title, items):
    """Show numbered list with skip option. Returns item or None."""
    print(f"\n  {title}:")
    for i, item in enumerate(items, 1):
        print(f"    {i:2}. {item}")
    print(f"    {'0':>3}. Skip")
    while True:
        raw = input("  Choice: ").strip()
        if raw == "0":
            return None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        print("  ✗ Invalid selection.")

def yes_no(prompt):
    """Ask yes/no question. Returns bool."""
    while True:
        raw = input(f"  {prompt} (yes/no): ").strip().lower()
        if raw in ("yes", "y"):
            return True
        if raw in ("no", "n"):
            return False
        print("  ✗ Please type yes or no.")

def ask_year(prompt, min_year=None, max_year=None):
    """Ask for a 4-digit year within optional bounds."""
    while True:
        raw = input(f"  {prompt} (YYYY): ").strip()
        if not raw.isdigit() or len(raw) != 4:
            print("  ✗ Must be a 4-digit year.")
            continue
        y = int(raw)
        if min_year and y < min_year:
            print(f"  ✗ Year must be at least {min_year}.")
            continue
        if max_year and y > max_year:
            print(f"  ✗ Year cannot exceed {max_year}.")
            continue
        return y

def ask_date(prompt, min_date=None, max_date=None, allow_future=False):
    """
    Ask for a YYYY-MM-DD date with optional min/max bounds.
    min_date / max_date : 'YYYY-MM-DD' strings or date objects.
    allow_future        : if True, dates after today are accepted.
    """
    while True:
        raw = input(f"  {prompt} (YYYY-MM-DD): ").strip()
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  ✗ Invalid format. Use YYYY-MM-DD (e.g. 2003-05-21).")
            continue
        if not allow_future and parsed > date.today():
            print("  ✗ Date cannot be in the future.")
            continue
        if min_date:
            min_d = datetime.strptime(min_date, "%Y-%m-%d").date() if isinstance(min_date, str) else min_date
            if parsed < min_d:
                print(f"  ✗ Date must be on or after {min_d}.")
                continue
        if max_date:
            max_d = datetime.strptime(max_date, "%Y-%m-%d").date() if isinstance(max_date, str) else max_date
            if parsed > max_d:
                print(f"  ✗ Date must be on or before {max_d}.")
                continue
        return raw

def ask_date_optional(prompt, min_date=None):
    """
    Ask for optional YYYY-MM-DD date. Loops until valid or blank.
    Returns value string or None if skipped.
    """
    while True:
        raw = input(f"  {prompt} (YYYY-MM-DD, or Enter to skip): ").strip()
        if not raw:
            return None
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  ✗ Invalid format. Use YYYY-MM-DD.")
            continue
        if min_date:
            min_d = datetime.strptime(min_date, "%Y-%m-%d").date() if isinstance(min_date, str) else min_date
            if parsed < min_d:
                print(f"  ✗ Date must be on or after {min_d}.")
                continue
        return raw

def pause():
    input("\n  Press Enter to return to menu...")