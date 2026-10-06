"""
Початкові дані MiniCafe для ORM. Це ті самі дані, що й у database/schema_postgres.sql;
їх використовує локальна SQLite-база, якщо PostgreSQL (Railway) недоступний.
"""
from datetime import date
import random
from datetime import datetime, timedelta

from database.models import (CafeTable, Employee, MenuCategory, MenuItem, MenuItemIngredient,
                             Order, OrderItem, Product)

CATEGORIES = [(1, "Напої"), (2, "Випічка"), (3, "Основні страви"), (4, "Десерти"), (5, "Закуски"), (6, "Сніданки")]

PRODUCTS = [
    (1, "Кава в зернах", "кг", 450.00, 365), (2, "Молоко", "л", 35.00, 7), (3, "Чайне листя", "кг", 300.00, 540),
    (4, "Яйця", "шт", 4.50, 21), (5, "Бекон", "кг", 220.00, 30), (6, "Творог", "кг", 110.00, 10),
    (7, "Куряче філе", "кг", 160.00, 5), (8, "Салатний мікс", "кг", 90.00, 5), (9, "Помідори чері", "кг", 80.00, 7),
    (10, "Хліб", "шт", 25.00, 3), (11, "Маскарпоне", "кг", 280.00, 14), (12, "Печиво Савоярді", "кг", 200.00, 180),
    (13, "Борошно", "кг", 30.00, 365), (14, "Буряк", "кг", 25.00, 30),
]

# (id, назва, категорія, ціна, хв. приготування, рецепт) — id збігаються з ID страв у грі
MENU_ITEMS = [
    (1, "Кава", 1, 50.00, 4, "Еспресо у чашці."),
    (2, "Чай чорний", 1, 40.00, 3, "Заварити чайне листя окропом."),
    (3, "Печиво", 2, 65.00, 5, "Домашнє шоколадне печиво."),
    (4, "Айс лате", 1, 85.00, 6, "Еспресо, холодне молоко, лід."),
    (5, "Тортик", 4, 110.00, 8, "Святковий тортик з кремом."),
    (6, "Брускета", 5, 70.00, 5, "Підсмажений хліб, помідори чері, спеції."),
    (7, "Сирники", 6, 90.00, 6, "Обсмажити сирники з творогу."),
    (8, "Омлет з беконом", 6, 100.00, 7, "Збити яйця, обсмажити з беконом."),
    (9, "Салат Цезар", 3, 105.00, 6, "Куряче філе, салатний мікс, соус, сухарики."),
    (10, "Тірамісу", 4, 120.00, 7, "Маскарпоне, печиво Савоярді, кава."),
    (11, "Борщ", 3, 130.00, 8, "Традиційний борщ з буряком."),
    (12, "Лате", 1, 60.00, 4, "Еспресо, велика частка молока."),
    (13, "Кава з собою", 1, 45.00, 3, "Кава в паперовому стаканчику."),
    (14, "Круасан", 2, 55.00, 4, "Свіжий хрусткий круасан."),
    (15, "Капучино", 1, 65.00, 4, "Еспресо та збите молоко."),
]

# (id, страва, продукт, кількість)
INGREDIENTS = [
    (1, 1, 1, 0.018), (2, 2, 3, 0.005), (3, 3, 13, 0.050), (4, 4, 1, 0.018), (5, 4, 2, 0.150),
    (6, 5, 13, 0.100), (7, 5, 4, 2.000), (8, 6, 10, 1.000), (9, 6, 9, 0.080), (10, 7, 6, 0.200),
    (11, 8, 4, 3.000), (12, 8, 5, 0.080), (13, 9, 7, 0.150), (14, 9, 8, 0.100), (15, 10, 11, 0.120),
    (16, 10, 12, 0.060), (17, 11, 14, 0.150), (18, 12, 1, 0.018), (19, 12, 2, 0.180), (20, 13, 1, 0.018),
    (21, 14, 13, 0.080), (22, 15, 1, 0.018), (23, 15, 2, 0.100),
]

# (id, номер, місць, розташування)
TABLES = [
    (1, 1, 2, "зал"), (2, 2, 2, "зал"), (3, 3, 4, "зал"), (4, 4, 4, "зал"), (5, 5, 2, "тераса"),
    (6, 6, 4, "тераса"), (7, 7, 2, "тераса"), (8, 8, 4, "тераса"), (9, 9, 2, "зал"), (10, 10, 2, "зал"),
]

EMPLOYEES = [
    (1, "Коваленко Ірина", "бариста", "+380671000001", date(2024, 3, 1)),
    (2, "Петренко Олег", "офіціант", "+380671000002", date(2024, 5, 15)),
    (3, "Сидоренко Марія", "кухар", "+380671000003", date(2023, 11, 20)),
    (4, "Бондаренко Андрій", "адміністратор", "+380671000004", date(2022, 9, 10)),
]

CHEF_ITEM_IDS = (5, 6, 7, 8, 9, 10, 11)


def seed_reference_data(session):
    """Довідкові дані: категорії, продукти, меню, склад, столики, співробітники"""
    session.add_all([MenuCategory(id=i, name=n) for i, n in CATEGORIES])
    session.add_all([Product(id=i, name=n, unit=u, unitprice=p, shelflifedays=s) for i, n, u, p, s in PRODUCTS])
    session.add_all([MenuItem(id=i, name=n, categoryid=c, price=p, cookingtimemin=t, recipe=r)
                     for i, n, c, p, t, r in MENU_ITEMS])
    session.flush()
    session.add_all([MenuItemIngredient(id=i, menuitemid=m, productid=p, quantity=q) for i, m, p, q in INGREDIENTS])
    session.add_all([CafeTable(id=i, tablenumber=n, capacity=c, location=l) for i, n, c, l in TABLES])
    session.add_all([Employee(id=i, fullname=f, position=p, phone=ph, hiredate=h) for i, f, p, ph, h in EMPLOYEES])
    session.flush()


def add_demo_orders(session, count: int = 60, days: int = 6, seed: int = 7) -> int:
    """
    Демонстраційна історія замовлень (для показу статистики): випадкові столики, страви та дні.
    Страви кухаря готує кухар (id 3), решту — бариста (id 1).
    """
    rng = random.Random(seed)
    items = session.query(MenuItem).all()
    base = datetime.now() - timedelta(days=days)
    created = 0
    for _ in range(count):
        day = rng.randint(1, days)
        table_id = rng.choice([t[0] for t in TABLES])
        dishes = rng.sample(items, 2 if rng.random() < 0.3 else 1)
        chef = any(d.id in CHEF_ITEM_IDS for d in dishes)
        status = rng.choices(["оплачено", "скасовано"], weights=[85, 15])[0]
        order = Order(tableid=table_id, employeeid=3 if chef else 1, status=status, gameday=day,
                      orderdatetime=base + timedelta(days=day - 1, hours=rng.randint(9, 20),
                                                     minutes=rng.randint(0, 59)))
        session.add(order)
        session.flush()
        for d in dishes:
            session.add(OrderItem(orderid=order.id, menuitemid=d.id, quantity=1, priceatorder=d.price))
        created += 1
    session.flush()
    return created
