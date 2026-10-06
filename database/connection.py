"""
Підключення до бази даних. Вся робота з БД виконується через ORM (SQLAlchemy),
див. database/orm.py (engine і сесії), database/models.py (моделі), database/queries.py та
database/stats.py (запити).
"""
from database import orm


def get_connection():
    """Ініціалізує ORM. Повертає engine, якщо підключено PostgreSQL (Railway), інакше None (офлайн)."""
    engine = orm.init()
    return engine if orm.is_online() else None


def is_online() -> bool:
    return orm.is_online()


def close():
    orm.close()
