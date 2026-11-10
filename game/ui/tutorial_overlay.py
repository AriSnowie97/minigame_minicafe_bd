"""
Покрокова система інтерактивного навчання (День 0: Як грати у MiniCafe).
Повністю інтегрована з авторськими спрайтами помічниці Арі:
- teach_ari (пояснення та введення в гру)
- idle_ari (спостереження за процесом варіння)
- wink_ari (підморгування, коли замовлення готове)
- wow_ari (захоплення при подачі напою гостю)
- happy_ari (радість при зборі виручки)
- shy_ari (подяка та фінал навчання)
- sad_ari (підтримка при труднощах)
"""
import os
import math
import random
import pygame
from typing import Optional, Tuple, Dict

from game.core.settings import C, WIDTH, HEIGHT
from game.core.assets   import assets
from game.core.audio    import audio
from game.core.utils    import resource_path
from game.core.profile  import set_tutorial_completed
from game.entities.table import TableState


class TutorialOverlay:
    """
    Інтерактивний помічник для Дня 0:
    - Показує наставницю Арі ліворуч від зали кафе, притиснуту до низу екрана.
    - Відображає портретні емоції Арі у верхній діалоговій картці.
    - Підсвічує цілі та анімує стрілочки тільки коли ціль активна.
    - Автоматично переходить до завершення щойно замовлення виконано.
    """

    STEP_TAKE_ORDER   = 0
    STEP_BREWING      = 1
    STEP_PICKUP       = 2
    STEP_SERVE        = 3
    STEP_COLLECT_COIN = 4
    STEP_COMPLETE     = 5

    STEP_SPRITE_NAMES = {
        STEP_TAKE_ORDER:   "teach_ari",
        STEP_BREWING:      "idle_ari",
        STEP_PICKUP:       "wink_ari",
        STEP_SERVE:        "wow_ari",
        STEP_COLLECT_COIN: "happy_ari",
        STEP_COMPLETE:     "happy_ari",
    }

    def __init__(self, scene):
        self.scene = scene
        self.step = self.STEP_TAKE_ORDER
        self._t = 0.0
        self.completed = False
        self._cache: Dict[str, pygame.Surface] = {}

        # Інтерактивні прямокутники
        self.btn_finish_rect = pygame.Rect(WIDTH // 2 - 140, 120, 280, 44)
        self.btn_skip_rect   = pygame.Rect(WIDTH - 150, 14, 136, 28)
        self.ari_full_rect   = pygame.Rect(0, 0, 1, 1)

        # Репліка Арі при кліку на неї
        self.ari_dialog_msg: Optional[str] = None
        self.ari_dialog_timer: float = 0.0

    def reset(self):
        self.step = self.STEP_TAKE_ORDER
        self._t = 0.0
        self.completed = False
        self.ari_dialog_msg = None
        self.ari_dialog_timer = 0.0

    def update(self, dt: float):
        if getattr(self.scene, "day", 1) != 0:
            return
        self._t += dt

        if self.ari_dialog_timer > 0:
            self.ari_dialog_timer -= dt
            if self.ari_dialog_timer <= 0:
                self.ari_dialog_msg = None

        tables = getattr(self.scene, "_tables", [])
        active_table = next((t for t in tables if getattr(t, "table_number", None) == 3), (tables[0] if tables else None))
        orders_done = getattr(self.scene, "orders_done", 0)

        # Якщо замовлення вже виконано або гість пішов після обслуговування — завершуємо навчання!
        if orders_done >= 1:
            if self.step < self.STEP_COMPLETE:
                self.step = self.STEP_COMPLETE
                set_tutorial_completed(True)
                audio.play("order_complete")

        if self.step in (self.STEP_COMPLETE, self.STEP_COLLECT_COIN):
            self._auto_advance_timer = getattr(self, "_auto_advance_timer", 0.0) + dt
            if self._auto_advance_timer >= 3.5:
                self._finish_tutorial()
            return

        # Крок 0: Прийом замовлення -> завершується, коли замовлення прийнято
        if self.step == self.STEP_TAKE_ORDER:
            if active_table and active_table.state in (TableState.ORDERED, TableState.READY, TableState.PAYING):
                self.step = self.STEP_BREWING
                audio.play("star", mult=0.8)

        # Крок 1: Бариста варить -> завершується, коли напій готовий на стійці
        elif self.step == self.STEP_BREWING:
            ready_item = getattr(self.scene, "ready_item", None)
            barista = getattr(self.scene, "barista", None)
            if ready_item is not None or (barista and barista.state == "serve") or (active_table and active_table.state == TableState.READY):
                self.step = self.STEP_PICKUP
                audio.play("service_bell")

        # Крок 2: Взяти напій зі стійки -> гравець несе замовлення
        elif self.step == self.STEP_PICKUP:
            if getattr(self.scene, "player_carrying_table", None) is not None:
                self.step = self.STEP_SERVE
                audio.play("plate_place")

        # Крок 3: Подати гостю -> щойно напій подано або гість розрахувався
        elif self.step in (self.STEP_SERVE, self.STEP_COLLECT_COIN):
            # Якщо гравець уже подав (не несе) і стіл не порожній, або стіл звільнився, або гроші нараховані
            if getattr(self.scene, "player_carrying_table", None) is None:
                if active_table and active_table.state in (TableState.PAYING, TableState.EMPTY):
                    self.step = self.STEP_COMPLETE
                    set_tutorial_completed(True)
                    audio.play("order_complete")

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        if getattr(self.scene, "day", 1) != 0:
            return False

        # Клік по кнопці пропуску навчання
        if self.btn_skip_rect.collidepoint(pos):
            set_tutorial_completed(True)
            audio.play("ui_click")
            self._finish_tutorial()
            return True

        # Клік для переходу до підсумків дня та Дня 1
        if self.step in (self.STEP_COMPLETE, self.STEP_COLLECT_COIN):
            set_tutorial_completed(True)
            audio.play("ui_click")
            self._finish_tutorial()
            return True

        # Інтерактивний клік по самій Арі
        if self.ari_full_rect.collidepoint(pos):
            audio.play("ui_click")
            self.on_ari_clicked()
            return True

        return False

    def on_ari_clicked(self):
        """Реакція Арі на дотик/клік гравця."""
        quotes = [
            "Я вірю у вас, бос! Усе вийде :3",
            "Клікайте на підсвічені столики та барну стійку!",
            "Наше кафе буде найзатишнішим у місті!",
            "Мурр! Кава вариться з теплом та любов'ю :3",
            "Слухайте дзвіночок — коли він дзеленчить, напій готовий!",
        ]
        self.ari_dialog_msg = random.choice(quotes)
        self.ari_dialog_timer = 2.8

    def _finish_tutorial(self):
        """Завершення Дня 0 та перехід до підсумків / Дня 1"""
        self.completed = True
        set_tutorial_completed(True)
        self.scene.manager.switch(
            "game_over",
            day=0,
            money=max(35, getattr(self.scene, "money", 35)),
            rating=5.0,
            orders_done=max(1, getattr(self.scene, "orders_done", 1)),
            orders_bad=0,
            upgrades=getattr(self.scene, "upgrades", {}),
            failed=False,
            fail_reason="",
            stock=getattr(self.scene, "stock", {}),
            player_name=getattr(self.scene, "player_name", "Котик")
        )

    # ------------------------------------------------------------------
    # Робота зі спрайтами Арі (портрет та повний зріст)
    # ------------------------------------------------------------------
    def get_ari_sprite_name(self) -> str:
        return self.STEP_SPRITE_NAMES.get(self.step, "teach_ari")

    def get_ari_portrait(self, name: str, size: int = 76) -> pygame.Surface:
        """Створює детальний портрет обличчя Арі для діалогової картки."""
        key = f"portrait_{name}_{size}"
        if key not in self._cache:
            base = assets.image(name)
            if base and not getattr(base, "_is_placeholder", False):
                w, h = base.get_size()
                head_sz = int(h * 0.38)
                x1 = max(0, min(w - head_sz, w // 2 - head_sz // 2))
                cropped = base.subsurface((x1, 0, head_sz, head_sz))
                self._cache[key] = pygame.transform.smoothscale(cropped, (size, size))
            else:
                self._cache[key] = assets.image_by_height("cat_caramel_happy", size)
        return self._cache[key]

    def get_ari_full(self, name: str, height: int = 420) -> pygame.Surface:
        """Створює фігуру Арі для відображення поруч із кафе."""
        key = f"full_{name}_{height}"
        if key not in self._cache:
            base = assets.image(name)
            if base and not getattr(base, "_is_placeholder", False):
                w, h = base.get_size()
                scale = height / max(1, h)
                target_w = max(1, int(w * scale))
                self._cache[key] = pygame.transform.smoothscale(base, (target_w, height))
            else:
                self._cache[key] = assets.image_by_height("cat_caramel_sit", height)
        return self._cache[key]

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, offset_x: int = 0):
        if getattr(self.scene, "day", 1) != 0:
            return

        mouse_pos = pygame.mouse.get_pos()
        tables = getattr(self.scene, "_tables", [])
        active_table = next((t for t in tables if getattr(t, "table_number", None) == 3), (tables[0] if tables else None))
        current_ari_spr = self.get_ari_sprite_name()

        # -------------------------------------------------------------
        # 1. Фігура Арі ліворуч від зали кафе (притиснута до низу екрана)
        # -------------------------------------------------------------
        cx_ari = 135
        cy_ari = HEIGHT + 2
        bob = int(math.sin(self._t * 2.5) * 2.0)

        # Сама фігура Арі (низ акуратно схований під нижню рамку вікна)
        ari_full = self.get_ari_full(current_ari_spr, height=420)
        ari_rect = ari_full.get_rect(midbottom=(cx_ari, cy_ari + bob))
        self.ari_full_rect = ari_rect
        surface.blit(ari_full, ari_rect)

        # Бейджик імені Арі над головою
        badge_rect = pygame.Rect(cx_ari - 64, ari_rect.top - 20, 128, 22)
        pygame.draw.rect(surface, (255, 248, 240), badge_rect, border_radius=6)
        pygame.draw.rect(surface, C.TERRACOTTA, badge_rect, 1, border_radius=6)
        f_badge = assets.font_ui(11, bold=True)
        bt = f_badge.render("Арі • Наставниця", True, C.TERRACOTTA)
        surface.blit(bt, bt.get_rect(center=badge_rect.center))

        # Спливаюча мовна хмаринка при кліку на Арі
        if self.ari_dialog_msg:
            f_bubble = assets.font_ui(12, bold=True)
            bubble_t = f_bubble.render(self.ari_dialog_msg, True, C.TEXT_DARK)
            bw = bubble_t.get_width() + 20
            bh = 32
            bx = cx_ari - bw // 2
            by = ari_rect.top - 60
            b_rect = pygame.Rect(bx, by, bw, bh)
            pygame.draw.rect(surface, (255, 255, 255), b_rect, border_radius=8)
            pygame.draw.rect(surface, C.TERRACOTTA, b_rect, 1, border_radius=8)
            # Хвостик хмаринки
            pygame.draw.polygon(surface, (255, 255, 255), [(cx_ari - 6, by + bh), (cx_ari + 6, by + bh), (cx_ari, by + bh + 6)])
            pygame.draw.polygon(surface, C.TERRACOTTA, [(cx_ari - 6, by + bh), (cx_ari + 6, by + bh), (cx_ari, by + bh + 6)], 1)
            surface.blit(bubble_t, bubble_t.get_rect(center=b_rect.center))

        # -------------------------------------------------------------
        # 2. Підсвічування та анімовані стрілочки тільки для ДІЙСНИХ цілей
        # -------------------------------------------------------------
        target_pos = None
        # Стрілка на столик потрібна ТІЛЬКИ коли гість реально там сидить і чекає
        if self.step == self.STEP_TAKE_ORDER:
            if active_table and active_table.state == TableState.SEATED:
                target_pos = (active_table.screen_x + offset_x, active_table.screen_y - 20)
        elif self.step == self.STEP_BREWING:
            barista = getattr(self.scene, "barista", None)
            if barista:
                target_pos = (barista.screen_x + offset_x, barista.screen_y - 75)
        elif self.step == self.STEP_PICKUP:
            target_pos = (785 + offset_x, 480)
        elif self.step == self.STEP_SERVE:
            if active_table and active_table.state not in (TableState.EMPTY, TableState.FREE if hasattr(TableState, "FREE") else "free"):
                target_pos = (active_table.screen_x + offset_x, active_table.screen_y - 20)

        # Малюємо стрілочку ТІЛЬКИ якщо є дійсна незавершена ціль
        if target_pos and self.step not in (self.STEP_COMPLETE, self.STEP_COLLECT_COIN):
            tx, ty = target_pos
            tbob = math.sin(self._t * 6.0) * 8.0
            pulse = math.sin(self._t * 4.0) * 0.25 + 0.75

            # Пульсуючий ореол навколо цілі
            glow_surf = pygame.Surface((90, 44), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (*C.TERRACOTTA, int(110 * pulse)), (0, 0, 90, 44), 3)
            surface.blit(glow_surf, glow_surf.get_rect(center=(tx, ty + 15)))

            # Стрілочка, що вказує вниз
            arrow_color = (255, 230, 110)
            arr_y = ty - 45 + tbob
            pts = [
                (tx, arr_y + 22),
                (tx - 12, arr_y + 8),
                (tx - 5, arr_y + 8),
                (tx - 5, arr_y),
                (tx + 5, arr_y),
                (tx + 5, arr_y + 8),
                (tx + 12, arr_y + 8)
            ]
            pygame.draw.polygon(surface, arrow_color, pts)
            pygame.draw.polygon(surface, (80, 40, 20), pts, 2)

        # -------------------------------------------------------------
        # 3. Верхня плашка навчання (Tutorial Dialogue Card)
        # -------------------------------------------------------------
        card_w, card_h = 760, 102
        card_x = (WIDTH - card_w) // 2
        card_y = 12

        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
        shadow_rect = pygame.Rect(card_x + 3, card_y + 4, card_w, card_h)

        pygame.draw.rect(surface, (0, 0, 0, 45), shadow_rect, border_radius=14)
        pygame.draw.rect(surface, (255, 252, 246), card_rect, border_radius=14)
        pygame.draw.rect(surface, C.TERRACOTTA, card_rect, 2, border_radius=14)

        # Зона під портрет Арі
        avatar_box = pygame.Rect(card_x + 12, card_y + 12, 78, 78)
        pygame.draw.rect(surface, (254, 245, 235), avatar_box, border_radius=12)
        pygame.draw.rect(surface, (235, 215, 200), avatar_box, 1, border_radius=12)

        # Відображення портрета Арі
        portrait = self.get_ari_portrait(current_ari_spr, size=76)
        surface.blit(portrait, portrait.get_rect(center=avatar_box.center))

        # -------------------------------------------------------------
        # 4. Текст інструкцій за кроками
        # -------------------------------------------------------------
        f_step_pill = assets.font_ui(11, bold=True)
        f_headline  = assets.font_ui(15, bold=True)
        f_desc      = assets.font_ui(13)

        STEP_DATA = {
            self.STEP_TAKE_ORDER: (
                "Крок 1/4: Прийом замовлення",
                "Ласкаво просимо до MiniCafe!",
                "До столика сів перший гість кафе. Клікніть на столик №3, щоб прийняти замовлення :3"
            ),
            self.STEP_BREWING: (
                "Крок 2/4: Приготування напою",
                "Бариста готує замовлення",
                "Бариста варить каву на стійці. Ви можете клікати на баристу, щоб пришвидшити процес!"
            ),
            self.STEP_PICKUP: (
                "Крок 3/4: Видача страви",
                "Замовлення готове на стійці!",
                "Клікніть на готову чашку на стійці роздачі, щоб узяти її в лапки та нести гостю."
            ),
            self.STEP_SERVE: (
                "Крок 4/4: Подача гостю",
                "Подайте напій гостю",
                "Несіть свіжу каву клієнту — клікніть на столик №3, щоб пригостити котика!"
            ),
            self.STEP_COLLECT_COIN: (
                "Навчання успішно пройдено! :3",
                "Чудова робота, бос котиків!",
                "Ви заробили перші монети та освоїли всі правила кафе. Натисніть «Наступний день», щоб продовжити!"
            ),
            self.STEP_COMPLETE: (
                "Навчання успішно пройдено! :3",
                "Чудова робота, бос котиків!",
                "Ви заробили перші монети та освоїли всі правила кафе. Натисніть «Наступний день», щоб продовжити!"
            ),
        }

        pill_text, headline_text, desc_text = STEP_DATA.get(self.step, STEP_DATA[self.STEP_COMPLETE])

        # Бейдж імені Арі (з чіткою графічною іконкою лапки замість шрифтового емодзі)
        name_t = f_step_pill.render("Арі", True, C.WHITE)
        paw_ico = assets.image_by_height("ui_icon_paw", 13)
        nw = name_t.get_width() + 6 + paw_ico.get_width() + 14
        nh = 20
        nx, ny = card_x + 104, card_y + 12
        pygame.draw.rect(surface, C.TERRACOTTA, (nx, ny, nw, nh), border_radius=6)
        surface.blit(name_t, (nx + 7, ny + 2))
        surface.blit(paw_ico, (nx + 7 + name_t.get_width() + 5, ny + (nh - paw_ico.get_height()) // 2))

        # Бейдж поточного кроку
        p_t = f_step_pill.render(pill_text, True, C.DARK_SAGE)
        pw, ph = p_t.get_width() + 14, 20
        px = nx + nw + 8
        py = ny
        pygame.draw.rect(surface, (244, 240, 232), (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(surface, C.SAGE_GRAY, (px, py, pw, ph), 1, border_radius=6)
        surface.blit(p_t, (px + 7, py + 2))

        # Заголовок та детальний опис
        h_t = f_headline.render(headline_text, True, C.TEXT_DARK)
        surface.blit(h_t, (card_x + 104, card_y + 38))

        d_t = f_desc.render(desc_text, True, C.DARK_SAGE)
        surface.blit(d_t, (card_x + 104, card_y + 64))

        # -------------------------------------------------------------
        # 5. Кнопки управління
        # -------------------------------------------------------------
        # Кнопка «Пропустити навчання» у кутку екрана (показується тільки до фіналу)
        if self.step not in (self.STEP_COMPLETE, self.STEP_COLLECT_COIN):
            skip_hover = self.btn_skip_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, (255, 246, 238) if skip_hover else (255, 252, 248), self.btn_skip_rect, border_radius=8)
            pygame.draw.rect(surface, C.TERRACOTTA if skip_hover else C.SAGE_GRAY, self.btn_skip_rect, 1, border_radius=8)
            f_skip = assets.font_ui(11, bold=True)
            sk_t = f_skip.render("Пропустити >>", True, C.TERRACOTTA if skip_hover else (140, 130, 120))
            surface.blit(sk_t, sk_t.get_rect(center=self.btn_skip_rect.center))

        # На фінальному кроці: велика зручна зелена кнопка «Розпочати День 1»
        if self.step in (self.STEP_COMPLETE, self.STEP_COLLECT_COIN):
            pulse = math.sin(self._t * 4.0) * 0.15 + 0.85
            btn_h = self.btn_finish_rect.collidepoint(mouse_pos)
            bg = (90, 185, 110) if btn_h else (int(70 * pulse), int(160 * pulse), int(85 * pulse))
            pygame.draw.rect(surface, bg, self.btn_finish_rect, border_radius=12)
            pygame.draw.rect(surface, (40, 110, 55), self.btn_finish_rect, 2, border_radius=12)
            f_fin = assets.font_ui(15, bold=True)
            fin_t = assets.render_outlined(f_fin, "Наступний день >>", C.WHITE, (30, 70, 40), 1)
            surface.blit(fin_t, fin_t.get_rect(center=self.btn_finish_rect.center))
