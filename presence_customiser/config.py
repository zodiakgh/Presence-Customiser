"""Configuration de Presence Customiser : chargement, sauvegarde, validation."""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "Presence Customiser"
CONFIG_VERSION = 1


def home_dir() -> Path:
    """Dossier de données de l'appli (config + plugins)."""
    env = os.environ.get("PRESENCE_CUSTOMISER_HOME")
    if env:
        base = Path(env)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / APP_NAME.lower().replace(" ", "-")
    (base / "plugins").mkdir(parents=True, exist_ok=True)
    return base


def config_path() -> Path:
    return home_dir() / "config.json"


def default_config() -> dict:
    return {
        "version": CONFIG_VERSION,
        "default_profile": "Défaut",
        "settings": {
            "client_id": "",
            "min_interval": 15,
            "autostart_engine": True,
            "tray": True,
            "minimize_to_tray": True,
            "start_minimized": False,
            "appearance": "dark",
            "accent": "#7c5cff",
            "privacy": {
                "hidden_processes": ["KeePass.exe", "KeePassXC.exe", "Bitwarden.exe", "1Password.exe"],
                "hidden_words": ["mot de passe", "password", "banque", "bank"],
                "hidden_profile": "Privé",
            },
        },
        "variables": {
            "pseudo": "MonPseudo",
            "statut": "Disponible",
        },
        "app_names": {
            "Code.exe": "VS Code",
            "Cursor.exe": "Cursor",
            "chrome.exe": "Chrome",
            "firefox.exe": "Firefox",
            "msedge.exe": "Edge",
            "Discord.exe": "Discord",
            "Spotify.exe": "Spotify",
            "WindowsTerminal.exe": "Terminal",
            "python.exe": "Python",
            "javaw.exe": "Minecraft",
        },
        "profiles": [
            {
                "name": "Défaut",
                "type": "playing",
                "client_id": "",
                "timer": "session",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "En ligne depuis {session}",
                        "state": "{weekday|cap} • {time}",
                        "large_image": "",
                        "large_text": "{pseudo}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    },
                    {
                        "details": "CPU {cpu}% • RAM {ram}%",
                        "state": "{cpu|bar:10}",
                        "large_image": "",
                        "large_text": "{pseudo}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    },
                ],
            },
            {
                "name": "Code",
                "type": "playing",
                "client_id": "",
                "timer": "profile",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "Code : {project?un projet}",
                        "state": "Fichier : {file?…|noext}",
                        "large_image": "",
                        "large_text": "{app?Éditeur}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    },
                    {
                        "details": "{statut}",
                        "state": "Session : {profile_time}",
                        "large_image": "",
                        "large_text": "{pseudo}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    },
                ],
            },
            {
                "name": "Jeu",
                "type": "playing",
                "client_id": "",
                "timer": "profile",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "Joue à {app?un jeu}",
                        "state": "Depuis {profile_time}",
                        "large_image": "",
                        "large_text": "{pseudo}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    }
                ],
            },
            {
                "name": "Musique",
                "type": "listening",
                "client_id": "",
                "timer": "none",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "{spotify|trunc:60}",
                        "state": "{time}",
                        "large_image": "",
                        "large_text": "Spotify",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "spotify",
                        "buttons": [],
                    }
                ],
            },
            {
                "name": "Inactif",
                "type": "playing",
                "client_id": "",
                "timer": "profile",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "Absent",
                        "state": "Inactif depuis {idle_min} min",
                        "large_image": "",
                        "large_text": "{pseudo}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    }
                ],
            },
            {
                "name": "Nuit",
                "type": "playing",
                "client_id": "",
                "timer": "none",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "Mode nuit",
                        "state": "{time}",
                        "large_image": "",
                        "large_text": "{pseudo}",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    }
                ],
            },
            {
                "name": "Privé",
                "type": "playing",
                "client_id": "",
                "timer": "none",
                "countdown_minutes": 25,
                "rotate_seconds": 30,
                "shuffle": False,
                "frames": [
                    {
                        "details": "En ligne",
                        "state": "",
                        "large_image": "",
                        "large_text": "",
                        "small_image": "",
                        "small_text": "",
                        "party": "",
                        "show_if": "",
                        "buttons": [],
                    }
                ],
            },
        ],
        "rules": [
            {"name": "Inactif", "profile": "Inactif", "priority": 90, "enabled": True,
             "when": {"idle_over": 300}},
            {"name": "Jeux", "profile": "Jeu", "priority": 60, "enabled": True,
             "when": {"process": ["javaw.exe", "Minecraft.Windows.exe", "RobloxPlayerBeta.exe"]}},
            {"name": "Code", "profile": "Code", "priority": 50, "enabled": True,
             "when": {"process": ["Code.exe", "Cursor.exe", "pycharm64.exe", "idea64.exe",
                                  "WindowsTerminal.exe", "sublime_text.exe", "notepad++.exe"]}},
            {"name": "Musique", "profile": "Musique", "priority": 20, "enabled": True,
             "when": {"expr": "spotify"}},
            {"name": "Nuit", "profile": "Nuit", "priority": 5, "enabled": True,
             "when": {"time_between": "00:00-06:00"}},
        ],
    }


EXAMPLE_PLUGIN = '''"""Exemple de plugin Presence Customiser.

Un plugin est un fichier .py placé dans le dossier "plugins".
Il expose get_variables(vars) qui retourne un dict {nom: valeur}.
Ces variables sont ensuite utilisables dans les templates : {quote}, {emoji_clock}...
`vars` contient toutes les variables déjà calculées (time, cpu, app, ...).
"""
import time

QUOTES = [
    "Un bug à la fois.",
    "Ça marche sur ma machine.",
    "Premature optimization is the root of all evil.",
    "Make it work, make it right, make it fast.",
]

CLOCKS = "🕛🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚"


def get_variables(vars):
    now = time.localtime()
    return {
        "quote": QUOTES[(now.tm_hour * 60 + now.tm_min) % len(QUOTES)],
        "emoji_clock": CLOCKS[now.tm_hour % 12],
    }
'''


def ensure_example_plugin() -> None:
    plugins = home_dir() / "plugins"
    if not any(plugins.glob("*.py")):
        (plugins / "example_plugin.py").write_text(EXAMPLE_PLUGIN, encoding="utf-8")


def _merge(defaults: dict, user: dict) -> dict:
    out = copy.deepcopy(defaults)
    for key, value in user.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def normalize(cfg: dict) -> dict:
    """Fusionne avec les valeurs par défaut : seul `settings` est fusionné en profondeur."""
    base = default_config()
    out = copy.deepcopy(base)
    for key, value in cfg.items():
        if key == "settings" and isinstance(value, dict):
            out["settings"] = _merge(base["settings"], value)
        else:
            out[key] = value
    return out


def load_config(path: Path | None = None) -> dict:
    path = path or config_path()
    if not path.exists():
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("la racine doit être un objet JSON")
        return normalize(data)
    except Exception:
        shutil.copy2(path, path.with_suffix(".broken.json"))
        cfg = default_config()
        save_config(cfg, path)
        return cfg


def save_config(cfg: dict, path: Path | None = None) -> None:
    path = path or config_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def validate_config(cfg: dict) -> list[str]:
    problems: list[str] = []
    profiles = cfg.get("profiles") or []
    if not profiles:
        problems.append("Aucun profil défini.")
    names = [p.get("name", "") for p in profiles]
    for name in sorted(set(names)):
        if names.count(name) > 1:
            problems.append(f"Nom de profil en double : « {name} ».")
    if cfg.get("default_profile") not in names:
        problems.append("Le profil par défaut n'existe pas.")
    for profile in profiles:
        pname = profile.get("name", "?")
        frames = profile.get("frames") or []
        if not frames:
            problems.append(f"Profil « {pname} » : aucune frame.")
        for i, frame in enumerate(frames, 1):
            buttons = frame.get("buttons") or []
            if len(buttons) > 2:
                problems.append(f"Profil « {pname} », frame {i} : 2 boutons maximum.")
            for button in buttons:
                url = button.get("url", "")
                if url and "{" not in url and not url.startswith(("http://", "https://")):
                    problems.append(f"Profil « {pname} », frame {i} : URL de bouton invalide ({url}).")
    for rule in cfg.get("rules") or []:
        if rule.get("profile") not in names:
            problems.append(f"Règle « {rule.get('name', '?')} » : profil introuvable.")
    hidden = (cfg.get("settings", {}).get("privacy", {}) or {}).get("hidden_profile")
    if hidden and hidden not in names:
        problems.append(f"Profil de confidentialité « {hidden} » introuvable.")
    return problems
