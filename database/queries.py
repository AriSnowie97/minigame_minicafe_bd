"""
Все SQL-запросы к БД кафе.
Если соединение недоступно — возвращаем встроенные данные (offline fallback).
"""
from database.connection import execute

# ===========================================================
# Встроенные данные (fallback без интернета / БД)
# ===========================================================
_OFFLINE_MENU = [
    {"id": 1, "name": "Кава",      "categoryid": 1, "price": 50.00,  "cookingtimemin": 4},
    {"id": 2, "name": "Чай",       "categoryid": 1, "price": 40.00,  "cookingtimemin": 3},
    {"id": 3, "name": "Печиво",    "categoryid": 2, "price": 65.00,  "cookingtimemin": 5},
    {"id": 4, "name": "Айс Лате",  "categoryid": 1, "price": 85.00,  "cookingtimemin": 6},
    {"id": 5, "name": "Тортик",    "categoryid": 2, "price": 110.00, "cookingtimemin": 8},
    # Страви шеф-кухаря (доступні після найму кота-кухаря)
    {"id": 6,  "name": "Брускета",        "categoryid": 5, "price": 70.00,  "cookingtimemin": 5},
    {"id": 7,  "name": "Сирники",         "categoryid": 2, "price": 90.00,  "cookingtimemin": 6},
    {"id": 8,  "name": "Омлет з беконом", "categoryid": 2, "price": 100.00, "cookingtimemin": 7},
    {"id": 9,  "name": "Салат Цезар",     "categoryid": 3, "price": 105.00, "cookingtimemin": 6},
    {"id": 10, "name": "Тірамісу",        "categoryid": 4, "price": 120.00, "cookingtimemin": 7},
    {"id": 11, "name": "Борщ",            "categoryid": 3, "price": 130.00, "cookingtimemin": 8},
    {"id": 12, "name": "Лате",            "categoryid": 1, "price": 60.00,  "cookingtimemin": 4},
    {"id": 13, "name": "Кава з собою",    "categoryid": 1, "price": 45.00,  "cookingtimemin": 3},
    {"id": 14, "name": "Круасан",         "categoryid": 2, "price": 55.00,  "cookingtimemin": 4},
    {"id": 15, "name": "Капучино",        "categoryid": 1, "price": 65.00,  "cookingtimemin": 4},
]

_OFFLINE_TABLES = [
    {"id": 1, "tablenumber": 1, "capacity": 2, "location": "зал"},
    {"id": 2, "tablenumber": 2, "capacity": 2, "location": "зал"},
    {"id": 3, "tablenumber": 3, "capacity": 4, "location": "зал"},
    {"id": 4, "tablenumber": 4, "capacity": 4, "location": "зал"},
    {"id": 9, "tablenumber": 9, "capacity": 2, "location": "зал"},
    {"id": 10, "tablenumber": 10, "capacity": 2, "location": "зал"},
    {"id": 5, "tablenumber": 5, "capacity": 2, "location": "тераса"},
    {"id": 6, "tablenumber": 6, "capacity": 4, "location": "тераса"},
    {"id": 7, "tablenumber": 7, "capacity": 2, "location": "тераса"},
    {"id": 8, "tablenumber": 8, "capacity": 4, "location": "тераса"},
]

_OFFLINE_EMPLOYEES = [
    {"id": 1, "fullname": "Коваленко Ірина",   "position": "бариста"},
    {"id": 2, "fullname": "Петренко Олег",     "position": "офіціант"},
    {"id": 3, "fullname": "Сидоренко Марія",   "position": "кухар"},
    {"id": 4, "fullname": "Бондаренко Андрій", "position": "адміністратор"},
]


# ===========================================================
# Запросы на чтение
# ===========================================================
def get_menu_items() -> list:
    rows = execute("SELECT id, name, categoryid, price, cookingtimemin FROM MenuItems ORDER BY categoryid, id", fetch="all")
    if not rows:
        return _OFFLINE_MENU
    items = [dict(r) for r in rows]
    known = {it["id"] for it in items}
    return items + [it for it in _OFFLINE_MENU if it["id"] not in known]


def get_tables() -> list:
    rows = execute("SELECT id, tablenumber, capacity, location FROM CafeTables ORDER BY tablenumber", fetch="all")
    if not rows:
        return _OFFLINE_TABLES
    tables = [dict(r) for r in rows]
    known = {t["tablenumber"] for t in tables}
    return tables + [t for t in _OFFLINE_TABLES if t["tablenumber"] not in known]


def get_employees() -> list:
    rows = execute("SELECT id, fullname, position FROM Employees ORDER BY id", fetch="all")
    return [dict(r) for r in rows] if rows else _OFFLINE_EMPLOYEES


def get_menu_categories() -> list:
    rows = execute("SELECT id, name FROM MenuCategories ORDER BY id", fetch="all")
    return [dict(r) for r in rows] if rows else []


def get_ingredients(menu_item_id: int) -> list:
    rows = execute(
        """SELECT p.name, mii.quantity, p.unit
           FROM MenuItemIngredients mii
           JOIN Products p ON p.id = mii.productid
           WHERE mii.menuitemid = %s""",
        (menu_item_id,), fetch="all"
    )
    return [dict(r) for r in rows] if rows else []


# ===========================================================
# Запросы на запись (игровые события)
# ===========================================================
def create_order(table_id: int, employee_id: int) -> Optional[int]:
    """Создать новый заказ, вернуть его ID."""
    row = execute(
        """INSERT INTO Orders (tableid, employeeid, orderdatetime, status)
           VALUES (%s, %s, NOW(), 'відкрито')
           RETURNING id""",
        (table_id, employee_id), fetch="one"
    )
    return row["id"] if row else None


def add_order_item(order_id: int, menu_item_id: int, quantity: int, price: float) -> bool:
    """Добавить позицию к заказу."""
    result = execute(
        """INSERT INTO OrderItems (orderid, menuitemid, quantity, priceatorder)
           VALUES (%s, %s, %s, %s)""",
        (order_id, menu_item_id, quantity, price)
    )
    return result is not None


def complete_order(order_id: int) -> bool:
    """Пометить заказ как оплаченный."""
    result = execute(
        "UPDATE Orders SET status = 'оплачено' WHERE id = %s",
        (order_id,)
    )
    return result is not None


def cancel_order(order_id: int) -> bool:
    """Пометить заказ как скасований."""
    result = execute(
        "UPDATE Orders SET status = 'скасовано' WHERE id = %s",
        (order_id,)
    )
    return result is not None


def get_day_stats() -> dict:
    """Статистика за сегодня."""
    row = execute(
        """SELECT
             COUNT(*) FILTER (WHERE status = 'оплачено') AS completed,
             COUNT(*) FILTER (WHERE status = 'скасовано') AS cancelled,
             COALESCE(SUM(oi.priceatorder * oi.quantity)
               FILTER (WHERE o.status = 'оплачено'), 0) AS earned
           FROM Orders o
           LEFT JOIN OrderItems oi ON oi.orderid = o.id
           WHERE o.orderdatetime::date = CURRENT_DATE""",
        fetch="one"
    )
    return dict(row) if row else {"completed": 0, "cancelled": 0, "earned": 0}


# Аннотация типа для Optional (совместимость Python 3.9)
from typing import Optional
