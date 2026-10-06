import math
import random
import pygame
from game.core.assets import assets
from game.core.settings import C, to_screen, s_scale


# Робочі місця кухаря на кухні (екранні координати кімнати) та що на яких готується
STATIONS = {
    "stove": (632.0, 470.0),   # плита
    "oven":  (548.0, 503.0),   # духовка
    "prep":  (498.0, 538.0),   # обробний стіл
}
DISH_STATION = {11: "stove", 8: "stove", 7: "stove", 6: "oven", 5: "oven", 9: "prep", 10: "prep"}
DISH_TEXT = {
    11: "Варю борщ на плиті!",
    8:  "Смажу омлет з беконом на плиті!",
    7:  "Смажу сирники на плиті!",
    6:  "Підсмажую брускету в духовці!",
    5:  "Випікаю тортик у духовці!",
    9:  "Ріжу овочі на салат Цезар!",
    10: "Збираю тірамісу на столі!",
}


class CatCook:
    """
    Котик-кухар на кухні (bg_kitchen.png).
    Готує замовлення на плиті та столі приготування,
    радіє готовим стравам та спілкується з гравцем.
    """
    STATE_IDLE = "idle"
    STATE_COOKING = "cooking"
    STATE_SERVE = "serve"
    STATE_HAPPY = "happy"

    QUOTES = [
        "Мяу! На кухні все під контролем! 🍳",
        "Люблю готувати смачненьке для котиків :3",
        "Замовлення смажиться на плиті! ✨",
        "Свіжі інгредієнти — запорука успіху! 🐟",
        "Зараз зробимо найапетитніший десерт! 🍰",
    ]

    def __init__(self, pos_2048: tuple = (1060, 1240)):
        self.pos_2048 = pos_2048
        self.screen_x, self.screen_y = to_screen(*pos_2048)
        self.height = s_scale(330)

        self.state = self.STATE_IDLE
        self._t = 0.0

        # Мова та репліки
        self.dialogue_text = ""
        self.dialogue_timer = 0.0

        # Анімація радості після приготування
        self.happy_timer = 0.0

        # Рух по кухні: куди йде кухар і на якому місці зараз готує
        self.home = (float(self.screen_x), float(self.screen_y))
        self.speed = 120.0
        self.moving = False
        self._dish_idx = 0
        self._cur_dish = None
        self._visit_timer = 0.0
        self._announce = False
        self._call_timer = 0.0

        # Хітбокс для кліку
        w = int(self.height * 0.75)
        self.hitbox = pygame.Rect(self.screen_x - w // 2, self.screen_y - self.height, w, self.height)

    def on_dish_ready(self):
        """Викликається коли замовлення щойно приготувалося"""
        self.happy_timer = 3.0
        self.state = self.STATE_HAPPY
        self.say(random.choice(["Дінь! Готово! Смачного! :3", "Мур! Замовлення на столі видачі! ✨"]), duration=2.8)

    def say(self, text: str, duration: float = 2.5):
        self.dialogue_text = text
        self.dialogue_timer = duration

    def on_click(self):
        """Клік гравця по котику-кухарю"""
        self.say(random.choice(self.QUOTES), duration=2.8)
        self.happy_timer = 1.5

    def set_home(self, x: float, y: float):
        """Місце, де кухар стоїть, коли нічого не готує"""
        self.home = (float(x), float(y))
        self.screen_x, self.screen_y = float(x), float(y)

    def _walk_to(self, tx: float, ty: float, dt: float) -> bool:
        """Іде до точки; True, коли дійшов"""
        dx, dy = tx - self.screen_x, ty - self.screen_y
        dist = math.hypot(dx, dy)
        if dist <= 3.0:
            self.screen_x, self.screen_y = tx, ty
            self.moving = False
            return True
        step = min(self.speed * dt, dist)
        self.screen_x += dx / dist * step
        self.screen_y += dy / dist * step
        self.moving = True
        return False

    def update(self, dt: float, is_cooking: bool = False, dishes=None, ready=None, has_waiter: bool = False):
        """dishes — id страв, що готуються зараз (до 3); ready — [(№ столика, назва)] готові, але не забрані"""
        self._t += dt
        dishes = dishes or []
        ready = ready or []

        if dishes:
            # Ходить між плитою, духовкою та столом залежно від страви; щоразу каже, що робить
            self._visit_timer -= dt
            if self._cur_dish not in dishes or self._visit_timer <= 0:
                if self._cur_dish in dishes and len(dishes) > 1:
                    self._dish_idx = (dishes.index(self._cur_dish) + 1) % len(dishes)
                else:
                    self._dish_idx = 0
                self._cur_dish = dishes[self._dish_idx]
                self._visit_timer = 4.5
                self._announce = True
            tx, ty = STATIONS[DISH_STATION.get(self._cur_dish, "stove")]
            if self._walk_to(tx, ty, dt) and self._announce:
                self._announce = False
                self.say(DISH_TEXT.get(self._cur_dish, "Готую смачненьке! 🍳"), duration=3.4)
        else:
            self._cur_dish = None
            self._announce = False
            self._walk_to(self.home[0], self.home[1], dt)

        # Готові страви: кухар кличе офіціанта (або гравця) забрати замовлення
        if ready and not dishes:
            self._call_timer -= dt
            if self._call_timer <= 0 and self.dialogue_timer <= 0:
                num, name = ready[0]
                if has_waiter:
                    self.say(f"Офіціанте! Заберіть {name} для столика №{num}!", duration=3.2)
                else:
                    self.say(f"{name} для столика №{num} готово! Заберіть на кухні!", duration=3.2)
                self._call_timer = 5.0
        else:
            self._call_timer = 0.0

        # Хітбокс слідує за кухарем
        w = int(self.height * 0.75)
        self.hitbox = pygame.Rect(int(self.screen_x) - w // 2, int(self.screen_y) - self.height, w, self.height)

        if self.dialogue_timer > 0:
            self.dialogue_timer -= dt
            if self.dialogue_timer <= 0:
                self.dialogue_text = ""

        if self.happy_timer > 0:
            self.happy_timer -= dt
            self.state = self.STATE_HAPPY if self.happy_timer > 1.2 else self.STATE_SERVE
        elif self.moving:
            self.state = self.STATE_IDLE
        elif is_cooking:
            self.state = self.STATE_COOKING
        else:
            self.state = self.STATE_IDLE

    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        draw_x = self.screen_x + offset_x
        draw_y = self.screen_y

        # Вибір спрайту
        if self.state == self.STATE_COOKING:
            spr_name = "cat_cook_cook"
            bob = math.sin(self._t * 9.0) * 3.0
        elif self.state == self.STATE_HAPPY:
            spr_name = "cat_cook_happy"
            bob = -abs(math.sin(self._t * 8.0)) * 5.0
        elif self.state == self.STATE_SERVE:
            spr_name = "cat_cook_serve"
            bob = math.sin(self._t * 4.0) * 2.0
        else:
            spr_name = "cat_cook_idle"
            bob = -abs(math.sin(self._t * 10.0)) * 3.0 if self.moving else math.sin(self._t * 2.2) * 2.0

        spr = assets.image_by_height(spr_name, self.height)
        rect = spr.get_rect(midbottom=(draw_x, int(draw_y + bob)))
        surface.blit(spr, rect)

        # Тінь під кухарем
        shadow_w = int(self.height * 0.45)
        shadow_h = int(shadow_w * 0.35)
        shadow_rect = pygame.Rect(draw_x - shadow_w // 2, draw_y - shadow_h // 2, shadow_w, shadow_h)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (50, 30, 20, 70), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow_surf, shadow_rect.topleft)

        # Діалогова хмарка
        if self.dialogue_text and self.dialogue_timer > 0:
            f = assets.font_ui(12, bold=True)
            txt = f.render(self.dialogue_text, True, (45, 30, 20))
            bw = txt.get_width() + 20
            bh = 26
            bx = draw_x - bw // 2
            by = rect.top - bh - 8

            bubble = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
            pygame.draw.rect(bubble, (255, 252, 245), (0, 0, bw, bh), border_radius=8)
            pygame.draw.rect(bubble, (220, 140, 70), (0, 0, bw, bh), 2, border_radius=8)
            tail = [(bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 5)]
            pygame.draw.polygon(bubble, (255, 252, 245), tail)
            pygame.draw.polygon(bubble, (220, 140, 70), tail, 1)
            bubble.blit(txt, (10, 4))
            surface.blit(bubble, (bx, by))
