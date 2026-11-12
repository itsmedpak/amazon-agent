import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import streamlit as st

from config import LOCK_SECONDS, MAX_FAILED_ATTEMPTS, MIN_PASSWORD_LENGTH
from database import connect

ITERATIONS = 600_000


def init_auth():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT,          -- NULL = initial empty password
                salt TEXT,
                iterations INTEGER,
                must_change INTEGER NOT NULL DEFAULT 1,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT
            )
        """)
        conn.execute("INSERT OR IGNORE INTO auth (id, must_change) VALUES (1, 1)")


def _row():
    with connect() as conn:
        return dict(conn.execute("SELECT * FROM auth WHERE id = 1").fetchone())


def _hash(password, salt_hex, iterations):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations
    ).hex()


def _matches(row, password):
    if row["password_hash"] is None:
        return password == ""
    candidate = _hash(password, row["salt"], row["iterations"])
    return hmac.compare_digest(candidate, row["password_hash"])


def is_initial():
    return _row()["password_hash"] is None


def state():
    """'logged_out' | 'must_change' | 'ok'. must_change is read from the DB each run."""
    if not st.session_state.get("auth"):
        return "logged_out"
    return "must_change" if _row()["must_change"] else "ok"


def login(password):
    row = _row()
    now = datetime.now(timezone.utc)

    if row["locked_until"]:
        until = datetime.fromisoformat(row["locked_until"])
        if until > now:
            secs = int((until - now).total_seconds()) + 1
            return False, f"Too many failed attempts. Try again in {secs} seconds."

    if _matches(row, password):
        with connect() as conn:
            conn.execute("UPDATE auth SET failed_attempts = 0, locked_until = NULL WHERE id = 1")
        st.session_state["auth"] = True
        return True, ""

    fails = row["failed_attempts"] + 1
    locked, msg = None, "Incorrect password."
    if fails >= MAX_FAILED_ATTEMPTS:
        locked = (now + timedelta(seconds=LOCK_SECONDS)).isoformat(timespec="seconds")
        fails = 0
        msg = f"Too many failed attempts. Login is locked for {LOCK_SECONDS // 60} minutes."
    with connect() as conn:
        conn.execute("UPDATE auth SET failed_attempts = ?, locked_until = ? WHERE id = 1",
                     (fails, locked))
    return False, msg


def change_password(current, new, confirm):
    row = _row()
    if not _matches(row, current):
        return False, "Current password is incorrect."
    if not new:
        return False, "New password cannot be empty."
    if len(new) < MIN_PASSWORD_LENGTH:
        return False, f"New password must be at least {MIN_PASSWORD_LENGTH} characters."
    if new != confirm:
        return False, "New password and confirmation do not match."
    if new == current:
        return False, "New password must be different from the current password."

    salt = secrets.token_hex(16)
    with connect() as conn:
        conn.execute(
            "UPDATE auth SET password_hash = ?, salt = ?, iterations = ?, must_change = 0, "
            "failed_attempts = 0, locked_until = NULL WHERE id = 1",
            (_hash(new, salt, ITERATIONS), salt, ITERATIONS),
        )
    return True, "Password updated."


def logout():
    st.session_state.clear()


if __name__ == "__main__":
    # Recovery if the password is forgotten:  python auth.py --reset
    import sys
    if "--reset" in sys.argv:
        init_auth()
        with connect() as conn:
            conn.execute(
                "UPDATE auth SET password_hash = NULL, salt = NULL, iterations = NULL, "
                "must_change = 1, failed_attempts = 0, locked_until = NULL WHERE id = 1"
            )
        print("Password reset. Next login uses an empty password and forces a new one.")