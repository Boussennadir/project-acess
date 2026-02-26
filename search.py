# ============================================================
# search.py — Multi-Criteria Search & Detailed Person View
# University Identity Management System
# ============================================================

from db import get_connection
from utils import TYPE_LABELS, sep, header, pause, log_history


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────
def _row_summary(i, p):
    name = f"{p['first_name']} {p['last_name']}"
    print(
        f"  {str(i+1):>3}. "
        f"{p['unique_identifier']:<16} "
        f"{name:<26} "
        f"{TYPE_LABELS.get(p['type'], p['type']):<14} "
        f"{p['status']}"
    )


def _display_detail(p):
    conn = get_connection()
    print(f"\n  {'═'*56}")
    print(f"  IDENTITY RECORD: {p['unique_identifier']}")
    print(f"  {'═'*56}")

    print(f"\n  ── COMMON INFORMATION")
    print(f"     Full Name      : {p['first_name']} {p['last_name']}")
    print(f"     Type           : {TYPE_LABELS.get(p['type'], p['type'])}")
    print(f"     Status         : {p['status']}")
    print(f"     Date of Birth  : {p['date_of_birth']}")
    print(f"     Place of Birth : {p['place_of_birth']}")
    print(f"     Nationality    : {p['nationality']}")
    print(f"     Gender         : {'Male' if p['gender'] == 'M' else 'Female'}")
    print(f"     Email          : {p['email']}")
    print(f"     Phone          : {p['phone']}")
    print(f"     Created At     : {p['created_at']}")
    print(f"     Updated At     : {p['updated_at']}")

    t = p["type"]

    if t in ("STU", "PHD"):
        s = conn.execute("SELECT * FROM student WHERE person_id = ?", (p["id"],)).fetchone()
        if s:
            print(f"\n  ── ACADEMIC INFORMATION")
            print(f"     High School Type   : {s['high_school_type']}")
            print(f"     High School Year   : {s['high_school_year']}")
            print(f"     High School Honors : {s['high_school_honors']}")
            print(f"     Major              : {s['major']}")
            print(f"     Entry Year         : {s['entry_year']}")
            print(f"     Academic Status    : {s['academic_status']}")
            print(f"     Faculty            : {s['faculty']}")
            print(f"     Department         : {s['department']}")
            print(f"     Group              : {s['group_name'] or '—'}")
            print(f"\n  ── FINANCIAL INFORMATION")
            print(f"     Scholarship        : {s['scholarship']}")

    elif t == "FAC":
        f = conn.execute("SELECT * FROM faculty WHERE person_id = ?", (p["id"],)).fetchone()
        if f:
            print(f"\n  ── PROFESSIONAL INFORMATION")
            print(f"     Rank               : {f['rank']}")
            print(f"     Employment Cat.    : {f['employment_category']}")
            print(f"     Appointment Start  : {f['appointment_start']}")
            print(f"     Primary Dept.      : {f['primary_department']}")
            print(f"     Secondary Depts.   : {f['secondary_departments'] or '—'}")
            bldg  = f['office_building'] or '—'
            floor = f['office_floor']    or '—'
            room  = f['office_room']     or '—'
            print(f"     Office             : Building {bldg}, Floor {floor}, Room {room}")
            print(f"     PhD Institution    : {f['phd_institution'] or '—'}")
            print(f"     Research Areas     : {f['research_areas'] or '—'}")
            print(f"     HDR                : {'Yes' if f['hdr'] else 'No'}")
            print(f"\n  ── CONTRACT INFORMATION")
            print(f"     Contract Type      : {f['contract_type']}")
            print(f"     Contract Start     : {f['contract_start']}")
            print(f"     Contract End       : {f['contract_end'] or 'Open-ended'}")
            print(f"     Teaching Hours/wk  : {f['teaching_hours']}")

    elif t in ("STF", "TMP"):
        s = conn.execute("SELECT * FROM staff WHERE person_id = ?", (p["id"],)).fetchone()
        if s:
            print(f"\n  ── STAFF INFORMATION")
            print(f"     Department         : {s['department']}")
            print(f"     Job Title          : {s['job_title']}")
            print(f"     Grade              : {s['grade']}")
            print(f"     Entry Date         : {s['entry_date']}")

    print(f"\n  {'═'*56}\n")
    conn.close()


def _display_history(person_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM history WHERE person_id = ? ORDER BY changed_at DESC",
        (person_id,),
    ).fetchall()
    conn.close()

    if not rows:
        print("\n  No modification history found.")
        return

    print(f"\n  ── MODIFICATION HISTORY ({len(rows)} entries)")
    for r in rows:
        print(f"\n     [{r['changed_at']}]  {r['action']}")
        if r["field_name"]:
            print(f"       Field  : {r['field_name']}")
            print(f"       Before : {r['old_value'] or '—'}")
            print(f"       After  : {r['new_value'] or '—'}")
        if r["note"]:
            print(f"       Note   : {r['note']}")


# ─────────────────────────────────────────────
# AFTER RESULTS — PICK ONE
# ─────────────────────────────────────────────
def _after_results(results):
    if not results:
        print("\n  No results found.")
        return

    print(f"\n  {sep()}")
    print(f"  {'#':>4}  {'ID':<16} {'Full Name':<26} {'Type':<14} Status")
    print(f"  {sep()}")
    for i, p in enumerate(results):
        _row_summary(i, p)
    print(f"  {sep()}")
    print(f"  {len(results)} result(s) found.\n")

    while True:
        raw = input(f"  Select number (1-{len(results)}) to view details, or 0 to go back: ").strip()
        if raw == "0":
            return
        try:
            idx = int(raw) - 1
            assert 0 <= idx < len(results)
            break
        except (ValueError, AssertionError):
            print(f"  ✗ Please enter a number between 1 and {len(results)}, or 0 to go back.")

    person = results[idx]
    _display_detail(person)

    print("  Options:")
    print("    1. View modification history")
    print("    2. Back to results")
    print("    0. Main menu")

    sub = input("  Choice: ").strip()
    if sub == "1":
        _display_history(person["id"])
        _after_results(results)
    elif sub == "2":
        _after_results(results)
    # else fall through → main menu


# ─────────────────────────────────────────────
# SEARCHES
# ─────────────────────────────────────────────
def _run_query(sql, params=()):
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def _search_by_name():
    name = input("  Name (first or last, partial ok): ").strip()
    q = f"%{name}%"
    return _run_query(
        "SELECT * FROM person WHERE first_name LIKE ? OR last_name LIKE ? ORDER BY last_name",
        (q, q),
    )


def _search_by_id():
    uid = input("  Unique ID (partial ok): ").strip().upper()
    return _run_query(
        "SELECT * FROM person WHERE unique_identifier LIKE ? ORDER BY unique_identifier",
        (f"%{uid}%",),
    )


def _search_by_email():
    email = input("  Email (partial ok): ").strip()
    return _run_query(
        "SELECT * FROM person WHERE email LIKE ? ORDER BY last_name",
        (f"%{email}%",),
    )


def _search_by_type():
    print("  Types: STU, PHD, FAC, STF, TMP")
    t = input("  Type: ").strip().upper()
    valid = {"STU", "PHD", "FAC", "STF", "TMP"}
    if t not in valid:
        print("  ✗ Invalid type.")
        return []
    return _run_query(
        "SELECT * FROM person WHERE type = ? ORDER BY last_name",
        (t,),
    )


def _search_by_status():
    print("  Statuses: Pending, Active, Suspended, Inactive, Archived")
    raw = input("  Status: ").strip()
    valid = ["Pending", "Active", "Suspended", "Inactive", "Archived"]
    match = next((v for v in valid if v.lower() == raw.lower()), None)
    if not match:
        print("  ✗ Invalid status.")
        return []
    return _run_query(
        "SELECT * FROM person WHERE status = ? ORDER BY last_name",
        (match,),
    )


def _search_by_department():
    dept = input("  Department (partial ok): ").strip()
    q = f"%{dept}%"
    return _run_query(
        """SELECT DISTINCT p.* FROM person p
           LEFT JOIN student st ON p.id = st.person_id
           LEFT JOIN faculty  f  ON p.id = f.person_id
           LEFT JOIN staff    s  ON p.id = s.person_id
           WHERE st.department LIKE ?
              OR f.primary_department LIKE ?
              OR s.department LIKE ?
           ORDER BY p.last_name""",
        (q, q, q),
    )


def _search_by_year():
    raw = input("  Year (entry or graduation): ").strip()
    try:
        y = int(raw)
    except ValueError:
        print("  ✗ Invalid year.")
        return []
    return _run_query(
        """SELECT p.* FROM person p
           LEFT JOIN student st ON p.id = st.person_id
           WHERE st.entry_year = ? OR st.high_school_year = ?
           ORDER BY p.last_name""",
        (y, y),
    )


def _advanced_search():
    print("\n  ── Advanced Search (press Enter to skip any field)")
    filters, params = [], []

    def opt(label, col, transform=lambda v: v, like=False):
        raw = input(f"  {label} (Enter to skip): ").strip()
        if raw:
            v = transform(raw)
            if like:
                filters.append(f"{col} LIKE ?")
                params.append(f"%{v}%")
            else:
                filters.append(f"{col} = ?")
                params.append(v)

    opt("First Name",  "p.first_name",  like=True)
    opt("Last Name",   "p.last_name",   like=True)
    opt("Type",        "p.type",        transform=str.upper)
    opt("Status",      "p.status")
    opt("Nationality", "p.nationality", like=True)
    opt("Gender (M/F)","p.gender",      transform=str.upper)

    where = "WHERE " + " AND ".join(filters) if filters else ""
    return _run_query(
        f"SELECT p.* FROM person p {where} ORDER BY p.last_name",
        params,
    )


# ─────────────────────────────────────────────
# MENU
# ─────────────────────────────────────────────
def search_identity():
    header("SEARCH IDENTITIES")
    print("    1. Search by Name")
    print("    2. Search by Unique ID")
    print("    3. Search by Email")
    print("    4. Search by Type")
    print("    5. Search by Status")
    print("    6. Search by Department")
    print("    7. Search by Year")
    print("    8. Advanced Search (multiple filters)")
    print("    9. List All")
    print("    0. Back to Menu")

    choice = input("\n  Choice: ").strip()

    dispatch = {
        "1": _search_by_name,
        "2": _search_by_id,
        "3": _search_by_email,
        "4": _search_by_type,
        "5": _search_by_status,
        "6": _search_by_department,
        "7": _search_by_year,
        "8": _advanced_search,
        "9": lambda: _run_query("SELECT * FROM person ORDER BY type, last_name"),
    }

    if choice == "0":
        return
    if choice not in dispatch:
        print("  ✗ Invalid choice.")
        return search_identity()

    results = dispatch[choice]()
    _after_results(results)