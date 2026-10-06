"""
Экран настроек — язык, звук, музыка.
"""
import pygame
from game.core.settings   import C, WIDTH, HEIGHT
from game.core.assets     import assets
from game.core.localization import locale
from game.ui.button       import Button


class SettingsScene:
    def __init__(self, manager):
        self.manager    = manager
        self.sound_on   = True
        self.music_on   = True
        self._build_ui()

    def _build_ui(self):
        cx = WIDTH // 2
        # Кнопки языка внутри карточки
        langs = [("uk", "Українська"), ("ru", "Русский"), ("en", "English")]
        self.lang_btns = []
        for i, (code, label) in enumerate(langs):
            r = pygame.Rect(cx - 130, 215 + i * 50, 260, 44)
            self.lang_btns.append((code, label, Button(r, label, font_size=20)))

        self.btn_sound = Button(pygame.Rect(cx - 130, 380, 260, 46),
                                self._sound_label(), font_size=20)
        self.btn_music = Button(pygame.Rect(cx - 130, 435, 260, 46),
                                self._music_label(), font_size=20)

        self.btn_back  = Button(pygame.Rect(cx - 110, 505, 220, 50),
                                locale.get("settings.back"), font_size=24)

    def _sound_label(self):
        state = locale.get("settings.on") if self.sound_on else locale.get("settings.off")
        return f"{locale.get('settings.sound')}: {state}"

    def _music_label(self):
        state = locale.get("settings.on") if self.music_on else locale.get("settings.off")
        return f"{locale.get('settings.music')}: {state}"

    def on_enter(self, **kwargs):
        self._build_ui()

    def handle_event(self, event: pygame.event.Event):
        if self.btn_back.handle_event(event):
            self.manager.switch("main_menu")

        for code, label, btn in self.lang_btns:
            if btn.handle_event(event):
                locale.set_lang(code)
                self._build_ui()   # обновляем тексты

        if self.btn_sound.handle_event(event):
            self.sound_on = not self.sound_on
            self.btn_sound.set_text(self._sound_label())

        if self.btn_music.handle_event(event):
            self.music_on = not self.music_on
            self.btn_music.set_text(self._music_label())

    def update(self, dt: float):
        self.btn_back.update(dt)
        self.btn_sound.update(dt)
        self.btn_music.update(dt)
        for _, _, btn in self.lang_btns:
            btn.update(dt)

    def draw(self, surface: pygame.Surface):
        cx, cy = WIDTH // 2, HEIGHT // 2

        # 1. Фон улицы (смягченный bg_settings)
        bg_img = assets.image("bg_settings")
        if bg_img and not getattr(bg_img, "_is_placeholder", False):
            if not hasattr(self, "_cached_bg"):
                scaled = pygame.transform.smoothscale(bg_img, (1280, 1280))
                self._cached_bg = scaled.subsurface((0, 100, 1280, 720)).copy()
            surface.blit(self._cached_bg, (0, 0))
        else:
            surface.fill(C.DARK_SAGE)

        # 2. Затемнение для акцента на модальном окне
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 20, 20, 90))
        surface.blit(dim, (0, 0))

        # 3. Фирменная карточка-панель с кошачьими лапками в углах
        panel = assets.image("ui_panel")
        pw, ph = 460, 520
        panel_s = pygame.transform.smoothscale(panel, (pw, ph))
        surface.blit(panel_s, panel_s.get_rect(center=(cx, cy)))

        # 4. Плашка заголовка
        banner = assets.image("ui_banner_plate")
        bw = 290
        bh = int(bw * (banner.get_height() / max(1, banner.get_width())))
        banner_s = pygame.transform.smoothscale(banner, (bw, bh))
        surface.blit(banner_s, banner_s.get_rect(center=(cx, cy - 195)))

        f_title = assets.font_title(24)
        t = f_title.render(locale.get("settings.title"), True, C.WHITE)
        surface.blit(t, t.get_rect(center=(cx, cy - 197)))

        # 5. Кнопки языка
        f_label = assets.font_ui(15)
        lang_lbl = f_label.render(locale.get("settings.language"), True, C.LIGHT_GRAY)
        surface.blit(lang_lbl, lang_lbl.get_rect(center=(cx, 195)))
        for code, _, btn in self.lang_btns:
            btn.draw(surface)

        # 6. Звук / музыка
        self.btn_sound.draw(surface)
        self.btn_music.draw(surface)

        # 7. Назад
        self.btn_back.draw(surface)
