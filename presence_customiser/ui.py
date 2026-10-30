"""Graphical interface (CustomTkinter) for Presence Customiser."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import DISPLAY_NAME, ISSUES_URL, RELEASES_URL, REPO_URL, __version__
from . import config as config_mod
from . import sysutil
from .templates import render

TYPE_LABELS = {"playing": "Playing…", "listening": "Listening to…", "watching": "Watching…", "competing": "Competing in…"}
TIMER_LABELS = {
    "none": "No timer",
    "profile": "Since the profile started",
    "session": "Since the app started",
    "boot": "Since the PC booted",
    "countdown": "Countdown",
}
FRAME_FIELDS = [
    ("details", "Line 1 (details)", "Online for {session}"),
    ("state", "Line 2 (state)", "{weekday|cap} • {time}"),
    ("large_image", "Large image", "Discord asset key or https:// URL"),
    ("large_text", "Large image tooltip", "{nickname}"),
    ("small_image", "Small image", "asset key or URL"),
    ("small_text", "Small image tooltip", ""),
    ("party", "Party", "1/4  (or {x}/{y})"),
    ("show_if", "Show only if", "cpu > 80   |   app == Chrome   |   spotify"),
]
RULE_LIST_FIELDS = [
    ("process", "Processes (comma-separated)", "Code.exe, Cursor.exe"),
    ("window_contains", "Window title contains (comma-separated)", "youtube, netflix"),
]
RULE_TEXT_FIELDS = [
    ("window_regex", "Window title (regex)", r"^GitHub.*"),
    ("time_between", "Time range", "22:00-06:00"),
    ("weekdays", "Days", "mon, tue, sat  (or 0,1,5)"),
    ("cpu_above", "CPU above (%)", "80"),
    ("ram_above", "RAM above (%)", "90"),
    ("battery_below", "Battery below (%)", "20"),
    ("idle_over", "Idle for more than (s)", "300"),
    ("expr", "Custom condition", "app == Chrome and hour >= 22"),
]


def _title(parent, text: str):
    ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x", pady=(12, 4))


def _hint(parent, text: str):
    ctk.CTkLabel(parent, text=text, text_color="gray", anchor="w", justify="left", wraplength=620).pack(fill="x", pady=(0, 4))


def _entry(app, parent, label: str, var, placeholder: str = ""):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=2)
    ctk.CTkLabel(row, text=label, width=200, anchor="w").pack(side="left")
    entry = ctk.CTkEntry(row, textvariable=var, placeholder_text=placeholder)
    entry.pack(side="left", fill="x", expand=True)
    app.track(entry)
    return entry


def _num_or_text(text: str):
    text = text.strip()
    try:
        number = float(text.replace(",", "."))
        return int(number) if number == int(number) else number
    except ValueError:
        return text


def _split_csv(text: str) -> list[str]:
    return [p.strip() for p in text.split(",") if p.strip()]


def _parse_pairs(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            if key.strip():
                out[key.strip()] = value.strip()
    return out


def _set_text(box: ctk.CTkTextbox, text: str):
    box.delete("1.0", "end")
    box.insert("1.0", text)


def _fmt_clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ====================================================================== Dashboard
class DashboardTab:
    def __init__(self, app: "App", parent):
        self.app = app
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(6, 8))
        self.dot = ctk.CTkLabel(top, text="●", font=ctk.CTkFont(size=22), text_color="gray")
        self.dot.pack(side="left", padx=(4, 6))
        self.status = ctk.CTkLabel(top, text="", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self.toggle_btn = ctk.CTkButton(top, text="Enable presence", width=180, fg_color=app.accent,
                                        command=app.toggle)
        self.toggle_btn.pack(side="right")
        ctk.CTkButton(top, text="⬇ Download Presence Customiser", width=230, fg_color="transparent",
                      border_width=1, text_color=("black", "white"),
                      command=app.open_releases).pack(side="right", padx=8)

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row, text="Profile:").pack(side="left", padx=(4, 8))
        self.profile_var = ctk.StringVar(value="Auto (rules)")
        self.profile_menu = ctk.CTkOptionMenu(row, variable=self.profile_var, values=["Auto (rules)"],
                                              command=self.on_profile, width=220)
        self.profile_menu.pack(side="left")
        self.rule_lbl = ctk.CTkLabel(row, text="", text_color="gray")
        self.rule_lbl.pack(side="left", padx=12)

        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=("#e9e9f0", "#2b2d31"))
        card.pack(fill="x", padx=4, pady=4)
        self.c_head = ctk.CTkLabel(card, text="", anchor="w", font=ctk.CTkFont(size=11, weight="bold"),
                                   text_color="gray")
        self.c_head.pack(fill="x", padx=16, pady=(12, 0))
        self.c_details = ctk.CTkLabel(card, text="", anchor="w", font=ctk.CTkFont(size=15, weight="bold"))
        self.c_details.pack(fill="x", padx=16)
        self.c_state = ctk.CTkLabel(card, text="", anchor="w")
        self.c_state.pack(fill="x", padx=16)
        self.c_timer = ctk.CTkLabel(card, text="", anchor="w", text_color="#3ba55d")
        self.c_timer.pack(fill="x", padx=16)
        self.c_extra = ctk.CTkLabel(card, text="", anchor="w", text_color="gray", justify="left", wraplength=800)
        self.c_extra.pack(fill="x", padx=16, pady=(0, 12))

        _title(parent, "Live variables")
        self.vars_box = ctk.CTkTextbox(parent, font=ctk.CTkFont(family="Consolas", size=12))
        self.vars_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._last_vars = ""
        self.reload_profiles()

    def reload_profiles(self):
        names = ["Auto (rules)"] + [p["name"] for p in self.app.cfg["profiles"]]
        self.profile_menu.configure(values=names)
        if self.profile_var.get() not in names:
            self.profile_var.set(names[0])
            self.app.engine.force_profile(None)

    def on_profile(self, choice: str):
        self.app.engine.force_profile(None if choice.startswith("Auto") else choice)

    def refresh(self, snap: dict, engine):
        if not engine.enabled:
            color = "gray"
        elif snap.get("connected"):
            color = "#3ba55d"
        else:
            color = "#f0a020"
        self.dot.configure(text_color=color)
        self.status.configure(text=engine.status)
        self.toggle_btn.configure(text="Disable" if engine.enabled else "Enable presence")
        self.rule_lbl.configure(text=f"rule: {snap['rule']}" if snap.get("rule") else "")

        payload = snap.get("payload") or {}
        head = TYPE_LABELS.get(payload.get("type", "playing"), "").upper()
        self.c_head.configure(text=f"{head}  (your Discord application's name)")
        self.c_details.configure(text=payload.get("details", "—"))
        self.c_state.configure(text=payload.get("state", ""))
        if payload.get("start"):
            self.c_timer.configure(text=f"⏱ {_fmt_clock(time.time() - payload['start'])}")
        elif payload.get("end"):
            self.c_timer.configure(text=f"⏳ left {_fmt_clock(payload['end'] - time.time())}")
        else:
            self.c_timer.configure(text="")
        extra = []
        if payload.get("large_image"):
            extra.append(f"🖼 {payload['large_image']}")
        if payload.get("party"):
            extra.append(f"👥 {payload['party'][0]} of {payload['party'][1]}")
        for button in payload.get("buttons", []):
            extra.append(f"[ {button['label']} ]")
        if snap.get("frame_count"):
            extra.append(f"frame {snap['frame_index'] + 1}/{snap['frame_count']}")
        self.c_extra.configure(text="   ".join(extra))

        text = "\n".join(f"{k:<14} = {v}" for k, v in sorted((snap.get("vars") or {}).items()))
        if text != self._last_vars:
            self._last_vars = text
            try:
                pos = self.vars_box._textbox.yview()[0]
            except Exception:
                pos = 0.0
            _set_text(self.vars_box, text)
            try:
                self.vars_box._textbox.yview_moveto(pos)
            except Exception:
                pass


# ============================================================================== Profiles
class ProfilesTab:
    FRAME_KEYS = [k for k, _, _ in FRAME_FIELDS]

    def __init__(self, app: "App", parent):
        self.app = app
        self.p_idx = 0
        self.f_idx = 0
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(parent, width=210)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        ctk.CTkLabel(left, text="Profiles", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(8, 4))
        self.plist = ctk.CTkScrollableFrame(left, width=190)
        self.plist.pack(fill="both", expand=True, padx=6)
        for text, cmd in (("+ New", self.add_profile), ("Duplicate", self.dup_profile),
                          ("Delete", self.del_profile)):
            ctk.CTkButton(left, text=text, command=cmd, width=170).pack(pady=3, padx=8)

        right = ctk.CTkScrollableFrame(parent)
        right.grid(row=0, column=1, sticky="nsew")

        _title(right, "Profile")
        self.pv = {
            "name": ctk.StringVar(), "client_id": ctk.StringVar(), "type": ctk.StringVar(),
            "timer": ctk.StringVar(), "countdown": ctk.StringVar(), "rotate": ctk.StringVar(),
            "shuffle": ctk.BooleanVar(),
        }
        _entry(app, right, "Name", self.pv["name"])
        _entry(app, right, "Client ID (optional)", self.pv["client_id"], "empty = Client ID from Settings")
        _hint(right, "A different Client ID per profile lets you show a different application name "
                     "(“Playing Coding”, “Listening to Music”…).")
        self._menu_row(right, "Activity type", self.pv["type"], list(TYPE_LABELS.values()))
        self._menu_row(right, "Timer", self.pv["timer"], list(TIMER_LABELS.values()))
        _entry(app, right, "Countdown length (min)", self.pv["countdown"], "25")
        _entry(app, right, "Frame rotation (s)", self.pv["rotate"], "30  (minimum 15)")
        ctk.CTkSwitch(right, text="Shuffle frames", variable=self.pv["shuffle"]).pack(anchor="w", pady=4)

        _title(right, "Frames (pages that rotate)")
        bar = ctk.CTkFrame(right, fg_color="transparent")
        bar.pack(fill="x")
        self.seg = ctk.CTkSegmentedButton(bar, values=["1"], command=self.on_frame)
        self.seg.pack(side="left", padx=(0, 8))
        for text, cmd in (("+", self.add_frame), ("Duplicate", self.dup_frame), ("Delete", self.del_frame),
                          ("◀", lambda: self.move_frame(-1)), ("▶", lambda: self.move_frame(1))):
            ctk.CTkButton(bar, text=text, width=34 if len(text) == 1 else 90, command=cmd).pack(side="left", padx=2)

        pick = ctk.CTkFrame(right, fg_color="transparent")
        pick.pack(fill="x", pady=(8, 2))
        ctk.CTkLabel(pick, text="Insert a variable:", anchor="w").pack(side="left", padx=(0, 8))
        self.var_menu = ctk.CTkOptionMenu(pick, values=["time"], command=app.insert_variable, width=200)
        self.var_menu.pack(side="left")
        ctk.CTkButton(pick, text="Preview", width=130, command=self.preview).pack(side="left", padx=10)
        self.preview_lbl = ctk.CTkLabel(right, text="", anchor="w", text_color="gray", justify="left", wraplength=640)
        self.preview_lbl.pack(fill="x")

        self.fv = {k: ctk.StringVar() for k in self.FRAME_KEYS}
        for key, label, placeholder in FRAME_FIELDS:
            _entry(app, right, label, self.fv[key], placeholder)
        _hint(right, "Syntax: {variable}, {variable?default}, {variable?default|filter:arg}. "
                     "Filters: upper lower title cap trunc:N round:N pad:N bar:N noext clean prefix:x suffix:x "
                     "replace:a=b default:x.")
        _title(right, "Buttons (2 max, visible to others)")
        self.bv = {k: ctk.StringVar() for k in ("l1", "u1", "l2", "u2")}
        _entry(app, right, "Button 1: label", self.bv["l1"], "My GitHub")
        _entry(app, right, "Button 1: URL", self.bv["u1"], "https://github.com/…")
        _entry(app, right, "Button 2: label", self.bv["l2"])
        _entry(app, right, "Button 2: URL", self.bv["u2"])

        ctk.CTkButton(right, text="Save profile", fg_color=app.accent, height=36,
                      command=self.save).pack(fill="x", pady=(16, 8))
        self.reload()

    def _menu_row(self, parent, label, var, values):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=200, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(row, variable=var, values=values, width=260).pack(side="left")

    # ------------------------------------------------------------------ data
    @property
    def profiles(self) -> list:
        profiles = self.app.cfg.setdefault("profiles", [])
        if not profiles:
            profiles.append(self._blank_profile("Default"))
            self.app.cfg["default_profile"] = "Default"
        return profiles

    @staticmethod
    def _blank_frame() -> dict:
        return {"details": "", "state": "", "large_image": "", "large_text": "", "small_image": "",
                "small_text": "", "party": "", "show_if": "", "buttons": []}

    def _blank_profile(self, name: str) -> dict:
        return {"name": name, "type": "playing", "client_id": "", "timer": "none", "countdown_minutes": 25,
                "rotate_seconds": 30, "shuffle": False, "frames": [self._blank_frame()]}

    def _unique_name(self, base: str) -> str:
        names = {p["name"] for p in self.profiles}
        if base not in names:
            return base
        n = 2
        while f"{base} {n}" in names:
            n += 1
        return f"{base} {n}"

    def reload(self):
        self.p_idx = min(self.p_idx, len(self.profiles) - 1)
        self.refresh_list()
        self.load()

    def refresh_list(self):
        for w in self.plist.winfo_children():
            w.destroy()
        for i, profile in enumerate(self.profiles):
            selected = i == self.p_idx
            ctk.CTkButton(self.plist, text=profile["name"], anchor="w",
                          fg_color=self.app.accent if selected else "transparent",
                          text_color="white" if selected else ("black", "white"),
                          hover_color=("#d0d0dc", "#3a3c42"),
                          command=lambda i=i: self.select(i)).pack(fill="x", pady=1)

    def load(self):
        profile = self.profiles[self.p_idx]
        self.pv["name"].set(profile.get("name", ""))
        self.pv["client_id"].set(profile.get("client_id", ""))
        self.pv["type"].set(TYPE_LABELS.get(profile.get("type", "playing"), TYPE_LABELS["playing"]))
        self.pv["timer"].set(TIMER_LABELS.get(profile.get("timer", "none"), TIMER_LABELS["none"]))
        self.pv["countdown"].set(str(profile.get("countdown_minutes", 25)))
        self.pv["rotate"].set(str(profile.get("rotate_seconds", 30)))
        self.pv["shuffle"].set(bool(profile.get("shuffle", False)))
        frames = profile.setdefault("frames", [self._blank_frame()])
        self.f_idx = min(self.f_idx, len(frames) - 1)
        self.seg.configure(values=[str(i + 1) for i in range(len(frames))])
        self.seg.set(str(self.f_idx + 1))
        names = sorted((self.app.engine.snapshot.get("vars") or {"time": ""}).keys()) or ["time"]
        self.var_menu.configure(values=names)
        self.load_frame()

    def load_frame(self):
        frame = self.profiles[self.p_idx]["frames"][self.f_idx]
        for key in self.FRAME_KEYS:
            self.fv[key].set(frame.get(key, ""))
        buttons = frame.get("buttons") or []
        for n in (1, 2):
            b = buttons[n - 1] if len(buttons) >= n else {}
            self.bv[f"l{n}"].set(b.get("label", ""))
            self.bv[f"u{n}"].set(b.get("url", ""))
        self.preview_lbl.configure(text="")

    def collect_frame(self):
        frames = self.profiles[self.p_idx]["frames"]
        if not frames or self.f_idx >= len(frames):
            return
        frame = frames[self.f_idx]
        for key in self.FRAME_KEYS:
            frame[key] = self.fv[key].get()
        buttons = []
        for n in (1, 2):
            label, url = self.bv[f"l{n}"].get().strip(), self.bv[f"u{n}"].get().strip()
            if label or url:
                buttons.append({"label": label, "url": url})
        frame["buttons"] = buttons

    def collect(self):
        profile = self.profiles[self.p_idx]
        self.collect_frame()
        old = profile["name"]
        new = self.pv["name"].get().strip()
        if new and new != old and new not in {p["name"] for p in self.profiles}:
            profile["name"] = new
            cfg = self.app.cfg
            if cfg.get("default_profile") == old:
                cfg["default_profile"] = new
            for rule in cfg.get("rules", []):
                if rule.get("profile") == old:
                    rule["profile"] = new
            privacy = cfg["settings"].get("privacy", {})
            if privacy.get("hidden_profile") == old:
                privacy["hidden_profile"] = new
        profile["client_id"] = self.pv["client_id"].get().strip()
        profile["type"] = next((k for k, v in TYPE_LABELS.items() if v == self.pv["type"].get()), "playing")
        profile["timer"] = next((k for k, v in TIMER_LABELS.items() if v == self.pv["timer"].get()), "none")
        for key, field, default in (("countdown_minutes", "countdown", 25), ("rotate_seconds", "rotate", 30)):
            try:
                profile[key] = max(1, int(float(self.pv[field].get().replace(",", "."))))
            except ValueError:
                profile[key] = default
        profile["shuffle"] = bool(self.pv["shuffle"].get())

    # ------------------------------------------------------------------ actions
    def select(self, i: int):
        self.collect()
        self.p_idx, self.f_idx = i, 0
        self.refresh_list()
        self.load()

    def on_frame(self, value: str):
        self.collect_frame()
        self.f_idx = int(value) - 1
        self.load_frame()

    def add_profile(self):
        self.collect()
        self.profiles.append(self._blank_profile(self._unique_name("New profile")))
        self.p_idx, self.f_idx = len(self.profiles) - 1, 0
        self.refresh_list()
        self.load()

    def dup_profile(self):
        self.collect()
        clone = copy.deepcopy(self.profiles[self.p_idx])
        clone["name"] = self._unique_name(clone["name"] + " (copy)")
        self.profiles.append(clone)
        self.p_idx, self.f_idx = len(self.profiles) - 1, 0
        self.refresh_list()
        self.load()

    def del_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showinfo("Presence Customiser", "You must keep at least one profile.")
            return
        name = self.profiles[self.p_idx]["name"]
        if not messagebox.askyesno("Presence Customiser", f'Delete profile "{name}"?'):
            return
        del self.profiles[self.p_idx]
        if self.app.cfg.get("default_profile") == name:
            self.app.cfg["default_profile"] = self.profiles[0]["name"]
        self.p_idx = max(0, self.p_idx - 1)
        self.f_idx = 0
        self.refresh_list()
        self.load()
        self.app.after_profiles_changed()

    def add_frame(self):
        self.collect()
        frames = self.profiles[self.p_idx]["frames"]
        frames.append(self._blank_frame())
        self.f_idx = len(frames) - 1
        self.load()

    def dup_frame(self):
        self.collect()
        frames = self.profiles[self.p_idx]["frames"]
        frames.append(copy.deepcopy(frames[self.f_idx]))
        self.f_idx = len(frames) - 1
        self.load()

    def del_frame(self):
        self.collect()
        frames = self.profiles[self.p_idx]["frames"]
        if len(frames) <= 1:
            messagebox.showinfo("Presence Customiser", "You must keep at least one frame.")
            return
        del frames[self.f_idx]
        self.f_idx = max(0, self.f_idx - 1)
        self.load()

    def move_frame(self, delta: int):
        self.collect()
        frames = self.profiles[self.p_idx]["frames"]
        j = self.f_idx + delta
        if 0 <= j < len(frames):
            frames[self.f_idx], frames[j] = frames[j], frames[self.f_idx]
            self.f_idx = j
            self.load()

    def preview(self):
        variables = dict(self.app.engine.snapshot.get("vars") or {})
        lines = [render(self.fv[k].get(), variables) for k in ("details", "state")]
        self.preview_lbl.configure(text="Preview: " + "  /  ".join(l for l in lines if l))

    def save(self):
        self.collect()
        self.refresh_list()
        self.app.persist("Profile saved.")
        self.app.after_profiles_changed()


# =============================================================================== Rules
class RulesTab:
    def __init__(self, app: "App", parent):
        self.app = app
        self.idx = 0
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(parent, width=230)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        ctk.CTkLabel(left, text="Rules", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(8, 2))
        ctk.CTkLabel(left, text="Highest priority wins", text_color="gray",
                     font=ctk.CTkFont(size=11)).pack()
        self.rlist = ctk.CTkScrollableFrame(left, width=210)
        self.rlist.pack(fill="both", expand=True, padx=6, pady=4)
        for text, cmd in (("+ New", self.add), ("Duplicate", self.dup), ("Delete", self.delete)):
            ctk.CTkButton(left, text=text, command=cmd, width=190).pack(pady=3, padx=8)

        right = ctk.CTkScrollableFrame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        _title(right, "Rule")
        self.name = ctk.StringVar()
        self.profile = ctk.StringVar()
        self.priority = ctk.StringVar()
        self.enabled = ctk.BooleanVar(value=True)
        _entry(app, right, "Name", self.name)
        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text="Profile to activate", width=200, anchor="w").pack(side="left")
        self.profile_menu = ctk.CTkOptionMenu(row, variable=self.profile, values=["—"], width=260)
        self.profile_menu.pack(side="left")
        _entry(app, right, "Priority", self.priority, "50")
        ctk.CTkSwitch(right, text="Rule enabled", variable=self.enabled).pack(anchor="w", pady=4)

        _title(right, "Conditions (every condition you fill in must match)")
        self.wv = {k: ctk.StringVar() for k, _, _ in RULE_LIST_FIELDS + RULE_TEXT_FIELDS}
        for key, label, ph in RULE_LIST_FIELDS + RULE_TEXT_FIELDS:
            _entry(app, right, label, self.wv[key], ph)
        _hint(right, "Leave empty whatever you don't use. “Custom condition” accepts: cpu > 80, app == Chrome, "
                     "window contains youtube, spotify, !project, combined with “and”. The variables are the "
                     "ones listed on the dashboard.")
        ctk.CTkButton(right, text="Save rule", fg_color=app.accent, height=36,
                      command=self.save).pack(fill="x", pady=(16, 8))
        self.reload()

    @property
    def rules(self) -> list:
        return self.app.cfg.setdefault("rules", [])

    def reload(self):
        names = [p["name"] for p in self.app.cfg["profiles"]] or ["—"]
        self.profile_menu.configure(values=names)
        self.idx = min(self.idx, max(0, len(self.rules) - 1))
        self.refresh_list()
        self.load()

    def refresh_list(self):
        for w in self.rlist.winfo_children():
            w.destroy()
        for i, rule in enumerate(self.rules):
            selected = i == self.idx
            mark = "" if rule.get("enabled", True) else "⏸ "
            ctk.CTkButton(self.rlist, text=f"{mark}{rule.get('name', '?')}  ({rule.get('priority', 0)})",
                          anchor="w", fg_color=self.app.accent if selected else "transparent",
                          text_color="white" if selected else ("black", "white"),
                          hover_color=("#d0d0dc", "#3a3c42"),
                          command=lambda i=i: self.select(i)).pack(fill="x", pady=1)

    def load(self):
        for var in self.wv.values():
            var.set("")
        if not self.rules:
            self.name.set("")
            self.priority.set("")
            return
        rule = self.rules[self.idx]
        when = rule.get("when") or {}
        self.name.set(rule.get("name", ""))
        self.profile.set(rule.get("profile", ""))
        self.priority.set(str(rule.get("priority", 0)))
        self.enabled.set(bool(rule.get("enabled", True)))
        for key, _, _ in RULE_LIST_FIELDS:
            self.wv[key].set(", ".join(map(str, when.get(key, []))))
        for key, _, _ in RULE_TEXT_FIELDS:
            if key in when:
                value = when[key]
                self.wv[key].set(", ".join(map(str, value)) if isinstance(value, list) else str(value))

    def collect(self):
        if not self.rules:
            return
        rule = self.rules[self.idx]
        rule["name"] = self.name.get().strip() or "Rule"
        rule["profile"] = self.profile.get()
        try:
            rule["priority"] = int(float(self.priority.get().replace(",", ".")))
        except ValueError:
            rule["priority"] = 0
        rule["enabled"] = bool(self.enabled.get())
        when: dict = {}
        for key, _, _ in RULE_LIST_FIELDS:
            items = _split_csv(self.wv[key].get())
            if items:
                when[key] = items
        for key, _, _ in RULE_TEXT_FIELDS:
            text = self.wv[key].get().strip()
            if not text:
                continue
            if key in ("cpu_above", "ram_above", "battery_below", "idle_over"):
                when[key] = _num_or_text(text)
            else:
                when[key] = text
        rule["when"] = when

    def select(self, i: int):
        self.collect()
        self.idx = i
        self.refresh_list()
        self.load()

    def add(self):
        self.collect()
        profile = self.app.cfg["profiles"][0]["name"] if self.app.cfg["profiles"] else ""
        self.rules.append({"name": "New rule", "profile": profile, "priority": 10, "enabled": True, "when": {}})
        self.idx = len(self.rules) - 1
        self.refresh_list()
        self.load()

    def dup(self):
        if not self.rules:
            return
        self.collect()
        clone = copy.deepcopy(self.rules[self.idx])
        clone["name"] += " (copy)"
        self.rules.append(clone)
        self.idx = len(self.rules) - 1
        self.refresh_list()
        self.load()

    def delete(self):
        if not self.rules:
            return
        del self.rules[self.idx]
        self.idx = max(0, self.idx - 1)
        self.refresh_list()
        self.load()
        self.app.persist("Rule deleted.")

    def save(self):
        self.collect()
        self.refresh_list()
        self.app.persist("Rule saved.")


# ============================================================================ Variables
class VariablesTab:
    def __init__(self, app: "App", parent):
        self.app = app
        parent.grid_columnconfigure((0, 1), weight=1)
        parent.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        _title(left, "Custom variables")
        _hint(left, "One per line: name = value. They can use the variables defined above them "
                    "(e.g. title = {nickname} • {day_part}).")
        self.vars_box = ctk.CTkTextbox(left, height=200, font=ctk.CTkFont(family="Consolas", size=12))
        self.vars_box.pack(fill="both", expand=True)
        _title(left, "Application names")
        _hint(left, "process = display name  (feeds the {app} variable).")
        self.apps_box = ctk.CTkTextbox(left, height=200, font=ctk.CTkFont(family="Consolas", size=12))
        self.apps_box.pack(fill="both", expand=True)
        ctk.CTkButton(left, text="Save", fg_color=app.accent, height=36, command=self.save).pack(
            fill="x", pady=(10, 0))

        _title(right, "Plugins")
        _hint(right, "Python files in the plugins folder add their own variables. "
                     "An example (quote, emoji_clock) is included.")
        self.plugin_lbl = ctk.CTkLabel(right, text="", anchor="nw", justify="left", wraplength=420)
        self.plugin_lbl.pack(fill="both", expand=True)
        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Reload plugins", command=self.reload_plugins).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="Open folder", command=self.open_folder).pack(side="left")
        self.reload()

    def reload(self):
        _set_text(self.vars_box, "\n".join(f"{k} = {v}" for k, v in self.app.cfg.get("variables", {}).items()))
        _set_text(self.apps_box, "\n".join(f"{k} = {v}" for k, v in self.app.cfg.get("app_names", {}).items()))
        self.show_plugins()

    def show_plugins(self):
        lines = []
        for plugin in self.app.engine.plugins:
            lines.append(f"{'✗' if plugin.error else '✓'} {plugin.name}" + (f"  ({plugin.error})" if plugin.error else ""))
        for err in self.app.engine.plugin_errors:
            lines.append(f"⚠ {err}")
        self.plugin_lbl.configure(text="\n".join(lines) or "No plugins loaded.")

    def reload_plugins(self):
        self.app.engine.reload_plugins()
        self.show_plugins()
        self.app.toast("Plugins reloaded.")

    def open_folder(self):
        path = str(config_mod.home_dir() / "plugins")
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            messagebox.showinfo("Presence Customiser", path)

    def save(self):
        self.app.cfg["variables"] = _parse_pairs(self.vars_box.get("1.0", "end"))
        self.app.cfg["app_names"] = _parse_pairs(self.apps_box.get("1.0", "end"))
        self.app.persist("Variables saved.")


# ==================================================================== Advanced JSON
class JsonTab:
    def __init__(self, app: "App", parent):
        self.app = app
        _hint(parent, "Everything can be edited here: this is the full configuration. "
                      "Validate, then apply; if there is a syntax error nothing is changed.")
        self.box = ctk.CTkTextbox(parent, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
        self.box.pack(fill="both", expand=True, pady=(0, 8))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Validate and apply", fg_color=app.accent, command=self.apply).pack(side="left")
        ctk.CTkButton(row, text="Reload", command=self.reload).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Import…", command=self.import_file).pack(side="left")
        ctk.CTkButton(row, text="Export…", command=self.export_file).pack(side="left", padx=6)
        self.reload()

    def reload(self):
        _set_text(self.box, json.dumps(self.app.cfg, indent=2, ensure_ascii=False))

    def _parse(self, text: str):
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("the root must be a JSON object")
            return config_mod.normalize(data)
        except Exception as exc:
            messagebox.showerror("Invalid JSON", str(exc))
            return None

    def apply(self):
        cfg = self._parse(self.box.get("1.0", "end"))
        if cfg is None:
            return
        self.app.replace_config(cfg)

    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            text = open(path, encoding="utf-8").read()
        except OSError as exc:
            messagebox.showerror("Import", str(exc))
            return
        cfg = self._parse(text)
        if cfg is not None:
            self.app.replace_config(cfg)

    def export_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="presence-customiser-config.json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            open(path, "w", encoding="utf-8").write(json.dumps(self.app.cfg, indent=2, ensure_ascii=False))
            self.app.toast("Configuration exported.")


# ================================================================================ Settings
class SettingsTab:
    def __init__(self, app: "App", parent):
        self.app = app
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True)
        s = app.cfg["settings"]
        self.client_id = ctk.StringVar()
        self.min_interval = ctk.StringVar()
        self.default_profile = ctk.StringVar()
        self.hidden_profile = ctk.StringVar()
        self.appearance = ctk.StringVar()
        self.accent = ctk.StringVar()
        self.sw = {k: ctk.BooleanVar() for k in
                   ("autostart_engine", "tray", "minimize_to_tray", "start_minimized", "windows_autostart")}

        _title(scroll, "Discord")
        _entry(app, scroll, "Client ID (Application ID)", self.client_id, "e.g. 123456789012345678")
        _hint(scroll, "Create an application at discord.com/developers/applications, copy its Application ID "
                      "here, then add your images under Rich Presence > Art Assets. The application's name is "
                      "what Discord displays (“Playing …”).")
        _entry(app, scroll, "Minimum interval (s)", self.min_interval, "15")
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text="Default profile", width=200, anchor="w").pack(side="left")
        self.default_menu = ctk.CTkOptionMenu(row, variable=self.default_profile, values=["—"], width=260)
        self.default_menu.pack(side="left")

        _title(scroll, "Application")
        ctk.CTkSwitch(scroll, text="Enable presence on launch", variable=self.sw["autostart_engine"]).pack(anchor="w", pady=3)
        ctk.CTkSwitch(scroll, text="System tray icon", variable=self.sw["tray"]).pack(anchor="w", pady=3)
        ctk.CTkSwitch(scroll, text="Minimize to tray when closing", variable=self.sw["minimize_to_tray"]).pack(anchor="w", pady=3)
        ctk.CTkSwitch(scroll, text="Start minimized", variable=self.sw["start_minimized"]).pack(anchor="w", pady=3)
        ctk.CTkSwitch(scroll, text="Launch with Windows", variable=self.sw["windows_autostart"]).pack(anchor="w", pady=3)

        _title(scroll, "Appearance")
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text="Theme", width=200, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(row, variable=self.appearance, values=["dark", "light", "system"], width=160).pack(side="left")
        _entry(app, scroll, "Accent color (restart required)", self.accent, "#7c5cff")

        _title(scroll, "Privacy")
        _hint(scroll, "If one of these processes or words appears in the active window, Presence Customiser switches to "
                      "the privacy profile and hides process, window, app, file, project and spotify.")
        ctk.CTkLabel(scroll, text="Processes to hide (one per line)", anchor="w").pack(fill="x")
        self.hide_procs = ctk.CTkTextbox(scroll, height=90)
        self.hide_procs.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(scroll, text="Words to hide in the window title (one per line)", anchor="w").pack(fill="x")
        self.hide_words = ctk.CTkTextbox(scroll, height=90)
        self.hide_words.pack(fill="x", pady=(0, 6))
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text="Privacy profile", width=200, anchor="w").pack(side="left")
        self.hidden_menu = ctk.CTkOptionMenu(row, variable=self.hidden_profile, values=["—"], width=260)
        self.hidden_menu.pack(side="left")

        _title(scroll, "About")
        _hint(scroll, f"{DISPLAY_NAME} v{__version__}. New versions are published in the project's GitHub "
                      "releases: download the latest .exe and replace the old one (your configuration is "
                      "kept).")
        about = ctk.CTkFrame(scroll, fg_color="transparent")
        about.pack(fill="x", pady=2)
        ctk.CTkButton(about, text="⬇ Download Presence Customiser", command=app.open_releases).pack(side="left")
        ctk.CTkButton(about, text="Source code", command=lambda: app.open_url(REPO_URL)).pack(side="left", padx=6)
        ctk.CTkButton(about, text="Report a bug", command=lambda: app.open_url(ISSUES_URL)).pack(side="left")

        ctk.CTkButton(scroll, text="Save settings", fg_color=app.accent, height=36,
                      command=self.save).pack(fill="x", pady=(16, 8))
        self.reload()

    def reload(self):
        s = self.app.cfg["settings"]
        privacy = s.get("privacy", {})
        names = [p["name"] for p in self.app.cfg["profiles"]] or ["—"]
        self.default_menu.configure(values=names)
        self.hidden_menu.configure(values=names)
        self.client_id.set(s.get("client_id", ""))
        self.min_interval.set(str(s.get("min_interval", 15)))
        self.default_profile.set(self.app.cfg.get("default_profile", names[0]))
        self.hidden_profile.set(privacy.get("hidden_profile", names[0]))
        self.appearance.set(s.get("appearance", "dark"))
        self.accent.set(s.get("accent", "#7c5cff"))
        for key in ("autostart_engine", "tray", "minimize_to_tray", "start_minimized"):
            self.sw[key].set(bool(s.get(key, False)))
        self.sw["windows_autostart"].set(sysutil.is_autostart_enabled())
        _set_text(self.hide_procs, "\n".join(privacy.get("hidden_processes", [])))
        _set_text(self.hide_words, "\n".join(privacy.get("hidden_words", [])))

    def save(self):
        cfg = self.app.cfg
        s = cfg["settings"]
        s["client_id"] = self.client_id.get().strip()
        try:
            s["min_interval"] = max(15, int(float(self.min_interval.get().replace(",", "."))))
        except ValueError:
            s["min_interval"] = 15
        cfg["default_profile"] = self.default_profile.get()
        for key in ("autostart_engine", "tray", "minimize_to_tray", "start_minimized"):
            s[key] = bool(self.sw[key].get())
        s["appearance"] = self.appearance.get()
        accent = self.accent.get().strip()
        s["accent"] = accent if accent.startswith("#") and len(accent) in (4, 7) else "#7c5cff"
        s["privacy"] = {
            "hidden_processes": [l.strip() for l in self.hide_procs.get("1.0", "end").splitlines() if l.strip()],
            "hidden_words": [l.strip() for l in self.hide_words.get("1.0", "end").splitlines() if l.strip()],
            "hidden_profile": self.hidden_profile.get(),
        }
        ctk.set_appearance_mode(s["appearance"])
        if sys.platform == "win32":
            if not sysutil.set_autostart(bool(self.sw["windows_autostart"].get())):
                self.app.toast("Could not change the Windows startup setting.")
        self.app.persist("Settings saved.")
        self.app.sync_tray()


# ===================================================================================== App
class App(ctk.CTk):
    def __init__(self, engine, cfg: dict, start_minimized: bool = False):
        super().__init__()
        self.engine = engine
        self.cfg = cfg
        settings = cfg["settings"]
        ctk.set_appearance_mode(settings.get("appearance", "dark"))
        self.accent = settings.get("accent", "#7c5cff")
        self.title(f"{DISPLAY_NAME} v{__version__}")
        self.geometry("1040x760")
        self.minsize(920, 640)
        self._focus_entry = None
        self.tray = None
        self._toast_job = None

        self.footer = ctk.CTkLabel(self, text="", anchor="w", text_color="gray")
        self.footer.pack(side="bottom", fill="x", padx=14, pady=(0, 6))
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        self.dashboard = DashboardTab(self, self.tabs.add("Dashboard"))
        self.profiles_tab = ProfilesTab(self, self.tabs.add("Profiles"))
        self.rules_tab = RulesTab(self, self.tabs.add("Rules"))
        self.vars_tab = VariablesTab(self, self.tabs.add("Variables"))
        self.json_tab = JsonTab(self, self.tabs.add("Advanced JSON"))
        self.settings_tab = SettingsTab(self, self.tabs.add("Settings"))

        problems = config_mod.validate_config(cfg)
        if problems:
            self.toast("Config: " + problems[0])

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.engine.start()
        if settings.get("autostart_engine", True):
            self.engine.set_enabled(True)
        self.sync_tray()
        if start_minimized or settings.get("start_minimized"):
            self.after(200, self.hide_window)
        if not settings.get("client_id") and not any(p.get("client_id") for p in cfg["profiles"]):
            self.tabs.set("Settings")
            self.toast("Paste your Discord Client ID to get started.")
        self.after(1000, self._tick)

    # ------------------------------------------------------------------ utilities
    def track(self, entry):
        entry.bind("<FocusIn>", lambda _e, w=entry: setattr(self, "_focus_entry", w))

    def insert_variable(self, name: str):
        if self._focus_entry is not None:
            try:
                self._focus_entry.insert("insert", "{" + name + "}")
            except Exception:
                pass

    def toast(self, message: str):
        self.footer.configure(text=message)
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(6000, lambda: self.footer.configure(text=""))

    def persist(self, message: str = ""):
        problems = config_mod.validate_config(self.cfg)
        config_mod.save_config(self.cfg)
        self.engine.set_config(self.cfg)
        self.toast((message + "  ⚠ " + problems[0]) if problems else message)

    def after_profiles_changed(self):
        self.dashboard.reload_profiles()
        self.rules_tab.reload()
        self.settings_tab.reload()

    def replace_config(self, cfg: dict):
        self.cfg = cfg
        self.persist("Configuration applied.")
        self.profiles_tab.reload()
        self.rules_tab.reload()
        self.vars_tab.reload()
        self.settings_tab.reload()
        self.dashboard.reload_profiles()
        self.json_tab.reload()

    def toggle(self):
        self.engine.set_enabled(not self.engine.enabled)

    def open_url(self, url: str):
        if "OWNER" in url:
            self.toast("Replace OWNER with your GitHub username in presence_customiser/__init__.py")
            return
        webbrowser.open(url)

    def open_releases(self):
        self.open_url(RELEASES_URL)

    # --------------------------------------------------------------------- loop
    def _tick(self):
        try:
            self.dashboard.refresh(self.engine.snapshot or {}, self.engine)
        except Exception:
            pass
        self.after(1000, self._tick)

    # ----------------------------------------------------------------------- tray
    def sync_tray(self):
        want = bool(self.cfg["settings"].get("tray", True))
        if want and self.tray is None:
            self._start_tray()
        elif not want and self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.tray = None

    def _start_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((4, 4, 60, 60), fill=self.accent)
        draw.rectangle((24, 18, 30, 46), fill="white")
        draw.rectangle((30, 18, 42, 26), fill="white")
        draw.rectangle((36, 26, 42, 34), fill="white")
        draw.rectangle((30, 34, 42, 40), fill="white")
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda icon, item: self.after(0, self.show_window), default=True),
            pystray.MenuItem("Enable / Disable", lambda icon, item: self.after(0, self.toggle)),
            pystray.MenuItem("Quit", lambda icon, item: self.after(0, self.quit_app)),
        )
        try:
            self.tray = pystray.Icon("Presence Customiser", image, "Presence Customiser", menu)
            self.tray.run_detached()
        except Exception:
            self.tray = None

    def hide_window(self):
        if self.tray is not None:
            self.withdraw()
        else:
            self.iconify()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close(self):
        if self.tray is not None and self.cfg["settings"].get("minimize_to_tray", True):
            self.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        self.engine.shutdown()
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.destroy()


def run_app(engine, cfg: dict, start_minimized: bool = False):
    app = App(engine, cfg, start_minimized=start_minimized)
    app.mainloop()
