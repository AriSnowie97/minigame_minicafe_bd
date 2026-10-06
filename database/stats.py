"""
Складні аналітичні запити MiniCafe (SQLAlchemy ORM).

Використовуються на екрані «Статистика» в грі. Кожна функція — один запит, у якому є
JOIN кількох таблиць, GROUP BY / HAVING, а також підзапити та віконні функції
(RANK, SUM() OVER, ...). Запити однаково працюють у PostgreSQL та SQLite.
"""
from sqlalchemy import case, func, select

from database import orm
from database.models import (CafeTable, Employee, MenuCategory, MenuItem, MenuItemIngredient,
                             Order, OrderItem, Product)
from database.seed import add_demo_orders

PAID = Order.status == "оплачено"
CANCELLED = Order.status == "скасовано"
LINE_SUM = OrderItem.quantity * OrderItem.priceatorder        # сума позиції замовлення


def _clean(value):
    """None -> 0, число -> float (для виводу в таблиці)"""
    if value is None:
        return 0
    try:
        return float(value) if not isinstance(value, (int, str)) else value
    except (TypeError, ValueError):
        return value


def _run(stmt) -> list:
    with orm.session() as s:
        return [tuple(_clean(v) for v in row) for row in s.execute(stmt).all()]


# ----------------------------------------------------------------
# 1. Топ страв: JOIN 4 таблиць + GROUP BY + HAVING + RANK() OVER (PARTITION BY категорія)
# ----------------------------------------------------------------
def top_dishes(limit: int = 10) -> list:
    """(страва, категорія, продано, виручка, місце всередині своєї категорії)"""
    revenue = func.sum(LINE_SUM)
    stmt = (select(MenuItem.name, MenuCategory.name,
                   func.sum(OrderItem.quantity), revenue,
                   func.rank().over(partition_by=MenuCategory.id, order_by=revenue.desc()))
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.orderid)
            .join(MenuItem, MenuItem.id == OrderItem.menuitemid)
            .join(MenuCategory, MenuCategory.id == MenuItem.categoryid)
            .where(PAID)
            .group_by(MenuItem.id, MenuItem.name, MenuCategory.id, MenuCategory.name)
            .having(func.sum(OrderItem.quantity) > 0)
            .order_by(revenue.desc())
            .limit(limit))
    return _run(stmt)


# ----------------------------------------------------------------
# 2. Виручка по ігрових днях: підзапит (сума кожного замовлення) + умовні агрегати
#    + накопичувальна сума SUM() OVER (ORDER BY день)
# ----------------------------------------------------------------
def revenue_by_gameday() -> list:
    """(день, оплачено, скасовано, виручка, середній чек, виручка наростаючим підсумком)"""
    per_order = (select(Order.id.label("oid"), Order.gameday.label("day"), Order.status.label("st"),
                        func.sum(LINE_SUM).label("total"))
                 .select_from(Order).join(OrderItem, OrderItem.orderid == Order.id)
                 .group_by(Order.id, Order.gameday, Order.status)
                 .subquery())
    is_paid = per_order.c.st == "оплачено"
    revenue = func.sum(case((is_paid, per_order.c.total), else_=0))
    stmt = (select(per_order.c.day,
                   func.sum(case((is_paid, 1), else_=0)),
                   func.sum(case((per_order.c.st == "скасовано", 1), else_=0)),
                   revenue,
                   func.avg(case((is_paid, per_order.c.total))),
                   func.sum(revenue).over(order_by=per_order.c.day))
            .group_by(per_order.c.day)
            .order_by(per_order.c.day))
    return _run(stmt)


# ----------------------------------------------------------------
# 3. Співробітники: LEFT JOIN трьох таблиць + скалярний підзапит (частка від загальної виручки)
# ----------------------------------------------------------------
def employee_stats() -> list:
    """(співробітник, посада, оплачено, скасовано, виручка, частка % від усієї виручки)"""
    total_paid = (select(func.coalesce(func.sum(LINE_SUM), 0))
                  .select_from(OrderItem).join(Order, Order.id == OrderItem.orderid)
                  .where(PAID).scalar_subquery())
    revenue = func.coalesce(func.sum(case((PAID, LINE_SUM), else_=0)), 0)
    stmt = (select(Employee.fullname, Employee.position,
                   func.count(func.distinct(case((PAID, Order.id)))),
                   func.count(func.distinct(case((CANCELLED, Order.id)))),
                   revenue,
                   100.0 * revenue / func.nullif(total_paid, 0))
            .select_from(Employee)
            .outerjoin(Order, Order.employeeid == Employee.id)
            .outerjoin(OrderItem, OrderItem.orderid == Order.id)
            .group_by(Employee.id, Employee.fullname, Employee.position)
            .order_by(revenue.desc()))
    return _run(stmt)


# ----------------------------------------------------------------
# 4. Столики: LEFT JOIN + похідний показник (середній чек = виручка / кількість замовлень)
# ----------------------------------------------------------------
def table_stats() -> list:
    """(№ столика, розташування, оплачено замовлень, виручка, середній чек)"""
    paid_orders = func.count(func.distinct(case((PAID, Order.id))))
    revenue = func.coalesce(func.sum(case((PAID, LINE_SUM), else_=0)), 0)
    stmt = (select(CafeTable.tablenumber, CafeTable.location, paid_orders, revenue,
                   revenue / func.nullif(paid_orders, 0))
            .select_from(CafeTable)
            .outerjoin(Order, Order.tableid == CafeTable.id)
            .outerjoin(OrderItem, OrderItem.orderid == Order.id)
            .group_by(CafeTable.id, CafeTable.tablenumber, CafeTable.location)
            .order_by(revenue.desc(), CafeTable.tablenumber))
    return _run(stmt)


# ----------------------------------------------------------------
# 5. Категорії меню: частка кожної категорії через SUM(SUM(...)) OVER ()
# ----------------------------------------------------------------
def category_stats() -> list:
    """(категорія, продано, виручка, частка % від усієї виручки)"""
    revenue = func.sum(LINE_SUM)
    stmt = (select(MenuCategory.name, func.sum(OrderItem.quantity), revenue,
                   100.0 * revenue / func.sum(revenue).over())
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.orderid)
            .join(MenuItem, MenuItem.id == OrderItem.menuitemid)
            .join(MenuCategory, MenuCategory.id == MenuItem.categoryid)
            .where(PAID)
            .group_by(MenuCategory.id, MenuCategory.name)
            .order_by(revenue.desc()))
    return _run(stmt)


# ----------------------------------------------------------------
# 6. Витрата продуктів: JOIN п'яти таблиць (замовлення -> страви -> склад -> продукти)
# ----------------------------------------------------------------
def product_usage() -> list:
    """(продукт, одиниця, витрачено, вартість)"""
    used = func.sum(OrderItem.quantity * MenuItemIngredient.quantity)
    cost = used * Product.unitprice
    stmt = (select(Product.name, Product.unit, used, cost)
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.orderid)
            .join(MenuItemIngredient, MenuItemIngredient.menuitemid == OrderItem.menuitemid)
            .join(Product, Product.id == MenuItemIngredient.productid)
            .where(PAID)
            .group_by(Product.id, Product.name, Product.unit, Product.unitprice)
            .having(used > 0)
            .order_by(cost.desc()))
    return _run(stmt)


# ----------------------------------------------------------------
# 7. Прибутковість страв: підзапит із собівартістю страви (сума продуктів складу) + JOIN
# ----------------------------------------------------------------
def dish_profit() -> list:
    """(страва, продано, виручка, собівартість, прибуток, маржа %)"""
    unit_cost = (select(MenuItemIngredient.menuitemid.label("mid"),
                        func.sum(MenuItemIngredient.quantity * Product.unitprice).label("cost"))
                 .select_from(MenuItemIngredient)
                 .join(Product, Product.id == MenuItemIngredient.productid)
                 .group_by(MenuItemIngredient.menuitemid)
                 .subquery())
    revenue = func.sum(LINE_SUM)
    cost = func.sum(OrderItem.quantity * func.coalesce(unit_cost.c.cost, 0))
    stmt = (select(MenuItem.name, func.sum(OrderItem.quantity), revenue, cost,
                   revenue - cost, 100.0 * (revenue - cost) / func.nullif(revenue, 0))
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.orderid)
            .join(MenuItem, MenuItem.id == OrderItem.menuitemid)
            .outerjoin(unit_cost, unit_cost.c.mid == OrderItem.menuitemid)
            .where(PAID)
            .group_by(MenuItem.id, MenuItem.name)
            .order_by((revenue - cost).desc()))
    return _run(stmt)


# ----------------------------------------------------------------
# Допоміжне
# ----------------------------------------------------------------
def orders_count() -> int:
    with orm.session() as s:
        return s.scalar(select(func.count(Order.id))) or 0


def add_demo_data() -> int:
    """Додає демонстраційну історію замовлень (для показу статистики)"""
    with orm.session() as s:
        return add_demo_orders(s)
