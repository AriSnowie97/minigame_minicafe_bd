"""
Менеджер сцен — переключение между экранами игры.
"""
import pygame
from typing import Dict


class SceneManager:
    def __init__(self):
        self._scenes: Dict[str, object] = {}
        self._current: str = ""
        self._next: str = ""

    def add(self, name: str, scene):
        self._scenes[name] = scene

    def switch(self, name: str, **kwargs):
        """Переключить на сцену. kwargs передаются в on_enter()."""
        if name not in self._scenes:
            print(f"[SceneManager] Unknown scene: {name}")
            return
        if self._current and self._current in self._scenes:
            if hasattr(self._scenes[self._current], "on_exit"):
                self._scenes[self._current].on_exit()
        self._current = name
        scene = self._scenes[name]
        if hasattr(scene, "on_enter"):
            scene.on_enter(**kwargs)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        scene = self._scenes.get(self._current)
        if scene:
            scene.handle_event(event)

    def update(self, dt: float):
        scene = self._scenes.get(self._current)
        if scene:
            scene.update(dt)

    def draw(self, surface: pygame.Surface):
        scene = self._scenes.get(self._current)
        if scene:
            scene.draw(surface)
