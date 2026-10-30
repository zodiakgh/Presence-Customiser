"""Connexion à Discord (Rich Presence via IPC local, bibliothèque pypresence).

Important : tous les appels doivent venir du même thread (boucle asyncio dédiée),
c'est le thread du moteur qui s'en charge.
"""
from __future__ import annotations

import asyncio

_ERRORS = {
    "DiscordNotFound": "Discord introuvable : lance l'application Discord (pas le navigateur).",
    "InvalidID": "Client ID invalide : vérifie l'Application ID du portail développeur.",
    "InvalidPipe": "Discord ne répond pas, réessaie dans un instant.",
    "ConnectionRefusedError": "Connexion refusée par Discord.",
    "FileNotFoundError": "Discord introuvable : lance l'application Discord (pas le navigateur).",
}


class RPCClient:
    def __init__(self) -> None:
        self._rpc = None
        self.client_id: str | None = None
        self.connected = False
        self.last_error = ""

    def connect(self, client_id: str) -> bool:
        self.close()
        try:
            from pypresence import Presence
        except ImportError:
            self.last_error = "pypresence n'est pas installé (pip install pypresence)."
            return False
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._rpc = Presence(str(client_id), loop=loop)
            self._rpc.connect()
            self.client_id = str(client_id)
            self.connected = True
            self.last_error = ""
            return True
        except Exception as exc:
            self.connected = False
            self._rpc = None
            self.last_error = _ERRORS.get(type(exc).__name__, f"{type(exc).__name__}: {exc}")
            return False

    def update(self, payload: dict) -> bool:
        if not (self.connected and self._rpc):
            return False
        kwargs: dict = {}
        for key in ("details", "state", "start", "end", "large_image", "large_text",
                    "small_image", "small_text", "buttons"):
            if payload.get(key):
                kwargs[key] = payload[key]
        if payload.get("party"):
            kwargs["party_size"] = list(payload["party"])
        try:
            from pypresence import ActivityType
            kwargs["activity_type"] = getattr(ActivityType, str(payload.get("type", "playing")).upper())
        except Exception:
            pass
        try:
            try:
                self._rpc.update(**kwargs)
            except TypeError:  # ancienne version de pypresence sans activity_type
                kwargs.pop("activity_type", None)
                self._rpc.update(**kwargs)
            return True
        except Exception as exc:
            self.connected = False
            self.last_error = _ERRORS.get(type(exc).__name__, f"{type(exc).__name__}: {exc}")
            return False

    def clear(self) -> None:
        try:
            if self.connected and self._rpc:
                self._rpc.clear()
        except Exception:
            self.connected = False

    def close(self) -> None:
        try:
            if self._rpc:
                self._rpc.close()
        except Exception:
            pass
        self._rpc = None
        self.connected = False
        self.client_id = None
