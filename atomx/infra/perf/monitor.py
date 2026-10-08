"""PerfMonitor — lightweight CPU/memory/FPS sampling.

The implementation is intentionally dependency-light: it shells to the
platform's native tools (adb shell, hdc shell) so we don't need extra
Python packages.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


class PerfMonitor:
    """Read process CPU/memory from the device."""

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    def process(self, package: str) -> Dict[str, float]:
        shell = self._try_shell()
        if shell is None:
            return {}
        # Android/Harmony: dumpsys + top -m 1
        try:
            top = shell(f"top -b -n 1 -m 3 2>/dev/null | grep {re.escape(package)} | head -n1")
        except Exception:  # noqa: BLE001
            top = ""
        return self._parse_top_line(top, package)

    @staticmethod
    def _parse_top_line(line: str, package: str) -> Dict[str, float]:
        if not line:
            return {}
        parts = line.split()
        # Typical columns: USER PID ... %CPU CPU% MEM% COMMAND
        out: Dict[str, float] = {}
        for i, tok in enumerate(parts):
            if i < 3:
                continue
            if tok.endswith("%"):
                try:
                    out[f"metric_{i}"] = float(tok[:-1])
                except ValueError:
                    continue
        return out

    def _try_shell(self) -> Optional[Any]:
        device = getattr(self._driver, "_device", None)
        if device is not None and hasattr(device, "shell"):
            return device.shell
        hdc = getattr(self._driver, "_hdc", None)
        if hdc is not None and hasattr(hdc, "shell"):
            return hdc.shell
        return None
