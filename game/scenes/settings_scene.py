"""
Екран налаштувань — мова, звук, музика та перевірка оновлень гри.
"""
import pygame
from typing import Optional

from game.core.settings   import C, WIDTH, HEIGHT, GAME_VERSION
from game.core.assets     import assets
from game.core.localization import locale
from game.core.audio      import audio
from game.core.updater    import updater
from game.core.profile    import set_tutorial_completed, is_tutorial_completed
from game.ui.button       import Button
from game.ui.whats_new_modal import WhatsNewModal


class SettingsScene:
    def __init__(self, manager):
        self.manager    = manager
        self.sound_on   = audio.sfx_on
        self.music_on   = audio.music_on
        self.whats_new_modal = WhatsNewModal()
        self.check_status: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        cx = WIDTH // 2
        # Кнопки вибору мови
        langs = [("uk", "Українська"), ("ru", "Русский"), ("en", "English")]
        self.lang_btns = []
        for i, (code, label) in enumerate(langs):
            r = pygame.Rect(cx - 130, 205 + i * 42, 260, 36)
            self.lang_btns.append((code, label, Button(r, label, font_size=17)))

        self.btn_sound = Button(pygame.Rect(cx - 130, 338, 260, 40),
                                self._sound_label(), font_size=18)
        self.btn_music = Button(pygame.Rect(cx - 130, 384, 260, 40),
                                self._music_label(), font_size=18)

        # Кнопка оновлень
        btn_update_label = "Оновити гру зараз!" if updater.has_update else "Перевірити оновлення"
        self.btn_update = Button(pygame.Rect(cx - 130, 428, 260, 36),
                                 btn_update_label, font_size=16)

        # Кнопка повтору навчання (День 0)
        self.btn_tutorial = Button(pygame.Rect(cx - 130, 492, 260, 34),
                                   "Пройти навчання знову (День 0)", font_size=14)

        self.btn_back  = Button(pygame.Rect(cx - 110, 536, 220, 42),
                                locale.get("settings.back"), font_size=20)

    def _sound_label(self):
        state = locale.get("settings.on") if self.sound_on else locale.get("settings.off")
        return f"{locale.get('settings.sound')}: {state}"

    def _music_label(self):
        state = locale.get("settings.on") if self.music_on else locale.get("settings.off")
        return f"{locale.get('settings.music')}: {state}"

    def on_enter(self, **kwargs):
        self.sound_on = audio.sfx_on
        self.music_on = audio.music_on
        self.check_status = None
        self._build_ui()

    def handle_event(self, event: pygame.event.Event):
        if self.whats_new_modal.is_open:
            if self.whats_new_modal.handle_event(event):
                return

        if self.btn_back.handle_event(event):
            self.manager.switch("main_menu")
            return

        for code, label, btn in self.lang_btns:
            if btn.handle_event(event):
                locale.set_lang(code)
                self._build_ui()

        if self.btn_sound.handle_event(event):
            self.sound_on = not self.sound_on
            audio.set_sfx_enabled(self.sound_on)
            self.btn_sound.set_text(self._sound_label())
            audio.play("ui_click")

        if self.btn_music.handle_event(event):
            self.music_on = not self.music_on
            audio.set_music_enabled(self.music_on)
            self.btn_music.set_text(self._music_label())

        if self.btn_update.handle_event(event):
            audio.play("ui_click")
            if updater.has_update or updater.download_state in ("downloading", "completed"):
                self.whats_new_modal.open("update_available")
            else:
                self.check_status = "Перевірка зв'язку з GitHub..."
                self.btn_update.set_text("Перевірка...")

                def on_done(has_update):
                    if has_update:
                        self.check_status = f"Доступне оновлення {updater.latest_version}!"
                        self.btn_update.set_text("Оновити гру зараз!")
                        self.whats_new_modal.open("update_available")
                    else:
                        self.check_status = f"Встановлено найновішу версію ({GAME_VERSION})"
                        self.btn_update.set_text("Перевірити оновлення")

                updater.check(force=True, on_complete=on_done)

        if self.btn_tutorial.handle_event(event):
            audio.play("ui_click")
            set_tutorial_completed(False)
            self.check_status = "Навчання скинуто! При натисканні «Грати» почнеться День 0."

    def update(self, dt: float):
        if self.whats_new_modal.is_open:
            self.whats_new_modal.update(dt)
            return

        self.btn_back.update(dt)
        self.btn_sound.update(dt)
        self.btn_music.update(dt)
        self.btn_update.update(dt)
        self.btn_tutorial.update(dt)
        for _, _, btn in self.lang_btns:
            btn.update(dt)

    def draw(self, surface: pygame.Surface):
        cx, cy = WIDTH // 2, HEIGHT // 2

        # 1. Фон вулиці (bg_settings)
        bg_img = assets.image("bg_settings")
        if bg_img and not getattr(bg_img, "_is_placeholder", False):
            if not hasattr(self, "_cached_bg"):
                scaled = pygame.transform.smoothscale(bg_img, (1280, 1280))
                self._cached_bg = scaled.subsurface((0, 100, 1280, 720)).copy()
            surface.blit(self._cached_bg, (0, 0))
        else:
            surface.fill(C.DARK_SAGE)

        # 2. Затемнення для акценту на модальному вікні
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 20, 20, 90))
        surface.blit(dim, (0, 0))

        # 3. Фірмова картка-панель
        panel = assets.image("ui_panel")
        pw, ph = 460, 530
        panel_s = pygame.transform.smoothscale(panel, (pw, ph))
        surface.blit(panel_s, panel_s.get_rect(center=(cx, cy)))

        # 4. Плашка заголовка
        banner = assets.image("ui_banner_plate")
        bw = 290
        bh = int(bw * (banner.get_height() / max(1, banner.get_width())))
        banner_s = pygame.transform.smoothscale(banner, (bw, bh))
        surface.blit(banner_s, banner_s.get_rect(center=(cx, cy - 200)))

        f_title = assets.font_title(24)
        t = f_title.render(locale.get("settings.title"), True, C.WHITE)
        surface.blit(t, t.get_rect(center=(cx, cy - 202)))

        # 5. Мова
        f_label = assets.font_ui(14)
        lang_lbl = f_label.render(locale.get("settings.language"), True, C.LIGHT_GRAY)
        surface.blit(lang_lbl, lang_lbl.get_rect(center=(cx, 188)))
        for code, _, btn in self.lang_btns:
            btn.draw(surface)

        # 6. Звук / музика
        self.btn_sound.draw(surface)
        self.btn_music.draw(surface)

        # 7. Оновлення гри
        self.btn_update.draw(surface)

        # Підпис статусу версії
        f_info = assets.font_ui(12)
        stat_text = self.check_status or f"MiniCafe {GAME_VERSION}"
        stat_col = (80, 160, 90) if ("найновіш" in stat_text or "скинуто" in stat_text) else ((210, 110, 40) if "Доступне" in stat_text else C.LIGHT_GRAY)
        st_t = f_info.render(stat_text, True, stat_col)
        surface.blit(st_t, st_t.get_rect(center=(cx, 472)))

        # 8. Кнопка перезапуску навчання
        self.btn_tutorial.draw(surface)

        # 9. Кнопка Назад
        self.btn_back.draw(surface)

        # 10. Модальне вікно оновлення/новин, якщо відкрите
        if self.whats_new_modal.is_open:
            self.whats_new_modal.draw(surface)
