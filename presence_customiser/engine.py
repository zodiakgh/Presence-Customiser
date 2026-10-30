"""Moteur : collecte -> profil (règles) -> frame -> rendu -> envoi à Discord."""
from __future__ import annotations

import random
import re
import threading
import time
from pathlib import Path

from . import plugins as plug_mod
from . import variables as var_mod
from .rules import select_profile
from .templates import check_condition, render

TYPES = ("playing", "listening", "watching", "competing")
HIDDEN_VARS = ("process", "window", "app", "file", "project", "spotify")


def _clamp(text: str, limit: int = 128) -> str:
    text = (text or "").strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    if len(text) == 1:  # Discord exige au moins 2 caractères
        text += "⠀"
    return text


def build_payload(profile: dict, frame: dict, v: dict, ctx: var_mod.Context,
                  now: float, default_client_id: str = "") -> dict:
    """Rend une frame en charge utile Discord valide (longueurs, boutons, groupe, timer)."""
    ptype = profile.get("type", "playing")
    payload: dict = {
        "client_id": str(profile.get("client_id") or default_client_id or "").strip(),
        "type": ptype if ptype in TYPES else "playing",
    }
    for key in ("details", "state"):
        text = _clamp(render(frame.get(key, ""), v))
        if text:
            payload[key] = text
    for key in ("large", "small"):
        image = render(frame.get(f"{key}_image", ""), v).strip()
        if image:
            payload[f"{key}_image"] = image[:256]
            text = _clamp(render(frame.get(f"{key}_text", ""), v))
            if text:
                payload[f"{key}_text"] = text

    match = re.fullmatch(r"(\d+)\s*/\s*(\d+)", render(frame.get("party", ""), v).strip())
    if match:
        cur, mx = int(match.group(1)), int(match.group(2))
        if mx >= 1 and 1 <= cur <= mx:
            payload["party"] = (cur, mx)

    buttons = []
    for button in (frame.get("buttons") or [])[:2]:
        label = _clamp(render(button.get("label", ""), v), 32)
        url = render(button.get("url", ""), v).strip()
        if label and url.startswith(("http://", "https://")) and len(url) <= 512:
            buttons.append({"label": label, "url": url})
    if buttons:
        payload["buttons"] = buttons

    mode = profile.get("timer", "none")
    if mode == "profile":
        payload["start"] = int(ctx.profile_since)
    elif mode == "session":
        payload["start"] = int(ctx.app_start)
    elif mode == "boot" and var_mod.psutil is not None:
        try:
            payload["start"] = int(var_mod.psutil.boot_time())
        except Exception:
            pass
    elif mode == "countdown":
        end = int(ctx.profile_since + float(profile.get("countdown_minutes", 25) or 25) * 60)
        if end > now:
            payload["end"] = end
    return payload


class Engine:
    def __init__(self, cfg: dict, rpc=None, plugins_dir: Path | None = None) -> None:
        self.cfg = cfg
        self.rpc = rpc
        self.plugins_dir = plugins_dir
        self.plugins: list[plug_mod.Plugin] = []
        self.plugin_errors: list[str] = []
        self.ctx = var_mod.Context()
        self.enabled = False
        self.forced_profile: str | None = None
        self.snapshot: dict = {}
        self.status = "Désactivé"
        self._current_profile: str | None = None
        self._last_payload: dict | None = None
        self._last_sent = 0.0
        self._last_connect = 0.0
        self._need_clear = False
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.reload_plugins()

    # ----------------------------------------------------------- configuration
    def set_config(self, cfg: dict) -> None:
        with self._lock:
            self.cfg = cfg
            self._last_payload = None

    def reload_plugins(self) -> None:
        if self.plugins_dir:
            self.plugins = plug_mod.load_plugins(self.plugins_dir)

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.enabled = enabled
            self._last_payload = None
            if enabled:
                self.status = "En attente de Discord…"
            else:
                self._need_clear = True
                self.status = "Désactivé"

    def force_profile(self, name: str | None) -> None:
        with self._lock:
            self.forced_profile = name or None

    # ------------------------------------------------------------------- tick
    def _is_hidden(self, base: dict) -> bool:
        privacy = self.cfg.get("settings", {}).get("privacy", {}) or {}
        process = base.get("process", "").lower()
        window = base.get("window", "").lower()
        if process and process in [p.lower() for p in privacy.get("hidden_processes", [])]:
            return True
        return any(w.lower() in window for w in privacy.get("hidden_words", []) if w and window)

    def tick(self, now: float | None = None, send: bool = True) -> dict:
        with self._lock:
            now = time.time() if now is None else now
            cfg = self.cfg
            settings = cfg.get("settings", {})
            min_interval = max(15, int(settings.get("min_interval", 15) or 15))

            base = var_mod.collect(self.ctx, cfg, now)
            hidden = self._is_hidden(base)
            if hidden:
                for key in HIDDEN_VARS:
                    base[key] = ""
            v = dict(base)
            for key, value in (cfg.get("variables") or {}).items():
                v[str(key)] = render(str(value), v)  # une variable perso peut utiliser les précédentes
            extra, self.plugin_errors = plug_mod.run_plugins(self.plugins, v)
            v.update(extra)

            profiles = {p.get("name"): p for p in cfg.get("profiles", [])}
            if hidden:
                name = (settings.get("privacy", {}) or {}).get("hidden_profile", "")
                rule = "(confidentialité)"
            elif self.forced_profile in profiles:
                name, rule = self.forced_profile, "(forcé)"
            else:
                name, rule = select_profile(cfg, v)
            profile = (profiles.get(name) or profiles.get(cfg.get("default_profile"))
                       or (cfg["profiles"][0] if cfg.get("profiles") else None))
            if profile is None:
                self.snapshot = {"status": "Aucun profil défini", "vars": v, "payload": {},
                                 "profile": "", "rule": None, "enabled": self.enabled, "connected": False}
                return self.snapshot

            if profile["name"] != self._current_profile:
                self._current_profile = profile["name"]
                self.ctx.profile_since = now
            v["profile"] = profile["name"]
            v["profile_time"] = var_mod.humanize(now - self.ctx.profile_since)

            frames = profile.get("frames") or [{}]
            eligible = [f for f in frames if check_condition(f.get("show_if", ""), v)] or frames
            rotate = max(int(profile.get("rotate_seconds", 30) or 30), min_interval)
            slot = int((now - self.ctx.profile_since) // rotate)
            if profile.get("shuffle") and len(eligible) > 1:
                index = random.Random(f"{profile['name']}:{slot}").randrange(len(eligible))
            else:
                index = slot % len(eligible)
            payload = build_payload(profile, eligible[index], v, self.ctx, now,
                                    str(settings.get("client_id", "")))

            if send:
                self._push(payload, now, min_interval)

            self.snapshot = {
                "profile": profile["name"], "rule": rule,
                "frame_index": index, "frame_count": len(eligible),
                "payload": payload, "vars": v,
                "status": self.status, "enabled": self.enabled,
                "connected": bool(self.rpc and self.rpc.connected),
                "plugin_errors": list(self.plugin_errors),
            }
            return self.snapshot

    def _push(self, payload: dict, now: float, min_interval: int) -> None:
        if self.rpc is None:
            return
        if not self.enabled:
            if self._need_clear:
                self.rpc.clear()
                self.rpc.close()
                self._need_clear = False
                self._last_payload = None
            return
        client_id = payload.get("client_id")
        if not client_id:
            self.status = "Client ID manquant (Réglages ou profil)."
            return
        if not self.rpc.connected or self.rpc.client_id != client_id:
            if now - self._last_connect < 8:
                return
            self._last_connect = now
            self._last_payload = None
            if not self.rpc.connect(client_id):
                self.status = self.rpc.last_error or "Connexion à Discord impossible."
                return
        if payload != self._last_payload and now - self._last_sent >= min_interval:
            if self.rpc.update(payload):
                self._last_payload, self._last_sent = payload, now
                self.status = "Connecté : présence active"
            else:
                self.status = self.rpc.last_error or "Échec de la mise à jour."
        elif self.rpc.connected and self._last_payload is not None:
            self.status = "Connecté : présence active"

    # ----------------------------------------------------------------- thread
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="presence-customiser-engine", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # le moteur ne doit jamais mourir
                self.status = f"Erreur interne : {type(exc).__name__}: {exc}"
            self._stop.wait(1.0)
        if self.rpc is not None:
            self.rpc.clear()
            self.rpc.close()

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
