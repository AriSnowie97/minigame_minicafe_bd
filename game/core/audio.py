"""
Менеджер звука MiniCafe.

Что умеет:
  * короткие эффекты (SFX) с индивидуальной громкостью, обрезкой «хвостов» и плавным затуханием;
  * защита от спама: кулдауны на звук и общий кулдаун на «кошачьи голоса»;
  * музыку для сцен с плавным (неблокирующим) переходом между треками;
  * фоновую атмосферу трёх комнат (зал / кухня / тераса) — громкость зависит от положения камеры;
  * выключатели «Звук» и «Музыка» из настроек.

Если звуковое устройство недоступно или файла нет — игра просто работает без звука.
"""
import array
import os
import random
import time

import pygame

from game.core.utils import resource_path

# ----------------------------------------------------------------------
# Описание звуков.
#   file     — имя файла в assets/sounds (без .wav)
#   vol      — базовая громкость (0..1); все эффекты специально сделаны тихими
#   trim     — обрезать звук до N секунд (с плавным затуханием), убирает длинные хвосты
#   gain     — программное усиление для слишком тихих файлов
#   cooldown — минимальная пауза между повторами этого звука (сек)
#   group    — общая пауза для группы звуков (например, «голоса» котиков)
# ----------------------------------------------------------------------
SFX = {
    # --- интерфейс ---
    "ui_hover":       dict(file="sfx_ui_hover",       vol=0.16, trim=0.14, cooldown=0.06),
    "ui_pressed":     dict(file="sfx_ui_pressed",     vol=0.28, trim=0.20),
    "ui_click":       dict(file="sfx_ui_click",       vol=0.40, trim=0.30, cooldown=0.05),
    "ui_open":        dict(file="sfx_ui_open",        vol=0.32, trim=0.70),
    "ui_disabled":    dict(file="sfx_ui_disabled",    vol=0.28, trim=0.45, cooldown=0.35),
    # --- деньги и результаты ---
    "coin":           dict(file="sfx_coin",           vol=0.34, trim=1.00),
    "coin_x2":        dict(file="sfx_coin_x2",        vol=0.34, trim=1.40),
    "cash_register":  dict(file="sfx_cash_register",  vol=0.34, trim=1.80),
    "star":           dict(file="sfx_star",           vol=0.30, trim=1.40),
    "order_complete": dict(file="sfx_order_complete", vol=0.34, trim=1.80),
    "order_fail":     dict(file="sfx_order_fail",     vol=0.28, trim=1.40, cooldown=1.0),
    # --- заказы ---
    "order_new":      dict(file="sfx_order_new",      vol=0.36, trim=1.00, cooldown=0.4),
    "order_ready":    dict(file="sfx_order_ready",    vol=0.32, trim=1.60, cooldown=0.8),
    "service_bell":   dict(file="sfx_service_bell",   vol=0.38, trim=1.30, cooldown=0.5),
    "oven_ding":      dict(file="sfx_oven_ding",      vol=0.34, trim=0.80, cooldown=0.5),
    "door_bell":      dict(file="sfx_door_bell",      vol=0.32, trim=1.60, cooldown=1.2),
    # --- кухня и бар (звук начала готовки) ---
    "coffee_machine": dict(file="sfx_coffee_machine", vol=0.38, trim=2.20, gain=2.0, cooldown=0.8),
    "milk_steam":     dict(file="sfx_milk_steam",     vol=0.22, trim=1.80, cooldown=0.8),
    "pan_sizzle":     dict(file="sfx_pan_sizzle",     vol=0.28, trim=2.00, cooldown=0.8),
    "pot_simmer":     dict(file="sfx_pot_simmer",     vol=0.34, trim=2.20, gain=3.0, cooldown=0.8),
    "chop":           dict(file="sfx_chop",           vol=0.20, trim=1.80, cooldown=0.8),
    "plate_place":    dict(file="sfx_plate_place",    vol=0.34, trim=1.00, cooldown=0.15),
    "cup_clink":      dict(file="sfx_cup_clink",      vol=0.34, trim=1.00, cooldown=0.15),
    "cat_steps":      dict(file="sfx_cat_steps",      vol=0.30, trim=1.20, gain=2.5, cooldown=2.5),
    # --- голоса котиков (общий кулдаун, чтобы не мяукали без конца) ---
    "cat_happy":      dict(file="sfx_cat_happy",      vol=0.38, trim=1.40, gain=1.5, group="voice"),
    "cat_wait":       dict(file="sfx_cat_wait",       vol=0.40, trim=1.20, gain=1.6, group="voice"),
    "cat_impatient":  dict(file="sfx_cat_impatient",  vol=0.36, trim=1.00, group="alert"),
}

# Кулдауны групп, сек
GROUP_COOLDOWN = {"voice": 3.5, "alert": 2.5}

# --- Атмосфера комнат (зацикленные фоновые шумы очень тихие в исходниках — усиливаем) ---
AMBIENCE = {
    "hall":    dict(file="amb_cafe",    gain=3.0, vol=0.55),
    "kitchen": dict(file="amb_kitchen", gain=3.5, vol=0.55),
    "terrace": dict(file="amb_terrace", gain=2.0, vol=0.55),
}

# --- Музыка ---
MUSIC = {
    "menu":    dict(file="music_menu",    vol=0.26),
    "game":    dict(file="music_game",    vol=0.16),   # в игре тише, чтобы были слышны эффекты
    "results": dict(file="music_results", vol=0.24),
}

# Какая музыка играет на какой сцене (None — продолжить то, что играет)
SCENE_MUSIC = {
    "main_menu": "menu",
    "settings":  None,
    "stats":     None,
    "cafe_hall": "game",
    "game_over": "results",
}

SFX_MASTER = 0.85         # общий множитель громкости эффектов
MUSIC_FADE_TIME = 0.7     # сек на затухание/нарастание музыки
AMBIENCE_FADE_SPEED = 1.6 # скорость сглаживания громкости атмосферы (1/сек)


class AudioManager:
    def __init__(self):
        self.enabled = False          # удалось ли инициализировать микшер
        self.sfx_on = True
        self.music_on = True

        self._sounds: dict = {}       # кэш обработанных Sound
        self._last_play: dict = {}    # name -> time
        self._group_last: dict = {}   # group -> time
        self._pending: list = []      # [[осталось_сек, name, mult]]

        # музыка
        self._music_target = None     # какую музыку хотим
        self._music_cur = None        # какая реально играет
        self._music_fade = 0.0        # 0..1 — текущая «огибающая» громкости

        # атмосфера
        self._amb_channels: dict = {}
        self._amb_target: dict = {}   # name -> желаемая громкость 0..1
        self._amb_level: dict = {}    # name -> текущая громкость 0..1
        self._amb_active = False

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------
    def init(self):
        """Инициализирует микшер. Безопасно вызывать повторно."""
        if self.enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(len(AMBIENCE))   # каналы 0..2 — под атмосферу
            self.enabled = True
        except Exception as e:           # нет звуковой карты и т.п.
            print(f"[Audio] Звук отключён: {e}")
            self.enabled = False

    def preload(self):
        """Заранее готовит все звуки (чтобы не было подвисаний в игре)."""
        if not self.enabled:
            return
        for name in SFX:
            self._get_sfx(name)
        for name in AMBIENCE:
            self._get_ambience(name)

    # ------------------------------------------------------------------
    # Загрузка и обработка
    # ------------------------------------------------------------------
    @staticmethod
    def _path(folder: str, file: str) -> str:
        return resource_path(os.path.join("assets", folder, f"{file}.wav"))

    def _load_processed(self, path: str, trim=None, gain=1.0, loop_xfade=0.0):
        """Загружает wav и (если формат 16 бит) обрезает, усиливает, сглаживает края."""
        if not os.path.exists(path):
            return None
        snd = pygame.mixer.Sound(path)
        init = pygame.mixer.get_init()
        if not init:
            return snd
        freq, fmt, channels = init
        if fmt != -16 or not (trim or gain != 1.0 or loop_xfade):
            return snd

        a = array.array("h")
        a.frombytes(snd.get_raw())
        ch = channels
        frames = len(a) // ch

        if trim:
            frames = min(frames, int(trim * freq))
            a = a[: frames * ch]

        if gain != 1.0:
            lo, hi = -32768, 32767
            a = array.array("h", [max(lo, min(hi, int(s * gain))) for s in a])

        if loop_xfade:
            # Бесшовная петля: хвост плавно перетекает в начало
            n = min(int(loop_xfade * freq), frames // 3)
            if n > 0:
                for i in range(n):
                    w = i / n
                    for c in range(ch):
                        head = i * ch + c
                        tail = (frames - n + i) * ch + c
                        a[head] = int(a[head] * w + a[tail] * (1.0 - w))
                a = a[: (frames - n) * ch]
                frames -= n
        else:
            # Короткое нарастание (без щелчка) и плавное затухание
            fi = min(int(0.004 * freq), frames)
            for i in range(fi):
                k = i / fi
                for c in range(ch):
                    a[i * ch + c] = int(a[i * ch + c] * k)
            if trim:
                fo = min(int(min(0.18, trim * 0.45) * freq), frames)
                for i in range(fo):
                    k = 1.0 - i / fo
                    idx = (frames - fo + i) * ch
                    for c in range(ch):
                        a[idx + c] = int(a[idx + c] * k)

        return pygame.mixer.Sound(buffer=a.tobytes())

    def _get_sfx(self, name: str):
        if name in self._sounds:
            return self._sounds[name]
        spec = SFX.get(name)
        snd = None
        if spec:
            try:
                snd = self._load_processed(self._path("sounds", spec["file"]),
                                           trim=spec.get("trim"), gain=spec.get("gain", 1.0))
                if snd:
                    snd.set_volume(spec["vol"])
            except Exception as e:
                print(f"[Audio] Не удалось загрузить {name}: {e}")
        self._sounds[name] = snd
        return snd

    def _get_ambience(self, name: str):
        key = f"amb:{name}"
        if key in self._sounds:
            return self._sounds[key]
        spec = AMBIENCE[name]
        snd = None
        try:
            snd = self._load_processed(self._path("sounds", spec["file"]),
                                       gain=spec["gain"], loop_xfade=0.4)
        except Exception as e:
            print(f"[Audio] Не удалось загрузить {name}: {e}")
        self._sounds[key] = snd
        return snd

    # ------------------------------------------------------------------
    # Эффекты
    # ------------------------------------------------------------------
    def play(self, name: str, mult: float = 1.0, delay: float = 0.0):
        """
        Проигрывает эффект.
        mult  — множитель громкости (например, 0.45 для событий в соседней комнате)
        delay — отложенный старт в секундах
        """
        if not (self.enabled and self.sfx_on) or mult <= 0.0:
            return
        if delay > 0:
            self._pending.append([delay, name, mult])
            return
        spec = SFX.get(name)
        if spec is None:
            return

        now = time.monotonic()
        cd = spec.get("cooldown", 0.0)
        if cd and now - self._last_play.get(name, -99.0) < cd:
            return
        group = spec.get("group")
        if group and now - self._group_last.get(group, -99.0) < GROUP_COOLDOWN.get(group, 0.0):
            return

        snd = self._get_sfx(name)
        if snd is None:
            return
        ch = snd.play()
        if ch is not None:
            # лёгкая случайность громкости — повторяющиеся звуки не «режут» слух
            ch.set_volume(min(1.0, SFX_MASTER * mult * random.uniform(0.9, 1.0)))
        self._last_play[name] = now
        if group:
            self._group_last[group] = now

    # ------------------------------------------------------------------
    # Музыка
    # ------------------------------------------------------------------
    def play_music(self, key):
        """Запросить музыку ('menu' | 'game' | 'results' | None=тишина). Переход плавный."""
        self._music_target = key

    def on_scene(self, scene_name: str):
        """Вызывается менеджером сцен при переключении."""
        if scene_name in SCENE_MUSIC and SCENE_MUSIC[scene_name] is not None:
            self.play_music(SCENE_MUSIC[scene_name])
        # Атмосфера кафе нужна только в игровой сцене
        self._amb_active = (scene_name == "cafe_hall")
        if not self._amb_active:
            self._amb_target = {n: 0.0 for n in AMBIENCE}

    def _effective_music_target(self):
        return self._music_target if (self.enabled and self.music_on) else None

    def _update_music(self, dt: float):
        target = self._effective_music_target()
        step = dt / MUSIC_FADE_TIME

        if self._music_cur != target:
            # затухаем, потом переключаем трек
            self._music_fade = max(0.0, self._music_fade - step * 1.4)
            if self._music_fade <= 0.0:
                pygame.mixer.music.stop()
                self._music_cur = None
                if target:
                    try:
                        path = self._path("music", MUSIC[target]["file"])
                        if os.path.exists(path):
                            pygame.mixer.music.load(path)
                            pygame.mixer.music.set_volume(0.0)
                            pygame.mixer.music.play(loops=-1)
                            self._music_cur = target
                    except Exception as e:
                        print(f"[Audio] Музыка не загрузилась: {e}")
                        self._music_target = None
        else:
            self._music_fade = min(1.0, self._music_fade + step)

        if self._music_cur:
            pygame.mixer.music.set_volume(MUSIC[self._music_cur]["vol"] * self._music_fade)

    # ------------------------------------------------------------------
    # Атмосфера комнат
    # ------------------------------------------------------------------
    def set_ambience(self, levels: dict):
        """levels: {'hall': 0..1, 'kitchen': 0..1, 'terrace': 0..1} — вклад каждой комнаты."""
        if self._amb_active:
            self._amb_target = {n: max(0.0, min(1.0, levels.get(n, 0.0))) for n in AMBIENCE}

    def _update_ambience(self, dt: float):
        allowed = self.enabled and self.sfx_on
        k = min(1.0, dt * AMBIENCE_FADE_SPEED)
        for i, (name, spec) in enumerate(AMBIENCE.items()):
            target = self._amb_target.get(name, 0.0) if allowed else 0.0
            cur = self._amb_level.get(name, 0.0)
            cur += (target - cur) * k
            if abs(cur - target) < 0.002:
                cur = target
            self._amb_level[name] = cur

            chan = self._amb_channels.get(name)
            if cur > 0.0 and (chan is None or not chan.get_busy()):
                snd = self._get_ambience(name)
                if snd is None:
                    continue
                chan = pygame.mixer.Channel(i)
                chan.play(snd, loops=-1)
                self._amb_channels[name] = chan
            if chan is not None:
                if cur > 0.0:
                    chan.set_volume(spec["vol"] * cur)
                elif chan.get_busy():
                    chan.stop()

    # ------------------------------------------------------------------
    # Общий апдейт (вызывается каждый кадр из main)
    # ------------------------------------------------------------------
    def update(self, dt: float):
        if not self.enabled:
            return
        if self._pending:
            still = []
            for item in self._pending:
                item[0] -= dt
                if item[0] <= 0:
                    self.play(item[1], item[2])
                else:
                    still.append(item)
            self._pending = still
        self._update_music(dt)
        self._update_ambience(dt)

    # ------------------------------------------------------------------
    # Настройки
    # ------------------------------------------------------------------
    def set_sfx_enabled(self, value: bool):
        self.sfx_on = bool(value)
        if not self.sfx_on:
            self._pending.clear()
            if self.enabled:
                for ch_i in range(len(AMBIENCE), pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(ch_i).stop()

    def set_music_enabled(self, value: bool):
        self.music_on = bool(value)


# Глобальный синглтон (как assets / locale)
audio = AudioManager()
