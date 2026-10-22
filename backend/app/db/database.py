import os
import json
import time
import secrets
import sqlite3
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.security import hash_password

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_FILE = os.path.join(DB_DIR, "tradegear.db")
LEGACY_USERS_JSON = os.path.join(DB_DIR, "users.json")
LEGACY_SETTINGS_JSON = os.path.join(DB_DIR, "account_settings.json")


def generate_bridge_token() -> str:
    """Generate a secure, high-entropy bridge token."""
    return f"tg_live_{secrets.token_hex(16)}"


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    """Initialize database tables and run migration if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'trader',
                bridge_token TEXT UNIQUE NOT NULL,
                token_version INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_bridge_token ON users(bridge_token);
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_settings (
                user_id INTEGER PRIMARY KEY,
                custom_initial_deposit REAL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        conn.commit()

    _migrate_legacy_data()
    _seed_default_admin()


def _migrate_legacy_data():
    """Migrate legacy users.json and account_settings.json to SQLite if present."""
    if not os.path.exists(LEGACY_USERS_JSON):
        return

    try:
        with open(LEGACY_USERS_JSON, "r", encoding="utf-8") as f:
            legacy_users: Dict[str, Any] = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read legacy users file for migration: {e}")
        return

    now = int(time.time())
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for key, udata in legacy_users.items():
            username = udata.get("username", key).strip()
            if not username:
                continue

            # Check if user already in DB
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                continue

            pw_hash = udata.get("password_hash", "")
            role = udata.get("role", "trader")
            is_active = 1 if udata.get("is_active", True) else 0
            bridge_token = generate_bridge_token()

            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, bridge_token, token_version, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (username, pw_hash, role, bridge_token, is_active, now, now)
            )

        # Migrate custom initial deposit if settings file exists
        if os.path.exists(LEGACY_SETTINGS_JSON):
            try:
                with open(LEGACY_SETTINGS_JSON, "r", encoding="utf-8") as sf:
                    settings_data = json.load(sf)
                    deposit_val = settings_data.get("custom_initial_deposit")
                    if deposit_val is not None:
                        # Assign to admin user
                        cursor.execute("SELECT id FROM users WHERE username = ?", (settings.ADMIN_USERNAME,))
                        admin_row = cursor.fetchone()
                        if admin_row:
                            cursor.execute(
                                """
                                INSERT OR REPLACE INTO account_settings (user_id, custom_initial_deposit, updated_at)
                                VALUES (?, ?, ?)
                                """,
                                (admin_row["id"], float(deposit_val), now)
                            )
            except Exception as se:
                logger.warning(f"Could not migrate legacy account settings: {se}")

        conn.commit()

    # Rename migrated files to prevent re-processing
    try:
        os.rename(LEGACY_USERS_JSON, f"{LEGACY_USERS_JSON}.migrated")
        if os.path.exists(LEGACY_SETTINGS_JSON):
            os.rename(LEGACY_SETTINGS_JSON, f"{LEGACY_SETTINGS_JSON}.migrated")
        logger.info("Successfully migrated legacy JSON user data to SQLite database.")
    except Exception as e:
        logger.warning(f"Could not rename legacy JSON files: {e}")


def _seed_default_admin():
    """Ensure default admin account exists in database."""
    admin_user = settings.ADMIN_USERNAME.strip()
    admin_pass = settings.ADMIN_PASSWORD
    now = int(time.time())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (admin_user,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, bridge_token, token_version, is_active, created_at, updated_at)
                VALUES (?, ?, 'admin', ?, 1, 1, ?, ?)
                """,
                (admin_user, hash_password(admin_pass), generate_bridge_token(), now, now)
            )
            conn.commit()
            logger.info(f"Seeded default admin user '{admin_user}' in SQLite database.")
