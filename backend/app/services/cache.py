"""Caché clave-valor en SQLite con expiración, para no saturar APIs públicas."""
import hashlib
import json
import sqlite3
import threading
import time
from typing import Any

from app.config import CACHE_PATH

_lock = threading.Lock()
_conn = sqlite3.connect(CACHE_PATH, check_same_thread=False)
_conn.execute(
    "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)"
)
_conn.commit()


def make_key(*parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(key: str) -> Any | None:
    with _lock:
        row = _conn.execute("SELECT value, expires FROM cache WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    value, expires = row
    if expires < time.time():
        return None
    return json.loads(value)


def set(key: str, value: Any, ttl_s: float) -> None:
    with _lock:
        _conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), time.time() + ttl_s),
        )
        _conn.commit()
