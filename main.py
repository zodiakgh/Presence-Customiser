"""Presence Customiser entry point.

  python main.py              -> graphical interface
  python main.py --minimized  -> start minimized (tray)
  python main.py --headless   -> no interface, runs in the terminal
  python main.py --once       -> compute the presence once and print it (test, nothing is sent)
"""
import argparse
import json
import sys
import time

from presence_customiser import config
from presence_customiser.engine import Engine
from presence_customiser.rpc import RPCClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Presence Customiser: a fully customizable Discord Rich Presence")
    parser.add_argument("--minimized", action="store_true", help="start minimized to the system tray")
    parser.add_argument("--headless", action="store_true", help="run without the graphical interface")
    parser.add_argument("--once", action="store_true", help="print the computed presence and exit")
    args = parser.parse_args()

    cfg = config.load_config()
    config.ensure_example_plugin()
    problems = config.validate_config(cfg)
    for problem in problems:
        print(f"[config] {problem}", file=sys.stderr)

    plugins_dir = config.home_dir() / "plugins"

    if args.once:
        engine = Engine(cfg, rpc=None, plugins_dir=plugins_dir)
        engine.ctx.cached("spotify", 0, lambda: "")
        snap = engine.tick(send=False)
        print(json.dumps({"profile": snap["profile"], "rule": snap["rule"],
                          "payload": snap["payload"], "variables": snap["vars"]},
                         ensure_ascii=False, indent=2, default=list))
        return 0

    engine = Engine(cfg, rpc=RPCClient(), plugins_dir=plugins_dir)

    if args.headless:
        engine.set_enabled(True)
        engine.start()
        print("Presence Customiser started (Ctrl+C to quit).")
        try:
            while True:
                time.sleep(5)
                snap = engine.snapshot
                print(f"[{snap.get('profile', '?')}] {engine.status}")
        except KeyboardInterrupt:
            engine.shutdown()
        return 0

    from presence_customiser.ui import run_app
    run_app(engine, cfg, start_minimized=args.minimized)
    return 0


if __name__ == "__main__":
    sys.exit(main())
