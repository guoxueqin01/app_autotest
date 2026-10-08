"""AtomX pytest 插件 — 自动截图/录屏/步骤记录/多设备并行分发。

功能:
1. 自动截图: 每个操作步骤截图并附加到 Allure
2. 失败重跑: 配合 pytest-rerunfailures
3. 多设备并行: 配合 pytest-xdist
4. 视频录屏: 测试期间自动录屏
5. 性能指标: 采集每步耗时
6. UI 树快照: 每个关键步骤自动 dump UI 树
"""
from __future__ import annotations

import functools
import time
from typing import Any

import pytest


# ==================== 1. 操作步骤自动截图 ====================

class ScreenshotContext:
    """上下文管理器: 在 Allure step 内自动截图"""

    _screenshot_enabled = True
    _screenshot_interval = 1.0  # 最小截图间隔

    @classmethod
    def attach_screenshot(cls, app: Any, step_name: str = "") -> None:
        if not cls._screenshot_enabled:
            return
        try:
            import allure  # type: ignore

            screenshot = app.driver.screenshot()
            allure.attach(
                screenshot,
                name=f"{step_name or 'step'}_{time.time():.0f}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:  # noqa: BLE001
            pass


# ==================== 2. 录屏管理 ====================

class VideoRecorder:
    """测试期间录屏 — 结束后附加到 Allure"""

    _recordings: dict = {}  # test_node_id -> video_path

    @classmethod
    def start(cls, app: Any, node_id: str) -> None:
        try:
            path = app.driver.screen_record_start()
            cls._recordings[node_id] = path
        except Exception:  # noqa: BLE001
            pass

    @classmethod
    def stop_and_attach(cls, app: Any, node_id: str) -> None:
        if node_id not in cls._recordings:
            return
        try:
            import allure  # type: ignore

            video_bytes = app.driver.screen_record_stop()
            if video_bytes:
                allure.attach(
                    video_bytes,
                    name="录屏",
                    attachment_type=allure.attachment_type.MP4,
                )
        except Exception:  # noqa: BLE001
            pass
        finally:
            cls._recordings.pop(node_id, None)


# ==================== 3. pytest hooks ====================

def pytest_runtest_teardown(item: Any, nextitem: Any) -> None:
    """每个用例执行后 — 停止录屏并附加"""
    app = getattr(item, "_atomx_app", None)
    if app:
        VideoRecorder.stop_and_attach(app, item.nodeid)


# ==================== 4. Allure 步骤自动截图装饰器 ====================

def atomx_step(name: str = "", screenshot: bool = True):
    """AtomX Allure 步骤装饰器 — 自动截图 + 耗时记录

    用法:
        @atomx_step("执行登录", screenshot=True)
        def login(app, user, pwd):
            app.find("登录").tap()
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                import allure  # type: ignore
                step_ctx = allure.step(name or func.__name__)
            except ImportError:
                step_ctx = _NullContext()

            with step_ctx:
                start = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start

                if screenshot:
                    app = None
                    for arg in args:
                        if hasattr(arg, "find") and hasattr(arg, "driver"):
                            app = arg
                            break
                    if app:
                        ScreenshotContext.attach_screenshot(app, name or func.__name__)

                try:
                    import allure  # type: ignore
                    allure.attach(
                        f"耗时: {duration:.3f}s",
                        name="性能指标",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                except ImportError:
                    pass

                return result
        return wrapper
    return decorator


class _NullContext:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
