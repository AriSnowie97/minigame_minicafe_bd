"""
Загрузчик ассетов.
Пробует загрузить PNG-спрайты; если файл не найден — рисует placeholder.
"""
import os
import pygame
from game.core.utils import resource_path
from game.core.settings import C


class Assets:
    def __init__(self):
        self._images: dict = {}
        self._fonts: dict  = {}

    # ------------------------------------------------------------------
    # Изображения
    # ------------------------------------------------------------------
    def image(self, name: str, size: tuple = None) -> pygame.Surface:
        """
        Загружает sprites/<name>.png или возвращает placeholder.
        size=(w,h) — опциональное масштабирование.
        """
        key = (name, size)
        if key in self._images:
            return self._images[key]

        # Проверяем кэш-директорию (оптимизированные и обрезанные спрайты)
        cache_path = resource_path(os.path.join("assets", ".cache", f"{name}.png"))
        if os.path.exists(cache_path) and not name.startswith("bg_"):
            surf = pygame.image.load(cache_path)
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
        else:
            found_path = None
            for ext in (".png", ".jpeg", ".jpg"):
                p = resource_path(os.path.join("assets", "sprites", f"{name}{ext}"))
                if os.path.exists(p):
                    found_path = p
                    break
                p2 = resource_path(os.path.join("assets", f"{name}{ext}"))
                if os.path.exists(p2):
                    found_path = p2
                    break

            if found_path:
                surf = pygame.image.load(found_path)
                if pygame.display.get_surface():
                    surf = surf.convert_alpha()
                # Автоматическая обрезка пустых прозрачных краев вокруг спрайта (кроме фонов)
                if not name.startswith("bg_"):
                    bbox = surf.get_bounding_rect()
                    if bbox.width > 4 and bbox.height > 4:
                        surf = surf.subsurface(bbox).copy()
                    # Сохраняем в .cache для моментальной последующей загрузки
                    try:
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        save_surf = surf
                        if max(surf.get_size()) > 512:
                            w, h = surf.get_size()
                            scale = 512.0 / max(w, h)
                            save_surf = pygame.transform.smoothscale(surf, (int(w * scale), int(h * scale)))
                        pygame.image.save(save_surf, cache_path)
                    except Exception:
                        pass
            else:
                surf = self._make_placeholder(name, size or (64, 64))

        if size and surf.get_size() != size:
            surf = pygame.transform.smoothscale(surf, size)

        self._images[key] = surf
        return surf

    def image_by_height(self, name: str, height: int) -> pygame.Surface:
        """Возвращает спрайт, смасштабированный до указанной высоты с сохранением пропорций (кэшируется)."""
        base = self.image(name)
        if base.get_height() == 0:
            return base
        w = max(1, int(height * (base.get_width() / base.get_height())))
        return self.image(name, (w, height))

    def image_by_width(self, name: str, width: int) -> pygame.Surface:
        """Возвращает спрайт, смасштабированный до указанной ширины с сохранением пропорций (кэшируется)."""
        base = self.image(name)
        if base.get_width() == 0:
            return base
        h = max(1, int(width * (base.get_height() / base.get_width())))
        return self.image(name, (width, h))

    def _make_placeholder(self, name: str, size: tuple) -> pygame.Surface:
        """Цветной прямоугольник с текстом вместо спрайта"""
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((*C.DUSTY_ROSE, 180))
        pygame.draw.rect(surf, C.TERRACOTTA, surf.get_rect(), 2)
        font = pygame.font.SysFont("Arial", max(10, size[1] // 5), bold=True)
        label = font.render(name[:10], True, C.WHITE)
        surf.blit(label, label.get_rect(center=(size[0] // 2, size[1] // 2)))
        return surf

    # ------------------------------------------------------------------
    # Шрифты
    # ------------------------------------------------------------------
    def font(self, name: str, size: int, bold: bool = True) -> pygame.font.Font:
        """
        Загружает fonts/<name>.ttf или системный шрифт как fallback.
        Поддерживает Nunito (UI/основной текст) и Rubik (заголовки).
        По умолчанию bold=True для лучшей читаемости.
        """
        key = (name, size, bold)
        if key in self._fonts:
            return self._fonts[key]

        # --- Маппинг имён шрифтов ---
        _FONT_MAP = {
            "nunito":      ("Nunito-Regular", "Nunito-Bold"),
            "rubik":       ("Rubik-Regular",  "Rubik-Bold"),
            "font_main":   ("Nunito-Regular", "Nunito-Bold"),
            "font_title":  ("Rubik-Regular",  "Rubik-Bold"),
            "font_ui":     ("Nunito-Regular", "Nunito-Bold"),
        }
        if name in _FONT_MAP:
            fname = _FONT_MAP[name][1 if bold else 0]
        else:
            fname = name

        path = resource_path(os.path.join("assets", "fonts", f"{fname}.ttf"))
        if not os.path.exists(path):
            # Попробуем без суффикса
            path = resource_path(os.path.join("assets", "fonts", f"{name}.ttf"))

        if os.path.exists(path):
            f = pygame.font.Font(path, size)
            if bold:
                f.set_bold(True)
        else:
            # Fallback системный шрифт
            sys_name = "Arial" if "ui" in name else "Segoe UI"
            f = pygame.font.SysFont(sys_name, size, bold=bold)

        self._fonts[key] = f
        return f

    # ------------------------------------------------------------------
    # Удобные шрифты по назначению
    # ------------------------------------------------------------------
    def font_title(self, size: int, bold: bool = True) -> pygame.font.Font:
        """Rubik — заголовки и крупные надписи."""
        return self.font("font_title", size, bold=bold)

    def font_main(self, size: int, bold: bool = True) -> pygame.font.Font:
        """Nunito — основной текст."""
        return self.font("font_main", size, bold=bold)

    def font_ui(self, size: int, bold: bool = True) -> pygame.font.Font:
        """Nunito — элементы интерфейса (HUD, кнопки, уведомления)."""
        return self.font("font_ui", size, bold=bold)

    # ------------------------------------------------------------------
    # Отрисовка текста с четкой обводкой (Stroke / Outline)
    # ------------------------------------------------------------------
    @staticmethod
    def render_outlined(font: pygame.font.Font, text: str, color: tuple,
                        outline_color: tuple = (40, 32, 28),
                        outline_width: int = 2) -> pygame.Surface:
        """Рендерит текст с четкой контрастной обводкой для максимальной читаемости."""
        base = font.render(text, True, color)
        if outline_width <= 0:
            return base
        w = base.get_width() + outline_width * 2
        h = base.get_height() + outline_width * 2
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        outline = font.render(text, True, outline_color)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    surf.blit(outline, (dx + outline_width, dy + outline_width))
        surf.blit(base, (outline_width, outline_width))
        return surf


# --- Глобальный синглтон (инициализируется после pygame.init()) ---
assets = Assets()
