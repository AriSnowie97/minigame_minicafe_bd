"""
Модальне вікно «Що нового в оновленні» та картка сповіщення про оновлення версії.
Повністю підтримує:
- Відображення списку нововведень (Changelog) поточної версії або свіжого релізу.
- Автоматичний або ручний запуск вбудованого завантаження оновлення MiniCafe.exe.
- Анімований прогрес-бар (МБ, %, швидкість) під час скачування.
- Кнопку безшовного перезапуску та оновлення гри в 1 клік.
- Виправлені іконки замість емодзі (жодних квадратів []).
"""
import pygame
import math
from typing import Optional, Dict, Any, List

from game.core.settings import C, WIDTH, HEIGHT, GAME_VERSION
from game.core.assets import assets
from game.core.audio import audio
from game.core.updater import updater, mark_whats_new_seen, get_current_changelog, CHANGELOGS


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
    - Може показувати новини доступної нової версії з кнопкою оновлення та прогрес-баром.
    """

    ICON_SPRITES = {
        "🚚": "vehicle_truck_closed",
        "truck": "vehicle_truck_closed",
        "delivery": "vehicle_truck_closed",
        "📦": "cat_mover_carry",
        "box": "cat_mover_carry",
        "warehouse": "cat_mover_carry",
        "stock": "cat_mover_carry",
        "🏆": "ui_icon_star",
        "trophy": "ui_icon_star",
        "star": "ui_icon_star",
        "leaderboard": "ui_icon_star",
        "profile": "ui_icon_star",
        "💰": "ui_icon_coin",
        "coin": "ui_icon_coin",
        "money": "ui_icon_coin",
        "finance": "ui_icon_coin",
        "🪑": "furniture_chair",
        "chair": "furniture_chair",
        "furniture": "furniture_chair",
        "interior": "furniture_chair",
        "🐾": "ui_icon_paw",
        "paw": "ui_icon_paw",
        "ari": "happy_ari",
        "teach": "teach_ari",
        "🚀": "ui_icon_star",
        "rocket": "ui_icon_star",
        "speed": "ui_icon_star",
        "💾": "ui_icon_coin",
        "save": "ui_icon_coin",
    }

    def __init__(self):
        self.is_open = False
        self.mode = "whats_new"     # "whats_new" або "update_available"
        self._t = 0.0
        self.scroll_y = 0
        self.max_scroll = 0
        self._icon_cache: Dict[str, pygame.Surface] = {}
        self.check_status_msg: Optional[str] = None

        # Геометрія модального вікна (по центру екрана)
        self.width = 780
        self.height = 540
        self.x = (WIDTH - self.width) // 2
        self.y = (HEIGHT - self.height) // 2

        self.close_rect = pygame.Rect(self.x + self.width - 44, self.y + 16, 28, 28)

        # Інтерактивні прямокутники кнопок
        self.btn_action_rect = pygame.Rect(0, 0, 1, 1)
        self.btn_site_rect = pygame.Rect(0, 0, 1, 1)
        self.btn_later_rect = pygame.Rect(0, 0, 1, 1)
        self.btn_cancel_rect = pygame.Rect(0, 0, 1, 1)
        self.btn_check_rect = pygame.Rect(0, 0, 1, 1)

    def _draw_icon(self, surface: pygame.Surface, icon_key: str, box_rect: pygame.Rect):
        """Малює красиву ігрову іконку замість шрифтових емодзі, уникаючи появи квадратів []."""
        key = str(icon_key).strip()
        if key in ("⬇️", "download"):
            cx, cy = box_rect.center
            col = (70, 150, 90)
            pygame.draw.line(surface, col, (cx, cy - 8), (cx, cy + 4), 3)
            pygame.draw.polygon(surface, col, [(cx - 6, cy + 3), (cx + 6, cy + 3), (cx, cy + 9)])
            pygame.draw.line(surface, col, (cx - 8, cy + 10), (cx + 8, cy + 10), 2)
            return

        spr_name = self.ICON_SPRITES.get(key, key)
        if key not in self._icon_cache:
            base = assets.image(spr_name)
            bw, bh = base.get_size()
            if bw > 0 and bh > 0:
                scale = min(30.0 / bw, 30.0 / bh)
                scaled = pygame.transform.smoothscale(base, (max(1, int(bw * scale)), max(1, int(bh * scale))))
            else:
                scaled = assets.image("ui_icon_paw", (26, 26))
            self._icon_cache[key] = scaled

        img = self._icon_cache[key]
        surface.blit(img, img.get_rect(center=box_rect.center))

    def open(self, mode: str = "whats_new"):
        """Відкрити вікно новин. mode: 'whats_new' або 'update_available'"""
        self.mode = mode
        self.is_open = True
        self.scroll_y = 0
        self._t = 0.0
        self.check_status_msg = None
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
            # Якщо завантажується оновлення, не закриваємо випадково по Escape
            if updater.download_state != "downloading":
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
                if updater.download_state != "downloading":
                    self.close()
                else:
                    updater.cancel_download()
                    self.close()
                return True

            # Клік за межами модалки закриває її
            modal_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if not modal_rect.collidepoint(mx, my):
                if updater.download_state != "downloading":
                    self.close()
                return True

            # ---------------------------------------------------------
            # Режим доступного оновлення
            # ---------------------------------------------------------
            if self.mode == "update_available":
                # Стан: очікування завантаження
                if updater.download_state == "idle":
                    # Головна кнопка: Оновити гру зараз (вбудоване завантаження)
                    if self.btn_action_rect.collidepoint(mx, my):
                        audio.play("cash_register")
                        updater.start_download()
                        return True

                    # Кнопка: Сторінка релізу
                    if self.btn_site_rect.collidepoint(mx, my):
                        audio.play("ui_click")
                        updater.open_update_page()
                        return True

                    # Кнопка: Пізніше
                    if self.btn_later_rect.collidepoint(mx, my):
                        self.close()
                        return True

                # Стан: скачування
                elif updater.download_state == "downloading":
                    if self.btn_cancel_rect.collidepoint(mx, my):
                        audio.play("ui_click")
                        updater.cancel_download()
                        return True

                # Стан: завантажено і готово до встановлення
                elif updater.download_state == "completed":
                    if self.btn_action_rect.collidepoint(mx, my):
                        audio.play("cash_register")
                        updater.apply_update_and_restart()
                        return True

                # Стан: помилка завантаження
                elif updater.download_state == "error":
                    if self.btn_action_rect.collidepoint(mx, my):
                        audio.play("ui_click")
                        updater.start_download()
                        return True
                    if self.btn_site_rect.collidepoint(mx, my):
                        audio.play("ui_click")
                        updater.open_direct_download()
                        return True
                    if self.btn_later_rect.collidepoint(mx, my):
                        self.close()
                        return True

            # ---------------------------------------------------------
            # Режим «Що нового у поточній версії»
            # ---------------------------------------------------------
            else:
                # Кнопка «Зрозуміло! До гри»
                if self.btn_action_rect.collidepoint(mx, my):
                    self.close()
                    return True

                # Кнопка «Перевірити оновлення»
                if self.btn_check_rect.collidepoint(mx, my):
                    audio.play("ui_click")
                    self.check_status_msg = "Перевірка зв'язку з сервером..."

                    def on_complete(has_update):
                        if has_update:
                            self.open("update_available")
                        else:
                            self.check_status_msg = f"У вас встановлена найновіша версія ({GAME_VERSION})!"

                    updater.check(force=True, on_complete=on_complete)
                    return True

            return True

        # Блокуємо решту кліків всередині модального вікна від передачі сцені під ним
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
        paw_icon = assets.image_by_height("ui_icon_star" if self.mode == "update_available" else "ui_icon_paw", 26)
        surface.blit(paw_icon, (self.x + 22, self.y + 24))

        # Заголовок та підзаголовок
        f_title = assets.font_ui(20, bold=True)
        f_sub   = assets.font_ui(13)
        f_badge = assets.font_ui(12, bold=True)

        if self.mode == "update_available":
            v_name = updater.latest_version or "нової версії"
            title_str = f"Доступне оновлення {v_name}!"
            sub_str = "Вийшла свіжа версія гри! Оновіть гру, щоб отримати всі покращення:"
        else:
            title_str = f"Що нового у MiniCafe {GAME_VERSION}?"
            sub_str = "Дякуємо, що граєте в MiniCafe! Ось головні нововведення цього релізу:"

        title_t = f_title.render(title_str, True, C.TEXT_DARK)
        surface.blit(title_t, (self.x + 58, self.y + 15))

        sub_t = f_sub.render(sub_str, True, C.DARK_SAGE)
        surface.blit(sub_t, (self.x + 58, self.y + 44))

        # Бейдж поточної / цільової версії в шапці
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
        cx, cy = self.close_rect.center
        sz = 5
        pygame.draw.line(surface, cx_col, (cx - sz, cy - sz), (cx + sz, cy + sz), 2)
        pygame.draw.line(surface, cx_col, (cx - sz, cy + sz), (cx + sz, cy - sz), 2)

        # 4. Область зі списком змін (кліп для скролу)
        content_rect = pygame.Rect(self.x + 22, self.y + 86, self.width - 44, self.height - 164)
        orig_clip = surface.get_clip()
        surface.set_clip(content_rect)

        # Отримуємо елементи новин
        if self.mode == "update_available":
            # Якщо є опис саме нової версії в CHANGELOGS
            target_v = updater.latest_version
            if target_v and target_v in CHANGELOGS:
                items = CHANGELOGS[target_v].get("items", [])
            else:
                items = [
                    {
                        "icon": "star",
                        "title": f"Свіжий випуск {updater.latest_version or 'нової версії'}",
                        "desc": "Нові ігрові можливості, покращена стабільність та свіжі виправлення для котячого кафе."
                    },
                    {
                        "icon": "box",
                        "title": "Вбудоване швидке оновлення",
                        "desc": "Гра завантажить новий файл MiniCafe.exe у фоні та автоматично замінить його при перезапуску."
                    },
                    {
                        "icon": "coin",
                        "title": "Збереження прогресу та профілю",
                        "desc": "Ваші збережені дні, таблиця лідерів та налаштування залишаються недоторканими на вашому ПК."
                    }
                ]
        else:
            changelog = get_current_changelog()
            items = changelog.get("items", [])

        card_y = self.y + 88 - self.scroll_y
        card_w = content_rect.width - 10
        total_content_height = 0

        f_item_title = assets.font_ui(15, bold=True)
        f_item_desc  = assets.font_ui(13)

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

            self._draw_icon(surface, item.get("icon", "paw"), ico_box)

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

        # Смуга прокрутки, якщо вміст перевищує висоту області
        if self.max_scroll > 0:
            bar_h = int(content_rect.height * (content_rect.height / total_content_height))
            bar_y = content_rect.y + int((content_rect.height - bar_h) * (self.scroll_y / self.max_scroll))
            pygame.draw.rect(surface, (220, 210, 200), (content_rect.right - 5, content_rect.y, 4, content_rect.height), border_radius=2)
            pygame.draw.rect(surface, C.TERRACOTTA, (content_rect.right - 5, bar_y, 4, bar_h), border_radius=2)

        # 5. Нижня панель дій
        action_bar = pygame.Rect(self.x, self.y + self.height - 76, self.width, 76)
        pygame.draw.rect(surface, (254, 248, 240), action_bar, border_bottom_left_radius=18, border_bottom_right_radius=18)
        pygame.draw.line(surface, (235, 220, 205), (self.x, action_bar.y), (self.x + self.width, action_bar.y), 1)

        f_btn = assets.font_ui(15, bold=True)
        f_info = assets.font_ui(12)

        # =============================================================
        # 5A. Режим доступного оновлення
        # =============================================================
        if self.mode == "update_available":
            # --- СТАН 1: Завантаження триває ---
            if updater.download_state == "downloading":
                # Прогрес-бар
                bar_rect = pygame.Rect(self.x + 35, self.y + self.height - 62, self.width - 170, 26)
                pygame.draw.rect(surface, (235, 225, 215), bar_rect, border_radius=8)
                fill_w = max(4, int(bar_rect.width * updater.download_progress))
                fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height)
                pygame.draw.rect(surface, (80, 175, 95), fill_rect, border_radius=8)
                pygame.draw.rect(surface, (170, 150, 130), bar_rect, 1, border_radius=8)

                # Текст прогресу на смузі
                pct = int(updater.download_progress * 100)
                prog_str = f"{pct}%  ({updater.downloaded_mb:.1f} / {updater.total_mb:.1f} МБ)  -  {updater.speed_str}"
                pt = f_info.render(prog_str, True, C.TEXT_DARK)
                surface.blit(pt, pt.get_rect(center=bar_rect.center))

                # Підпис знизу
                sub_info = f_info.render("Завантажуємо свіжу версію... Гра оновиться при перезапуску.", True, C.DARK_SAGE)
                surface.blit(sub_info, (self.x + 35, self.y + self.height - 30))

                # Кнопка Скасувати
                self.btn_cancel_rect = pygame.Rect(self.x + self.width - 125, self.y + self.height - 62, 95, 26)
                c_hover = self.btn_cancel_rect.collidepoint(mouse_pos)
                pygame.draw.rect(surface, (255, 230, 225) if c_hover else (245, 235, 230), self.btn_cancel_rect, border_radius=6)
                pygame.draw.rect(surface, C.TERRACOTTA, self.btn_cancel_rect, 1, border_radius=6)
                ct = f_info.render("Скасувати", True, C.TERRACOTTA)
                surface.blit(ct, ct.get_rect(center=self.btn_cancel_rect.center))

            # --- СТАН 2: Оновлення завантажено успішно ---
            elif updater.download_state == "completed":
                btn_restart = pygame.Rect(self.x + (self.width - 340) // 2, self.y + self.height - 62, 340, 46)
                self.btn_action_rect = btn_restart
                rh = btn_restart.collidepoint(mouse_pos)
                # Пульсуючий зелений колір
                pulse = math.sin(self._t * 5.0) * 0.15 + 0.85
                bg_g = (int(70 * pulse), int(175 * pulse), int(90 * pulse)) if not rh else (90, 195, 110)
                pygame.draw.rect(surface, bg_g, btn_restart, border_radius=12)
                pygame.draw.rect(surface, (40, 110, 55), btn_restart, 2, border_radius=12)

                rt = assets.render_outlined(f_btn, "Перезапустити гру зараз >>", C.WHITE, (30, 70, 40), 1)
                surface.blit(rt, rt.get_rect(center=btn_restart.center))

            # --- СТАН 3: Помилка завантаження ---
            elif updater.download_state == "error":
                err_str = f"Помилка: {updater.download_error or 'Збій з`єднання'}"
                et = f_info.render(err_str[:70], True, (180, 50, 40))
                surface.blit(et, (self.x + 35, self.y + self.height - 70))

                # Кнопка Спробувати знову
                b_retry = pygame.Rect(self.x + 35, self.y + self.height - 48, 190, 36)
                self.btn_action_rect = b_retry
                pygame.draw.rect(surface, C.BTN_BG, b_retry, border_radius=8)
                pygame.draw.rect(surface, C.TERRACOTTA, b_retry, 1, border_radius=8)
                rt_t = f_info.render("Спробувати знову", True, C.WHITE)
                surface.blit(rt_t, rt_t.get_rect(center=b_retry.center))

                # Кнопка Завантажити у браузері
                b_site = pygame.Rect(self.x + 235, self.y + self.height - 48, 200, 36)
                self.btn_site_rect = b_site
                pygame.draw.rect(surface, (245, 238, 230), b_site, border_radius=8)
                pygame.draw.rect(surface, C.DARK_SAGE, b_site, 1, border_radius=8)
                st_t = f_info.render("Відкрити у браузері", True, C.DARK_SAGE)
                surface.blit(st_t, st_t.get_rect(center=b_site.center))

                # Кнопка Закрити
                b_close = pygame.Rect(self.x + self.width - 120, self.y + self.height - 48, 90, 36)
                self.btn_later_rect = b_close
                pygame.draw.rect(surface, (240, 235, 230), b_close, border_radius=8)
                ct_t = f_info.render("Закрити", True, C.TEXT_DARK)
                surface.blit(ct_t, ct_t.get_rect(center=b_close.center))

            # --- СТАН 0: Звичайний екран готовності до оновлення (idle) ---
            else:
                # Кнопка 1: Оновити гру зараз (вбудоване скачування в грі)
                btn1 = pygame.Rect(self.x + 35, self.y + self.height - 60, 320, 44)
                self.btn_action_rect = btn1
                h1 = btn1.collidepoint(mouse_pos)
                bg1 = (90, 180, 110) if h1 else (70, 155, 90)
                pygame.draw.rect(surface, bg1, btn1, border_radius=10)
                pygame.draw.rect(surface, (45, 115, 60), btn1, 2, border_radius=10)
                b1_t = assets.render_outlined(f_btn, "Оновити гру зараз >>", C.WHITE, (30, 75, 40), 1)
                surface.blit(b1_t, b1_t.get_rect(center=btn1.center))

                # Кнопка 2: Сторінка релізу GitHub (по центру/праворуч)
                btn2 = pygame.Rect(self.x + 370, self.y + self.height - 60, 210, 44)
                self.btn_site_rect = btn2
                h2 = btn2.collidepoint(mouse_pos)
                bg2 = C.BTN_HOVER if h2 else C.BTN_BG
                pygame.draw.rect(surface, bg2, btn2, border_radius=10)
                pygame.draw.rect(surface, C.TERRACOTTA, btn2, 1, border_radius=10)
                b2_t = assets.render_outlined(f_btn, "Сторінка релізу", C.WHITE, (60, 45, 40), 1)
                surface.blit(b2_t, b2_t.get_rect(center=btn2.center))

                # Кнопка 3: Пізніше
                btn_later = pygame.Rect(self.x + self.width - 150, self.y + self.height - 60, 115, 44)
                self.btn_later_rect = btn_later
                hl = btn_later.collidepoint(mouse_pos)
                pygame.draw.rect(surface, (240, 235, 228) if hl else (248, 245, 240), btn_later, border_radius=10)
                pygame.draw.rect(surface, (190, 180, 170), btn_later, 1, border_radius=10)
                fl_t = f_btn.render("Пізніше", True, (130, 120, 110))
                surface.blit(fl_t, fl_t.get_rect(center=btn_later.center))

        # =============================================================
        # 5B. Режим «Що нового у поточній версії»
        # =============================================================
        else:
            # Кнопка «Зрозуміло! До гри» з іконкою лапки
            btn = pygame.Rect(self.x + 40, self.y + self.height - 62, 300, 46)
            self.btn_action_rect = btn
            h = btn.collidepoint(mouse_pos)
            bg = C.BTN_HOVER if h else C.BTN_BG
            pygame.draw.rect(surface, bg, btn, border_radius=12)
            pygame.draw.rect(surface, C.TERRACOTTA, btn, 2, border_radius=12)
            btn_t = assets.render_outlined(f_btn, "Зрозуміло! До гри", C.WHITE, (60, 45, 40), 1)
            paw_ico = assets.image_by_height("ui_icon_paw", 18)
            tot_w = btn_t.get_width() + 8 + paw_ico.get_width()
            bx = btn.centerx - tot_w // 2
            surface.blit(btn_t, (bx, btn.centery - btn_t.get_height() // 2))
            surface.blit(paw_ico, (bx + btn_t.get_width() + 8, btn.centery - paw_ico.get_height() // 2))

            # Кнопка «Перевірити оновлення»
            btn_chk = pygame.Rect(self.x + 360, self.y + self.height - 62, 230, 46)
            self.btn_check_rect = btn_chk
            hc = btn_chk.collidepoint(mouse_pos)
            pygame.draw.rect(surface, (250, 242, 234) if hc else (245, 238, 230), btn_chk, border_radius=12)
            pygame.draw.rect(surface, C.DARK_SAGE if not hc else C.TERRACOTTA, btn_chk, 1, border_radius=12)
            chk_label = "Перевірка..." if updater.is_checking else "Перевірити оновлення"
            chk_t = f_btn.render(chk_label, True, C.DARK_SAGE if not hc else C.TERRACOTTA)
            surface.blit(chk_t, chk_t.get_rect(center=btn_chk.center))

            # Повідомлення статусу перевірки праворуч
            if self.check_status_msg:
                st_t = f_info.render(self.check_status_msg, True, (60, 140, 70))
                surface.blit(st_t, (self.x + 605, self.y + self.height - 48))
