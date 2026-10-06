"""
Экран конца дня — итоги, статистика, переход к следующему дню.
"""
import pygame
import math
from game.core.settings   import C, WIDTH, HEIGHT
from game.core.assets     import assets
from game.core.localization import locale
from game.ui.button       import Button
from game.ui.hud          import draw_star
from game.ui.shop         import ShopModal


class GameOverScene:
    def __init__(self, manager):
        self.manager = manager
        self._t      = 0.0
        self.day     = 1
        self.money   = 0
        self.rating  = 3.0
        self.orders_done = 0
        self.orders_bad  = 0
        self.upgrades    = {}
        self.failed      = False
        self.fail_reason = ""

        cx = WIDTH // 2
        self.btn_shop = Button(pygame.Rect(cx - 90, 485, 180, 44),
                               "Магазин", font_size=20)
        self.btn_next = Button(pygame.Rect(cx - 190, 545, 180, 48),
                               locale.get("game_over.next_day"), font_size=20)
        self.btn_menu = Button(pygame.Rect(cx + 10,  545, 180, 48),
                               locale.get("game_over.main_menu"), font_size=20)
        self._coins_anim = 0.0
        self.shop_modal = ShopModal()

    # ------------------------------------------------------------------
    def on_enter(self, day=1, money=0, rating=3.0, orders_done=0, orders_bad=0, upgrades=None,
                 failed=False, fail_reason=""):
        self.day        = day
        self.money      = money
        self.rating     = rating
        self.orders_done = orders_done
        self.orders_bad  = orders_bad
        self.upgrades   = upgrades or {}
        self.failed      = failed
        self.fail_reason = fail_reason
        self._t         = 0.0
        self._coins_anim = 0.0
        self.shop_modal.close()
        self.btn_next.set_text(locale.get("game_over.restart" if failed else "game_over.next_day"))
        self.btn_menu.set_text(locale.get("game_over.main_menu"))

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        # 1. Спершу обробка модального вікна магазину (якщо відкрите)
        handled, new_money, bought_id = self.shop_modal.handle_event(event, self.money, self.upgrades)
        if handled:
            self.money = new_money
            return

        if not self.failed and self.btn_shop.handle_event(event):
            self.shop_modal.open()
            return

        if self.btn_next.handle_event(event):
            if self.failed:
                # Провал: гра починається з нуля
                self.manager.switch("cafe_hall", day=1, money=0, rating=3.0, upgrades={})
            else:
                self.manager.switch("cafe_hall",
                                    day=self.day + 1,
                                    money=self.money,
                                    rating=self.rating,
                                    upgrades=self.upgrades)
        if self.btn_menu.handle_event(event):
            self.manager.switch("main_menu")

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._t += dt
        self._coins_anim = min(1.0, self._coins_anim + dt * 0.6)
        if not self.failed:
            self.btn_shop.update(dt)
        self.btn_next.update(dt)
        self.btn_menu.update(dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        cx = WIDTH // 2

        # 1. Фон улицы (bg_settings)
        bg_img = assets.image("bg_settings")
        if bg_img and not getattr(bg_img, "_is_placeholder", False):
            if not hasattr(self, "_cached_bg"):
                scaled = pygame.transform.smoothscale(bg_img, (1280, 1280))
                self._cached_bg = scaled.subsurface((0, 100, 1280, 720)).copy()
            surface.blit(self._cached_bg, (0, 0))
        else:
            surface.fill(C.DARK_SAGE)

        # 2. Затемнение фона
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 20, 20, 95))
        surface.blit(dim, (0, 0))

        # 3. Фирменная карточка-панель
        panel = assets.image("ui_panel")
        pw, ph = 480, 520
        panel_x = cx - pw // 2
        panel_y = 115
        panel_s = pygame.transform.smoothscale(panel, (pw, ph))
        surface.blit(panel_s, (panel_x, panel_y))

        # 4. Плашка заголовка
        banner = assets.image("ui_banner_plate")
        bw = 320
        bh = int(bw * (banner.get_height() / max(1, banner.get_width())))
        banner_s = pygame.transform.smoothscale(banner, (bw, bh))
        surface.blit(banner_s, banner_s.get_rect(center=(cx, panel_y + 40)))

        f_title = assets.font_title(26)
        title_key = "game_over.failed_title" if self.failed else "game_over.title"
        title_t = f_title.render(locale.get(title_key), True, C.WHITE)
        surface.blit(title_t, title_t.get_rect(center=(cx, panel_y + 38)))

        # 5. День
        f_ui = assets.font_ui(20)
        day_t = f_ui.render(f"{locale.get('hud.day')} {self.day}", True, C.CREAM)
        surface.blit(day_t, day_t.get_rect(center=(cx, panel_y + 90)))

        # 6. Звёзды рейтинга
        star_icon = assets.image_by_height("ui_icon_star", 26)
        for i in range(5):
            filled = (i < round(self.rating))
            sx = cx - 70 + i * 30
            sy = panel_y + 120
            if filled:
                surface.blit(star_icon, (sx, sy))
            else:
                dim_star = star_icon.copy()
                dim_star.fill((255, 255, 255, 80), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(dim_star, (sx, sy))

        # 7. Статистика
        f_main  = assets.font_main(24)
        f_small = assets.font_ui(16)
        stats = [
            (locale.get("game_over.earned"), f"+{self.money}", C.WHITE, True),
            (locale.get("game_over.orders_done"), f"{self.orders_done}", C.PATIENCE_GOOD, False),
            (locale.get("game_over.orders_cancelled"), f"{self.orders_bad}", C.PATIENCE_LOW, False),
        ]
        coin_icon = assets.image_by_height("ui_icon_coin", 22)
        for i, (label, val, color, has_coin) in enumerate(stats):
            y_row = panel_y + 175 + i * 56
            lbl_t = f_small.render(label, True, C.LIGHT_GRAY)
            val_t = f_main.render(val, True, color)
            surface.blit(lbl_t, (panel_x + 50, y_row))

            vx = panel_x + pw - val_t.get_width() - 50
            if has_coin:
                surface.blit(coin_icon, (vx - coin_icon.get_width() - 6, y_row + 2))
            surface.blit(val_t, (vx, y_row))

            pygame.draw.line(surface, (*C.LIGHT_GRAY, 60),
                             (panel_x + 45, y_row + 40),
                             (panel_x + pw - 45, y_row + 40), 1)

        # 7.1 Причина провалу
        if self.failed and self.fail_reason:
            f_reason = assets.font_ui(17)
            reason_t = assets.render_outlined(f_reason, locale.get(self.fail_reason), (255, 215, 200), (60, 30, 25), 1)
            surface.blit(reason_t, reason_t.get_rect(center=(cx, panel_y + 160)))

        # 8. Кнопки
        if not self.failed:
            self.btn_shop.draw(surface)
        self.btn_next.draw(surface)
        self.btn_menu.draw(surface)

        # 9. Счастливый котик над карточкой
        self._draw_happy_cat(surface, cx, panel_y - 25)

        # 10. Модальне вікно магазину (якщо відкрите)
        self.shop_modal.draw(surface, self.money, self.upgrades)

    def _draw_happy_cat(self, surface, x, y):
        bob = int(math.sin(self._t * 2) * 3)
        if self.failed:
            # Грустный котик: если спрайта cat_caramel_sad.png нет, при провале котика не рисуем
            import os
            from game.core.utils import resource_path
            if not os.path.exists(resource_path(os.path.join("assets", "sprites", "cat_caramel_sad.png"))):
                return
            cat_img = assets.image_by_height("cat_caramel_sad", 70)
        else:
            cat_img = assets.image_by_height("cat_caramel_happy", 70)
        if cat_img and not getattr(cat_img, "_is_placeholder", False):
            surface.blit(cat_img, cat_img.get_rect(midbottom=(x, y + bob)))
