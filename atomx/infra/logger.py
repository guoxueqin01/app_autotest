"""Unified logging facade.

Uses `loguru` when available so callers can configure sinks; falls back to
stdlib logging otherwise. Exposes a small `Logger` shim so higher layers
don't have to care about the backend.
"""
from __future__ import annotations

import logging
import os
from typing import Any


class Logger:
    """Thin wrapper over loguru / stdlib logger."""

    def __init__(self, name: str = "atomx") -> None:
        self.name = name
        try:
            from loguru import logger  # type: ignore

            self._loguru = logger
            self._backend = "loguru"
        except ImportError:
            self._loguru = None
            self._stdlib = logging.getLogger(name)
            if not self._stdlib.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
                self._stdlib.addHandler(handler)
            self._stdlib.setLevel(os.environ.get("ATOMX_LOG_LEVEL", "INFO").upper())
            self._backend = "stdlib"

    @property
    def backend(self) -> str:
        return self._backend

    def _emit(self, level: str, message: str, *args: Any) -> None:
        text = message
        if args:
            try:
                text = message % args
            except Exception:  # noqa: BLE001
                text = f"{message} {args}"
        if self._loguru is not None:
            getattr(self._loguru, level)(text)
        else:
            numeric = {
                "debug": 10,
                "info": 20,
                "warning": 30,
                "error": 40,
                "critical": 50,
            }.get(level, 20)
            self._stdlib.log(numeric, text)

    def debug(self, msg: str, *a: Any) -> None:
        self._emit("debug", msg, *a)

    def info(self, msg: str, *a: Any) -> None:
        self._emit("info", msg, *a)

    def warning(self, msg: str, *a: Any) -> None:
        self._emit("warning", msg, *a)

    def error(self, msg: str, *a: Any) -> None:
        self._emit("error", msg, *a)

    def exception(self, msg: str, *a: Any) -> None:
        self._emit("error", msg, *a)

    def critical(self, msg: str, *a: Any) -> None:
        self._emit("critical", msg, *a)
