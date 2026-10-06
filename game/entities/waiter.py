"""
Сущность: Официант (Waiter).
Котик-официант в жилетке с галстуком-бабочкой и подносом.
Передвигается по залу кафе, принимает заказы у столиков и разносит готовые блюда.
Выполняет ровно по 1 задаче за раз из очереди (принятие заказа -> забор с кухни -> подача на стол).
"""
import pygame
import math
import random
from typing import Optional, Callable
from game.core.settings import C, get_item_sprite
from game.core.assets import assets
from game.entities.table import CafeTable, TableState


ROOM_ORDER = ["kitchen", "hall", "terrace"]

# Выходы из комнат (куда идёт официант, чтобы перейти в соседнюю комнату) и точки входа в соседней
ROOM_EXIT = {
    ("kitchen", "right"): (938.0, 538.0),
    ("hall", "left"): (350.0, 545.0),
    ("hall", "right"): (940.0, 538.0),
    ("terrace", "left"): (345.0, 540.0),
}
ROOM_ENTRY = {
    ("hall", "right"): (360.0, 540.0),     # из кухни вошли в зал слева
    ("terrace", "right"): (365.0, 538.0),  # из зала вошли на террасу слева
    ("kitchen", "left"): (930.0, 536.0),   # из зала вошли на кухню справа
    ("hall", "left"): (935.0, 536.0),      # с террасы вошли в зал справа
}


def table_room(table) -> str:
    """Комната, в которой стоит столик"""
    return "terrace" if getattr(table, "table_number", 1) in (5, 6, 7, 8) else "hall"


def table_stand_point(table) -> tuple:
    """Где официант стоит у столика: на полу сбоку (со стороны, где нет стула), а не на самом столе"""
    from game.core.settings import CHAIR_RIGHT_TABLES
    side = -1 if getattr(table, "table_number", 0) in CHAIR_RIGHT_TABLES else 1
    return float(table.screen_x) + side * 58.0, float(table.screen_y) + 46.0


class WaiterState:
    IDLE  = "idle"     # Стоит на месте
    WALK  = "walk"     # Шагает к целевой точке
    SERVE = "serve"    # Подаёт заказ (довольные закрытые глазки ^^)
    HAPPY = "happy"    # Радостно машет лапками с сердечком


class TaskType:
    TAKE_ORDER   = "take_order"    # Подойти к столику, взять заказ, отнести баристе к стойке
    PICKUP_DISH  = "pickup_dish"   # Подойти к стойке и забрать готовое блюдо на поднос
    SERVE_DISH   = "serve_dish"    # Подойти к столику и вручную подать блюдо
    SERVE_ORDER  = "serve_order"   # Автоматический забор и подача (обратная совместимость)


class WaiterTask:
    def __init__(self, task_type: str, table: CafeTable, menu_item: dict = None):
        self.task_type = task_type
        self.table = table
        self.menu_item = menu_item or getattr(table, "menu_item", {})
        self.phase = "start"     # Этап внутри составной задачи


class WaiterParticle:
    """Сердечко или искорка при подаче заказа"""
    def __init__(self, x: float, y: float, ptype: str = "heart"):
        self.x = x
        self.y = y
        self.ptype = ptype
        self.age = 0.0
        self.lifetime = random.uniform(0.9, 1.4)
        self.vx = random.uniform(-14, 14)
        self.vy = random.uniform(-28, -42)
        self.size = random.uniform(5, 8)

    def update(self, dt: float) -> bool:
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface):
        progress = self.age / self.lifetime
        alpha = max(0, int((1.0 - progress) * 230))
        if self.ptype == "heart":
            hs = int(self.size)
            h_surf = pygame.Surface((hs * 2, hs * 2), pygame.SRCALPHA)
            col = (*C.TERRACOTTA, alpha)
            r = hs // 2
            pygame.draw.circle(h_surf, col, (r, r), r)
            pygame.draw.circle(h_surf, col, (hs + r, r), r)
            pygame.draw.polygon(h_surf, col, [(0, r), (hs * 2, r), (hs, hs * 2)])
            surface.blit(h_surf, (int(self.x - hs), int(self.y - hs)))
        else:
            ss = int(self.size)
            s_surf = pygame.Surface((ss * 2, ss * 2), pygame.SRCALPHA)
            col = (255, 220, 120, alpha)
            pygame.draw.line(s_surf, col, (ss, 0), (ss, ss * 2), 2)
            pygame.draw.line(s_surf, col, (0, ss), (ss * 2, ss), 2)
            surface.blit(s_surf, (int(self.x - ss), int(self.y - ss)))


class Waiter:
    """Котик-официант заведения"""

    def __init__(self, home_x: float = 680.0, home_y: float = 550.0,
                 pickup_x: float = 750.0, pickup_y: float = 525.0):
        # Базовая позиция точно по макету (между столиком 4 и стойкой)
        self.home_x = float(home_x)
        self.home_y = float(home_y)
        self.pickup_x = float(pickup_x)
        self.pickup_y = float(pickup_y)
        self.pickup_room = "hall"   # в какой комнате находится точка выдачи
        self.room = "hall"          # комната, где сейчас находится официант
        self.target_room = "hall"   # комната цели
        self.home_room = "hall"     # комната дежурного места

        # Текущая позиция
        self.x = float(home_x)
        self.y = float(home_y)
        self.target_x = float(home_x)
        self.target_y = float(home_y)

        # Скорость передвижения (пикселей в секунду)
        self.speed = 175.0
        self.facing_left = False

        # Состояние анимации
        self.state = WaiterState.IDLE
        self.anim_t = 0.0
        self.action_timer = 0.0

        # Предмет на подносе
        self.carrying_item: Optional[dict] = None
        self.carrying_for_table: Optional[CafeTable] = None

        # Очередь задач (строго по 1 задаче за раз)
        self.queue: list[WaiterTask] = []
        self.current_task: Optional[WaiterTask] = None

        # Частицы и облачко речи
        self.particles: list[WaiterParticle] = []
        self.speech_text: Optional[str] = None
        self.speech_timer = 0.0

        # Коллбеки для синхронизации с игрой
        self.on_order_taken_cb: Optional[Callable] = None
        self.on_order_served_cb: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Управление очередью задач
    # ------------------------------------------------------------------
    def is_busy(self) -> bool:
        """Занят ли официант в данный момент выполнением задачи или имеет задачи в очереди"""
        return self.current_task is not None or len(self.queue) > 0

    def is_table_busy(self, table: CafeTable) -> bool:
        """Проверяет, привязан ли уже столик к текущей задаче или очереди"""
        if self.current_task and self.current_task.table == table:
            return True
        return any(t.table == table for t in self.queue)

    def enqueue_take_order(self, table: CafeTable) -> bool:
        """Добавляет задачу подойти к столику, принять заказ и отнести на кухню"""
        if self.is_table_busy(table):
            return False
        self.queue.append(WaiterTask(TaskType.TAKE_ORDER, table))
        return True

    def enqueue_pickup_dish(self, table: CafeTable, menu_item: dict = None) -> bool:
        """Добавляет задачу подойти к стойке выдачи и взять готовое блюдо на поднос"""
        if self.carrying_item is not None:
            return False
        item = menu_item or getattr(table, "menu_item", None)
        self.queue.append(WaiterTask(TaskType.PICKUP_DISH, table, item))
        return True

    def enqueue_serve_dish(self, table: CafeTable) -> bool:
        """Добавляет задачу отнести блюдо с подноса на целевой столик"""
        if self.carrying_item is None:
            return False
        self.queue.append(WaiterTask(TaskType.SERVE_DISH, table, self.carrying_item))
        return True

    def enqueue_serve_order(self, table: CafeTable, menu_item: dict = None) -> bool:
        """Добавляет составную задачу: забрать заказ со стойки и подать на столик"""
        if self.is_table_busy(table):
            return False
        item = menu_item or getattr(table, "menu_item", None)
        self.queue.append(WaiterTask(TaskType.SERVE_ORDER, table, item))
        return True

    def say(self, text: str, duration: float = 1.8):
        self.speech_text = text
        self.speech_timer = duration

    # ------------------------------------------------------------------
    # Обновление логики
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.anim_t += dt

        if self.speech_timer > 0:
            self.speech_timer -= dt

        # Обновление частиц
        self.particles = [p for p in self.particles if p.update(dt)]

        # Если текущей задачи нет — берём следующую из очереди
        if self.current_task is None:
            if len(self.queue) > 0:
                self.current_task = self.queue.pop(0)
                self._start_task(self.current_task)
            else:
                # Очередь пуста — возвращаемся на дежурное место
                self.target_room = self.home_room
                dist = math.hypot(self.x - self.home_x, self.y - self.home_y)
                if self.room != self.home_room or dist > 8:
                    self._move_towards(self.home_x, self.home_y, dt)
                    self.state = WaiterState.WALK
                else:
                    self.x = self.home_x
                    self.y = self.home_y
                    self.state = WaiterState.IDLE
            return

        # Обработка текущей задачи
        task = self.current_task

        if task.task_type == TaskType.TAKE_ORDER:
            self._update_take_order_task(task, dt)
        elif task.task_type == TaskType.PICKUP_DISH:
            self._update_pickup_dish_task(task, dt)
        elif task.task_type == TaskType.SERVE_DISH:
            self._update_serve_dish_task(task, dt)
        elif task.task_type == TaskType.SERVE_ORDER:
            self._update_serve_order_task(task, dt)

    def _start_task(self, task: WaiterTask):
        """Инициализация первой фазы задачи"""
        if task.task_type == TaskType.TAKE_ORDER:
            # Идём к столику (встаём чуть правее стола для удобного ракурса)
            self.target_x = table_stand_point(task.table)[0]
            self.target_y = table_stand_point(task.table)[1]
            self.target_room = table_room(task.table)
            self.state = WaiterState.WALK
            task.phase = "goto_table"

        elif task.task_type == TaskType.PICKUP_DISH:
            # Идём к стойке выдачи забрать заказ
            self.target_x = self.pickup_x
            self.target_y = self.pickup_y
            self.target_room = self.pickup_room
            self.state = WaiterState.WALK
            task.phase = "goto_counter"

        elif task.task_type == TaskType.SERVE_DISH:
            # Идём с подносом к столику
            self.target_x = table_stand_point(task.table)[0]
            self.target_y = table_stand_point(task.table)[1]
            self.target_room = table_room(task.table)
            self.state = WaiterState.WALK
            task.phase = "goto_table"

        elif task.task_type == TaskType.SERVE_ORDER:
            # Сначала идём к барной стойке забрать готовое блюдо
            self.target_x = self.pickup_x
            self.target_y = self.pickup_y
            self.target_room = self.pickup_room
            self.state = WaiterState.WALK
            task.phase = "goto_pickup"

    def _update_take_order_task(self, task: WaiterTask, dt: float):
        # Если клиент уже ушёл — отменяем
        if not task.table.customer or task.table.customer.state in ("leaving", "gone"):
            task.table.is_queued_waiter = False
            self.current_task = None
            return

        if task.phase == "goto_table":
            if not self._arrived():
                self._move_towards(self.target_x, self.target_y, dt)
                self.state = WaiterState.WALK
            else:
                self.x, self.y = self.target_x, self.target_y
                task.phase = "taking"
                self.action_timer = 0.5
                self.state = WaiterState.IDLE
                self.say("Мур! Що вам подати? :3", duration=1.6)

        elif task.phase == "taking":
            self.action_timer -= dt
            self.state = WaiterState.IDLE
            if self.action_timer <= 0:
                task.phase = "goto_counter"
                self.target_x = self.pickup_x
                self.target_y = self.pickup_y
                self.target_room = "hall"
                self.state = WaiterState.WALK
                self.say("Несу замовлення баристі! :3", duration=1.4)

        elif task.phase == "goto_counter":
            if not self._arrived():
                self._move_towards(self.target_x, self.target_y, dt)
                self.state = WaiterState.WALK
            else:
                self.x, self.y = self.target_x, self.target_y
                task.phase = "hand_order"
                self.action_timer = 0.35
                self.state = WaiterState.IDLE

        elif task.phase == "hand_order":
            self.action_timer -= dt
            self.state = WaiterState.IDLE
            if self.action_timer <= 0:
                task.table.is_queued_waiter = False
                if self.on_order_taken_cb:
                    self.on_order_taken_cb(task.table)
                self.current_task = None

    def _update_pickup_dish_task(self, task: WaiterTask, dt: float):
        if task.phase == "goto_counter":
            if not self._arrived():
                self._move_towards(self.target_x, self.target_y, dt)
                self.state = WaiterState.WALK
            else:
                self.x, self.y = self.target_x, self.target_y
                task.phase = "picking_up"
                self.action_timer = 0.35
                self.state = WaiterState.IDLE

        elif task.phase == "picking_up":
            self.action_timer -= dt
            self.state = WaiterState.IDLE
            if self.action_timer <= 0:
                self.carrying_item = task.menu_item or getattr(task.table, "menu_item", {})
                self.carrying_for_table = task.table
                task.table.is_picked_up = True
                self.say(f"Взяв! До столика №{task.table.table_number}! :3", duration=1.8)
                self.current_task = None

    def _update_serve_dish_task(self, task: WaiterTask, dt: float):
        # Если клиент уже ушёл
        if not task.table.customer or task.table.customer.state in ("leaving", "gone"):
            self.carrying_item = None
            self.carrying_for_table = None
            task.table.is_picked_up = False
            task.table.is_queued_waiter = False
            self.current_task = None
            self.say("Клієнт пішов... :(", duration=1.8)
            return

        if task.phase == "goto_table":
            if not self._arrived():
                self._move_towards(self.target_x, self.target_y, dt)
                self.state = WaiterState.WALK
            else:
                self.x, self.y = self.target_x, self.target_y
                task.phase = "serving"
                self.action_timer = 0.7
                self.state = WaiterState.SERVE
                self.say("Смачного! ^^", duration=1.8)
                for _ in range(4):
                    self.particles.append(WaiterParticle(self.x, self.y - 45, "heart"))
                    self.particles.append(WaiterParticle(self.x, self.y - 40, "sparkle"))

        elif task.phase == "serving":
            self.action_timer -= dt
            self.state = WaiterState.SERVE
            if self.action_timer <= 0:
                if self.on_order_served_cb:
                    self.on_order_served_cb(task.table)
                self.carrying_item = None
                self.carrying_for_table = None
                task.table.is_picked_up = False
                task.table.is_queued_waiter = False
                self.current_task = None

    def _update_serve_order_task(self, task: WaiterTask, dt: float):
        # Если клиент ушёл — отменяем задачу
        if not task.table.customer or task.table.customer.state in ("leaving", "gone"):
            self.carrying_item = None
            self.carrying_for_table = None
            task.table.is_picked_up = False
            task.table.is_queued_waiter = False
            self.current_task = None
            return

        # Режим обратной совместимости (забрать и сразу подать)
        if task.phase == "goto_pickup":
            if not self._arrived():
                self._move_towards(self.target_x, self.target_y, dt)
                self.state = WaiterState.WALK
            else:
                self.x, self.y = self.target_x, self.target_y
                task.phase = "picking_up"
                self.action_timer = 0.35
                self.state = WaiterState.IDLE

        elif task.phase == "picking_up":
            self.action_timer -= dt
            self.state = WaiterState.IDLE
            if self.action_timer <= 0:
                self.carrying_item = task.menu_item or getattr(task.table, "menu_item", {})
                self.carrying_for_table = task.table
                task.table.is_picked_up = True
                task.phase = "goto_table"
                self.target_x = table_stand_point(task.table)[0]
                self.target_y = table_stand_point(task.table)[1]
                self.target_room = table_room(task.table)
                self.state = WaiterState.WALK

        elif task.phase == "goto_table":
            if not self._arrived():
                self._move_towards(self.target_x, self.target_y, dt)
                self.state = WaiterState.WALK
            else:
                self.x, self.y = self.target_x, self.target_y
                task.phase = "serving"
                self.action_timer = 0.7
                self.state = WaiterState.SERVE
                self.say("Смачного! ^^", duration=1.8)
                for _ in range(4):
                    self.particles.append(WaiterParticle(self.x, self.y - 45, "heart"))
                    self.particles.append(WaiterParticle(self.x, self.y - 40, "sparkle"))

        elif task.phase == "serving":
            self.action_timer -= dt
            self.state = WaiterState.SERVE
            if self.action_timer <= 0:
                if self.on_order_served_cb:
                    self.on_order_served_cb(task.table)
                self.carrying_item = None
                self.carrying_for_table = None
                task.table.is_picked_up = False
                task.table.is_queued_waiter = False
                self.current_task = None

    def _arrived(self) -> bool:
        """Дошёл ли официант до цели (в нужной комнате)"""
        return self.room == self.target_room and \
            math.hypot(self.x - self.target_x, self.y - self.target_y) <= 6

    def _move_towards(self, tx: float, ty: float, dt: float):
        """Идёт к цели; если цель в другой комнате — сначала к выходу, затем переходит в соседнюю комнату"""
        if self.room != self.target_room:
            ci = ROOM_ORDER.index(self.room)
            ti = ROOM_ORDER.index(self.target_room)
            side = "right" if ti > ci else "left"
            ex, ey = ROOM_EXIT[(self.room, side)]
            if math.hypot(self.x - ex, self.y - ey) <= 8:
                self.room = ROOM_ORDER[ci + (1 if side == "right" else -1)]
                self.x, self.y = ROOM_ENTRY[(self.room, side)]
            else:
                self._step(ex, ey, dt)
            return
        self._step(tx, ty, dt)

    def _step(self, tx: float, ty: float, dt: float):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 1.5:
            step = min(self.speed * dt, dist)
            self.x += (dx / dist) * step
            self.y += (dy / dist) * step
            if abs(dx) > 2.0:
                self.facing_left = (dx < 0)

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        from game.core.settings import s_scale
        target_h = s_scale(340)  # 124 px — точно по макету
        ix, iy = int(self.x) + offset_x, int(self.y)

        # Покачивание
        if self.carrying_item:
            # Официант несёт поднос с заказом, как на втором макете пользователя
            spr_name = "cat_waiter_serve"
            bob = int(math.sin(self.anim_t * 6.0) * 1.5)
        elif self.state == WaiterState.WALK:
            bob = int(math.sin(self.anim_t * 12.0) * 2.5)
            spr_name = "cat_waiter_walk"
        elif self.state == WaiterState.SERVE:
            bob = int(math.sin(self.anim_t * 6.0) * 1.5)
            spr_name = "cat_waiter_serve"
        elif self.state == WaiterState.HAPPY:
            bob = int(math.sin(self.anim_t * 8.0) * 2.5)
            spr_name = "cat_waiter_happy"
        else:
            bob = int(math.sin(self.anim_t * 3.0) * 1.5)
            spr_name = "cat_waiter_idle"

        base_spr = assets.image_by_height(spr_name, target_h)
        sw, sh = base_spr.get_size()

        # Разворот спрайта
        if self.facing_left:
            spr = pygame.transform.flip(base_spr, True, False)
        else:
            spr = base_spr

        bx = ix - sw // 2
        by = iy - sh + bob
        surface.blit(spr, (bx, by))

        # Отрисовка блюда на подносе (как круассан на тарелочке в макете)
        if self.carrying_item:
            food_id = self.carrying_item.get("id", 1)
            item_spr_name = get_item_sprite(food_id)
            dish_img = assets.image_by_height(item_spr_name, s_scale(80))

            # Точный центр тарелочки в лапке официанта
            rel_x = int(sw * 0.74)
            rel_y = int(sh * 0.44)

            if self.facing_left:
                dx = sw - rel_x
            else:
                dx = rel_x
            dy = rel_y

            dish_rect = dish_img.get_rect(center=(bx + dx, by + dy))
            surface.blit(dish_img, dish_rect)

        # Отрисовка частиц
        for p in self.particles:
            p.draw(surface)

        # Реплика
        if self.speech_timer > 0 and self.speech_text:
            self._draw_speech(surface, ix, iy - sh + bob)

    def _draw_speech(self, surface: pygame.Surface, cx: int, cy: int):
        f = assets.font_ui(12)
        txt = f.render(self.speech_text, True, C.TEXT_DARK)
        bw = txt.get_width() + 16
        bh = 24
        bx = cx - bw // 2
        by = cy - 26

        bubble = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
        pygame.draw.rect(bubble, C.WHITE, (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(bubble, C.TERRACOTTA, (0, 0, bw, bh), 2, border_radius=8)

        # Хвостик
        tail_pts = [(bw // 2 - 3, bh), (bw // 2 + 3, bh), (bw // 2, bh + 5)]
        pygame.draw.polygon(bubble, C.WHITE, tail_pts)
        pygame.draw.polygon(bubble, C.TERRACOTTA, tail_pts, 1)

        bubble.blit(txt, (8, 3))
        surface.blit(bubble, (bx, by))
