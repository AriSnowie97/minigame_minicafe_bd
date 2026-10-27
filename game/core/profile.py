"""
Профіль гравця: збереження імені та локальних налаштувань.
Дозволяє гравцям, які завантажили гру із сайту, вводити своє ім'я
для онлайн та локальної таблиці лідерів у базі даних.
"""
import json
import os

_PROFILE_FILE = "player_profile.json"
_DEFAULT_NAME = "Котик Гравець"


def _load_profile() -> dict:
    try:
        if os.path.exists(_PROFILE_FILE):
            with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_profile(data: dict):
    try:
        with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_player_name() -> str:
    data = _load_profile()
    name = data.get("name", _DEFAULT_NAME)
    return name.strip() if name and name.strip() else _DEFAULT_NAME


def set_player_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean:
        clean = _DEFAULT_NAME
    clean = clean[:24]
    data = _load_profile()
    data["name"] = clean
    _save_profile(data)
    return clean


def get_last_seen_version() -> str:
    """Отримати версію гри, для якої гравець вже бачив новини оновлення."""
    data = _load_profile()
    return str(data.get("last_seen_version", "")).strip()


def set_last_seen_version(version: str):
    """Позначити версію як переглянуту, щоб не показувати новини повторно."""
    data = _load_profile()
    data["last_seen_version"] = (version or "").strip()
    _save_profile(data)
