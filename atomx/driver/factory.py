"""DriverFactory — maps platform name to concrete driver class."""
from __future__ import annotations

from typing import Any, Dict, Type

from atomx.driver.android.driver import AndroidDriver
from atomx.driver.base import BaseDriver
from atomx.driver.harmony.driver import HarmonyDriver
from atomx.driver.ios.driver import IOSDriver


class DriverFactory:
    """Create the right driver class based on platform name."""

    _registry: Dict[str, Type[BaseDriver]] = {
        "android": AndroidDriver,
        "ios": IOSDriver,
        "harmony": HarmonyDriver,
    }

    @classmethod
    def register(cls, platform: str, driver_cls: Type[BaseDriver]) -> None:
        cls._registry[platform] = driver_cls

    @classmethod
    def supported_platforms(cls) -> list:
        return sorted(cls._registry.keys())

    @classmethod
    def validate_platform(cls, platform: str) -> str:
        if platform not in cls._registry:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {cls.supported_platforms()}")
        return platform

    @classmethod
    def create(cls, platform: str, serial: str = "", **kwargs: Any) -> BaseDriver:
        cls.validate_platform(platform)
        driver = cls._registry[platform]()
        return driver.connect(serial=serial, **kwargs)
