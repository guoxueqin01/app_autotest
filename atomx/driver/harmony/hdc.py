"""Minimal `hdc` command wrapper for HarmonyOS devices.

`hdc` is HarmonyOS' analogue to `adb`. We shell out to the binary via
subprocess so users can install hdc from the SDK without touching Python.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Iterable, Optional


class HdcError(RuntimeError):
    """Raised when hdc cannot be executed or returns a non-zero exit code."""


class HdcClient:
    """Small wrapper around the `hdc` command line tool."""

    def __init__(self, serial: str = "") -> None:
        self.serial = serial
        self._binary = shutil.which("hdc") or os.environ.get("HDC_BIN", "hdc")

    # -- Device discovery --

    @staticmethod
    def list_targets() -> list:
        try:
            result = subprocess.run(["hdc", "list", "targets"], capture_output=True, text=True, timeout=10)
        except (FileNotFoundError, subprocess.SubprocessError):
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _args(self, *extra: str) -> Iterable[str]:
        base = [self._binary]
        if self.serial:
            base.extend(["-t", self.serial])
        return [*base, *extra]

    # -- Shell / file ops --

    def shell(self, cmd: str, timeout: float = 15.0) -> str:
        try:
            result = subprocess.run(
                list(self._args("shell", cmd)),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise HdcError(f"hdc binary not found (tried {self._binary!r})") from exc
        except subprocess.SubprocessError as exc:
            raise HdcError(f"hdc shell failed: {exc}") from exc
        if result.returncode != 0:
            raise HdcError(f"hdc shell exit={result.returncode} stderr={result.stderr[:200]}")
        return result.stdout

    def pull_bytes(self, remote_path: str) -> bytes:
        local = "/tmp/atomx_hdc_pull.bin"
        try:
            subprocess.run(list(self._args("file", "recv", remote_path, local)), check=True, timeout=30)
            with open(local, "rb") as f:
                return f.read()
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            raise HdcError(f"hdc pull failed for {remote_path}: {exc}") from exc

    def push(self, local_path: str, remote_path: str) -> None:
        subprocess.run(list(self._args("file", "send", local_path, remote_path)), check=True, timeout=30)

    def info(self) -> dict:
        out: dict[str, Any] = {}
        try:
            out["version"] = self.shell("param get const.ohos.boot.hardware.version").strip()
        except HdcError:
            pass
        return out
