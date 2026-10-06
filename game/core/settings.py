# =========================================================
# MiniCafe — Константы и настройки игры
# =========================================================

# --- Экран ---
WIDTH  = 1280
HEIGHT = 720
FPS    = 60
TITLE  = "MiniCafe 🐱☕"

# --- Макет кімнати та ізометричні координати (відповідність мокапу 100%) ---
ROOM_SIZE = 750
ROOM_X    = (WIDTH - ROOM_SIZE) // 2   # 265
ROOM_Y    = 40

def to_screen(rx: float, ry: float) -> tuple:
    """Перетворює координати з простору фону 2048x2048 у координати екрана 1280x720."""
    scale = ROOM_SIZE / 2048.0
    return int(ROOM_X + rx * scale), int(ROOM_Y + ry * scale)

def s_scale(size_2048: float) -> int:
    """Масштабує розмір елемента з простору 2048 відповідно до розміру кімнати."""
    return max(1, int(size_2048 * (ROOM_SIZE / 2048.0)))

# Точні координати столиків відповідно до макета:
TABLE_COORDINATES = {
    # --- Основний зал кафе (room: "hall") ---
    1: (480, 460),  # Столик 1 — задній ряд зліва
    2: (660, 445),  # Столик 2 — задній ряд справа
    3: (495, 540),  # Столик 3 — передній ряд зліва
    4: (622, 553),  # Столик 4 — передній ряд по центру/справа
    9: (540, 600),  # Столик 9 — зал, нижній кут ліворуч
    10: (698, 620), # Столик 10 — зал, нижній кут праворуч

    # --- Літня тераса кафе (room: "terrace") за макетом користувача ---
    5: (473, 560),  # Столик 5 — тераса, зліва біля рослини
    6: (587, 633),  # Столик 6 — тераса, передній план
    7: (667, 472),  # Столик 7 — тераса, по центру біля перил
    8: (814, 541),  # Столик 8 — тераса, праворуч біля перил
}

# Столики, у которых стул стоит справа сзади (у остальных — слева)
CHAIR_RIGHT_TABLES = (1, 2, 3, 10)

# --- Изометрическая сетка ---
ISO_TILE_W  = 80    # Ширина тайла (горизонталь)
ISO_TILE_H  = 40    # Высота тайла (вертикаль)
ISO_ORIGIN_X = WIDTH  // 2  # Начало координат X
ISO_ORIGIN_Y = 220          # Начало координат Y

GRID_COLS = 10
GRID_ROWS = 8

# --- Игровые таймеры ---
DAY_DURATION       = 180   # секунд в игровом дне
CUSTOMER_PATIENCE  = 35    # секунд до ухода клиента
COOKING_SPEED      = 0.4   # множитель скорости готовки (< 1 = быстрее)

# --- Монеты ---
RATING_BONUS = {5: 50, 4: 30, 3: 10, 2: 0, 1: -10}

# =========================================================
# Палитра цветов (от пользователя)
# =========================================================
class C:
    # --- Интерьер и UI ---
    LIGHT_GRAY  = (209, 210, 212)  # #D1D2D4
    SAGE_GRAY   = (144, 148, 131)  # #909483
    DARK_SAGE   = (97,  102,  87)  # #616657
    DUSTY_ROSE  = (193, 147, 134)  # #C19386
    TERRACOTTA  = (178,  92,  64)  # #B25C40

    # --- Котики ---
    CAT_BROWN   = (111,  91,  66)  # #6F5B42
    CAT_BEIGE   = (181, 168, 146)  # #B5A892
    CAT_LIGHT   = (210, 210, 209)  # #D2D2D1
    CAT_MID     = (190, 187, 180)  # #BEBBB4
    CAT_DARK    = ( 21,  22,  10)  # #15160A

    # --- Базовые ---
    WHITE  = (255, 255, 255)
    BLACK  = (  0,   0,   0)
    CREAM  = (255, 248, 235)
    TRANS  = (  0,   0,   0,   0)

    # --- Производные UI ---
    BTN_BG     = (193, 147, 134)   # DUSTY_ROSE
    BTN_HOVER  = (210, 165, 150)
    BTN_PRESS  = (155, 115, 100)
    BTN_BORDER = (178,  92,  64)   # TERRACOTTA

    PANEL_BG     = ( 97, 102,  87)  # DARK_SAGE
    PANEL_BORDER = (144, 148, 131)  # SAGE_GRAY
    PANEL_LIGHT  = (120, 125, 108)

    # --- Пол (тайлы) ---
    TILE_A   = (222, 216, 205)
    TILE_B   = (210, 204, 192)
    TILE_TOP = (230, 225, 215)
    TILE_BORDER = (180, 174, 162)

    # --- Стены ---
    WALL_LIGHT = (220, 218, 215)
    WALL_DARK  = (190, 188, 184)

    # --- Текст ---
    TEXT_LIGHT  = (255, 248, 235)
    TEXT_DARK   = ( 35,  30,  25)
    TEXT_ACCENT = (178,  92,  64)   # TERRACOTTA

    # --- Состояния клиентов ---
    PATIENCE_GOOD = ( 95, 175,  95)
    PATIENCE_MID  = (220, 180,  60)
    PATIENCE_LOW  = (210,  80,  60)

    # --- Уведомления ---
    NOTIF_GOOD = ( 95, 175,  95)
    NOTIF_BAD  = (210,  80,  60)
    NOTIF_INFO = (193, 147, 134)

# --- Позиции столиков на изо-сетке (col, row) ---
# Соответствует CafeTables из БД (1..6)
TABLE_GRID_POSITIONS = {
    1: (2, 2),   # Table 1 — задний ряд слева
    2: (5, 2),   # Table 2 — задний ряд по центру
    3: (7, 4),   # Table 3 — перед стойкой с большим простором
    4: (1, 4),   # Table 4 — средний ряд слева
    5: (4, 4),   # Table 5 — центр зала (VIP-кресло)
    6: (3, 6),   # Table 6 — передний ряд слева
}

# --- Цвета котиков для разных клиентов ---
CUSTOMER_CAT_COLORS = [
    (111,  91,  66),  # коричневый
    (181, 168, 146),  # бежевый
    (210, 210, 209),  # светло-серый
    (190, 187, 180),  # серый
]

# --- ID блюд из БД и ключи локализации ---
MENU_ITEM_KEYS = {
    1: "coffee",
    2: "tea",
    3: "cookies",
    4: "iced_latte",
    5: "cake",
    6: "bruschetta",
    7: "syrnyky",
    8: "omelette",
    9: "caesar",
    10: "tiramisu",
    11: "borscht",
    12: "latte",
    13: "takeaway_coffee",
    14: "croissant",
    15: "cappuccino",
}

# --- Соответствие блюд спрайтам из assets/sprites/item_*.png ---
MENU_ITEM_SPRITES = {
    1: "item_coffee_cup",      # Кава
    2: "item_black_tea",       # Чай
    3: "item_cookies",         # Печиво
    4: "item_iced_coffee",     # Айс лате
    5: "item_cake",            # Тортик
    6: "item_bruschetta",      # Брускета (кухня)
    7: "item_syrniki",         # Сирники (кухня)
    8: "item_omelette_bacon",  # Омлет з беконом (кухня)
    9: "item_caesar_salad",    # Салат Цезар (кухня)
    10: "item_tiramisu",       # Тірамісу (кухня)
    11: "item_borscht",        # Борщ (кухня)
    12: "item_latte",          # Лате
    13: "item_takeaway_cup",   # Кава з собою
    14: "item_croissant",      # Круасан
    15: "item_cappuccino",     # Капучино (розширене меню)
}

def get_item_sprite(item_id_or_name) -> str:
    """Возвращает имя спрайта item_* для переданного ID или названия."""
    if isinstance(item_id_or_name, int) and item_id_or_name in MENU_ITEM_SPRITES:
        return MENU_ITEM_SPRITES[item_id_or_name]
    name = str(item_id_or_name).lower()
    if any(k in name for k in ["ice", "айс", "холод", "лате", "latte"]):
        return "item_iced_coffee"
    if any(k in name for k in ["cook", "печ", "печен"]):
        return "item_cookies"
    if any(k in name for k in ["cake", "торт", "тірам", "сирн", "десерт"]):
        return "item_cake"
    if any(k in name for k in ["tea", "чай", "takeaway"]):
        return "item_takeaway_cup"
    return "item_coffee_cup"
