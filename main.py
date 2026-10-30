"""Point d'entrée de Presence Customiser.

  python main.py              -> interface graphique
  python main.py --minimized  -> démarre réduit (tray)
  python main.py --headless   -> sans interface, dans le terminal
  python main.py --once       -> calcule une fois la présence et l'affiche (test, rien n'est envoyé)
"""
import argparse
import json
import sys
import time

from presence_customiser import config
from presence_customiser.engine import Engine
from presence_customiser.rpc import RPCClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Presence Customiser : Rich Presence Discord personnalisable")
    parser.add_argument("--minimized", action="store_true", help="démarrer réduit dans la barre système")
    parser.add_argument("--headless", action="store_true", help="lancer sans interface graphique")
    parser.add_argument("--once", action="store_true", help="afficher la présence calculée et quitter")
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
        print(json.dumps({"profil": snap["profile"], "règle": snap["rule"],
                          "payload": snap["payload"], "variables": snap["vars"]},
                         ensure_ascii=False, indent=2, default=list))
        return 0

    engine = Engine(cfg, rpc=RPCClient(), plugins_dir=plugins_dir)

    if args.headless:
        engine.set_enabled(True)
        engine.start()
        print("Presence Customiser lancé (Ctrl+C pour quitter).")
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
