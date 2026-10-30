"""Moteur de templates : {variable|filtre:arg|filtre?valeur_par_defaut} + conditions simples."""
from __future__ import annotations

import re

_TOKEN = re.compile(r"\{([^{}]+)\}")


def _num(value):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def apply_filter(spec: str, value) -> str:
    name, _, arg = spec.partition(":")
    name = name.strip().lower()
    s = "" if value is None else str(value)
    try:
        if name == "upper":
            return s.upper()
        if name == "lower":
            return s.lower()
        if name == "title":
            return s.title()
        if name == "cap":
            return s[:1].upper() + s[1:]
        if name == "strip":
            return s.strip()
        if name == "trunc":
            n = int(arg or 30)
            return s if len(s) <= n else s[: max(1, n - 1)].rstrip() + "…"
        if name == "round":
            n = _num(s)
            digits = int(arg or 0)
            if n is None:
                return s
            return str(int(round(n))) if digits == 0 else f"{n:.{digits}f}"
        if name == "pad":
            return s.zfill(int(arg or 2))
        if name == "clean":
            return re.sub(r"^[\s●•*·]+", "", s).strip()
        if name == "noext":
            return re.sub(r"\.[A-Za-z0-9]{1,6}$", "", re.sub(r"^[\s●•*·]+", "", s)).strip()
        if name == "bar":
            n = _num(s)
            width = int(arg or 10)
            if n is None:
                return s
            filled = max(0, min(width, round(n / 100 * width)))
            return "▰" * filled + "▱" * (width - filled)
        if name == "default":
            return s or arg
        if name == "replace":
            a, _, b = arg.partition("=")
            return s.replace(a, b)
        if name == "prefix":
            return arg + s if s else s
        if name == "suffix":
            return s + arg if s else s
    except Exception:
        return s
    return s


def render(template: str, variables: dict) -> str:
    """Remplace {var}, {var?défaut}, {var|filtre:arg|filtre2} dans le texte."""
    if not template:
        return ""

    def repl(match: re.Match) -> str:
        parts = match.group(1).split("|")
        head = parts[0]
        default = None
        if "?" in head:
            head, default = head.split("?", 1)
        value = variables.get(head.strip())
        if value in (None, ""):
            value = default if default is not None else ""
        for spec in parts[1:]:
            value = apply_filter(spec, value)
        return "" if value is None else str(value)

    return _TOKEN.sub(repl, template)


# ---------------------------------------------------------------- conditions

_OPS = (">=", "<=", "==", "!=", " contains ", ">", "<")


def _truthy(value) -> bool:
    return str(value or "").strip().lower() not in ("", "0", "false", "none")


def _check_one(part: str, variables: dict) -> bool:
    part = part.strip()
    if not part:
        return True
    for op in _OPS:
        if op in part:
            left, right = part.split(op, 1)
            lval = str(variables.get(left.strip(), ""))
            rval = right.strip().strip("'\"")
            ln, rn = _num(lval), _num(rval)
            if op == " contains ":
                return rval.casefold() in lval.casefold()
            if ln is not None and rn is not None:
                a, b = ln, rn
            else:
                a, b = lval.casefold(), rval.casefold()
            return {
                ">=": a >= b, "<=": a <= b, "==": a == b,
                "!=": a != b, ">": a > b, "<": a < b,
            }[op]
    if part.startswith("!"):
        return not _truthy(variables.get(part[1:].strip(), ""))
    return _truthy(variables.get(part, ""))


def check_condition(expr: str, variables: dict) -> bool:
    """Ex : "cpu > 80", "app == Chrome and hour >= 22", "spotify", "!project", "window contains youtube"."""
    expr = (expr or "").strip()
    if not expr:
        return True
    return all(_check_one(p, variables) for p in re.split(r"\s+(?:and|&&)\s+", expr))
