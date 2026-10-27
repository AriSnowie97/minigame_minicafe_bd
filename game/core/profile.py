"""
Профіль гравця: збереження імені та локальних налаштувань.
Дозволяє гравцям, які завантажили гру із сайту, вводити своє ім'я
для онлайн та локальної таблиці лідерів у базі даних.
"""
import json
import os

_PROFILE_FILE = "player_profile.json"
_DEFAULT_NAME = "Котик Гравець"


def get_player_name() -> str:
    try:
        if os.path.exists(_PROFILE_FILE):
            with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                name = data.get("name", _DEFAULT_NAME)
                return name.strip() if name and name.strip() else _DEFAULT_NAME
    except Exception:
        pass
    return _DEFAULT_NAME


def set_player_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean:
        clean = _DEFAULT_NAME
    # Обмеження довжини імені
    clean = clean[:24]
    try:
        with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump({"name": clean}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return clean
