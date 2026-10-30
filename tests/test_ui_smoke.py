"""Test fumée de l'interface avec un faux toolkit (aucun affichage, tkinter non requis).

Il exécute toute la logique de ui.py (formulaires, ajout/suppression de profils, règles,
réglages, JSON, boutons de téléchargement) pour détecter les erreurs de code.
Il ne remplace pas un vrai lancement : `python main.py` sur Windows reste le test final.
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

os.environ["PRESENCE_CUSTOMISER_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class Var:
    def __init__(self, value=None, **_kw):
        self.v = "" if value is None else value

    def get(self):
        return self.v

    def set(self, value):
        self.v = value


class BoolVar(Var):
    def __init__(self, value=False, **_kw):
        self.v = value


class Widget:
    def __init__(self, *_a, **_k):
        pass

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def method(*_a, **_k):
            if name == "winfo_children":
                return []
            if name == "after":
                return "job"
            if name == "get":
                return ""
            return Widget()
        return method


ctk = types.ModuleType("customtkinter")
for _n in ("CTk", "CTkFrame", "CTkLabel", "CTkButton", "CTkEntry", "CTkOptionMenu", "CTkSwitch", "CTkTextbox",
           "CTkTabview", "CTkScrollableFrame", "CTkSegmentedButton", "CTkFont"):
    setattr(ctk, _n, type(_n, (Widget,), {}))
ctk.StringVar, ctk.BooleanVar = Var, BoolVar
ctk.set_appearance_mode = lambda _m: None
tk = types.ModuleType("tkinter")
fd = types.ModuleType("tkinter.filedialog")
mb = types.ModuleType("tkinter.messagebox")
mb.askyesno = lambda *a, **k: True
mb.showinfo = mb.showerror = lambda *a, **k: None
tk.filedialog, tk.messagebox = fd, mb
sys.modules.update({"customtkinter": ctk, "tkinter": tk, "tkinter.filedialog": fd, "tkinter.messagebox": mb})

from presence_customiser import config, ui, variables  # noqa: E402
from presence_customiser.engine import Engine  # noqa: E402

variables.get_active_window = lambda: ("Code.exe", "a.py - proj - Visual Studio Code")
variables.get_idle_seconds = lambda: 0.0


def main():
    config.ensure_example_plugin()
    cfg = config.default_config()
    cfg["settings"]["client_id"] = "123456789012345678"
    cfg["settings"]["tray"] = False
    engine = Engine(cfg, rpc=None, plugins_dir=config.home_dir() / "plugins")
    app = ui.App(engine, cfg)
    try:
        app.dashboard.refresh(engine.tick(send=False), engine)

        # --- profils et frames
        pt = app.profiles_tab
        n = len(cfg["profiles"])
        pt.add_profile()
        assert len(cfg["profiles"]) == n + 1
        pt.pv["name"].set("Streaming")
        pt.fv["details"].set("Live {time}")
        pt.bv["l1"].set("Site")
        pt.bv["u1"].set("https://example.com")
        pt.add_frame()
        pt.dup_frame()
        pt.move_frame(-1)
        pt.del_frame()
        pt.preview()
        pt.save()
        streaming = next(p for p in cfg["profiles"] if p["name"] == "Streaming")
        assert streaming["frames"][0]["details"] == "Live {time}"
        assert streaming["frames"][0]["buttons"] == [{"label": "Site", "url": "https://example.com"}]
        assert len(streaming["frames"]) == 2

        # renommage : les références suivent
        pt.pv["name"].set("Live")
        pt.save()
        assert any(p["name"] == "Live" for p in cfg["profiles"])
        pt.dup_profile()
        pt.del_profile()

        # --- règles
        rt = app.rules_tab
        rt.add()
        rt.name.set("Test")
        rt.wv["process"].set("a.exe, b.exe")
        rt.wv["cpu_above"].set("80")
        rt.wv["time_between"].set("22:00-06:00")
        rt.save()
        when = cfg["rules"][-1]["when"]
        assert when["process"] == ["a.exe", "b.exe"] and when["cpu_above"] == 80
        rt.dup()
        rt.delete()

        # --- variables
        app.vars_tab.vars_box.get = lambda *_a: "a = 1\nb = {a} 2\n"
        app.vars_tab.apps_box.get = lambda *_a: "x.exe = X"
        app.vars_tab.save()
        assert cfg["variables"] == {"a": "1", "b": "{a} 2"} and cfg["app_names"] == {"x.exe": "X"}

        # --- réglages
        st = app.settings_tab
        st.client_id.set("999")
        st.min_interval.set("3")
        st.hide_procs.get = lambda *_a: "A.exe\nB.exe\n"
        st.save()
        assert cfg["settings"]["client_id"] == "999" and cfg["settings"]["min_interval"] == 15
        assert cfg["settings"]["privacy"]["hidden_processes"] == ["A.exe", "B.exe"]

        # --- JSON : valide puis invalide
        app.json_tab.box.get = lambda *_a: json.dumps(cfg)
        app.json_tab.apply()
        assert app.cfg is engine.cfg
        before = app.cfg
        app.json_tab.box.get = lambda *_a: "{pas du json"
        app.json_tab.apply()
        assert app.cfg is before

        # --- boutons Download : ouvrent les releases ; une URL avec OWNER (modèle non rempli) est bloquée
        opened = []
        ui.webbrowser.open = lambda url: opened.append(url)
        app.open_url("https://github.com/OWNER/presence-customiser/releases/latest")
        assert opened == [], "ne doit pas ouvrir une URL contenant OWNER"
        app.open_releases()
        assert opened == [ui.RELEASES_URL]
        assert ui.RELEASES_URL == "https://github.com/zodiakgh/Presence-Customiser/releases/latest"

        assert config.validate_config(app.cfg) == [], config.validate_config(app.cfg)
        print("OK   ui smoke")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()
