"""
Система автоматичного оновлення гри та новини версії (Changelog / What's New).
- Безпечно у фоновому потоці перевіряє GitHub Releases на наявність нових версій.
- Підтримує як API GitHub, так і безлімітний прямий fallback через redirect.
- Вбудоване завантаження оновлення MiniCafe.exe у грі з відображенням прогресу (МБ/%/швидкість).
- 1-клік безшовна заміна виконуваного файлу на Windows через фоновий bat-скрипт без блокувань.
- Показ вікна новин та списку змін (Changelog) після кожного оновлення гри.
"""
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Optional, Dict, Any, List, Callable

from game.core.settings import GAME_VERSION, GITHUB_REPO
from game.core.profile import get_last_seen_version, set_last_seen_version


def safe_open_url(url: str):
    """Безпечне відкриття URL у браузері користувача на будь-якій системі."""
    if not url:
        return
    try:
        if sys.platform == "win32" and hasattr(os, "startfile"):
            os.startfile(url)
            return
    except Exception:
        pass
    try:
        webbrowser.open(url)
    except Exception:
        pass


def parse_version(tag: str) -> tuple:
    """Перетворює рядок версії ('v1.1.1' або '1.2') на числовий кортеж для порівняння."""
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


# Локальні новини для версій гри (працюють навіть офлайн)
CHANGELOGS: Dict[str, Dict[str, Any]] = {
    "v1.1.1": {
        "tag": "v1.1.1",
        "title": "Оновлення v1.1.1: Навчання (День 0), двері доставки та авто-оновлення!",
        "subtitle": "Свіже оновлення MiniCafe! Ось головні нововведення цього релізу:",
        "items": [
            {
                "icon": "ari",
                "title": "Інтерактивне навчання з Арі (День 0)",
                "desc": "Нова наставниця Арі проведе вас через перший підготовчий день! Покрокові підказки зі стрілочками та авторськими емоціями допоможуть легко освоїти всі кроки від замовлення до розрахунку."
            },
            {
                "icon": "truck",
                "title": "Покращений маршрут доставки",
                "desc": "Котик-вантажник більше не ходить під меблями! Він акуратно прямує лівим проходом прямо до дверей службового входу з кавовою табличкою."
            },
            {
                "icon": "star",
                "title": "Вбудоване авто-оновлення гри",
                "desc": "MiniCafe тепер завантажує нові версії гри прямо всередині програми з прогрес-баром і перезапускається в один клік без ручного скачування з браузера."
            },
            {
                "icon": "coin",
                "title": "Зручний інтерфейс завершення дня",
                "desc": "Поміняно місцями кнопки в кінці зміни: перехід до наступного дня тепер праворуч під рукою, а повернення до меню - ліворуч."
            },
            {
                "icon": "chair",
                "title": "Виправлення шрифтів та стабільність",
                "desc": "Замінено текстові символи на чіткі векторні та растрові іконки, оптимізовано роботу з базою даних та поліпшено сумісність Windows."
            }
        ]
    },
    "v1.1.0": {
        "tag": "v1.1.0",
        "title": "Оновлення v1.1.0: Служба доставки, склад та рекорди!",
        "subtitle": "Головні нововведення попереднього великого релізу:",
        "items": [
            {
                "icon": "truck",
                "title": "Служба доставки продуктів",
                "desc": "До великого вікна залу під'їжджає фірмова вантажівка, а котик-вантажник заносить ящики з припасами на кухню!"
            },
            {
                "icon": "box",
                "title": "Склад та облік залишків страв",
                "desc": "У страв та напоїв є запаси! Вони закінчуються при замовленнях; докуповуйте поставки прямо в магазині."
            },
            {
                "icon": "trophy",
                "title": "Профіль гравця та Топ лідерів",
                "desc": "Введіть своє ім'я у головному меню та змагайтеся з іншими гравцями в таблиці рекордів за звання найкращого кафе!"
            },
            {
                "icon": "coin",
                "title": "Фінансовий облік витрат",
                "desc": "Фіксація витрат на закупівлі та детальний розрахунок чистого прибутку кафе з накопичувальним підсумком."
            },
            {
                "icon": "chair",
                "title": "Поліпшення залу та інтерфейсу",
                "desc": "Котики за столиками сидять обличчям усередину залу, а готові страви ідеально вирівняні на стійці роздачі."
            }
        ]
    }
}


class UpdateChecker:
    """
    Система контролю оновлень: перевірка, потокове фонове завантаження та
    безшовна заміна виконуваного файлу гри на Windows.
    """

    def __init__(self):
        self.current_version = GAME_VERSION
        self.latest_version: Optional[str] = None
        self.release_title: Optional[str] = None
        self.release_url: Optional[str] = None
        self.release_notes: Optional[str] = None
        self.download_url: Optional[str] = None
        self.remote_file_size: int = 0
        self.has_update = False
        self.is_checking = False
        self.checked = False
        self.error: Optional[str] = None

        # Стан процесу завантаження
        # 'idle' -> 'downloading' -> 'completed' або 'error'
        self.download_state: str = "idle"
        self.download_progress: float = 0.0  # 0.0 .. 1.0
        self.downloaded_bytes: int = 0
        self.total_bytes: int = 0
        self.download_speed: float = 0.0     # байт/сек
        self.download_error: Optional[str] = None
        self.download_temp_path: Optional[str] = None
        self._cancel_download: bool = False
        self._download_thread: Optional[threading.Thread] = None
        self.restart_ready: bool = False
        self._on_check_complete: Optional[Callable[[bool], None]] = None

    # ------------------------------------------------------------------
    # Властивості для зручного відображення в UI
    # ------------------------------------------------------------------
    @property
    def downloaded_mb(self) -> float:
        return self.downloaded_bytes / (1024.0 * 1024.0)

    @property
    def total_mb(self) -> float:
        return max(1.0, self.total_bytes / (1024.0 * 1024.0))

    @property
    def speed_kbps(self) -> float:
        return self.download_speed / 1024.0

    @property
    def speed_mbps(self) -> float:
        return self.download_speed / (1024.0 * 1024.0)

    @property
    def speed_str(self) -> str:
        if self.speed_mbps >= 1.0:
            return f"{self.speed_mbps:.1f} МБ/с"
        return f"{self.speed_kbps:.0f} КБ/с"

    # ------------------------------------------------------------------
    # Перевірка наявності нових версій
    # ------------------------------------------------------------------
    def check_async(self):
        """Фоновий запуск при старті гри."""
        self.check(force=False)

    def check(self, force: bool = False, on_complete: Optional[Callable[[bool], None]] = None):
        """Запустити перевірку оновлень. Якщо force=True, перевіряє навіть повторно."""
        if self.is_checking:
            return
        if self.checked and not force:
            if on_complete:
                on_complete(self.has_update)
            return

        self.is_checking = True
        self.error = None
        self._on_check_complete = on_complete

        thread = threading.Thread(
            target=self._run_check,
            daemon=True,
            name="MiniCafe-UpdateCheck"
        )
        thread.start()

    def _run_check(self):
        remote_tag = None
        release_name = None
        release_url = None
        release_body = None
        download_url = None
        file_size = 0

        # Спроба 1: Офіційний GitHub REST API
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "MiniCafe-Game-Client/1.1",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    remote_tag = data.get("tag_name", "").strip()
                    release_name = data.get("name", f"MiniCafe {remote_tag}")
                    release_url = data.get("html_url")
                    release_body = data.get("body", "")

                    for asset in data.get("assets", []):
                        if asset.get("name") == "MiniCafe.exe":
                            download_url = asset.get("browser_download_url")
                            file_size = asset.get("size", 0)
                            break
        except Exception as e:
            # Якщо API rate limit (403) або тимчасова помилка мережі
            self.error = str(e)

        # Спроба 2 (Резервна безлімітна): Отримання фінального редіректу GitHub
        if not remote_tag:
            try:
                redirect_url = f"https://github.com/{GITHUB_REPO}/releases/latest"
                redir_req = urllib.request.Request(
                    redirect_url,
                    method="HEAD",
                    headers={"User-Agent": "MiniCafe-Game-Client/1.1"}
                )
                with urllib.request.urlopen(redir_req, timeout=10.0) as resp:
                    final_url = resp.geturl()
                    if "/tag/" in final_url:
                        remote_tag = final_url.split("/tag/")[-1].strip().split("/")[0]
                        release_name = f"MiniCafe {remote_tag}"
                        release_url = final_url
                        download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{remote_tag}/MiniCafe.exe"
            except Exception as e2:
                if not self.error:
                    self.error = str(e2)

        if remote_tag:
            self.latest_version = remote_tag
            self.release_title = release_name or f"MiniCafe {remote_tag}"
            self.release_url = release_url or f"https://github.com/{GITHUB_REPO}/releases/tag/{remote_tag}"
            self.release_notes = release_body or ""
            if not download_url:
                download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{remote_tag}/MiniCafe.exe"
            self.download_url = download_url
            self.remote_file_size = file_size

            curr_tuple = parse_version(self.current_version)
            remote_tuple = parse_version(remote_tag)
            self.has_update = (remote_tuple > curr_tuple)
            self.error = None

        self.is_checking = False
        self.checked = True

        if self._on_check_complete and callable(self._on_check_complete):
            try:
                self._on_check_complete(self.has_update)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Вбудоване фонове завантаження MiniCafe.exe з прогрес-баром
    # ------------------------------------------------------------------
    def start_download(self):
        """Почати завантаження MiniCafe.exe у фоновому потоці з відстеженням прогресу."""
        if self.download_state == "downloading":
            return
        if not self.download_url:
            self.download_error = "Посилання для завантаження відсутнє"
            self.download_state = "error"
            return

        self.download_state = "downloading"
        self.download_progress = 0.0
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.download_speed = 0.0
        self.download_error = None
        self._cancel_download = False
        self.restart_ready = False

        self._download_thread = threading.Thread(
            target=self._run_download,
            daemon=True,
            name="MiniCafe-DownloadThread"
        )
        self._download_thread.start()

    def cancel_download(self):
        """Скасувати поточне завантаження."""
        self._cancel_download = True

    def _run_download(self):
        url = self.download_url
        is_frozen = getattr(sys, "frozen", False)
        target_dir = os.path.dirname(sys.executable) if is_frozen else os.path.abspath("dist")
        temp_file = os.path.join(target_dir, "MiniCafe_update.tmp")

        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(temp_file, "wb") as f:
                pass
        except Exception:
            temp_file = os.path.join(tempfile.gettempdir(), "MiniCafe_update.tmp")

        self.download_temp_path = temp_file

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MiniCafe-Game-Client/1.1"}
            )
            start_time = time.time()
            last_speed_time = start_time
            bytes_since_last_speed = 0

            with urllib.request.urlopen(req, timeout=20) as resp:
                content_len = resp.headers.get("Content-Length")
                if content_len:
                    self.total_bytes = int(content_len)
                else:
                    self.total_bytes = self.remote_file_size or int(260 * 1024 * 1024)

                chunk_size = 128 * 1024  # 128 KB
                with open(temp_file, "wb") as f:
                    while True:
                        if self._cancel_download:
                            self.download_state = "idle"
                            try:
                                os.remove(temp_file)
                            except Exception:
                                pass
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        self.downloaded_bytes += len(chunk)
                        bytes_since_last_speed += len(chunk)

                        now = time.time()
                        dt = now - last_speed_time
                        if dt >= 0.4:
                            self.download_speed = bytes_since_last_speed / dt
                            bytes_since_last_speed = 0
                            last_speed_time = now

                        if self.total_bytes > 0:
                            self.download_progress = min(0.99, self.downloaded_bytes / self.total_bytes)

            # Перевірка цілісності: розмір > 5 МБ та валідний PE заголовок (MZ)
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 5 * 1024 * 1024:
                raise Exception("Файл оновлення пошкоджений або має замалий розмір")

            with open(temp_file, "rb") as f:
                if f.read(2) != b"MZ":
                    raise Exception("Файл не є дійсним бінарним файлом Windows (.exe)")

            self.download_progress = 1.0
            self.download_state = "completed"
            self.restart_ready = True

        except Exception as e:
            self.download_error = str(e)
            self.download_state = "error"
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Безшовне оновлення та перезапуск на Windows
    # ------------------------------------------------------------------
    def apply_update_and_restart(self):
        """Застосувати завантажене оновлення та перезапустити гру."""
        import subprocess
        import pygame

        if not self.restart_ready or not self.download_temp_path or not os.path.exists(self.download_temp_path):
            return False

        is_frozen = getattr(sys, "frozen", False)
        if not is_frozen:
            # Якщо запущено з Python-коду: копіюємо в dist/MiniCafe.exe
            target_exe = os.path.abspath(os.path.join("dist", "MiniCafe.exe"))
            try:
                import shutil
                os.makedirs(os.path.dirname(target_exe), exist_ok=True)
                shutil.copyfile(self.download_temp_path, target_exe)
                self.download_state = "completed"
                return True
            except Exception as e:
                self.download_error = f"Помилка копіювання: {e}"
                return False

        target_exe = os.path.abspath(sys.executable)
        temp_exe = os.path.abspath(self.download_temp_path)

        # Створюємо скрипт minicafe_updater.bat у тимчасовій теці
        bat_path = os.path.join(tempfile.gettempdir(), "minicafe_updater.bat")
        bat_content = f"""@echo off
chcp 65001 >nul
setlocal
set "PID={os.getpid()}"
set "NEW_EXE={temp_exe}"
set "TARGET_EXE={target_exe}"

set /a ATTEMPTS=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
tasklist /fi "PID eq %PID%" 2>nul | findstr /i "%PID%" >nul
if errorlevel 1 goto PROCESS_GONE
set /a ATTEMPTS+=1
if %ATTEMPTS% geq 20 goto KILL_OLD
goto WAIT_LOOP

:KILL_OLD
taskkill /f /pid %PID% >nul 2>&1
timeout /t 1 /nobreak >nul

:PROCESS_GONE
timeout /t 1 /nobreak >nul

copy /y "%NEW_EXE%" "%TARGET_EXE%" >nul 2>&1
if errorlevel 1 (
    move /y "%NEW_EXE%" "%TARGET_EXE%" >nul 2>&1
)

if exist "%NEW_EXE%" del /f /q "%NEW_EXE%" >nul 2>&1

start "" "%TARGET_EXE%"

(goto) 2>nul & del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as bf:
            bf.write(bat_content)

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=flags,
            close_fds=True
        )

        try:
            pygame.quit()
        except Exception:
            pass
        sys.exit(0)

    # ------------------------------------------------------------------
    # Запасні посилання для відкриття у браузері
    # ------------------------------------------------------------------
    def open_update_page(self):
        """Відкрити сторінку релізу на GitHub у браузері."""
        target_url = self.release_url or f"https://github.com/{GITHUB_REPO}/releases/latest"
        safe_open_url(target_url)

    def open_direct_download(self):
        """Відкрити пряме посилання на MiniCafe.exe у браузері."""
        url = self.download_url or f"https://github.com/{GITHUB_REPO}/releases/download/{self.latest_version or self.current_version}/MiniCafe.exe"
        safe_open_url(url)


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
