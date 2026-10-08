"""IOSDriver — WebDriverAgent based implementation."""
from __future__ import annotations

from typing import Any, Dict, Optional

from atomx.driver.base import BaseDriver
from atomx.driver.ios.usb_client import USBClient


class IOSDriver(BaseDriver):
    """iOS driver wrapping facebook-wda / raw WDA HTTP API."""

    def __init__(self) -> None:
        self._client: Optional[USBClient] = None
        self._serial: str = ""

    def connect(self, serial: str = "", **kwargs: Any) -> "IOSDriver":
        self._serial = serial
        port = int(kwargs.get("port", 8100))
        host = kwargs.get("host", "127.0.0.1")
        timeout = float(kwargs.get("timeout", 120))
        self._client = USBClient(udid=serial or None, port=port, host=host)
        self._client.wait_ready(timeout=timeout)
        return self

    def disconnect(self) -> None:
        self._client = None

    def _require_client(self) -> USBClient:
        if self._client is None:
            raise RuntimeError("IOSDriver not connected. Call connect() first.")
        return self._client

    # --- BaseDriver contract ---

    def dump_hierarchy(self) -> str:
        return self._require_client().source()

    def click(self, x: int, y: int) -> None:
        self._require_client().tap(x, y)

    def long_press(self, x: int, y: int, duration: float = 2.0) -> None:
        """iOS 长按 — 通过 WDA press 接口"""
        client = self._require_client()
        client.press(x, y, duration * 1000)  # WDA press 用毫秒

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        self._require_client().swipe(x1, y1, x2, y2, duration)

    def input_text(self, text: str) -> None:
        self._require_client().set_text(text)

    def screenshot(self) -> bytes:
        return self._require_client().screenshot_as_png()

    def start_app(self, package: str, activity: str = "") -> None:
        self._require_client().session(package).activate()

    def stop_app(self, package: str) -> None:
        self._require_client().session(package).deactivate()

    def press_key(self, key: str) -> None:
        client = self._require_client()
        key = key.lower()
        if key == "home":
            client.home()
        elif key == "volume_up":
            client.volume_up()
        elif key == "volume_down":
            client.volume_down()
        else:
            raise NotImplementedError(f"iOS does not support key={key}")

    def get_device_info(self) -> Dict[str, Any]:
        client = self._require_client()
        info: Dict[str, Any] = {"platform": "ios", "serial": self._serial}
        status = client.status() or {}
        device_info = client.device_info() or {}
        info["status"] = status
        info.update(device_info)
        return info

    def screen_record_start(self, **kwargs: Any) -> Optional[str]:
        """开始录屏 — 通过 WDA video API"""
        client = self._require_client()
        client.start_video_recording(
            quality=kwargs.get("quality", "medium"),
            scale=kwargs.get("scale", "1.0"),
            codec=kwargs.get("codec", "libx264"),
        )
        return "/session/video"

    def screen_record_stop(self) -> bytes:
        """停止录屏 — 通过 WDA video API 获取视频字节流"""
        client = self._require_client()
        try:
            return client.stop_video_recording()
        except Exception:  # noqa: BLE001
            return b""
