"""
Главное меню — первый экран игры.
"""
import pygame
import math
import random
from game.core.settings   import C, WIDTH, HEIGHT, GAME_VERSION
from game.core.assets     import assets
from game.core.localization import locale
from game.core.audio      import audio
from game.core.profile    import get_player_name, set_player_name
from game.core.updater    import updater, should_show_whats_new
from game.ui.button       import Button
from game.ui.whats_new_modal import WhatsNewModal


class MainMenuScene:
    def __init__(self, manager):
        self.manager = manager
        self._t      = 0.0
        self._cats   = []       # декоративные котики (позиция, фаза, цвет)
        self._paws   = []       # декоративные следы лап
        self.player_name = get_player_name()
        self.editing_name = False
        self.whats_new_modal = WhatsNewModal()
        self.whats_new_btn_rect = pygame.Rect(WIDTH - 145, HEIGHT - 32, 133, 24)
        cx = 880
        self.update_banner_rect = pygame.Rect(cx - 165, 578, 330, 52)

        self._build_ui()
        self._build_decoration()

        # Фоновий запуск перевірки нових версій гри
        updater.check_async()

    # ------------------------------------------------------------------
    def _build_ui(self):
        cx = 880
        self.btn_play     = Button(pygame.Rect(cx - 150, 260, 300, 64), locale.get("menu.play"),     font_size=30)
        self.btn_stats    = Button(pygame.Rect(cx - 150, 345, 300, 60), locale.get("menu.stats"),    font_size=26)
        self.btn_settings = Button(pygame.Rect(cx - 150, 425, 300, 60), locale.get("menu.settings"), font_size=26)
        self.btn_quit     = Button(pygame.Rect(cx - 150, 505, 300, 60), locale.get("menu.quit"),     font_size=26)

        # Картка імені гравця (для рейтингу) у правому верхньому кутку замість кнопок мов
        self.player_name_rect = pygame.Rect(WIDTH - 295, 18, 275, 46)
        self.lang_buttons = []

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
        self.player_name = get_player_name()
        self.editing_name = False

        # Якщо щойно оновили гру — автоматично показуємо новини оновлення!
        if should_show_whats_new():
            self.whats_new_modal.open("whats_new")

    def _refresh_texts(self):
        self.btn_play.set_text(locale.get("menu.play"))
        self.btn_stats.set_text(locale.get("menu.stats"))
        self.btn_settings.set_text(locale.get("menu.settings"))
        self.btn_quit.set_text(locale.get("menu.quit"))

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        # Якщо відкрите модальне вікно новин / оновлення версії
        if self.whats_new_modal.is_open:
            if self.whats_new_modal.handle_event(event):
                return

        # Введення імені гравця з клавіатури
        if self.editing_name:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.editing_name = False
                    self.player_name = set_player_name(self.player_name)
                    audio.play("ui_click")
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                else:
                    if len(self.player_name) < 20 and event.unicode and event.unicode.isprintable():
                        self.player_name += event.unicode
                return
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not self.player_name_rect.collidepoint(event.pos):
                    self.editing_name = False
                    self.player_name = set_player_name(self.player_name)

        if self.btn_play.handle_event(event):
            self.player_name = set_player_name(self.player_name)
            self.manager.switch("cafe_hall", day=1, money=0, rating=3.0, upgrades={}, player_name=self.player_name)

        if self.btn_stats.handle_event(event):
            self.manager.switch("stats", back="main_menu")

        if self.btn_settings.handle_event(event):
            self.manager.switch("settings")

        if self.btn_quit.handle_event(event):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Клік по картці імені гравця для редагування
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.player_name_rect.collidepoint(event.pos):
                audio.play("ui_click")
                self.editing_name = True
                return

            # Клік по кнопці «Що нового?» у правому нижньому кутку
            if self.whats_new_btn_rect.collidepoint(event.pos):
                audio.play("ui_click")
                self.whats_new_modal.open("whats_new")
                return

            # Клік по банеру доступного оновлення
            if updater.has_update and self.update_banner_rect.collidepoint(event.pos):
                audio.play("cash_register")
                self.whats_new_modal.open("update_available")
                return

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._t += dt
        self.whats_new_modal.update(dt)
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

        # --- Банер доступного оновлення гри ---
        if updater.has_update:
            self._draw_update_banner(surface)

        # --- Картка імені гравця (вгорі праворуч) ---
        self._draw_player_card(surface)

        # --- Статус БД та версія гри / новини ---
        self._draw_db_status(surface)
        self._draw_version_info(surface)

        # --- Модальне вікно «Що нового» / «Доступне оновлення» ---
        if self.whats_new_modal.is_open:
            self.whats_new_modal.draw(surface)

    def _draw_player_card(self, surface: pygame.Surface):
        """Картка з ім'ям гравця для участі у таблиці рекордів"""
        r = self.player_name_rect
        mouse = pygame.mouse.get_pos()
        hover = r.collidepoint(mouse)

        bg = (255, 252, 246) if not self.editing_name else (255, 248, 220)
        border = C.TERRACOTTA if (hover or self.editing_name) else C.SAGE_GRAY
        pygame.draw.rect(surface, bg, r, border_radius=10)
        pygame.draw.rect(surface, border, r, 2 if (hover or self.editing_name) else 1, border_radius=10)

        paw = assets.image_by_height("ui_icon_paw", 18)
        surface.blit(paw, (r.x + 10, r.y + 13))

        f_lbl = assets.font_ui(11)
        lbl_t = f_lbl.render("Ім'я в рейтингу:", True, C.DARK_SAGE)
        surface.blit(lbl_t, (r.x + 36, r.y + 5))

        # Ім'я
        f_name = assets.font_ui(14, bold=True)
        name_str = self.player_name
        if self.editing_name and (int(self._t * 2.5) % 2 == 0):
            name_str += "|"
        name_col = C.TERRACOTTA if self.editing_name else C.TEXT_DARK
        name_t = f_name.render(name_str, True, name_col)
        surface.blit(name_t, (r.x + 36, r.y + 20))

        # Підказка редагування
        hint_str = "[Enter]" if self.editing_name else "[змінити]"
        hint_t = f_lbl.render(hint_str, True, (160, 130, 110) if not hover else C.TERRACOTTA)
        surface.blit(hint_t, (r.right - hint_t.get_width() - 10, r.y + 15))


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

    def _draw_update_banner(self, surface: pygame.Surface):
        """Анімований банер-нагадування про доступне оновлення гри."""
        r = self.update_banner_rect
        mouse = pygame.mouse.get_pos()
        hover = r.collidepoint(mouse)

        # М'яка пульсація рамки для привернення уваги
        pulse = math.sin(self._t * 4.0) * 0.15 + 0.85
        bg_col = (255, 245, 225) if not hover else (255, 238, 205)
        border_col = (235, 130, 30) if hover else (int(220 * pulse), int(120 * pulse), int(30 * pulse))

        # Тінь
        pygame.draw.rect(surface, (0, 0, 0, 35), (r.x + 3, r.y + 4, r.width, r.height), border_radius=12)
        pygame.draw.rect(surface, bg_col, r, border_radius=12)
        pygame.draw.rect(surface, border_col, r, 2, border_radius=12)

        # Зірочка / подарунок зліва
        star_icon = assets.image_by_height("ui_icon_star", 22)
        bob = int(math.sin(self._t * 5.0) * 2)
        surface.blit(star_icon, (r.x + 12, r.y + 15 + bob))

        # Текст
        f_top = assets.font_ui(13, bold=True)
        f_sub = assets.font_ui(11)
        v_str = updater.latest_version or "нова версія"
        txt_top = f_top.render(f"✨ Доступне оновлення {v_str}!", True, C.TERRACOTTA)
        surface.blit(txt_top, (r.x + 42, r.y + 8))

        txt_sub = f_sub.render("Натисніть, щоб переглянути та завантажити ⬇️", True, (140, 80, 20) if hover else C.DARK_SAGE)
        surface.blit(txt_sub, (r.x + 42, r.y + 28))

    def _draw_version_info(self, surface: pygame.Surface):
        """Версія гри та компактна кнопка «Що нового?» у правому нижньому кутку."""
        # 1. Текст поточної версії
        f_ver = assets.font_ui(12)
        ver_t = f_ver.render(f"MiniCafe {GAME_VERSION}", True, (185, 165, 150))
        surface.blit(ver_t, (self.whats_new_btn_rect.x - ver_t.get_width() - 12, HEIGHT - 27))

        # 2. Кнопка «✨ Що нового?»
        r = self.whats_new_btn_rect
        mouse = pygame.mouse.get_pos()
        hover = r.collidepoint(mouse)

        bg = (255, 246, 238) if hover else (255, 252, 248)
        border = C.TERRACOTTA if hover else C.SAGE_GRAY
        pygame.draw.rect(surface, bg, r, border_radius=8)
        pygame.draw.rect(surface, border, r, 1, border_radius=8)

        f_btn = assets.font_ui(11, bold=True)
        txt_col = C.TERRACOTTA if hover else C.DARK_SAGE
        btn_t = f_btn.render("✨ Що нового?", True, txt_col)
        surface.blit(btn_t, btn_t.get_rect(center=r.center))
