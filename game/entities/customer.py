"""
Сущность: Клиент-котик (Customer).
Анимированный котик с состоянием, позицией, таймером терпения.
"""
import pygame
import math
import random
from game.core.settings import C, CUSTOMER_PATIENCE, CUSTOMER_CAT_COLORS
from game.core.assets   import assets
from game.core.localization import locale
from game.core.utils import lerp


class CustomerState:
    WALKING_IN  = "walking_in"
    SEATED      = "seated"
    WAITING     = "waiting"     # заказ не принят
    ORDER_TAKEN = "order_taken" # заказ принят, ждёт еду
    EATING      = "eating"
    PAYING      = "paying"
    LEAVING     = "leaving"
    GONE        = "gone"


class Customer:
    _id_counter = 0

    def __init__(self, target_table, menu_item: dict, spawn_x: int, spawn_y: int, max_patience: float = float(CUSTOMER_PATIENCE), order_items: list = None):
        Customer._id_counter += 1
        self.uid         = Customer._id_counter

        self.table       = target_table
        if order_items:
            self.menu_items = order_items
            self.menu_item  = order_items[0]
        else:
            self.menu_item  = menu_item
            self.menu_items = [menu_item]

        # Позиція входу/виходу (для тераси — арка, для залу — двері з килимком)
        if target_table and getattr(target_table, "table_number", 1) in (5, 6, 7, 8):
            self.door_x = 515.0
            self.door_y = 330.0
            self.mat_x  = 530.0
            self.mat_y  = 375.0
        else:
            self.door_x = 550.0
            self.door_y = 431.0
            self.mat_x  = 580.0
            self.mat_y  = 440.0

        self.x = float(spawn_x if spawn_x is not None else self.door_x)
        self.y = float(spawn_y if spawn_y is not None else self.door_y)
        self.exit_x = self.door_x
        self.exit_y = self.door_y
        self.target_x = float(target_table.screen_x)
        self.target_y = float(target_table.screen_y)

        self.walk_phase = "to_mat"
        self.leave_phase = "to_mat"
        self.state       = CustomerState.WALKING_IN
        self.max_patience = float(max_patience)
        self.patience    = self.max_patience
        self.eat_timer   = 8.0          # секунд на поедание
        self.pay_timer   = 2.0

        # Визуальные параметры
        self.breed       = random.choice([
            "caramel", "chocolate", "cream", "ginger", "graytabby", "lightgray"
        ])
        self.using_table_sprite = False
        self.cat_color   = random.choice(CUSTOMER_CAT_COLORS)
        self.anim_t      = random.uniform(0, math.pi * 2)  # фаза анимации
        self.direction   = "right"
        self.satisfied   = True         # стал ли доволен

        # Пузырь заказа
        self._bubble_alpha = 0
        self._coins_show   = 0.0        # время показа монет после оплаты

        self.earned_coins  = sum(int(it.get("price", 50)) for it in self.menu_items)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.anim_t += dt * 3.0

        if self.state in (CustomerState.SEATED, CustomerState.WAITING,
                          CustomerState.ORDER_TAKEN, CustomerState.EATING,
                          CustomerState.PAYING):
            self.using_table_sprite = True
        else:
            self.using_table_sprite = False

        if self.state == CustomerState.WALKING_IN:
            if self.walk_phase == "to_mat":
                self._move_towards(self.mat_x, self.mat_y, speed=120, dt=dt)
                if math.hypot(self.x - self.mat_x, self.y - self.mat_y) < 6:
                    self.walk_phase = "to_table"
            else:
                self._move_towards(self.target_x, self.target_y, speed=135, dt=dt)
                if math.hypot(self.x - self.target_x, self.y - self.target_y) < 6:
                    self.x, self.y = self.target_x, self.target_y
                    self.state = CustomerState.SEATED
                    self.table.state = "seated"

        elif self.state == CustomerState.SEATED:
            # Немного ждём, потом начинаем ждать заказ
            self.patience -= dt * 0.3
            if self.patience < self.max_patience - 1.8:
                self.state = CustomerState.WAITING

        elif self.state == CustomerState.WAITING:
            self.patience -= dt
            self._bubble_alpha = min(255, self._bubble_alpha + dt * 300)
            if self.patience <= 0:
                self.satisfied = False
                self._start_leaving()

        elif self.state == CustomerState.ORDER_TAKEN:
            self._bubble_alpha = max(0, self._bubble_alpha - dt * 200)
            self.patience -= dt * 0.4
            if self.patience <= 0:
                self.satisfied = False
                self._start_leaving()

        elif self.state == CustomerState.EATING:
            self.eat_timer -= dt
            if self.eat_timer <= 0:
                self.state = CustomerState.PAYING
                self.pay_timer = 2.0
                self._coins_show = 2.0

        elif self.state == CustomerState.PAYING:
            self.pay_timer -= dt
            self._coins_show = max(0.0, self._coins_show - dt)
            if self.pay_timer <= 0:
                self._start_leaving()

        elif self.state == CustomerState.LEAVING:
            if self.leave_phase == "to_mat":
                self._move_towards(self.mat_x, self.mat_y, speed=140, dt=dt)
                if math.hypot(self.x - self.mat_x, self.y - self.mat_y) < 8:
                    self.leave_phase = "to_door"
            else:
                self._move_towards(self.door_x, self.door_y, speed=140, dt=dt)
                if math.hypot(self.x - self.door_x, self.y - self.door_y) < 8:
                    self.state = CustomerState.GONE

        # Монеты
        if self._coins_show > 0:
            self._coins_show -= dt

    # ------------------------------------------------------------------
    def _move_towards(self, tx: float, ty: float, speed: float, dt: float):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 2:
            step = min(speed * dt, dist)
            self.x += dx / dist * step
            self.y += dy / dist * step
            self.direction = "right" if dx > 0 else "left"

    def _start_leaving(self):
        self.state = CustomerState.LEAVING
        self.leave_phase = "to_mat"
        self.table.reset()

    # ------------------------------------------------------------------
    def start_eating(self):
        self.state = CustomerState.EATING
        self.eat_timer = 8.0

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        import os
        from game.core.utils import resource_path

        ix, iy = int(self.x) + offset_x, int(self.y)

        # Выбираем позу и динамическую анимацию для котика
        if self.state in (CustomerState.WALKING_IN, CustomerState.LEAVING):
            pose = "walk"
            bob = int(math.sin(self.anim_t * 6.0) * 3)
        elif self.state == CustomerState.WAITING:
            # Анимация поднятия лапки: котик машет лапкой, подзывая заказ
            wave = math.sin(self.anim_t * 2.5)
            pose = "wait" if wave > -0.2 else "sit"
            bob = int(math.sin(self.anim_t * 2.0) * 1.5)
        elif self.state == CustomerState.ORDER_TAKEN:
            pose = "sit"
            bob = int(math.sin(self.anim_t * 1.5) * 1.0)
        elif self.state in (CustomerState.EATING, CustomerState.PAYING):
            # Счастливый довольный котик (прищуренные глазки ^^, улыбка, сердечко)
            pose = "happy"
            bob = int(math.sin(self.anim_t * 4.5) * 2.0)
        else:
            pose = "sit"
            bob = int(math.sin(self.anim_t * 1.5) * 1.0)

        sprite_name = f"cat_{self.breed}_{pose}"
        sprite_path = resource_path(os.path.join("assets", "sprites", f"{sprite_name}.png"))

        # Если для этого окраса конкретная поза ещё в процессе — берём ближайший готовый спрайт
        if not os.path.exists(sprite_path):
            fallback_breed = "cream" if self.breed == "ginger" else "graytabby"
            fallback_name = f"cat_{fallback_breed}_{pose}"
            if os.path.exists(resource_path(os.path.join("assets", "sprites", f"{fallback_name}.png"))):
                sprite_name = fallback_name
                sprite_path = resource_path(os.path.join("assets", "sprites", f"{fallback_name}.png"))

        has_sprite = os.path.exists(sprite_path)

        if has_sprite:
            if pose == "walk":
                spr = assets.image_by_height(sprite_name, 60)
                if self.direction == "left":
                    spr = pygame.transform.flip(spr, True, False)
                rect = spr.get_rect(midbottom=(ix, iy))
                surface.blit(spr, rect)
            else:
                spr = assets.image_by_height(sprite_name, 120)
                from game.core.settings import CHAIR_RIGHT_TABLES
                if getattr(self.table, "table_number", 0) in CHAIR_RIGHT_TABLES:
                    spr = pygame.transform.flip(spr, True, False)
                    rect = spr.get_rect(center=(ix + 21, iy - 14 + bob))
                else:
                    rect = spr.get_rect(center=(ix - 21, iy - 14 + bob))
                surface.blit(spr, rect)
        else:
            self._draw_cat(surface, ix, iy + bob)

        # Еда на столике перед котиком во время поедания
        if self.state in (CustomerState.EATING, CustomerState.PAYING):
            from game.core.settings import get_item_sprite
            if len(self.menu_items) > 1:
                spr1 = get_item_sprite(self.menu_items[0].get("id", 1))
                spr2 = get_item_sprite(self.menu_items[1].get("id", 1))
                img1 = assets.image_by_height(spr1, 22)
                img2 = assets.image_by_height(spr2, 22)
                surface.blit(img1, img1.get_rect(center=(ix - 10, iy - 6 + bob)))
                surface.blit(img2, img2.get_rect(center=(ix + 10, iy - 6 + bob)))
            else:
                food_spr_name = get_item_sprite(self.menu_item.get("id", 1))
                food_img = assets.image_by_height(food_spr_name, 28)
                surface.blit(food_img, food_img.get_rect(center=(ix, iy - 6 + bob)))

        # Пузырь заказа (показывается когда котик ждёт заказ)
        if self._bubble_alpha > 0 and self.state == CustomerState.WAITING:
            self._draw_order_bubble(surface, ix, iy + bob)

        # Монеты после оплаты
        if self._coins_show > 0:
            self._draw_coins(surface, ix, iy)

    # ------------------------------------------------------------------
    def _draw_cat(self, surface, x, y, size=36):
        """Рисует котика pygame.draw примитивами"""
        r, g, b = self.cat_color
        dark = (max(0, r - 35), max(0, g - 35), max(0, b - 35))
        ear_inner = (min(255, r + 40), min(255, int(g * 0.7)), min(255, int(b * 0.7)))

        flip = (self.direction == "left")
        ex = -1 if flip else 1   # направление

        # Тело
        body = pygame.Rect(x - size // 2, y - size // 3, size, size * 2 // 3)
        pygame.draw.ellipse(surface, self.cat_color, body)

        # Голова
        hr = size // 2
        hx = x + ex * (size // 5)
        hy = y - size // 2 - hr // 2
        pygame.draw.circle(surface, self.cat_color, (hx, hy), hr)

        # Уши (внешние)
        ear_l = [(hx - hr + 2, hy - hr // 2),
                 (hx - hr - 6, hy - hr - 10),
                 (hx - 4, hy - hr + 2)]
        ear_r = [(hx + hr - 2, hy - hr // 2),
                 (hx + hr + 6, hy - hr - 10),
                 (hx + 4, hy - hr + 2)]
        pygame.draw.polygon(surface, dark, ear_l)
        pygame.draw.polygon(surface, dark, ear_r)

        # Уши (внутренние — розовые)
        ear_li = [(hx - hr + 4, hy - hr // 2 - 1),
                  (hx - hr - 2, hy - hr - 6),
                  (hx - 6, hy - hr + 3)]
        ear_ri = [(hx + hr - 4, hy - hr // 2 - 1),
                  (hx + hr + 2, hy - hr - 6),
                  (hx + 6, hy - hr + 3)]
        pygame.draw.polygon(surface, ear_inner, ear_li)
        pygame.draw.polygon(surface, ear_inner, ear_ri)

        # Глаза
        blink = abs(math.sin(self.anim_t * 0.5)) > 0.95
        ey = hy - 2
        for ex_off in [-hr // 3, hr // 3]:
            ex_ = hx + ex_off
            if blink:
                pygame.draw.line(surface, C.CAT_DARK, (ex_ - 4, ey), (ex_ + 4, ey), 2)
            else:
                pygame.draw.circle(surface, C.CAT_DARK, (ex_, ey), 4)
                pygame.draw.circle(surface, C.WHITE, (ex_ + 1, ey - 1), 1)

        # Нос
        pygame.draw.circle(surface, (200, 140, 140), (hx, hy + 3), 2)

        # Усы
        for side in [-1, 1]:
            for wy in [-1, 1]:
                pygame.draw.line(surface, dark,
                                 (hx + side * 2, hy + 3 + wy),
                                 (hx + side * 12, hy + 2 + wy * 3), 1)

        # Хвост
        tail_x = x - ex * size // 2
        pygame.draw.arc(surface, self.cat_color,
                        pygame.Rect(tail_x - 15, y - 5, 24, 28),
                        math.pi * 0.1, math.pi * 0.9, 5)

    # ------------------------------------------------------------------
    def _draw_order_bubble(self, surface, x, y):
        """Компактный уютный баббл заказа прямо над головой котика с встроенной полоской терпения"""
        alpha = min(255, int(self._bubble_alpha))
        from game.core.settings import get_item_sprite

        items = getattr(self, "menu_items", [self.menu_item])
        is_double = len(items) > 1

        # Голова котика в сидячем спрайте находится левее центра столика: x - 36
        head_x = x - 36
        head_y = y - 42

        bw, bh = (68, 34) if is_double else (42, 34)
        bx = head_x - bw // 2
        by = head_y - bh - 6

        bubble = pygame.Surface((bw, bh + 5), pygame.SRCALPHA)
        # Фон и терракотовая обводка
        pygame.draw.rect(bubble, (*C.WHITE, alpha), (0, 0, bw, bh), border_radius=10)
        pygame.draw.rect(bubble, (*C.TERRACOTTA, alpha), (0, 0, bw, bh), 2, border_radius=10)

        # Хвостик баббла прямо к ушку котика
        tail_pts = [(bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 5)]
        pygame.draw.polygon(bubble, (*C.WHITE, alpha), tail_pts)
        pygame.draw.polygon(bubble, (*C.TERRACOTTA, alpha), tail_pts, 1)

        if is_double:
            # Дві страви поруч із плюсиком
            spr1 = get_item_sprite(items[0].get("id", 1))
            icon1 = assets.image_by_height(spr1, 20)
            if alpha < 255:
                icon1.set_alpha(alpha)
            bubble.blit(icon1, icon1.get_rect(center=(bw // 4 + 2, bh // 2 - 2)))

            plus_f = assets.font_ui(11, bold=True)
            plus_t = plus_f.render("+", True, (*C.TERRACOTTA, alpha))
            bubble.blit(plus_t, plus_t.get_rect(center=(bw // 2, bh // 2 - 2)))

            spr2 = get_item_sprite(items[1].get("id", 1))
            icon2 = assets.image_by_height(spr2, 20)
            if alpha < 255:
                icon2.set_alpha(alpha)
            bubble.blit(icon2, icon2.get_rect(center=(bw * 3 // 4 - 2, bh // 2 - 2)))
        else:
            item_spr_name = get_item_sprite(items[0].get("id", 1))
            item_icon = assets.image_by_height(item_spr_name, 22)
            icon_surf = item_icon.copy()
            if alpha < 255:
                icon_surf.set_alpha(alpha)
            bubble.blit(icon_surf, icon_surf.get_rect(center=(bw // 2, bh // 2 - 2)))

        # Встроенная аккуратная полоска терпения в нижний край баббла
        ratio = max(0.0, min(1.0, self.patience / getattr(self, 'max_patience', CUSTOMER_PATIENCE)))
        p_w = bw - 10
        p_h = 3
        px = 5
        py = bh - 5
        pygame.draw.rect(bubble, (*C.SAGE_GRAY, alpha), (px, py, p_w, p_h), border_radius=2)
        color = C.PATIENCE_GOOD if ratio > 0.5 else (
                C.PATIENCE_MID if ratio > 0.25 else C.PATIENCE_LOW)
        fw = max(1, int(p_w * ratio))
        pygame.draw.rect(bubble, (*color, alpha), (px, py, fw, p_h), border_radius=2)

        surface.blit(bubble, (bx, by))

    # ------------------------------------------------------------------
    def _draw_coins(self, surface, x, y):
        t = max(0.0, min(1.0, self._coins_show / 2.0))
        offset_y = int((1.0 - t) * 36)
        alpha = min(255, int(t * 300))

        coin_icon = assets.image_by_height("ui_icon_coin", 18)
        c_surf = coin_icon.copy()
        c_surf.set_alpha(alpha)

        f = assets.font_ui(16, bold=True)
        txt = assets.render_outlined(f, f"+{self.earned_coins}", (*C.PATIENCE_GOOD, alpha), (40, 35, 30), 1)

        total_w = txt.get_width() + c_surf.get_width() + 4
        start_x = x - total_w // 2
        cy = y - 55 - offset_y

        surface.blit(txt, (start_x, cy))
        surface.blit(c_surf, (start_x + txt.get_width() + 4, cy + (txt.get_height() - c_surf.get_height()) // 2))
