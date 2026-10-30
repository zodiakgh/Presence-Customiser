"""Connection to Discord (Rich Presence over local IPC, using the pypresence library).

Important: every call must come from the same thread (dedicated asyncio loop);
the engine thread takes care of that.
"""
from __future__ import annotations

import asyncio

_ERRORS = {
    "DiscordNotFound": "Discord not found: start the Discord desktop app (not the browser).",
    "InvalidID": "Invalid Client ID: check the Application ID in the developer portal.",
    "InvalidPipe": "Discord is not responding, try again in a moment.",
    "ConnectionRefusedError": "Connection refused by Discord.",
    "FileNotFoundError": "Discord not found: start the Discord desktop app (not the browser).",
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
            self.last_error = "pypresence is not installed (pip install pypresence)."
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
            except TypeError:  # older pypresence without activity_type
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
