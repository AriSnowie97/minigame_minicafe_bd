"""
Система доставки продуктів: Машинка постачання та Котик-вантажник (кур'єр).

Логіка та анімації з використанням офіційних спрайтів:
- vehicle_truck_closed: вантажівка їде до кафе зліва направо (закриті двері);
- vehicle_truck_open: вантажівка припаркована біля кафе, двері кузова відчинені;
- cat_mover_carry: котик несе коробку з продуктами (напої / десерти баристи);
- cat_mover_push: котик штовхає візок із 3 коробками (страви шеф-кухаря Мурчика);
- cat_mover_stand: котик урочисто передає поповнення на стійку / кухню;
- cat_mover_walk: котик порожніми лапками повертається до машинки, махаючи лапкою;
- vehicle_truck_closed (розвернута ліворуч): машинка зачиняється та від'їжджає.
"""
import math
import random
import pygame
from typing import Optional, List, Dict, Tuple, Any

from game.core.settings import C, WIDTH, HEIGHT
from game.core.assets   import assets
from game.core.audio    import audio


class DeliveryOrder:
    def __init__(self, item_id: int, item_name: str, is_chef: bool, quantity: int = 10, icon: str = ""):
        self.item_id   = item_id
        self.item_name = item_name
        self.is_chef   = is_chef
        self.quantity  = quantity
        self.icon      = icon


class DeliveryManager:
    """Керує повним життєвим циклом машинки доставки та котика-вантажника"""

    STATE_IDLE              = "idle"
    STATE_VAN_IN            = "van_in"
    STATE_COURIER_DELIVER   = "courier_deliver"
    STATE_COURIER_HANDOFF   = "courier_handoff"
    STATE_COURIER_RETURN    = "courier_return"
    STATE_VAN_OUT           = "van_out"

    def __init__(self, scene):
        self.scene = scene
        self.queue: List[DeliveryOrder] = []
        self.current: Optional[DeliveryOrder] = None
        self.state = self.STATE_IDLE
        self.state_time = 0.0

        # Позиція та рух вантажівки (координати зала)
        self.van_x = -320.0
        self.van_target_x = 145.0
        self.van_y = 650.0
        self.van_speed = 230.0
        self.van_honked = False

        # Позиція та навігація котика-кур'єра
        self.courier_x = 145.0
        self.courier_y = 635.0
        self.courier_speed = 140.0
        self.courier_walk_t = 0.0
        self.courier_room = "hall"   # "hall" або "kitchen"
        self.courier_facing_right = True

        # Точки маршруту (вейпоінти)
        self.waypoints: List[Tuple[float, float]] = []
        self.waypoint_idx = 0
        self.use_push_cart = False

        # Димок із вихлопної труби
        self.exhaust_particles: List[Dict[str, float]] = []

    @property
    def has_active_delivery(self) -> bool:
        return self.state != self.STATE_IDLE or bool(self.queue)

    def order_delivery(self, item_id: int, item_name: str, is_chef: bool, quantity: int = 10, icon: str = ""):
        """Поставити нове замовлення доставки в чергу або розпочати негайно"""
        order = DeliveryOrder(item_id, item_name, is_chef, quantity, icon)
        self.queue.append(order)
        if self.state == self.STATE_IDLE:
            self._start_next_order()

    def _start_next_order(self):
        if not self.queue:
            self.state = self.STATE_IDLE
            self.current = None
            return

        self.current = self.queue.pop(0)
        self.state = self.STATE_VAN_IN
        self.state_time = 0.0
        self.van_x = -320.0
        self.van_honked = False
        self.use_push_cart = bool(self.current.is_chef or random.random() < 0.35)
        audio.play("door_bell")

    def update(self, dt: float):
        self.state_time += dt

        # Оновлення димку з вихлопної труби
        for p in self.exhaust_particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self.exhaust_particles = [p for p in self.exhaust_particles if p["life"] > 0]

        if self.state == self.STATE_IDLE:
            if self.queue:
                self._start_next_order()
            return

        # -------------------------------------------------------------
        # 1. Машинка під'їжджає (двері зачинені)
        # -------------------------------------------------------------
        if self.state == self.STATE_VAN_IN:
            if self.van_x < self.van_target_x:
                dist = self.van_target_x - self.van_x
                spd = max(65.0, min(self.van_speed, dist * 2.3))
                self.van_x += spd * dt
                self._emit_exhaust(dt, forward=True)
            else:
                self.van_x = self.van_target_x
                if not self.van_honked:
                    self.van_honked = True
                    audio.play("service_bell")
                if self.state_time > 0.45:
                    # Двері машинки відчиняються, кур'єр виходить
                    self.state = self.STATE_COURIER_DELIVER
                    self.state_time = 0.0
                    self.courier_room = "hall"
                    self.courier_x = self.van_x + 10.0
                    self.courier_y = self.van_y - 20.0
                    self._setup_delivery_waypoints()

        # -------------------------------------------------------------
        # 2. Кур'єр несе / везе продукцію до станції
        # -------------------------------------------------------------
        elif self.state == self.STATE_COURIER_DELIVER:
            self.courier_walk_t += dt * 8.5
            if self.waypoint_idx < len(self.waypoints):
                tx, ty = self.waypoints[self.waypoint_idx]
                dx = tx - self.courier_x
                dy = ty - self.courier_y
                dist = math.hypot(dx, dy)

                if abs(dx) > 0.5:
                    self.courier_facing_right = (dx > 0)

                step = self.courier_speed * dt
                if dist <= max(step, 8.0):
                    self.courier_x = tx
                    self.courier_y = ty
                    self.waypoint_idx += 1

                    # Перевіряємо, чи це був перехід через двері на кухню
                    if self.current and self.current.is_chef and self.courier_room == "hall" and self.waypoint_idx >= 3:
                        self.courier_room = "kitchen"
                        self.courier_x = 830.0
                        self.courier_y = 520.0
                        self.waypoints = [(640.0, 604.0)]
                        self.waypoint_idx = 0
                else:
                    ang = math.atan2(dy, dx)
                    self.courier_x += math.cos(ang) * step
                    self.courier_y += math.sin(ang) * step
            else:
                # Дійшли до стійки або кухні — передача товару
                self.state = self.STATE_COURIER_HANDOFF
                self.state_time = 0.0
                audio.play("plate_place")
                audio.play("star", mult=0.8, delay=0.15)
                self._on_delivered()

        # -------------------------------------------------------------
        # 3. Передача товару (котик радіє з руками в боки / візком)
        # -------------------------------------------------------------
        elif self.state == self.STATE_COURIER_HANDOFF:
            if self.state_time > 1.35:
                self.state = self.STATE_COURIER_RETURN
                self.state_time = 0.0
                self._setup_return_waypoints()

        # -------------------------------------------------------------
        # 4. Кур'єр порожніми лапками повертається до машинки
        # -------------------------------------------------------------
        elif self.state == self.STATE_COURIER_RETURN:
            self.courier_walk_t += dt * 8.5
            if self.waypoint_idx < len(self.waypoints):
                tx, ty = self.waypoints[self.waypoint_idx]
                dx = tx - self.courier_x
                dy = ty - self.courier_y
                dist = math.hypot(dx, dy)

                if abs(dx) > 0.5:
                    self.courier_facing_right = (dx > 0)

                step = self.courier_speed * dt
                if dist <= max(step, 8.0):
                    self.courier_x = tx
                    self.courier_y = ty
                    self.waypoint_idx += 1

                    # Якщо вийшли з дверей кухні назад у зал
                    if self.courier_room == "kitchen" and self.waypoint_idx >= len(self.waypoints):
                        self.courier_room = "hall"
                        self.courier_x = 45.0
                        self.courier_y = 470.0
                        door_van_x = self.van_x + 10.0
                        door_van_y = self.van_y - 20.0
                        self.waypoints = [
                            (140.0, 530.0),
                            (350.0, 620.0),
                            (door_van_x, door_van_y),
                        ]
                        self.waypoint_idx = 0
                else:
                    ang = math.atan2(dy, dx)
                    self.courier_x += math.cos(ang) * step
                    self.courier_y += math.sin(ang) * step
            else:
                # Кур'єр застрибнув назад у фургон
                self.state = self.STATE_VAN_OUT
                self.state_time = 0.0
                audio.play("cat_happy")
                audio.play("service_bell", delay=0.1)

        # -------------------------------------------------------------
        # 5. Машинка зачиняється, розвертається та їде геть ліворуч
        # -------------------------------------------------------------
        elif self.state == self.STATE_VAN_OUT:
            self.van_x -= self.van_speed * 1.35 * dt
            self._emit_exhaust(dt, forward=False)
            if self.van_x < -360.0:
                self._start_next_order()

    def _setup_delivery_waypoints(self):
        """Побудова акуратного шляху від дверей машинки до станції прийому"""
        if not self.current:
            return
        if self.current.is_chef:
            # На кухню через лівий прохід зали
            self.waypoints = [
                (250.0, 630.0),
                (140.0, 530.0),
                (45.0, 470.0),
            ]
        else:
            # До барної стійки баристи
            self.waypoints = [
                (350.0, 625.0),
                (540.0, 575.0),
                (760.0, 535.0),
            ]
        self.waypoint_idx = 0

    def _setup_return_waypoints(self):
        """Шлях повернення від станції назад до відчинених дверей вантажівки"""
        door_van_x = self.van_x + 10.0
        door_van_y = self.van_y - 20.0

        if self.courier_room == "kitchen":
            # З кухні спочатку до арки виходу праворуч
            self.waypoints = [
                (830.0, 520.0),
            ]
        else:
            # З зали кафе через центральний прохід назад до машинки
            self.waypoints = [
                (540.0, 575.0),
                (350.0, 625.0),
                (door_van_x, door_van_y),
            ]
        self.waypoint_idx = 0

    def _on_delivered(self):
        """Зарахування +10 одиниць товару та святкові спецефекти"""
        if not self.current:
            return
        mid = self.current.item_id
        old_val = self.scene.stock.get(mid, 0)
        self.scene.stock[mid] = old_val + self.current.quantity

        if hasattr(self.scene, "star_particles"):
            from game.scenes.cafe_hall import StarParticle
            px = 610.0 if self.current.is_chef else 810.0
            py = 590.0 if self.current.is_chef else 490.0
            for _ in range(12):
                self.scene.star_particles.append(StarParticle(px, py))

        name = self.current.item_name
        if self.current.is_chef:
            if hasattr(self.scene, "cook") and hasattr(self.scene.cook, "say"):
                self.scene.cook.say(f"Свіжі продукти для {name} на кухні! :3", duration=2.5)
        else:
            if hasattr(self.scene, "barista") and hasattr(self.scene.barista, "say"):
                self.scene.barista.say(f"Отримали запас {name} (+10)! :3", duration=2.5)

        if hasattr(self.scene, "notifications"):
            from game.scenes.cafe_hall import Notification
            self.scene.notifications.append(
                Notification(f"Поставка прибула: +10 шт {name}!", (60, 150, 80), 3.0)
            )

    def _emit_exhaust(self, dt: float, forward: bool = True):
        if random.random() < 0.40:
            tail_x = self.van_x - 70.0 if forward else self.van_x + 70.0
            tail_y = self.van_y - 15.0
            self.exhaust_particles.append({
                "x": tail_x,
                "y": tail_y,
                "vx": random.uniform(-40, -15) if forward else random.uniform(15, 40),
                "vy": random.uniform(-18, -4),
                "r": random.uniform(4.0, 7.5),
                "life": random.uniform(0.5, 0.9),
                "max_life": 0.9,
            })

    # =================================================================
    # Отрисовка
    # =================================================================
    def draw_van(self, surface: pygame.Surface, offset_x: int = 0):
        """Отрисовка вантажівки (малюється на вулиці перед залом)"""
        if self.state == self.STATE_IDLE:
            return

        # 1. Димок вихлопу
        for p in self.exhaust_particles:
            ratio = max(0.0, p["life"] / p["max_life"])
            alpha = int(170 * ratio)
            r = int(p["r"] * (1.0 + (1.0 - ratio) * 0.8))
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (225, 225, 225, alpha), (r + 1, r + 1), r)
            surface.blit(s, (int(p["x"] + offset_x - r), int(p["y"] - r)))

        vx = int(self.van_x + offset_x)
        vy = int(self.van_y)

        # Тінь вантажівки на бруківці
        shadow = pygame.Surface((215, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 75), (0, 0, 215, 36))
        surface.blit(shadow, shadow.get_rect(center=(vx, vy + 2)))

        # 2. Вибір спрайту: закритий чи з відкритими дверима
        if self.state in (self.STATE_COURIER_DELIVER, self.STATE_COURIER_HANDOFF, self.STATE_COURIER_RETURN):
            # Вантажівка стоїть на розвантаженні — двері кузова відчинені!
            van_spr = assets.image_by_height("vehicle_truck_open", 170)
            if van_spr and not getattr(van_spr, "_is_placeholder", False):
                # Фіксуємо правий край кабіни, щоб колеса й кабіна стояли на місці
                right_edge = vx + 104
                surface.blit(van_spr, van_spr.get_rect(bottomright=(right_edge, vy)))
            else:
                self._draw_procedural_van(surface, vx, vy)
        elif self.state == self.STATE_VAN_OUT:
            # Машинка розвернулася та їде ліворуч — закрита, віддзеркалена
            van_spr = assets.image_by_height("vehicle_truck_closed", 170)
            if van_spr and not getattr(van_spr, "_is_placeholder", False):
                flipped_van = pygame.transform.flip(van_spr, True, False)
                left_edge = vx - 104
                surface.blit(flipped_van, flipped_van.get_rect(bottomleft=(left_edge, vy)))
            else:
                self._draw_procedural_van(surface, vx, vy, flip=True)
        else:
            # Машинка заїжджає праворуч — закрита
            van_spr = assets.image_by_height("vehicle_truck_closed", 170)
            if van_spr and not getattr(van_spr, "_is_placeholder", False):
                right_edge = vx + 104
                surface.blit(van_spr, van_spr.get_rect(bottomright=(right_edge, vy)))
            else:
                self._draw_procedural_van(surface, vx, vy)

        # 3. Плашка-хмаринка над машинкою при прибутті
        if self.state in (self.STATE_VAN_IN, self.STATE_COURIER_DELIVER) and self.van_x >= self.van_target_x - 10:
            f = assets.font_ui(12, bold=True)
            bubble_txt = assets.render_outlined(f, "Біп-біп! Доставка :3", C.WHITE, (45, 40, 35), 1)
            bw, bh = bubble_txt.get_width() + 18, 24
            bsurf = pygame.Surface((bw, bh + 4), pygame.SRCALPHA)
            pygame.draw.rect(bsurf, (*C.TERRACOTTA, 240), (0, 0, bw, bh), border_radius=8)
            pygame.draw.rect(bsurf, C.WHITE, (0, 0, bw, bh), 1, border_radius=8)
            pygame.draw.polygon(bsurf, (*C.TERRACOTTA, 240), [(bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 4)])
            bsurf.blit(bubble_txt, (9, 3))
            surface.blit(bsurf, (vx - bw // 2, vy - 150))

    def draw_courier(self, surface: pygame.Surface, room_name: str, offset_x: int = 0):
        """Отрисовка котика-вантажника у залі або на кухні"""
        if self.state not in (self.STATE_COURIER_DELIVER, self.STATE_COURIER_HANDOFF, self.STATE_COURIER_RETURN):
            return
        if self.courier_room != room_name:
            return

        cx = int(self.courier_x + offset_x)
        cy = int(self.courier_y)
        bob = int(math.sin(self.courier_walk_t) * 2.0) if self.state != self.STATE_COURIER_HANDOFF else 0

        # Тінь під лапками котика
        shadow = pygame.Surface((34, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 75), (0, 0, 34, 14))
        surface.blit(shadow, shadow.get_rect(center=(cx, cy - 2)))

        # Вибір спрайту залежно від стану
        if self.state == self.STATE_COURIER_DELIVER:
            spr_name = "cat_mover_push" if self.use_push_cart else "cat_mover_carry"
            target_h = 92
        elif self.state == self.STATE_COURIER_HANDOFF:
            spr_name = "cat_mover_stand"
            target_h = 95
        else:  # STATE_COURIER_RETURN
            spr_name = "cat_mover_walk"
            target_h = 95

        spr = assets.image_by_height(spr_name, target_h)
        if spr and not getattr(spr, "_is_placeholder", False):
            # За замовчуванням спрайти дивляться ліворуч.
            # Якщо котик рухається праворуч — віддзеркалюємо по горизонталі!
            if self.courier_facing_right:
                spr = pygame.transform.flip(spr, True, False)
            rect = spr.get_rect(midbottom=(cx, cy + bob))
            surface.blit(spr, rect)

            # Якщо несе коробку або візок — наносимо міні-іконку страви
            if self.state in (self.STATE_COURIER_DELIVER, self.STATE_COURIER_HANDOFF) and self.current and self.current.icon:
                icon_img = assets.image_by_height(self.current.icon, 16)
                if icon_img and not getattr(icon_img, "_is_placeholder", False):
                    # Розміщення по центру передньої коробки
                    icon_rel_x = rect.centerx + (14 if self.courier_facing_right else -14)
                    icon_rel_y = rect.centery + 6
                    surface.blit(icon_img, icon_img.get_rect(center=(icon_rel_x, icon_rel_y)))
        else:
            self._draw_procedural_courier(surface, cx, cy)

    def _draw_procedural_van(self, surface: pygame.Surface, vx: int, vy: int, flip: bool = False):
        """Резервна процедурна детальна ретро-вантажівка на випадок відсутності файлів"""
        van_surf = pygame.Surface((180, 100), pygame.SRCALPHA)
        pygame.draw.rect(van_surf, (85, 160, 135), (10, 32, 160, 50), border_radius=12)
        pygame.draw.rect(van_surf, (255, 248, 235), (20, 8, 145, 36), border_top_left_radius=14, border_top_right_radius=10)
        pygame.draw.rect(van_surf, (200, 230, 245), (120, 12, 40, 24), border_top_right_radius=8)
        pygame.draw.rect(van_surf, (200, 230, 245), (55, 12, 58, 24), border_radius=4)
        paw_icon = assets.image_by_height("ui_icon_paw", 18)
        van_surf.blit(paw_icon, (76, 46))
        pygame.draw.circle(van_surf, (40, 40, 40), (46, 82), 14)
        pygame.draw.circle(van_surf, (40, 40, 40), (138, 82), 14)
        if flip:
            van_surf = pygame.transform.flip(van_surf, True, False)
        surface.blit(van_surf, (vx - 90, vy - 70))

    def _draw_procedural_courier(self, surface: pygame.Surface, cx: int, cy: int):
        """Резервний процедурний рудий котик-кур'єр"""
        bob = int(math.sin(self.courier_walk_t) * 2.0)
        base_y = cy - 28 + bob
        pygame.draw.circle(surface, (235, 145, 65), (cx, base_y), 15)
        pygame.draw.circle(surface, (40, 30, 20), (cx - 4, base_y - 2), 2)
        pygame.draw.circle(surface, (40, 30, 20), (cx + 4, base_y - 2), 2)
        pygame.draw.polygon(surface, (230, 120, 110), [(cx - 2, base_y + 2), (cx + 2, base_y + 2), (cx, base_y + 4)])
