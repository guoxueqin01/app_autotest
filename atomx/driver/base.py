from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseDriver(ABC):
    """Platform driver contract."""

    @abstractmethod
    def connect(self, serial: str = "", **kwargs: Any) -> "BaseDriver":
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def dump_hierarchy(self) -> str:
        ...

    @abstractmethod
    def click(self, x: int, y: int) -> None:
        ...

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        ...

    @abstractmethod
    def input_text(self, text: str) -> None:
        ...

    @abstractmethod
    def screenshot(self) -> bytes:
        ...

    @abstractmethod
    def start_app(self, package: str, activity: str = "") -> None:
        ...

    @abstractmethod
    def stop_app(self, package: str) -> None:
        ...

    @abstractmethod
    def press_key(self, key: str) -> None:
        ...

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        ...

    def long_press(self, x: int, y: int, duration: float = 2.0) -> None:
        """长按坐标 — 默认降级为短距 swipe (起点终点相同)"""
        self.swipe(x, y, x, y, duration)

    def screen_record_start(self, **kwargs: Any) -> Optional[str]:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持录屏")

    def screen_record_stop(self) -> bytes:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持录屏")

    def install_app(self, path: str) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持安装应用")
