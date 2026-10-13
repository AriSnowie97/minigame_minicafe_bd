"""
MiniCafe 🐱☕ — точка входа
"""
import os
import sys
import pygame

# Убеждаемся, что корень проекта в PYTHONPATH (нужно для PyInstaller)
ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from game.core.settings   import WIDTH, HEIGHT, FPS, TITLE
from game.core.assets     import assets
from game.core.localization import locale
from game.core.audio      import audio
from game.scenes.scene_manager import SceneManager
from game.scenes.main_menu     import MainMenuScene
from game.scenes.cafe_hall     import CafeHallScene
from game.scenes.settings_scene import SettingsScene
from game.scenes.game_over     import GameOverScene
from game.scenes.stats_scene    import StatsScene
from database.connection       import get_connection


def main():
    # На Windows привязываем процесс к собственному AppUserModelID,
    # чтобы панель задач группировала окно как отдельное приложение со своей иконкой,
    # а не как дефолтный python.exe со значком дискеты
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AriSnowie.MiniCafe.Game.1.0")
        except Exception:
            pass

    pygame.init()
    pygame.display.set_caption(TITLE)

    # Звук: микшер + подготовка всех эффектов (без звуковой карты игра работает тихо)
    audio.init()
    audio.preload()

    # Иконка окна (если есть)
    for icon_path in (
        os.path.join(ROOT, "assets", "icon.png"),
        os.path.join(ROOT, "assets", "icon.ico"),
        os.path.join(ROOT, "assets", "sprites", "logo_minicafe.png"),
        os.path.join(ROOT, "assets", "sprites", "ui_icon_paw.png"),
    ):
        if os.path.exists(icon_path):
            try:
                icon_src = pygame.image.load(icon_path)
                iw, ih = icon_src.get_size()
                k = 64 / max(iw, ih)
                icon_s = pygame.transform.smoothscale(icon_src, (max(1, int(iw * k)), max(1, int(ih * k))))
                icon = pygame.Surface((64, 64), pygame.SRCALPHA)
                icon.blit(icon_s, icon_s.get_rect(center=(32, 32)))
                pygame.display.set_icon(icon)
                break
            except Exception:
                pass

    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    # Для Windows: явно регистрируем HICON через WM_SETICON и SetClassLongPtrW для панели задач
    if sys.platform == "win32":
        try:
            import ctypes
            ico_file = os.path.join(ROOT, "assets", "icon.ico")
            if not os.path.exists(ico_file) and hasattr(sys, "_MEIPASS"):
                ico_file = os.path.join(sys._MEIPASS, "assets", "icon.ico")
            if os.path.exists(ico_file):
                user32 = ctypes.windll.user32
                wm_info = pygame.display.get_wm_info()
                hwnd = wm_info.get("window")
                if hwnd:
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x0010
                    hicon_big = user32.LoadImageW(0, ico_file, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                    hicon_small = user32.LoadImageW(0, ico_file, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if hicon_big:
                        WM_SETICON = 0x0080
                        user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small or hicon_big)
                        user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_big)
                        if hasattr(user32, "SetClassLongPtrW"):
                            user32.SetClassLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
                            user32.SetClassLongPtrW.restype = ctypes.c_void_p
                            user32.SetClassLongPtrW(hwnd, -14, hicon_big)
                            user32.SetClassLongPtrW(hwnd, -34, hicon_small or hicon_big)
        except Exception:
            pass

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
        audio.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    from database.connection import close as db_close
    db_close()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
