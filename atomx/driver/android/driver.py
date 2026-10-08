"""AndroidDriver — direct HTTP RPC to on-device uiautomator service.

This driver wraps `adbutils` for device shell access and `HttpTransport` for
high-frequency UI operations. It is intentionally decoupled from Appium so we
don't pay the server round-trip cost for simple actions.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from atomx.driver.base import BaseDriver
from atomx.driver.android.transport import HttpTransport
from atomx.driver.android.installer import AutoInstaller


class AndroidDriver(BaseDriver):
    """Android driver with direct RPC (uiautomator2 style)."""

    def __init__(self) -> None:
        self._device: Optional[Any] = None
        self._transport: Optional[HttpTransport] = None
        self._installer = AutoInstaller()
        self._serial: str = ""

    def connect(self, serial: str = "", **kwargs: Any) -> "AndroidDriver":
        self._serial = serial
        try:
            import adbutils  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised when dep missing
            raise RuntimeError("adbutils is required for AndroidDriver. `pip install adbutils`") from exc

        if not serial:
            devices = adbutils.adb.device_list()
            if not devices:
                raise RuntimeError("No Android device detected. Plug in a device or pass serial=...")
            self._device = devices[0]
        else:
            self._device = adbutils.adb.device(serial=serial)

        self._installer.ensure_ready(self._device)
        local_port = self._installer.forward_port(self._device)
        self._transport = HttpTransport(f"http://127.0.0.1:{local_port}")
        return self

    def disconnect(self) -> None:
        self._device = None
        self._transport = None

    # --- BaseDriver contract ---

    def dump_hierarchy(self) -> str:
        self._require_transport()
        result = self._transport.jsonrpc_call("dumpHierarchy")
        if isinstance(result, str):
            return result
        # Some services return {"hierarchy": "..."}
        return result.get("hierarchy", "") if isinstance(result, dict) else str(result)

    def click(self, x: int, y: int) -> None:
        self._require_transport()
        self._transport.jsonrpc_call("click", x, y)

    def long_press(self, x: int, y: int, duration: float = 2.0) -> None:
        """Android 长按 — 用 input touchscreen longpress"""
        self._require_transport()
        self._transport.jsonrpc_call("longClick", x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        self._require_transport()
        self._transport.jsonrpc_call("swipe", x1, y1, x2, y2, int(duration * 200))

    def input_text(self, text: str) -> None:
        self._require_transport()
        self._transport.jsonrpc_call("setText", text)

    def screenshot(self) -> bytes:
        self._require_transport()
        return self._transport.jsonrpc_call("takeScreenshot", return_bytes=True)

    def start_app(self, package: str, activity: str = "") -> None:
        if not self._device:
            raise RuntimeError("Not connected")
        if activity:
            self._device.shell(f"am start -n {package}/{activity}")
        else:
            self._device.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

    def stop_app(self, package: str) -> None:
        if not self._device:
            raise RuntimeError("Not connected")
        self._device.shell(f"am force-stop {package}")

    def press_key(self, key: str) -> None:
        self._require_transport()
        key_map = {"home": 3, "back": 4, "menu": 82, "power": 26, "enter": 66, "delete": 67}
        keycode = key_map.get(key.lower(), key)
        self._transport.jsonrpc_call("pressKey", keycode)

    def get_device_info(self) -> Dict[str, Any]:
        self._require_transport()
        info: Dict[str, Any] = {"platform": "android", "serial": self._serial}
        try:
            raw = self._transport.jsonrpc_call("deviceInfo")
            if isinstance(raw, dict):
                info.update(raw)
        except Exception:
            pass
        if "displayWidth" not in info and "width" in info:
            info["displayWidth"] = info.pop("width")
        if "displayHeight" not in info and "height" in info:
            info["displayHeight"] = info.pop("height")
        return info

    # --- Extra capabilities ---

    def screen_record_start(self, **kwargs: Any) -> Optional[str]:
        if not self._device:
            return None
        path = kwargs.get("remote_path", "/sdcard/atomx_screen.mp4")
        try:
            self._device.shell(f"screenrecord --time-limit {kwargs.get('time_limit', 180)} {path}")
            return path
        except Exception:
            return None

    def screen_record_stop(self) -> bytes:
        if not self._device:
            return b""
        remote = "/sdcard/atomx_screen.mp4"
        local = os.environ.get("ATOMX_RECORD_PATH", "/tmp/atomx_screen.mp4")
        try:
            self._device.sync.pull(remote, local)
            with open(local, "rb") as f:
                return f.read()
        except Exception:
            return b""

    def install_app(self, path: str) -> None:
        if not self._device:
            raise RuntimeError("Not connected")
        self._device.install(path)

    # --- Helpers ---

    def _require_transport(self) -> None:
        if self._transport is None:
            raise RuntimeError("AndroidDriver not connected. Call connect() first.")
