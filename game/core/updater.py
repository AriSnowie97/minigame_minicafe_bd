"""
Система перевірки оновлень та новини версії (Changelog / What's New).
- Безпечно у фоновому потоці перевіряє GitHub Releases на наявність нових версій.
- Нагадує гравцю оновити гру, якщо вийшла нова версія, та надає посилання на завантаження.
- Після оновлення гри показує красиве вікно з новинами та списком змін.
"""
import json
import re
import threading
import urllib.request
import urllib.error
import webbrowser
from typing import Optional, Dict, Any, List

from game.core.settings import GAME_VERSION, GITHUB_REPO
from game.core.profile import get_last_seen_version, set_last_seen_version


def parse_version(tag: str) -> tuple:
    """Перетворює рядок версії ('v1.1.0' або '1.2') на числовий кортеж для порівняння."""
    if not tag:
        return (0, 0, 0)
    cleaned = re.sub(r'^[^\d]*', '', tag.strip())
    parts = []
    for p in cleaned.split('.'):
        digits = re.match(r'^\d+', p)
        if digits:
            parts.append(int(digits.group(0)))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


# Локальні новини для поточної версії (працюють навіть без підключення до мережі)
CHANGELOGS: Dict[str, Dict[str, Any]] = {
    "v1.1.0": {
        "tag": "v1.1.0",
        "title": "Оновлення v1.1.0: Служба доставки, склад та рекорди!",
        "subtitle": "Ласкаво просимо до свіжого оновлення MiniCafe! Ось головні нововведення:",
        "items": [
            {
                "icon": "🚚",
                "title": "Служба доставки продуктів",
                "desc": "До великого вікна залу під'їжджає фірмова вантажівка, а котик-вантажник у кепці заносить ящики з припасами на кухню!"
            },
            {
                "icon": "📦",
                "title": "Склад та облік залишків страв",
                "desc": "Тепер у страв та напоїв є запаси! Вони закінчуються при замовленнях; докуповуйте поставки (+10 шт) прямо в меню магазину."
            },
            {
                "icon": "🏆",
                "title": "Профіль гравця та Топ лідерів",
                "desc": "Введіть своє ім'я у головному меню та змагайтеся з іншими гравцями в таблиці рекордів за звання найкращого кафе!"
            },
            {
                "icon": "💰",
                "title": "Фінансовий облік витрат",
                "desc": "Фіксація витрат на закупівлі та детальний розрахунок чистого прибутку кафе (Виручка - Витрати) з накопичувальним підсумком."
            },
            {
                "icon": "🪑",
                "title": "Поліпшення залу та інтерфейсу",
                "desc": "Котики за столиками тепер сидять обличчям усередину залу, а готові страви ідеально вирівняні на стійці роздачі."
            }
        ]
    }
}


class UpdateChecker:
    """Фоновий агент для перевірки нових версій гри на GitHub."""

    def __init__(self):
        self.current_version = GAME_VERSION
        self.latest_version: Optional[str] = None
        self.release_title: Optional[str] = None
        self.release_url: Optional[str] = None
        self.release_notes: Optional[str] = None
        self.download_url: Optional[str] = None
        self.has_update = False
        self.is_checking = False
        self.checked = False
        self.error: Optional[str] = None

    def check_async(self):
        """Запустити неблокуючу перевірку у фоновому потоці."""
        if self.is_checking or self.checked:
            return
        self.is_checking = True
        thread = threading.Thread(target=self._run_check, daemon=True, name="MiniCafe-UpdateCheck")
        thread.start()

    def _run_check(self):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MiniCafe-Game-Client",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    remote_tag = data.get("tag_name", "").strip()
                    if remote_tag:
                        self.latest_version = remote_tag
                        self.release_title = data.get("name", f"MiniCafe {remote_tag}")
                        self.release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/tag/{remote_tag}")
                        self.release_notes = data.get("body", "")

                        # Шукаємо пряме посилання на MiniCafe.exe у assets
                        for asset in data.get("assets", []):
                            if asset.get("name") == "MiniCafe.exe":
                                self.download_url = asset.get("browser_download_url")
                                break
                        if not self.download_url:
                            self.download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{remote_tag}/MiniCafe.exe"

                        curr_tuple = parse_version(self.current_version)
                        remote_tuple = parse_version(remote_tag)
                        if remote_tuple > curr_tuple:
                            self.has_update = True
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_checking = False
            self.checked = True

    def open_update_page(self):
        """Відкрити сторінку релізу або завантаження в браузері гравця."""
        target_url = self.release_url or f"https://github.com/{GITHUB_REPO}/releases/latest"
        try:
            webbrowser.open(target_url)
        except Exception:
            pass

    def open_direct_download(self):
        """Відкрити пряме завантаження MiniCafe.exe у браузері."""
        url = self.download_url or f"https://github.com/{GITHUB_REPO}/releases/download/{self.latest_version or self.current_version}/MiniCafe.exe"
        try:
            webbrowser.open(url)
        except Exception:
            pass


# Глобальний екземпляр
updater = UpdateChecker()


def should_show_whats_new() -> bool:
    """
    Перевіряє, чи потрібно автоматично відкрити новини версії після оновлення:
    якщо гравець ще не бачив новини саме поточної версії (наприклад, щойно оновився).
    """
    last_seen = get_last_seen_version()
    return last_seen != GAME_VERSION


def mark_whats_new_seen():
    """Позначити поточну версію як переглянуту."""
    set_last_seen_version(GAME_VERSION)


def get_current_changelog() -> Dict[str, Any]:
    """Отримати новини поточної версії."""
    return CHANGELOGS.get(GAME_VERSION, {
        "tag": GAME_VERSION,
        "title": f"Оновлення {GAME_VERSION}",
        "subtitle": "Ось головні зміни та нововведення гри:",
        "items": []
    })
