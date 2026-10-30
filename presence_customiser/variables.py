"""Dynamic variables (time, CPU, active window, VS Code project, Spotify...)."""
from __future__ import annotations

import ctypes
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime

try:
    import psutil
except ImportError:  # the app stays usable, with fewer variables
    psutil = None

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
EDITOR_SUFFIXES = (
    "Visual Studio Code", "Cursor", "VSCodium", "Windsurf", "Sublime Text",
    "PyCharm", "IntelliJ IDEA", "WebStorm", "CLion", "Notepad++",
)
SPOTIFY_IDLE_TITLES = {"spotify", "spotify free", "spotify premium"}


class Context:
    """State shared between ticks (start time, current profile, small cache)."""

    def __init__(self) -> None:
        self.app_start = time.time()
        self.profile_since = time.time()
        self._cache: dict = {}

    def cached(self, key: str, ttl: float, fn):
        now = time.time()
        hit = self._cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
        value = fn()
        self._cache[key] = (now, value)
        return value


def humanize(seconds: float) -> str:
    sec = int(max(0, seconds))
    if sec < 60:
        return f"{sec}s"
    minutes = sec // 60
    if minutes < 60:
        return f"{minutes}min"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}"
    days, hours = divmod(hours, 24)
    return f"{days}j {hours}h"


# ------------------------------------------------------------ active window

def _win_process_name(pid: int) -> str:
    if psutil is None:
        return ""
    try:
        return psutil.Process(pid).name()
    except Exception:
        return ""


def _win_active_window() -> tuple[str, str]:
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", ""
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return _win_process_name(pid.value), buf.value


def _linux_active_window() -> tuple[str, str]:
    try:
        title = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                               capture_output=True, text=True, timeout=0.5).stdout.strip()
        pid = subprocess.run(["xdotool", "getactivewindow", "getwindowpid"],
                             capture_output=True, text=True, timeout=0.5).stdout.strip()
        return (_win_process_name(int(pid)) if pid.isdigit() else ""), title
    except Exception:
        return "", ""


def get_active_window() -> tuple[str, str]:
    """(process name, window title) of the foreground window."""
    try:
        if sys.platform == "win32":
            return _win_active_window()
        if sys.platform.startswith("linux"):
            return _linux_active_window()
    except Exception:
        pass
    return "", ""


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    if sys.platform != "win32":
        return 0.0
    try:
        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
            return max(0.0, (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000.0)  # type: ignore[attr-defined]
    except Exception:
        pass
    return 0.0


def _win_titles_of(process_name: str) -> list[str]:
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    titles: list[str] = []
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _win_process_name(pid.value).lower() == process_name.lower():
            titles.append(buf.value)
        return True

    user32.EnumWindows(enum_proc(callback), 0)
    return titles


def get_spotify_track() -> str:
    """Current track ("Artist - Title") from the Spotify window, else ""."""
    if sys.platform != "win32":
        return ""
    try:
        for title in _win_titles_of("Spotify.exe"):
            if title.strip().lower() not in SPOTIFY_IDLE_TITLES and " - " in title:
                return title.strip()
    except Exception:
        pass
    return ""


def parse_editor_title(title: str) -> tuple[str, str]:
    """Extract (file, project) from an editor title: "file - project - Visual Studio Code"."""
    norm = title.replace(" – ", " - ").replace(" — ", " - ")
    for suffix in EDITOR_SUFFIXES:
        if norm.endswith(suffix) or f" - {suffix}" in norm:
            body = norm.split(f" - {suffix}")[0] if f" - {suffix}" in norm else norm[: -len(suffix)]
            parts = [p.strip() for p in body.split(" - ") if p.strip()]
            if not parts:
                return "", ""
            if suffix in ("PyCharm", "IntelliJ IDEA", "WebStorm", "CLion"):  # "project - file"
                return (parts[1] if len(parts) > 1 else ""), parts[0]
            return parts[0], (parts[1] if len(parts) > 1 else "")
    return "", ""


# ------------------------------------------------------------------ collection

def collect(ctx: Context, cfg: dict, now: float | None = None) -> dict:
    """Built-in variables (excluding custom variables and plugins)."""
    now = time.time() if now is None else now
    dt = datetime.fromtimestamp(now)
    process, window = get_active_window()
    idle = get_idle_seconds()

    app_names = {k.lower(): v for k, v in (cfg.get("app_names") or {}).items()}
    app = app_names.get(process.lower()) or re.sub(r"\.exe$", "", process, flags=re.I)
    file_name, project = parse_editor_title(window)

    cpu = ram = battery = ""
    if psutil is not None:
        try:
            cpu = str(int(psutil.cpu_percent(interval=None)))
            ram = str(int(psutil.virtual_memory().percent))
            bat = psutil.sensors_battery()
            battery = str(int(bat.percent)) if bat else ""
        except Exception:
            pass
    try:
        uptime = humanize(now - psutil.boot_time()) if psutil is not None else ""
    except Exception:
        uptime = ""

    hour = dt.hour
    day_part = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 18 else "evening" if 18 <= hour < 22 else "night"
    spotify = ctx.cached("spotify", 5.0, get_spotify_track)

    return {
        "time": dt.strftime("%H:%M"),
        "date": dt.strftime("%d/%m/%Y"),
        "hour": str(hour),
        "minute": str(dt.minute),
        "weekday": WEEKDAYS[dt.weekday()],
        "weekday_num": str(dt.weekday()),
        "day_part": day_part,
        "cpu": cpu,
        "ram": ram,
        "battery": battery,
        "uptime": uptime,
        "session": humanize(now - ctx.app_start),
        "process": process,
        "window": window,
        "app": app,
        "file": file_name,
        "project": project,
        "idle": str(int(idle)),
        "idle_min": str(int(idle // 60)),
        "spotify": spotify,
        "os": platform.system(),
    }
