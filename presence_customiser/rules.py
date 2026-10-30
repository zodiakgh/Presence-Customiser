"""Automatic rules: pick the profile from activity (process, window, time, CPU...)."""
from __future__ import annotations

import re

from .templates import check_condition

_DAYS = {"lun": 0, "mon": 0, "mar": 1, "tue": 1, "mer": 2, "wed": 2, "jeu": 3, "thu": 3,
         "ven": 4, "fri": 4, "sam": 5, "sat": 5, "dim": 6, "sun": 6}


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_days(days) -> set[int]:
    out: set[int] = set()
    for d in days if isinstance(days, (list, tuple)) else str(days).split(","):
        d = str(d).strip().lower()
        if d.isdigit():
            out.add(int(d) % 7)
        elif d[:3] in _DAYS:
            out.add(_DAYS[d[:3]])
    return out


def _minutes(hhmm: str) -> int:
    h, _, m = hhmm.strip().partition(":")
    return int(h) * 60 + int(m or 0)


def _time_between(spec: str, now_hhmm: str) -> bool:
    try:
        start, end = spec.split("-")
        s, e, n = _minutes(start), _minutes(end), _minutes(now_hhmm)
    except Exception:
        return False
    return s <= n < e if s <= e else (n >= s or n < e)


def match_when(when: dict, v: dict) -> bool:
    """Every key that is present must match (logical AND)."""
    if not when:
        return False
    process = v.get("process", "").lower()
    window = v.get("window", "").lower()

    if "process" in when:
        wanted = [str(p).lower() for p in when["process"]]
        if process not in wanted:
            return False
    if "window_contains" in when:
        if not any(str(w).lower() in window for w in when["window_contains"]):
            return False
    if when.get("window_regex"):
        try:
            if not re.search(when["window_regex"], v.get("window", ""), re.I):
                return False
        except re.error:
            return False
    if when.get("time_between") and not _time_between(when["time_between"], v.get("time", "00:00")):
        return False
    if "weekdays" in when and int(_num(v.get("weekday_num"))) not in _parse_days(when["weekdays"]):
        return False
    if "cpu_above" in when and _num(v.get("cpu")) <= _num(when["cpu_above"]):
        return False
    if "ram_above" in when and _num(v.get("ram")) <= _num(when["ram_above"]):
        return False
    if "battery_below" in when:
        if v.get("battery", "") == "" or _num(v.get("battery")) >= _num(when["battery_below"]):
            return False
    if "idle_over" in when and _num(v.get("idle")) <= _num(when["idle_over"]):
        return False
    if when.get("expr") and not check_condition(when["expr"], v):
        return False
    return True


def select_profile(cfg: dict, v: dict) -> tuple[str, str | None]:
    """Return (profile name, rule name); rule None = default profile."""
    rules = [r for r in cfg.get("rules", []) if r.get("enabled", True)]
    rules.sort(key=lambda r: -_num(r.get("priority", 0)))  # stable sort: list order breaks ties
    for rule in rules:
        if match_when(rule.get("when") or {}, v):
            return rule.get("profile", ""), rule.get("name")
    return cfg.get("default_profile", ""), None
