"""
Основная сцена игры — зал кафе.
Изометрический вид с уютным фоном, котиками-клиентами, котиком-баристой,
шеф-поваром Мурчиком, официантом с ручной подачей заказов,
системой магазина улучшений, прогрессией сложности и анимированной готовкой.
"""
import pygame
import math
import random
from game.core.settings import (C, WIDTH, HEIGHT, ISO_TILE_W, ISO_TILE_H,
                                 ISO_ORIGIN_X, ISO_ORIGIN_Y, GRID_COLS, GRID_ROWS,
                                 DAY_DURATION, COOKING_SPEED, CUSTOMER_PATIENCE,
                                 TABLE_GRID_POSITIONS, MENU_ITEM_KEYS, get_item_sprite)
from game.core.assets       import assets
from game.core.localization import locale
from game.entities.table    import CafeTable, TableState, iso_to_screen
from game.entities.customer import Customer, CustomerState
from game.entities.barista  import Barista, BaristaState
from game.entities.waiter   import Waiter, WaiterState
from game.entities.cook     import CatCook
from game.ui.hud            import HUD
from game.ui.shop           import ShopModal
from game.core.progression  import get_day_config
from database               import queries

# Горизонтальні координати кімнат у просторі безшовного панорамування камери
HALL_TABLES = (1, 2, 3, 4, 9, 10)
CHEF_ITEM_IDS = (5, 6, 7, 8, 9, 10, 11)   # страви кухаря (тортик теж, якщо кухар найнятий); напої — завжди бариста
HALL_PICKUP = (712.0, 566.0)           # де офіціант стоїть біля стійки баристи (на підлозі перед нею)
KITCHEN_PICKUP = (655.0, 595.0)        # видача на кухні
MENU_BOARD_POS = (868, 344)
MENU_BOARD_SIZE = (128, 98)

ROOM_OFFSETS = {
    "kitchen": -1280.0,
    "hall": 0.0,
    "terrace": 1280.0,
}


class Notification:
    def __init__(self, text: str, color: tuple, duration: float = 2.5):
        self.text     = text
        self.color    = color
        self.duration = duration
        self.timer    = duration

    @property
    def alive(self):
        return self.timer > 0

    def update(self, dt):
        self.timer -= dt

    def draw(self, surface, x, y):
        alpha = min(1.0, self.timer / 0.35)
        f     = assets.font_ui(13, bold=True)
        txt   = assets.render_outlined(f, self.text, self.color, (30, 25, 20), 1)
        tw, th = txt.get_size()
        pw, ph = tw + 22, th + 8
        pill = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(pill, (255, 252, 245, int(220 * alpha)), (0, 0, pw, ph), border_radius=10)
        pygame.draw.rect(pill, (*self.color[:3], int(210 * alpha)), (0, 0, pw, ph), 2, border_radius=10)
        txt.set_alpha(int(255 * alpha))
        pill.blit(txt, (11, 4))
        surface.blit(pill, pill.get_rect(center=(x, y)))


class StarParticle:
    """Іскри та зірочки, що вибухають при готовності страви на стійці"""
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(40, 115)
        self.vx = math.cos(ang) * spd
        self.vy = math.sin(ang) * spd - random.uniform(25, 65)
        self.size = random.uniform(4, 9)
        self.color = random.choice([
            (255, 235, 90),
            (255, 210, 50),
            (255, 255, 210),
            (255, 175, 50)
        ])
        self.life = random.uniform(0.65, 1.1)
        self.max_life = self.life

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 50 * dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        if self.life <= 0:
            return
        ratio = max(0.0, self.life / self.max_life)
        alpha = int(255 * ratio)
        sz = int(self.size * (0.4 + 0.6 * ratio))
        if sz < 2:
            return
        surf = pygame.Surface((sz * 2 + 2, sz * 2 + 2), pygame.SRCALPHA)
        col = (*self.color, alpha)
        cx, cy = sz + 1, sz + 1
        pygame.draw.line(surf, col, (cx - sz, cy), (cx + sz, cy), 2)
        pygame.draw.line(surf, col, (cx, cy - sz), (cx, cy + sz), 2)
        pygame.draw.circle(surf, (255, 255, 255, alpha), (cx, cy), max(1, sz // 3))
        surface.blit(surf, (int(self.x + offset_x - cx), int(self.y - cy)))


class CafeHallScene:

    def __init__(self, manager):
        self.manager      = manager
        self.hud          = HUD(WIDTH)
        self._t           = 0.0

        # Ігровий стан
        self.day          = 1
        self.money        = 0
        self.rating       = 3.0
        self.orders_done  = 0
        self.orders_bad   = 0
        self.time_left    = float(DAY_DURATION)

        # Оновлення кафе та магазин
        self.upgrades     = {}
        self.shop_modal   = ShopModal()
        self.day_cfg      = get_day_config(1, self.upgrades)

        # Анімація приготування та "Дінь!"
        self.star_particles: list[StarParticle] = []
        self.ready_pop_anim = 0.0
        self._prev_table_states = {}

        # Спавн клієнтів
        self._spawn_timer = 0.0
        self._spawn_interval = 10.0

        # Дані з БД
        self._menu_items  = []
        self._tables      = []
        self._employees   = []

        # Сутності
        self.customers: list[Customer] = []
        self.notifications: list[Notification] = []

        # Ручне обслуговування (на початкових рівнях до найму офіціанта)
        self.player_carrying_table = None
        self.pending_barista_orders: list[CafeTable] = []

        # Персонал: бариста та офіціант
        self.barista = Barista()
        self._init_barista_pos()

        self.waiter = Waiter(home_x=680.0, home_y=550.0, pickup_x=712.0, pickup_y=566.0)
        self.waiter.on_order_taken_cb = self._on_waiter_took_order
        self.waiter.on_order_served_cb = self._on_waiter_served_order

        # Кімнати закладу: "kitchen", "hall", "terrace" та плавне панорамування камери
        self.camera_x = 0.0
        self.target_camera_x = 0.0
        self.current_room = "hall"
        self.target_room = "hall"

        # Персонал кухні: котик-кухар
        self.cook = CatCook()
        self.cook.set_home(739, 533)

        # Кнопки навігації по краях екрана
        self.hall_to_kitchen_rect = pygame.Rect(15, 390, 180, 46)
        self.hall_to_terrace_rect = pygame.Rect(WIDTH - 195, 390, 180, 46)
        self.kitchen_to_hall_rect = pygame.Rect(WIDTH - 195, 390, 180, 46)
        self.terrace_to_hall_rect = pygame.Rect(15, 390, 180, 46)

        # Дверні арки в ізометрії (для кліку по дверях)
        self.arch_hall_to_kitchen = pygame.Rect(380, 310, 80, 120)
        self.arch_hall_to_terrace = pygame.Rect(800, 310, 80, 120)
        self.arch_kitchen_to_hall = pygame.Rect(760, 310, 80, 130)
        self.arch_terrace_to_hall = pygame.Rect(440, 180, 110, 140)

        # Стійка видачі готових страв баристи (у залі)
        self.counter_pickup_rect = pygame.Rect(700, 500, 95, 75)
        # Стіл видачі готових страв на кухні
        self.kitchen_pickup_rect  = pygame.Rect(565, 540, 90, 70)

        self._bg_surf = None
        self._bg_terrace_surf = None
        self._bg_kitchen_surf = None

    def switch_room(self, room_name: str):
        """Плавне переміщення поля видимості камери до обраної кімнати"""
        if room_name not in ROOM_OFFSETS:
            return
        if room_name == "terrace" and not self.day_cfg.get("has_terrace", False):
            self.notifications.append(
                Notification("Літня тераса закрита! Відкрийте її в Магазині (150 монет) :3", C.TERRACOTTA, 2.8)
            )
            self.shop_modal.open()
            return
        if room_name == "kitchen" and not self.upgrades.get("chef", False):
            self.notifications.append(
                Notification("Кухня закрита! Найміть шеф-кухаря Мурчика в Магазині (160 монет) :3", C.TERRACOTTA, 2.8)
            )
            self.shop_modal.open()
            return
        self.target_room = room_name
        self.target_camera_x = ROOM_OFFSETS[room_name]

    def _init_barista_pos(self):
        """Розміщення барної стійки у правому нижньому куті кімнати точно всередині підлоги"""
        cx, cy = 823, 512
        self.barista.screen_x = cx
        self.barista.screen_y = cy
        self.barista.hitbox = pygame.Rect(cx - 110, cy - 95, 230, 160)
        self.counter_pickup_rect = pygame.Rect(cx - 55, cy - 30, 75, 65)

    # ------------------------------------------------------------------
    def on_enter(self, day: int = 1, money: int = 0, rating: float = 3.0, upgrades: dict = None):
        self.day         = day
        self.money       = money
        self.rating      = rating
        self.orders_done = 0
        self.orders_bad  = 0
        self.time_left   = float(DAY_DURATION)
        self._spawn_timer = 2.0
        self.customers   = []
        self.notifications = []
        self.star_particles = []
        self.ready_pop_anim = 0.0
        self._prev_table_states = {}

        self.player_carrying_table = None
        self.pending_barista_orders = []

        if upgrades is not None:
            self.upgrades = upgrades
        elif not hasattr(self, 'upgrades') or self.upgrades is None:
            self.upgrades = {}

        # Ефект від Монстери (+0.5 до рейтингу)
        if self.upgrades.get("monstera", False) and self.rating < 3.5:
            self.rating = min(5.0, self.rating + 0.5)

        # Конфігурація дня з урахуванням складності та покупок
        self.day_cfg = get_day_config(self.day, self.upgrades)
        self._spawn_interval = self.day_cfg["spawn_interval"]

        self.shop_modal.close()

        # Скидання персоналу
        self.barista = Barista()
        self._init_barista_pos()

        self.waiter = Waiter(home_x=680.0, home_y=550.0, pickup_x=712.0, pickup_y=566.0)
        self.waiter.on_order_taken_cb = self._on_waiter_took_order
        self.waiter.on_order_served_cb = self._on_waiter_served_order

        # Завантажуємо дані з БД
        self._menu_items = queries.get_menu_items()
        tables_data      = queries.get_tables()
        self._employees  = queries.get_employees()

        # Створюємо столики
        self._tables = []
        for td in tables_data:
            tid = td["id"]
            tbl = CafeTable(
                db_id=tid,
                table_number=td["tablenumber"],
                capacity=td["capacity"],
                location=td["location"],
                grid_col=0,
                grid_row=0,
            )
            if tbl.table_number == 5:
                tbl.is_vip = self.upgrades.get("vip_armchair", False)
            self._tables.append(tbl)

        # Будуємо фон та скидаємо камеру на основний зал
        self.current_room = "hall"
        self.target_room = "hall"
        self.camera_x = 0.0
        self.target_camera_x = 0.0
        self._build_background()

        # Повідомлення про початок дня
        day_title = self.day_cfg.get("day_title", f"День {self.day}")
        self.notifications.append(Notification(f"~ {day_title} ~", C.TERRACOTTA, 3.5))

        # Спеціальна порада на 2-му тижні (котики замовляють по 2 страви)
        if self.day >= 8 and not self.upgrades.get("waiter", False):
            self.notifications.append(
                Notification("🐱 2-й тиждень! Гості замовляють по 2 страви! Рекомендуємо взяти офіціанта :3", C.TERRACOTTA, 4.2)
            )

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        # 1. Спершу обробка модального вікна магазину (якщо відкрите)
        if self.shop_modal.is_open:
            handled, new_money, bought_id = self.shop_modal.handle_event(event, self.money, self.upgrades)
            if handled:
                if bought_id:
                    self.money = new_money
                    self.day_cfg = get_day_config(self.day, self.upgrades)
                    if bought_id == "monstera":
                        self.rating = min(5.0, self.rating + 0.5)
                    for tbl in self._tables:
                        if tbl.table_number == 5:
                            tbl.is_vip = self.upgrades.get("vip_armchair", False)
                    if bought_id == "chef":
                        self.notifications.append(
                            Notification("Мурчик на кухні! Відкрито кухню та нові страви :3", C.NOTIF_GOOD, 3.5)
                        )
                    elif bought_id == "terrace":
                        self.notifications.append(
                            Notification("Літню терасу відкрито! Перемикайтесь кнопкою 'Тераса' вгорі! 🌿", C.NOTIF_GOOD, 3.5)
                        )
                    else:
                        self.notifications.append(
                            Notification("Покращення успішно придбано! :3", C.NOTIF_GOOD, 2.5)
                        )
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.switch("main_menu")
            elif event.key in (pygame.K_1, pygame.K_k):
                self.switch_room("kitchen")
            elif event.key in (pygame.K_2, pygame.K_h):
                self.switch_room("hall")
            elif event.key in (pygame.K_3, pygame.K_t):
                self.switch_room("terrace")
            elif event.key == pygame.K_LEFT:
                if self.target_room == "terrace":
                    self.switch_room("hall")
                elif self.target_room == "hall":
                    self.switch_room("kitchen")
            elif event.key == pygame.K_RIGHT:
                if self.target_room == "kitchen":
                    self.switch_room("hall")
                elif self.target_room == "hall":
                    self.switch_room("terrace")

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mx, my = event.pos

            # 2. Клік по кнопці Магазину в HUD
            if hasattr(self.hud, 'shop_rect') and self.hud.shop_rect and self.hud.shop_rect.collidepoint(mx, my):
                self.shop_modal.open()
                return

            # 3. Вкладки перемикання кімнат в HUD (Кухня / Зал / Тераса)
            if hasattr(self.hud, 'tab_kitchen_rect') and self.hud.tab_kitchen_rect.collidepoint(mx, my):
                self.switch_room("kitchen")
                return

            if hasattr(self.hud, 'tab_hall_rect') and self.hud.tab_hall_rect.collidepoint(mx, my):
                self.switch_room("hall")
                return

            if hasattr(self.hud, 'tab_terrace_rect') and self.hud.tab_terrace_rect.collidepoint(mx, my):
                self.switch_room("terrace")
                return

            # 4. Переходи між кімнатами та взаємодія залів
            if self.target_room == "hall":
                # Перехід на кухню (ліворуч)
                if self.hall_to_kitchen_rect.collidepoint(mx, my) or self.arch_hall_to_kitchen.collidepoint(mx, my):
                    self.switch_room("kitchen")
                    return

                # Перехід на терасу (праворуч)
                if self.hall_to_terrace_rect.collidepoint(mx, my) or self.arch_hall_to_terrace.collidepoint(mx, my):
                    self.switch_room("terrace")
                    return

                # Клік по барній стійці / видачі страв
                if self.counter_pickup_rect.collidepoint(mx, my) or self.barista.hitbox.collidepoint(mx, my):
                    if self._on_counter_click(mx, my):
                        return

                # Клік по столиках залу (1..4)
                for tbl in [t for t in self._tables if t.table_number in HALL_TABLES]:
                    if tbl.hitbox.collidepoint(mx, my):
                        self._on_table_click(tbl)
                        return

            elif self.target_room == "kitchen":
                # Перехід до залу кафе (праворуч)
                if self.kitchen_to_hall_rect.collidepoint(mx, my) or self.arch_kitchen_to_hall.collidepoint(mx, my):
                    self.switch_room("hall")
                    return

                # Клік по котику-кухарю
                if self.cook.hitbox.collidepoint(mx, my):
                    self.cook.on_click()
                    return

                # Клік по столу видачі страв на кухні
                if self.kitchen_pickup_rect.collidepoint(mx, my):
                    if self._on_counter_click(mx, my):
                        return

            elif self.target_room == "terrace":
                # Перехід до залу кафе (ліворуч)
                if self.terrace_to_hall_rect.collidepoint(mx, my) or self.arch_terrace_to_hall.collidepoint(mx, my):
                    self.switch_room("hall")
                    return

                # Клік по столиках тераси (5..8)
                for tbl in [t for t in self._tables if t.table_number in (5, 6, 7, 8)]:
                    if tbl.hitbox.collidepoint(mx, my):
                        self._on_table_click(tbl)
                        return

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _on_counter_click(self, mx: int, my: int) -> bool:
        """Гравець клікнув на барну стійку / зону видачі замовлень"""
        has_waiter = self.day_cfg.get("has_waiter", False)
        ready_tables = [t for t in self._tables if t.state == TableState.READY and not getattr(t, 'is_picked_up', False)]
        if has_waiter:
            # Ці страви офіціант уже несе сам
            ready_tables = [t for t in ready_tables if not self.waiter.is_table_busy(t)]

        # 1. Якщо є готові страви на стійці
        if ready_tables:
            if self.player_carrying_table is not None:
                tbl_num = self.player_carrying_table.table_number
                self.notifications.append(
                    Notification(f"У вас уже є страва! Віднесіть її до столика №{tbl_num}!", C.NOTIF_BAD, 2.0)
                )
                return True

            if has_waiter and self.waiter.carrying_item is not None:
                tbl_num = self.waiter.carrying_for_table.table_number if self.waiter.carrying_for_table else "?"
                self.notifications.append(
                    Notification(f"На таці вже є страва! Віднесіть її до столика №{tbl_num}!", C.NOTIF_BAD, 2.0)
                )
                self.waiter.say(f"Спочатку віднесу до столика №{tbl_num}! :3", duration=1.8)
                return True

            target_tbl = ready_tables[0]
            items = getattr(target_tbl, "order_items", [target_tbl.menu_item] if getattr(target_tbl, "menu_item", None) else [])
            food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
            if has_waiter:
                # Офіціант забирає готову страву (строго по одному завданню за раз)
                if self._waiter_is_busy_notice():
                    return True
                self._set_waiter_pickup_for(target_tbl)
                if self.waiter.enqueue_pickup_dish(target_tbl, target_tbl.menu_item):
                    self.notifications.append(
                        Notification(f"Офіціант забирає {food_names} для столика №{target_tbl.table_number}! :3", C.NOTIF_INFO, 1.4)
                    )
            else:
                # Гравець САМ забирає страву на руки
                target_tbl.is_picked_up = True
                self.player_carrying_table = target_tbl
                self.notifications.append(
                    Notification(f"Взяли {food_names}! Клікніть по столику №{target_tbl.table_number}, щоб подати!", C.NOTIF_GOOD, 2.2)
                )
            return True

        # 2. Якщо є замовлення, які очікують початку приготування баристою
        if self.pending_barista_orders:
            chef_order = self._order_is_chef(self.pending_barista_orders[0])
            if self._cook_busy(chef_order):
                self._cook_busy_notice(chef_order)
                return True
            next_tbl = self.pending_barista_orders.pop(0)
            self._start_order_cooking(next_tbl)
            items = getattr(next_tbl, "order_items", [next_tbl.menu_item] if getattr(next_tbl, "menu_item", None) else [])
            food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
            self.notifications.append(
                Notification(f"Бариста варить: {food_names} для столика №{next_tbl.table_number}!", C.NOTIF_INFO, 1.8)
            )
            self.barista.say(f"Готую {food_names}! :3", duration=2.0)
            return True

        # 3. Якщо страва ще готується
        cooking_tables = [t for t in self._tables if t.state == TableState.ORDERED]
        if cooking_tables:
            self.barista.say("Замовлення ще готується! Зачекайте хвилинку :3", duration=2.0)
            self.notifications.append(
                Notification("Бариста ще готує замовлення на кухні!", C.NOTIF_INFO, 1.4)
            )
            return True

        # Інакше — звичайний інтерактивний діалог з баристою
        return self.barista.handle_click(mx, my)

    # ------------------------------------------------------------------
    def _waiter_is_busy_notice(self) -> bool:
        """Офіціант виконує завдання строго по черзі: якщо зайнятий — кажемо про це і нічого не додаємо"""
        w = self.waiter
        if not (w.is_busy() or w.carrying_item is not None):
            return False
        w.say("Я зайнятий іншим замовленням! :3", duration=1.8)
        self.notifications.append(
            Notification("Офіціант зайнятий іншим замовленням! Зачекайте, поки він закінчить.", C.NOTIF_INFO, 1.8)
        )
        return True

    def _on_table_click(self, tbl: CafeTable):
        """Гравець клікнув по столику"""
        if tbl.state == TableState.EMPTY or tbl.customer is None:
            return

        cust = tbl.customer
        has_waiter = self.day_cfg.get("has_waiter", False)

        # 1. Гравець несе страву на руках -> вручну подаємо гостю!
        if self.player_carrying_table is not None:
            if self.player_carrying_table == tbl:
                self._on_player_served_order(tbl)
                self.player_carrying_table = None
            else:
                correct_num = self.player_carrying_table.table_number
                self.notifications.append(
                    Notification(f"Це страва для столика №{correct_num}! Віднесіть туди :3", C.NOTIF_BAD, 2.0)
                )
            return

        # 2. Якщо офіціант несе страву на таці -> подаємо гостю!
        if has_waiter and self.waiter.carrying_item is not None:
            if self.waiter.carrying_for_table == tbl:
                tbl.is_queued_waiter = True
                if self.waiter.enqueue_serve_dish(tbl):
                    self.notifications.append(
                        Notification(f"Офіціант подає замовлення столику №{tbl.table_number}! ^^", C.NOTIF_GOOD, 1.4)
                    )
            else:
                correct_num = self.waiter.carrying_for_table.table_number if self.waiter.carrying_for_table else "?"
                self.notifications.append(
                    Notification(f"Це замовлення для столика №{correct_num}! Віднесіть туди.", C.NOTIF_BAD, 2.0)
                )
                self.waiter.say(f"Це для столика №{correct_num}! :3", duration=1.8)
            return

        # 3. Клієнт очікує замовлення (WAITING)
        if cust.state == CustomerState.WAITING:
            if has_waiter:
                if tbl.is_queued_waiter:
                    self.notifications.append(
                        Notification(f"Столик №{tbl.table_number} вже в черзі офіціанта!", C.NOTIF_INFO, 1.2)
                    )
                    return
                if self._waiter_is_busy_notice():
                    return
                if self.waiter.enqueue_take_order(tbl):
                    tbl.is_queued_waiter = True
                    self.notifications.append(
                        Notification(f"Офіціант іде приймати замовлення у столика №{tbl.table_number}! :3", C.NOTIF_INFO, 1.4)
                    )
            else:
                # Гравець САМ приймає замовлення кліком
                if tbl not in self.pending_barista_orders and tbl.state != TableState.ORDERED:
                    self.pending_barista_orders.append(tbl)
                    cust.state = CustomerState.ORDER_TAKEN
                    cust.patience = min(float(self.day_cfg["patience"]), cust.patience + 15.0)
                    items = getattr(cust, "menu_items", [cust.menu_item] if getattr(cust, "menu_item", None) else [])
                    food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
                    self.notifications.append(
                        Notification(f"Замовлення столика №{tbl.table_number} прийнято ({food_names})! Клікніть на баристу!", C.NOTIF_INFO, 2.4)
                    )
                    self.barista.say("Клікніть на мене, я зварю! :3", duration=2.5)
            return

        # Страва готова: якщо є офіціант — гравець посилає його до цього столика
        if tbl.state == TableState.READY and not getattr(tbl, 'is_picked_up', False) and has_waiter:
            if tbl.is_queued_waiter or self.waiter.is_table_busy(tbl):
                return
            if self._waiter_is_busy_notice():
                return
            self._set_waiter_pickup_for(tbl)
            tbl.is_queued_waiter = True
            items = getattr(tbl, "order_items", [tbl.menu_item] if getattr(tbl, "menu_item", None) else [])
            if self.waiter.enqueue_serve_order(tbl, items[0] if items else None):
                food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
                self.notifications.append(
                    Notification(f"Офіціант несе {food_names} до столика №{tbl.table_number}! :3", C.NOTIF_INFO, 1.6)
                )
            else:
                tbl.is_queued_waiter = False
            return

        # Страва вже готова на стійці, але гравець клікнув столик замість стійки
        if tbl.state == TableState.READY and not getattr(tbl, 'is_picked_up', False):
            self.notifications.append(
                Notification("Страва готова на стійці! Клікніть на стійку баристи, щоб забрати!", C.NOTIF_INFO, 2.0)
            )
            self.barista.say(f"Замовлення столика №{tbl.table_number} на стійці! :3", duration=1.8)
            return

        # Замовлення зараз готується
        if tbl.state == TableState.ORDERED:
            cook_prog = int((1.0 - tbl.cook_timer / max(0.1, tbl.cook_total)) * 100)
            self.notifications.append(
                Notification(f"Замовлення столика №{tbl.table_number} готується... ({cook_prog}%)", C.NOTIF_INFO, 1.2)
            )
            return

        # Клієнт щойно сів
        if cust.state == CustomerState.SEATED:
            self.notifications.append(
                Notification("Котик ще обирає страву з меню...", C.NOTIF_INFO, 1.2)
            )
            return

        # Клієнт їсть
        if cust.state == CustomerState.EATING:
            self.notifications.append(
                Notification("Котик смакує замовлення! *ням-ням*", C.NOTIF_INFO, 1.2)
            )
            return

    # ------------------------------------------------------------------
    def _start_order_cooking(self, tbl: CafeTable):
        """Бариста починає готувати страву для вказаного столика"""
        cust = tbl.customer
        if cust is None:
            return

        items = getattr(cust, "menu_items", [cust.menu_item] if getattr(cust, "menu_item", None) else [])
        if not items:
            items = [{"id": 1, "price": 50, "cookingtimemin": 4}]

        # Сумарний час готування для всіх замовлених страв
        # Шеф-кухар пришвидшує лише свої страви; напої завжди готує бариста у звичайному темпі
        has_chef = self.upgrades.get("chef", False)
        total_cook = sum(
            max(2.0, min(5.0, it.get("cookingtimemin", 4) * 0.5))
            * (self.day_cfg["cook_speed_mult"] if has_chef and it.get("id") in CHEF_ITEM_IDS else 1.0)
            for it in items)

        emp = self._employees[0] if self._employees else {"id": 1}
        order_id = queries.create_order(tbl.db_id, emp["id"])
        if order_id:
            for it in items:
                queries.add_order_item(order_id, it.get("id", 1), 1, it.get("price", 50))

        tbl.order_items = items
        tbl.start_order(order_id, items[0], total_cook)
        cust.state = CustomerState.ORDER_TAKEN
        cust.patience = min(float(self.day_cfg["patience"]), cust.patience + 14.0)

        food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
        if self._is_chef_dish(items):
            self.cook.say(f"Готую {food_names}! :3", duration=2.0)
        else:
            self.barista.on_order_taken(food_names)

    def _on_player_served_order(self, tbl: CafeTable):
        """Гравець власноруч приніс і подав замовлення гостю"""
        tbl.is_picked_up = False
        cust = tbl.customer
        if cust is None:
            return

        tip_mult = self.day_cfg["tip_mult"]
        if self.upgrades.get("vip_armchair", False) and tbl.table_number == 5:
            tip_mult *= 1.30

        earned = int(cust.earned_coins * tip_mult)
        self.money += earned
        self.orders_done += 1
        self.rating = min(5.0, self.rating + 0.1)

        if tbl.order_id:
            queries.complete_order(tbl.order_id)

        cust.start_eating()
        tbl.state = TableState.PAYING

        msg = locale.get("notify.order_done", coins=earned)
        self.notifications.append(Notification(msg, C.NOTIF_GOOD, 2.5))
        self.barista.on_order_served(earned)

    # ------------------------------------------------------------------
    # Коллбеки роботи офіціанта
    # ------------------------------------------------------------------
    def _on_waiter_took_order(self, tbl: CafeTable):
        """Офіціант приніс бланк замовлення на барну стійку"""
        tbl.is_queued_waiter = False
        cust = tbl.customer
        if cust is None or cust.state != CustomerState.WAITING:
            return
        tbl.waiter_order = True   # цей заказ прийняв офіціант — сам же віднесе готову страву
        chef_order = self._order_is_chef(tbl)
        if self._cook_busy(chef_order):
            # Готувальник зайнятий — замовлення чекає в черзі та стартує автоматично
            cust.state = CustomerState.ORDER_TAKEN
            if tbl not in self.pending_barista_orders:
                self.pending_barista_orders.append(tbl)
            self._cook_busy_notice(chef_order)
            return
        self._start_order_cooking(tbl)
        self.notifications.append(
            Notification(locale.get("action.take_order"), C.NOTIF_INFO, 1.4)
        )

    def _on_waiter_served_order(self, tbl: CafeTable):
        """Офіціант приніс замовлення до столика"""
        tbl.is_queued_waiter = False
        self._on_player_served_order(tbl)

    def _on_dish_ready(self, tbl: CafeTable):
        """Анімація завершення готування страви — Дінь! та іскри на стійці"""
        if self._is_chef_table(tbl):
            self.cook.on_dish_ready()
        else:
            self.ready_pop_anim = 1.0
            # Феєрверк золотистих зірочок на стійці роздачі та дзвоник баристи
            for _ in range(16):
                self.star_particles.append(StarParticle(795, 520))
            self.barista.say("Дінь! Замовлення готове! :3", duration=2.4)
        items = getattr(tbl, "order_items", [tbl.menu_item] if getattr(tbl, "menu_item", None) else [])
        food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
        self.notifications.append(
            Notification(f"Готово: {food_names} для столика №{tbl.table_number}! Заберіть на кухні!" if self._is_chef_table(tbl) else f"Готово: {food_names} для столика №{tbl.table_number}! Заберіть на стійці!", C.NOTIF_GOOD, 2.5)
        )

    def _try_spawn_customer(self):
        """Садить нового гостя за вільний столик (якщо є місце та не перевищено ліміт)"""
        if len(self.customers) >= self.day_cfg["max_customers"]:
            return

        allowed = self.day_cfg["allowed_tables"]
        free = [t for t in self._tables
                if t.table_number in allowed
                and t.state == TableState.EMPTY
                and t.customer is None]
        if not free:
            return

        pool = [m for m in self._menu_items if m.get("id") in self.day_cfg["allowed_items"]]
        if not pool:
            pool = list(self._menu_items)
        if not pool:
            return

        tbl = random.choice(free)
        if len(pool) > 1 and random.random() < self.day_cfg["two_items_chance"]:
            order_items = random.sample(pool, 2)
        else:
            order_items = [random.choice(pool)]

        cust = Customer(tbl, order_items[0], None, None,
                        max_patience=float(self.day_cfg["patience"]),
                        order_items=order_items)
        tbl.customer = cust
        tbl.waiter_order = False
        self.customers.append(cust)

        # Гість сів у кімнаті, яку гравець зараз не бачить — повідомляємо
        guest_room = "terrace" if tbl.table_number in (5, 6, 7, 8) else "hall"
        if guest_room != self.target_room:
            where = "На терасі новий гість" if guest_room == "terrace" else "У залі новий гість"
            self.notifications.append(
                Notification(f"{where} — столик №{tbl.table_number}!", C.NOTIF_INFO, 2.4)
            )

    def _auto_serve_waiter_orders(self):
        """Замовлення, яке прийняв офіціант: щойно воно готове — він сам забирає страву і несе до столика"""
        w = self.waiter
        if w.is_busy() or w.carrying_item is not None or self.player_carrying_table is not None:
            return
        for tbl in self._tables:
            if tbl.state != TableState.READY or getattr(tbl, "is_picked_up", False):
                continue
            if not getattr(tbl, "waiter_order", False):
                continue
            cust = tbl.customer
            if cust is None or cust.state in (CustomerState.LEAVING, CustomerState.GONE):
                continue
            items = getattr(tbl, "order_items", [tbl.menu_item] if getattr(tbl, "menu_item", None) else [])
            self._set_waiter_pickup_for(tbl)
            tbl.is_queued_waiter = True
            if w.enqueue_serve_order(tbl, items[0] if items else None):
                food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)
                self.notifications.append(
                    Notification(f"Офіціант несе {food_names} до столика №{tbl.table_number}! :3", C.NOTIF_INFO, 1.6)
                )
            else:
                tbl.is_queued_waiter = False
            return

    def _start_queued_orders(self):
        """Коли бариста/кухар звільнилися — беруть наступне замовлення з черги"""
        for tbl in list(self.pending_barista_orders):
            cust = tbl.customer
            if cust is None or cust.state in (CustomerState.LEAVING, CustomerState.GONE):
                self.pending_barista_orders.remove(tbl)
                continue
            if self._cook_busy(self._order_is_chef(tbl)):
                continue
            self.pending_barista_orders.remove(tbl)
            self._start_order_cooking(tbl)
            return

    def _is_chef_dish(self, items) -> bool:
        """Страву готує кухар (а не бариста), якщо кухар найнятий"""
        if not self.upgrades.get("chef", False):
            return False
        return any(it.get("id") in CHEF_ITEM_IDS for it in items)

    def _order_is_chef(self, tbl) -> bool:
        """Чи готуватиме це замовлення кухар (до початку готування страви беремо з гостя)"""
        items = getattr(tbl, "order_items", None)
        if not items and tbl.customer is not None:
            items = getattr(tbl.customer, "menu_items", [])
        return self._is_chef_dish(items or [])

    def _cook_busy(self, chef: bool) -> bool:
        """Бариста та кухар готують строго по одному замовленню за раз"""
        busy = sum(1 for t in self._tables if t.state == TableState.ORDERED and self._is_chef_table(t) == chef)
        return busy >= (3 if chef else 1)

    def _cook_busy_notice(self, chef: bool):
        if chef:
            self.cook.say("Руки зайняті — вже готую 3 страви! :3", duration=2.0)
            text = "Шеф-кухар вже готує 3 страви! Зачекайте."
        else:
            self.barista.say("Я зайнята іншим замовленням! :3", duration=1.8)
            text = "Бариста зайнята іншим замовленням! Зачекайте, поки вона закінчить."
        self.notifications.append(Notification(text, C.NOTIF_INFO, 1.8))

    def _is_chef_table(self, tbl) -> bool:
        items = getattr(tbl, "order_items", [tbl.menu_item] if getattr(tbl, "menu_item", None) else [])
        return self._is_chef_dish(items)

    def _set_waiter_pickup_for(self, tbl):
        """Куди офіціант іде за готовою стравою: на кухню (страви кухаря) або до стійки баристи"""
        w = self.waiter
        if self._is_chef_table(tbl):
            w.pickup_x, w.pickup_y, w.pickup_room = KITCHEN_PICKUP[0], KITCHEN_PICKUP[1], "kitchen"
        else:
            w.pickup_x, w.pickup_y, w.pickup_room = HALL_PICKUP[0], HALL_PICKUP[1], "hall"

    def _reset_waiter_pickup(self):
        """Поки офіціант вільний, точка видачі — стійка в залі (сюди ж він несе бланки замовлень)"""
        w = self.waiter
        if not w.is_busy() and w.carrying_item is None:
            w.pickup_x, w.pickup_y, w.pickup_room = HALL_PICKUP[0], HALL_PICKUP[1], "hall"

    def _should_draw_waiter_in(self, room: str) -> bool:
        """Офіціант малюється в тій кімнаті, де він зараз реально знаходиться"""
        if not self.day_cfg.get("has_waiter", False):
            return False
        return room == self.waiter.room

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._t += dt

        # Якщо відкритий магазин — пауза часу дня, щоб гравець міг спокійно обирати
        if self.shop_modal.is_open:
            return

        # Плавне панорамування камери ("поле видимості") між кімнатами
        diff = self.target_camera_x - self.camera_x
        if abs(diff) > 1.0:
            self.camera_x += diff * min(1.0, dt * 9.0)
        else:
            self.camera_x = self.target_camera_x
            self.current_room = self.target_room

        self.time_left = max(0.0, self.time_left - dt)

        # Анімація появи страви
        if self.ready_pop_anim > 0:
            self.ready_pop_anim = max(0.0, self.ready_pop_anim - dt * 1.5)

        # Оновлення зірочок
        self.star_particles = [p for p in self.star_particles if p.update(dt)]

        # Оновлення котика-кухаря на кухні
        chef_cooking = [t for t in self._tables if t.state == TableState.ORDERED and self._is_chef_table(t)]
        chef_dish_ids = []
        for t in chef_cooking:
            for it in getattr(t, "order_items", []):
                if it.get("id") in CHEF_ITEM_IDS:
                    chef_dish_ids.append(it["id"])
        chef_ready = []
        for t in self._tables:
            if t.state == TableState.READY and not getattr(t, "is_picked_up", False) and self._is_chef_table(t):
                names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}")
                                   for it in getattr(t, "order_items", []))
                chef_ready.append((t.table_number, names))
        self.cook.update(dt, is_cooking=bool(chef_cooking), dishes=chef_dish_ids, ready=chef_ready,
                         has_waiter=self.day_cfg.get("has_waiter", False))

        # Спавн клієнтів
        self._spawn_timer -= dt
        if self._spawn_timer <= 0 and self.time_left > 18:
            self._try_spawn_customer()
            self._spawn_timer = self._spawn_interval * random.uniform(0.75, 1.25)

        # Оновлюємо офіціанта тільки якщо він найнятий у магазині
        if self.day_cfg.get("has_waiter", False):
            if not self.waiter.is_busy():
                self.waiter.home_x = 680.0
                self.waiter.home_y = 550.0
                self.waiter.home_room = "hall"
            self._reset_waiter_pickup()
            self._auto_serve_waiter_orders()
            self.waiter.update(dt)
            self._start_queued_orders()

        # Оновлюємо баристу
        self.barista.update(dt, [t for t in self._tables if not self._is_chef_table(t)], self.customers)

        # Оновлюємо столики та відстежуємо завершення приготування
        for tbl in self._tables:
            old_st = tbl.state
            tbl.update(dt)
            if old_st == TableState.ORDERED and tbl.state == TableState.READY:
                self._on_dish_ready(tbl)

        # Оновлюємо клієнтів
        for cust in self.customers:
            cust.update(dt)
            if cust.state == CustomerState.GONE and not cust.satisfied:
                self.orders_bad += 1
                self.rating = max(1.0, self.rating - 0.2)
                msg = locale.get("notify.customer_left")
                self.notifications.append(Notification(msg, C.NOTIF_BAD, 2.0))

        self.customers = [c for c in self.customers if c.state != CustomerState.GONE]

        for n in self.notifications:
            n.update(dt)
        self.notifications = [n for n in self.notifications if n.alive][-2:]

        # Жорстке правило: менше 3 зірок або понад 5 скасованих замовлень — кафе закривається
        fail_reason = ""
        if round(self.rating) < 3:
            fail_reason = "game_over.fail_rating"
        elif self.orders_bad > 5:
            fail_reason = "game_over.fail_orders"
        if fail_reason:
            self.manager.switch("game_over",
                                day=self.day,
                                money=self.money,
                                rating=self.rating,
                                orders_done=self.orders_done,
                                orders_bad=self.orders_bad,
                                upgrades=self.upgrades,
                                failed=True,
                                fail_reason=fail_reason)
            return

        # Кінець дня
        if self.time_left <= 0:
            self.manager.switch("game_over",
                                day=self.day,
                                money=self.money,
                                rating=self.rating,
                                orders_done=self.orders_done,
                                orders_bad=self.orders_bad,
                                upgrades=self.upgrades)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        has_terrace = self.day_cfg.get("has_terrace", False)

        # 1. Перевірка потреби в обслуговуванні для кожної кімнати (для червоних індикаторів (!) в HUD)
        hall_tables = [t for t in self._tables if t.table_number in HALL_TABLES]
        terrace_tables = [t for t in self._tables if t.table_number in (5, 6, 7, 8)]
        cooking_tables = [t for t in self._tables if t.state == TableState.ORDERED]
        ready_tables = [t for t in self._tables if t.state == TableState.READY and not getattr(t, 'is_picked_up', False)]

        has_kitchen = self.upgrades.get("chef", False)
        kitchen_alert = has_kitchen and any(
            self._is_chef_table(t) for t in cooking_tables + ready_tables)
        hall_alert = any(t.state == TableState.READY or (t.customer and t.customer.state == CustomerState.WAITING and t.customer.patience < 20) for t in hall_tables)
        terrace_alert = has_terrace and any(t.state == TableState.READY or (t.customer and t.customer.state == CustomerState.WAITING and t.customer.patience < 20) for t in terrace_tables)

        # 2. Рендеримо кімнати відповідно до поля видимості камери
        # Безшовне панорамування: Кухня (-1280), Зал (0), Тераса (+1280)
        rooms_to_render = [
            ("kitchen", self._bg_kitchen_surf, ROOM_OFFSETS["kitchen"]),
            ("hall",    self._bg_surf,         ROOM_OFFSETS["hall"]),
            ("terrace", self._bg_terrace_surf, ROOM_OFFSETS["terrace"]),
        ]

        for room_name, bg_surf, room_base_x in rooms_to_render:
            dx = int(room_base_x - self.camera_x)
            # Якщо кімната повністю поза екраном, пропускаємо
            if dx <= -WIDTH or dx >= WIDTH:
                continue

            # 2.1 Фон навколо кімнати та сама кімната
            self._draw_backdrop(surface, room_name, dx)
            if bg_surf:
                surface.blit(bg_surf, (dx, 0))

            # 2.2 Вміст відповідної кімнати
            if room_name == "kitchen":
                self._draw_kitchen_room(surface, offset_x=dx)
                if self._should_draw_waiter_in("kitchen"):
                    self.waiter.draw(surface, offset_x=dx)

            elif room_name == "hall":
                # Стіни та декор
                self._draw_walls(surface, offset_x=dx)
                # Вивіски переходів
                self._draw_hall_passages(surface, offset_x=dx)
                # Бариста
                self.barista.draw(surface, offset_x=dx)
                # Зона готування та видачі
                self._draw_cooking_station(surface, offset_x=dx)
                self._draw_counter_pickup_station(surface, offset_x=dx)

                # Сортування по глибині (Y): столики залу 1..4, клієнти, офіціант
                draw_list = []
                for tbl in hall_tables:
                    draw_list.append((tbl.screen_y, lambda s, t=tbl: t.draw(s, offset_x=dx)))

                for cust in self.customers:
                    cust_tbl_num = getattr(cust.table, "table_number", 1)
                    if cust_tbl_num in HALL_TABLES:
                        draw_list.append((cust.y + 1, lambda s, c=cust: c.draw(s, offset_x=dx)))

                if self._should_draw_waiter_in("hall"):
                    draw_list.append((self.waiter.y, lambda s: self.waiter.draw(s, offset_x=dx)))

                draw_list.sort(key=lambda item: item[0])
                for _, draw_fn in draw_list:
                    draw_fn(surface)

                # Зірочки та частинки "Дінь!" над стійкою
                for p in self.star_particles:
                    p.draw(surface, offset_x=dx)

            elif room_name == "terrace":
                self._draw_terrace_room(surface, offset_x=dx)

                draw_list = []
                for tbl in terrace_tables:
                    draw_list.append((tbl.screen_y, lambda s, t=tbl: t.draw(s, offset_x=dx)))

                for cust in self.customers:
                    cust_tbl_num = getattr(cust.table, "table_number", 1)
                    if cust_tbl_num in (5, 6, 7, 8):
                        draw_list.append((cust.y + 1, lambda s, c=cust: c.draw(s, offset_x=dx)))

                if self._should_draw_waiter_in("terrace"):
                    draw_list.append((self.waiter.y, lambda s: self.waiter.draw(s, offset_x=dx)))

                draw_list.sort(key=lambda item: item[0])
                for _, draw_fn in draw_list:
                    draw_fn(surface)

        # 3. HUD (завжди зверху, фіксований на екрані)
        self.hud.draw(surface,
                      money=self.money,
                      day=self.day,
                      time_left=self.time_left,
                      day_duration=DAY_DURATION,
                      rating=self.rating,
                      orders_done=self.orders_done,
                      current_room=self.target_room,
                      has_terrace=has_terrace,
                      kitchen_alert=kitchen_alert,
                      hall_alert=hall_alert,
                      terrace_alert=terrace_alert,
                      has_kitchen=has_kitchen)

        # 4. Підказка щодо поточної страви на таці офіціанта або в руках гравця
        if not self.shop_modal.is_open:
            has_waiter = self.day_cfg.get("has_waiter", False)
            is_carrying = False
            if has_waiter and self.waiter.carrying_item and self.waiter.carrying_for_table:
                self._draw_carrying_guide(surface, self.waiter.carrying_for_table, self.waiter.carrying_item)
                is_carrying = True
            elif self.player_carrying_table and self.player_carrying_table.menu_item:
                self._draw_carrying_guide(surface, self.player_carrying_table, self.player_carrying_table.menu_item)
                is_carrying = True

            # 4.1 Сповіщення (максимум 2 останніх, не перекривають планку підказки)
            base_y = 104 if is_carrying else 68
            for i, notif in enumerate(self.notifications[-2:]):
                notif.draw(surface, WIDTH // 2, base_y + i * 32)

        # 5. Підказка керування ESC
        f = assets.font_ui(12, bold=True)
        esc_t = assets.render_outlined(f, "ESC — меню | [1] Кухня  [2] Зал  [3] Тераса", C.SAGE_GRAY, (40, 35, 30), 1)
        surface.blit(esc_t, (WIDTH - 305, HEIGHT - 20))

        # 6. Модальне вікно магазину (якщо відкрите)
        if self.shop_modal.is_open:
            self.shop_modal.draw(surface, self.money, self.upgrades)

    # ------------------------------------------------------------------
    def _draw_hall_passages(self, surface: pygame.Surface, offset_x: int = 0):
        """Акуратні дерев'яні вивіски переходів: ліворуч — до кухні, праворуч — на терасу"""
        has_terrace = self.day_cfg.get("has_terrace", False)
        mouse_pos = pygame.mouse.get_pos()
        f = assets.font_ui(13, bold=True)

        # 1. Перехід до кухні (ліворуч)
        hover_k = (self.current_room == "hall" and self.hall_to_kitchen_rect.collidepoint(mouse_pos))
        bw, bh = 180, 46
        bx_k = 15 + offset_x
        by = 390

        board_k = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg_col_k = (*C.TERRACOTTA, 235 if hover_k else 195)
        pygame.draw.rect(board_k, bg_col_k, (0, 0, bw, bh), border_radius=12)
        pygame.draw.rect(board_k, C.WHITE, (0, 0, bw, bh), 2 if hover_k else 1, border_radius=12)
        if self.upgrades.get("chef", False):
            txt_k = assets.render_outlined(f, "<< До кухні", C.WHITE, (40, 35, 30), 1)
        else:
            board_k.fill((0, 0, 0, 0))
            pygame.draw.rect(board_k, (110, 115, 100, 235 if hover_k else 195), (0, 0, bw, bh), border_radius=12)
            pygame.draw.rect(board_k, C.DARK_SAGE, (0, 0, bw, bh), 1, border_radius=12)
            txt_k = assets.render_outlined(assets.font_ui(12, bold=True), "Кухня: кухар 160 [!]", (245, 240, 230), (40, 35, 30), 1)
        board_k.blit(txt_k, txt_k.get_rect(center=(bw // 2, bh // 2)))
        surface.blit(board_k, (bx_k, by))

        # 2. Перехід на літню терасу (праворуч)
        hover_t = (self.current_room == "hall" and self.hall_to_terrace_rect.collidepoint(mouse_pos))
        bx_t = WIDTH - 195 + offset_x

        board_t = pygame.Surface((bw, bh), pygame.SRCALPHA)
        if has_terrace:
            bg_col_t = (*C.TERRACOTTA, 235 if hover_t else 195)
            pygame.draw.rect(board_t, bg_col_t, (0, 0, bw, bh), border_radius=12)
            pygame.draw.rect(board_t, C.WHITE, (0, 0, bw, bh), 2 if hover_t else 1, border_radius=12)
            txt_t = assets.render_outlined(f, "На літню терасу >>", C.WHITE, (40, 35, 30), 1)
            board_t.blit(txt_t, txt_t.get_rect(center=(bw // 2, bh // 2)))
        else:
            bg_col_t = (110, 115, 100, 235 if hover_t else 195)
            pygame.draw.rect(board_t, bg_col_t, (0, 0, bw, bh), border_radius=12)
            pygame.draw.rect(board_t, C.DARK_SAGE, (0, 0, bw, bh), 1, border_radius=12)
            f_sm = assets.font_ui(12, bold=True)
            txt_t = assets.render_outlined(f_sm, "Тераса: 150 монет [!]", (245, 240, 230), (40, 35, 30), 1)
            board_t.blit(txt_t, txt_t.get_rect(center=(bw // 2, bh // 2)))

        surface.blit(board_t, (bx_t, by))

    def _draw_terrace_room(self, surface: pygame.Surface, offset_x: int = 0):
        """Отрисовка декору тераси точно за макетом користувача з підтримкою панорамування"""
        from game.core.settings import s_scale, ROOM_SIZE, ROOM_X, ROOM_Y

        def t_to_screen(tx, ty):
            scale = ROOM_SIZE / 2048.0
            return int(ROOM_X + offset_x + tx * scale), int(ROOM_Y + ty * scale)

        # 1. Поличка на лівій стіні
        shelves = assets.image_by_height("decor_shelves", s_scale(240))
        surface.blit(shelves, shelves.get_rect(center=t_to_screen(380, 960)))

        # 2. Картина з лапкою на стіні
        paw_pic = assets.image_by_height("decor_picture_paw", s_scale(190))
        surface.blit(paw_pic, paw_pic.get_rect(center=t_to_screen(550, 780)))

        # 3. Велика рослина ліворуч від арки
        p1 = assets.image_by_height("decor_plant_big", s_scale(280))
        surface.blit(p1, p1.get_rect(midbottom=t_to_screen(600, 1140)))

        # 4. Велика рослина праворуч від арки
        p2 = assets.image_by_height("decor_plant_big", s_scale(280))
        surface.blit(p2, p2.get_rect(midbottom=t_to_screen(940, 970)))

        # 5. Дверна арка повернення до залу (клікабельна кнопка над аркою)
        mouse_pos = pygame.mouse.get_pos()
        door_hover = (self.current_room == "terrace" and (self.terrace_to_hall_rect.collidepoint(mouse_pos) or self.arch_terrace_to_hall.collidepoint(mouse_pos)))
        f_door = assets.font_ui(12, bold=True)
        txt = assets.render_outlined(f_door, "<< До залу кафе", C.WHITE, (40, 35, 30), 1)
        bw, bh = txt.get_width() + 20, 26
        bx, by = int(495 + offset_x - bw // 2), 210
        btn_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(btn_s, (*C.TERRACOTTA, 235 if door_hover else 190), (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(btn_s, C.WHITE, (0, 0, bw, bh), 2 if door_hover else 1, border_radius=8)
        btn_s.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
        surface.blit(btn_s, (bx, by))

        # 6. Бічна кнопка повернення до залу ліворуч
        side_hover = (self.current_room == "terrace" and self.terrace_to_hall_rect.collidepoint(mouse_pos))
        side_bw, side_bh = 180, 46
        side_bx = 15 + offset_x
        side_by = 390
        side_s = pygame.Surface((side_bw, side_bh), pygame.SRCALPHA)
        pygame.draw.rect(side_s, (*C.TERRACOTTA, 235 if side_hover else 195), (0, 0, side_bw, side_bh), border_radius=12)
        pygame.draw.rect(side_s, C.WHITE, (0, 0, side_bw, side_bh), 2 if side_hover else 1, border_radius=12)
        f_side = assets.font_ui(13, bold=True)
        txt_s = assets.render_outlined(f_side, "<< До залу кафе", C.WHITE, (40, 35, 30), 1)
        side_s.blit(txt_s, txt_s.get_rect(center=(side_bw // 2, side_bh // 2)))
        surface.blit(side_s, (side_bx, side_by))

    def _draw_kitchen_room(self, surface: pygame.Surface, offset_x: int = 0):
        """Повноцінна інтерактивна затишна кухня з котиком-кухарем, плитою, духовкою, холодильником та роздачею"""
        from game.core.settings import s_scale, ROOM_SIZE, ROOM_X, ROOM_Y

        def k_to_screen(kx, ky):
            scale = ROOM_SIZE / 2048.0
            return int(ROOM_X + offset_x + kx * scale), int(ROOM_Y + ky * scale)

        mouse_pos = pygame.mouse.get_pos()

        cooking_tables = [t for t in self._tables if t.state == TableState.ORDERED and self._is_chef_table(t)]

        def put(name, cx, bottom, h, flip=False):
            """Ставить спрайт по центру X та нижній межі (екранні координати кімнати кухні)"""
            spr = assets.image_by_height(name, h)
            if flip:
                spr = pygame.transform.flip(spr, True, False)
            rect = spr.get_rect(midbottom=(cx + offset_x, bottom))
            surface.blit(spr, rect)
            return rect

        # Розстановка точно за макетом кухні (задня стіна ліворуч -> праворуч)
        # 1. Полички зі спеціями та посудом на стінах (в одному спрайті — дві)
        put("furniture_wall_shelf", 642, 297, 108)

        # 2. Підвісний кухонний реманент над плитою
        put("decor_hanging_utensils", 538, 350, 43)

        # 3. Холодильник у куті
        put("furniture_fridge", 645, 418, 126, flip=True)

        # 4. Плита з каструлею
        stove_rect = put("furniture_stove", 594, 448, 111, flip=True)

        # 5. Духова шафа
        put("furniture_oven", 515, 478, 113, flip=True)

        # 6. Обробний стіл шефа з дошкою
        put("furniture_prep_table", 455, 515, 111, flip=True)

        # 7. Анімація пари над плитою, якщо зараз готується страва
        if cooking_tables:
            for i in range(4):
                st_phase = (self._t * 2.2 + i * 0.5) % 2.0
                st_y = stove_rect.top + 8 - st_phase * 34
                st_x = stove_rect.centerx + math.sin(st_phase * 4.0 + i) * 8
                st_alpha = int((1.0 - (st_phase / 2.0)) * 200)
                st_r = int(3 + st_phase * 5)
                if st_r > 0 and st_alpha > 0:
                    st_surf = pygame.Surface((st_r * 2, st_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(st_surf, (250, 250, 255, st_alpha), (st_r, st_r), st_r)
                    surface.blit(st_surf, (int(st_x - st_r), int(st_y - st_r)))

        # 8. Стіл видачі готових страв (виставляється нижче, у п.10)
        pickup_pos = (610 + offset_x, 575)

        # 9. Котик-кухар Мурчик (шеф) та мийка справа
        put("furniture_sink", 882, 562, 130)

        self.cook.height = 107
        self.cook.draw(surface, offset_x=offset_x)

        # 10. Стіл видачі готових страв на кухні (біля арочного проходу до залу кафе)
        tw, th = 85, 42
        pygame.draw.ellipse(surface, (145, 95, 60), (pickup_pos[0] - tw // 2, pickup_pos[1] - th // 2, tw, th))
        pygame.draw.ellipse(surface, (190, 140, 95), (pickup_pos[0] - tw // 2 + 2, pickup_pos[1] - th // 2 + 2, tw - 4, th - 4))

        # Вивіска над столиком видачі
        f_pic = assets.font_ui(11, bold=True)
        t_pic = assets.render_outlined(f_pic, "Роздача кухні", C.WHITE, (40, 35, 30), 1)
        surface.blit(t_pic, t_pic.get_rect(center=(pickup_pos[0], pickup_pos[1] + 28)))

        # Якщо є готова страва — підсвічуємо столик роздачі та малюємо страву
        ready_tables = [t for t in self._tables if t.state == TableState.READY and not getattr(t, 'is_picked_up', False) and self._is_chef_table(t)]
        if ready_tables:
            top_tbl = ready_tables[0]
            pulse = (math.sin(self._t * 5.0) + 1.0) * 0.5
            glow_r = int(26 + pulse * 6)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 220, 110, int(70 + pulse * 50)), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (pickup_pos[0] - glow_r, pickup_pos[1] - glow_r))

            bob = int(math.sin(self._t * 6.0) * 2)
            items = getattr(top_tbl, "order_items", [top_tbl.menu_item] if getattr(top_tbl, "menu_item", None) else [])
            if len(items) > 1:
                spr1 = get_item_sprite(items[0].get("id", 1))
                spr2 = get_item_sprite(items[1].get("id", 1))
                img1 = assets.image_by_height(spr1, 22)
                img2 = assets.image_by_height(spr2, 22)
                surface.blit(img1, img1.get_rect(center=(pickup_pos[0] - 10, pickup_pos[1] - 8 + bob)))
                surface.blit(img2, img2.get_rect(center=(pickup_pos[0] + 10, pickup_pos[1] - 8 + bob)))
            else:
                item_id = items[0].get("id", 1) if items else 1
                dish_img = assets.image_by_height(get_item_sprite(item_id), 28)
                surface.blit(dish_img, dish_img.get_rect(center=(pickup_pos[0], pickup_pos[1] - 8 + bob)))

            badge_text = f"№{top_tbl.table_number} Забрати!"
            f = assets.font_ui(12)
            txt = f.render(badge_text, True, C.TEXT_DARK)
            bw = txt.get_width() + 16
            bh = 22
            badge = pygame.Surface((bw, bh + 5), pygame.SRCALPHA)
            pygame.draw.rect(badge, (255, 250, 230), (0, 0, bw, bh), border_radius=7)
            pygame.draw.rect(badge, (230, 150, 40), (0, 0, bw, bh), 2, border_radius=7)
            tail_pts = [(bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 4)]
            pygame.draw.polygon(badge, (255, 250, 230), tail_pts)
            pygame.draw.polygon(badge, (230, 150, 40), tail_pts, 1)
            badge.blit(txt, (8, 3))
            surface.blit(badge, (pickup_pos[0] - bw // 2, pickup_pos[1] - 44))

        # 11. Віджет прогресу приготування страви (якщо зараз щось готується)
        if cooking_tables:
            act_t = cooking_tables[0]
            total = max(0.1, act_t.cook_total)
            prog = max(0.0, min(1.0, 1.0 - (act_t.cook_timer / total)))
            pct = int(prog * 100)
            items = getattr(act_t, "order_items", [act_t.menu_item] if getattr(act_t, "menu_item", None) else [])
            food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)

            cw, ch = (245, 38) if len(items) > 1 else (210, 36)
            wx, wy = stove_rect.centerx, 290
            card = pygame.Surface((cw, ch + 6), pygame.SRCALPHA)
            pygame.draw.rect(card, (255, 250, 240, 245), (0, 0, cw, ch), border_radius=10)
            pygame.draw.rect(card, (225, 140, 60, 245), (0, 0, cw, ch), 2, border_radius=10)

            if len(items) > 1:
                d1 = assets.image_by_height(get_item_sprite(items[0].get("id", 1)), 18)
                d2 = assets.image_by_height(get_item_sprite(items[1].get("id", 1)), 18)
                card.blit(d1, (6, 9))
                card.blit(d2, (26, 9))
                text_x = 48
            else:
                d_icon = assets.image_by_height(get_item_sprite(items[0].get("id", 1) if items else 1), 20)
                card.blit(d_icon, (8, 8))
                text_x = 32

            f_sm = assets.font_ui(10 if len(items) > 1 else 11)
            txt_t = f_sm.render(f"Шеф варить: {food_names} ({pct}%)", True, C.TEXT_DARK)
            card.blit(txt_t, (text_x, 5))

            bar_w = cw - text_x - 10
            bar_h = 5
            pygame.draw.rect(card, (220, 210, 200), (text_x, 23, bar_w, bar_h), border_radius=3)
            fw = max(3, int(bar_w * prog))
            pygame.draw.rect(card, (235, 135, 45), (text_x, 23, fw, bar_h), border_radius=3)

            tail_pts = [(cw // 2 - 4, ch), (cw // 2 + 4, ch), (cw // 2, ch + 5)]
            pygame.draw.polygon(card, (255, 250, 240, 245), tail_pts)
            pygame.draw.polygon(card, (225, 140, 60, 245), tail_pts, 1)
            surface.blit(card, (wx - cw // 2, wy - ch // 2))

        # 12. Дверна арка повернення до залу кафе (кнопка над аркою праворуч)
        door_hover = (self.current_room == "kitchen" and (self.kitchen_to_hall_rect.collidepoint(mouse_pos) or self.arch_kitchen_to_hall.collidepoint(mouse_pos)))
        f_door = assets.font_ui(12, bold=True)
        txt = assets.render_outlined(f_door, "До залу кафе >>", C.WHITE, (40, 35, 30), 1)
        bw, bh = txt.get_width() + 20, 26
        bx, by = int(815 + offset_x - bw // 2), 212
        btn_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(btn_s, (*C.TERRACOTTA, 235 if door_hover else 190), (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(btn_s, C.WHITE, (0, 0, bw, bh), 2 if door_hover else 1, border_radius=8)
        btn_s.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
        surface.blit(btn_s, (bx, by))

        # 13. Бічна кнопка переходу до залу кафе праворуч
        side_hover = (self.current_room == "kitchen" and self.kitchen_to_hall_rect.collidepoint(mouse_pos))
        side_bw, side_bh = 180, 46
        side_bx = WIDTH - 195 + offset_x
        side_by = 390
        side_s = pygame.Surface((side_bw, side_bh), pygame.SRCALPHA)
        pygame.draw.rect(side_s, (*C.TERRACOTTA, 235 if side_hover else 195), (0, 0, side_bw, side_bh), border_radius=12)
        pygame.draw.rect(side_s, C.WHITE, (0, 0, side_bw, side_bh), 2 if side_hover else 1, border_radius=12)
        f_side = assets.font_ui(13, bold=True)
        txt_s = assets.render_outlined(f_side, "До залу кафе >>", C.WHITE, (40, 35, 30), 1)
        side_s.blit(txt_s, txt_s.get_rect(center=(side_bw // 2, side_bh // 2)))
        surface.blit(side_s, (side_bx, side_by))

    # ------------------------------------------------------------------
    def _draw_cooking_station(self, surface: pygame.Surface, offset_x: int = 0):
        """Анімація активного готування страв на кухні та помічник шеф-кухар Мурчик"""
        cooking_tables = [t for t in self._tables if t.state == TableState.ORDERED and not self._is_chef_table(t)]

        # 2. Якщо є замовлення, які зараз готуються -> показуємо дим та плаваючий віджет готування!
        if cooking_tables:
            act_t = cooking_tables[0]
            total = max(0.1, act_t.cook_total)
            prog = max(0.0, min(1.0, 1.0 - (act_t.cook_timer / total)))
            pct = int(prog * 100)

            items = getattr(act_t, "order_items", [act_t.menu_item] if getattr(act_t, "menu_item", None) else [])
            food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)

            # 2.1 Анімація клубочків пари над кавомашиною / плитою
            for i in range(4):
                st_phase = (self._t * 2.0 + i * 0.6) % 2.0
                st_y = 472 - st_phase * 34
                st_x = 863 + offset_x + math.sin(st_phase * 4.5 + i) * 8
                st_alpha = int((1.0 - (st_phase / 2.0)) * 190)
                st_r = int(3 + st_phase * 5)
                if st_r > 0 and st_alpha > 0:
                    st_surf = pygame.Surface((st_r * 2, st_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(st_surf, (255, 245, 255, st_alpha), (st_r, st_r), st_r)
                    surface.blit(st_surf, (int(st_x - st_r), int(st_y - st_r)))

            # 2.2 Плаваюча плашка статусу приготування над зоною кухні праворуч
            cw, ch = (235, 38) if len(items) > 1 else (195, 36)
            wx, wy = 960 + offset_x, 330
            card = pygame.Surface((cw, ch + 6), pygame.SRCALPHA)

            pygame.draw.rect(card, (255, 250, 240, 245), (0, 0, cw, ch), border_radius=10)
            pygame.draw.rect(card, (225, 140, 60, 245), (0, 0, cw, ch), 2, border_radius=10)

            # Іконка страви (або двох страв)
            if len(items) > 1:
                spr1 = get_item_sprite(items[0].get("id", 1))
                spr2 = get_item_sprite(items[1].get("id", 1))
                d1 = assets.image_by_height(spr1, 18)
                d2 = assets.image_by_height(spr2, 18)
                card.blit(d1, (6, 9))
                card.blit(d2, (26, 9))
                text_x = 48
            else:
                food_id = items[0].get("id", 1) if items else 1
                dish_spr_name = get_item_sprite(food_id)
                d_icon = assets.image_by_height(dish_spr_name, 20)
                card.blit(d_icon, (8, 8))
                text_x = 32

            # Текст: назва та відсоток
            f_sm = assets.font_ui(10 if len(items) > 1 else 11)
            txt_t = f_sm.render(f"Готується: {food_names} ({pct}%)", True, C.TEXT_DARK)
            card.blit(txt_t, (text_x, 5))

            # Прогрес-бар
            bar_w = cw - text_x - 10
            bar_h = 5
            bx, by = text_x, 23
            pygame.draw.rect(card, (220, 210, 200), (bx, by, bar_w, bar_h), border_radius=3)
            fw = max(3, int(bar_w * prog))
            pygame.draw.rect(card, (235, 135, 45), (bx, by, fw, bar_h), border_radius=3)

            # Хвостик баббла
            tail_pts = [(cw // 2 - 4, ch), (cw // 2 + 4, ch), (cw // 2, ch + 5)]
            pygame.draw.polygon(card, (255, 250, 240, 245), tail_pts)
            pygame.draw.polygon(card, (225, 140, 60, 245), tail_pts, 1)

            surface.blit(card, (wx - cw // 2, wy - ch // 2))

    # ------------------------------------------------------------------
    def _draw_counter_pickup_station(self, surface: pygame.Surface, offset_x: int = 0):
        """Отрисовка готових страв на стійці видачі баристи з ефектом 'Дінь!'"""
        ready_tables = [t for t in self._tables if t.state == TableState.READY and not getattr(t, 'is_picked_up', False) and not self._is_chef_table(t)]
        if not ready_tables:
            return

        cx, cy = 806 + offset_x, 505

        # М'яке золотисте сяйво стійки роздачі
        pulse = (math.sin(self._t * 5.0) + 1.0) * 0.5
        glow_r = int(24 + pulse * 6)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        glow_alpha = int(60 + pulse * 50)
        pygame.draw.circle(glow_surf, (255, 220, 110, glow_alpha), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (cx - glow_r, cy - glow_r))

        # Анімація пружного вибуху "Дінь!" при щойно приготованій страві
        if self.ready_pop_anim > 0:
            ring_r = int(18 + (1.0 - self.ready_pop_anim) * 36)
            ring_alpha = int(self.ready_pop_anim * 220)
            ring_surf = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255, 230, 80, ring_alpha), (ring_r, ring_r), ring_r, 3)
            surface.blit(ring_surf, (cx - ring_r, cy - ring_r))

        # Дерев'яна таця роздачі
        pw, ph = 52, 26
        tray_rect = pygame.Rect(cx - pw // 2, cy - ph // 2, pw, ph)
        pygame.draw.ellipse(surface, (145, 95, 60), tray_rect)
        pygame.draw.ellipse(surface, (190, 140, 95), (cx - pw // 2 + 2, cy - ph // 2 + 2, pw - 4, ph - 4))

        # Готова страва (або дві страви)
        top_tbl = ready_tables[0]
        items = getattr(top_tbl, "order_items", [top_tbl.menu_item] if getattr(top_tbl, "menu_item", None) else [])
        bob = int(math.sin(self._t * 6.0) * 2)

        if len(items) > 1:
            spr1 = get_item_sprite(items[0].get("id", 1))
            spr2 = get_item_sprite(items[1].get("id", 1))
            img1 = assets.image_by_height(spr1, 22)
            img2 = assets.image_by_height(spr2, 22)
            surface.blit(img1, img1.get_rect(center=(cx - 10, cy - 8 + bob)))
            surface.blit(img2, img2.get_rect(center=(cx + 10, cy - 8 + bob)))
        else:
            item_id = items[0].get("id", 1) if items else 1
            dish_spr_name = get_item_sprite(item_id)
            dish_img = assets.image_by_height(dish_spr_name, 28)
            surface.blit(dish_img, dish_img.get_rect(center=(cx, cy - 8 + bob)))

        # Бейджик з номером столика та кнопкою "Забрати!"
        badge_text = f"№{top_tbl.table_number} Забрати!"

        f = assets.font_ui(12)
        txt = f.render(badge_text, True, C.TEXT_DARK)
        bw = txt.get_width() + 16
        bh = 22
        bx = cx - bw // 2
        by = cy - 42

        badge = pygame.Surface((bw, bh + 5), pygame.SRCALPHA)
        pygame.draw.rect(badge, (255, 250, 230), (0, 0, bw, bh), border_radius=7)
        pygame.draw.rect(badge, (230, 150, 40), (0, 0, bw, bh), 2, border_radius=7)
        tail_pts = [(bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 4)]
        pygame.draw.polygon(badge, (255, 250, 230), tail_pts)
        pygame.draw.polygon(badge, (230, 150, 40), tail_pts, 1)

        badge.blit(txt, (8, 3))
        surface.blit(badge, (bx, by))

    def _draw_carrying_guide(self, surface: pygame.Surface, tbl: CafeTable = None, item: dict = None):
        """Інформаційний бейдж-підказка вгорі екрана, коли несеться страва"""
        if tbl is None:
            tbl = self.waiter.carrying_for_table
        if not tbl:
            return

        items = getattr(tbl, "order_items", [item] if item else [tbl.menu_item] if getattr(tbl, "menu_item", None) else [])
        food_names = " + ".join(locale.get(f"food.{MENU_ITEM_KEYS.get(it.get('id', 1), 'cappuccino')}") for it in items)

        is_terrace_table = tbl.table_number in (5, 6, 7, 8)
        if is_terrace_table and self.target_room != "terrace":
            guide_text = f"Несіть ({food_names}) до столика №{tbl.table_number}! Перейдіть на терасу ➡"
        elif not is_terrace_table and self.target_room != "hall":
            guide_text = f"Несіть ({food_names}) до столика №{tbl.table_number}! Перейдіть до залу ⬅"
        else:
            guide_text = f"Несіть ({food_names}) до столика №{tbl.table_number}! Клікніть по столику"

        f = assets.font_ui(13, bold=True)
        txt = assets.render_outlined(f, guide_text, C.TEXT_LIGHT, (45, 30, 20), 1)
        paw_img = assets.image_by_height("ui_icon_paw", 14)
        bw = txt.get_width() + 52
        bh = 30
        bx = WIDTH // 2 - bw // 2
        by = 64

        guide_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(guide_surf, (*C.TERRACOTTA, 240), (0, 0, bw, bh), border_radius=14)
        pygame.draw.rect(guide_surf, C.WHITE, (0, 0, bw, bh), 1, border_radius=14)
        guide_surf.blit(paw_img, (10, 8))
        guide_surf.blit(txt, (28, 5))
        guide_surf.blit(paw_img, (bw - 22, 8))
        surface.blit(guide_surf, (bx, by))

    # ------------------------------------------------------------------
    def _build_background(self):
        """Кімнати (кухня, зал, тераса) лишаються, а навколо них — фони з assets: двір (день/вечір) та бруківка"""
        from game.core.settings import ROOM_SIZE, ROOM_X, ROOM_Y
        import os
        from game.core.utils import resource_path

        def load(name):
            return pygame.image.load(resource_path(os.path.join("assets", "sprites", name)))

        BG_COLOR = (230, 211, 197)

        def room_layer(name):
            """Прозорий шар 1280x720 з кімнатою по центру"""
            layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            try:
                room = load(name)
                room = pygame.transform.smoothscale(room, (ROOM_SIZE, ROOM_SIZE))
                layer.blit(room, (ROOM_X, ROOM_Y))
            except Exception as e:
                print(f"Room background load error ({name}):", e)
            return layer

        self._bg_kitchen_surf = room_layer("bg_kitchen.png")
        self._bg_surf = room_layer("bg_cafe.png")
        self._bg_terrace_surf = room_layer("bg_terrace.png")

        # Двір навколо залу: верхня біла смуга файлу відрізається, картинка заповнює екран
        def world(name):
            try:
                img = load(name).convert()
                top = int(img.get_height() * 152 / 1536)
                img = img.subsurface((0, top, img.get_width(), img.get_height() - top))
                k = HEIGHT / img.get_height()
                img = pygame.transform.smoothscale(img, (int(img.get_width() * k), HEIGHT))
                out = pygame.Surface((WIDTH, HEIGHT))
                out.blit(img, (-(img.get_width() - WIDTH) // 2, 0))
                return out
            except Exception as e:
                print(f"World background load error ({name}):", e)
                fallback = pygame.Surface((WIDTH, HEIGHT))
                fallback.fill(BG_COLOR)
                return fallback

        self._world_day = world("bg_world.jpeg")
        self._world_eve = world("bg_world_evening.jpeg")

        # Бруківка навколо кухні та тераси (бесшовна плитка)
        tile_day = pygame.Surface((WIDTH, HEIGHT))
        tile_day.fill(BG_COLOR)
        try:
            tile = pygame.transform.smoothscale(load("bg_ground_tile.jpeg").convert(), (640, 640))
            for ty in range(0, HEIGHT, 640):
                for tx in range(0, WIDTH, 640):
                    tile_day.blit(tile, (tx, ty))
        except Exception as e:
            print("Ground tile load error:", e)
        tile_eve = tile_day.copy()
        tile_eve.fill((255, 214, 196), special_flags=pygame.BLEND_RGB_MULT)
        self._tile_day = tile_day
        self._tile_eve = tile_eve

    def _draw_backdrop(self, surface: pygame.Surface, room_name: str, dx: int):
        """Фон за кімнатою: двір для залу, бруківка для кухні/тераси; ввечері плавно теплішає"""
        if room_name == "hall":
            day, eve = self._world_day, self._world_eve
        else:
            day, eve = self._tile_day, self._tile_eve
        surface.blit(day, (dx, 0))
        ratio = self.time_left / float(DAY_DURATION)
        evening = max(0.0, min(1.0, (0.40 - ratio) / 0.15))
        if evening > 0.0:
            eve.set_alpha(int(evening * 255))
            surface.blit(eve, (dx, 0))

    def _get_wall_menu_board(self) -> pygame.Surface:
        """Широка дошка меню, перекошена під нахил правої стіни (кешується)"""
        if getattr(self, "_menu_board_surf", None) is None:
            src = pygame.transform.flip(assets.image("decor_menu_board"), True, False)
            w, h = MENU_BOARD_SIZE
            base = pygame.transform.smoothscale(src, (w, h))
            slope_now = 0.25 * (h / src.get_height()) / (w / src.get_width())
            extra = max(0.0, 0.5625 - slope_now)
            out = pygame.Surface((w, h + int(extra * w) + 2), pygame.SRCALPHA)
            for x in range(w):
                out.blit(base, (x, int(extra * x)), area=pygame.Rect(x, 0, 1, h))
            self._menu_board_surf = out
        return self._menu_board_surf

    def _draw_floor(self, surface: pygame.Surface):
        """Підлога вже вбудована в офіційний ізометричний фон bg_cafe.png"""
        pass

    def _draw_walls(self, surface: pygame.Surface, offset_x: int = 0):
        """Офіційний декор кімнати точно за координатами макета з правильним віддзеркаленням"""
        from game.core.settings import s_scale

        # 1. Декор лівої стіни
        has_monstera = self.upgrades.get("monstera", False)
        m_h = s_scale(320 if has_monstera else 280)
        p_big = assets.image_by_height("decor_plant_big", m_h)
        m_pos = (360 + offset_x, 535)
        if has_monstera:
            pulse = (math.sin(self._t * 3.5) + 1.0) * 0.5
            aura_r = int(p_big.get_width() // 2 + 8 + pulse * 4)
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (255, 225, 110, int(75 + pulse * 60)), (aura_r, aura_r), aura_r)
            surface.blit(aura_surf, (m_pos[0] - aura_r, m_pos[1] - m_h // 2 - aura_r))
        surface.blit(p_big, p_big.get_rect(midbottom=m_pos))

        # Поличка на лівій стіні (вище рослини, без жодних налізань на гостя за столиком №1)
        shelves = assets.image_by_height("decor_shelves", s_scale(230))
        surface.blit(shelves, shelves.get_rect(center=(365 + offset_x, 310)))

        # Картина з лапкою на стіні (акуратно між поличкою та дверима)
        paw_pic = assets.image_by_height("decor_picture_paw", s_scale(190))
        surface.blit(paw_pic, paw_pic.get_rect(center=(455 + offset_x, 265)))

        # Вхідні двері з круглим віконцем (природно стоять на рівні підлоги)
        door = assets.image_by_height("decor_door", s_scale(560))
        surface.blit(door, door.get_rect(midbottom=(550 + offset_x, 431)))

        # Килимок перед дверима (вільний прохід до столиків)
        has_rug = self.upgrades.get("doormat", False)
        mat_w = s_scale(240 if has_rug else 220)
        mat = assets.image_by_width("decor_doormat", mat_w)
        surface.blit(mat, mat.get_rect(center=(580 + offset_x, 440)))

        # 2. Декор правої стіни (природне розміщення вікна, підвісних рослин і дошки)
        win = assets.image_by_height("decor_window", s_scale(310))
        win = pygame.transform.flip(win, True, False)
        surface.blit(win, win.get_rect(center=(701 + offset_x, 305)))

        # Підвісна рослина біля вікна (ВІДДЗЕРКАЛЮЄМО кріплення до правої стіни)
        hp1 = assets.image_by_height("decor_plant_hanging", s_scale(220))
        hp1 = pygame.transform.flip(hp1, True, False)
        surface.blit(hp1, hp1.get_rect(midtop=(780 + offset_x, 290)))

        # Велика крейдова дошка з меню ПОЗАДУ БАРИСТИ
        menu = self._get_wall_menu_board()
        surface.blit(menu, menu.get_rect(center=(MENU_BOARD_POS[0] + offset_x, MENU_BOARD_POS[1])))

        # Підвісна рослина у правому куті кімнати (ВІДДЗЕРКАЛЮЄМО кріплення до правої стіни)
        hp2 = assets.image_by_height("decor_plant_hanging", s_scale(220))
        hp2 = pygame.transform.flip(hp2, True, False)
        surface.blit(hp2, hp2.get_rect(midtop=(935 + offset_x, 385)))
