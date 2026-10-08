"""Auto-installer for the uiautomator HTTP service.

Responsible for:
  1. Detecting whether the uiautomator service APK is on-device.
  2. Pushing / launching the service when missing.
  3. Setting up `adb forward` for stable local HTTP endpoint.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Optional

UIAUTOMATOR_APK = os.environ.get("UIAUTOMATOR_APK", "")
DEVICE_APK_PATH = "/data/local/tmp/u2.jar"
DEFAULT_LOCAL_PORT = 9008


class InstallerError(RuntimeError):
    """Raised when we cannot prepare the on-device uiautomator service."""


class AutoInstaller:
    """Best-effort service installer. Degrades gracefully when ADB is missing."""

    def __init__(self, local_port: int = DEFAULT_LOCAL_PORT) -> None:
        self._local_port = local_port
        self._remote_port = int(os.environ.get("UIAUTOMATOR_PORT", "9008"))

    def ensure_ready(self, device: Any) -> None:
        """Ensure the uiautomator service is running on-device."""
        try:
            exists = device.shell(f"ls {DEVICE_APK_PATH} >/dev/null 2>&1 && echo ok").strip() == "ok"
        except Exception:
            exists = True

        if not exists and UIAUTOMATOR_APK:
            if not os.path.exists(UIAUTOMATOR_APK):
                raise InstallerError(f"uiautomator APK not found: {UIAUTOMATOR_APK}")
            device.sync.push(UIAUTOMATOR_APK, DEVICE_APK_PATH)
            device.shell("chmod 644 %s" % DEVICE_APK_PATH)

        # If service is not listening, try to start it (best effort).
        try:
            pid = device.shell("pidof com.github.uiautomator || true").strip()
        except Exception:
            pid = ""

        if not pid:
            try:
                device.shell(
                    f"app_process -Djava.class.path={DEVICE_APK_PATH} "
                    "/dev/com.github.uiautomator /usr/bin/logcat/com.github.uiautomator.Stub"
                )
            except Exception:
                # Device may already have the service running through another mechanism.
                pass

    def forward_port(self, device: Any) -> int:
        """Set up `adb forward tcp:<port> tcp:<remote>` and return local port."""
        if shutil.which("adb") is None:
            return self._local_port
        try:
            subprocess.run(
                ["adb", "-s", str(device.serial), "forward", f"tcp:{self._local_port}", f"tcp:{self._remote_port}"],
                check=True,
                timeout=10,
            )
        except (subprocess.SubprocessError, OSError):
            pass
        return self._local_port
