"""API 数据提供者 — 从后端接口拉取测试数据。"""
from __future__ import annotations

from typing import Any, Optional

from atomx.infra.data.provider import DataProvider


class APIDataProvider:
    """从后端 API 拉取测试数据的封装。"""

    def __init__(self, base_url: str = "", token: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._provider = DataProvider()

    def fetch(self, endpoint: str, params: Optional[dict] = None, **kwargs: Any) -> Any:
        """从 API 拉取数据"""
        url = f"{self._base_url}{endpoint}" if self._base_url else endpoint
        headers = kwargs.pop("headers", {})
        if self._token:
            headers.setdefault("Authorization", f"Bearer {self._token}")
        return self._provider.from_api(url, params=params, headers=headers, **kwargs)
