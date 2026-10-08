"""AutoScreenshotPlugin — 操作步骤/失败时自动截图并附加到 Allure。"""
from __future__ import annotations

from typing import Any

from atomx.plugin.base import AtomXPlugin


class AutoScreenshotPlugin(AtomXPlugin):
    """自动截图插件 — 每个操作步骤自动截图并附加到 Allure。"""

    name = "auto_screenshot"
    priority = 10

    def __init__(self, enabled: bool = True, on_step: bool = False, on_failure: bool = True) -> None:
        self._enabled = enabled
        self._on_step = on_step
        self._on_failure = on_failure

    def on_action(self, app: Any, action: str, args: tuple, kwargs: dict,
                  result: Any = None) -> Any:
        if not self._enabled or not self._on_step:
            return result
        try:
            import allure  # type: ignore

            screenshot = app.driver.screenshot()
            allure.attach(
                screenshot,
                name=f"screenshot_{action}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:  # noqa: BLE001
            pass
        return result

    def on_error(self, app: Any, error: Exception, context: dict) -> None:
        if not self._enabled or not self._on_failure:
            return
        try:
            import allure  # type: ignore

            screenshot = app.driver.screenshot()
            allure.attach(
                screenshot,
                name="error_screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:  # noqa: BLE001
            pass
