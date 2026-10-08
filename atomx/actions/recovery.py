"""SessionRecovery — tiered error recovery around element operations.

Levels of recovery:
  1. RETRY: transient network/RPC failures get a short retry budget.
  2. RECONNECT: driver-level reconnect when the RPC transport is broken.
  3. RAISE: if the exception is semantic (element not found) we bail out.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional, Tuple, Type

from atomx.engine.control.element import ElementNotFoundError


class RecoveryExhausted(RuntimeError):
    """Raised after all recovery strategies are exhausted."""


class SessionRecovery:
    """Small policy engine around element lookups."""

    RETRIABLE = (TimeoutError, ConnectionError, OSError)
    SEMANTIC = (ElementNotFoundError, ValueError, TypeError)

    def __init__(self, atomx: Any, max_retries: int = 3, retry_delay: float = 0.2, reconnect: bool = True) -> None:
        self._atomx = atomx
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._reconnect = reconnect

    def execute_with_recovery(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exc: Optional[BaseException] = None
        attempts = 0
        while attempts <= self._max_retries:
            try:
                return func(*args, **kwargs)
            except self.SEMANTIC:
                raise
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                # 通知插件 on_error hook
                self._notify_error(exc)
                attempts += 1
                if not isinstance(exc, self.RETRIABLE):
                    # Unknown error — try once more then bail.
                    if attempts >= self._max_retries:
                        break
                if self._reconnect and self._should_reconnect(exc):
                    self._try_reconnect()
                time.sleep(self._retry_delay * attempts)

        raise RecoveryExhausted(f"Failed after {attempts} attempts: {last_exc}") from last_exc

    def _notify_error(self, exc: BaseException) -> None:
        """通知插件 on_error hook"""
        atomx = self._atomx
        if atomx is None:
            return
        plugins = getattr(atomx, "_plugins", None)
        if plugins is not None:
            try:
                plugins.call_error(atomx, exc, {"action": "recovery"})
            except Exception:  # noqa: BLE001
                pass

    def _should_reconnect(self, exc: BaseException) -> bool:
        name = exc.__class__.__name__.lower()
        return "transport" in name or "connection" in name or "timeout" in name

    def _try_reconnect(self) -> None:
        atomx = self._atomx
        if not atomx:
            return
        try:
            platform = getattr(atomx, "_platform", "")
            serial = getattr(atomx, "_serial", "")
            if not platform:
                return
            atomx.connect(platform=platform, serial=serial)
        except Exception:  # noqa: BLE001
            pass
