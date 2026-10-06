"""
Сущность: Столик (Table).
Хранит состояние, позицию на изо-сетке, текущий заказ.
"""
import pygame
import math
from game.core.settings import C
from game.core.assets   import assets
from game.core.localization import locale


class TableState:
    EMPTY   = "empty"
    SEATED  = "seated"     # клиент сидит, ещё не заказал
    ORDERED = "ordered"    # заказ принят, готовится
    READY   = "ready"      # заказ готов — нужно подать
    PAYING  = "paying"     # клиент платит


def iso_to_screen(col: int, row: int,
                  tile_w=80, tile_h=40,
                  origin_x=640, origin_y=220) -> tuple:
    sx = origin_x + (col - row) * (tile_w // 2)
    sy = origin_y + (col + row) * (tile_h // 2)
    return sx, sy


class CafeTable:
    """Один столик в зале"""

    def __init__(self, db_id: int, table_number: int, capacity: int,
                 location: str, grid_col: int, grid_row: int):
        self.db_id        = db_id
        self.table_number = table_number
        self.capacity     = capacity
        self.location     = location
        self.grid_col     = grid_col
        self.grid_row     = grid_row

        self.state        = TableState.EMPTY
        self.customer     = None   # ссылка на Customer
        self.order_id     = None   # ID в БД
        self.cook_timer   = 0.0    # оставшееся время готовки
        self.cook_total   = 0.0
        self._bounce      = 0.0    # анимация покачивания
        self._pulse       = 0.0
        self.is_queued_waiter = False
        self.is_picked_up = False
        self.waiter_order = False   # заказ принял официант (сам же отнесёт блюдо)

        # Экранные координаты столиков
        from game.core.settings import TABLE_COORDINATES, TABLE_GRID_POSITIONS, ISO_TILE_W, ISO_TILE_H, ISO_ORIGIN_X, ISO_ORIGIN_Y
        if db_id in TABLE_COORDINATES:
            sx, sy = TABLE_COORDINATES[db_id]
        elif db_id in TABLE_GRID_POSITIONS:
            gc, gr = TABLE_GRID_POSITIONS[db_id]
            self.grid_col = gc
            self.grid_row = gr
            sx, sy = iso_to_screen(gc, gr, ISO_TILE_W, ISO_TILE_H, ISO_ORIGIN_X, ISO_ORIGIN_Y)
        else:
            sx, sy = iso_to_screen(grid_col, grid_row, ISO_TILE_W, ISO_TILE_H, ISO_ORIGIN_X, ISO_ORIGIN_Y)
        self.screen_x = sx
        self.screen_y = sy

        # Кликабельная зона
        self.hitbox = pygame.Rect(sx - 48, sy - 38, 96, 76)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._bounce += dt * 3.0
        self._pulse  += dt * 4.0

        if self.state == TableState.ORDERED:
            self.cook_timer -= dt
            if self.cook_timer <= 0:
                self.cook_timer = 0.0
                self.state = TableState.READY

    # ------------------------------------------------------------------
    def start_order(self, order_id, menu_item, cook_time_sec: float):
        self.order_id   = order_id
        self.menu_item  = menu_item
        self.cook_timer = cook_time_sec
        self.cook_total = cook_time_sec
        self.state      = TableState.ORDERED
        self.is_picked_up = False

    # ------------------------------------------------------------------
    def reset(self):
        self.state      = TableState.EMPTY
        self.customer   = None
        self.order_id   = None
        self.cook_timer = 0.0
        self.cook_total = 0.0
        self.is_queued_waiter = False
        self.is_picked_up = False
        self.waiter_order = False

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        x, y = self.screen_x + offset_x, self.screen_y

        # Клиент сидит за столом и его спрайт уже включает стул и столик
        is_seated = (
            self.customer is not None and 
            self.customer.state in ("seated", "waiting", "order_taken", "eating", "paying")
        )

        if not is_seated:
            self._draw_furniture(surface, x, y)

        # --- Индикатор задачи официанта (официант идёт сюда) ---
        if self.is_queued_waiter:
            paw = assets.image_by_height("ui_icon_paw", 16)
            surface.blit(paw, (x - 8, y - 62 + int(math.sin(self._bounce) * 2)))

        # --- Иконка состояния ---
        if self.state == TableState.READY:
            from game.core.settings import get_item_sprite
            food_id = self.menu_item.get("id", 1) if getattr(self, "menu_item", None) else 1
            food_spr_name = get_item_sprite(food_id)
            dish_img = assets.image_by_height(food_spr_name, 22)

            bounce = int(math.sin(self._pulse * 1.5) * 3)

            if self.is_picked_up:
                # Официант взял блюдо на поднос — яркий маркер "Сюди!"
                bw, bh = 74, 26
                bx, by = x - bw // 2, y - 58 + bounce
                badge = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
                pygame.draw.rect(badge, (255, 248, 230), (0, 0, bw, bh), border_radius=8)
                pygame.draw.rect(badge, C.PATIENCE_GOOD, (0, 0, bw, bh), 2, border_radius=8)
                tail_pts = [(bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 5)]
                pygame.draw.polygon(badge, (255, 248, 230), tail_pts)
                pygame.draw.polygon(badge, C.PATIENCE_GOOD, tail_pts, 1)

                f = assets.font_ui(12)
                txt = f.render("Сюди!", True, C.TEXT_DARK)
                paw = assets.image_by_height("ui_icon_paw", 14)
                badge.blit(paw, (8, 6))
                badge.blit(txt, (26, 4))
                surface.blit(badge, (bx, by))
            else:
                # Блюдо готово на стойке у баристы, ждёт клика на стойку
                order_items = getattr(self, "order_items", [self.menu_item] if getattr(self, "menu_item", None) else [])
                if len(order_items) > 1:
                    spr1 = get_item_sprite(order_items[0].get("id", 1))
                    spr2 = get_item_sprite(order_items[1].get("id", 1))
                    img1 = assets.image_by_height(spr1, 20)
                    img2 = assets.image_by_height(spr2, 20)
                    bw, bh = img1.get_width() + img2.get_width() + 18, 26
                    bx, by = x - bw // 2, y - 52 + bounce
                    badge = pygame.Surface((bw, bh + 5), pygame.SRCALPHA)
                    pygame.draw.rect(badge, C.WHITE, (0, 0, bw, bh), border_radius=8)
                    pygame.draw.rect(badge, C.SAGE_GRAY, (0, 0, bw, bh), 2, border_radius=8)
                    tail_pts = [(bw // 2 - 3, bh), (bw // 2 + 3, bh), (bw // 2, bh + 4)]
                    pygame.draw.polygon(badge, C.WHITE, tail_pts)
                    pygame.draw.polygon(badge, C.SAGE_GRAY, tail_pts, 1)
                    badge.blit(img1, (6, (bh - img1.get_height()) // 2))
                    badge.blit(img2, (img1.get_width() + 10, (bh - img2.get_height()) // 2))
                    surface.blit(badge, (bx, by))
                else:
                    bw, bh = dish_img.get_width() + 14, 26
                    bx, by = x - bw // 2, y - 52 + bounce
                    badge = pygame.Surface((bw, bh + 5), pygame.SRCALPHA)
                    pygame.draw.rect(badge, C.WHITE, (0, 0, bw, bh), border_radius=8)
                    pygame.draw.rect(badge, C.SAGE_GRAY, (0, 0, bw, bh), 2, border_radius=8)
                    tail_pts = [(bw // 2 - 3, bh), (bw // 2 + 3, bh), (bw // 2, bh + 4)]
                    pygame.draw.polygon(badge, C.WHITE, tail_pts)
                    pygame.draw.polygon(badge, C.SAGE_GRAY, tail_pts, 1)

                    badge.blit(dish_img, (7, (bh - dish_img.get_height()) // 2))
                    surface.blit(badge, (bx, by))

        elif self.state == TableState.ORDERED:
            # Прогресс готовки баристой
            if self.cook_total > 0:
                prog = 1.0 - (self.cook_timer / self.cook_total)
                bar_w = 40
                bar_h = 5
                bx, by = x - bar_w // 2, y - 48
                pygame.draw.rect(surface, C.SAGE_GRAY,    (bx, by, bar_w, bar_h), border_radius=2)
                pygame.draw.rect(surface, C.PATIENCE_MID, (bx, by, int(bar_w * prog), bar_h), border_radius=2)


    # ------------------------------------------------------------------
    def _draw_furniture(self, surface: pygame.Surface, x: int, y: int):
        """Отрисовка официальных спрайтов стола и стульев точно по макету"""
        from game.core.settings import s_scale, CHAIR_RIGHT_TABLES
        right = self.table_number in CHAIR_RIGHT_TABLES   # стул справа сзади, иначе слева сзади
        side = 1 if right else -1
        # 1. Стул позади столика (в верхне-правом направлении x + 16, y - 16)
        if getattr(self, 'is_vip', False):
            arm_h = s_scale(240)
            arm_img = assets.image_by_height("furniture_armchair", arm_h)
            if not right:
                arm_img = pygame.transform.flip(arm_img, True, False)
            surface.blit(arm_img, arm_img.get_rect(center=(x + side * s_scale(45), y - s_scale(45))))
        else:
            chr_h = s_scale(240)
            chr_img = assets.image_by_height("furniture_chair", chr_h)
            if not right:
                chr_img = pygame.transform.flip(chr_img, True, False)
            surface.blit(chr_img, chr_img.get_rect(center=(x + side * s_scale(45), y - s_scale(45))))

        # 2. Круглый столик кафе спереди
        tbl_h = s_scale(250)
        tbl_img = assets.image_by_height("furniture_table", tbl_h)
        if not right:
            tbl_img = pygame.transform.flip(tbl_img, True, False)
        surface.blit(tbl_img, tbl_img.get_rect(center=(x, y)))

        # Золотистий бейдж для покращеного VIP-столика
        if getattr(self, 'is_vip', False):
            star_ic = assets.image_by_height("ui_icon_star", 18)
            surface.blit(star_ic, (x + s_scale(35) if right else x - s_scale(35) - 18, y - s_scale(55)))

