"""ControlEngine — UI-tree based element location.

The engine parses the driver's XML dump into an lxml root, translates the
caller's locator via LocatorAdapter, and returns unified Element objects.

Implements implicit wait (§6.2): when `implicit_retries > 0`, a failed
`find` triggers N refresh-and-retry cycles before raising.
"""
from __future__ import annotations

import time
from typing import Any, List, Optional

from lxml import etree

from atomx.engine.control.element import Element, ElementNotFoundError
from atomx.engine.control.locator_adapter import Locator, LocatorAdapter


def detect_platform(driver: Any) -> str:
    name = driver.__class__.__name__.lower()
    if "android" in name:
        return "android"
    if "ios" in name:
        return "ios"
    if "harmony" in name:
        return "harmony"
    platform = getattr(driver, "platform", "") or ""
    if platform:
        return platform
    return "android"


class ControlEngine:
    """UI-tree based element location engine."""

    def __init__(self, driver: Any, implicit_retries: int = 0, implicit_delay: float = 0.2) -> None:
        self._driver = driver
        self._platform = detect_platform(driver)
        self._adapter = LocatorAdapter(self._platform)
        self._cached_root: Optional[Any] = None
        self._implicit_retries = implicit_retries
        self._implicit_delay = implicit_delay

    @property
    def adapter(self) -> LocatorAdapter:
        return self._adapter

    @property
    def platform(self) -> str:
        return self._platform

    def clear_cache(self) -> None:
        self._cached_root = None

    def find(self, locator: Locator, refresh: bool = True) -> Element:
        """查找元素，失败时根据 implicit_retries 配置自动重试"""
        last_exc: Optional[Exception] = None
        for attempt in range(self._implicit_retries + 1):
            root = self._get_root(refresh=True if attempt == 0 else True)
            xpath = self._adapter.to_xpath(locator)
            try:
                matches = root.xpath(xpath)
            except etree.XPathSyntaxError as exc:
                raise ValueError(f"Invalid XPath: {xpath}") from exc
            if matches:
                return Element(node=matches[0], driver=self._driver, engine=self, platform=self._platform)
            last_exc = ElementNotFoundError(f"Element not found: {locator!r} (XPath: {xpath})")
            if attempt < self._implicit_retries:
                time.sleep(self._implicit_delay)
        raise last_exc

    def find_all(self, locator: Locator, refresh: bool = True) -> List[Element]:
        root = self._get_root(refresh)
        xpath = self._adapter.to_xpath(locator)
        try:
            matches = root.xpath(xpath)
        except etree.XPathSyntaxError:
            return []
        return [Element(node=m, driver=self._driver, engine=self, platform=self._platform) for m in matches]

    def exists(self, locator: Locator) -> bool:
        try:
            self.find(locator)
            return True
        except (ElementNotFoundError, ValueError, etree.XPathSyntaxError):
            return False

    def _get_root(self, refresh: bool = True) -> Any:
        if self._cached_root is not None and not refresh:
            return self._cached_root
        xml = self._driver.dump_hierarchy()
        if not xml:
            raise RuntimeError("Driver returned an empty UI hierarchy.")
        self._cached_root = etree.fromstring(xml.encode("utf-8"))
        return self._cached_root
