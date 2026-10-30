"""User plugins: .py files that add their own variables."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Plugin:
    name: str
    path: Path
    module: object | None = None
    error: str = ""


def load_plugins(directory: Path) -> list[Plugin]:
    plugins: list[Plugin] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        plugin = Plugin(name=path.stem, path=path)
        try:
            spec = importlib.util.spec_from_file_location(f"pf_plugin_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            plugin.module = module
        except Exception as exc:  # a broken plugin must never crash the app
            plugin.error = f"{type(exc).__name__}: {exc}"
        plugins.append(plugin)
    return plugins


def run_plugins(plugins: list[Plugin], base_vars: dict) -> tuple[dict, list[str]]:
    """Call get_variables(vars) and/or VARIABLES = {name: function} of each plugin."""
    out: dict = {}
    errors: list[str] = []
    for plugin in plugins:
        if plugin.error:
            errors.append(f"{plugin.name}: {plugin.error}")
            continue
        module = plugin.module
        try:
            fn = getattr(module, "get_variables", None)
            if callable(fn):
                result = fn(dict(base_vars))
                if isinstance(result, dict):
                    out.update({str(k): "" if v is None else str(v) for k, v in result.items()})
            for name, func in (getattr(module, "VARIABLES", None) or {}).items():
                out[str(name)] = str(func(dict(base_vars)))
        except Exception as exc:
            errors.append(f"{plugin.name}: {type(exc).__name__}: {exc}")
    return out, errors
