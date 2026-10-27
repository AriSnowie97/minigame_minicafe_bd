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
                             Order, OrderItem, Product, CafeExpense, Player)
from database.seed import EMPLOYEES, MENU_ITEMS, TABLES

# Запасні дані на випадок збою ORM (гра не повинна падати)
_OFFLINE_MENU = [{"id": i, "name": n, "categoryid": c, "price": p, "cookingtimemin": t}
                 for i, n, c, p, t, _ in MENU_ITEMS]
_OFFLINE_TABLES = [{"id": i, "tablenumber": n, "capacity": c, "location": l} for i, n, c, l in TABLES]
_OFFLINE_EMPLOYEES = [{"id": i, "fullname": f, "position": p} for i, f, p in EMPLOYEES]


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
def create_order(table_id: int, employee_id: int, gameday: Optional[int] = None,
                 guestbreed: Optional[str] = None) -> Optional[int]:
    """Створити нове замовлення, повернути його ID."""
    try:
        with orm.session() as s:
            order = Order(tableid=table_id, employeeid=employee_id, status="відкрито",
                          gameday=gameday, guestbreed=guestbreed, orderdatetime=datetime.now())
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


def assign_waiter(order_id: int, waiter_id: int) -> bool:
    """Записати, який офіціант розніс замовлення гостю."""
    try:
        with orm.session() as s:
            order = s.get(Order, order_id)
            if order is None:
                return False
            order.waiterid = waiter_id
        return True
    except Exception as e:
        print(f"[DB] assign_waiter: {e}")
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


def log_supply_expense(gameday: int, menu_item_id: int, quantity: int, cost: float) -> bool:
    """Записати витрати на закупівлю партії продуктів машинки."""
    try:
        with orm.session() as s:
            s.add(CafeExpense(gameday=gameday, menuitemid=menu_item_id, quantity=quantity, cost=float(cost)))
        return True
    except Exception as e:
        print(f"[DB] log_supply_expense: {e}")
        return False


def get_total_expenses(gameday: Optional[int] = None) -> float:
    """Сумарні витрати на продукти за день (або за всю гру)."""
    try:
        with orm.session() as s:
            stmt = select(func.coalesce(func.sum(CafeExpense.cost), 0))
            if gameday is not None:
                stmt = stmt.where(CafeExpense.gameday == gameday)
            return float(s.scalar(stmt) or 0)
    except Exception as e:
        print(f"[DB] get_total_expenses: {e}")
        return 0.0


def save_player_stats(name: str, money: int, days_played: int, orders_done: int, rating: float) -> bool:
    """Зберегти або оновити статистику гравця для онлайн/локальної таблиці рекордів."""
    if not name or not name.strip():
        name = "Котик Гравець"
    name = name.strip()
    try:
        with orm.session() as s:
            player = s.scalar(select(Player).where(Player.name == name))
            if player is None:
                player = Player(name=name, total_money=int(money), days_played=int(days_played),
                                orders_done=int(orders_done), rating=float(rating), updated_at=datetime.now())
                s.add(player)
            else:
                player.total_money = max(player.total_money, int(money))
                player.days_played = max(player.days_played, int(days_played))
                player.orders_done = max(player.orders_done, int(orders_done))
                player.rating = round(float(rating), 2)
                player.updated_at = datetime.now()
        return True
    except Exception as e:
        print(f"[DB] save_player_stats: {e}")
        return False


def get_top_players(limit: int = 10) -> list:
    """Отримати найкращих гравців за заробленими монетами."""
    try:
        with orm.session() as s:
            stmt = (select(Player)
                    .order_by(Player.total_money.desc(), Player.orders_done.desc())
                    .limit(limit))
            rows = s.scalars(stmt).all()
            return [{"id": p.id, "name": p.name, "total_money": p.total_money,
                     "days_played": p.days_played, "orders_done": p.orders_done,
                     "rating": float(p.rating)} for p in rows]
    except Exception as e:
        print(f"[DB] get_top_players: {e}")
        return []

