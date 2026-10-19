import os
import json
import logging
import threading
from typing import Dict, Optional, Any
from app.core.config import settings
from app.core.security import hash_password, verify_password

logger = logging.getLogger(__name__)

USER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "users.json")


class UserService:
    def __init__(self, data_file: str = USER_DATA_FILE):
        self.data_file = data_file
        self._lock = threading.Lock()
        self._users: Dict[str, Dict[str, Any]] = {}
        self._ensure_storage_dir()
        self._load_users()
        self._seed_default_admin()

    def _ensure_storage_dir(self):
        dir_name = os.path.dirname(self.data_file)
        if dir_name and not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create user data directory: {e}")

    def _load_users(self):
        with self._lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        self._users = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading users from {self.data_file}: {e}")
                    self._users = {}

    def _save_users(self):
        # Atomic file write to avoid corrupted / 0-byte json file
        tmp_file = f"{self.data_file}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._users, f, indent=2)
            os.replace(tmp_file, self.data_file)
        except Exception as e:
            logger.error(f"Error saving users to {self.data_file}: {e}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

    def _seed_default_admin(self):
        admin_user = settings.ADMIN_USERNAME
        admin_pass = settings.ADMIN_PASSWORD
        key = admin_user.strip().lower()

        with self._lock:
            if key not in self._users:
                self._users[key] = {
                    "username": admin_user,
                    "password_hash": hash_password(admin_pass),
                    "role": "admin",
                    "is_active": True
                }
                self._save_users()

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        key = username.strip().lower()
        with self._lock:
            return self._users.get(key)

    def authenticate(self, username: str, plain_password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user(username)
        if not user or not user.get("is_active", True):
            return None

        stored_hash = user.get("password_hash", "")
        if verify_password(plain_password, stored_hash):
            return user
        return None

    def register(self, username: str, plain_password: str, role: str = "trader") -> Dict[str, Any]:
        cleaned_username = username.strip()
        if not cleaned_username:
            raise ValueError("Username cannot be empty")
        if len(plain_password) < 4:
            raise ValueError("Password must be at least 4 characters")

        key = cleaned_username.lower()

        with self._lock:
            if key in self._users:
                raise ValueError("Username already registered")

            new_user = {
                "username": cleaned_username,
                "password_hash": hash_password(plain_password),
                "role": role,
                "is_active": True
            }
            self._users[key] = new_user
            self._save_users()
            return new_user

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        user = self.authenticate(username, old_password)
        if not user:
            return False

        if len(new_password) < 4:
            raise ValueError("New password must be at least 4 characters")

        key = username.strip().lower()
        with self._lock:
            if key in self._users:
                self._users[key]["password_hash"] = hash_password(new_password)
                self._save_users()
                return True
        return False


user_service = UserService()
