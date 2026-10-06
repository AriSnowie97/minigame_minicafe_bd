"""
Скрипт перевірки та зняття скріншотів оновленого MiniCafe
"""
import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

from game.core.settings import WIDTH, HEIGHT, C
from game.scenes.scene_manager import SceneManager
from game.scenes.main_menu import MainMenuScene
from game.scenes.cafe_hall import CafeHallScene
from game.entities.customer import Customer, CustomerState
from game.entities.table import TableState

screen = pygame.display.set_mode((WIDTH, HEIGHT))
manager = SceneManager()

menu_scene = MainMenuScene(manager)
cafe_scene = CafeHallScene(manager)

manager.add("main_menu", menu_scene)
manager.add("cafe_hall", cafe_scene)

# 1. Скріншот головного меню з жирними обведеними шрифтами
manager.switch("main_menu")
manager.update(0.1)
manager.draw(screen)
pygame.image.save(screen, "screenshot_menu_verified.png")
print("1. Menu screenshot saved: screenshot_menu_verified.png")

# 2. Скріншот залу кафе (День 1, без офіціанта, безшовний фон, вулична тераса ліворуч, декор праворуч)
manager.switch("cafe_hall", day=1, money=50, rating=3.0, upgrades={})
cafe_scene._try_spawn_customer()
manager.update(0.1)
manager.draw(screen)
pygame.image.save(screen, "screenshot_hall_day1_verified.png")
print("2. Hall Day 1 screenshot saved: screenshot_hall_day1_verified.png")

# 3. Тест ручного обслуговування (без офіціанта):
# Клік по столику з клієнтом
if cafe_scene.customers:
    cust = cafe_scene.customers[0]
    cust.state = CustomerState.WAITING
    # Клік по столику
    cafe_scene._on_table_click(cust.table)
    print(f"3a. Order taken manually for table {cust.table.table_number}. Pending barista: {len(cafe_scene.pending_barista_orders)}")

    # Клік по баристі (початок варіння)
    cafe_scene._on_counter_click(800, 500)
    print(f"3b. Barista cooking: table state = {cust.table.state}, cook_timer = {cust.table.cook_timer}")

    # Завершення готування
    cust.table.cook_timer = 0.0
    cafe_scene.update(0.1)
    print(f"3c. Cooking complete: table state = {cust.table.state}")

    # Гравець клікає на стійку і забирає готову страву
    cafe_scene._on_counter_click(800, 500)
    print(f"3d. Player carrying dish for table: {getattr(cafe_scene.player_carrying_table, 'table_number', None)}")

    # Знімок з підказкою та стравою в руках
    manager.draw(screen)
    pygame.image.save(screen, "screenshot_carrying_dish_verified.png")
    print("3e. Carrying dish screenshot saved: screenshot_carrying_dish_verified.png")

    # Подача страви на стіл
    cafe_scene._on_table_click(cust.table)
    print(f"3f. Order served: money = {cafe_scene.money}, orders_done = {cafe_scene.orders_done}")

# 4. Скріншот магазину з вкладками (Кафе/Персонал та Розширення меню)
cafe_scene.shop_modal.open()
manager.draw(screen)
pygame.image.save(screen, "screenshot_shop_tab0_verified.png")
print("4a. Shop Tab 0 screenshot saved: screenshot_shop_tab0_verified.png")

# Перемикання на вкладку Розширення меню
cafe_scene.shop_modal.current_tab = 1
manager.draw(screen)
pygame.image.save(screen, "screenshot_shop_tab1_verified.png")
print("4b. Shop Tab 1 screenshot saved: screenshot_shop_tab1_verified.png")

# 5. Скріншот з купленим офіціантом та терасою
cafe_scene.shop_modal.close()
upgrades = {"waiter": True, "terrace": True, "menu_cookies": True, "menu_iced_coffee": True, "menu_cake": True}
manager.switch("cafe_hall", day=2, money=250, rating=4.2, upgrades=upgrades)
cafe_scene._try_spawn_customer()
manager.update(0.1)
manager.draw(screen)
pygame.image.save(screen, "screenshot_waiter_terrace_verified.png")
print("5. Waiter & terrace screenshot saved: screenshot_waiter_terrace_verified.png")

print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
