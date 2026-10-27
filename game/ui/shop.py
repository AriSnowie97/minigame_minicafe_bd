"""
Модальне вікно магазину покращень та меблів (Shop Modal).
Дозволяє купувати за зароблені монети розширення кафе (Тераса),
котика-офіціанта, помічника шеф-кухаря, розширення меню (печиво, айс лате, тортик)
та затишний декор.
"""
import pygame
from typing import Dict, Any, Optional, Tuple
from game.core.settings import C, WIDTH, HEIGHT
from game.core.assets   import assets
from game.core.audio    import audio


SHOP_CATEGORIES = [
    {
        "id": "cafe",
        "title": "Кафе та персонал",
        "items": [
            {
                "id": "waiter",
                "name": "Котик-офіціант",
                "desc": "Приймає замовлення та розносить страви гостям!",
                "price": 120,
                "icon": "cat_waiter_happy",
            },
            {
                "id": "waiter2",
                "name": "Другий офіціант",
                "desc": "Працює лише на терасі: приймає замовлення й носить їх до баристи та шеф-кухаря.",
                "price": 130,
                "icon": "cat_waiter2_happy",
                "requires": "terrace",
                "requires_text": "Потрібна тераса",
            },
            {
                "id": "terrace",
                "name": "Літня Тераса",
                "desc": "Відкриває столики тераси, настил та ліхтарики!",
                "price": 150,
                "icon": "furniture_table",
            },
            {
                "id": "chef",
                "name": "Шеф-кухар Мурчик",
                "desc": "Відкриває кухню з новими стравами та прискорює готування на 45%!",
                "price": 160,
                "icon": "cat_cook_happy",
            },
            {
                "id": "doormat",
                "name": "М'який килимок",
                "desc": "+8 сек до терпіння гостей при вході.",
                "price": 60,
                "icon": "decor_doormat",
            },
            {
                "id": "vip_armchair",
                "name": "VIP-крісло",
                "desc": "Королівське крісло: +30% до чайових.",
                "price": 90,
                "icon": "furniture_armchair",
            },
            {
                "id": "monstera",
                "name": "Велика Монстера",
                "desc": "Тропічна рослина: +0.5 до рейтингу кафе.",
                "price": 70,
                "icon": "decor_plant_big",
            },
        ],
    },
    {
        "id": "menu",
        "title": "Меню та продукти",
        "items": [
            # Базові напої (бариста)
            {
                "id": "menu_coffee",
                "menu_item_id": 1,
                "name": "Кава (Еспресо)",
                "desc": "Базовий напій: ароматний еспресо у чашці (+50 монет).",
                "price": 0,
                "is_base": True,
                "restock_price": 25,
                "icon": "item_coffee_cup",
            },
            {
                "id": "menu_tea",
                "menu_item_id": 2,
                "name": "Чай чорний",
                "desc": "Базовий напій: гарячий заварений чай (+40 монет).",
                "price": 0,
                "is_base": True,
                "restock_price": 20,
                "icon": "item_black_tea",
            },
            {
                "id": "menu_cappuccino",
                "menu_item_id": 15,
                "name": "Капучино",
                "desc": "Базовий напій: еспресо з ніжною пінкою (+65 монет).",
                "price": 0,
                "is_base": True,
                "restock_price": 30,
                "icon": "item_cappuccino",
            },
            {
                "id": "menu_latte",
                "menu_item_id": 12,
                "name": "Лате",
                "desc": "Базовий напій: еспресо та збите молоко (+60 монет).",
                "price": 0,
                "is_base": True,
                "restock_price": 30,
                "icon": "item_latte",
            },
            {
                "id": "menu_iced_latte",
                "menu_item_id": 4,
                "name": "Айс лате",
                "desc": "Базовий напій: охолоджений лате з льодом (+85 монет).",
                "price": 0,
                "is_base": True,
                "restock_price": 35,
                "icon": "item_iced_coffee",
            },
            {
                "id": "menu_takeaway",
                "menu_item_id": 13,
                "name": "Кава з собою",
                "desc": "Базовий напій: кава у зручному стаканчику (+45 монет).",
                "price": 0,
                "is_base": True,
                "restock_price": 20,
                "icon": "item_takeaway_cup",
            },
            # Розширення меню (випічка та десерти)
            {
                "id": "menu_cookies",
                "menu_item_id": 3,
                "name": "Домашнє печиво",
                "desc": "Бариста додає до меню шоколадне печиво (+65 монет).",
                "price": 50,
                "restock_price": 30,
                "icon": "item_cookies",
            },
            {
                "id": "menu_croissant",
                "menu_item_id": 14,
                "name": "Круасани",
                "desc": "Бариста додає до меню хрусткі круасани (+55 монет).",
                "price": 60,
                "restock_price": 28,
                "icon": "item_croissant",
            },
            {
                "id": "menu_cake",
                "menu_item_id": 5,
                "name": "Святковий Тортик",
                "desc": "Преміум десерт (+110 монет): готує кухар.",
                "price": 100,
                "restock_price": 45,
                "icon": "item_cake",
                "is_chef": True,
            },
            # Страви шеф-кухаря (кухня)
            {
                "id": "menu_bruschetta",
                "menu_item_id": 6,
                "name": "Брускета",
                "desc": "Страва кухні (потрібен кухар): +70 монет.",
                "price": 90,
                "restock_price": 35,
                "icon": "item_bruschetta",
                "requires": "chef",
                "requires_text": "Потрібен кухар",
                "is_chef": True,
            },
            {
                "id": "menu_syrniki",
                "menu_item_id": 7,
                "name": "Сирники",
                "desc": "Страва кухні (потрібен кухар): +90 монет.",
                "price": 100,
                "restock_price": 40,
                "icon": "item_syrniki",
                "requires": "chef",
                "requires_text": "Потрібен кухар",
                "is_chef": True,
            },
            {
                "id": "menu_omelette",
                "menu_item_id": 8,
                "name": "Омлет з беконом",
                "desc": "Страва кухні (потрібен кухар): +100 монет.",
                "price": 110,
                "restock_price": 45,
                "icon": "item_omelette_bacon",
                "requires": "chef",
                "requires_text": "Потрібен кухар",
                "is_chef": True,
            },
            {
                "id": "menu_caesar",
                "menu_item_id": 9,
                "name": "Салат Цезар",
                "desc": "Страва кухні (потрібен кухар): +105 монет.",
                "price": 120,
                "restock_price": 50,
                "icon": "item_caesar_salad",
                "requires": "chef",
                "requires_text": "Потрібен кухар",
                "is_chef": True,
            },
            {
                "id": "menu_tiramisu",
                "menu_item_id": 10,
                "name": "Тірамісу",
                "desc": "Страва кухні (потрібен кухар): +120 монет.",
                "price": 130,
                "restock_price": 55,
                "icon": "item_tiramisu",
                "requires": "chef",
                "requires_text": "Потрібен кухар",
                "is_chef": True,
            },
            {
                "id": "menu_borscht",
                "menu_item_id": 11,
                "name": "Борщ",
                "desc": "Страва кухні (потрібен кухар): +130 монет.",
                "price": 140,
                "restock_price": 55,
                "icon": "item_borscht",
                "requires": "chef",
                "requires_text": "Потрібен кухар",
                "is_chef": True,
            },
        ],
    },
]


class ShopModal:
    """Модальне вікно магазину оновлень кафе з вкладками"""

    def __init__(self):
        self.is_open = False
        self.width = 680
        self.height = 580
        self.x = (WIDTH - self.width) // 2
        self.y = (HEIGHT - self.height) // 2
        self.close_rect = pygame.Rect(self.x + self.width - 44, self.y + 14, 30, 30)

        self.current_tab = 0  # 0: Кафе/Персонал, 1: Меню та продукти
        self.tab_rects = [
            pygame.Rect(self.x + 24, self.y + 70, 200, 36),
            pygame.Rect(self.x + 234, self.y + 70, 200, 36),
        ]

        # Скролл / офсет для довгого списку
        self.scroll_y = 0
        self._btn_rects: Dict[str, pygame.Rect] = {}

    def open(self):
        if not self.is_open:
            audio.play("ui_open")
        self.is_open = True
        self.scroll_y = 0

    def close(self):
        self.is_open = False

    def handle_event(self, event: pygame.event.Event, money: int, upgrades: Dict[str, Any], stock: Optional[Dict[int, int]] = None) -> Tuple[bool, int, Optional[Any]]:
        if not self.is_open:
            return False, money, None

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
            audio.play("ui_click")
            self.close()
            return True, money, None

        if event.type == pygame.MOUSEWHEEL:
            n_items = len(SHOP_CATEGORIES[self.current_tab]["items"])
            max_scroll = max(0, n_items * 74 - (self.height - 130) + 10)
            self.scroll_y = max(0, min(self.scroll_y - event.y * 30, max_scroll))
            return True, money, None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mx, my = event.pos

            # Клік по кнопці закриття [X]
            if self.close_rect.collidepoint(mx, my):
                audio.play("ui_click")
                self.close()
                return True, money, None

            # Клік за межами модального вікна закриває його
            modal_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if not modal_rect.collidepoint(mx, my):
                audio.play("ui_click")
                self.close()
                return True, money, None

            # Клік по вкладках
            for tab_idx, tr in enumerate(self.tab_rects):
                if tr.collidepoint(mx, my):
                    if tab_idx != self.current_tab:
                        audio.play("ui_click")
                    self.current_tab = tab_idx
                    self.scroll_y = 0
                    return True, money, None

            # Клік по кнопках покупок поточного списку
            cat_items = SHOP_CATEGORIES[self.current_tab]["items"]
            for item in cat_items:
                item_id = item["id"]
                btn_r = self._btn_rects.get(item_id)
                if btn_r and btn_r.collidepoint(mx, my):
                    is_menu_tab = (self.current_tab == 1)
                    is_unlocked = item.get("is_base", False) or upgrades.get(item_id, False)

                    # 1. Повторна покупка позиції в меню (замовлення поставки +10 шт машинки)
                    if is_menu_tab and is_unlocked:
                        restock_cost = item.get("restock_price", 30)
                        if money >= restock_cost:
                            new_money = money - restock_cost
                            audio.play("cash_register")
                            audio.play("star", mult=0.8, delay=0.25)
                            return True, new_money, {"type": "restock", "item": item}
                        else:
                            audio.play("ui_disabled")
                            return True, money, None

                    # 2. Перша покупка / розблокування
                    req = item.get("requires")
                    if req and not upgrades.get(req, False):
                        audio.play("ui_disabled")
                        return True, money, None

                    if not is_unlocked and money >= item["price"]:
                        new_money = money - item["price"]
                        upgrades[item_id] = True
                        audio.play("cash_register")
                        audio.play("star", mult=0.8, delay=0.25)
                        return True, new_money, item_id

                    if not is_unlocked:
                        audio.play("ui_disabled")   # не вистачає монет
            return True, money, None

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return True, money, None

        return False, money, None

    def draw(self, surface: pygame.Surface, money: int, upgrades: Dict[str, Any], stock: Optional[Dict[int, int]] = None):
        if not self.is_open:
            return

        # 1. Затемнення фону
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 20, 20, 140))
        surface.blit(dim, (0, 0))

        # 2. Карточка магазину
        card = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(card, (255, 252, 246), (0, 0, self.width, self.height), border_radius=16)
        pygame.draw.rect(card, C.TERRACOTTA, (0, 0, self.width, self.height), 3, border_radius=16)
        surface.blit(card, (self.x, self.y))

        # 3. Шапка магазину
        header_h = 60
        h_surf = pygame.Surface((self.width, header_h), pygame.SRCALPHA)
        pygame.draw.rect(h_surf, (*C.DARK_SAGE, 245), (0, 0, self.width, header_h),
                         border_top_left_radius=14, border_top_right_radius=14)
        pygame.draw.line(h_surf, C.TERRACOTTA, (0, header_h - 2), (self.width, header_h - 2), 2)
        surface.blit(h_surf, (self.x, self.y))

        # Заголовок
        f_title = assets.font_title(22, bold=True)
        title_t = assets.render_outlined(f_title, "Котяча Крамниця Оновлень", C.WHITE, (45, 40, 35), 1)
        surface.blit(title_t, (self.x + 20, self.y + 16))

        # Баланс монет гравця
        f_ui = assets.font_ui(18, bold=True)
        coin_icon = assets.image_by_height("ui_icon_coin", 24)
        surface.blit(coin_icon, (self.x + self.width - 200, self.y + 18))
        coin_t = assets.render_outlined(f_ui, f"{money}", (255, 225, 120), (45, 40, 35), 1)
        surface.blit(coin_t, (self.x + self.width - 170, self.y + 17))

        # Кнопка [X]
        pygame.draw.rect(surface, C.TERRACOTTA, self.close_rect, border_radius=8)
        f_x = assets.font_ui(16, bold=True)
        x_t = f_x.render("X", True, C.WHITE)
        surface.blit(x_t, x_t.get_rect(center=self.close_rect.center))

        # 4. Вкладки (Tabs)
        f_tab = assets.font_ui(14, bold=True)
        for idx, (cat, tr) in enumerate(zip(SHOP_CATEGORIES, self.tab_rects)):
            active = (self.current_tab == idx)
            tab_bg = (255, 252, 246) if active else (235, 228, 218)
            tab_border = C.TERRACOTTA if active else C.SAGE_GRAY
            pygame.draw.rect(surface, tab_bg, tr, border_top_left_radius=8, border_top_right_radius=8)
            pygame.draw.rect(surface, tab_border, tr, 2 if active else 1, border_top_left_radius=8, border_top_right_radius=8)
            txt_col = C.TERRACOTTA if active else C.DARK_SAGE
            tab_lbl = f_tab.render(cat["title"], True, txt_col)
            surface.blit(tab_lbl, tab_lbl.get_rect(center=tr.center))

        # Лінія під вкладками
        pygame.draw.line(surface, C.TERRACOTTA, (self.x + 18, self.y + 106), (self.x + self.width - 18, self.y + 106), 2)

        # 5. Список товарів активної вкладки
        cat_items = SHOP_CATEGORIES[self.current_tab]["items"]
        mouse_pos = pygame.mouse.get_pos()
        f_name = assets.font_ui(15, bold=True)
        f_desc = assets.font_ui(12)
        f_btn  = assets.font_ui(12, bold=True)
        f_stock = assets.font_ui(11, bold=True)

        start_y = self.y + 116
        row_h = 74

        self._btn_rects.clear()

        # Область списку
        list_clip = pygame.Rect(self.x + 10, start_y, self.width - 20, self.height - 130)
        orig_clip = surface.get_clip()
        surface.set_clip(list_clip)

        is_menu_tab = (self.current_tab == 1)

        for i, item in enumerate(cat_items):
            item_id = item["id"]
            iy = start_y + i * row_h - self.scroll_y
            is_unlocked = item.get("is_base", False) or upgrades.get(item_id, False)

            # Розділювач рядків
            if i > 0:
                pygame.draw.line(surface, (230, 224, 216), (self.x + 20, iy - 2), (self.x + self.width - 20, iy - 2), 1)

            # Іконка товару в рамці
            icon_box = pygame.Rect(self.x + 22, iy + 4, 56, 56)
            pygame.draw.rect(surface, (245, 240, 230), icon_box, border_radius=10)
            pygame.draw.rect(surface, C.SAGE_GRAY, icon_box, 1, border_radius=10)

            item_img = assets.image_by_height(item["icon"], 40)
            surface.blit(item_img, item_img.get_rect(center=icon_box.center))

            # Назва та бейдж запасу
            name_col = C.TEXT_DARK if not is_unlocked else C.DARK_SAGE
            name_t = assets.render_outlined(f_name, item["name"], name_col, (255, 255, 255), 1)
            surface.blit(name_t, (self.x + 90, iy + 6))

            # Якщо це страва/напій — показуємо поточний залишок
            if is_menu_tab:
                mid = item.get("menu_item_id", 1)
                cur_cnt = stock.get(mid, 20) if stock is not None else 20
                if cur_cnt == 0:
                    badge_bg = (255, 225, 225)
                    badge_border = (220, 80, 80)
                    badge_txt_col = (180, 30, 30)
                    badge_str = "0 шт (Немає!)"
                elif cur_cnt <= 5:
                    badge_bg = (255, 245, 215)
                    badge_border = (235, 150, 40)
                    badge_txt_col = (180, 100, 10)
                    badge_str = f"{cur_cnt} шт (Мало)"
                else:
                    badge_bg = (230, 245, 230)
                    badge_border = (110, 185, 110)
                    badge_txt_col = (45, 130, 45)
                    badge_str = f"{cur_cnt} шт"

                st_t = f_stock.render(badge_str, True, badge_txt_col)
                sw, sh = st_t.get_width() + 10, 18
                sx = self.x + 90 + name_t.get_width() + 10
                sy = iy + 6
                pygame.draw.rect(surface, badge_bg, (sx, sy, sw, sh), border_radius=6)
                pygame.draw.rect(surface, badge_border, (sx, sy, sw, sh), 1, border_radius=6)
                surface.blit(st_t, (sx + 5, sy + 2))

            desc_t = f_desc.render(item["desc"], True, C.DARK_SAGE)
            surface.blit(desc_t, (self.x + 90, iy + 34))

            # Кнопка дії
            btn_r = pygame.Rect(self.x + self.width - 155, iy + 14, 135, 36)
            self._btn_rects[item_id] = btn_r

            hover = btn_r.collidepoint(mouse_pos)

            # 1. Позиція меню, яка вже доступна -> кнопка замовлення поставки машинки (+10 шт)
            if is_menu_tab and is_unlocked:
                restock_cost = item.get("restock_price", 30)
                can_afford = (money >= restock_cost)
                if can_afford:
                    bg_col = (90, 175, 110) if hover else (70, 150, 90)
                    border_col = (50, 120, 70)
                    txt_col = C.WHITE
                else:
                    bg_col = (220, 220, 220)
                    border_col = (180, 180, 180)
                    txt_col = (130, 130, 130)

                pygame.draw.rect(surface, bg_col, btn_r, border_radius=8)
                pygame.draw.rect(surface, border_col, btn_r, 1, border_radius=8)
                txt_str = f"+10 шт ({restock_cost} м)"
                txt = assets.render_outlined(f_btn, txt_str, txt_col, (35, 75, 45) if can_afford else (170, 170, 170), 1)
                surface.blit(txt, txt.get_rect(center=btn_r.center))

            # 2. Не меню, а покращення кафе/персонал, яке вже куплено
            elif not is_menu_tab and is_unlocked:
                pygame.draw.rect(surface, (225, 245, 225), btn_r, border_radius=8)
                pygame.draw.rect(surface, C.PATIENCE_GOOD, btn_r, 1, border_radius=8)
                txt = assets.render_outlined(f_btn, "Куплено ✓", C.PATIENCE_GOOD, (240, 255, 240), 1)
                surface.blit(txt, txt.get_rect(center=btn_r.center))

            # 3. Вимагає іншого покращення
            elif item.get("requires") and not upgrades.get(item["requires"], False):
                pygame.draw.rect(surface, (225, 222, 215), btn_r, border_radius=8)
                pygame.draw.rect(surface, (180, 178, 170), btn_r, 1, border_radius=8)
                txt = assets.render_outlined(f_btn, item.get("requires_text", "Недоступно"), (125, 120, 112), (240, 236, 230), 1)
                surface.blit(txt, txt.get_rect(center=btn_r.center))

            # 4. Позиція ще не куплена -> кнопка розблокування
            else:
                can_afford = (money >= item["price"])
                if can_afford:
                    bg_col = C.BTN_HOVER if hover else C.BTN_BG
                    border_col = C.TERRACOTTA
                    txt_col = C.WHITE
                else:
                    bg_col = (220, 220, 220)
                    border_col = (180, 180, 180)
                    txt_col = (130, 130, 130)

                pygame.draw.rect(surface, bg_col, btn_r, border_radius=8)
                pygame.draw.rect(surface, border_col, btn_r, 1, border_radius=8)
                txt_str = f"{item['price']} монет"
                txt = assets.render_outlined(f_btn, txt_str, txt_col, (60, 45, 40) if can_afford else (170, 170, 170), 1)
                surface.blit(txt, txt.get_rect(center=btn_r.center))

        surface.set_clip(orig_clip)

