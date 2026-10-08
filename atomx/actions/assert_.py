"""AssertionActions — element / attribute / image / numeric assertions.

The module automatically captures a screenshot into Allure on failure so
reports stay useful even when the test doesn't touch the app afterwards.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from atomx.engine.control.engine import ControlEngine
from atomx.engine.control.element import ElementNotFoundError
from atomx.engine.control.locator_adapter import Locator
from atomx.engine.image.engine import ImageEngine


class AssertionFailure(AssertionError):
    """Raised when an assertion fails. Extends AssertionError for pytest friendliness."""


class AssertionActions:
    """Element / attribute / image / numeric assertions with screenshot-on-fail."""

    def __init__(self, control: ControlEngine, image: ImageEngine, driver: Any) -> None:
        self._control = control
        self._image = image
        self._driver = driver
        self._plugins: Any = None  # 注入 by AtomX

    # --- element presence ---

    def exists(self, locator: Locator) -> None:
        if not self._control.exists(locator):
            self._fail(f"Element should exist but was not found: {locator!r}")
            self._notify_assert("exists", False, locator=locator)
        self._notify_assert("exists", True, locator=locator)

    def not_exists(self, locator: Locator) -> None:
        if self._control.exists(locator):
            self._fail(f"Element should NOT exist but was found: {locator!r}")
            self._notify_assert("not_exists", False, locator=locator)
        self._notify_assert("not_exists", True, locator=locator)

    # --- text ---

    def text_equals(self, locator: Locator, expected: str) -> None:
        try:
            actual = self._control.find(locator).text
        except ElementNotFoundError as exc:
            self._fail(f"Element for text_equals not found: {locator!r}", exc)
        if actual != expected:
            self._fail(f"Text mismatch: expected={expected!r}, actual={actual!r}")
        self._notify_assert("text_equals", True, locator=locator, actual=actual, expected=expected)

    def text_contains(self, locator: Locator, substring: str) -> None:
        try:
            actual = self._control.find(locator).text
        except ElementNotFoundError as exc:
            self._fail(f"Element for text_contains not found: {locator!r}", exc)
        if substring not in actual:
            self._fail(f"Text does not contain {substring!r}; actual={actual!r}")
        self._notify_assert("text_contains", True, locator=locator, actual=actual, expected=substring)

    # --- attribute ---

    def attribute_equals(self, locator: Locator, attr: str, expected: str) -> None:
        try:
            actual = self._control.find(locator).get_attribute(attr)
        except ElementNotFoundError as exc:
            self._fail(f"Element for attribute_equals not found: {locator!r}", exc)
        if actual != expected:
            self._fail(f"Attribute {attr!r} mismatch: expected={expected!r}, actual={actual!r}")
        self._notify_assert("attribute_equals", True, locator=locator, attr=attr, expected=expected)

    def is_enabled(self, locator: Locator) -> None:
        try:
            el = self._control.find(locator)
        except ElementNotFoundError as exc:
            self._fail(f"Element for is_enabled not found: {locator!r}", exc)
        if not el.is_enabled:
            self._fail(f"Element not enabled: {locator!r}")
        self._notify_assert("is_enabled", True, locator=locator)

    def is_checked(self, locator: Locator) -> None:
        try:
            el = self._control.find(locator)
        except ElementNotFoundError as exc:
            self._fail(f"Element for is_checked not found: {locator!r}", exc)
        if not el.is_checked:
            self._fail(f"Element not checked: {locator!r}")
        self._notify_assert("is_checked", True, locator=locator)

    # --- count ---

    def count_equals(self, locator: Locator, expected: int) -> None:
        actual = len(self._control.find_all(locator))
        if actual != expected:
            self._fail(f"Count mismatch: expected={expected}, actual={actual}")
        self._notify_assert("count_equals", True, locator=locator, actual=actual, expected=expected)

    def count_at_least(self, locator: Locator, minimum: int) -> None:
        actual = len(self._control.find_all(locator))
        if actual < minimum:
            self._fail(f"Count below minimum: expected>={minimum}, actual={actual}")
        self._notify_assert("count_at_least", True, locator=locator, actual=actual, minimum=minimum)

    # --- image ---

    def image_exists(self, template_path: str, threshold: Optional[float] = None) -> None:
        if not self._image.exists(template_path, threshold=threshold):
            self._fail(f"Image template not found on screen: {template_path!r}")
        self._notify_assert("image_exists", True, template=template_path)

    def image_not_exists(self, template_path: str, threshold: Optional[float] = None) -> None:
        if self._image.exists(template_path, threshold=threshold):
            self._fail(f"Image template should NOT be present: {template_path!r}")
        self._notify_assert("image_not_exists", True, template=template_path)

    # --- numeric ---

    def greater_than(self, threshold: Union[int, float], actual: Union[int, float], message: str = "") -> None:
        """断言 actual > threshold"""
        if not actual > threshold:
            self._fail(f"{message or '数值断言失败'}: {actual} 不大于 {threshold}")
        self._notify_assert("greater_than", True, threshold=threshold, actual=actual, message=message)

    def less_than(self, threshold: Union[int, float], actual: Union[int, float], message: str = "") -> None:
        """断言 actual < threshold"""
        if not actual < threshold:
            self._fail(f"{message or '数值断言失败'}: {actual} 不小于 {threshold}")
        self._notify_assert("less_than", True, threshold=threshold, actual=actual, message=message)

    def greater_equal(self, threshold: Union[int, float], actual: Union[int, float], message: str = "") -> None:
        """断言 actual >= threshold"""
        if not actual >= threshold:
            self._fail(f"{message or '数值断言失败'}: {actual} 不大于等于 {threshold}")
        self._notify_assert("greater_equal", True, threshold=threshold, actual=actual, message=message)

    def less_equal(self, threshold: Union[int, float], actual: Union[int, float], message: str = "") -> None:
        """断言 actual <= threshold"""
        if not actual <= threshold:
            self._fail(f"{message or '数值断言失败'}: {actual} 不小于等于 {threshold}")
        self._notify_assert("less_equal", True, threshold=threshold, actual=actual, message=message)

    def equals(self, expected: Union[int, float, str], actual: Union[int, float, str], message: str = "") -> None:
        """断言 actual == expected"""
        if actual != expected:
            self._fail(f"{message or '数值断言失败'}: {actual} != {expected}")
        self._notify_assert("equals", True, expected=expected, actual=actual, message=message)

    # --- internal ---

    def _notify_assert(self, assertion: str, passed: bool, **kwargs: Any) -> None:
        """通知插件 on_assert hook"""
        if self._plugins is not None:
            try:
                self._plugins.call_assert(self, assertion, passed, **kwargs)
            except Exception:  # noqa: BLE001
                pass

    def _fail(self, message: str, exc: Optional[BaseException] = None) -> None:
        screenshot = self._try_screenshot()
        if screenshot and self._try_attach(screenshot):
            pass  # Allure already attached
        # 通知插件 on_error hook
        if self._plugins is not None:
            try:
                self._plugins.call_error(self, AssertionFailure(message), {"message": message})
            except Exception:  # noqa: BLE001
                pass
        raise AssertionFailure(message) from exc

    def _try_screenshot(self) -> Optional[bytes]:
        try:
            return self._driver.screenshot()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _try_attach(png: bytes) -> bool:
        try:
            import allure  # type: ignore

            allure.attach(png, name="failure_screenshot", attachment_type=allure.attachment_type.PNG)
            return True
        except Exception:  # noqa: BLE001
            return False
