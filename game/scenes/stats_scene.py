"""
Екран «Статистика»: результати складних запитів до БД (JOIN, GROUP BY, підзапити, віконні функції)
через ORM. Дані беруться з PostgreSQL на Railway або (офлайн) з локальної SQLite.
"""
import pygame

from game.core.assets import assets
from game.core.localization import locale
from game.core.settings import C, HEIGHT, WIDTH
from game.ui.button import Button
from database import orm, stats

# --- Тексти екрана (uk / ru / en) ---
TEXT = {
    "title":   {"uk": "Статистика кафе", "ru": "Статистика кафе", "en": "Cafe statistics"},
    "source":  {"uk": "Джерело даних", "ru": "Источник данных", "en": "Data source"},
    "back":    {"uk": "Назад", "ru": "Назад", "en": "Back"},
    "refresh": {"uk": "Оновити", "ru": "Обновить", "en": "Refresh"},
    "demo":    {"uk": "Додати демо-дані", "ru": "Добавить демо-данные", "en": "Add demo data"},
    "empty":   {"uk": "Поки що немає замовлень. Зіграйте кілька днів або додайте демо-дані.",
                "ru": "Пока нет заказов. Сыграйте несколько дней или добавьте демо-данные.",
                "en": "No orders yet. Play a few days or add demo data."},
    "error":   {"uk": "Не вдалося отримати дані", "ru": "Не удалось получить данные", "en": "Could not load data"},
    "query":   {"uk": "Запит", "ru": "Запрос", "en": "Query"},
    # заголовки колонок
    "dish": {"uk": "Страва", "ru": "Блюдо", "en": "Dish"},
    "category": {"uk": "Категорія", "ru": "Категория", "en": "Category"},
    "sold": {"uk": "Продано", "ru": "Продано", "en": "Sold"},
    "revenue": {"uk": "Виручка", "ru": "Выручка", "en": "Revenue"},
    "rank": {"uk": "Місце в категорії", "ru": "Место в категории", "en": "Rank in category"},
    "day": {"uk": "День", "ru": "День", "en": "Day"},
    "paid": {"uk": "Оплачено", "ru": "Оплачено", "en": "Paid"},
    "cancelled": {"uk": "Скасовано", "ru": "Отменено", "en": "Cancelled"},
    "avg": {"uk": "Сер. чек", "ru": "Ср. чек", "en": "Avg check"},
    "running": {"uk": "Наростаючим", "ru": "Нарастающим", "en": "Running total"},
    "employee": {"uk": "Співробітник", "ru": "Сотрудник", "en": "Employee"},
    "position": {"uk": "Посада", "ru": "Должность", "en": "Position"},
    "share": {"uk": "Частка", "ru": "Доля", "en": "Share"},
    "table": {"uk": "Столик", "ru": "Столик", "en": "Table"},
    "place": {"uk": "Де", "ru": "Где", "en": "Where"},
    "product": {"uk": "Продукт", "ru": "Продукт", "en": "Product"},
    "unit": {"uk": "Од.", "ru": "Ед.", "en": "Unit"},
    "used": {"uk": "Витрачено", "ru": "Потрачено", "en": "Used"},
    "cost": {"uk": "Вартість", "ru": "Стоимость", "en": "Cost"},
    "cogs": {"uk": "Собівартість", "ru": "Себестоимость", "en": "Cost of goods"},
    "profit": {"uk": "Прибуток", "ru": "Прибыль", "en": "Profit"},
    "margin": {"uk": "Маржа", "ru": "Маржа", "en": "Margin"},
    # вкладки
    "tab_top": {"uk": "Топ страв", "ru": "Топ блюд", "en": "Top dishes"},
    "tab_days": {"uk": "По днях", "ru": "По дням", "en": "By day"},
    "tab_staff": {"uk": "Персонал", "ru": "Персонал", "en": "Staff"},
    "tab_tables": {"uk": "Столики", "ru": "Столики", "en": "Tables"},
    "tab_cats": {"uk": "Категорії", "ru": "Категории", "en": "Categories"},
    "tab_prod": {"uk": "Продукти", "ru": "Продукты", "en": "Products"},
    "tab_profit": {"uk": "Прибуток", "ru": "Прибыль", "en": "Profit"},
    "tab_guests": {"uk": "Гості", "ru": "Гости", "en": "Guests"},
    "guest": {"uk": "Гість-котик", "ru": "Гость-котик", "en": "Cat guest"},
    "left": {"uk": "Пішли без страви", "ru": "Ушли без блюда", "en": "Left unserved"},
    "prepared": {"uk": "Приготував", "ru": "Приготовил", "en": "Prepared"},
    "served": {"uk": "Розніс", "ru": "Разнёс", "en": "Served"},
    "place_rank": {"uk": "Місце", "ru": "Место", "en": "Rank"},
}


def tr(key: str) -> str:
    entry = TEXT.get(key, {})
    return entry.get(locale.current) or entry.get("uk") or key


def _int(v):
    return str(int(round(v))) if isinstance(v, (int, float)) else str(v)


def _money(v):
    return f"{v:.0f}" if isinstance(v, (int, float)) else str(v)


def _dec(v):
    return f"{v:.1f}" if isinstance(v, (int, float)) else str(v)


def _pct(v):
    return f"{v:.1f}%" if isinstance(v, (int, float)) else str(v)


def _day(v):
    return "—" if not v else _int(v)


def _txt(v):
    return str(v)


def _breed(v):
    from database.seed import GUEST_BREEDS
    return GUEST_BREEDS.get(v, str(v))


# (ключ вкладки, функція запиту, колонки [(ключ заголовка, ширина, вирівнювання, формат)], опис SQL-прийомів)
TABS = [
    ("tab_top", stats.top_dishes,
     [("dish", 300, "l", _txt), ("category", 220, "l", _txt), ("sold", 130, "r", _int),
      ("revenue", 150, "r", _money), ("rank", 200, "r", _int)],
     "JOIN 4 таблиць · GROUP BY · HAVING · RANK() OVER (PARTITION BY категорія)"),
    ("tab_days", stats.revenue_by_gameday,
     [("day", 120, "l", _day), ("paid", 170, "r", _int), ("cancelled", 170, "r", _int),
      ("revenue", 170, "r", _money), ("avg", 170, "r", _dec), ("running", 200, "r", _money)],
     "Підзапит (сума кожного замовлення) · CASE-агрегати · SUM() OVER (ORDER BY день)"),
    ("tab_staff", stats.employee_stats,
     [("employee", 270, "l", _txt), ("position", 150, "l", _txt), ("prepared", 150, "r", _int),
      ("served", 130, "r", _int), ("cancelled", 130, "r", _int), ("revenue", 150, "r", _money)],
     "Корельовані скалярні підзапити (приготував / розніс / скасовано) · CASE за посадою"),
    ("tab_tables", stats.table_stats,
     [("table", 150, "l", _int), ("place", 200, "l", _txt), ("paid", 200, "r", _int),
      ("revenue", 200, "r", _money), ("avg", 200, "r", _dec)],
     "LEFT JOIN · COUNT(DISTINCT CASE …) · похідний показник (виручка / кількість)"),
    ("tab_cats", stats.category_stats,
     [("category", 320, "l", _txt), ("sold", 200, "r", _int), ("revenue", 220, "r", _money),
      ("share", 220, "r", _pct)],
     "JOIN 4 таблиць · GROUP BY · SUM(SUM(...)) OVER () — частка категорії"),
    ("tab_prod", stats.product_usage,
     [("product", 320, "l", _txt), ("unit", 120, "l", _txt), ("used", 220, "r", _dec),
      ("cost", 220, "r", _money)],
     "JOIN 5 таблиць (замовлення → страви → склад → продукти) · GROUP BY · HAVING"),
    ("tab_guests", stats.guest_stats,
     [("guest", 220, "l", _breed), ("paid", 130, "r", _int), ("cancelled", 130, "r", _int),
      ("revenue", 140, "r", _money), ("avg", 130, "r", _dec), ("left", 190, "r", _pct),
      ("place_rank", 110, "r", _int)],
     "GROUP BY окрас · COUNT(DISTINCT CASE …) · HAVING · RANK() OVER (ORDER BY виручка)"),
    ("tab_profit", stats.dish_profit,
     [("dish", 280, "l", _txt), ("sold", 110, "r", _int), ("revenue", 140, "r", _money),
      ("cogs", 170, "r", _money), ("profit", 140, "r", _money), ("margin", 130, "r", _pct)],
     "Підзапит: собівартість страви зі складу · LEFT JOIN · GROUP BY · різниця агрегатів"),
]

PANEL = pygame.Rect(60, 40, WIDTH - 120, HEIGHT - 80)
ROW_H = 33
MAX_ROWS = 10


class StatsScene:
    def __init__(self, manager):
        self.manager = manager
        self.back_to = "main_menu"
        self.back_kwargs = {}
        self.tab = 0
        self._data = {}
        self._error = ""
        self._has_orders = False
        self._t = 0.0

        self.btn_back = Button(pygame.Rect(PANEL.x + 30, PANEL.bottom - 64, 170, 44), tr("back"), font_size=20)
        self.btn_refresh = Button(pygame.Rect(PANEL.right - 200, PANEL.bottom - 64, 170, 44), tr("refresh"), font_size=20)
        self.btn_demo = Button(pygame.Rect(PANEL.centerx - 130, PANEL.bottom - 64, 260, 44), tr("demo"), font_size=20)
        self.tab_rects = []
        tab_w = (PANEL.width - 60) // len(TABS)
        for i in range(len(TABS)):
            self.tab_rects.append(pygame.Rect(PANEL.x + 30 + i * tab_w, PANEL.y + 78, tab_w - 6, 36))

    # ------------------------------------------------------------------
    def on_enter(self, back: str = "main_menu", back_kwargs: dict = None, **kwargs):
        self.back_to = back
        self.back_kwargs = back_kwargs or {}
        self.btn_back.set_text(tr("back"))
        self.btn_refresh.set_text(tr("refresh"))
        self.btn_demo.set_text(tr("demo"))
        self._reload()

    def _reload(self):
        """Заново виконує запит поточної вкладки (і перевіряє, чи є в БД замовлення)"""
        self._error = ""
        try:
            self._has_orders = stats.orders_count() > 0
            self._data[self.tab] = TABS[self.tab][1]()[:MAX_ROWS]
        except Exception as e:                      # мережа/БД недоступна — не ламаємо гру
            self._error = f"{tr('error')}: {str(e).splitlines()[0][:80]}"
            self._data[self.tab] = []

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.switch(self.back_to, **self.back_kwargs)
            return

        if self.btn_back.handle_event(event):
            self.manager.switch(self.back_to, **self.back_kwargs)
            return
        if self.btn_refresh.handle_event(event):
            self._reload()
            return
        if not self._has_orders and self.btn_demo.handle_event(event):
            try:
                stats.add_demo_data()
            except Exception as e:
                self._error = f"{tr('error')}: {str(e).splitlines()[0][:80]}"
            else:
                self._reload()
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for i, r in enumerate(self.tab_rects):
                if r.collidepoint(event.pos) and i != self.tab:
                    self.tab = i
                    self._reload()
                    return

    def update(self, dt: float):
        self._t += dt
        for b in (self.btn_back, self.btn_refresh, self.btn_demo):
            b.update(dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        bg = assets.image("bg_settings")
        if not hasattr(self, "_cached_bg"):
            scaled = pygame.transform.smoothscale(bg, (1280, 1280))
            self._cached_bg = scaled.subsurface((0, 100, 1280, 720)).copy()
        surface.blit(self._cached_bg, (0, 0))
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 20, 20, 110))
        surface.blit(dim, (0, 0))

        # Панель
        panel = pygame.Surface(PANEL.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 250, 240, 245), panel.get_rect(), border_radius=20)
        pygame.draw.rect(panel, C.TERRACOTTA, panel.get_rect(), 3, border_radius=20)
        surface.blit(panel, PANEL.topleft)

        f_title = assets.font_title(30)
        title = assets.render_outlined(f_title, tr("title"), C.WHITE, (60, 45, 38), 2)
        banner = pygame.Rect(PANEL.x + 30, PANEL.y + 14, 340, 54)
        pygame.draw.rect(surface, C.DARK_SAGE, banner, border_radius=14)
        pygame.draw.rect(surface, C.TERRACOTTA, banner, 2, border_radius=14)
        surface.blit(title, title.get_rect(center=banner.center))

        f_small = assets.font_ui(14)
        src = f_small.render(f"{tr('source')}: {orm.backend_name()}", True, C.DARK_SAGE)
        surface.blit(src, (PANEL.right - src.get_width() - 34, PANEL.y + 30))

        # Вкладки
        f_tab = assets.font_ui(15, bold=True)
        mouse = pygame.mouse.get_pos()
        for i, r in enumerate(self.tab_rects):
            active = i == self.tab
            col = C.TERRACOTTA if active else ((205, 198, 186) if r.collidepoint(mouse) else (232, 225, 214))
            pygame.draw.rect(surface, col, r, border_radius=10)
            pygame.draw.rect(surface, C.DARK_SAGE, r, 1, border_radius=10)
            t = f_tab.render(tr(TABS[i][0]), True, C.WHITE if active else C.TEXT_DARK)
            surface.blit(t, t.get_rect(center=r.center))

        # Таблиця
        _, _, cols, note = TABS[self.tab]
        x0 = PANEL.x + 40
        y = PANEL.y + 132
        f_head = assets.font_ui(15, bold=True)
        f_cell = assets.font_ui(16)
        pygame.draw.rect(surface, C.DARK_SAGE, (x0 - 10, y - 4, sum(c[1] for c in cols) + 20, ROW_H), border_radius=8)
        cx = x0
        for key, width, align, _fmt in cols:
            t = f_head.render(tr(key), True, C.CREAM)
            surface.blit(t, (cx if align == "l" else cx + width - t.get_width(), y + 2))
            cx += width
        y += ROW_H + 2

        rows = self._data.get(self.tab, [])
        if self._error:
            msg = assets.font_ui(17, bold=True).render(self._error, True, C.PATIENCE_LOW)
            surface.blit(msg, (x0, y + 20))
        elif not rows:
            msg = assets.font_ui(17, bold=True).render(tr("empty"), True, C.DARK_SAGE)
            surface.blit(msg, (x0, y + 20))
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                pygame.draw.rect(surface, (244, 238, 228), (x0 - 10, y - 3, sum(c[1] for c in cols) + 20, ROW_H - 2), border_radius=6)
            cx = x0
            for (key, width, align, fmt), val in zip(cols, row):
                t = f_cell.render(fmt(val), True, C.TEXT_DARK)
                if t.get_width() > width - 10:
                    t = t.subsurface((0, 0, width - 10, t.get_height()))
                surface.blit(t, (cx if align == "l" else cx + width - t.get_width(), y))
                cx += width
            y += ROW_H

        # Опис використаних SQL-прийомів
        f_note = assets.font_ui(14)
        n = f_note.render(f"{tr('query')}: {note}", True, C.DARK_SAGE)
        surface.blit(n, (PANEL.x + 40, PANEL.bottom - 108))

        # Кнопки
        self.btn_back.draw(surface)
        self.btn_refresh.draw(surface)
        if not self._has_orders:
            self.btn_demo.draw(surface)
