"""
Запити гри до бази даних через ORM (SQLAlchemy).
Працюють і з PostgreSQL на Railway, і з локальною SQLite (див. database/orm.py).
Складні аналітичні запити (JOIN, GROUP BY, підзапити, віконні функції) — у database/stats.py.
"""
from datetime import datetime, time
from typing import Optional

from sqlalchemy import case, func, select

from database import orm
from database.models import (CafeTable, Employee, MenuCategory, MenuItem, MenuItemIngredient,
                             Order, OrderItem, Product)
from database.seed import EMPLOYEES, MENU_ITEMS, TABLES

# Запасні дані на випадок збою ORM (гра не повинна падати)
_OFFLINE_MENU = [{"id": i, "name": n, "categoryid": c, "price": p, "cookingtimemin": t}
                 for i, n, c, p, t, _ in MENU_ITEMS]
_OFFLINE_TABLES = [{"id": i, "tablenumber": n, "capacity": c, "location": l} for i, n, c, l in TABLES]
_OFFLINE_EMPLOYEES = [{"id": i, "fullname": f, "position": p} for i, f, p, _, _ in EMPLOYEES]


# ===========================================================
# Довідкові запити (читання)
# ===========================================================
def get_menu_items() -> list:
    """Усі страви меню: SELECT * FROM menuitems ORDER BY categoryid, id"""
    try:
        with orm.session() as s:
            rows = s.scalars(select(MenuItem).order_by(MenuItem.categoryid, MenuItem.id)).all()
            items = [{"id": m.id, "name": m.name, "categoryid": m.categoryid,
                      "price": float(m.price), "cookingtimemin": m.cookingtimemin} for m in rows]
    except Exception as e:
        print(f"[DB] get_menu_items: {e}")
        return _OFFLINE_MENU
    known = {it["id"] for it in items}
    return items + [it for it in _OFFLINE_MENU if it["id"] not in known]


def get_tables() -> list:
    try:
        with orm.session() as s:
            rows = s.scalars(select(CafeTable).order_by(CafeTable.tablenumber)).all()
            tables = [{"id": t.id, "tablenumber": t.tablenumber, "capacity": t.capacity,
                       "location": t.location} for t in rows]
    except Exception as e:
        print(f"[DB] get_tables: {e}")
        return _OFFLINE_TABLES
    known = {t["tablenumber"] for t in tables}
    return tables + [t for t in _OFFLINE_TABLES if t["tablenumber"] not in known]


def get_employees() -> list:
    try:
        with orm.session() as s:
            rows = s.scalars(select(Employee).order_by(Employee.id)).all()
            emps = [{"id": e.id, "fullname": e.fullname, "position": e.position} for e in rows]
        return emps or _OFFLINE_EMPLOYEES
    except Exception as e:
        print(f"[DB] get_employees: {e}")
        return _OFFLINE_EMPLOYEES


def get_menu_categories() -> list:
    try:
        with orm.session() as s:
            return [{"id": c.id, "name": c.name} for c in s.scalars(select(MenuCategory).order_by(MenuCategory.id))]
    except Exception as e:
        print(f"[DB] get_menu_categories: {e}")
        return []


def get_ingredients(menu_item_id: int) -> list:
    """Склад страви: JOIN menuitemingredients -> products"""
    try:
        with orm.session() as s:
            stmt = (select(Product.name, MenuItemIngredient.quantity, Product.unit)
                    .join(MenuItemIngredient, MenuItemIngredient.productid == Product.id)
                    .where(MenuItemIngredient.menuitemid == menu_item_id))
            return [{"name": n, "quantity": q, "unit": u} for n, q, u in s.execute(stmt)]
    except Exception as e:
        print(f"[DB] get_ingredients: {e}")
        return []


# ===========================================================
# Запити на запис (ігрові події)
# ===========================================================
def create_order(table_id: int, employee_id: int, gameday: Optional[int] = None) -> Optional[int]:
    """Створити нове замовлення, повернути його ID."""
    try:
        with orm.session() as s:
            order = Order(tableid=table_id, employeeid=employee_id, status="відкрито",
                          gameday=gameday, orderdatetime=datetime.now())
            s.add(order)
            s.flush()
            return order.id
    except Exception as e:
        print(f"[DB] create_order: {e}")
        return None


def add_order_item(order_id: int, menu_item_id: int, quantity: int, price: float) -> bool:
    """Додати позицію до замовлення."""
    try:
        with orm.session() as s:
            s.add(OrderItem(orderid=order_id, menuitemid=menu_item_id, quantity=quantity,
                            priceatorder=float(price)))
        return True
    except Exception as e:
        print(f"[DB] add_order_item: {e}")
        return False


def _set_status(order_id: int, status: str) -> bool:
    try:
        with orm.session() as s:
            order = s.get(Order, order_id)
            if order is None:
                return False
            order.status = status
        return True
    except Exception as e:
        print(f"[DB] set_status: {e}")
        return False


def complete_order(order_id: int) -> bool:
    """Замовлення оплачено."""
    return _set_status(order_id, "оплачено")


def cancel_order(order_id: int) -> bool:
    """Замовлення скасовано (гість пішов, не дочекавшись)."""
    return _set_status(order_id, "скасовано")


def get_day_stats() -> dict:
    """Статистика за сьогодні: LEFT JOIN + умовні агрегати (CASE)"""
    try:
        with orm.session() as s:
            line = OrderItem.quantity * OrderItem.priceatorder
            stmt = (select(
                        func.count(func.distinct(case((Order.status == "оплачено", Order.id)))),
                        func.count(func.distinct(case((Order.status == "скасовано", Order.id)))),
                        func.coalesce(func.sum(case((Order.status == "оплачено", line), else_=0)), 0))
                    .select_from(Order).outerjoin(OrderItem, OrderItem.orderid == Order.id)
                    .where(Order.orderdatetime >= datetime.combine(datetime.now().date(), time.min)))
            done, cancelled, earned = s.execute(stmt).one()
            return {"completed": done, "cancelled": cancelled, "earned": float(earned)}
    except Exception as e:
        print(f"[DB] get_day_stats: {e}")
        return {"completed": 0, "cancelled": 0, "earned": 0}
