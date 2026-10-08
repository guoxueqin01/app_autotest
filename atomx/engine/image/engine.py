"""ImageEngine — OpenCV-based template matching with multi-scale support.

Used as fallback for game/Canvas UIs where the control tree is not usable.
The engine returns an `Element` object with `center`/`rect`/`confidence`
populated so upper layers stay engine-agnostic.

Features:
  1. Single-pass template matching (TM_CCOEFF_NORMED)
  2. Multi-scale matching (resize template at 0.5x, 0.75x, 1.0x, 1.25x, 1.5x)
  3. OCR text recognition (optional, via pytesseract)
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

import numpy as np

from atomx.engine.control.element import Element, ElementNotFoundError

# Multi-scale factors for template matching
DEFAULT_SCALES: Tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5)


class ImageEngine:
    """Template-matching based visual locator with multi-scale support."""

    def __init__(self, driver: Any, threshold: float = 0.7, platform: str = "android",
                 scales: Optional[Tuple[float, ...]] = None) -> None:
        self._driver = driver
        self._threshold = threshold
        self._platform = platform
        self._scales = scales or DEFAULT_SCALES

    @property
    def threshold(self) -> float:
        return self._threshold

    def find(self, template_path: str, threshold: Optional[float] = None) -> Element:
        """Find template — tries multi-scale matching, returns best hit."""
        import cv2  # imported lazily: opencv is a heavy dependency

        screen = self._load_screen(cv2)
        template = cv2.imread(template_path)
        if template is None:
            raise FileNotFoundError(f"Template not found: {template_path}")
        if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
            raise ValueError("Template is larger than the screen.")

        thr = self._threshold if threshold is None else threshold

        # Try multi-scale matching
        best_score: float = -1.0
        best_loc: Optional[Tuple[int, int]] = None
        best_size: Optional[Tuple[int, int]] = None

        for scale in self._scales:
            if scale == 1.0:
                scaled = template
            else:
                w = max(1, int(template.shape[1] * scale))
                h = max(1, int(template.shape[0] * scale))
                scaled = cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)

            if scaled.shape[0] > screen.shape[0] or scaled.shape[1] > screen.shape[1]:
                continue

            result = cv2.matchTemplate(screen, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if float(max_val) > best_score:
                best_score = float(max_val)
                best_loc = max_loc
                best_size = (scaled.shape[1], scaled.shape[0])

        if best_score < float(thr) or best_loc is None or best_size is None:
            raise ElementNotFoundError(
                f"Template not matched: {template_path} "
                f"(best_score={best_score:.3f} < threshold={thr})"
            )

        x, y = int(best_loc[0]), int(best_loc[1])
        w, h = best_size
        center: Tuple[int, int] = (x + w // 2, y + h // 2)
        return Element(
            driver=self._driver,
            engine=self,
            center=center,
            rect=(x, y, w, h),
            confidence=best_score,
            platform=self._platform,
        )

    def find_all(self, template_path: str, threshold: Optional[float] = None, max_count: int = 20) -> List[Element]:
        """Find all occurrences of template (at scale 1.0 only for performance)."""
        import cv2

        screen = self._load_screen(cv2)
        template = cv2.imread(template_path)
        if template is None:
            raise FileNotFoundError(f"Template not found: {template_path}")

        thr = self._threshold if threshold is None else threshold
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= thr)
        if len(locations[0]) == 0:
            return []
        h, w = template.shape[:2]
        elements: List[Element] = []
        for y, x in zip(locations[0][:max_count], locations[1][:max_count]):
            elements.append(
                Element(
                    driver=self._driver,
                    engine=self,
                    center=(int(x) + w // 2, int(y) + h // 2),
                    rect=(int(x), int(y), w, h),
                    confidence=float(result[y, x]),
                    platform=self._platform,
                )
            )
        return elements

    def exists(self, template_path: str, threshold: Optional[float] = None) -> bool:
        try:
            self.find(template_path, threshold)
            return True
        except (ElementNotFoundError, FileNotFoundError):
            return False

    def recognize_text(self, lang: str = "chi_sim+eng") -> str:
        """OCR 文本识别 — 从当前屏幕截图识别文本

        需安装 pytesseract: pip install pytesseract
        系统还需安装 tesseract-ocr
        """
        try:
            import pytesseract  # type: ignore
        except ImportError:
            raise RuntimeError("pytesseract not installed. Run: pip install pytesseract")

        import cv2
        screen = self._load_screen(cv2)
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, lang=lang)
        return text.strip()

    def find_text(self, text: str, lang: str = "chi_sim+eng") -> Optional[Element]:
        """通过 OCR 在屏幕上查找包含指定文本的区域"""
        import cv2
        try:
            import pytesseract  # type: ignore
        except ImportError:
            raise RuntimeError("pytesseract not installed. Run: pip install pytesseract")

        screen = self._load_screen(cv2)
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        data = pytesseract.image_to_data(gray, lang=lang, output_type=pytesseract.Output.DICT)

        for i in range(len(data["text"])):
            if text in data["text"][i]:
                x = int(data["left"][i])
                y = int(data["top"][i])
                w = int(data["width"][i])
                h = int(data["height"][i])
                center = (x + w // 2, y + h // 2)
                return Element(
                    driver=self._driver,
                    engine=self,
                    center=center,
                    rect=(x, y, w, h),
                    confidence=float(data["conf"][i]) / 100.0,
                    platform=self._platform,
                )
        return None

    # --- helpers ---

    def _load_screen(self, cv2: Any) -> "np.ndarray":
        screen_bytes = self._driver.screenshot()
        arr = np.frombuffer(screen_bytes, dtype=np.uint8)
        screen = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if screen is None:
            raise RuntimeError("Failed to decode screenshot from driver")
        return screen
