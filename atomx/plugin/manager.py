"""PluginManager — 注册、排序、分发回调。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from atomx.plugin.base import AtomXPlugin


class PluginManager:
    """插件管理器 — 注册、排序、分发回调。"""

    def __init__(self) -> None:
        self._plugins: List[AtomXPlugin] = []

    def register(self, plugin: AtomXPlugin) -> None:
        """注册插件，按 priority 排序"""
        if not isinstance(plugin, AtomXPlugin):
            raise TypeError("plugin must be an AtomXPlugin instance")
        self._plugins.append(plugin)
        self._plugins.sort(key=lambda p: p.priority)

    def unregister(self, name: str) -> None:
        """注销插件"""
        self._plugins = [p for p in self._plugins if p.name != name]

    def get(self, name: str) -> Optional[AtomXPlugin]:
        """获取指定插件"""
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    def plugins(self) -> List[AtomXPlugin]:
        return list(self._plugins)

    # === 回调分发 ===

    def call_connect(self, app: Any, **kwargs: Any) -> None:
        for plugin in self._plugins:
            try:
                plugin.on_connect(app, **kwargs)
            except Exception:  # noqa: BLE001
                pass

    def call_disconnect(self, app: Any) -> None:
        for plugin in self._plugins:
            try:
                plugin.on_disconnect(app)
            except Exception:  # noqa: BLE001
                pass

    def call_find(self, app: Any, locator: Any, result: Any = None) -> Any:
        for plugin in self._plugins:
            try:
                result = plugin.on_find(app, locator, result)
            except Exception:  # noqa: BLE001
                pass
        return result

    def call_action(self, app: Any, action: str, args: tuple, kwargs: dict, result: Any = None) -> Any:
        for plugin in self._plugins:
            try:
                result = plugin.on_action(app, action, args, kwargs, result)
            except Exception:  # noqa: BLE001
                pass
        return result

    def call_assert(self, app: Any, assertion: str, passed: bool, **kwargs: Any) -> None:
        for plugin in self._plugins:
            try:
                plugin.on_assert(app, assertion, passed, **kwargs)
            except Exception:  # noqa: BLE001
                pass

    def call_error(self, app: Any, error: Exception, context: dict) -> None:
        for plugin in self._plugins:
            try:
                plugin.on_error(app, error, context)
            except Exception:  # noqa: BLE001
                pass

    def call_screenshot(self, app: Any, png: bytes, tag: str = "screenshot") -> None:
        for plugin in self._plugins:
            try:
                plugin.on_screenshot(app, png, tag)
            except Exception:  # noqa: BLE001
                pass

    def call_report(self, app: Any, report_data: dict) -> dict:
        for plugin in self._plugins:
            try:
                report_data = plugin.on_report(app, report_data)
            except Exception:  # noqa: BLE001
                pass
        return report_data

    def call_teardown(self, app: Any) -> None:
        for plugin in self._plugins:
            try:
                plugin.teardown(app)
            except Exception:  # noqa: BLE001
                pass

    # === 配置驱动注册 ===

    @classmethod
    def from_config(cls, config: dict, app: Any) -> "PluginManager":
        """从 config.yaml 的 plugins 段自动实例化插件"""
        pm = cls()
        plugins_cfg: Dict[str, dict] = config.get("plugins", {}) or {}
        for name, opts in plugins_cfg.items():
            if not isinstance(opts, dict) or not opts.get("enabled", True):
                continue
            plugin = _try_create_builtin(name, opts)
            if plugin is not None:
                pm.register(plugin)
        return pm


def _try_create_builtin(name: str, opts: dict) -> Optional[AtomXPlugin]:
    """尝试创建内置插件"""
    if name in ("auto_screenshot", "screenshot"):
        from atomx.plugin.builtin.auto_screenshot import AutoScreenshotPlugin
        return AutoScreenshotPlugin(
            enabled=opts.get("enabled", True),
            on_step=opts.get("on_step", False),
            on_failure=opts.get("on_failure", True),
        )
    if name in ("watcher", "watcher_plugin"):
        from atomx.plugin.builtin.watcher import WatcherPlugin
        return WatcherPlugin(
            enabled=opts.get("enabled", True),
            interval=opts.get("interval", 2.0),
        )
    return None
