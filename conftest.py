"""Root pytest fixtures — platform / device / AtomX session + Allure 深度集成."""
from __future__ import annotations

import os
import traceback
from typing import Any

import pytest

# 注册 AtomX pytest 插件 (录屏/标记)
pytest_plugins = ["atomx.plugin.pytest_plugin"]

from atomx import AtomX  # noqa: E402
from atomx.plugin.pytest_plugin import VideoRecorder  # noqa: E402
from utils.config import load_config  # noqa: E402


# ==================== 命令行参数 ====================

def pytest_addoption(parser: Any) -> None:
    parser.addoption("--platform", action="store", default=None,
                      choices=["android", "ios", "harmony"],
                      help="目标测试平台")
    parser.addoption("--serial", action="store", default=None,
                      help="设备序列号 (留空自动选择)")
    parser.addoption("--app-package", action="store", default=None,
                      help="被测应用包名")
    parser.addoption("--package", action="store", default=None,
                      help="被测应用包名 (同 --app-package 别名)")


# ==================== 平台过滤 — no-op, 通过 -m 标记过滤 ====================

def pytest_collection_modifyitems(config: Any, items: list) -> None:
    """不自动按平台跳过用例；平台过滤通过 -m 标记完成"""
    pass


# ==================== Allure 环境信息 ====================

@pytest.fixture(scope="session", autouse=True)
def allure_environment(request: Any) -> None:
    """将设备信息写入 Allure 环境变量 — 报告首页展示"""
    try:
        import allure  # type: ignore
    except ImportError:
        return

    platform = request.config.getoption("--platform") or "android"
    serial = request.config.getoption("--serial") or "auto"

    allure.attach(
        f"Platform={platform}\n"
        f"DeviceSerial={serial}\n"
        f"Python={os.popen('python --version').read().strip()}\n"
        f"AtomX={getattr(AtomX, '__version__', 'dev')}\n"
        f"TestTime={__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        name="environment.properties",
        attachment_type=allure.attachment_type.PROPERTIES,
    )


# ==================== Session 级 Fixture ====================

@pytest.fixture(scope="session")
def config(request: Any) -> dict:
    """全局配置 — CLI 参数优先于 config.yaml"""
    base = load_config()
    for key in ("platform", "serial"):
        val = request.config.getoption(f"--{key}")
        if val:
            base[key] = val
    pkg = request.config.getoption("--app-package") or request.config.getoption("--package")
    if pkg:
        base["package"] = pkg
    return base


@pytest.fixture(scope="session")
def device_info(config: dict) -> dict:
    """Session 级设备信息 — 从 config 读取，保证 CLI 和 yaml 一致性"""
    return {"platform": config.get("platform", "android"), "serial": config.get("serial", "")}


# ==================== Function 级 App Fixture ====================

@pytest.fixture(scope="function")
def app(request: Any, device_info: dict, config: dict) -> Any:
    """每个测试函数自动创建/销毁 AtomX 实例 — 自动关联 Allure"""
    try:
        import allure  # type: ignore
        _has_allure = True
    except ImportError:
        _has_allure = False

    platform = device_info["platform"]
    serial = device_info.get("serial", "")

    # Allure 动态标签
    if _has_allure:
        allure.dynamic.label("platform", platform)
        allure.dynamic.label("device", serial or "auto")
        allure.dynamic.title(request.node.name.replace("test_", "").replace("_", " ").title())

        for marker in request.node.iter_markers():
            if marker.name in ("feature", "story", "epic"):
                allure.dynamic.label(marker.name, marker.name)

    # 创建 AtomX 实例并传入 config (自动加载插件)
    atomx = AtomX(config=config)

    # 注册 Allure 操作回调 (实例级, 非全局猴补丁)
    allure_hooks = AllureHooks(atomx) if _has_allure else None
    allure_hooks.install() if allure_hooks else None

    if _has_allure:
        with allure.step(f"连接 {platform} 设备: {serial or 'auto'}"):
            atomx.connect(platform=platform, serial=serial)
    else:
        atomx.connect(platform=platform, serial=serial)

    # 录屏: 根据 diagnostics 配置决定是否开启
    # 停止录屏由 pytest_plugin.py 的 pytest_runtest_teardown 负责
    if config.get("diagnostics", {}).get("failure_video", True):
        try:
            VideoRecorder.start(atomx, request.node.nodeid)
        except Exception:  # noqa: BLE001
            pass

    # 保存 app 引用供 pytest_runtest_teardown 使用
    request.node._atomx_app = atomx

    yield atomx

    # Teardown 顺序: pytest_runtest_teardown 先停止录屏, 本 finalizer 再截图
    # 失败时附加截图 + UI 树 + 异常堆栈 + 设备日志
    if hasattr(request.node, "rep_call") and request.node.rep_call and request.node.rep_call.failed:
        if config.get("diagnostics", {}).get("failure_screenshot", True):
            _attach_failure_screenshot(atomx, request)

    # 还原 Allure hooks
    if allure_hooks:
        allure_hooks.uninstall()

    try:
        if _has_allure:
            with allure.step("断开设备连接"):
                atomx.disconnect()
        else:
            atomx.disconnect()
    except Exception:  # noqa: BLE001
        pass


# ==================== Hooks: 测试结果监听 ====================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any) -> Any:
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ==================== AllureHooks — 实例级, 避免 Element 全局猴补丁累积 ====================

class AllureHooks:
    """实例级 Allure 操作回调 — install/uninstall 配对, 不污染类方法"""

    def __init__(self, app: AtomX) -> None:
        self._app = app
        self._original_find = None
        self._installed = False  # 实例变量, 非类变量

    def install(self) -> None:
        if self._installed:
            return
        try:
            import allure  # type: ignore
        except ImportError:
            return

        self._original_find = self._app.find

        @allure.step("查找元素: {locator}")
        def _allure_find(locator):
            return self._original_find(locator)

        self._app.find = _allure_find
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        if self._original_find is not None:
            self._app.find = self._original_find
        self._installed = False


# ==================== 辅助函数 ====================

def _attach_failure_screenshot(app: AtomX, request: Any) -> None:
    """失败时截图 + UI 树 + 异常堆栈 + 设备日志附加到 Allure"""
    try:
        import allure  # type: ignore
    except ImportError:
        return

    # 1. 截图
    try:
        screenshot = app.driver.screenshot()
        allure.attach(screenshot, name="失败截图",
                      attachment_type=allure.attachment_type.PNG)
    except Exception:  # noqa: BLE001
        pass

    # 2. UI 树 (XML)
    try:
        hierarchy = app.driver.dump_hierarchy()
        allure.attach(hierarchy, name="UI层级树",
                      attachment_type=allure.attachment_type.XML)
    except Exception:  # noqa: BLE001
        pass

    # 3. 异常信息
    try:
        allure.attach(traceback.format_exc(), name="异常堆栈",
                      attachment_type=allure.attachment_type.TEXT)
    except Exception:  # noqa: BLE001
        pass

    # 4. 设备日志 (logcat / syslog)
    try:
        driver_name = app.driver.__class__.__name__
        if driver_name == "AndroidDriver":
            device = getattr(app.driver, "_device", None)
            if device:
                logs = device.shell("logcat -d -t 200")
            else:
                logs = "设备日志不可用"
        elif driver_name == "IOSDriver":
            logs = "iOS 设备日志需通过 idevicesyslog 获取"
        elif driver_name == "HarmonyDriver":
            hdc = getattr(app.driver, "_hdc", None)
            if hdc:
                logs = hdc.shell("hilog -x 2>/dev/null | tail -200")
            else:
                logs = "鸿蒙设备日志不可用"
        else:
            logs = "日志获取不支持"
        allure.attach(logs, name="设备日志",
                      attachment_type=allure.attachment_type.TEXT)
    except Exception:  # noqa: BLE001
        pass
