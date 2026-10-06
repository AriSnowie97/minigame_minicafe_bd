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
        "title": "Розширення меню",
        "items": [
            {
                "id": "menu_cookies",
                "name": "Домашнє печиво",
                "desc": "Бариста додає до меню шоколадне печиво (+65 монет).",
                "price": 50,
                "icon": "item_cookies",
            },
            {
                "id": "menu_croissant",
                "name": "Круасани",
                "desc": "Бариста додає до меню хрусткі круасани (+55 монет).",
                "price": 60,
                "icon": "item_croissant",
            },
            {
                "id": "menu_cake",
                "name": "Святковий Тортик",
                "desc": "Преміум десерт (+110 монет): готує кухар, якщо він найнятий.",
                "price": 100,
                "icon": "item_cake",
            },
            {
                "id": "menu_bruschetta",
                "name": "Брускета",
                "desc": "Страва кухні (потрібен кухар): +70 монет.",
                "price": 90,
                "icon": "item_bruschetta",
            },
            {
                "id": "menu_syrniki",
                "name": "Сирники",
                "desc": "Страва кухні (потрібен кухар): +90 монет.",
                "price": 100,
                "icon": "item_syrniki",
            },
            {
                "id": "menu_omelette",
                "name": "Омлет з беконом",
                "desc": "Страва кухні (потрібен кухар): +100 монет.",
                "price": 110,
                "icon": "item_omelette_bacon",
            },
            {
                "id": "menu_caesar",
                "name": "Салат Цезар",
                "desc": "Страва кухні (потрібен кухар): +105 монет.",
                "price": 120,
                "icon": "item_caesar_salad",
            },
            {
                "id": "menu_tiramisu",
                "name": "Тірамісу",
                "desc": "Страва кухні (потрібен кухар): +120 монет.",
                "price": 130,
                "icon": "item_tiramisu",
            },
            {
                "id": "menu_borscht",
                "name": "Борщ",
                "desc": "Страва кухні (потрібен кухар): +130 монет.",
                "price": 140,
                "icon": "item_borscht",
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

        self.current_tab = 0  # 0: Кафе/Персонал, 1: Меню
        self.tab_rects = [
            pygame.Rect(self.x + 24, self.y + 70, 200, 36),
            pygame.Rect(self.x + 234, self.y + 70, 200, 36),
        ]

        # Скролл / офсет для довгого списку
        self.scroll_y = 0
        self._btn_rects: Dict[str, pygame.Rect] = {}

    def open(self):
        self.is_open = True
        self.scroll_y = 0

    def close(self):
        self.is_open = False

    def handle_event(self, event: pygame.event.Event, money: int, upgrades: Dict[str, Any]) -> Tuple[bool, int, Optional[str]]:
        if not self.is_open:
            return False, money, None

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
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
                self.close()
                return True, money, None

            # Клік за межами модального вікна закриває його
            modal_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if not modal_rect.collidepoint(mx, my):
                self.close()
                return True, money, None

            # Клік по вкладках
            for tab_idx, tr in enumerate(self.tab_rects):
                if tr.collidepoint(mx, my):
                    self.current_tab = tab_idx
                    self.scroll_y = 0
                    return True, money, None

            # Клік по кнопках покупок поточного списку
            cat_items = SHOP_CATEGORIES[self.current_tab]["items"]
            for item in cat_items:
                item_id = item["id"]
                btn_r = self._btn_rects.get(item_id)
                if btn_r and btn_r.collidepoint(mx, my):
                    if not upgrades.get(item_id, False) and money >= item["price"]:
                        new_money = money - item["price"]
                        upgrades[item_id] = True
                        return True, new_money, item_id
            return True, money, None

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return True, money, None

        return False, money, None

    def draw(self, surface: pygame.Surface, money: int, upgrades: Dict[str, Any]):
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
        f_name = assets.font_ui(16, bold=True)
        f_desc = assets.font_ui(12)
        f_btn  = assets.font_ui(13, bold=True)

        start_y = self.y + 116
        row_h = 74

        self._btn_rects.clear()

        # Область списку
        list_clip = pygame.Rect(self.x + 10, start_y, self.width - 20, self.height - 130)
        orig_clip = surface.get_clip()
        surface.set_clip(list_clip)

        for i, item in enumerate(cat_items):
            item_id = item["id"]
            iy = start_y + i * row_h - self.scroll_y
            owned = upgrades.get(item_id, False)

            # Розділювач рядків
            if i > 0:
                pygame.draw.line(surface, (230, 224, 216), (self.x + 20, iy - 2), (self.x + self.width - 20, iy - 2), 1)

            # Іконка товару в рамці
            icon_box = pygame.Rect(self.x + 22, iy + 4, 56, 56)
            pygame.draw.rect(surface, (245, 240, 230), icon_box, border_radius=10)
            pygame.draw.rect(surface, C.SAGE_GRAY, icon_box, 1, border_radius=10)

            item_img = assets.image_by_height(item["icon"], 40)
            surface.blit(item_img, item_img.get_rect(center=icon_box.center))

            # Назва та опис
            name_col = C.TEXT_DARK if not owned else C.DARK_SAGE
            name_t = assets.render_outlined(f_name, item["name"], name_col, (255, 255, 255), 1)
            surface.blit(name_t, (self.x + 90, iy + 6))

            desc_t = f_desc.render(item["desc"], True, C.DARK_SAGE)
            surface.blit(desc_t, (self.x + 90, iy + 34))

            # Кнопка дії
            btn_r = pygame.Rect(self.x + self.width - 150, iy + 14, 130, 36)
            self._btn_rects[item_id] = btn_r

            if owned:
                pygame.draw.rect(surface, (225, 245, 225), btn_r, border_radius=8)
                pygame.draw.rect(surface, C.PATIENCE_GOOD, btn_r, 1, border_radius=8)
                txt = assets.render_outlined(f_btn, "Куплено ✓", C.PATIENCE_GOOD, (240, 255, 240), 1)
                surface.blit(txt, txt.get_rect(center=btn_r.center))
            else:
                can_afford = (money >= item["price"])
                hover = btn_r.collidepoint(mouse_pos)

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
