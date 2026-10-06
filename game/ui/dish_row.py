"""
Ряд иконок блюд (до 4 штук) — для заказа с несколькими позициями.
"""
import pygame
from game.core.assets import assets
from game.core.settings import get_item_sprite


def dish_images(items, height: int):
    """Иконки блюд заказа в виде списка поверхностей"""
    return [assets.image_by_height(get_item_sprite(it.get("id", 1)), height) for it in items]


def blit_dish_row(surface: pygame.Surface, items, cx: int, cy: int, height: int = 22, gap: int = 2):
    """Рисует блюда заказа в один ряд, выровняв по центру (cx, cy)"""
    imgs = dish_images(items, height)
    if not imgs:
        return
    total = sum(i.get_width() for i in imgs) + gap * (len(imgs) - 1)
    x = cx - total // 2
    for im in imgs:
        surface.blit(im, im.get_rect(midleft=(x, cy)))
        x += im.get_width() + gap
