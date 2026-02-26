# ============================================================
# update.py — Identity Information Modification
# University Identity Management System
# ============================================================

import re
from db import get_connection
from utils import (
    TYPE_LABELS, HONORS_LIST, ACADEMIC_STATUSES, FACULTIES, DEPARTMENTS,
    GROUPS, FACULTY_RANKS, EMPLOYMENT_CATS, CONTRACT_TYPES, STAFF_GRADES,
    header, is_valid_date, log_history, choose_optional, letters_only,
)


# ─────────────────────────────────────────────
# FIND PERSON
# ─────────────────────────────────────────────
def _find_person():
    print("  Find person by:")
    print("    1. Unique ID")
    print("    2. Name")
    choice = input("  Choice: ").strip()

    conn = get_connection()
    if choice == "1":
        uid = input("  Unique ID: ").strip().upper()
        row = conn.execute(
            "SELECT * FROM person WHERE unique_identifier = ?", (uid,)
        ).fetchone()
        conn.close()
        if not row:
            print("  ✗ Not found.")
            return None
        return row
    elif choice == "2":
        name = input("  Name: ").strip()
        q    = f"%{name}%"
        rows = conn.execute(
            "SELECT * FROM person WHERE first_name LIKE ? OR last_name LIKE ? ORDER BY last_name",
            (q, q),
        ).fetchall()
        conn.close()
        if not rows:
            print("  ✗ No results.")
            return None
        for i, p in enumerate(rows):
            print(f"    {i+1}. [{p['unique_identifier']}] {p['first_name']} {p['last_name']} ({p['type']})")
        raw = input("  Select #: ").strip()
        try:
            idx = int(raw) - 1
            assert 0 <= idx < len(rows)
            return rows[idx]
        except (ValueError, AssertionError):
            return None
    else:
        conn.close()
        return None


# ─────────────────────────────────────────────
# GENERIC FIELD UPDATER
# ─────────────────────────────────────────────
def _update_text(conn, person_id, table, pk_col, pk_val, field, label, current, validate=None):
    print(f"\n  Current \"{label}\": {current or '—'}")
    raw = input("  New value (Enter to skip): ").strip()
    if not raw:
        return
    if validate:
        err = validate(raw)
        if err:
            print(f"  ✗ {err}")
            return
    conn.execute(f"UPDATE {table} SET {field} = ? WHERE {pk_col} = ?", (raw, pk_val))
    log_history(conn, person_id, "UPDATE", field=label, old_val=current, new_val=raw)
    print("  ✓ Updated.")


def _update_choice(conn, person_id, table, pk_col, pk_val, field, label, current, options):
    new_val = choose_optional(f'Update "{label}" — current: {current or "—"}', options)
    if new_val is None:
        return
    conn.execute(f"UPDATE {table} SET {field} = ? WHERE {pk_col} = ?", (new_val, pk_val))
    log_history(conn, person_id, "UPDATE", field=label, old_val=current, new_val=new_val)
    print("  ✓ Updated.")


# ─────────────────────────────────────────────
# UPDATE COMMON (person table)
# ─────────────────────────────────────────────
def _update_common(conn, person):
    print("\n  ── COMMON INFORMATION (Enter to skip any field)")
    pid = person["id"]

    _update_text(conn, pid, "person", "id", pid, "first_name", "First Name",
                 person["first_name"],
                 lambda v: "Minimum 2 characters." if len(v) < 2 else letters_only(v))

    _update_text(conn, pid, "person", "id", pid, "last_name", "Last Name",
                 person["last_name"],
                 lambda v: "Minimum 2 characters." if len(v) < 2 else letters_only(v))

    _update_text(conn, pid, "person", "id", pid, "place_of_birth", "Place of Birth",
                 person["place_of_birth"], letters_only)

    _update_text(conn, pid, "person", "id", pid, "nationality", "Nationality",
                 person["nationality"], letters_only)

    _update_text(conn, pid, "person", "id", pid, "phone", "Phone",
                 person["phone"],
                 lambda v: "Only digits, 9–15 characters." if not re.match(r"^\d{9,15}$", v) else None)

    conn.execute("UPDATE person SET updated_at = datetime('now') WHERE id = ?", (pid,))


# ─────────────────────────────────────────────
# UPDATE STUDENT
# ─────────────────────────────────────────────
def _update_student(conn, person):
    s = conn.execute("SELECT * FROM student WHERE person_id = ?", (person["id"],)).fetchone()
    if not s:
        print("  ✗ No student record found.")
        return

    print("\n  ── ACADEMIC INFORMATION")
    pid = person["id"]

    _update_text(conn, pid, "student", "person_id", pid, "major", "Major", s["major"])

    _update_choice(conn, pid, "student", "person_id", pid,
                   "high_school_honors", "High School Honors", s["high_school_honors"], HONORS_LIST)

    _update_choice(conn, pid, "student", "person_id", pid,
                   "academic_status", "Academic Status", s["academic_status"], ACADEMIC_STATUSES)

    _update_choice(conn, pid, "student", "person_id", pid,
                   "faculty", "Faculty", s["faculty"], FACULTIES)

    _update_choice(conn, pid, "student", "person_id", pid,
                   "department", "Department", s["department"], DEPARTMENTS)

    _update_choice(conn, pid, "student", "person_id", pid,
                   "group_name", "Group", s["group_name"], GROUPS)

    print(f"\n  ── FINANCIAL INFORMATION")
    print(f"\n  Current \"Scholarship\": {s['scholarship']}")
    raw = input("  New value (yes/no, Enter to skip): ").strip().lower()
    if raw in ("yes", "no"):
        conn.execute("UPDATE student SET scholarship = ? WHERE person_id = ?", (raw, pid))
        log_history(conn, pid, "UPDATE", field="scholarship", old_val=s["scholarship"], new_val=raw)
        print("  ✓ Updated.")

    conn.execute("UPDATE person SET updated_at = datetime('now') WHERE id = ?", (pid,))


# ─────────────────────────────────────────────
# UPDATE FACULTY
# ─────────────────────────────────────────────
def _update_faculty(conn, person):
    f = conn.execute("SELECT * FROM faculty WHERE person_id = ?", (person["id"],)).fetchone()
    if not f:
        print("  ✗ No faculty record found.")
        return

    print("\n  ── PROFESSIONAL INFORMATION")
    pid = person["id"]

    _update_choice(conn, pid, "faculty", "person_id", pid,
                   "rank", "Rank", f["rank"], FACULTY_RANKS)

    _update_choice(conn, pid, "faculty", "person_id", pid,
                   "employment_category", "Employment Category", f["employment_category"], EMPLOYMENT_CATS)

    _update_choice(conn, pid, "faculty", "person_id", pid,
                   "primary_department", "Primary Department", f["primary_department"], DEPARTMENTS)

    _update_text(conn, pid, "faculty", "person_id", pid,
                 "secondary_departments", "Secondary Departments", f["secondary_departments"])

    # Office
    current_office = f"Bldg={f['office_building'] or '—'}, Floor={f['office_floor'] or '—'}, Room={f['office_room'] or '—'}"
    print(f"\n  Current Office: {current_office}")
    if input("  Update office? (yes/no): ").strip().lower() in ("yes", "y"):
        bldg  = input("  Building: ").strip() or None
        floor = input("  Floor: ").strip() or None
        room  = input("  Room Number: ").strip() or None
        conn.execute(
            "UPDATE faculty SET office_building=?, office_floor=?, office_room=? WHERE person_id=?",
            (bldg, floor, room, pid),
        )
        log_history(conn, pid, "UPDATE", field="office",
                    old_val=current_office, new_val=f"Bldg={bldg}, Floor={floor}, Room={room}")
        print("  ✓ Updated.")

    _update_text(conn, pid, "faculty", "person_id", pid,
                 "research_areas", "Research Areas", f["research_areas"])

    # Teaching hours
    print(f"\n  Current \"Teaching Hours\": {f['teaching_hours']}")
    raw = input("  New value (Enter to skip): ").strip()
    if raw:
        try:
            h = float(raw)
            conn.execute("UPDATE faculty SET teaching_hours=? WHERE person_id=?", (h, pid))
            log_history(conn, pid, "UPDATE", field="teaching_hours",
                        old_val=f["teaching_hours"], new_val=h)
            print("  ✓ Updated.")
        except ValueError:
            print("  ✗ Invalid number, skipping.")

    print("\n  ── CONTRACT INFORMATION")
    _update_choice(conn, pid, "faculty", "person_id", pid,
                   "contract_type", "Contract Type", f["contract_type"], CONTRACT_TYPES)

    # Contract end date
    print(f"\n  Current \"Contract End Date\": {f['contract_end'] or 'Open-ended'}")
    raw = input("  New date (YYYY-MM-DD, Enter to skip): ").strip()
    if raw:
        if is_valid_date(raw):
            conn.execute("UPDATE faculty SET contract_end=? WHERE person_id=?", (raw, pid))
            log_history(conn, pid, "UPDATE", field="contract_end",
                        old_val=f["contract_end"], new_val=raw)
            print("  ✓ Updated.")
        else:
            print("  ✗ Invalid date, skipping.")

    conn.execute("UPDATE person SET updated_at = datetime('now') WHERE id = ?", (pid,))


# ─────────────────────────────────────────────
# UPDATE STAFF
# ─────────────────────────────────────────────
def _update_staff(conn, person):
    s = conn.execute("SELECT * FROM staff WHERE person_id = ?", (person["id"],)).fetchone()
    if not s:
        print("  ✗ No staff record found.")
        return

    print("\n  ── STAFF INFORMATION")
    pid = person["id"]

    _update_choice(conn, pid, "staff", "person_id", pid,
                   "department", "Department", s["department"], DEPARTMENTS)

    _update_choice(conn, pid, "staff", "person_id", pid,
                   "grade", "Grade", s["grade"], STAFF_GRADES)

    _update_text(conn, pid, "staff", "person_id", pid,
                 "job_title", "Job Title", s["job_title"])

    conn.execute("UPDATE person SET updated_at = datetime('now') WHERE id = ?", (pid,))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def update_identity():
    header("UPDATE IDENTITY INFORMATION")

    person = _find_person()
    if not person:
        return

    print(f"\n  Editing : {person['first_name']} {person['last_name']}")
    print(f"  ID      : {person['unique_identifier']}")
    print(f"  Type    : {TYPE_LABELS.get(person['type'], person['type'])}")
    print(f"  Status  : {person['status']}")

    print("\n  What to update?")
    print("    1. Common information (name, place, phone)")
    print("    2. Type-specific information")
    print("    3. Both")
    print("    0. Cancel")

    choice = input("  Choice: ").strip()
    if choice == "0":
        return

    conn = get_connection()

    try:
        if choice in ("1", "3"):
            _update_common(conn, person)

        if choice in ("2", "3"):
            t = person["type"]
            if t in ("STU", "PHD"):
                _update_student(conn, person)
            elif t == "FAC":
                _update_faculty(conn, person)
            elif t in ("STF", "TMP"):
                _update_staff(conn, person)

        conn.commit()
        print("\n  ✓ All updates saved.\n")
    except Exception as e:
        conn.rollback()
        print(f"\n  ✗ Error: {e}")
    finally:
        conn.close()