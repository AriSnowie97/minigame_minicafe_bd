"""
Кнопка с hover/press анимацией в стиле MiniCafe.
"""
import pygame
from game.core.settings import C
from game.core.assets import assets


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font_size: int = 28,
        color_bg=C.BTN_BG,
        color_hover=C.BTN_HOVER,
        color_press=C.BTN_PRESS,
        color_border=C.BTN_BORDER,
        color_text=C.TEXT_LIGHT,
        radius: int = 16,
        icon: pygame.Surface = None,
    ):
        self.rect        = pygame.Rect(rect)
        self.text        = text
        self.font_size   = font_size
        self.color_bg    = color_bg
        self.color_hover = color_hover
        self.color_press = color_press
        self.color_border= color_border
        self.color_text  = color_text
        self.radius      = radius
        self.icon        = icon

        self._hovered  = False
        self._pressed  = False
        self._scale    = 1.0      # для анимации
        self._anim_t   = 0.0

    # ------------------------------------------------------------------
    def set_text(self, text: str):
        self.text = text

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Возвращает True если кнопка была нажата (click)."""
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self.rect.collidepoint(event.pos):
                self._pressed = False
                return True
            self._pressed = False
        return False

    # ------------------------------------------------------------------
    def update(self, dt: float):
        target = 0.96 if self._pressed else (0.98 if self._hovered else 1.0)
        self._scale += (target - self._scale) * min(1.0, dt * 12)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        font  = assets.font_ui(self.font_size)
        color = self.color_press if self._pressed else (
                self.color_hover if self._hovered else self.color_bg)

        # Масштабируем rect вокруг центра
        cx, cy = self.rect.center
        w  = int(self.rect.width  * self._scale)
        h  = int(self.rect.height * self._scale)
        r  = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

        # Проверяем официальные спрайты кнопок
        state_name = "ui_button_pressed" if self._pressed else (
                     "ui_button_hover" if self._hovered else "ui_button_normal")
        base_spr = assets.image(state_name, (self.rect.width, self.rect.height))

        if base_spr:
            spr_to_draw = (pygame.transform.smoothscale(base_spr, (w, h)) 
                           if (w, h) != (self.rect.width, self.rect.height) else base_spr)
            surface.blit(spr_to_draw, r.topleft)
        else:
            # Тень
            shadow = r.move(3, 4)
            self._draw_rounded(surface, shadow, (0, 0, 0, 60), self.radius)
            # Тело
            self._draw_rounded(surface, r, color, self.radius)
            # Граница
            pygame.draw.rect(surface, self.color_border, r, 3, border_radius=self.radius)

        # Текст и иконка (с легким смещением вниз при нажатии)
        offset_y = 2 if self._pressed else -1
        txt_surf = assets.render_outlined(font, self.text, self.color_text, outline_color=(75, 52, 44), outline_width=1)
        if self.icon:
            total_w = self.icon.get_width() + 8 + txt_surf.get_width()
            ix = cx - total_w // 2
            iy = cy - self.icon.get_height() // 2 + offset_y
            surface.blit(self.icon, (ix, iy))
            surface.blit(txt_surf, (ix + self.icon.get_width() + 8,
                                    cy - txt_surf.get_height() // 2 + offset_y))
        else:
            surface.blit(txt_surf, txt_surf.get_rect(center=(cx, cy + offset_y)))

    # ------------------------------------------------------------------
    @staticmethod
    def _draw_rounded(surface, rect, color, radius):
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
        surface.blit(s, rect.topleft)
