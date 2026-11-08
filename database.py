"""App database: users + Dialect Lab analysis history (SQLite)."""
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("dialectmood.db")


@contextmanager
def get_connection():
    """Commit on success, roll back on error, ALWAYS close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                dialect TEXT,
                sentiment TEXT,
                confidence REAL,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, id)")


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               salt.encode("utf-8"), 260000).hex()


def register_user(name, email, password):
    salt = secrets.token_hex(16)
    hashed = hash_password(password, salt)
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (name, email, salt, password_hash) VALUES (?, ?, ?, ?)",
                (name.strip(), email.strip().lower(), salt, hashed))
        return True, "Account created successfully. Now sign in."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."


def authenticate_user(email, password):
    if not email or not password:
        return None
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?",
                            (email.strip().lower(),)).fetchone()
    if not user:
        return None
    entered = hash_password(password, user["salt"])
    if not secrets.compare_digest(entered, user["password_hash"]):
        return None
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


def save_analysis(user_id, text, dialect, sentiment, confidence, explanation):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO analyses (user_id, text, dialect, sentiment, confidence, explanation) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, text, dialect, sentiment, confidence, explanation))


def get_history(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, text, dialect, sentiment, confidence, explanation, created_at "
            "FROM analyses WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]
