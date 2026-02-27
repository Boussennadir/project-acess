# ============================================================
# create.py — New Identity Registration
# University Identity Management System
# ============================================================

import re
from datetime import date
from db import get_connection
from utils import (
    CATEGORIES, TYPE_LABELS, MIN_AGE, PHD_SUBCATS, SUBCAT_PREFIX,
    HIGH_SCHOOL_TYPES, HONORS_LIST, FACULTY_CATALOG, FACULTIES, DEPARTMENTS, GROUPS,
    FACULTY_RANKS, EMPLOYMENT_CATS, CONTRACT_TYPES, STAFF_GRADES,
    header, success_box, is_valid_date, calc_age, generate_id, log_history,
    ask, ask_optional, choose, yes_no, ask_year, ask_date, ask_date_optional,
    pause, letters_only,
)


# ═══════════════════════════════════════════════════════════
# STEP 0 — SELECT CATEGORY → SUB-CATEGORY
# ═══════════════════════════════════════════════════════════
def create_identity():
    header("NEW IDENTITY REGISTRATION")

    cat_keys  = list(CATEGORIES.keys())
    cat_names = [CATEGORIES[k]["label"] for k in cat_keys]

    print("\n  Select Category:")
    for i, name in enumerate(cat_names, 1):
        print(f"    {i}. {name}")
    print("    0. Back to Menu")

    raw = input("\n  Choice: ").strip()
    if raw == "0":
        return
    try:
        cat_code = cat_keys[int(raw) - 1]
    except (ValueError, IndexError):
        print("  ✗ Invalid choice.")
        return create_identity()

    subcats = CATEGORIES[cat_code]["subcategories"]
    print(f"\n  Select Sub-category ({CATEGORIES[cat_code]['label']}):")
    for i, sc in enumerate(subcats, 1):
        print(f"    {i}. {sc}")
    print("    0. Back")

    raw = input("\n  Choice: ").strip()
    if raw == "0":
        return create_identity()
    try:
        sub_cat = subcats[int(raw) - 1]
    except (ValueError, IndexError):
        print("  ✗ Invalid choice.")
        return create_identity()

    print(f"\n  Creating: {CATEGORIES[cat_code]['label']} — {sub_cat}")
    _collect_common(cat_code, sub_cat)


# ═══════════════════════════════════════════════════════════
# STEP 1 — COMMON DATA
# ═══════════════════════════════════════════════════════════
def _collect_common(cat_code, sub_cat):
    header("COMMON INFORMATION")
    d = {}

    d["first_name"] = ask(
        "First Name",
        lambda v: "Minimum 2 characters." if len(v) < 2 else letters_only(v),
    )
    d["last_name"] = ask(
        "Last Name",
        lambda v: "Minimum 2 characters." if len(v) < 2 else letters_only(v),
    )

    min_age = 23 if sub_cat in PHD_SUBCATS else MIN_AGE.get(cat_code, 16)

    while True:
        dob = ask_date("Date of Birth")
        if calc_age(dob) < min_age:
            print(f"  ✗ Minimum age for {sub_cat} is {min_age}.")
            continue
        break
    d["dob"]        = dob
    d["birth_year"] = int(dob.split("-")[0])

    d["place"]       = ask("Place of Birth", letters_only)
    d["nationality"] = ask("Nationality",    letters_only)
    d["gender"]      = ask(
        "Gender (M / F)",
        lambda v: None if v.upper() in ("M", "F") else "Please enter M or F.",
    ).upper()

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

    # Phone — unique check
    while True:
        phone = ask(
            "Phone Number (digits only, 9-15 digits)",
            lambda v: None if re.match(r"^\d{9,15}$", v) else "Only digits, 9-15 characters.",
        )
        conn = get_connection()
        row  = conn.execute("SELECT id FROM person WHERE phone = ?", (phone,)).fetchone()
        conn.close()
        if row:
            print("  ✗ Phone number already in use.")
            continue
        break
    d["phone"] = phone

    # Duplicate check — repeat name + DOB fields if duplicate found
    conn = get_connection()
    dup  = conn.execute(
        "SELECT id FROM person WHERE first_name=? AND last_name=? AND date_of_birth=?",
        (d["first_name"], d["last_name"], d["dob"]),
    ).fetchone()
    conn.close()
    if dup:
        print("\n  ✗ DUPLICATE DETECTED: a person with the same full name and date of birth already exists.")
        print("  Please re-enter the correct name and date of birth.\n")
        # Re-ask only name + DOB, keep the rest
        d["first_name"] = ask(
            "First Name",
            lambda v: "Minimum 2 characters." if len(v) < 2 else letters_only(v),
        )
        d["last_name"] = ask(
            "Last Name",
            lambda v: "Minimum 2 characters." if len(v) < 2 else letters_only(v),
        )
        while True:
            dob = ask_date("Date of Birth")
            if calc_age(dob) < min_age:
                print(f"  ✗ Minimum age is {min_age}.")
                continue
            break
        d["dob"]        = dob
        d["birth_year"] = int(dob.split("-")[0])
        # Re-check duplicate with new values
        conn = get_connection()
        dup2 = conn.execute(
            "SELECT id FROM person WHERE first_name=? AND last_name=? AND date_of_birth=?",
            (d["first_name"], d["last_name"], d["dob"]),
        ).fetchone()
        conn.close()
        if dup2:
            print("  ✗ Still a duplicate. Returning to menu.")
            return

    _save_person(cat_code, sub_cat, d)


# ═══════════════════════════════════════════════════════════
# INSERT PERSON → ROUTE TO TYPE-SPECIFIC
# ═══════════════════════════════════════════════════════════
def _save_person(cat_code, sub_cat, d):
    conn = get_connection()
    try:
        new_id, prefix = generate_id(conn, sub_cat)
    except ValueError as e:
        print(f"\n  ✗ {e}")
        conn.close()
        return

    conn.execute(
        """INSERT INTO person
               (unique_identifier, type, sub_category, id_prefix, status,
                first_name, last_name, date_of_birth, place_of_birth,
                nationality, gender, email, phone)
           VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, cat_code, sub_cat, prefix,
         d["first_name"], d["last_name"], d["dob"],
         d["place"], d["nationality"], d["gender"], d["email"], d["phone"]),
    )
    person_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    log_history(conn, person_id, "CREATE",
                note=f"New {CATEGORIES[cat_code]['label']} — {sub_cat} created")
    conn.commit()
    conn.close()

    if cat_code == "STU":
        _collect_student(person_id, new_id, d, sub_cat)
    elif cat_code == "FAC":
        _collect_faculty(person_id, new_id, d, sub_cat)
    elif cat_code == "STF":
        _collect_staff(person_id, new_id, d, sub_cat)
    else:
        success_box(new_id, f"{d['first_name']} {d['last_name']}")
        pause()


# ═══════════════════════════════════════════════════════════
# STEP 2A — STUDENT DATA
# ═══════════════════════════════════════════════════════════
def _collect_student(person_id, new_id, d, sub_cat):
    header("ACADEMIC INFORMATION")
    s = {}
    current_year = date.today().year

    s["hs_type"]   = choose("High School Type", HIGH_SCHOOL_TYPES)
    s["hs_year"]   = ask_year("High School Graduation Year",
                              min_year=d["birth_year"] + 17, max_year=current_year)
    s["hs_honors"] = choose("High School Honors", HONORS_LIST)
    s["entry_year"] = ask_year("Entry Year",
                               min_year=s["hs_year"], max_year=current_year)

    # Linked Faculty → Department → Major
    s["faculty"]    = choose("Faculty", FACULTIES)
    dept_list       = list(FACULTY_CATALOG[s["faculty"]].keys())
    s["department"] = choose("Department", dept_list)
    major_list      = FACULTY_CATALOG[s["faculty"]][s["department"]]
    s["major"]      = choose("Major / Program", major_list)

    # Group only for Undergraduate and Continuing Education
    if sub_cat in ("Undergraduate", "Continuing Education"):
        s["group"] = choose("Group", GROUPS)
    else:
        s["group"] = None

    header("FINANCIAL INFORMATION")
    s["scholarship"] = "yes" if yes_no("Scholarship") else "no"

    conn = get_connection()
    conn.execute(
        """INSERT INTO student
               (person_id, high_school_type, high_school_year, high_school_honors,
                major, entry_year, academic_status, faculty, department,
                group_name, scholarship)
           VALUES (?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, ?)""",
        (person_id, s["hs_type"], s["hs_year"], s["hs_honors"], s["major"],
         s["entry_year"], s["faculty"], s["department"],
         s["group"], s["scholarship"]),
    )
    conn.commit()
    conn.close()
    success_box(new_id, f"{d['first_name']} {d['last_name']}")
    pause()


# ═══════════════════════════════════════════════════════════
# STEP 2B — FACULTY DATA
# ═══════════════════════════════════════════════════════════
def _collect_faculty(person_id, new_id, d, sub_cat):
    header("PROFESSIONAL INFORMATION")
    f = {}

    rank_options = {
        "Tenured":             ["Professor", "Associate Professor", "Assistant Professor"],
        "Adjunct / Part-time": ["Assistant Professor", "Lecturer", "Teaching Assistant"],
        "Visiting Researcher": FACULTY_RANKS,
    }
    f["rank"]        = choose("Rank", rank_options.get(sub_cat, FACULTY_RANKS))
    f["emp_cat"]     = choose("Employment Category", EMPLOYMENT_CATS)

    appt_min         = f"{d['birth_year'] + 25}-01-01"
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
    f["contract_end"]   = ask_date_optional(
        "Contract End Date (leave blank for open-ended)",
        min_date=f["contract_start"],
    )

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
# STEP 2C — STAFF DATA
# ═══════════════════════════════════════════════════════════
def _collect_staff(person_id, new_id, d, sub_cat):
    header("STAFF INFORMATION")
    s = {}

    s["dept"]       = choose("Assigned Department / Service", DEPARTMENTS)
    s["title"]      = ask("Job Title")
    s["grade"]      = choose("Grade", STAFF_GRADES)
    entry_min       = f"{d['birth_year'] + 18}-01-01"
    s["entry_date"] = ask_date("Date of Entry to University", min_date=entry_min)

    conn = get_connection()
    conn.execute(
        "INSERT INTO staff (person_id, department, job_title, grade, entry_date) VALUES (?,?,?,?,?)",
        (person_id, s["dept"], s["title"], s["grade"], s["entry_date"]),
    )
    conn.commit()
    conn.close()
    success_box(new_id, f"{d['first_name']} {d['last_name']}")
    pause()