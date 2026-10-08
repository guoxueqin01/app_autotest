"""AtomX — unified facade over drivers, engines, actions and plugins."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from atomx.actions.assert_ import AssertionActions
from atomx.actions.recovery import SessionRecovery
from atomx.actions.wait import SmartWait
from atomx.driver.factory import DriverFactory
from atomx.engine.control.engine import ControlEngine
from atomx.engine.control.element import Element
from atomx.engine.control.locator_adapter import Locator
from atomx.engine.image.engine import ImageEngine
from atomx.infra.logger import Logger
from atomx.infra.perf.monitor import PerfMonitor
from atomx.plugin.manager import PluginManager


class AtomX:
    """Unified facade over drivers / engines / actions / plugins.

    Typical usage:

        app = AtomX()
        app.connect(platform="android")
        app.start_app("com.example.app", ".MainActivity")
        app.find({"id": "username"}).input_text("admin")
        app.find("登录").tap()
        app.assert_.exists("首页")
        app.disconnect()
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self._driver: Optional[Any] = None
        self._control: Optional[ControlEngine] = None
        self._image: Optional[ImageEngine] = None
        self._platform: str = ""
        self._serial: str = ""
        self.logger: Logger = Logger()
        self._recovery: Optional[SessionRecovery] = None
        self._plugins: PluginManager = (
            PluginManager.from_config(config or {}, self) if config and config.get("plugins") else PluginManager()
        )
        self.wait: Optional[SmartWait] = None
        self.assert_: Optional[AssertionActions] = None
        self._connected = False
        self._config: dict = dict(config or {})
        self._implicit_retries: int = int(self._config.get("implicit_retries", 0))
        self._implicit_delay: float = float(self._config.get("implicit_delay", 0.2))
        self._wait_timeout: float = float(self._config.get("wait_timeout", 10.0))
        self._image_threshold: float = float(self._config.get("image_threshold", 0.7))

    # --- Connection ---

    def connect(self, platform: str, serial: str = "", **kwargs: Any) -> "AtomX":
        self._platform = platform
        self._serial = serial
        self.logger.info("Connecting %s device: %s", platform, serial or "auto")
        self._driver = DriverFactory.create(platform, serial, **kwargs)
        self._control = ControlEngine(
            self._driver,
            implicit_retries=self._implicit_retries,
            implicit_delay=self._implicit_delay,
        )
        self._image = ImageEngine(self._driver, platform=platform, threshold=self._image_threshold)
        self.wait = SmartWait(self._control, self._image, default_timeout=self._wait_timeout)
        self.assert_ = AssertionActions(self._control, self._image, self._driver)
        # 注入 plugins 引用到 AssertionActions, 使其能触发 on_assert/on_error hook
        self.assert_._plugins = self._plugins
        self._recovery = SessionRecovery(self)
        self._plugins.call_connect(self, platform=platform, serial=serial)
        self._connected = True
        return self

    def disconnect(self) -> None:
        if self._plugins:
            self._plugins.call_report(self, {"platform": self._platform, "serial": self._serial})
            self._plugins.call_disconnect(self)
            self._plugins.call_teardown(self)
        if self._driver is not None:
            try:
                self._driver.disconnect()
            finally:
                self.logger.info("Device disconnected")
        self._connected = False

    @property
    def driver(self) -> Any:
        return self._driver

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def serial(self) -> str:
        return self._serial

    @property
    def plugins(self) -> PluginManager:
        return self._plugins

    def register_plugin(self, plugin: Any) -> "AtomX":
        self._plugins.register(plugin)
        return self

    def perf_monitor(self) -> PerfMonitor:
        return PerfMonitor(self._driver)

    # --- Locate ---

    def find(self, locator: Locator) -> Element:
        """Unified element lookup across control / image engines."""
        if isinstance(locator, str) and locator.startswith("image:"):
            result = self._require_image().find(locator[6:])
        elif self._recovery is not None:
            result = self._recovery.execute_with_recovery(self._require_control().find, locator)
        else:
            result = self._require_control().find(locator)
        self._plugins.call_find(self, locator, result)
        return result

    def find_all(self, locator: Locator) -> List[Element]:
        if isinstance(locator, str) and locator.startswith("image:"):
            results = self._require_image().find_all(locator[6:])
        else:
            results = self._require_control().find_all(locator)
        self._plugins.call_find(self, locator, results)
        return results

    def exists(self, locator: Locator) -> bool:
        try:
            self.find(locator)
            return True
        except Exception:  # noqa: BLE001
            return False

    # --- Actions ---

    def tap(self, x: int, y: int) -> "AtomX":
        self._require_driver().click(x, y)
        self._plugins.call_action(self, "tap", (x, y), {}, None)
        return self

    def long_press(self, x: int, y: int, duration: float = 2.0) -> "AtomX":
        driver = self._require_driver()
        if hasattr(driver, "long_press"):
            driver.long_press(x, y, duration)  # type: ignore[attr-defined]
        else:
            driver.click(x, y)
        self._plugins.call_action(self, "long_press", (x, y, duration), {}, None)
        return self

    def swipe(self, direction: str = "up", duration: float = 0.5) -> "AtomX":
        info = self.info
        w = int(info.get("displayWidth") or info.get("width") or 1080)
        h = int(info.get("displayHeight") or info.get("height") or 1920)
        cx, cy = w // 2, h // 2
        offsets = {
            "up": (0, h // 3),
            "down": (0, -h // 3),
            "left": (w // 3, 0),
            "right": (-w // 3, 0),
        }
        dx, dy = offsets.get(direction, (0, -h // 3))
        self._require_driver().swipe(cx, cy, cx + dx, cy + dy, duration)
        self._plugins.call_action(self, "swipe", (direction, duration), {}, None)
        return self

    def start_app(self, package: str, activity: str = "") -> "AtomX":
        self._require_driver().start_app(package, activity)
        self._plugins.call_action(self, "start_app", (package, activity), {}, None)
        return self

    def stop_app(self, package: str) -> "AtomX":
        self._require_driver().stop_app(package)
        self._plugins.call_action(self, "stop_app", (package,), {}, None)
        return self

    def press_key(self, key: str) -> "AtomX":
        self._require_driver().press_key(key)
        self._plugins.call_action(self, "press_key", (key,), {}, None)
        return self

    def input_text(self, text: str) -> "AtomX":
        self._require_driver().input_text(text)
        self._plugins.call_action(self, "input_text", (text,), {}, None)
        return self

    def screenshot(self, tag: str = "screenshot") -> bytes:
        png = self._require_driver().screenshot()
        self._plugins.call_screenshot(self, png, tag)
        return png

    @property
    def info(self) -> Dict[str, Any]:
        return self._require_driver().get_device_info()

    # --- Context manager ---

    def __enter__(self) -> "AtomX":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.disconnect()

    # --- Guards ---

    def _require_driver(self) -> Any:
        if self._driver is None:
            raise RuntimeError("AtomX not connected. Call connect() first.")
        return self._driver

    def _require_control(self) -> ControlEngine:
        if self._control is None:
            raise RuntimeError("ControlEngine unavailable. Connect first.")
        return self._control

    def _require_image(self) -> ImageEngine:
        if self._image is None:
            raise RuntimeError("ImageEngine unavailable. Connect first.")
        return self._image
