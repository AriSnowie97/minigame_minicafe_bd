"""
Сущность: Бариста-котик (Barista).
Управляет состояниями анимации, работой за барной стойкой, реакциями на заказы и интерактивом.
"""
import pygame
import math
import random
from game.core.settings import (C, ISO_TILE_W, ISO_TILE_H, ISO_ORIGIN_X, ISO_ORIGIN_Y)
from game.core.assets import assets
from game.entities.table import iso_to_screen, TableState


class BaristaState:
    IDLE   = "idle"     # Спокойно ждёт за стойкой (:3)
    ORDER  = "order"    # Машет лапкой, приветствует / принимает заказ (:D)
    MAKING = "making"   # Взбивает молоко в питчере, готовит напиток
    SERVE  = "serve"    # Держит готовый стаканчик кофе, закрытые довольные глазки (^^)


class BaristaParticle:
    """Анимированная частица (пар над кофе, сердечко или искорка)"""
    def __init__(self, x: float, y: float, ptype: str = "steam"):
        self.x = x
        self.y = y
        self.ptype = ptype
        self.age = 0.0

        if ptype == "steam":
            self.lifetime = random.uniform(1.1, 1.6)
            self.vx = random.uniform(-3, 3)
            self.vy = random.uniform(-18, -26)
            self.size = random.uniform(3, 5)
        elif ptype == "heart":
            self.lifetime = random.uniform(1.2, 1.7)
            self.vx = random.uniform(-10, 10)
            self.vy = random.uniform(-25, -36)
            self.size = random.uniform(5, 7)
        else:  # sparkle
            self.lifetime = random.uniform(0.7, 1.1)
            self.vx = random.uniform(-14, 14)
            self.vy = random.uniform(-16, -26)
            self.size = random.uniform(3, 5)

    def update(self, dt: float) -> bool:
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.ptype == "steam":
            self.size += dt * 3.5
            self.x += math.sin(self.age * 4.0) * 0.4
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface):
        progress = self.age / self.lifetime
        alpha = max(0, int((1.0 - progress) * 220))

        if self.ptype == "steam":
            s = int(self.size)
            if s <= 1:
                return
            p_surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (245, 245, 250, alpha), (s, s), s)
            surface.blit(p_surf, (int(self.x - s), int(self.y - s)))
        elif self.ptype == "heart":
            hs = int(self.size)
            h_surf = pygame.Surface((hs * 2, hs * 2), pygame.SRCALPHA)
            col = (*C.TERRACOTTA, alpha)
            r = hs // 2
            pygame.draw.circle(h_surf, col, (r, r), r)
            pygame.draw.circle(h_surf, col, (hs + r, r), r)
            pygame.draw.polygon(h_surf, col, [(0, r), (hs * 2, r), (hs, hs * 2)])
            surface.blit(h_surf, (int(self.x - hs), int(self.y - hs)))
        else:  # sparkle
            ss = int(self.size)
            s_surf = pygame.Surface((ss * 2, ss * 2), pygame.SRCALPHA)
            col = (255, 215, 110, alpha)
            pygame.draw.line(s_surf, col, (ss, 0), (ss, ss * 2), 2)
            pygame.draw.line(s_surf, col, (0, ss), (ss * 2, ss), 2)
            surface.blit(s_surf, (int(self.x - ss), int(self.y - ss)))


class Barista:
    """Котик-бариста за изометрической барной стойкой с мебелью и витриной"""

    def __init__(self, grid_col: float = 8.2, grid_row: float = 0.0):
        self.grid_col = grid_col
        self.grid_row = grid_row

        from game.core.settings import s_scale
        # Екранні координати центру стійки — точно всередині підлоги кімнати без налізань на стіни та край
        self.screen_x, self.screen_y = 823, 512
        cw = s_scale(530)
        s = cw / 512.0
        self.showcase_x = self.screen_x + int(154 * s)
        self.showcase_y = self.screen_y - int(106 * s)

        # Состояние и таймеры
        self.state = BaristaState.IDLE
        self._temp_state = None
        self._temp_timer = 0.0

        self.anim_t = 0.0
        self._steam_timer = 0.0
        self.particles: list[BaristaParticle] = []

        # Облачко реплики
        self.speech_text = None
        self.speech_timer = 0.0
        self.speech_duration = 2.0

        # Клікабельна зона всієї барної зони (стійка + вітрина + каса)
        self.hitbox = pygame.Rect(self.screen_x - 110, self.screen_y - 95, 230, 160)

        # Уютные реплики при клике
        self._greetings = [
            "Мур-р! Ласкаво просимо! :3",
            "Кава зварена з любов'ю! *мур*",
            "Свіжа арабіка та ніжна пінка!",
            "Сьогодні чудовий день! ^^",
            "Мяу! Гарного вам настрою!",
            "Найкраща кава для улюблених гостей! :3",
            "Мурр! Робота кипить!",
        ]

        self._showcase_quotes = [
            "Свіжі круасани та тістечка! :3",
            "Сьогодні в меню ніжне тірамісу!",
            "Ароматна випічка з печі! ✨",
            "Хрусткі круасани до кави! ^^",
        ]

    # ------------------------------------------------------------------
    # Временные состояния и реплики
    # ------------------------------------------------------------------
    def set_temp_state(self, state: str, duration: float = 1.8):
        self._temp_state = state
        self._temp_timer = duration
        self.state = state

    def say(self, text: str, duration: float = 2.0):
        self.speech_text = text
        self.speech_duration = duration
        self.speech_timer = duration

    # ------------------------------------------------------------------
    # Игровые триггеры
    # ------------------------------------------------------------------
    def on_order_taken(self, item_name: str = ""):
        """Игрок принял заказ со столика"""
        self.set_temp_state(BaristaState.ORDER, duration=1.8)
        if item_name:
            self.say(f"Готую {item_name}! :3", duration=2.2)
        else:
            self.say("Прийнято! Готую :3", duration=2.0)
        self._spawn_burst("sparkle", count=5)

    def on_order_ready(self):
        """Заказ приготовился и ждет на стойке"""
        if self._temp_state is None:
            self.say("Замовлення готове! :3", duration=2.0)

    def on_order_served(self, coins: int = 0):
        """Заказ успешно подан гостю"""
        self.set_temp_state(BaristaState.SERVE, duration=1.8)
        self.say("Смачного! ^^", duration=2.2)
        self._spawn_burst("heart", count=5)

    def on_customer_entered(self):
        """В кафе вошел новый клиент"""
        if self.state == BaristaState.IDLE and self._temp_state is None:
            self.set_temp_state(BaristaState.ORDER, duration=1.4)
            self.say("Ласкаво просимо! :3", duration=1.8)

    def handle_click(self, mx: int, my: int) -> bool:
        """Интерактивный клик по баристе, кассе или витрине"""
        if not self.hitbox.collidepoint(mx, my):
            return False

        # Клик по витрине с десертами
        if abs(mx - self.showcase_x) < 45 and abs(my - (self.showcase_y - 20)) < 50:
            msg = random.choice(self._showcase_quotes)
            self.say(msg, duration=2.2)
            self._spawn_burst("sparkle", count=4)
            return True

        # Клик по баристе / стойке / кассе
        self.set_temp_state(BaristaState.ORDER, duration=2.0)
        msg = random.choice(self._greetings)
        self.say(msg, duration=2.2)
        self._spawn_burst("heart", count=4)
        self._spawn_burst("sparkle", count=4)
        return True

    def _spawn_burst(self, ptype: str, count: int = 4):
        cx, cy = self.screen_x, self.screen_y
        for _ in range(count):
            px = cx + random.uniform(-25, 25)
            py = cy + random.uniform(-40, -10)
            self.particles.append(BaristaParticle(px, py, ptype=ptype))

    # ------------------------------------------------------------------
    # Обновление
    # ------------------------------------------------------------------
    def update(self, dt: float, tables: list = None, customers: list = None):
        self.anim_t += dt

        # Обновление временного состояния
        if self._temp_timer > 0:
            self._temp_timer -= dt
            self.state = self._temp_state
            if self._temp_timer <= 0:
                self._temp_state = None

        # Если нет временного триггера — состояние определяется происходящим в кафе
        if self._temp_state is None and tables:
            has_ready = any(t.state == TableState.READY and not getattr(t, 'is_picked_up', False) for t in tables)
            has_cooking = any(t.state == TableState.ORDERED for t in tables)

            if has_ready:
                if self.state != BaristaState.SERVE and self.speech_timer <= 0:
                    self.say("Замовлення готове! :3", duration=2.0)
                self.state = BaristaState.SERVE
            elif has_cooking:
                self.state = BaristaState.MAKING
            else:
                self.state = BaristaState.IDLE

        # Облачко диалога
        if self.speech_timer > 0:
            self.speech_timer -= dt

        # Генерация пара при варке / подаче
        self._steam_timer -= dt
        if self._steam_timer <= 0:
            cx, cy = self.screen_x, self.screen_y
            if self.state == BaristaState.MAKING:
                # Пар над питчером и стойкой
                self.particles.append(BaristaParticle(cx - 2, cy - 14, "steam"))
                self._steam_timer = 0.25
            elif self.state == BaristaState.SERVE:
                # Пар над стаканчиком
                self.particles.append(BaristaParticle(cx - 6, cy - 16, "steam"))
                self._steam_timer = 0.4
            else:
                self._steam_timer = 1.0

        # Обновление частиц
        self.particles = [p for p in self.particles if p.update(dt)]

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        from game.core.settings import s_scale
        cx, cy = self.screen_x + offset_x, self.screen_y

        # Покачивание баристы
        if self.state == BaristaState.ORDER:
            bob = int(math.sin(self.anim_t * 6.0) * 2.0)
        elif self.state == BaristaState.MAKING:
            bob = int(math.sin(self.anim_t * 9.0) * 2.5)
        else:
            bob = int(math.sin(self.anim_t * 2.5) * 1.5)

        # 1. Задняя часть и основа стойки
        cw = s_scale(530)
        cb_img = assets.image("furniture_counter_back")
        cf_img = assets.image("furniture_counter_front")
        ch = int(cw * (cb_img.get_height() / max(1, cb_img.get_width())))
        s = cw / 512.0

        cb_s = pygame.transform.smoothscale(cb_img, (cw, ch))
        surface.blit(cb_s, (cx - cw // 2, cy - ch // 2))

        # 2. Спрайт баристы (внутри U стойки)
        self._draw_barista_sprite(surface, cx, cy, cw, ch, bob, s)

        # 3. Передняя часть стойки
        cf_s = pygame.transform.smoothscale(cf_img, (cw, ch))
        surface.blit(cf_s, (cx - cw // 2, cy - ch // 2))

        # 4. Кассовый аппарат на левом крыле стойки
        cash = assets.image_by_height("furniture_cash_register", s_scale(180))
        surface.blit(cash, cash.get_rect(center=(cx - int(141 * s), cy - int(51 * s))))

        # 5. Маленький вазончик с суккулентом на передней полке
        plant_s = assets.image_by_height("decor_plant_small", s_scale(75))
        surface.blit(plant_s, plant_s.get_rect(center=(cx - int(81 * s), cy - int(16 * s))))

        # 6. Кондитерская витрина на правом крыле стойки
        sc = assets.image_by_height("furniture_showcase", s_scale(200))
        surface.blit(sc, sc.get_rect(center=(cx + int(154 * s), cy - int(106 * s))))

        # 7. Частицы (пар, сердечки, искры)
        for p in self.particles:
            p.draw(surface)

        # 8. Реплика баристы (високо над головою котика, щоб не налізати на стійку, страви та статус готування)
        if self.speech_timer > 0 and self.speech_text:
            bubble_x = cx - int(4 * s) - 15
            bubble_y = cy - int(41 * s) - s_scale(300) - 22 + bob
            self._draw_speech_bubble(surface, bubble_x, bubble_y)

    def _draw_barista_sprite(self, surface: pygame.Surface, cx: int, cy: int, cw: int, ch: int, bob: int, s: float):
        """Отрисовка одного из 4-х официальных спрайтов баристы точно по макету"""
        from game.core.settings import s_scale
        sprite_name = f"barista_{self.state}"
        target_h = s_scale(300)
        barista = assets.image_by_height(sprite_name, target_h)
        rect = barista.get_rect(midbottom=(cx - int(4 * s), cy - int(41 * s) + bob))
        surface.blit(barista, rect)

    def _draw_speech_bubble(self, surface: pygame.Surface, cx: int, cy: int):
        """Уютное облачко реплики над головой баристы"""
        alpha_ratio = min(1.0, self.speech_timer / 0.4)
        alpha = int(alpha_ratio * 250)

        f = assets.font_ui(13)
        txt = f.render(self.speech_text, True, C.TEXT_DARK)
        bw = txt.get_width() + 18
        bh = 28
        bx = cx - bw // 2
        by = cy - bh

        bubble = pygame.Surface((bw, bh + 8), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (*C.WHITE, alpha), (0, 0, bw, bh), border_radius=10)
        pygame.draw.rect(bubble, (*C.TERRACOTTA, alpha), (0, 0, bw, bh), 2, border_radius=10)

        # Хвостик баббла направлен к шапочке баристы
        tail_x = max(12, min(bw - 12, bw // 2 + 14))
        tail_pts = [(tail_x - 4, bh), (tail_x + 4, bh), (tail_x, bh + 6)]
        pygame.draw.polygon(bubble, (*C.WHITE, alpha), tail_pts)
        pygame.draw.polygon(bubble, (*C.TERRACOTTA, alpha), tail_pts, 1)

        bubble.blit(txt, (9, 5))
        surface.blit(bubble, (bx, by))
