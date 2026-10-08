"""HTTP RPC transport for Android UiAutomator service.

Talks to the on-device uiautomator HTTP service using `requests`. Supports
both simple JSON-RPC style methods and byte-returning endpoints (screenshot).
"""
from __future__ import annotations

import base64
import json
from typing import Any, Optional

import requests


class TransportError(RuntimeError):
    """Raised when the on-device RPC service fails or is unreachable."""


class HttpTransport:
    """Minimal HTTP transport for the uiautomator HTTP service."""

    def __init__(self, base_url: str, timeout: float = 10.0, session: Optional[requests.Session] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

    def healthcheck(self) -> bool:
        try:
            r = self._session.get(f"{self.base_url}/ping", timeout=self.timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def jsonrpc_call(self, method: str, *args: Any, return_bytes: bool = False, **kwargs: Any) -> Any:
        """Call a JSON-RPC style method on the uiautomator service."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {"args": args, "kwargs": kwargs} if (args or kwargs) else {},
            "id": 1,
        }
        try:
            r = self._session.post(
                f"{self.base_url}/jsonrpc/0",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TransportError(f"RPC call failed for method={method}: {exc}") from exc

        if r.status_code != 200:
            raise TransportError(f"RPC HTTP {r.status_code}: {r.text[:200]}")

        try:
            body = r.json()
        except ValueError as exc:
            # Some uiautomator endpoints return raw binary (screenshots).
            if return_bytes:
                return r.content
            raise TransportError(f"RPC response is not JSON for method={method}") from exc

        if isinstance(body, dict) and "error" in body and body["error"]:
            raise TransportError(f"RPC error for {method}: {body['error']}")

        if return_bytes:
            result = body.get("result") if isinstance(body, dict) else body
            if isinstance(result, str):
                return base64.b64decode(result)
            return r.content

        if isinstance(body, dict) and "result" in body:
            return body["result"]
        return body

    def raw_get(self, path: str, **params: Any) -> bytes:
        r = self._session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        if r.status_code != 200:
            raise TransportError(f"GET {path} -> {r.status_code}")
        return r.content
