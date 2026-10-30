"""Tests du moteur (sans Discord ni interface) : python tests/test_engine.py"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["PRESENCE_CUSTOMISER_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence_customiser import config, variables
from presence_customiser.engine import Engine
from presence_customiser.templates import check_condition, render


class FakeRPC:
    def __init__(self):
        self.connected = False
        self.client_id = None
        self.last_error = ""
        self.sent = []
        self.cleared = 0

    def connect(self, cid):
        self.connected, self.client_id = True, cid
        return True

    def update(self, payload):
        self.sent.append(payload)
        return True

    def clear(self):
        self.cleared += 1

    def close(self):
        self.connected, self.client_id = False, None


def fake_env(process="", window="", idle=0.0):
    variables.get_active_window = lambda: (process, window)
    variables.get_idle_seconds = lambda: idle


def make_engine(rpc=None):
    cfg = config.default_config()
    cfg["settings"]["client_id"] = "123456789012345678"
    return Engine(cfg, rpc=rpc, plugins_dir=config.home_dir() / "plugins")


def test_templates():
    v = {"cpu": "40", "name": "ben", "empty": "", "long": "abcdefghij"}
    assert render("{name|upper}", v) == "BEN"
    assert render("{empty?rien}", v) == "rien"
    assert render("{missing}x", v) == "x"
    assert render("{long|trunc:5}", v) == "abcd…"
    assert render("{cpu|bar:10}", v) == "▰▰▰▰▱▱▱▱▱▱"
    assert render("{name|prefix:@}", v) == "@ben"
    assert render("{name|cap}", v) == "Ben"
    assert render("a.py", v) == "a.py"
    assert render("{x|noext}", {"x": "● main.py"}) == "main"


def test_conditions():
    v = {"cpu": "85", "app": "Chrome", "spotify": "A - B", "empty": "", "window": "YouTube - Chrome"}
    assert check_condition("cpu > 80", v)
    assert not check_condition("cpu > 90", v)
    assert check_condition("app == chrome and cpu >= 85", v)
    assert check_condition("spotify", v)
    assert check_condition("!empty", v)
    assert check_condition("window contains youtube", v)
    assert check_condition("", v)


def test_editor_title():
    assert variables.parse_editor_title("● main.py - presence_customiser - Visual Studio Code") == ("● main.py", "presence_customiser")
    assert variables.parse_editor_title("Cursor") == ("", "")
    assert variables.parse_editor_title("Untitled - Notepad") == ("", "")


def test_default_config_valid():
    assert config.validate_config(config.default_config()) == []


def test_rule_selection():
    eng = make_engine()
    fake_env("Code.exe", "main.py - presence_customiser - Visual Studio Code")
    snap = eng.tick(send=False)
    assert snap["profile"] == "Code" and snap["rule"] == "Code", snap["profile"]
    assert snap["payload"]["details"] == "Code : presence_customiser", snap["payload"]
    assert snap["payload"]["state"] == "Fichier : main", snap["payload"]

    fake_env("javaw.exe", "Minecraft 1.21")
    assert make_engine().tick(send=False)["profile"] == "Jeu"

    fake_env("explorer.exe", "Dossier", idle=400)
    snap = make_engine().tick(send=False)
    assert snap["profile"] == "Inactif" and "6 min" in snap["payload"]["state"]

    fake_env("explorer.exe", "Dossier")
    assert make_engine().tick(send=False)["profile"] in ("Défaut", "Nuit", "Musique")


def test_time_rule():
    fake_env("explorer.exe", "x")
    eng = make_engine()
    import time
    base = time.mktime((2026, 10, 30, 3, 0, 0, 0, 0, -1))
    assert eng.tick(now=base, send=False)["profile"] == "Nuit"
    noon = time.mktime((2026, 10, 30, 12, 0, 0, 0, 0, -1))
    assert eng.tick(now=noon, send=False)["profile"] == "Défaut"


def test_privacy():
    eng = make_engine()
    fake_env("KeePassXC.exe", "Base de données")
    snap = eng.tick(send=False)
    assert snap["profile"] == "Privé" and snap["rule"] == "(confidentialité)"
    assert snap["vars"]["window"] == "" and snap["vars"]["process"] == ""
    fake_env("chrome.exe", "Ma banque en ligne - Chrome")
    assert make_engine().tick(send=False)["profile"] == "Privé"


def test_forced_profile_and_rotation():
    fake_env("explorer.exe", "x")
    eng = make_engine()
    eng.force_profile("Défaut")
    import time
    t0 = time.time()
    first = eng.tick(now=t0, send=False)
    assert first["rule"] == "(forcé)"
    d0 = first["payload"]["details"]
    later = eng.tick(now=t0 + 31, send=False)
    assert later["frame_index"] == 1 and later["payload"]["details"] != d0


def test_send_throttle_and_clear():
    fake_env("explorer.exe", "x")
    rpc = FakeRPC()
    eng = make_engine(rpc)
    eng.force_profile("Défaut")  # indépendant de l'heure (la règle « Nuit » s'applique de 0h à 6h)
    import time
    t0 = time.time()
    eng.tick(now=t0)                 # désactivé -> rien d'envoyé
    assert rpc.sent == []
    eng.set_enabled(True)
    eng.tick(now=t0 + 1)
    assert len(rpc.sent) == 1 and rpc.client_id == "123456789012345678"
    eng.cfg["variables"]["pseudo"] = "Autre"
    eng.cfg["profiles"][0]["frames"][0]["details"] = "{pseudo} change"
    eng.tick(now=t0 + 5)             # < 15 s : pas d'envoi
    assert len(rpc.sent) == 1
    eng.tick(now=t0 + 20)            # >= 15 s : envoi
    assert len(rpc.sent) == 2 and rpc.sent[-1]["details"] == "Autre change"
    eng.set_enabled(False)
    eng.tick(now=t0 + 30)
    assert rpc.cleared >= 1 and not rpc.connected


def test_payload_validation():
    fake_env("explorer.exe", "x")
    eng = make_engine()
    frame = eng.cfg["profiles"][0]["frames"][0]
    frame.update({"details": "a", "state": "x" * 300, "large_image": "img", "large_text": "tip",
                  "party": "2/4",
                  "buttons": [{"label": "Ok", "url": "https://example.com"},
                              {"label": "Mauvais", "url": "javascript:alert(1)"},
                              {"label": "Trop", "url": "https://example.org"}]})
    eng.force_profile("Défaut")
    p = eng.tick(send=False)["payload"]
    assert len(p["details"]) == 2 and len(p["state"]) == 128
    assert p["party"] == (2, 4)
    assert p["large_image"] == "img" and p["large_text"] == "tip"
    assert [b["url"] for b in p["buttons"]] == ["https://example.com"]


def test_custom_vars_plugins_countdown():
    fake_env("explorer.exe", "x")
    config.ensure_example_plugin()
    eng = make_engine()
    eng.cfg["variables"]["combo"] = "{pseudo} @ {time}"
    eng.cfg["profiles"][0]["frames"][0]["details"] = "{combo} {quote|trunc:8} {emoji_clock}"
    eng.cfg["profiles"][0]["timer"] = "countdown"
    eng.force_profile("Défaut")
    snap = eng.tick(send=False)
    assert snap["payload"]["details"].startswith("MonPseudo @ "), snap["payload"]["details"]
    assert "end" in snap["payload"] and "start" not in snap["payload"]
    assert not snap["plugin_errors"], snap["plugin_errors"]


def test_config_roundtrip_and_broken_file():
    cfg = config.load_config()
    cfg["variables"]["x"] = "é"
    config.save_config(cfg)
    assert config.load_config()["variables"]["x"] == "é"
    config.config_path().write_text("{pas du json", encoding="utf-8")
    assert config.load_config()["default_profile"] == "Défaut"
    assert config.config_path().with_suffix(".broken.json").exists()


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"OK   {name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    sys.exit(1 if failed else 0)
