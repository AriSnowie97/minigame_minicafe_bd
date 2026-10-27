"""
Складні аналітичні запити MiniCafe (SQLAlchemy ORM).

Використовуються на екрані «Статистика» в грі. Кожна функція — один запит, у якому є
JOIN кількох таблиць, GROUP BY / HAVING, а також підзапити та віконні функції
(RANK, SUM() OVER, ...). Запити однаково працюють у PostgreSQL та SQLite.
"""
from sqlalchemy import case, func, select

from database import orm
from database.models import (CafeTable, Employee, MenuCategory, MenuItem, MenuItemIngredient,
                             Order, OrderItem, Product, CafeExpense, Player)
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
    """(день, оплачено, виручка, витрати на закупівлю, чистий прибуток, наростаючим)"""
    per_order = (select(Order.id.label("oid"), Order.gameday.label("day"), Order.status.label("st"),
                        func.sum(LINE_SUM).label("total"))
                 .select_from(Order).join(OrderItem, OrderItem.orderid == Order.id)
                 .group_by(Order.id, Order.gameday, Order.status)
                 .subquery())
    is_paid = per_order.c.st == "оплачено"
    rev_sub = (select(per_order.c.day.label("day"),
                      func.sum(case((is_paid, 1), else_=0)).label("paid_cnt"),
                      func.sum(case((is_paid, per_order.c.total), else_=0)).label("revenue"))
               .group_by(per_order.c.day)
               .subquery())
    exp_sub = (select(CafeExpense.gameday.label("day"),
                      func.sum(CafeExpense.cost).label("expenses"))
               .group_by(CafeExpense.gameday)
               .subquery())

    revenue = func.coalesce(rev_sub.c.revenue, 0)
    expenses = func.coalesce(exp_sub.c.expenses, 0)
    profit = revenue - expenses

    stmt = (select(rev_sub.c.day,
                   rev_sub.c.paid_cnt,
                   revenue,
                   expenses,
                   profit,
                   func.sum(profit).over(order_by=rev_sub.c.day))
            .select_from(rev_sub)
            .outerjoin(exp_sub, exp_sub.c.day == rev_sub.c.day)
            .order_by(rev_sub.c.day))
    return _run(stmt)



# ----------------------------------------------------------------
# 3. Персонал: корельовані скалярні підзапити (приготовано / рознесено / скасовано / виручка)
# ----------------------------------------------------------------
def employee_stats() -> list:
    """(співробітник, посада, приготував, розніс, скасовано, виручка за свою роль)"""
    def count_where(*cond):
        return (select(func.count(Order.id)).where(*cond).correlate(Employee).scalar_subquery())

    def revenue_where(*cond):
        return (select(func.coalesce(func.sum(LINE_SUM), 0))
                .select_from(OrderItem).join(Order, Order.id == OrderItem.orderid)
                .where(*cond).correlate(Employee).scalar_subquery())

    prepared = count_where(Order.employeeid == Employee.id, PAID)
    served = count_where(Order.waiterid == Employee.id, PAID)
    cancelled = count_where(Order.employeeid == Employee.id, CANCELLED)
    revenue = case((Employee.position == "офіціант", revenue_where(Order.waiterid == Employee.id, PAID)),
                   else_=revenue_where(Order.employeeid == Employee.id, PAID))
    stmt = (select(Employee.fullname, Employee.position, prepared, served, cancelled, revenue)
            .order_by(revenue.desc(), Employee.id))
    return _run(stmt)


# ----------------------------------------------------------------
# 3.1. Гості-котики: GROUP BY окрас + HAVING + RANK() OVER (ORDER BY виручка)
# ----------------------------------------------------------------
def guest_stats() -> list:
    """(окрас, оплачено, пішли без замовлення, виручка, середній чек, % невдоволених, місце)"""
    paid_orders = func.count(func.distinct(case((PAID, Order.id))))
    cancelled = func.count(func.distinct(case((CANCELLED, Order.id))))
    revenue = func.coalesce(func.sum(case((PAID, LINE_SUM), else_=0)), 0)
    stmt = (select(Order.guestbreed, paid_orders, cancelled, revenue,
                   revenue / func.nullif(paid_orders, 0),
                   100.0 * cancelled / func.nullif(paid_orders + cancelled, 0),
                   func.rank().over(order_by=revenue.desc()))
            .select_from(Order)
            .outerjoin(OrderItem, OrderItem.orderid == Order.id)
            .where(Order.guestbreed.is_not(None))
            .group_by(Order.guestbreed)
            .having(func.count(func.distinct(Order.id)) > 0)
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


# ----------------------------------------------------------------
# 8. Найкращі гравці: RANK() OVER (ORDER BY total_money DESC)
# ----------------------------------------------------------------
def top_players(limit: int = 10) -> list:
    """(місце, гравець, днів зіграно, виконано замовлень, зароблено монет, рейтинг)"""
    stmt = (select(func.rank().over(order_by=Player.total_money.desc()),
                   Player.name, Player.days_played, Player.orders_done,
                   Player.total_money, Player.rating)
            .select_from(Player)
            .order_by(Player.total_money.desc(), Player.orders_done.desc())
            .limit(limit))
    return _run(stmt)


# ----------------------------------------------------------------
# 9. Витрати кафе на закупівлю продуктів (поставки машинки): JOIN + GROUP BY
# ----------------------------------------------------------------
def supply_expenses(limit: int = 15) -> list:
    """(день, страва, замовлено одиниць, витрачено монет)"""
    stmt = (select(CafeExpense.gameday, MenuItem.name,
                   func.sum(CafeExpense.quantity),
                   func.sum(CafeExpense.cost))
            .select_from(CafeExpense)
            .join(MenuItem, MenuItem.id == CafeExpense.menuitemid)
            .group_by(CafeExpense.gameday, MenuItem.id, MenuItem.name)
            .order_by(CafeExpense.gameday.desc(), func.sum(CafeExpense.cost).desc())
            .limit(limit))
    return _run(stmt)

