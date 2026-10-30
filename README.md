# Presence Customiser

A **fully customizable Discord Rich Presence**: profiles, rotating pages, automatic rules, live variables,
Python plugins, privacy controls, and a configuration that is 100% JSON.

[**⬇ Download Presence Customiser**](https://github.com/zodiakgh/Presence-Customiser/releases/latest) (Windows 10/11)

## Quick start

1. Download `PresenceCustomiser.exe` from the [releases](https://github.com/zodiakgh/Presence-Customiser/releases/latest) and run it.
2. Go to <https://discord.com/developers/applications>, create an application and copy its **Application ID**.
   Its **name** is what will be shown on your profile ("Playing *name*").
3. Paste the ID in **Settings → Client ID** and save.
4. Click **Enable presence**. Discord must be open on your PC (the desktop app, not the browser).

To show images: in the developer portal go to **Rich Presence → Art Assets**, upload your images, then use their
name (or an `https://` URL) in "Large image" / "Small image".

## Run from source

```bash
pip install -r requirements.txt
python main.py              # graphical interface
python main.py --minimized  # start in the system tray
python main.py --headless   # no interface, runs in the terminal
python main.py --once       # print the computed presence without sending anything
```

## What you can customize

**Profiles and frames.** A profile is an activity type (playing / listening / watching / competing), a timer
(none, since the profile started, since the app started, since the PC booted, countdown), and a list of
**frames** that rotate (rotation ≥ 15 s, shuffle optional). Each frame has two lines of text, two images with
tooltips, a party size (`1/4`), up to 2 buttons and a display condition (`show_if`).
A profile can have its own Client ID, and therefore its own displayed application name.

**Templates.** `{variable}`, `{variable?default}`, `{variable?default|filter:arg|filter2}`

| Filter | Effect |
|---|---|
| `upper` `lower` `title` `cap` | letter case |
| `trunc:N` | cut to N characters with "…" |
| `round:N` `pad:N` | rounding, leading zeros |
| `bar:N` | progress bar `▰▰▰▱▱` for a percentage |
| `noext` `clean` | strip the extension / the `●` bullets |
| `prefix:x` `suffix:x` | add text if the value is not empty |
| `replace:a=b` `default:x` `strip` | replacement, default value, whitespace |

**Built-in variables.** `time` `date` `hour` `minute` `weekday` `weekday_num` `day_part` `cpu` `ram` `battery`
`uptime` `session` `process` `window` `app` `file` `project` `idle` `idle_min` `spotify` `os` `profile`
`profile_time`. `file` and `project` are extracted from the titles of VS Code, Cursor, PyCharm, etc. You can add
your own (**Variables** tab, `name = value`, chaining allowed) and through **plugins**.

**Automatic rules.** The profile switches by itself. A rule = a profile + a priority + conditions
(every condition you fill in must match): `process`, `window_contains`, `window_regex`, `time_between`
(`22:00-06:00`), `weekdays`, `cpu_above`, `ram_above`, `battery_below`, `idle_over` and `expr` (free condition:
`cpu > 80`, `app == Chrome and hour >= 22`, `window contains youtube`, `spotify`, `!project`).

**Plugins.** A `.py` file in the `plugins` folder ("Open folder" button) that defines `get_variables(vars)` and
returns a `dict`. An example is created on first launch. Plugins are Python code run as-is: only install ones you
wrote or reviewed yourself.

**Privacy.** If a process (`KeePass.exe`…) or a word (`bank`, `password`…) shows up in the active window, the app
switches to the privacy profile and hides `process`, `window`, `app`, `file`, `project` and `spotify`.
Adjust it in **Settings**.

**Advanced JSON.** The tab of the same name edits the whole configuration (import / export to share it).
It is stored in `%APPDATA%\Presence Customiser\config.json`.

## Discord limits

- The Discord desktop app must be running on the same PC.
- Buttons are not visible on your own profile, only to other people.
- Discord limits the update rate: at least 15 s between two updates.
- Text: 128 characters max per line, 2 minimum (handled automatically).

## Publishing a release

The repository is <https://github.com/zodiakgh/Presence-Customiser>.

1. Push the code to `main`.
2. Publish a version: `git tag v1.0.0 && git push origin v1.0.0`. The `.github/workflows/release.yml` action
   builds `PresenceCustomiser.exe` and adds it to the **Releases** page: that is what the
   "Download Presence Customiser" button downloads.
3. Website (optional): **Settings → Pages → Branch `main`, folder `/docs`**. It has the same button, pointing to
   the latest release.

To build the exe by hand: `build_exe.bat` (outputs `dist\PresenceCustomiser.exe`).
The exe is not code-signed: Windows SmartScreen may show a warning on first launch
("More info → Run anyway").

## Tests

```bash
python tests/test_engine.py       # engine: templates, rules, privacy, sending, validation
python tests/test_ui_smoke.py     # interface logic with a fake toolkit
```

*Community project, not affiliated with Discord Inc.*
