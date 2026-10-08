"""Lightweight WebDriverAgent HTTP client.

Wraps either `facebook-wda` (when available) or a raw HTTP session against
http://127.0.0.1:8100. Only the subset needed by IOSDriver is exposed.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class WDAError(RuntimeError):
    """Raised when WDA fails to respond."""


class USBClient:
    """Small adapter over facebook-wda / raw WDA HTTP endpoints."""

    def __init__(self, udid: Optional[str] = None, port: int = 8100, host: str = "127.0.0.1", timeout: float = 15.0) -> None:
        self.udid = udid
        self.port = port
        self.host = host
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self._wda = None
        self._session = requests.Session()
        self._init_wda()

    # -- Init --

    def _init_wda(self) -> None:
        try:
            import wda  # type: ignore  # facebook-wda
        except ImportError:
            wda = None
        if wda is not None:
            client = wda.USBClient(host=self.host, port=self.port) if self.udid is None else wda.Client(self.base_url)
            # Try both entrypoints; some versions don't expose USBClient.
            try:
                self._wda = client
            except Exception:
                self._wda = wda.Client(self.base_url)

    def wait_ready(self, timeout: float = 120.0) -> None:
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.status():
                return
            time.sleep(0.5)
        raise WDAError(f"WDA not ready after {timeout}s on {self.base_url}")

    # -- WDA operations --

    def status(self) -> Dict[str, Any]:
        try:
            r = self._session.get(f"{self.base_url}/status", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            return {}

    def device_info(self) -> Dict[str, Any]:
        try:
            r = self._session.get(f"{self.base_url}/wda/device/info", timeout=self.timeout)
            r.raise_for_status()
            return r.json().get("value", {})
        except requests.RequestException:
            return {}

    def source(self) -> str:
        try:
            r = self._session.get(f"{self.base_url}/source?format=json", timeout=self.timeout)
            r.raise_for_status()
            return r.text
        except requests.RequestException as exc:
            raise WDAError(f"WDA /source failed: {exc}") from exc

    def session(self, bundle_id: str) -> "USBClient":
        # WDA sessions are keyed by bundle_id; expose a no-op shim.
        self._bundle_id = bundle_id
        return self

    def activate(self) -> None:
        if getattr(self, "_bundle_id", None):
            self.start(self._bundle_id)

    def deactivate(self) -> None:
        if getattr(self, "_bundle_id", None):
            self.stop(self._bundle_id)

    def start(self, bundle_id: str) -> None:
        try:
            r = self._session.post(
                f"{self.base_url}/wda/apps/launch",
                json={"bundleId": bundle_id},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"launch failed for {bundle_id}: {exc}") from exc

    def stop(self, bundle_id: str) -> None:
        try:
            r = self._session.post(
                f"{self.base_url}/wda/apps/terminate",
                json={"bundleId": bundle_id},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"terminate failed for {bundle_id}: {exc}") from exc

    def tap(self, x: int, y: int) -> None:
        try:
            r = self._session.post(
                f"{self.base_url}/wda/tap",
                json={"x": x, "y": y},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"tap failed: {exc}") from exc

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        try:
            r = self._session.post(
                f"{self.base_url}/wda/dragfromtoforduration",
                json={"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"swipe failed: {exc}") from exc

    def press(self, x: int, y: int, duration_ms: int = 2000) -> None:
        """长按 — WDA press API (duration in milliseconds)"""
        try:
            r = self._session.post(
                f"{self.base_url}/wda/touchAndHold",
                json={"x": x, "y": y, "duration": duration_ms},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"press failed: {exc}") from exc

    def start_video_recording(self, quality: str = "medium", scale: str = "1.0", codec: str = "libx264") -> None:
        """开始录屏 — WDA video API"""
        try:
            self._session.post(
                f"{self.base_url}/session/video",
                json={"quality": quality, "scale": scale, "codec": codec},
                timeout=self.timeout,
            ).raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"start_video_recording failed: {exc}") from exc

    def stop_video_recording(self) -> bytes:
        """停止录屏并返回视频字节流 — WDA video API"""
        try:
            r = self._session.get(
                f"{self.base_url}/session/video",
                timeout=60,
            )
            r.raise_for_status()
            # WDA returns base64-encoded video or raw bytes
            if isinstance(r.json(), dict) and "value" in r.json():
                return r.json()["value"].encode()
            return r.content
        except (requests.RequestException, ValueError) as exc:
            raise WDAError(f"stop_video_recording failed: {exc}") from exc

    def set_text(self, text: str) -> None:
        try:
            r = self._session.post(
                f"{self.base_url}/wda/keys",
                json={"value": list(text)},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"set_text failed: {exc}") from exc

    def screenshot_as_png(self) -> bytes:
        try:
            r = self._session.get(f"{self.base_url}/screenshot", timeout=self.timeout)
            r.raise_for_status()
            return r.json().get("value", "") if isinstance(r.content, str) else r.content
        except requests.RequestException as exc:
            raise WDAError(f"screenshot failed: {exc}") from exc

    def home(self) -> None:
        try:
            self._session.post(f"{self.base_url}/wda/homescreen", timeout=self.timeout).raise_for_status()
        except requests.RequestException as exc:
            raise WDAError(f"home failed: {exc}") from exc

    def volume_up(self) -> None:
        self._session.post(f"{self.base_url}/wda/volumeUp", timeout=self.timeout).raise_for_status()

    def volume_down(self) -> None:
        self._session.post(f"{self.base_url}/wda/volumeDown", timeout=self.timeout).raise_for_status()

    def start_recording(self, **kwargs: Any) -> str:
        # WDA recording: returns a marker so caller knows the stream is up.
        try:
            self._session.post(
                f"{self.base_url}/screenshot/record",
                json=kwargs,
                timeout=self.timeout,
            )
        except requests.RequestException:
            return ""
        return f"{self.base_url}/screenshot/record"
