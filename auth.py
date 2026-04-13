import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover
    bcrypt = None


def utc_now():
    return datetime.now(timezone.utc)


def _bcrypt_hash(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def _bcrypt_verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _pbkdf2_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def _pbkdf2_verify(password: str, hashed: str) -> bool:
    _, salt_hex, digest_hex = hashed.split("$")
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return hmac.compare_digest(expected, candidate)


def hash_password(password: str) -> str:
    if bcrypt:
        return _bcrypt_hash(password)
    return _pbkdf2_hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith("pbkdf2$"):
        return _pbkdf2_verify(password, hashed)
    if bcrypt:
        return _bcrypt_verify(password, hashed)
    return False


def validate_password_policy(password: str, username: str = "", full_name: str = "", birthdate: str = ""):
    if len(password) < 8 or len(password) > 64:
        return False, "Password must be 8 to 64 characters."
    checks = [
        any(ch.isupper() for ch in password),
        any(ch.islower() for ch in password),
        any(ch.isdigit() for ch in password),
        any(ch in "!@#$%^&*" for ch in password),
    ]
    if sum(checks) < 3:
        return False, "Password must include at least 3 categories (upper/lower/number/special)."

    lowered = password.lower()
    banned = [username.lower(), full_name.lower().replace(" ", ""), birthdate.replace("-", "")]
    if any(token and token in lowered for token in banned):
        return False, "Password cannot contain username, name, or birthdate."
    return True, ""


def log_auth_event(conn, username: str, success: int, reason: str = "", mfa_used: int = 0, session_id: str = ""):
    conn.execute(
        """
        INSERT INTO auth_event (event_time, username, success, ip_address, mfa_used, failure_reason, session_id)
        VALUES (datetime('now'), ?, ?, 'desktop-local', ?, ?, ?)
        """,
        (username, success, mfa_used, reason or None, session_id or None),
    )


def ensure_person_auth_user(conn, person_id: int, username: str, dob: str):
    if conn.execute("SELECT id FROM auth_user WHERE username=?", (username,)).fetchone():
        return
    temp_password = dob.replace("-", "")
    conn.execute(
        """
        INSERT INTO auth_user (person_id, username, password_hash, auth_level, role, first_login)
        VALUES (?, ?, ?, 'L1', 'user', 1)
        """,
        (person_id, username, hash_password(temp_password)),
    )


def lock_until_iso():
    return (utc_now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
