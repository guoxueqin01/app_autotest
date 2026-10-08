"""BasePage — generic operations shared by all page objects."""
from __future__ import annotations

from typing import Any, List, Type, Union

from atomx import AtomX
from atomx.engine.control.element import Element, ElementNotFoundError

try:
    import allure  # type: ignore
    _HAS_ALLURE = True
except ImportError:
    _HAS_ALLURE = False
    class _NullAllure:
        @staticmethod
        def feature(name): return lambda cls: cls
        @staticmethod
        def story(name): return lambda f: f
        @staticmethod
        def epic(name): return lambda cls: cls
        @staticmethod
        def severity(level): return lambda f: f
        @staticmethod
        def step(name): return lambda f: f
        @staticmethod
        def title(name): return lambda f: f
        class dynamic:
            @staticmethod
            def feature(name): pass
            @staticmethod
            def story(name): pass
            @staticmethod
            def label(name, value): pass
            @staticmethod
            def title(name): pass
    allure = _NullAllure()  # type: ignore

Locator = Union[str, dict]


class BasePage:
    """Shared base for Page Objects."""

    # Subclasses can override these class attributes
    PACKAGE: str = ""
    ACTIVITY: str = ""

    def __init__(self, app: AtomX) -> None:
        self.app = app
        self._logger = app.logger
        # Allure 动态设置层级
        feature = getattr(self.__class__, "feature", "")
        story = getattr(self.__class__, "story", "")
        page_name = getattr(self.__class__, "page_name", "") or self.__class__.__name__.replace("_", " ")
        if _HAS_ALLURE and feature:
            allure.dynamic.feature(feature)
        if _HAS_ALLURE and story:
            allure.dynamic.story(story)
        if _HAS_ALLURE:
            allure.dynamic.label("page", page_name)

    # --- Meta ---

    @property
    def page_name(self) -> str:
        return getattr(self.__class__, "page_name", "") or self.__class__.__name__.replace("_", " ")

    @property
    def logger(self) -> Any:
        return self._logger

    # --- Navigation ---

    def open(self, package: str = "", activity: str = "") -> None:
        pkg = package or self.PACKAGE
        act = activity or self.ACTIVITY
        if not pkg:
            raise ValueError(f"{self.page_name} requires PACKAGE to open")
        self.app.start_app(pkg, act)

    def wait_for_page_loaded(self) -> None:
        raise NotImplementedError(f"{self.page_name} must implement wait_for_page_loaded")

    def navigate(self, target_page_cls: Type["BasePage"]) -> "BasePage":
        """导航到另一个 Page Object"""
        target = target_page_cls(self.app)
        target.wait_for_page_loaded()
        return target

    # --- Locate ---

    def find(self, locator: Locator) -> Element:
        return self.app.find(locator)

    def find_all(self, locator: Locator) -> List[Element]:
        return self.app.find_all(locator)

    def exists(self, locator: Locator) -> bool:
        return self.app.exists(locator)

    # --- Gestures ---

    @allure.step("点击: {locator}")
    def tap(self, locator: Locator) -> None:
        self.app.find(locator).tap()

    @allure.step("长按: {locator}")
    def long_press(self, locator: Locator, duration: float = 2.0) -> None:
        self.app.find(locator).long_press(duration)

    @allure.step("滑动: {direction}")
    def swipe(self, direction: str = "up") -> None:
        self.app.swipe(direction)

    @allure.step("滚动到元素: {locator}")
    def scroll_to_element(self, locator: Locator, max_scrolls: int = 10) -> Element:
        for _ in range(max_scrolls):
            if self.app.exists(locator):
                return self.app.find(locator)
            self.app.swipe("up")
        raise ElementNotFoundError(f"Element not found after scrolling: {locator!r}")

    # --- Forms ---

    @allure.step("输入文本: {text}")
    def fill(self, locator: Locator, text: str) -> None:
        self.app.find(locator).input_text(text)

    @allure.step("清空: {locator}")
    def clear(self, locator: Locator) -> None:
        self.app.find(locator).clear()

    def get_text(self, locator: Locator) -> str:
        return self.app.find(locator).text

    def get_attribute(self, locator: Locator, attr: str) -> str:
        return self.app.find(locator).get_attribute(attr)

    def is_checked(self, locator: Locator) -> bool:
        return self.app.find(locator).is_checked

    def is_enabled(self, locator: Locator) -> bool:
        return self.app.find(locator).is_enabled

    # --- Waits ---

    @allure.step("等待可见: {locator}")
    def wait_for_visible(self, locator: Locator, timeout: float = 10.0) -> None:
        self.app.wait.until_visible(locator, timeout)

    @allure.step("等待消失: {locator}")
    def wait_for_gone(self, locator: Locator, timeout: float = 10.0) -> None:
        self.app.wait.until_gone(locator, timeout)

    @allure.step("等待文本: {text}")
    def wait_for_text(self, text: str, timeout: float = 10.0) -> None:
        self.app.wait.until(lambda: self.app.exists(text), timeout, message=f"text={text!r}")

    # --- Assertions ---

    @allure.step("断言存在: {locator}")
    def assert_visible(self, locator: Locator) -> None:
        self.app.assert_.exists(locator)

    @allure.step("断言不存在: {locator}")
    def assert_not_visible(self, locator: Locator) -> None:
        self.app.assert_.not_exists(locator)

    @allure.step("断言文本: {locator} == '{expected}'")
    def assert_text_equals(self, locator: Locator, expected: str) -> None:
        self.app.assert_.text_equals(locator, expected)

    @allure.step("断言文本包含: {locator} 包含 '{substring}'")
    def assert_text_contains(self, locator: Locator, substring: str) -> None:
        self.app.assert_.text_contains(locator, substring)

    @allure.step("断言数量: {locator} == {count}")
    def assert_count(self, locator: Locator, count: int) -> None:
        self.app.assert_.count_equals(locator, count)

    # --- Attachments ---

    @allure.step("截图")
    def screenshot(self, name: str = "screenshot") -> bytes:
        png = self.app.screenshot(name)
        if _HAS_ALLURE:
            allure.attach(png, name=name, attachment_type=allure.attachment_type.PNG)
        return png
