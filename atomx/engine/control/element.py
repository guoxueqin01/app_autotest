"""Cross-platform Element abstraction.

An Element wraps either:
  * an lxml node returned by the ControlEngine, or
  * pre-computed center/rect/confidence from the ImageEngine.

It exposes a small chainable API: tap / long_press / input_text / clear /
get_text / find.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from atomx.engine.control.locator_adapter import Locator

Bounds = Tuple[int, int, int, int]


class ElementNotFoundError(LookupError):
    """Raised when an element cannot be located."""


class Element:
    """Unified element across control and image engines."""

    def __init__(
        self,
        node: Optional[Any] = None,
        driver: Optional[Any] = None,
        engine: Optional[Any] = None,
        center: Optional[Tuple[int, int]] = None,
        rect: Optional[Bounds] = None,
        confidence: Optional[float] = None,
        platform: str = "android",
    ) -> None:
        self._node = node
        self._driver = driver
        self._engine = engine
        self._center = center
        self._rect = rect
        self._confidence = confidence
        self._platform = platform

    # --- Properties ---

    @property
    def text(self) -> str:
        if self._node is None:
            return ""
        return self._node.get("text") or self._node.get("label") or ""

    @property
    def value(self) -> str:
        if self._node is None:
            return ""
        return self._node.get("value") or ""

    @property
    def resource_id(self) -> str:
        if self._node is None:
            return ""
        return self._node.get("resource-id") or self._node.get("id") or self._node.get("name") or ""

    @property
    def confidence(self) -> Optional[float]:
        return self._confidence

    @property
    def bounds(self) -> Bounds:
        if self._rect:
            return self._rect
        if self._node is None:
            return (0, 0, 0, 0)

        # WDA style: rect="{'x':0,'y':0,'width':100,'height':50}"
        rect_str = self._node.get("rect") or ""
        if rect_str:
            parsed = self._parse_jsonish(rect_str)
            if isinstance(parsed, dict) and all(k in parsed for k in ("x", "y", "width", "height")):
                return (int(parsed["x"]), int(parsed["y"]), int(parsed["width"]), int(parsed["height"]))

        # HarmonyOS: JSON dict in `bounds`
        bounds_raw = self._node.get("bounds") or self._node.get("rect") or ""
        if bounds_raw.startswith("{"):
            parsed = self._parse_jsonish(bounds_raw)
            if isinstance(parsed, dict):
                return (int(parsed["x"]), int(parsed["y"]), int(parsed["width"]), int(parsed["height"]))

        # Android: "[x1,y1][x2,y2]"
        if bounds_raw:
            nums = [int(n) for n in re.findall(r"-?\d+", bounds_raw)]
            if len(nums) >= 4:
                x1, y1, x2, y2 = nums[:4]
                return (x1, y1, x2 - x1, y2 - y1)

        # WDA frame="[x,y,w,h]"
        frame = self._node.get("frame") or ""
        if frame:
            nums = [int(n) for n in re.findall(r"-?\d+", frame)]
            if len(nums) >= 4:
                return tuple(nums[:4])  # type: ignore[return-value]
        return (0, 0, 0, 0)

    @property
    def center(self) -> Tuple[int, int]:
        if self._center:
            return self._center
        x, y, w, h = self.bounds
        return (x + w // 2, y + h // 2)

    @property
    def is_displayed(self) -> bool:
        _, _, w, h = self.bounds
        return w > 0 and h > 0

    @property
    def is_enabled(self) -> bool:
        if self._node is None:
            return True
        raw = self._node.get("enabled", "true")
        return str(raw).lower() in ("true", "1", "yes")

    @property
    def is_checked(self) -> bool:
        if self._node is None:
            return False
        raw = self._node.get("checked") or self._node.get("value") or ""
        return str(raw).lower() in ("true", "1", "on", "yes")

    def get_attribute(self, attr: str) -> str:
        if self._node is None:
            return ""
        return self._node.get(attr) or ""

    # --- Sub-element ---

    def find(self, locator: Locator) -> "Element":
        if self._node is None:
            raise RuntimeError("Sub-element find is only supported on ControlEngine elements")
        if self._engine is None:
            raise RuntimeError("Element was not attached to an engine; cannot re-resolve.")
        root = self._node
        xpath = self._engine._adapter.to_xpath(locator)
        matches = root.xpath(f".{xpath}")
        if not matches:
            raise ElementNotFoundError(f"Sub-element not found: {locator!r}")
        return Element(node=matches[0], driver=self._driver, engine=self._engine, platform=self._platform)

    # --- Actions ---

    def tap(self) -> "Element":
        self._require_driver().click(*self.center)
        return self

    def long_press(self, duration: float = 2.0) -> "Element":
        """长按元素 — 优先用平台原生长按，降级用 swipe 模拟"""
        driver = self._require_driver()
        x, y = self.center
        if hasattr(driver, "long_press"):
            driver.long_press(x, y, duration)  # type: ignore[attr-defined]
            return self
        # 降级: 用短距离 swipe 模拟长按 (起点终点相同，duration 控制按压时长)
        driver.swipe(x, y, x, y, duration)
        return self

    def input_text(self, text: str) -> "Element":
        self.tap()
        self._require_driver().input_text(text)
        return self

    def clear(self) -> "Element":
        self.tap()
        driver = self._require_driver()
        if hasattr(driver, "clear_text"):
            driver.clear_text()  # type: ignore[attr-defined]
            return self
        driver.input_text("")
        return self

    def get_text(self) -> str:
        return self.text

    # --- Helpers ---

    def _require_driver(self) -> Any:
        if self._driver is None:
            raise RuntimeError("Element has no driver; cannot perform actions.")
        return self._driver

    @staticmethod
    def _parse_jsonish(raw: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            # WDA sometimes serialises as Python dict repr with single quotes.
            import ast

            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return None

    def __repr__(self) -> str:
        if self._node is not None:
            tag = getattr(self._node, "tag", "node")
            return f"<Element tag={tag} text={self.text!r} center={self.center}>"
        return f"<Element image center={self._center} confidence={self._confidence}>"
