# ============================================================
# create.py — New Identity Registration
# University Identity Management System
# ============================================================

import re
from datetime import date
from db import get_connection
from utils import (
    TYPE_LABELS, MIN_AGE, HIGH_SCHOOL_TYPES, HONORS_LIST, ACADEMIC_STATUSES,
    FACULTIES, DEPARTMENTS, GROUPS, FACULTY_RANKS, EMPLOYMENT_CATS,
    CONTRACT_TYPES, STAFF_GRADES,
    header, success_box, is_valid_date, calc_age, generate_id, log_history,
    ask, ask_optional, choose, yes_no, ask_year, ask_date, ask_date_optional, pause,
    letters_only,
)


# ═══════════════════════════════════════════════════════════
# MAIN ENTRY
# ═══════════════════════════════════════════════════════════
def create_identity():
    header("NEW IDENTITY REGISTRATION")

    print("\n  Select person type:")
    print("    1. Student")
    print("    2. PhD Student")
    print("    3. Faculty Member")
    print("    4. Staff")
    print("    5. Temporary Staff")
    print("    0. Back to Menu")

    choice = input("\n  Choice: ").strip()
    type_map = {"1": "STU", "2": "PHD", "3": "FAC", "4": "STF", "5": "TMP"}

    if choice == "0":
        return
    if choice not in type_map:
        print("  ✗ Invalid choice.")
        return create_identity()

    type_code = type_map[choice]
    print(f"\n  → Creating: {TYPE_LABELS[type_code]}")
    _collect_common(type_code)


# ═══════════════════════════════════════════════════════════
# STEP 1 — COMMON DATA
# ═══════════════════════════════════════════════════════════
def _collect_common(type_code):
    header("COMMON INFORMATION")
    d = {}

    d["first_name"] = ask(
        "First Name",
        lambda v: "Minimum 2 characters." if len(v) < 2 else (letters_only(v)),
    )
    d["last_name"] = ask(
        "Last Name",
        lambda v: "Minimum 2 characters." if len(v) < 2 else (letters_only(v)),
    )

    # Date of birth
    while True:
        dob = ask_date("Date of Birth")
        age = calc_age(dob)
        if age < MIN_AGE[type_code]:
            print(f"  ✗ Minimum age for {TYPE_LABELS[type_code]} is {MIN_AGE[type_code]}.")
            continue
        break
    d["dob"]        = dob
    d["birth_year"] = int(dob.split("-")[0])

    d["place"]       = ask("Place of Birth", letters_only)
    d["nationality"] = ask("Nationality", letters_only)

    # Gender
    d["gender"] = ask(
        "Gender (M / F)",
        lambda v: None if v.upper() in ("M", "F") else "Please enter M or F.",
    ).upper()

    # Email (unique check)
    while True:
        email = ask(
            "Personal Email",
            lambda v: None if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v) else "Invalid email format.",
        )
        conn = get_connection()
        row  = conn.execute("SELECT id FROM person WHERE email = ?", (email,)).fetchone()
        conn.close()
        if row:
            print("  ✗ Email already in use.")
            continue
        break
    d["email"] = email

    d["phone"] = ask(
        "Phone Number (digits only, 9–15 digits)",
        lambda v: None if re.match(r"^\d{9,15}$", v) else "Only digits, 9–15 characters.",
    )

    # Duplicate check
    conn = get_connection()
    dup  = conn.execute(
        "SELECT id FROM person WHERE first_name = ? AND last_name = ? AND date_of_birth = ?",
        (d["first_name"], d["last_name"], d["dob"]),
    ).fetchone()
    conn.close()

    if dup:
        print("\n  ✗ DUPLICATE DETECTED: A person with the same name and date of birth already exists.")
        return

    _save_person(type_code, d)


# ═══════════════════════════════════════════════════════════
# INSERT PERSON → ROUTE TO TYPE-SPECIFIC
# ═══════════════════════════════════════════════════════════
def _save_person(type_code, d):
    conn = get_connection()
    try:
        new_id = generate_id(conn, type_code)
    except ValueError as e:
        print(f"\n  ✗ {e}")
        conn.close()
        return

    conn.execute(
        """INSERT INTO person
               (unique_identifier, type, status, first_name, last_name,
                date_of_birth, place_of_birth, nationality, gender, email, phone)
           VALUES (?, ?, 'Pending', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, type_code, d["first_name"], d["last_name"], d["dob"],
         d["place"], d["nationality"], d["gender"], d["email"], d["phone"]),
    )
    person_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    log_history(conn, person_id, "CREATE", note=f"New {TYPE_LABELS[type_code]} created")
    conn.commit()
    conn.close()

    if type_code in ("STU", "PHD"):
        _collect_student(person_id, new_id, d)
    elif type_code == "FAC":
        _collect_faculty(person_id, new_id, d)
    elif type_code in ("STF", "TMP"):
        _collect_staff(person_id, new_id, d)
    else:
        success_box(new_id, f"{d['first_name']} {d['last_name']}")
    pause()


# ═══════════════════════════════════════════════════════════
# STEP 2A — STUDENT / PHD DATA
# ═══════════════════════════════════════════════════════════
def _collect_student(person_id, new_id, d):
    header("ACADEMIC INFORMATION")
    s = {}
    current_year = date.today().year

    s["hs_type"]   = choose("High School Type", HIGH_SCHOOL_TYPES)
    s["hs_year"]   = ask_year(
        "High School Graduation Year",
        min_year=d["birth_year"] + 17,
        max_year=current_year,
    )
    s["hs_honors"] = choose("High School Honors", HONORS_LIST)
    s["major"]     = ask("Chosen Major / Program")
    s["entry_year"] = ask_year(
        "Entry Year",
        min_year=s["hs_year"],
        max_year=current_year,
    )
    s["faculty"]         = choose("Faculty", FACULTIES)
    s["department"]      = choose("Department", DEPARTMENTS)
    s["group"]           = choose("Group", GROUPS)

    header("FINANCIAL INFORMATION")
    s["scholarship"] = "yes" if yes_no("Scholarship") else "no"

    conn = get_connection()
    conn.execute(
        """INSERT INTO student
               (person_id, high_school_type, high_school_year, high_school_honors,
                major, entry_year, academic_status, faculty, department, group_name, scholarship)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (person_id, s["hs_type"], s["hs_year"], s["hs_honors"], s["major"],
         s["entry_year"], "Active", s["faculty"], s["department"],
         s["group"], s["scholarship"]),
    )
    conn.commit()
    conn.close()
    success_box(new_id, f"{d['first_name']} {d['last_name']}")
    pause()


# ═══════════════════════════════════════════════════════════
# STEP 2B — FACULTY DATA
# ═══════════════════════════════════════════════════════════
def _collect_faculty(person_id, new_id, d):
    header("PROFESSIONAL INFORMATION")
    f = {}

    f["rank"]        = choose("Rank", FACULTY_RANKS)
    f["emp_cat"]     = choose("Employment Category", EMPLOYMENT_CATS)
    # Must be after DOB + min age (25 for FAC)
    appt_min = f"{d['birth_year'] + 25}-01-01"
    f["appt_start"]  = ask_date("Appointment Start Date", min_date=appt_min)
    f["primary_dept"] = choose("Primary Department", DEPARTMENTS)
    f["secondary"]   = ask_optional("Secondary Departments (comma-separated)")

    print("\n  Office Location:")
    f["bldg"]  = ask_optional("  Building")
    f["floor"] = ask_optional("  Floor")
    f["room"]  = ask_optional("  Room Number")

    f["phd_inst"] = ask_optional("PhD Institution")
    f["research"] = ask_optional("Research Areas (comma-separated)")
    f["hdr"]      = 1 if yes_no("Habilitation to Supervise Research (HDR)") else 0

    header("CONTRACT INFORMATION")
    f["contract_type"]  = choose("Contract Type", CONTRACT_TYPES)
    f["contract_start"] = ask_date("Contract Start Date", min_date=f["appt_start"])
    f["contract_end"]   = ask_date_optional("Contract End Date (leave blank for open-ended)", min_date=f["contract_start"])

    while True:
        raw = input("  Weekly Teaching Hours: ").strip()
        try:
            h = float(raw)
            if h >= 0:
                f["teaching_h"] = h
                break
        except ValueError:
            pass
        print("  ✗ Must be a positive number.")

    conn = get_connection()
    conn.execute(
        """INSERT INTO faculty
               (person_id, rank, employment_category, appointment_start,
                primary_department, secondary_departments,
                office_building, office_floor, office_room,
                phd_institution, research_areas, hdr,
                contract_type, contract_start, contract_end, teaching_hours)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (person_id, f["rank"], f["emp_cat"], f["appt_start"],
         f["primary_dept"], f["secondary"],
         f["bldg"], f["floor"], f["room"],
         f["phd_inst"], f["research"], f["hdr"],
         f["contract_type"], f["contract_start"], f["contract_end"], f["teaching_h"]),
    )
    conn.commit()
    conn.close()
    success_box(new_id, f"{d['first_name']} {d['last_name']}")
    pause()


# ═══════════════════════════════════════════════════════════
# STEP 2C — STAFF / TEMPORARY DATA
# ═══════════════════════════════════════════════════════════
def _collect_staff(person_id, new_id, d):
    header("STAFF INFORMATION")
    s = {}

    s["dept"]       = choose("Assigned Department / Service", DEPARTMENTS)
    s["title"]      = ask("Job Title")
    s["grade"]      = choose("Grade", STAFF_GRADES)
    entry_min = f"{d['birth_year'] + 18}-01-01"
    s["entry_date"] = ask_date("Date of Entry to University", min_date=entry_min)

    conn = get_connection()
    conn.execute(
        """INSERT INTO staff (person_id, department, job_title, grade, entry_date)
           VALUES (?, ?, ?, ?, ?)""",
        (person_id, s["dept"], s["title"], s["grade"], s["entry_date"]),
    )
    conn.commit()
    conn.close()
    success_box(new_id, f"{d['first_name']} {d['last_name']}")
    pause()