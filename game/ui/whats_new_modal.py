"""
Модальне вікно «Що нового в оновленні» та картка сповіщення про оновлення версії.
"""
import pygame
import math
from typing import Optional, Dict, Any, List

from game.core.settings import C, WIDTH, HEIGHT, GAME_VERSION
from game.core.assets import assets
from game.core.audio import audio
from game.core.updater import updater, mark_whats_new_seen, get_current_changelog


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Розбиває довгий текст на рядки відповідно до максимальної ширини."""
    words = text.split(" ")
    lines = []
    cur_line = []
    for w in words:
        test_line = " ".join(cur_line + [w])
        if font.size(test_line)[0] <= max_width:
            cur_line.append(w)
        else:
            if cur_line:
                lines.append(" ".join(cur_line))
            cur_line = [w]
    if cur_line:
        lines.append(" ".join(cur_line))
    return lines


class WhatsNewModal:
    """
    Модальне вікно з новинами оновлення:
    - Показується автоматично при першому запуску після оновлення версії.
    - Може бути викликане вручну гравцем натисканням «Що нового?».
    - Може показувати новини доступної нової версії з кнопкою оновлення.
    """

    def __init__(self):
        self.is_open = False
        self.mode = "whats_new"     # "whats_new" або "update_available"
        self._t = 0.0
        self.scroll_y = 0
        self.max_scroll = 0

        # Геометрія модального вікна (по центру)
        self.width = 780
        self.height = 540
        self.x = (WIDTH - self.width) // 2
        self.y = (HEIGHT - self.height) // 2

        self.close_rect = pygame.Rect(self.x + self.width - 44, self.y + 16, 28, 28)
        self.btn_action_rect = pygame.Rect(self.x + (self.width - 240) // 2, self.y + self.height - 62, 240, 44)
        self.btn_site_rect = pygame.Rect(self.x + self.width - 200, self.y + self.height - 62, 170, 44)

    def open(self, mode: str = "whats_new"):
        """Відкрити вікно новин. mode: 'whats_new' або 'update_available'"""
        self.mode = mode
        self.is_open = True
        self.scroll_y = 0
        self._t = 0.0
        audio.play("ui_open")
        if mode == "whats_new":
            mark_whats_new_seen()

    def close(self):
        if self.is_open:
            self.is_open = False
            audio.play("ui_click")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        # Закриття по Escape або Пробілу
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
            self.close()
            return True

        # Прокрутка коліщатком миші
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 30))
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mx, my = event.pos

            # Кнопка [X]
            if self.close_rect.collidepoint(mx, my):
                self.close()
                return True

            # Клік за межами модалки закриває її
            modal_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if not modal_rect.collidepoint(mx, my):
                self.close()
                return True

            # Головна кнопка дії внизу
            if self.mode == "update_available":
                # Режим доступного оновлення:
                # Кнопка 1: Завантажити MiniCafe.exe
                if self.btn_action_rect.collidepoint(mx, my):
                    audio.play("cash_register")
                    updater.open_direct_download()
                    return True
                # Кнопка 2: Сторінка релізу
                if self.btn_site_rect.collidepoint(mx, my):
                    audio.play("ui_click")
                    updater.open_update_page()
                    return True
            else:
                # Режим «Що нового в поточній версії»: кнопка «Зрозуміло! До гри 🐾»
                if self.btn_action_rect.collidepoint(mx, my):
                    self.close()
                    return True

            return True

        # Блокуємо решту кліків всередині модального вікна
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
            return True

        return False

    def update(self, dt: float):
        if self.is_open:
            self._t += dt

    def draw(self, surface: pygame.Surface):
        if not self.is_open:
            return

        # 1. Затемнення фону (overlay)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((25, 20, 18, 175))
        surface.blit(overlay, (0, 0))

        # 2. Тінь та тіло модального вікна
        shadow_rect = pygame.Rect(self.x + 8, self.y + 10, self.width, self.height)
        pygame.draw.rect(surface, (15, 12, 10, 80), shadow_rect, border_radius=18)

        card_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, (255, 252, 246), card_rect, border_radius=18)
        pygame.draw.rect(surface, C.TERRACOTTA, card_rect, 2, border_radius=18)

        # 3. Декоративна смуга-шапка вгорі
        header_bar = pygame.Rect(self.x, self.y, self.width, 74)
        pygame.draw.rect(surface, (254, 243, 230), header_bar, border_top_left_radius=18, border_top_right_radius=18)
        pygame.draw.line(surface, (235, 215, 195), (self.x, self.y + 74), (self.x + self.width, self.y + 74), 1)

        # Іконка лапки / зірочки
        paw_icon = assets.image_by_height("ui_icon_paw", 26)
        surface.blit(paw_icon, (self.x + 22, self.y + 24))

        # Заголовок та підзаголовок
        f_title = assets.font_ui(20, bold=True)
        f_sub   = assets.font_ui(13)
        f_badge = assets.font_ui(12, bold=True)

        if self.mode == "update_available":
            v_name = updater.latest_version or "нова версія"
            title_str = f"✨ Доступне оновлення {v_name}!"
            sub_str = "Вийшла свіжа версія гри! Оновіть гру, щоб отримати всі нові можливості:"
        else:
            title_str = f"🎉 Що нового у MiniCafe {GAME_VERSION}?"
            sub_str = "Дякуємо, що граєте в MiniCafe! Ось головні нововведення цього релізу:"

        title_t = f_title.render(title_str, True, C.TEXT_DARK)
        surface.blit(title_t, (self.x + 58, self.y + 15))

        sub_t = f_sub.render(sub_str, True, C.DARK_SAGE)
        surface.blit(sub_t, (self.x + 58, self.y + 44))

        # Бейдж поточної версії в шапці
        badge_text = GAME_VERSION if self.mode != "update_available" else (updater.latest_version or "NEW")
        b_t = f_badge.render(badge_text, True, C.TERRACOTTA)
        bw, bh = b_t.get_width() + 14, 22
        bx = self.x + self.width - bw - 58
        by = self.y + 26
        pygame.draw.rect(surface, (255, 236, 225), (bx, by, bw, bh), border_radius=6)
        pygame.draw.rect(surface, C.TERRACOTTA, (bx, by, bw, bh), 1, border_radius=6)
        surface.blit(b_t, (bx + 7, by + 2))

        # Кнопка [X]
        mouse_pos = pygame.mouse.get_pos()
        close_hover = self.close_rect.collidepoint(mouse_pos)
        cx_col = C.TERRACOTTA if close_hover else (180, 150, 135)
        pygame.draw.rect(surface, (255, 238, 230) if close_hover else (248, 243, 235), self.close_rect, border_radius=6)
        pygame.draw.rect(surface, cx_col, self.close_rect, 1, border_radius=6)
        f_x = assets.font_ui(14, bold=True)
        xt = f_x.render("✕", True, cx_col)
        surface.blit(xt, xt.get_rect(center=self.close_rect.center))

        # 4. Область зі списком змін (кліп для скролу)
        content_rect = pygame.Rect(self.x + 22, self.y + 86, self.width - 44, self.height - 162)
        orig_clip = surface.get_clip()
        surface.set_clip(content_rect)

        # Отримуємо елементи новин
        changelog = get_current_changelog()
        items = changelog.get("items", [])

        # Якщо це режим "update_available", але новин на сервері немає — показуємо загальний список переваг оновлення
        if self.mode == "update_available":
            items = [
                {
                    "icon": "🚀",
                    "title": f"Свіжий бінарник {updater.latest_version}",
                    "desc": "Нові ігрові механіки, покращена оптимізація та найсвіжіші виправлення котячого кафе."
                },
                {
                    "icon": "⬇️",
                    "title": "Один готовий файл MiniCafe.exe",
                    "desc": "Автономний запуск без встановлення Python. Просто завантажте новий файл та грайте!"
                },
                {
                    "icon": "💾",
                    "title": "Збереження прогресу",
                    "desc": "Ваш профіль, збережені рекорди та статистика автоматично залишаться на вашому комп'ютері."
                }
            ]

        card_y = self.y + 88 - self.scroll_y
        card_w = content_rect.width - 10
        total_content_height = 0

        f_item_title = assets.font_ui(15, bold=True)
        f_item_desc  = assets.font_ui(13)
        f_emoji      = assets.font_ui(24)

        for item in items:
            desc_lines = _wrap_text(item["desc"], f_item_desc, card_w - 76)
            card_h = max(66, 34 + len(desc_lines) * 19)

            item_card = pygame.Rect(self.x + 24, card_y, card_w, card_h)
            # Малюємо картку
            pygame.draw.rect(surface, (255, 255, 255), item_card, border_radius=10)
            pygame.draw.rect(surface, (236, 226, 216), item_card, 1, border_radius=10)

            # Кружечок з іконкою зліва
            ico_box = pygame.Rect(item_card.x + 12, item_card.y + (card_h - 40) // 2, 40, 40)
            pygame.draw.rect(surface, (254, 245, 235), ico_box, border_radius=10)
            pygame.draw.rect(surface, (235, 210, 195), ico_box, 1, border_radius=10)

            ico_t = f_emoji.render(item.get("icon", "🐾"), True, C.TEXT_DARK)
            surface.blit(ico_t, ico_t.get_rect(center=ico_box.center))

            # Заголовок нововведення
            it_title_t = f_item_title.render(item["title"], True, C.TERRACOTTA)
            surface.blit(it_title_t, (item_card.x + 62, item_card.y + 8))

            # Опис по рядках
            for li, line in enumerate(desc_lines):
                d_t = f_item_desc.render(line, True, C.TEXT_DARK)
                surface.blit(d_t, (item_card.x + 62, item_card.y + 32 + li * 19))

            card_y += card_h + 10
            total_content_height += card_h + 10

        self.max_scroll = max(0, total_content_height - content_rect.height)
        surface.set_clip(orig_clip)

        # Смуга прокрутки, якщо вміст не поміщається
        if self.max_scroll > 0:
            bar_h = int(content_rect.height * (content_rect.height / total_content_height))
            bar_y = content_rect.y + int((content_rect.height - bar_h) * (self.scroll_y / self.max_scroll))
            pygame.draw.rect(surface, (220, 210, 200), (content_rect.right - 5, content_rect.y, 4, content_rect.height), border_radius=2)
            pygame.draw.rect(surface, C.TERRACOTTA, (content_rect.right - 5, bar_y, 4, bar_h), border_radius=2)

        # 5. Нижня панель дій
        action_bar = pygame.Rect(self.x, self.y + self.height - 74, self.width, 74)
        pygame.draw.rect(surface, (254, 248, 240), action_bar, border_bottom_left_radius=18, border_bottom_right_radius=18)
        pygame.draw.line(surface, (235, 220, 205), (self.x, action_bar.y), (self.x + self.width, action_bar.y), 1)

        f_btn = assets.font_ui(15, bold=True)

        if self.mode == "update_available":
            # Кнопка 1: Пряме завантаження MiniCafe.exe (по центру/ліворуч)
            btn1 = pygame.Rect(self.x + 50, self.y + self.height - 60, 310, 44)
            self.btn_action_rect = btn1
            h1 = btn1.collidepoint(mouse_pos)
            bg1 = (90, 175, 110) if h1 else (70, 150, 90)
            pygame.draw.rect(surface, bg1, btn1, border_radius=10)
            pygame.draw.rect(surface, (50, 120, 70), btn1, 1, border_radius=10)
            b1_t = assets.render_outlined(f_btn, "⬇️ Завантажити MiniCafe.exe", C.WHITE, (35, 75, 45), 1)
            surface.blit(b1_t, b1_t.get_rect(center=btn1.center))

            # Кнопка 2: Сторінка релізу GitHub (праворуч)
            btn2 = pygame.Rect(self.x + 380, self.y + self.height - 60, 240, 44)
            self.btn_site_rect = btn2
            h2 = btn2.collidepoint(mouse_pos)
            bg2 = C.BTN_HOVER if h2 else C.BTN_BG
            pygame.draw.rect(surface, bg2, btn2, border_radius=10)
            pygame.draw.rect(surface, C.TERRACOTTA, btn2, 1, border_radius=10)
            b2_t = assets.render_outlined(f_btn, "🌐 Сторінка релізу", C.WHITE, (60, 45, 40), 1)
            surface.blit(b2_t, b2_t.get_rect(center=btn2.center))

            # Кнопка «Пізніше»
            btn_later = pygame.Rect(self.x + self.width - 120, self.y + self.height - 60, 95, 44)
            self.close_rect_later = btn_later
            hl = btn_later.collidepoint(mouse_pos)
            pygame.draw.rect(surface, (240, 235, 228) if hl else (248, 245, 240), btn_later, border_radius=10)
            pygame.draw.rect(surface, (190, 180, 170), btn_later, 1, border_radius=10)
            fl_t = f_btn.render("Пізніше", True, (130, 120, 110))
            surface.blit(fl_t, fl_t.get_rect(center=btn_later.center))
        else:
            # Звичайна кнопка «Зрозуміло! До гри 🐾»
            btn = pygame.Rect(self.x + (self.width - 280) // 2, self.y + self.height - 60, 280, 46)
            self.btn_action_rect = btn
            h = btn.collidepoint(mouse_pos)
            bg = C.BTN_HOVER if h else C.BTN_BG
            pygame.draw.rect(surface, bg, btn, border_radius=12)
            pygame.draw.rect(surface, C.TERRACOTTA, btn, 2, border_radius=12)
            btn_t = assets.render_outlined(f_btn, "Зрозуміло! До гри 🐾", C.WHITE, (60, 45, 40), 1)
            surface.blit(btn_t, btn_t.get_rect(center=btn.center))
