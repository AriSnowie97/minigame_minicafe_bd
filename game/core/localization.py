"""
Система локализации (uk / ru / en)
Использование:
    from game.core.localization import locale
    locale.set_lang('uk')
    text = locale.get('menu.play')
"""
import json
import os
from typing import Dict, Any

from game.core.utils import resource_path


class Localization:
    LANGUAGES = ["uk", "ru", "en"]

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._current: str = "uk"
        self._load_all()

    # ------------------------------------------------------------------
    def _load_all(self):
        for lang in self.LANGUAGES:
            path = resource_path(os.path.join("assets", "locales", f"{lang}.json"))
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self._data[lang] = json.load(f)
            else:
                print(f"[i18n] Locale not found: {path}")

        if not self._data:
            # Минимальный встроенный фолбэк
            self._data["en"] = {
                "menu": {"play": "Play", "settings": "Settings", "quit": "Quit"},
            }

    # ------------------------------------------------------------------
    def set_lang(self, lang: str):
        if lang in self._data:
            self._current = lang

    def cycle(self):
        """Переключить на следующий язык по кругу"""
        langs = [l for l in self.LANGUAGES if l in self._data]
        if not langs:
            return
        idx = (langs.index(self._current) + 1) % len(langs) if self._current in langs else 0
        self._current = langs[idx]

    # ------------------------------------------------------------------
    def get(self, key: str, **kwargs) -> str:
        """
        Получить строку по точечному ключу, напр. 'menu.play'.
        Поддерживает форматирование: locale.get('notify.order_done', coins=150)
        """
        data = self._data.get(self._current) or self._data.get("en") or {}
        val: Any = data
        for part in key.split("."):
            if isinstance(val, dict):
                val = val.get(part, None)
            else:
                val = None
                break

        if val is None:
            return key  # Возвращаем ключ как fallback

        if isinstance(val, str) and kwargs:
            try:
                return val.format(**kwargs)
            except (KeyError, ValueError):
                return val
        return str(val) if not isinstance(val, str) else val

    # ------------------------------------------------------------------
    @property
    def current(self) -> str:
        return self._current

    @property
    def lang_name(self) -> str:
        return self._data.get(self._current, {}).get("lang_name", self._current.upper())

    @property
    def available(self) -> list:
        return [l for l in self.LANGUAGES if l in self._data]


# --- Глобальный синглтон ---
locale = Localization()
