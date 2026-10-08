"""SmartWait — implicit / explicit / conditional waits.

The wait engine exposes a small set of until_* methods plus a raw `until`
predicate hook. Timeouts raise TimeoutError so pytest reports a clean stack.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from atomx.engine.control.element import ElementNotFoundError
from atomx.engine.control.locator_adapter import Locator
from atomx.engine.control.engine import ControlEngine
from atomx.engine.image.engine import ImageEngine


class WaitTimeoutError(TimeoutError):
    """Raised when a wait predicate fails to become true."""


class SmartWait:
    """Unified wait utility for both control and image engines."""

    def __init__(self, control: ControlEngine, image: ImageEngine, default_timeout: float = 10.0, interval: float = 0.5) -> None:
        self._control = control
        self._image = image
        self._default_timeout = default_timeout
        self._interval = interval

    # --- predicate hook ---

    def until(self, predicate: Callable[[], Any], timeout: Optional[float] = None, message: str = "predicate") -> Any:
        deadline = time.time() + (self._default_timeout if timeout is None else timeout)
        last_exc: Optional[BaseException] = None
        while time.time() < deadline:
            try:
                result = predicate()
                if result:
                    return result
            except Exception as exc:  # noqa: BLE001 - waits should be forgiving
                last_exc = exc
            time.sleep(self._interval)
        raise WaitTimeoutError(f"Timeout waiting for {message}: {self._format_timeout(deadline)}" + (f" (last: {last_exc})" if last_exc else ""))

    def until_not(self, predicate: Callable[[], Any], timeout: Optional[float] = None, message: str = "predicate") -> None:
        self.until(lambda: not predicate(), timeout=timeout, message=f"not({message})")

    # --- element waits ---

    def until_visible(self, locator: Locator, timeout: Optional[float] = None) -> Any:
        return self.until(lambda: self._control.find(locator, refresh=True), timeout=timeout, message=f"visible {locator!r}")

    def until_gone(self, locator: Locator, timeout: Optional[float] = None) -> None:
        self.until(lambda: not self._control.exists(locator), timeout=timeout, message=f"gone {locator!r}")

    def until_text(self, text: str, timeout: Optional[float] = None) -> None:
        self.until(lambda: self._control.exists(text), timeout=timeout, message=f"text {text!r}")

    # --- image waits ---

    def until_image_present(self, template_path: str, timeout: Optional[float] = None, threshold: Optional[float] = None) -> None:
        self.until(
            lambda: self._image.exists(template_path, threshold=threshold),
            timeout=timeout,
            message=f"image {template_path!r}",
        )

    def until_image_gone(self, template_path: str, timeout: Optional[float] = None, threshold: Optional[float] = None) -> None:
        self.until_not(
            lambda: self._image.exists(template_path, threshold=threshold),
            timeout=timeout,
            message=f"image {template_path!r}",
        )

    # --- utilities ---

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @staticmethod
    def _format_timeout(deadline: float) -> str:
        waited = time.time() - (deadline - max(deadline - time.time(), 0))
        return f"(waited ~{waited:.1f}s)"
