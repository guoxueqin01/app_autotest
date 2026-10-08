"""WatcherPlugin — 后台弹窗监控，自动关闭已知弹窗。"""
from __future__ import annotations

import threading
import time
from typing import Any, List

from atomx.plugin.base import AtomXPlugin


class WatcherPlugin(AtomXPlugin):
    """弹窗监控插件 — 后台线程检测并关闭已知弹窗。"""

    name = "watcher"
    priority = 20

    def __init__(self, enabled: bool = True, interval: float = 2.0) -> None:
        self._enabled = enabled
        self._interval = interval
        self._watchers: List[dict] = []
        self._thread: threading.Thread | None = None
        self._running = False
        self._app: Any = None

    def add_watcher(self, name: str, locator: Any, action: str = "tap") -> None:
        """添加一个弹窗监控规则"""
        self._watchers.append({"name": name, "locator": locator, "action": action})

    def remove_watcher(self, name: str) -> None:
        self._watchers = [w for w in self._watchers if w["name"] != name]

    def on_connect(self, app: Any, **kwargs: Any) -> None:
        self._app = app
        if self._enabled:
            self._start()

    def on_disconnect(self, app: Any) -> None:
        self._stop()

    def teardown(self, app: Any) -> None:
        self._stop()

    def _start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def _loop(self) -> None:
        while self._running and self._app:
            try:
                for w in self._watchers:
                    if self._app.exists(w["locator"]):
                        if w["action"] == "tap":
                            self._app.find(w["locator"]).tap()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(self._interval)
