"""
Система прогресії складності по днях та конфігурація покращень кафе.
"""
from typing import Dict, Any


def get_day_config(day: int, upgrades: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Повертає параметри складності для поточного дня з урахуванням куплених оновлень.
    """
    upgrades = upgrades or {}
    has_terrace = upgrades.get("terrace", False)
    has_doormat = upgrades.get("doormat", False)

    # 1. Максимальна кількість гостей одночасно
    if day == 1:
        base_max_cust = 2
    elif day == 2:
        base_max_cust = 3
    elif day == 3:
        base_max_cust = 4
    else:
        base_max_cust = 5

    # Тераса дозволяє приймати більше гостей одночасно (4 столики в залі + 4 на терасі)
    if has_terrace:
        base_max_cust = min(7, base_max_cust + 2)
    max_customers = base_max_cust

    # 2. Інтервал появи нових клієнтів (секунд)
    if day == 1:
        spawn_interval = 12.0
        day_title = "День 1: Затишний старт"
    elif day == 2:
        spawn_interval = 9.5
        day_title = "День 2: Солодкі замовлення"
    elif day == 3:
        spawn_interval = 7.5
        day_title = "День 3: Популярне кафе"
    elif day == 7:
        spawn_interval = 6.0
        day_title = "День 7: Фінал 1-го тижня кафе"
    elif day == 8:
        spawn_interval = 5.5
        day_title = "День 8: Подвійні замовлення!"
    else:
        spawn_interval = max(4.5, 7.0 - (day - 3) * 0.4)
        week_num = 1 + (day - 1) // 7
        day_title = f"День {day} (Тиждень {week_num}): Ресторанний ажіотаж"

    # Дозволені страви в меню:
    # Базово: 1 (Капучино) та 2 (Чай).
    # Додаткові страви розблоковуються покупкою в Магазині (Розширення меню)
    # Меню баристи. Базове: кава, кава з собою, чай, капучино, лате, айс лате.
    # Розширене (купується в Магазині): печиво, круасани, тортик.
    allowed_items = [1, 13, 2, 15, 12, 4]
    for upgrade_id, item_id in (("menu_cookies", 3), ("menu_croissant", 14), ("menu_cake", 5)):
        if upgrades.get(upgrade_id, False):
            allowed_items.append(item_id)
    # Страви кухаря: салат, брускета, тірамісу, борщ, сирники, омлет — потребують
    # і покупки в Магазині, і найнятого шеф-кухаря Мурчика
    if upgrades.get("chef", False):
        for upgrade_id, item_id in (("menu_caesar", 9), ("menu_bruschetta", 6),
                                    ("menu_tiramisu", 10), ("menu_borscht", 11),
                                    ("menu_syrniki", 7), ("menu_omelette", 8)):
            if upgrades.get(upgrade_id, False):
                allowed_items.append(item_id)

    # 3. Базовий час терпіння клієнтів (секунд)
    if day == 1:
        patience = 44.0
    elif day == 2:
        patience = 37.0
    elif day == 3:
        patience = 31.0
    else:
        patience = max(24.0, 30.0 - (day - 3) * 1.5)

    # Бонус від м'якого килимка
    if has_doormat:
        patience += 8.0

    # 4. Множник швидкості готування (Шеф-повар)
    cook_speed_mult = 0.55 if upgrades.get("chef", False) else 1.0

    # 5. Бонус до чайових (VIP-крісло)
    tip_mult = 1.30 if upgrades.get("vip_armchair", False) else 1.0

    # 6. Офіціант (купується окремо в магазині)
    has_waiter = upgrades.get("waiter", False)
    has_waiter2 = upgrades.get("waiter2", False)   # второй официант — работает только на террасе

    # 7. Дозволені столики (столики 1..4 — зал, 5..8 — літня тераса)
    if has_terrace:
        allowed_tables = [1, 2, 3, 4, 9, 10, 5, 6, 7, 8]
    else:
        allowed_tables = [1, 2, 3, 4, 9, 10]

    # 8. Складність після 1 тижня: котики замовляють по 2 предмети (напій + десерт)
    can_order_two = (day >= 8)
    two_items_chance = min(0.85, 0.60 + (day - 8) * 0.05) if can_order_two else 0.0

    return {
        "day": day,
        "day_title": day_title,
        "max_customers": max_customers,
        "spawn_interval": spawn_interval,
        "patience": patience,
        "allowed_items": allowed_items,
        "allowed_tables": allowed_tables,
        "cook_speed_mult": cook_speed_mult,
        "tip_mult": tip_mult,
        "has_terrace": has_terrace,
        "has_waiter": has_waiter,
        "has_waiter2": has_waiter2,
        "can_order_two": can_order_two,
        "two_items_chance": two_items_chance,
    }
