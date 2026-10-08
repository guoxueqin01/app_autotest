"""AtomXPlugin — 基类，8 个 Hook 点。

插件通过继承此类实现自定义逻辑，priority 决定执行顺序 (数字越小越先)。
"""
from __future__ import annotations

from abc import ABC
from typing import Any, Optional


class AtomXPlugin(ABC):
    """AtomX 插件基类 — 用户通过继承此类实现自定义插件。"""

    name: str = "base"
    priority: int = 0  # 执行优先级 (数字越小越先执行)

    def on_connect(self, app: Any, **kwargs: Any) -> None:
        """连接设备后回调"""
        pass

    def on_disconnect(self, app: Any) -> None:
        """断开设备前回调"""
        pass

    def on_find(self, app: Any, locator: Any, result: Any = None) -> Any:
        """查找元素后回调 — 可修改 result"""
        return result

    def on_action(self, app: Any, action: str, args: tuple, kwargs: dict,
                  result: Any = None) -> Any:
        """执行操作后回调 — 可修改 result"""
        return result

    def on_assert(self, app: Any, assertion: str, passed: bool, **kwargs: Any) -> None:
        """断言后回调"""
        pass

    def on_error(self, app: Any, error: Exception, context: dict) -> None:
        """异常发生时回调 — 可决定是否恢复"""
        pass

    def on_report(self, app: Any, report_data: dict) -> dict:
        """生成报告时回调 — 可附加数据"""
        return report_data

    def on_screenshot(self, app: Any, png: bytes, tag: str) -> None:
        """截图后回调"""
        pass

    def teardown(self, app: Any) -> None:
        """框架关闭时清理"""
        pass
