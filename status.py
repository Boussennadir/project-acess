# ============================================================
# status.py — Identity Status Management
# University Identity Management System
# ============================================================

from datetime import datetime, date
from db import get_connection
from utils import TYPE_LABELS, STATUS_TRANSITIONS, STATUS_DESCRIPTIONS, header, log_history


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
            print("  ✗ No person found with that ID.")
            return None
        return row

    elif choice == "2":
        name = input("  Name (first or last): ").strip()
        q    = f"%{name}%"
        rows = conn.execute(
            "SELECT * FROM person WHERE first_name LIKE ? OR last_name LIKE ? ORDER BY last_name",
            (q, q),
        ).fetchall()
        conn.close()
        if not rows:
            print("  ✗ No results.")
            return None
        print(f"\n  Found {len(rows)} result(s):")
        for i, p in enumerate(rows):
            print(f"    {i+1}. [{p['unique_identifier']}] {p['first_name']} {p['last_name']} "
                  f"— {p['type']} — {p['status']}")
        raw = input("\n  Select # (or 0 to cancel): ").strip()
        if raw == "0":
            return None
        try:
            idx = int(raw) - 1
            assert 0 <= idx < len(rows)
            return rows[idx]
        except (ValueError, AssertionError):
            print("  ✗ Invalid selection.")
            return None
    else:
        conn.close()
        print("  ✗ Invalid choice.")
        return None


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def change_status():
    header("STATUS MANAGEMENT")

    person = _find_person()
    if not person:
        return

    current = person["status"]
    allowed = STATUS_TRANSITIONS.get(current, [])

    print(f"\n  Person  : {person['first_name']} {person['last_name']}")
    print(f"  ID      : {person['unique_identifier']}")
    print(f"  Type    : {TYPE_LABELS.get(person['type'], person['type'])}")
    print(f"  Status  : {current}")

    if not allowed:
        print("\n  ✗ No transitions available. Archived is a final state.")
        return

    print(f"\n  Allowed transitions from \"{current}\":")
    for i, s in enumerate(allowed, 1):
        print(f"    {i}. {s} — {STATUS_DESCRIPTIONS[s]}")
    print("    0. Cancel")

    raw = input("\n  Choose new status: ").strip()
    if raw == "0":
        print("  Cancelled.")
        return
    try:
        idx = int(raw) - 1
        assert 0 <= idx < len(allowed)
    except (ValueError, AssertionError):
        print("  ✗ Invalid choice.")
        return

    new_status = allowed[idx]

    # Special rule: Inactive → Archived only after 5 years
    if current == "Inactive" and new_status == "Archived":
        try:
            updated = datetime.strptime(person["updated_at"][:19], "%Y-%m-%d %H:%M:%S")
            years_elapsed = (datetime.now() - updated).days / 365.25
            if years_elapsed < 5:
                print(f"\n  ✗ Cannot archive yet.")
                print(f"     Account must be Inactive for at least 5 years.")
                print(f"     Inactive since : {person['updated_at']}")
                print(f"     Years elapsed  : {years_elapsed:.2f}")
                return
        except Exception:
            pass  # If date parse fails, allow the transition

    note = input("  Reason / Note (optional, press Enter to skip): ").strip() or None

    conn = get_connection()
    conn.execute(
        "UPDATE person SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (new_status, person["id"]),
    )
    log_history(conn, person["id"], "STATUS_CHANGE", field="status",
                old_val=current, new_val=new_status, note=note)
    conn.commit()
    conn.close()

    print(f"\n  ✓ Status updated: {current} → {new_status}")
    print(f"    Person : {person['first_name']} {person['last_name']}")
    print(f"    ID     : {person['unique_identifier']}\n")
