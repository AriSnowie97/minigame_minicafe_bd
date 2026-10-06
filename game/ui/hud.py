"""
HUD — верхняя панель: монеты, день, время, рейтинг (звёзды).
"""
import pygame
import math
from game.core.settings import C
from game.core.assets   import assets
from game.core.localization import locale


def draw_star(surface, cx, cy, r, filled: bool, color_fill=C.TERRACOTTA, color_empty=C.SAGE_GRAY):
    """Рисует звезду (5-конечную) вокруг центра cx,cy радиуса r."""
    pts_outer, pts_inner = [], []
    for i in range(5):
        a_o = math.radians(-90 + 72 * i)
        a_i = math.radians(-90 + 72 * i + 36)
        pts_outer.append((cx + r * math.cos(a_o), cy + r * math.sin(a_o)))
        pts_inner.append((cx + r * 0.4 * math.cos(a_i), cy + r * 0.4 * math.sin(a_i)))
    pts = []
    for o, i in zip(pts_outer, pts_inner):
        pts.append(o)
        pts.append(i)
    color = color_fill if filled else color_empty
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, C.TERRACOTTA if filled else C.DARK_SAGE, pts, 1)


class HUD:
    HEIGHT = 60   # высота панели

    def __init__(self, screen_w: int):
        self.screen_w = screen_w
        self._panel   = pygame.Surface((screen_w, self.HEIGHT), pygame.SRCALPHA)
        self.tab_kitchen_rect = pygame.Rect(670, 13, 105, 34)
        self.tab_hall_rect    = pygame.Rect(785, 13, 95, 34)
        self.tab_terrace_rect = pygame.Rect(890, 13, 120, 34)
        self.shop_rect        = pygame.Rect(self.screen_w - 245, 13, 115, 34)

    def draw(self, surface: pygame.Surface, money: int, day: int,
             time_left: float, day_duration: float, rating: float,
             orders_done: int, current_room: str = "hall", has_terrace: bool = False,
             kitchen_alert: bool = False, hall_alert: bool = False, terrace_alert: bool = False,
             has_kitchen: bool = True):

        # Фон панелі
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.rect(surface, (*C.DARK_SAGE, 230), (0, 0, self.screen_w, self.HEIGHT))
        pygame.draw.line(surface, C.TERRACOTTA, (0, self.HEIGHT - 2), (self.screen_w, self.HEIGHT - 2), 2)

        f_ui    = assets.font_ui(22, bold=True)
        f_label = assets.font_ui(14, bold=True)

        # --- Монети ---
        coin_x = 18
        coin_label = assets.render_outlined(f_label, locale.get("hud.money"), (245, 230, 220), (35, 40, 32), 1)
        surface.blit(coin_label, (coin_x, 5))
        coin_icon = assets.image_by_height("ui_icon_coin", 24)
        surface.blit(coin_icon, (coin_x, 26))
        coin_val = assets.render_outlined(f_ui, str(money), C.WHITE, (35, 40, 32), 1)
        surface.blit(coin_val, (coin_x + coin_icon.get_width() + 6, 25))

        # --- День ---
        day_x = 135
        day_label = assets.render_outlined(f_label, locale.get("hud.day"), (245, 230, 220), (35, 40, 32), 1)
        surface.blit(day_label, (day_x, 5))
        day_val = assets.render_outlined(f_ui, str(day), C.WHITE, (35, 40, 32), 1)
        surface.blit(day_val, (day_x, 25))

        # --- Таймер (progress bar з іконкою годинника) ---
        clock_x = 215
        clock_icon = assets.image_by_height("ui_icon_clock", 22)
        surface.blit(clock_icon, (clock_x, 26))

        bar_x = 242
        bar_w = 125
        bar_h = 16
        bar_y = 29
        progress = max(0.0, time_left / day_duration)
        bg_rect  = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        fill_rect = pygame.Rect(bar_x, bar_y, int(bar_w * progress), bar_h)
        pygame.draw.rect(surface, C.SAGE_GRAY, bg_rect, border_radius=8)
        bar_color = C.PATIENCE_GOOD if progress > 0.5 else (
                    C.PATIENCE_MID  if progress > 0.25 else C.PATIENCE_LOW)
        if fill_rect.width > 0:
            pygame.draw.rect(surface, bar_color, fill_rect, border_radius=8)
        pygame.draw.rect(surface, C.DARK_SAGE, bg_rect, 2, border_radius=8)
        time_label = assets.render_outlined(f_label, locale.get("hud.time"), (245, 230, 220), (35, 40, 32), 1)
        surface.blit(time_label, (bar_x, 5))

        # --- Замовлення ---
        ord_x = 393
        ord_label = assets.render_outlined(f_label, locale.get("hud.orders"), (245, 230, 220), (35, 40, 32), 1)
        surface.blit(ord_label, (ord_x, 5))
        ord_val = assets.render_outlined(f_ui, str(orders_done), C.WHITE, (35, 40, 32), 1)
        surface.blit(ord_val, (ord_x, 25))

        # --- Рейтинг (зірочки) ---
        star_x = 505
        rating_label = assets.render_outlined(f_label, locale.get("hud.rating"), (245, 230, 220), (35, 40, 32), 1)
        surface.blit(rating_label, (star_x, 5))
        star_icon = assets.image_by_height("ui_icon_star", 22)
        for i in range(5):
            filled = (i < round(rating))
            if filled:
                surface.blit(star_icon, (star_x + i * 25, 26))
            else:
                dim_star = star_icon.copy()
                dim_star.fill((255, 255, 255, 80), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(dim_star, (star_x + i * 25, 26))

        # --- Кнопки перемикання кімнат (Кухня / Зал / Тераса) ---
        f_tab = assets.font_ui(14, bold=True)
        kitchen_active = (current_room == "kitchen")
        hall_active    = (current_room == "hall")
        terrace_active = (current_room == "terrace")

        # 1. Вкладка Кухня
        k_hover = self.tab_kitchen_rect.collidepoint(mouse_pos)
        if has_kitchen:
            k_col = C.TERRACOTTA if kitchen_active else (C.BTN_HOVER if k_hover else (115, 120, 105))
            k_title = "Кухня"
        else:
            k_col = (90, 95, 80)
            k_title = "Кухня (160)"
        pygame.draw.rect(surface, k_col, self.tab_kitchen_rect, border_radius=9)
        pygame.draw.rect(surface, (255, 245, 235) if kitchen_active else C.DARK_SAGE, self.tab_kitchen_rect, 2 if kitchen_active else 1, border_radius=9)
        txt_k = assets.render_outlined(f_tab, k_title, C.WHITE if has_kitchen else (200, 195, 185), (45, 30, 20), 1)
        surface.blit(txt_k, txt_k.get_rect(center=self.tab_kitchen_rect.center))
        if kitchen_alert and not kitchen_active:
            pygame.draw.circle(surface, (240, 70, 60), (self.tab_kitchen_rect.right - 6, self.tab_kitchen_rect.top + 6), 6)

        # 2. Вкладка Зал
        hall_hover = self.tab_hall_rect.collidepoint(mouse_pos)
        hall_col = C.TERRACOTTA if hall_active else (C.BTN_HOVER if hall_hover else (115, 120, 105))
        pygame.draw.rect(surface, hall_col, self.tab_hall_rect, border_radius=9)
        pygame.draw.rect(surface, (255, 245, 235) if hall_active else C.DARK_SAGE, self.tab_hall_rect, 2 if hall_active else 1, border_radius=9)
        txt_h = assets.render_outlined(f_tab, "Зал", C.WHITE, (45, 30, 20), 1)
        surface.blit(txt_h, txt_h.get_rect(center=self.tab_hall_rect.center))
        if hall_alert and not hall_active:
            pygame.draw.circle(surface, (240, 70, 60), (self.tab_hall_rect.right - 6, self.tab_hall_rect.top + 6), 6)

        # 3. Вкладка Тераса
        terrace_hover = self.tab_terrace_rect.collidepoint(mouse_pos)
        if not has_terrace:
            t_col = (90, 95, 80)
            t_title = "Тераса (150)"
        else:
            t_col = C.TERRACOTTA if terrace_active else (C.BTN_HOVER if terrace_hover else (115, 120, 105))
            t_title = "Тераса"
        pygame.draw.rect(surface, t_col, self.tab_terrace_rect, border_radius=9)
        pygame.draw.rect(surface, (255, 245, 235) if terrace_active else C.DARK_SAGE, self.tab_terrace_rect, 2 if terrace_active else 1, border_radius=9)
        txt_t = assets.render_outlined(f_tab, t_title, (240, 240, 240) if has_terrace else (200, 195, 185), (45, 30, 20), 1)
        surface.blit(txt_t, txt_t.get_rect(center=self.tab_terrace_rect.center))
        if terrace_alert and not terrace_active:
            pygame.draw.circle(surface, (240, 70, 60), (self.tab_terrace_rect.right - 6, self.tab_terrace_rect.top + 6), 6)

        # --- Кнопка Магазину ---
        shop_hover = self.shop_rect.collidepoint(mouse_pos)
        shop_bg = C.BTN_HOVER if shop_hover else C.BTN_BG
        pygame.draw.rect(surface, shop_bg, self.shop_rect, border_radius=10)
        pygame.draw.rect(surface, C.TERRACOTTA, self.shop_rect, 2, border_radius=10)

        paw_s = assets.image_by_height("ui_icon_paw", 16)
        surface.blit(paw_s, (self.shop_rect.x + 8, self.shop_rect.y + 9))
        f_shop = assets.font_ui(15, bold=True)
        shop_t = assets.render_outlined(f_shop, "Магазин", C.WHITE, (85, 45, 35), 1)
        surface.blit(shop_t, (self.shop_rect.x + 28, self.shop_rect.y + 7))

        # --- Іконка шестерні / меню ---
        gear_icon = assets.image_by_height("ui_icon_settings", 26)
        surface.blit(gear_icon, (self.screen_w - 48, 17))

