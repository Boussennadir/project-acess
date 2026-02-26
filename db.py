# ============================================================
# db.py — SQLite Database Initialization
# University Identity Management System
# ============================================================

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "university.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # ── PERSON (common data for all)
    c.execute("""
        CREATE TABLE IF NOT EXISTS person (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_identifier TEXT    NOT NULL UNIQUE,
            type              TEXT    NOT NULL CHECK(type IN ('STU','PHD','FAC','STF','TMP')),
            status            TEXT    NOT NULL DEFAULT 'Pending'
                                      CHECK(status IN ('Pending','Active','Suspended','Inactive','Archived')),
            first_name        TEXT    NOT NULL,
            last_name         TEXT    NOT NULL,
            date_of_birth     TEXT    NOT NULL,
            place_of_birth    TEXT    NOT NULL,
            nationality       TEXT    NOT NULL,
            gender            TEXT    NOT NULL CHECK(gender IN ('M','F')),
            email             TEXT    NOT NULL UNIQUE,
            phone             TEXT    NOT NULL,
            created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── STUDENT (STU + PHD)
    c.execute("""
        CREATE TABLE IF NOT EXISTS student (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id           INTEGER NOT NULL UNIQUE REFERENCES person(id) ON DELETE CASCADE,
            high_school_type    TEXT    NOT NULL,
            high_school_year    INTEGER NOT NULL,
            high_school_honors  TEXT    NOT NULL,
            major               TEXT    NOT NULL,
            entry_year          INTEGER NOT NULL,
            academic_status     TEXT    NOT NULL DEFAULT 'Active'
                                        CHECK(academic_status IN ('Active','Suspended','Graduated','Expelled')),
            faculty             TEXT    NOT NULL,
            department          TEXT    NOT NULL,
            group_name          TEXT,
            scholarship         TEXT    NOT NULL DEFAULT 'no' CHECK(scholarship IN ('yes','no'))
        )
    """)

    # ── FACULTY (FAC)
    c.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id             INTEGER NOT NULL UNIQUE REFERENCES person(id) ON DELETE CASCADE,
            rank                  TEXT    NOT NULL,
            employment_category   TEXT    NOT NULL,
            appointment_start     TEXT    NOT NULL,
            primary_department    TEXT    NOT NULL,
            secondary_departments TEXT,
            office_building       TEXT,
            office_floor          TEXT,
            office_room           TEXT,
            phd_institution       TEXT,
            research_areas        TEXT,
            hdr                   INTEGER NOT NULL DEFAULT 0 CHECK(hdr IN (0,1)),
            contract_type         TEXT    NOT NULL,
            contract_start        TEXT    NOT NULL,
            contract_end          TEXT,
            teaching_hours        REAL    NOT NULL DEFAULT 0
        )
    """)

    # ── STAFF (STF + TMP)
    c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id    INTEGER NOT NULL UNIQUE REFERENCES person(id) ON DELETE CASCADE,
            department   TEXT    NOT NULL,
            job_title    TEXT    NOT NULL,
            grade        TEXT    NOT NULL,
            entry_date   TEXT    NOT NULL
        )
    """)

    # ── HISTORY (audit trail)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id    INTEGER NOT NULL REFERENCES person(id),
            action       TEXT    NOT NULL,
            field_name   TEXT,
            old_value    TEXT,
            new_value    TEXT,
            changed_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            note         TEXT
        )
    """)

    conn.commit()
    conn.close()
