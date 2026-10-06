"""
Підключення ORM (SQLAlchemy).

Порядок: PostgreSQL на Railway (адреса з .env / змінної середовища / вшитого файлу в .exe).
Якщо бази немає або вона недоступна — тимчасова SQLite у пам'яті з тими самими моделями
та початковими даними, тож гра і складні запити працюють і без інтернету.
"""
import os
import sys
import threading
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_engine = None
_Session = None
_online = False
_lock = threading.Lock()


def database_url() -> Optional[str]:
    """
    Адреса бази: спершу DATABASE_URL (.env / змінна середовища),
    інакше — файл embedded.env, вшитий в MiniCafe.exe (обмежений користувач лише для гри).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    base = getattr(sys, "_MEIPASS", None)
    if base:
        try:
            with open(os.path.join(base, "embedded.env"), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            pass
    return None


def _sqlalchemy_url(url: str) -> str:
    """postgresql://... -> postgresql+psycopg2://... (драйвер для SQLAlchemy)"""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _make_sqlite():
    from database.seed import seed_reference_data
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as s:
        seed_reference_data(s)
        s.commit()
    return engine


def init():
    """Створює підключення (один раз) і повертає engine"""
    global _engine, _Session, _online
    with _lock:
        if _engine is not None:
            return _engine
        url = database_url()
        if url:
            try:
                engine = create_engine(_sqlalchemy_url(url), pool_pre_ping=True,
                                       connect_args={"connect_timeout": 5})
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                _engine, _online = engine, True
                print("[DB] Connected to Railway PostgreSQL ✓ (SQLAlchemy ORM)")
            except Exception as e:
                print(f"[DB] PostgreSQL недоступний ({str(e).splitlines()[0][:80]}) — працюю на локальній SQLite")
        if _engine is None:
            _engine, _online = _make_sqlite(), False
            print("[DB] Offline: локальна SQLite у пам'яті (ORM)")
        _Session = sessionmaker(_engine, expire_on_commit=False)
        return _engine


def is_online() -> bool:
    return _online


def backend_name() -> str:
    init()
    return "PostgreSQL (Railway)" if _online else "SQLite (локально, офлайн)"


@contextmanager
def session():
    """with session() as s: ...  — транзакція з автоматичним commit/rollback"""
    init()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def close():
    global _engine, _Session, _online
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine, _Session, _online = None, None, False
