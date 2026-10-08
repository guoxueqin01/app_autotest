"""数据清理脚本 — 测试后清理数据。"""
from __future__ import annotations

from typing import Any, List


def cleanup_test_users(usernames: List[str], api_provider: Any = None) -> None:
    """清理测试用户数据"""
    if api_provider is None:
        return
    for username in usernames:
        try:
            api_provider.fetch(f"/api/test/users/{username}", method="DELETE")
        except Exception:  # noqa: BLE001
            pass


def cleanup_test_orders(order_ids: List[str], api_provider: Any = None) -> None:
    """清理测试订单数据"""
    if api_provider is None:
        return
    for order_id in order_ids:
        try:
            api_provider.fetch(f"/api/test/orders/{order_id}", method="DELETE")
        except Exception:  # noqa: BLE001
            pass
