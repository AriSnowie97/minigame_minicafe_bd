"""
Подключение к PostgreSQL (Railway).
Автоматический фолбэк на встроенные данные если .env не задан.
"""
import os
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG2_OK = True
except ImportError:
    _PSYCOPG2_OK = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_connection = None
_is_online  = False


def get_connection():
    """
    Возвращает активное соединение с БД или None (offline mode).
    """
    global _connection, _is_online

    if not _PSYCOPG2_OK:
        return None

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    try:
        if _connection is None or _connection.closed:
            _connection = psycopg2.connect(db_url, connect_timeout=5)
            _connection.autocommit = False
            _is_online = True
            print("[DB] Connected to Railway PostgreSQL ✓")
        return _connection
    except Exception as e:
        print(f"[DB] Connection failed: {e}")
        _is_online = False
        return None


def is_online() -> bool:
    return _is_online


def close():
    global _connection, _is_online
    if _connection and not _connection.closed:
        _connection.close()
    _connection = None
    _is_online  = False


def execute(sql: str, params=None, fetch: str = "none"):
    """
    Выполнить SQL.
    fetch: 'one' | 'all' | 'none'
    Возвращает результат или None при ошибке.
    """
    conn = get_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == "one":
                return cur.fetchone()
            elif fetch == "all":
                return cur.fetchall()
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB] Query error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None
