#!/usr/bin/env python3
# ============================================================
# main.py — University Identity Management System
# Entry Point & Main Menu
# ============================================================

import os
import sys
from datetime import datetime

from db import init_db, get_connection
from create import create_identity
from search import search_identity
from status import change_status
from update import update_identity


# ─────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────
def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    now = datetime.now()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║       UNIVERSITY IDENTITY MANAGEMENT SYSTEM          ║")
    print("  ║             University of Batna 2 — IAM              ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(f"  Date: {now.strftime('%Y-%m-%d')}   Time: {now.strftime('%H:%M:%S')}")
    print("  ──────────────────────────────────────────────────────")


# ─────────────────────────────────────────────
# QUICK STATS ON MENU
# ─────────────────────────────────────────────
def _show_quick_stats():
    conn  = get_connection()
    rows  = conn.execute(
        "SELECT sub_category, COUNT(*) as cnt FROM person GROUP BY sub_category ORDER BY sub_category"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as cnt FROM person").fetchone()["cnt"]
    conn.close()

    print(f"\n  Registered identities: {total} total")
    for r in rows:
        lbl = r["sub_category"] or "Unknown"
        print(f"    • {lbl:<28}: {r['cnt']}")
    print()


# ─────────────────────────────────────────────
# FULL STATISTICS VIEW
# ─────────────────────────────────────────────
def _show_full_stats():
    conn = get_connection()
    print("\n  ══════════════════════════════════════════════")
    print("  FULL STATISTICS")
    print("  ══════════════════════════════════════════════\n")

    sections = [
        ("By Type",
         "SELECT type as label, COUNT(*) as count FROM person GROUP BY type"),
        ("By Status",
         "SELECT status as label, COUNT(*) as count FROM person GROUP BY status"),
        ("By Gender",
         "SELECT gender as label, COUNT(*) as count FROM person GROUP BY gender"),
        ("Students by Faculty",
         "SELECT faculty as label, COUNT(*) as count FROM student GROUP BY faculty"),
        ("Students by Academic Status",
         "SELECT academic_status as label, COUNT(*) as count FROM student GROUP BY academic_status"),
        ("Students with Scholarship",
         "SELECT scholarship as label, COUNT(*) as count FROM student GROUP BY scholarship"),
        ("Faculty by Rank",
         "SELECT rank as label, COUNT(*) as count FROM faculty GROUP BY rank"),
        ("Faculty by Employment Category",
         "SELECT employment_category as label, COUNT(*) as count FROM faculty GROUP BY employment_category"),
        ("Staff by Grade",
         "SELECT grade as label, COUNT(*) as count FROM staff GROUP BY grade"),
    ]

    for title, sql in sections:
        rows = conn.execute(sql).fetchall()
        if rows:
            print(f"  ── {title}")
            for r in rows:
                print(f"     {str(r['label'] or 'Unknown'):<34}: {r['count']}")
            print()

    conn.close()
    input("  Press Enter to return to menu...")


# ─────────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────────
def show_menu():
    print_banner()
    _show_quick_stats()

    print("  MAIN MENU")
    print("  ──────────────────────────────────────────────────────")
    print("    1.  Create New Identity")
    print("    2.  Search Identities")
    print("    3.  Update Information")
    print("    4.  Change Status")
    print("    5.  View Full Statistics")
    print("    0.  Exit")
    print("  ──────────────────────────────────────────────────────")

    choice = input("\n  Your choice: ").strip()

    if choice == "1":
        create_identity()
    elif choice == "2":
        search_identity()
    elif choice == "3":
        update_identity()
    elif choice == "4":
        change_status()
    elif choice == "5":
        _show_full_stats()
    elif choice == "0":
        print("\n  Goodbye!\n")
        sys.exit(0)
    else:
        print("  ✗ Invalid choice.")

    show_menu()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    try:
        show_menu()
    except KeyboardInterrupt:
        print("\n\n  Shutting down...\n")
        sys.exit(0)