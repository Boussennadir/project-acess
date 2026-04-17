# ============================================================
# auth.py — Authentication System
# University Identity Management System
# ============================================================

import sqlite3, os, hashlib, secrets, string, re
import json
import smtplib
import ssl
from email.message import EmailMessage
import base64
import hmac
from datetime import datetime, timedelta
from db import get_connection, DB_PATH

AUTH_DB_PATH = os.path.join(os.path.dirname(DB_PATH), "auth.db")
EMAIL_CFG_PATH = os.path.join(os.path.dirname(__file__), "email_config.json")

def _load_email_config():
    """Load SMTP config from email_config.json (kept out of source control)."""
    try:
        with open(EMAIL_CFG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
        return True, cfg
    except FileNotFoundError:
        return False, "Missing email_config.json (configure Gmail App Password)."
    except Exception as e:
        return False, f"Failed to read email_config.json: {e}"

def _mask_email(addr: str) -> str:
    a = (addr or "").strip()
    if "@" not in a:
        return a or "email"
    local, dom = a.split("@", 1)
    if len(local) <= 2:
        ml = local[:1] + "***"
    else:
        ml = local[:2] + "***"
    return f"{ml}@{dom}"

def _send_email_otp(to_email: str, code: str):
    ok, cfg = _load_email_config()
    if not ok:
        return False, cfg
    host = (cfg.get("smtp_host") or "smtp.gmail.com").strip()
    port = int(cfg.get("smtp_port") or 587)
    user = (cfg.get("smtp_user") or "").strip()
    app_pw = (cfg.get("smtp_app_password") or "").strip()
    from_name = (cfg.get("from_name") or "IAM System").strip()

    if not user or not app_pw or "PASTE_YOUR_GMAIL_APP_PASSWORD_HERE" in app_pw:
        return False, "Email OTP not configured. Put your Gmail App Password into email_config.json."
    if not to_email or "@" not in to_email:
        return False, "User email is missing/invalid."

    msg = EmailMessage()
    msg["Subject"] = "IAM Verification Code"
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email
    msg.set_content(
        "Your IAM verification code is:\n\n"
        f"{code}\n\n"
        f"This code expires in {OTP_VALID_MIN} minutes.\n"
    )

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(user, app_pw)
            s.send_message(msg)
        return True, None
    except Exception as e:
        return False, f"Failed to send email: {e}"

# ── Password Policy ──────────────────────────────────────────
MIN_LEN = 8
MAX_LEN = 64
MAX_FAILED = 5
LOCKOUT_MINUTES = 30
PASSWORD_HISTORY = 5

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

def _hash_password(password: str) -> str:
    if not HAS_BCRYPT:
        raise RuntimeError("bcrypt is required by the project spec but is not installed.")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()

def _verify_password(password: str, hashed: str) -> bool:
    if not hashed or not isinstance(hashed, str):
        return False
    if not HAS_BCRYPT:
        return False
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def _hash_value(value: str) -> str:
    """Hash non-password secrets (OTP, reset tokens, etc.) using SHA-256 with a random salt."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + (value or "")).encode()).hexdigest()
    return f"sha256:{salt}:{h}"

def _verify_value(value: str, hashed: str) -> bool:
    if not hashed or not hashed.startswith("sha256:"):
        return False
    try:
        _, salt, h = hashed.split(":", 2)
        return hashlib.sha256((salt + (value or "")).encode()).hexdigest() == h
    except Exception:
        return False

def _hash_answer(answer: str) -> str:
    """Security question answers are bcrypt-hashed (case-insensitive)."""
    if not HAS_BCRYPT:
        raise RuntimeError("bcrypt is required by the project spec but is not installed.")
    a = (answer or "").strip().lower()
    return bcrypt.hashpw(a.encode(), bcrypt.gensalt(12)).decode()

def _verify_answer(answer: str, hashed: str) -> bool:
    if not hashed:
        return False
    if not HAS_BCRYPT:
        return False
    try:
        return bcrypt.checkpw((answer or "").strip().lower().encode(), hashed.encode())
    except Exception:
        return False

# ── Strength Analysis ────────────────────────────────────────
def analyze_password_strength(password: str):
    tips = []
    score = 0
    if len(password) >= MIN_LEN: score += 1
    else: tips.append(f"Use at least {MIN_LEN} characters")

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))

    categories = sum([has_upper, has_lower, has_digit, has_special])
    if categories >= 3: score += 1
    else:
        missing = []
        if not has_upper: missing.append("uppercase letters")
        if not has_lower: missing.append("lowercase letters")
        if not has_digit: missing.append("numbers")
        if not has_special: missing.append("special characters (!@#$%^&*)")
        tips.append(f"Add: {', '.join(missing[:2])}")

    if len(password) >= 12: score += 1
    if len(password) >= 16 and categories == 4: score += 1

    labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#27ae60"]

    return {
        "score": min(score, 4), "label": labels[min(score, 4)],
        "color": colors[min(score, 4)], "tips": tips,
        "has_upper": has_upper, "has_lower": has_lower,
        "has_digit": has_digit, "has_special": has_special, "length": len(password),
    }

def validate_password_policy(password: str, username: str = "", first_name: str = "", last_name: str = "") -> list[str]:
    errors = []
    if len(password) < MIN_LEN: errors.append(f"Minimum {MIN_LEN} characters required.")
    if len(password) > MAX_LEN: errors.append(f"Maximum {MAX_LEN} characters allowed.")

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))
    if sum([has_upper, has_lower, has_digit, has_special]) < 3:
        errors.append("Must contain at least 3 of: uppercase, lowercase, numbers, special characters.")

    pw_lower = password.lower()
    for term in [username, first_name, last_name]:
        if term and len(term) >= 3 and term.lower() in pw_lower:
            errors.append("Password must not contain your name or username.")
            break
    return errors

# ── Auth DB ──────────────────────────────────────────────────
def get_auth_connection():
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_auth_db():
    conn = get_auth_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS auth_user (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            username         TEXT    NOT NULL UNIQUE,
            password_hash    TEXT    NOT NULL,
            person_id        INTEGER,
            role             TEXT    NOT NULL DEFAULT 'user'
                                     CHECK(role IN ('admin','user')),
            auth_level       INTEGER NOT NULL DEFAULT 1,
            failed_attempts  INTEGER NOT NULL DEFAULT 0,
            locked_until     TEXT,
            must_change_pw   INTEGER NOT NULL DEFAULT 0,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Migration: add auth_level column if it doesn't exist (for existing DBs)
    try:
        c.execute("ALTER TABLE auth_user ADD COLUMN auth_level INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    except Exception:
        pass  # Column already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS password_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
            password_hash TEXT NOT NULL,
            changed_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_user_id   INTEGER REFERENCES auth_user(id),
            username       TEXT    NOT NULL,
            person_id      INTEGER,
            identity_uid   TEXT,
            auth_level     INTEGER,
            success        INTEGER NOT NULL DEFAULT 0,
            ip_address     TEXT    NOT NULL DEFAULT 'localhost',
            failure_reason TEXT,
            session_id     TEXT,
            mfa_used       INTEGER NOT NULL DEFAULT 0,
            logged_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Migrations for new audit columns
    for stmt in [
        "ALTER TABLE login_log ADD COLUMN person_id INTEGER",
        "ALTER TABLE login_log ADD COLUMN identity_uid TEXT",
        "ALTER TABLE login_log ADD COLUMN auth_level INTEGER",
    ]:
        try:
            c.execute(stmt); conn.commit()
        except Exception:
            pass
    # Migration: add mfa_used column to existing login_log tables
    try:
        c.execute("ALTER TABLE login_log ADD COLUMN mfa_used INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    # ── MFA Tables ───────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS otp_state (
            auth_user_id     INTEGER PRIMARY KEY REFERENCES auth_user(id) ON DELETE CASCADE,
            code_hash        TEXT,
            expires_at       TEXT,
            last_sent_at     TEXT,
            hour_window_start TEXT,
            sent_in_window   INTEGER NOT NULL DEFAULT 0,
            failed_attempts  INTEGER NOT NULL DEFAULT 0,
            blocked_until    TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS totp (
            auth_user_id INTEGER PRIMARY KEY REFERENCES auth_user(id) ON DELETE CASCADE,
            secret_b32   TEXT,
            enabled      INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS backup_code (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
            code_hash   TEXT NOT NULL,
            used_at     TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS security_questions (
            auth_user_id     INTEGER PRIMARY KEY REFERENCES auth_user(id) ON DELETE CASCADE,
            q1              TEXT,
            a1_hash         TEXT,
            q2              TEXT,
            a2_hash         TEXT,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until    TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS password_reset (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
            token_hash  TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            used_at     TEXT
        )
    """)

    conn.commit()

    # Create default admin account if it doesn't exist
    existing = conn.execute("SELECT id FROM auth_user WHERE username='admin'").fetchone()
    if not existing:
        h = _hash_password("admin")
        conn.execute(
            "INSERT INTO auth_user (username, password_hash, role, auth_level, must_change_pw) VALUES ('admin', ?, 'admin', 4, 0)",
            (h,)
        )
        conn.commit()
    conn.close()

# ── Auth Operations ──────────────────────────────────────────
def authenticate(username: str, password: str, ip: str = "localhost"):
    conn = get_auth_connection()
    # Allow login by either:
    # - auth username (auth_user.username)
    # - university identity UID (person.unique_identifier) when auth_user.person_id is linked
    user = conn.execute("SELECT * FROM auth_user WHERE username=?", (username,)).fetchone()
    if not user:
        # Try to interpret input as a University ID and resolve to an auth user
        try:
            main = get_connection()
            pr = main.execute(
                "SELECT id FROM person WHERE unique_identifier=?",
                ((username or "").strip(),),
            ).fetchone()
            main.close()
            if pr:
                user = conn.execute(
                    "SELECT * FROM auth_user WHERE person_id=?",
                    (pr["id"],),
                ).fetchone()
        except Exception:
            user = None

    if not user:
        _log_login(conn, None, username, False, ip, "User not found")
        conn.commit(); conn.close()
        return {"ok": False, "user": None, "error": "Invalid credentials.", "locked": False}

    if user["locked_until"]:
        try:
            locked = datetime.strptime(user["locked_until"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < locked:
                mins = int((locked - datetime.now()).total_seconds() / 60) + 1
                _log_login(conn, user["id"], username, False, ip, "Account locked")
                conn.commit(); conn.close()
                return {"ok": False, "user": None, "error": f"Account locked. Try again in {mins} min.", "locked": True}
            else:
                conn.execute("UPDATE auth_user SET locked_until=NULL, failed_attempts=0 WHERE id=?", (user["id"],))
        except Exception: pass

    if not _verify_password(password, user["password_hash"]):
        new_fails = user["failed_attempts"] + 1
        if new_fails >= MAX_FAILED:
            lock_time = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("UPDATE auth_user SET failed_attempts=?, locked_until=? WHERE id=?", (new_fails, lock_time, user["id"]))
            _log_login(conn, user["id"], username, False, ip, f"Wrong password (locked after {MAX_FAILED} attempts)")
            conn.commit(); conn.close()
            return {"ok": False, "user": None, "error": f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes.", "locked": True}
        else:
            conn.execute("UPDATE auth_user SET failed_attempts=? WHERE id=?", (new_fails, user["id"]))
            remaining = MAX_FAILED - new_fails
            _log_login(conn, user["id"], username, False, ip, "Wrong password")
            conn.commit(); conn.close()
            return {"ok": False, "user": None, "error": f"Invalid credentials. {remaining} attempt(s) remaining.", "locked": False}

    sid = secrets.token_hex(16)
    conn.execute("UPDATE auth_user SET failed_attempts=0, locked_until=NULL, updated_at=datetime('now') WHERE id=?", (user["id"],))
    # Attach identity uid if linked
    identity_uid = None
    person_id = user["person_id"]
    if person_id:
        try:
            main = get_connection()
            pr = main.execute("SELECT unique_identifier FROM person WHERE id=?", (person_id,)).fetchone()
            main.close()
            if pr:
                identity_uid = pr["unique_identifier"]
        except Exception:
            identity_uid = None
    _log_login(conn, user["id"], username, True, ip, None, sid, 0, person_id=person_id, identity_uid=identity_uid, auth_level=user["auth_level"])
    conn.commit()
    user_dict = dict(user)
    conn.close()
    user_dict["session_id"] = sid
    return {"ok": True, "user": user_dict, "error": None, "locked": False}

def _log_login(conn, auth_user_id, username, success, ip, reason=None, session_id=None, mfa_used=0, person_id=None, identity_uid=None, auth_level=None):
    conn.execute(
        "INSERT INTO login_log (auth_user_id, username, person_id, identity_uid, auth_level, success, ip_address, failure_reason, session_id, mfa_used) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (auth_user_id, username, person_id, identity_uid, auth_level, 1 if success else 0, ip, reason, session_id, mfa_used)
    )

def change_password(auth_user_id: int, old_password: str, new_password: str, username: str = "", first_name: str = "", last_name: str = ""):
    conn = get_auth_connection()
    user = conn.execute("SELECT * FROM auth_user WHERE id=?", (auth_user_id,)).fetchone()
    if not user:
        conn.close(); return False, "User not found."
    if not _verify_password(old_password, user["password_hash"]):
        conn.close(); return False, "Current password is incorrect."
    errors = validate_password_policy(new_password, username, first_name, last_name)
    if errors:
        conn.close(); return False, "\n".join(errors)

    if _verify_password(new_password, user["password_hash"]):
        conn.close(); return False, f"Cannot reuse any of your last {PASSWORD_HISTORY} passwords."

    history = conn.execute("SELECT password_hash FROM password_history WHERE auth_user_id=? ORDER BY changed_at DESC LIMIT ?",
                           (auth_user_id, PASSWORD_HISTORY - 1)).fetchall()
    for h in history:
        if _verify_password(new_password, h["password_hash"]):
            conn.close(); return False, f"Cannot reuse any of your last {PASSWORD_HISTORY} passwords."

    new_hash = _hash_password(new_password)
    conn.execute("INSERT INTO password_history (auth_user_id, password_hash) VALUES (?,?)", (auth_user_id, user["password_hash"]))
    conn.execute("""DELETE FROM password_history WHERE auth_user_id=? AND id NOT IN (
        SELECT id FROM password_history WHERE auth_user_id=? ORDER BY changed_at DESC LIMIT ?
    )""", (auth_user_id, auth_user_id, PASSWORD_HISTORY))
    conn.execute("UPDATE auth_user SET password_hash=?, must_change_pw=0, updated_at=datetime('now') WHERE id=?", (new_hash, auth_user_id))
    conn.commit(); conn.close()
    return True, None

def reset_password_admin(auth_user_id: int, new_password: str):
    conn = get_auth_connection()
    user = conn.execute("SELECT * FROM auth_user WHERE id=?", (auth_user_id,)).fetchone()
    if not user:
        conn.close(); return False, "User not found."
    new_hash = _hash_password(new_password)
    conn.execute("INSERT INTO password_history (auth_user_id, password_hash) VALUES (?,?)", (auth_user_id, user["password_hash"]))
    conn.execute("""DELETE FROM password_history WHERE auth_user_id=? AND id NOT IN (
        SELECT id FROM password_history WHERE auth_user_id=? ORDER BY changed_at DESC LIMIT ?
    )""", (auth_user_id, auth_user_id, PASSWORD_HISTORY))
    conn.execute("UPDATE auth_user SET password_hash=?, must_change_pw=1, failed_attempts=0, locked_until=NULL, updated_at=datetime('now') WHERE id=?",
                 (new_hash, auth_user_id))
    conn.commit(); conn.close()
    return True, None

def unlock_account(auth_user_id: int):
    conn = get_auth_connection()
    conn.execute("UPDATE auth_user SET failed_attempts=0, locked_until=NULL, updated_at=datetime('now') WHERE id=?", (auth_user_id,))
    conn.commit(); conn.close()

def get_login_history(auth_user_id: int, limit: int = 20):
    conn = get_auth_connection()
    rows = conn.execute("SELECT * FROM login_log WHERE auth_user_id=? ORDER BY logged_at DESC LIMIT ?", (auth_user_id, limit)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_all_auth_users():
    conn = get_auth_connection()
    rows = conn.execute("SELECT * FROM auth_user ORDER BY username").fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_audit_log(limit: int = 100):
    conn = get_auth_connection()
    rows = conn.execute("SELECT * FROM login_log ORDER BY logged_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def mark_mfa_used(session_id: str):
    """Mark an already-logged successful login session as having used MFA."""
    if not session_id:
        return False, "Missing session id."
    conn = get_auth_connection()
    try:
        cur = conn.execute(
            "UPDATE login_log SET mfa_used=1 WHERE session_id=?",
            (session_id,),
        )
        conn.commit()
        if cur.rowcount <= 0:
            return False, "Session not found."
        return True, None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        conn.close()

# ── MFA requirement helpers ──────────────────────────────────
def get_user_auth_level(auth_user_id: int) -> int:
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT auth_level FROM auth_user WHERE id=?", (auth_user_id,)).fetchone()
        return int(row["auth_level"]) if row and row["auth_level"] is not None else 1
    finally:
        conn.close()

# ── OTP (L2+) — 8 digits, 5 minutes, 3 requests/hour, cooldown 60s, block after 3 wrong ──
OTP_LEN = 8
OTP_VALID_MIN = 5
OTP_MAX_PER_HOUR = 3
OTP_COOLDOWN_SEC = 60
OTP_MAX_FAIL = 3
OTP_FAIL_LOCK_MIN = 30

def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _parse_dt(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def request_sms_otp(auth_user_id: int):
    """Returns (ok, delivered_to_or_error). Sends OTP to user's email (Gmail SMTP)."""
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT * FROM otp_state WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if not row:
            conn.execute("INSERT INTO otp_state (auth_user_id, hour_window_start, sent_in_window) VALUES (?,?,0)", (auth_user_id, _now_str()))
            conn.commit()
            row = conn.execute("SELECT * FROM otp_state WHERE auth_user_id=?", (auth_user_id,)).fetchone()

        blocked_until = _parse_dt(row["blocked_until"])
        if blocked_until and datetime.now() < blocked_until:
            mins = int((blocked_until - datetime.now()).total_seconds() / 60) + 1
            return False, f"OTP blocked due to failed attempts. Try again in {mins} min."

        # cooldown
        last_sent = _parse_dt(row["last_sent_at"])
        if last_sent and (datetime.now() - last_sent).total_seconds() < OTP_COOLDOWN_SEC:
            wait = int(OTP_COOLDOWN_SEC - (datetime.now() - last_sent).total_seconds())
            return False, f"Please wait {wait}s before requesting another code."

        # hourly window
        wstart = _parse_dt(row["hour_window_start"]) or datetime.now()
        sent = int(row["sent_in_window"] or 0)
        if (datetime.now() - wstart) >= timedelta(hours=1):
            wstart = datetime.now()
            sent = 0
        if sent >= OTP_MAX_PER_HOUR:
            return False, "OTP request limit reached (max 3 per hour)."

        code = f"{secrets.randbelow(10**OTP_LEN):0{OTP_LEN}d}"
        ch = _hash_value(code)
        exp = (datetime.now() + timedelta(minutes=OTP_VALID_MIN)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE otp_state SET code_hash=?, expires_at=?, last_sent_at=?, hour_window_start=?, sent_in_window=?, failed_attempts=0 WHERE auth_user_id=?",
            (ch, exp, _now_str(), wstart.strftime("%Y-%m-%d %H:%M:%S"), sent + 1, auth_user_id),
        )
        conn.commit()
        # Resolve recipient email
        u = conn.execute("SELECT username, role, person_id FROM auth_user WHERE id=?", (auth_user_id,)).fetchone()
        person_id = u["person_id"] if u else None

        # Admin account is not linked to a person record; send to the configured admin Gmail (smtp_user)
        if not person_id:
            ok_cfg, cfg = _load_email_config()
            if not ok_cfg:
                return False, cfg
            admin_email = (cfg.get("smtp_user") or "").strip()
            if not admin_email:
                return False, "Email sender is not configured (smtp_user missing)."
            ok_s, err_s = _send_email_otp(admin_email, code)
            if not ok_s:
                return False, err_s
            return True, _mask_email(admin_email)
        try:
            main = get_connection()
            pr = main.execute("SELECT email FROM person WHERE id=?", (person_id,)).fetchone()
            main.close()
        except Exception:
            pr = None
        to_email = pr["email"] if pr and pr["email"] else None
        ok_s, err_s = _send_email_otp(to_email, code)
        if not ok_s:
            return False, err_s
        return True, _mask_email(to_email)
    finally:
        conn.close()

def verify_sms_otp(auth_user_id: int, code: str):
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT * FROM otp_state WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if not row:
            return False, "No OTP requested."
        blocked_until = _parse_dt(row["blocked_until"])
        if blocked_until and datetime.now() < blocked_until:
            mins = int((blocked_until - datetime.now()).total_seconds() / 60) + 1
            return False, f"OTP blocked. Try again in {mins} min."

        exp = _parse_dt(row["expires_at"])
        if not exp or datetime.now() > exp:
            return False, "OTP expired. Request a new code."

        if not _verify_value((code or "").strip(), row["code_hash"] or ""):
            fails = int(row["failed_attempts"] or 0) + 1
            if fails >= OTP_MAX_FAIL:
                until = (datetime.now() + timedelta(minutes=OTP_FAIL_LOCK_MIN)).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("UPDATE otp_state SET failed_attempts=?, blocked_until=? WHERE auth_user_id=?", (fails, until, auth_user_id))
                conn.commit()
                return False, f"Too many invalid OTP attempts. Blocked for {OTP_FAIL_LOCK_MIN} minutes."
            conn.execute("UPDATE otp_state SET failed_attempts=? WHERE auth_user_id=?", (fails, auth_user_id))
            conn.commit()
            return False, f"Invalid OTP. Attempts remaining: {OTP_MAX_FAIL - fails}."

        # success: clear current code
        conn.execute("UPDATE otp_state SET code_hash=NULL, expires_at=NULL, failed_attempts=0 WHERE auth_user_id=?", (auth_user_id,))
        conn.commit()
        return True, None
    finally:
        conn.close()

# ── TOTP (L3+) — RFC6238-ish: HMAC-SHA1, 6 digits ──────────
# Spec says 60s step, but some authenticator apps ignore custom period and always use 30s.
# To avoid "code always wrong" in demos, we ACCEPT both 60s and 30s during verification.
TOTP_STEP = 60
TOTP_STEP_FALLBACK = 30
TOTP_DIGITS = 6

def _b32_secret(nbytes: int = 20) -> str:
    raw = secrets.token_bytes(nbytes)
    return base64.b32encode(raw).decode().replace("=", "")

def _totp_at(secret_b32: str, for_time: int, step: int) -> str:
    # Base32 decode with padding
    s = (secret_b32 or "").strip().upper()
    pad = "=" * ((8 - (len(s) % 8)) % 8)
    key = base64.b32decode(s + pad)
    counter = int(for_time / step)
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code_int = (int.from_bytes(digest[off:off+4], "big") & 0x7fffffff) % (10**TOTP_DIGITS)
    return f"{code_int:0{TOTP_DIGITS}d}"

def totp_begin_enroll(auth_user_id: int):
    """Creates/overwrites a TOTP secret (not enabled until verified). Returns (ok, {secret, otpauth_uri})."""
    secret_b32 = _b32_secret()
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT auth_user_id FROM totp WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if row:
            conn.execute("UPDATE totp SET secret_b32=?, enabled=0, created_at=datetime('now') WHERE auth_user_id=?", (secret_b32, auth_user_id))
        else:
            conn.execute("INSERT INTO totp (auth_user_id, secret_b32, enabled) VALUES (?,?,0)", (auth_user_id, secret_b32))
        conn.commit()
    finally:
        conn.close()
    # Demo issuer/label
    issuer = "IAM-Batna2"
    label = f"IAM:{auth_user_id}"
    otpauth = f"otpauth://totp/{label}?secret={secret_b32}&issuer={issuer}&period={TOTP_STEP}&digits={TOTP_DIGITS}"
    return True, {"secret": secret_b32, "otpauth_uri": otpauth}

def totp_verify_and_enable(auth_user_id: int, code: str):
    code = (code or "").strip()
    if not (code.isdigit() and len(code) == TOTP_DIGITS):
        return False, "Enter a 6-digit TOTP code."
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT secret_b32 FROM totp WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if not row or not row["secret_b32"]:
            return False, "TOTP not enrolled yet."
        secret_b32 = row["secret_b32"]
        now = int(datetime.now().timestamp())
        valid = set()
        for step in (TOTP_STEP, TOTP_STEP_FALLBACK):
            valid |= {_totp_at(secret_b32, now + d * step, step) for d in (-1, 0, 1)}
        if code not in valid:
            return False, "Invalid TOTP code."
        conn.execute("UPDATE totp SET enabled=1 WHERE auth_user_id=?", (auth_user_id,))
        conn.commit()
        # generate fresh backup codes
        codes = generate_backup_codes(auth_user_id, rotate=True)
        return True, {"backup_codes": codes}
    finally:
        conn.close()

def totp_is_enabled(auth_user_id: int) -> bool:
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT enabled FROM totp WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        return bool(row and int(row["enabled"] or 0) == 1)
    finally:
        conn.close()

def totp_verify(auth_user_id: int, code: str):
    code = (code or "").strip()
    if not (code.isdigit() and len(code) == TOTP_DIGITS):
        return False, "Enter a 6-digit TOTP code."
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT secret_b32, enabled FROM totp WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if not row or not row["secret_b32"] or int(row["enabled"] or 0) != 1:
            return False, "TOTP not enabled."
        secret_b32 = row["secret_b32"]
        now = int(datetime.now().timestamp())
        valid = set()
        for step in (TOTP_STEP, TOTP_STEP_FALLBACK):
            valid |= {_totp_at(secret_b32, now + d * step, step) for d in (-1, 0, 1)}
        if code in valid:
            return True, None
        return False, "Invalid TOTP code."
    finally:
        conn.close()

def generate_backup_codes(auth_user_id: int, rotate: bool = False):
    """Returns plaintext codes (shown once). Stores hashes; old unused codes can be rotated."""
    conn = get_auth_connection()
    try:
        if rotate:
            conn.execute("DELETE FROM backup_code WHERE auth_user_id=? AND used_at IS NULL", (auth_user_id,))
        codes = []
        for _ in range(10):
            c = f"{secrets.randbelow(10**10):010d}"
            codes.append(c)
            conn.execute("INSERT INTO backup_code (auth_user_id, code_hash) VALUES (?,?)", (auth_user_id, _hash_value(c)))
        conn.commit()
        return codes
    finally:
        conn.close()

def verify_backup_code(auth_user_id: int, code: str):
    code = (code or "").strip()
    if not code:
        return False, "Enter a backup code."
    conn = get_auth_connection()
    try:
        rows = conn.execute("SELECT id, code_hash FROM backup_code WHERE auth_user_id=? AND used_at IS NULL", (auth_user_id,)).fetchall()
        for r in rows:
            if _verify_value(code, r["code_hash"]):
                conn.execute("UPDATE backup_code SET used_at=? WHERE id=?", (_now_str(), r["id"]))
                conn.commit()
                return True, None
        return False, "Invalid/used backup code."
    finally:
        conn.close()

# ── Security Questions (L4) ─────────────────────────────────
SECURITY_QUESTION_POOL = [
    "What was your first pet's name?",
    "In which city were you born?",
    "What was your childhood nickname?",
]
SECQ_MAX_FAIL = 3
SECQ_LOCK_MIN = 30

def secq_is_configured(auth_user_id: int) -> bool:
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT q1,a1_hash,q2,a2_hash FROM security_questions WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        return bool(row and row["q1"] and row["a1_hash"] and row["q2"] and row["a2_hash"])
    finally:
        conn.close()

def secq_set(auth_user_id: int, q1: str, a1: str, q2: str, a2: str):
    if q1 == q2:
        return False, "Please choose two different questions."
    if q1 not in SECURITY_QUESTION_POOL or q2 not in SECURITY_QUESTION_POOL:
        return False, "Invalid security question."
    if not (a1 and a2):
        return False, "Both answers are required."
    conn = get_auth_connection()
    try:
        h1 = _hash_answer(a1)
        h2 = _hash_answer(a2)
        row = conn.execute("SELECT auth_user_id FROM security_questions WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE security_questions SET q1=?,a1_hash=?,q2=?,a2_hash=?,failed_attempts=0,locked_until=NULL WHERE auth_user_id=?",
                (q1, h1, q2, h2, auth_user_id),
            )
        else:
            conn.execute(
                "INSERT INTO security_questions (auth_user_id,q1,a1_hash,q2,a2_hash) VALUES (?,?,?,?,?)",
                (auth_user_id, q1, h1, q2, h2),
            )
        conn.commit()
        return True, None
    finally:
        conn.close()

def secq_get_questions(auth_user_id: int):
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT q1,q2 FROM security_questions WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if not row or not row["q1"] or not row["q2"]:
            return False, "Not configured."
        return True, {"q1": row["q1"], "q2": row["q2"]}
    finally:
        conn.close()

def secq_verify(auth_user_id: int, a1: str, a2: str):
    conn = get_auth_connection()
    try:
        row = conn.execute("SELECT a1_hash,a2_hash,failed_attempts,locked_until FROM security_questions WHERE auth_user_id=?", (auth_user_id,)).fetchone()
        if not row:
            return False, "Security questions not configured."
        locked = _parse_dt(row["locked_until"])
        if locked and datetime.now() < locked:
            mins = int((locked - datetime.now()).total_seconds() / 60) + 1
            return False, f"Security questions locked. Try again in {mins} min."
        ok = _verify_answer(a1, row["a1_hash"]) and _verify_answer(a2, row["a2_hash"])
        if ok:
            conn.execute("UPDATE security_questions SET failed_attempts=0, locked_until=NULL WHERE auth_user_id=?", (auth_user_id,))
            conn.commit()
            return True, None
        fails = int(row["failed_attempts"] or 0) + 1
        if fails >= SECQ_MAX_FAIL:
            until = (datetime.now() + timedelta(minutes=SECQ_LOCK_MIN)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("UPDATE security_questions SET failed_attempts=?, locked_until=? WHERE auth_user_id=?", (fails, until, auth_user_id))
            conn.commit()
            return False, f"Too many attempts. Locked for {SECQ_LOCK_MIN} minutes."
        conn.execute("UPDATE security_questions SET failed_attempts=? WHERE auth_user_id=?", (fails, auth_user_id))
        conn.commit()
        return False, f"Incorrect answers. Attempts remaining: {SECQ_MAX_FAIL - fails}."
    finally:
        conn.close()

# ── Password reset (demo token display) ───────────────────────
RESET_TOKEN_VALID_MIN = 60

def request_password_reset(username_or_email: str):
    """Creates a reset token. In real life, you would email it. Returns (ok, token_or_error)."""
    if not username_or_email:
        return False, "Enter username/email."
    conn = get_auth_connection()
    try:
        u = conn.execute("SELECT id, username FROM auth_user WHERE username=?", (username_or_email,)).fetchone()
        if not u:
            # We don't have email in auth DB; treat input as username only for now.
            return False, "User not found."
        token = secrets.token_urlsafe(24)
        th = _hash_value(token)
        exp = (datetime.now() + timedelta(minutes=RESET_TOKEN_VALID_MIN)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO password_reset (auth_user_id, token_hash, expires_at) VALUES (?,?,?)", (u["id"], th, exp))
        conn.commit()
        return True, token
    finally:
        conn.close()

def reset_password_with_token(username: str, token: str, new_password: str):
    if not (username and token and new_password):
        return False, "Missing fields."
    conn = get_auth_connection()
    try:
        u = conn.execute("SELECT * FROM auth_user WHERE username=?", (username,)).fetchone()
        if not u:
            return False, "User not found."
        rows = conn.execute(
            "SELECT * FROM password_reset WHERE auth_user_id=? AND used_at IS NULL ORDER BY id DESC LIMIT 5",
            (u["id"],),
        ).fetchall()
        usable = None
        for r in rows:
            exp = _parse_dt(r["expires_at"])
            if not exp or datetime.now() > exp:
                continue
            if _verify_value(token, r["token_hash"]):
                usable = r
                break
        if not usable:
            return False, "Invalid or expired token."
        # enforce policy
        errs = validate_password_policy(new_password, username)
        if errs:
            return False, "\n".join(errs)
        # history check
        if _verify_password(new_password, u["password_hash"]):
            return False, f"Cannot reuse any of your last {PASSWORD_HISTORY} passwords."
        history = conn.execute(
            "SELECT password_hash FROM password_history WHERE auth_user_id=? ORDER BY changed_at DESC LIMIT ?",
            (u["id"], PASSWORD_HISTORY - 1),
        ).fetchall()
        for hrow in history:
            if _verify_password(new_password, hrow["password_hash"]):
                return False, f"Cannot reuse any of your last {PASSWORD_HISTORY} passwords."
        nh = _hash_password(new_password)
        conn.execute("INSERT INTO password_history (auth_user_id, password_hash) VALUES (?,?)", (u["id"], u["password_hash"]))
        conn.execute("""DELETE FROM password_history WHERE auth_user_id=? AND id NOT IN (
            SELECT id FROM password_history WHERE auth_user_id=? ORDER BY changed_at DESC LIMIT ?
        )""", (u["id"], u["id"], PASSWORD_HISTORY))
        conn.execute("UPDATE auth_user SET password_hash=?, must_change_pw=0, updated_at=datetime('now') WHERE id=?", (nh, u["id"]))
        conn.execute("UPDATE password_reset SET used_at=? WHERE id=?", (_now_str(), usable["id"]))
        conn.commit()
        return True, None
    finally:
        conn.close()

# ── Auth Level Management ────────────────────────────────────
AUTH_LEVELS = {
    1: {"name": "L1 — Basic",    "desc": "Password only",                          "color": "#3498db"},
    2: {"name": "L2 — Standard", "desc": "Password + SMS OTP",                    "color": "#f1c40f"},
    3: {"name": "L3 — High",     "desc": "Password + SMS OTP + TOTP",             "color": "#e67e22"},
    4: {"name": "L4 — Critical", "desc": "Password + SMS OTP + TOTP + Security Q","color": "#e74c3c"},
}

TYPE_DEFAULT_LEVEL = {"STU": 1, "FAC": 2, "STF": 2, "EXT": 1}
TYPE_MAX_LEVEL = {"STU": 2, "FAC": 3, "STF": 3, "EXT": 2}

def create_user_account(username: str, person_id: int, initial_password: str = None):
    if not initial_password:
        chars = string.ascii_letters + string.digits + "!@#$%"
        initial_password = "".join(secrets.choice(chars) for _ in range(12))
    h = _hash_password(initial_password)
    
    # Check default security level based on user type in standard DB
    default_level = 1
    main_conn = get_connection()
    p_row = main_conn.execute("SELECT type, sub_category FROM person WHERE id=?", (person_id,)).fetchone()
    main_conn.close()
    
    if p_row:
        p_type = p_row["type"]
        sub_cat = p_row["sub_category"]
        default_level = TYPE_DEFAULT_LEVEL.get(p_type, 1)
        if p_type == "STU" and "International" in sub_cat:
            default_level = 2
            
    conn = get_auth_connection()
    try:
        conn.execute(
            "INSERT INTO auth_user (username, password_hash, person_id, role, must_change_pw, auth_level) VALUES (?,?,?,'user',1,?)",
            (username, h, person_id, default_level)
        )
        conn.commit(); conn.close()
        return True, initial_password
    except sqlite3.IntegrityError:
        conn.close(); return False, "Username already exists."

def get_person_for_user(auth_user):
    if not auth_user.get("person_id"): return None
    conn = get_connection()
    p = conn.execute("SELECT * FROM person WHERE id=?", (auth_user["person_id"],)).fetchone()
    conn.close(); return dict(p) if p else None

def get_user_specific_data(person):
    if not person: return None
    conn = get_connection(); t = person["type"]; data = None
    if t == "STU":
        row = conn.execute("SELECT * FROM student WHERE person_id=?", (person["id"],)).fetchone()
        if row: data = dict(row)
    elif t == "FAC":
        row = conn.execute("SELECT * FROM faculty WHERE person_id=?", (person["id"],)).fetchone()
        if row: data = dict(row)
    elif t == "STF":
        row = conn.execute("SELECT * FROM staff WHERE person_id=?", (person["id"],)).fetchone()
        if row: data = dict(row)
    conn.close(); return data

def set_auth_level(auth_user_id: int, new_level: int):
    if new_level not in AUTH_LEVELS:
        return False, "Invalid level."
    conn = get_auth_connection()
    user = conn.execute("SELECT * FROM auth_user WHERE id=?", (auth_user_id,)).fetchone()
    if not user:
        conn.close()
        return False, "User not found."
    # Validate level constraints based on user type
    if user["person_id"]:
        main_conn = get_connection()
        p = main_conn.execute("SELECT type, sub_category FROM person WHERE id=?", (user["person_id"],)).fetchone()
        main_conn.close()
        if p:
            p_type = p["type"]
            sub_cat = p["sub_category"]
            min_lvl = TYPE_DEFAULT_LEVEL.get(p_type, 1)
            max_lvl = TYPE_MAX_LEVEL.get(p_type, 2)
            # Apply sub-category overrides
            if p_type == "STU" and "International" in sub_cat:
                min_lvl = 2
            if new_level < min_lvl:
                conn.close()
                return False, f"Minimum level for this user type is L{min_lvl}."
            if new_level > max_lvl:
                conn.close()
                return False, f"Maximum level for this user type is L{max_lvl}."
    else:
        # Admin: must stay at L4
        if new_level != 4:
            conn.close()
            return False, "Admin account must remain at L4 (Critical)."
    conn.execute("UPDATE auth_user SET auth_level=?, updated_at=datetime('now') WHERE id=?", (new_level, auth_user_id))
    conn.commit()
    conn.close()
    return True, None

def get_auth_level_info(auth_user_id: int):
    conn = get_auth_connection()
    row = conn.execute("SELECT auth_level FROM auth_user WHERE id=?", (auth_user_id,)).fetchone()
    conn.close()
    if not row: return None
    return AUTH_LEVELS.get(row["auth_level"], AUTH_LEVELS[1])


# ── Promotion helper ─────────────────────────────────────────
def create_promotion_account(old_person_id: int, new_person_id: int, suffix: str = "FAC"):
    """
    Create a second login for a promoted identity.

    - Finds the existing auth user linked to old_person_id.
    - Creates a new auth_user linked to new_person_id.
    - New username is oldUsername + suffix (auto-deduped).
    - Copies password_hash so the same password works.
    """
    if not old_person_id or not new_person_id:
        return False, "Missing person id(s)."

    conn = get_auth_connection()
    try:
        old_u = conn.execute(
            "SELECT * FROM auth_user WHERE person_id=? AND role='user' ORDER BY id LIMIT 1",
            (old_person_id,),
        ).fetchone()
        if not old_u:
            return False, "No existing login linked to the old identity."

        base = (old_u["username"] or "").strip()
        if not base:
            base = f"user{old_person_id}"
        suffix_clean = (suffix or "").strip().upper() or "FAC"
        desired = f"{base}{suffix_clean}"

        # Ensure username uniqueness
        candidate = desired
        i = 2
        while conn.execute("SELECT 1 FROM auth_user WHERE username=?", (candidate,)).fetchone():
            candidate = f"{desired}{i}"
            i += 1

        # Choose auth level based on new person type (fallback to 1)
        default_level = 1
        try:
            main = get_connection()
            p_row = main.execute("SELECT type, sub_category FROM person WHERE id=?", (new_person_id,)).fetchone()
            main.close()
            if p_row:
                p_type = p_row["type"]
                sub_cat = p_row["sub_category"] or ""
                default_level = TYPE_DEFAULT_LEVEL.get(p_type, 1)
                if p_type == "STU" and "International" in sub_cat:
                    default_level = 2
        except Exception:
            default_level = 1

        # Insert new account with same password hash
        conn.execute(
            "INSERT INTO auth_user (username, password_hash, person_id, role, must_change_pw, auth_level) VALUES (?,?,?,'user',0,?)",
            (candidate, old_u["password_hash"], new_person_id, default_level),
        )
        conn.commit()
        return True, {"username": candidate}
    except sqlite3.IntegrityError:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, "Username already exists."
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        conn.close()