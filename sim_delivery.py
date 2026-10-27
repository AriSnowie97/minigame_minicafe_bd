import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

from game.core.settings import WIDTH, HEIGHT
from game.scenes.scene_manager import SceneManager
from game.scenes.cafe_hall import CafeHallScene
from game.entities.delivery import DeliveryManager, DeliveryOrder

screen = pygame.display.set_mode((WIDTH, HEIGHT))
manager = SceneManager()
cafe_scene = CafeHallScene(manager)
manager.add("cafe_hall", cafe_scene)
manager.switch("cafe_hall", day=1, money=1000, rating=5.0)

# Simulate full update loop
dm = cafe_scene.delivery_manager
dm.order_delivery(1, "Чай", is_chef=False, quantity=10, icon="dish_tea")

print("Initial state:", dm.state)
states_seen = []
# Run 15 seconds of simulation
dt = 0.05
for step in range(300):
    cafe_scene.update(dt)
    if dm.state not in states_seen:
        states_seen.append(dm.state)
        print(f"Step {step} (t={step*dt:.2f}s): entered {dm.state}, courier_pos=({dm.courier_x:.1f}, {dm.courier_y:.1f})")

print("States seen:", states_seen)
