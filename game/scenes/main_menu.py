"""
Главное меню — первый экран игры.
"""
import pygame
import math
import random
from game.core.settings   import C, WIDTH, HEIGHT
from game.core.assets     import assets
from game.core.localization import locale
from game.ui.button       import Button


class MainMenuScene:
    def __init__(self, manager):
        self.manager = manager
        self._t      = 0.0
        self._cats   = []       # декоративные котики (позиция, фаза, цвет)
        self._paws   = []       # декоративные следы лап

        self._build_ui()
        self._build_decoration()

    # ------------------------------------------------------------------
    def _build_ui(self):
        cx = 880
        self.btn_play     = Button(pygame.Rect(cx - 150, 260, 300, 64), locale.get("menu.play"),     font_size=30)
        self.btn_stats    = Button(pygame.Rect(cx - 150, 350, 300, 64), locale.get("menu.stats"),    font_size=26)
        self.btn_settings = Button(pygame.Rect(cx - 150, 440, 300, 64), locale.get("menu.settings"), font_size=26)
        self.btn_quit     = Button(pygame.Rect(cx - 150, 530, 300, 64), locale.get("menu.quit"),     font_size=26)

        # Кнопки выбора языка (маленькие)
        self.lang_buttons = []
        langs = [("uk", "УКР"), ("ru", "РУС"), ("en", "ENG")]
        for i, (code, label) in enumerate(langs):
            r = pygame.Rect(WIDTH - 180 + i * 58, 20, 52, 32)
            self.lang_buttons.append((code, label, r))

        self._buttons = [self.btn_play, self.btn_stats, self.btn_settings, self.btn_quit]

    def _build_decoration(self):
        # Случайные следы лап
        random.seed(42)
        self._paws = [(random.randint(650, WIDTH - 50),
                       random.randint(50, HEIGHT - 50),
                       random.uniform(0, math.pi * 2),
                       random.uniform(0.3, 0.7)) for _ in range(12)]

        # Декоративные котики на экране меню (убраны)
        self._cats = []

    # ------------------------------------------------------------------
    def on_enter(self, **kwargs):
        self._refresh_texts()

    def _refresh_texts(self):
        self.btn_play.set_text(locale.get("menu.play"))
        self.btn_stats.set_text(locale.get("menu.stats"))
        self.btn_settings.set_text(locale.get("menu.settings"))
        self.btn_quit.set_text(locale.get("menu.quit"))

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if self.btn_play.handle_event(event):
            self.manager.switch("cafe_hall")

        if self.btn_stats.handle_event(event):
            self.manager.switch("stats", back="main_menu")

        if self.btn_settings.handle_event(event):
            self.manager.switch("settings")

        if self.btn_quit.handle_event(event):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Язык
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for code, label, r in self.lang_buttons:
                if r.collidepoint(event.pos):
                    locale.set_lang(code)
                    self._refresh_texts()

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._t += dt
        for btn in self._buttons:
            btn.update(dt)
        for cat in self._cats:
            cat["phase"] += dt * 2.5

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        # --- Фон ---
        self._draw_background(surface)

        # --- Следы лап ---
        self._draw_paws(surface)

        # --- Котики-декор ---
        for cat in self._cats:
            self._draw_deco_cat(surface, cat)

        # --- Заголовок ---
        self._draw_title(surface)

        # --- Кнопки ---
        for btn in self._buttons:
            btn.draw(surface)

        # --- Языки ---
        self._draw_lang_buttons(surface)

        # --- Статус БД ---
        self._draw_db_status(surface)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _draw_background(self, surface: pygame.Surface):
        """Официальный фон улицы кафе (bg_menu) или градиентный fallback"""
        bg_img = assets.image("bg_menu")
        if bg_img and not getattr(bg_img, "_is_placeholder", False):
            # Масштабируем и центрируем фон улицы
            if not hasattr(self, "_cached_bg"):
                scaled = pygame.transform.smoothscale(bg_img, (1280, 1280))
                self._cached_bg = scaled.subsurface((0, 100, 1280, 720)).copy()
            surface.blit(self._cached_bg, (0, 0))

            # Мягкая затемняющая подложка справа для лучшей читаемости меню
            overlay = pygame.Surface((560, 720), pygame.SRCALPHA)
            for x in range(560):
                alpha = int(min(140, (x / 560) * 160))
                pygame.draw.line(overlay, (40, 36, 32, alpha), (x, 0), (x, 720))
            surface.blit(overlay, (720, 0))
        else:
            # Вертикальный градиент CREAM → LIGHT_GRAY
            for y in range(HEIGHT):
                t = y / HEIGHT
                r = int(255 + (C.LIGHT_GRAY[0] - 255) * t)
                g = int(248 + (C.LIGHT_GRAY[1] - 248) * t)
                b = int(235 + (C.LIGHT_GRAY[2] - 235) * t)
                pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

    # ------------------------------------------------------------------
    def _draw_paws(self, surface: pygame.Surface):
        """Лёгкие декоративные следы лапок"""
        for px, py, angle, alpha in self._paws:
            self._draw_paw_print(surface, px, py, int(alpha * 80), size=14)

    def _draw_paw_print(self, surface, x, y, alpha, size=14):
        s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        c = (*C.DUSTY_ROSE, alpha)
        # Основная подушечка
        pygame.draw.ellipse(s, c, (size // 2, size, size, size))
        # Пальчики
        for dx, dy in [(-size // 2, 0), (size // 2, 0), (-size // 4, -size // 2 - 2), (size // 4, -size // 2 - 2)]:
            pygame.draw.circle(s, c, (size + dx, size + dy), size // 4)
        surface.blit(s, (x - size, y - size))

    # ------------------------------------------------------------------
    def _draw_title(self, surface: pygame.Surface):
        cx = 880

        # Проверяем, сгенерирован ли отдельный логотип от пользователя
        import os
        from game.core.utils import resource_path
        logo_path = None
        for cand in ["logo_minicafe.png", "logo.png", "logo_header.png", "logo.jpeg"]:
            p = resource_path(os.path.join("assets", "sprites", cand))
            if os.path.exists(p):
                logo_path = p
                break
            p2 = resource_path(os.path.join("assets", cand))
            if os.path.exists(p2):
                logo_path = p2
                break

        if logo_path:
            logo_img = pygame.image.load(logo_path).convert_alpha()
            lw = 420
            lh = int(lw * (logo_img.get_height() / max(1, logo_img.get_width())))
            logo_s = pygame.transform.smoothscale(logo_img, (lw, lh))
            surface.blit(logo_s, logo_s.get_rect(center=(cx, 140)))
        else:
            # Плашка-баннер с кошачьими лапками
            banner = assets.image("ui_banner_plate")
            bw = 380
            bh = int(bw * (banner.get_height() / max(1, banner.get_width())))
            banner_s = pygame.transform.smoothscale(banner, (bw, bh))
            surface.blit(banner_s, banner_s.get_rect(center=(cx, 140)))

            # Основной заголовок MiniCafe
            title_f = assets.font_title(46, bold=True)
            title = assets.render_outlined(title_f, "MiniCafe", C.WHITE, (55, 45, 38), 2)
            surface.blit(title, title.get_rect(center=(cx, 137)))

            # Иконки лапок по бокам заголовка
            paw_icon = assets.image_by_height("ui_icon_paw", 32)
            surface.blit(paw_icon, (cx - title.get_width() // 2 - 42, 122))
            surface.blit(paw_icon, (cx + title.get_width() // 2 + 10, 122))

            # Подзаголовок
            sub_f = assets.font_main(20, bold=True)
            sub = assets.render_outlined(sub_f, locale.get("menu.subtitle"), C.CREAM, (55, 45, 38), 1)
            surface.blit(sub, sub.get_rect(center=(cx, 202)))

    # ------------------------------------------------------------------
    def _draw_deco_cat(self, surface: pygame.Surface, cat: dict):
        """Декоративный котик на скамейке у входа в кафе"""
        x, y = cat["x"], cat["y"]
        bob  = int(math.sin(cat["phase"]) * 2)
        spr = assets.image_by_height("cat_caramel_sit", 56)
        if spr and not getattr(spr, "_is_placeholder", False):
            surface.blit(spr, spr.get_rect(midbottom=(x, y + bob)))
        else:
            self._draw_simple_cat(surface, x, y + bob, cat["color"], cat["size"])

    def _draw_simple_cat(self, surface, x, y, color, size=40):
        r, g, b = color
        dark = (max(0, r - 35), max(0, g - 35), max(0, b - 35))

        # Тело
        pygame.draw.ellipse(surface, color, (x - size // 2, y - size // 3, size, size * 2 // 3))
        # Голова
        hr = size // 2
        pygame.draw.circle(surface, color, (x, y - hr), hr)
        # Уши
        pygame.draw.polygon(surface, dark, [(x - hr + 2, y - hr * 2 + 4), (x - hr - 6, y - hr * 2 - 10), (x - 4, y - hr + 2)])
        pygame.draw.polygon(surface, dark, [(x + hr - 2, y - hr * 2 + 4), (x + hr + 6, y - hr * 2 - 10), (x + 4, y - hr + 2)])
        # Глаза
        pygame.draw.circle(surface, C.CAT_DARK, (x - hr // 3, y - hr - 2), 4)
        pygame.draw.circle(surface, C.CAT_DARK, (x + hr // 3, y - hr - 2), 4)
        pygame.draw.circle(surface, C.WHITE, (x - hr // 3 + 1, y - hr - 3), 1)
        pygame.draw.circle(surface, C.WHITE, (x + hr // 3 + 1, y - hr - 3), 1)
        # Нос
        pygame.draw.circle(surface, (200, 140, 140), (x, y - hr + 5), 2)

    # ------------------------------------------------------------------
    def _draw_lang_buttons(self, surface: pygame.Surface):
        for code, label, r in self.lang_buttons:
            active = (locale.current == code)
            bg_col = C.TERRACOTTA if active else C.DARK_SAGE
            border_col = C.DUSTY_ROSE if active else C.SAGE_GRAY
            pygame.draw.rect(surface, bg_col, r, border_radius=8)
            pygame.draw.rect(surface, border_col, r, 2, border_radius=8)
            f = assets.font_ui(14, bold=True)
            t = assets.render_outlined(f, label, C.TEXT_LIGHT, (40, 35, 30), 1)
            surface.blit(t, t.get_rect(center=r.center))

    # ------------------------------------------------------------------
    def _draw_db_status(self, surface: pygame.Surface):
        from database.connection import is_online
        from game.core.localization import locale as loc
        key = "notify.connected" if is_online() else "notify.offline"
        f = assets.font_ui(13)
        t = f.render(loc.get(key), True, C.SAGE_GRAY)
        surface.blit(t, (12, HEIGHT - 24))
