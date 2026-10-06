"""
MiniCafe 🐱☕ — точка входа
"""
import os
import sys
import pygame

# Убеждаемся, что корень проекта в PYTHONPATH (нужно для PyInstaller)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from game.core.settings   import WIDTH, HEIGHT, FPS, TITLE
from game.core.assets     import assets
from game.core.localization import locale
from game.scenes.scene_manager import SceneManager
from game.scenes.main_menu     import MainMenuScene
from game.scenes.cafe_hall     import CafeHallScene
from game.scenes.settings_scene import SettingsScene
from game.scenes.game_over     import GameOverScene
from game.scenes.stats_scene    import StatsScene
from database.connection       import get_connection


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)

    # Иконка окна (если есть)
    for icon_name in ("logo.png", "logo_minicafe.png"):
        icon_path = os.path.join(ROOT, "assets", "sprites", icon_name)
        if os.path.exists(icon_path):
            icon_src = pygame.image.load(icon_path)
            iw, ih = icon_src.get_size()
            k = 64 / max(iw, ih)
            icon_s = pygame.transform.smoothscale(icon_src, (max(1, int(iw * k)), max(1, int(ih * k))))
            icon = pygame.Surface((64, 64), pygame.SRCALPHA)
            icon.blit(icon_s, icon_s.get_rect(center=(32, 32)))
            pygame.display.set_icon(icon)
            break

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock  = pygame.time.Clock()

    # Пробуем подключиться к БД
    get_connection()

    # Создаём менеджер и регистрируем сцены
    manager = SceneManager()
    manager.add("main_menu",  MainMenuScene(manager))
    manager.add("cafe_hall",  CafeHallScene(manager))
    manager.add("settings",   SettingsScene(manager))
    manager.add("game_over",  GameOverScene(manager))
    manager.add("stats",      StatsScene(manager))
    manager.switch("main_menu")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # delta-time в секундах

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            manager.handle_event(event)

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    from database.connection import close as db_close
    db_close()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
