"""
Утилиты: пути к ресурсам (работает и в режиме разработки, и в .exe)
"""
import sys
import os


def resource_path(relative: str) -> str:
    """
    Возвращает абсолютный путь к ресурсу.
    Работает корректно и при запуске через Python, и из PyInstaller .exe.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller временная папка
        return os.path.join(sys._MEIPASS, relative)
    # Корень проекта — два уровня выше game/core/
    root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(root, relative)


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def lerp(a: float, b: float, t: float) -> float:
    """Линейная интерполяция"""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def lerp_tuple(a: tuple, b: tuple, t: float) -> tuple:
    """Lerp между двумя цветами/точками"""
    return tuple(int(lerp(ai, bi, t)) for ai, bi in zip(a, b))
