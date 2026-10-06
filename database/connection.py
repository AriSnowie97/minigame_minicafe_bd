"""
Подключение к PostgreSQL (Railway).
Автоматический фолбэк на встроенные данные если .env не задан.
"""
import os
import sys
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


def _database_url() -> Optional[str]:
    """
    Адрес базы: сначала DATABASE_URL (.env / змінна середовища),
    інакше — файл embedded.env, вшитий в MiniCafe.exe (обмежений користувач лише для гри).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    base = getattr(sys, "_MEIPASS", None)
    if base:
        path = os.path.join(base, "embedded.env")
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            pass
    return None


def get_connection():
    """
    Возвращает активное соединение с БД или None (offline mode).
    """
    global _connection, _is_online

    if not _PSYCOPG2_OK:
        return None

    db_url = _database_url()
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
            result = True
            if fetch == "one":
                result = cur.fetchone()
            elif fetch == "all":
                result = cur.fetchall()
            conn.commit()   # запис (INSERT ... RETURNING) теж має зберігатися
            return result
    except Exception as e:
        print(f"[DB] Query error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None
