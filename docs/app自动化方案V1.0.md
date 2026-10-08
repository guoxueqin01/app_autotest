# AtomX — 跨平台 App 自动化测试框架设计方案

> **AtomX** = App Test automation, Open-source, Multi-platform, eXtended
>
> 基于 Python 技术栈，整合 Appium、uiautomator2、Airtest、facebook-wda、Shadowstep 等开源框架的优点，支持 **Android / iOS / HarmonyOS** 三平台。

---

## 一、设计背景与目标

### 1.1 现有框架优缺点回顾

| 框架 | 核心优势 | 核心短板 |
|---|---|---|
| Appium Python Client | 跨平台、生态成熟、W3C 标准 | 速度慢（Server 中转）、环境复杂 |
| uiautomator2 | 极快（毫秒级）、纯 Python、API 简洁 | 仅 Android、v2→v3 破坏性变更 |
| Airtest Project | 图像识别、游戏测试、IDE 开箱即用 | 图像识别不稳定、性能损耗 |
| facebook-wda | 轻量 iOS 自动化 | 仅 iOS、需 Mac+Xcode 部署 |
| Shadowstep | Facade/PO/Navigator 设计模式完善 | 仅 Android、仍依赖 Appium |

### 1.2 设计目标

整合以上框架优点，打造一个：

```
快速（uiautomator2 级别）  +  跨平台（Appium 级别）  +  双引擎（Airtest 级别）  +  架构完善（Shadowstep 级别）
```

**具体目标：**

1. **三平台支持**：Android、iOS、HarmonyOS 统一 API
2. **双引擎驱动**：控件引擎（UI 树定位） + 图像引擎（OpenCV 视觉识别）
3. **高性能**：Android 优先直连 RPC（非 Appium 中转），毫秒级响应
4. **低门槛**：`pip install` 即用，可选 IDE 录制
5. **设计模式**：Facade / Page Object / Models 内置
6. **页面对象自动生成**：从 UI 树自动生成 Page Object 和 Models 代码
7. **HTML 报告**：截图、录屏、操作步骤全记录
8. **多设备并行**：pytest-xdist + 多设备调度
9. **CI/CD 友好**：JSON 日志、命令行驱动、Docker 化

---

## 二、整体架构

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│              测试用例层 (testcases/)                                  │
│   test_login.py  /  test_order_list.py  /  conftest.py              │
├──────────────────────────┬──────────────────────────────────────────┤
│  Page Object 层 (pages/)  │  Models 层 (models/)                      │
│  BasePage / XxxPage       │  BaseModels / XxxPageData (dataclass)     │
│  (元素定位器+操作+断言+     │  (连接 YAML 数据和 Page Object)            │
│   列表/表格行操作)         │                                          │
├──────────────────────────┴──────────────────────────────────────────┤
│                    代码生成器 (script/generator/)                    │
│  Scanner (UI树扫描) → Analyzer (元素分析) → CodeGenerator (Jinja2)  │
├─────────────────────────────────────────────────────────────────────┤
│                     API 层 (atomx/api.py)                            │
│   AtomX Facade ── find() / tap() / swipe() / start_app()            │
│        ├── SmartWait (隐式/显式/条件等待)                              │
│        ├── AssertionActions (元素/属性/图像/数值 断言)                  │
│        └── SessionRecovery (异常分级恢复)                             │
├──────────────┬──────────────┬───────────────────────────────────────┤
│ ControlEngine │  ImageEngine │  LocatorAdapter                        │
│ (UI 树定位)    │  (视觉识别)   │  (统一语义 → 平台属性翻译)              │
├──────────────┴──────────────┴───────────────────────────────────────┤
│              Platform Driver 层 (atomx/driver/)                     │
│  AndroidDriver  │  IOSDriver  │  HarmonyDriver                      │
│  (uiautomator2)  │  (WDA)      │  (hdc + uitest)                   │
├─────────────────────────────────────────────────────────────────────┤
│              基础设施层 (atomx/infra/)                               │
│  PerfMonitor │ Logger │ PluginManager (6 Hook 点扩展)              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

| 原则 | 说明 | 借鉴来源 |
|---|---|---|
| **Driver 抽象** | 平台差异封装在 Driver 层，上层 API 统一 | Appium |
| **直连优先** | Android 走 RPC 直连，不走 Server 中转 | uiautomator2 |
| **双引擎互补** | 控件引擎处理标准 UI，图像引擎处理游戏/Canvas | Airtest |
| **LocatorAdapter** | 统一定位语义 → 平台属性自动翻译，一行代码三平台适配 | 新设计 |
| **Page Object + Models** | 按页面生成 PO 类和 dataclass Models，代码生成器自动生成 | web_quality_ui_playwright |
| **渐进式复杂度** | 简单场景一行代码搞定，复杂场景可深度定制 | uiautomator2 |

---

## 三、项目目录结构

整个自动化项目是一个完整的工程，框架核心代码直接整合在项目内的 `atomx/` 包中。第三方依赖（adbutils、lxml、opencv、Jinja2 等）通过 `requirements.txt` 安装。

```
app_autotest/                       # 项目根目录
├── pytest.ini                      # pytest 配置
├── conftest.py                     # 全局 fixture (app 连接/失败截图/标记注册)
├── requirements.txt                # 依赖清单
│
├── atomx/                          # ========== 框架核心包 ==========
│   ├── __init__.py                 # 版本号、公共导出
│   ├── api.py                      # AtomX Facade 入口 (统一 API)
│   │
│   ├── driver/                     # ---- 平台驱动层 ----
│   │   ├── base.py                 # BaseDriver 抽象基类
│   │   ├── android/
│   │   │   ├── driver.py           # AndroidDriver (uiautomator2 直连 RPC)
│   │   │   ├── transport.py        # HTTP RPC 通信
│   │   │   └── installer.py        # 自动推送 uiautomator 服务
│   │   ├── ios/
│   │   │   ├── driver.py           # IOSDriver (WDA)
│   │   │   └── usb_client.py       # USB 直连 (usbmuxd)
│   │   └── harmony/
│   │       ├── driver.py           # HarmonyDriver (hdc + uitest)
│   │       └── hdc.py              # hdc 命令封装
│   │
│   ├── engine/                     # ---- 双引擎层 ----
│   │   ├── control/
│   │   │   ├── engine.py           # ControlEngine (UI 树定位)
│   │   │   ├── locator_adapter.py  # LocatorAdapter (统一语义 → 平台属性翻译)
│   │   │   └── element.py          # Element 跨平台元素抽象
│   │   └── image/
│   │       └── engine.py           # ImageEngine (OpenCV 模板匹配)
│   │
│   ├── actions/                    # ---- 操作 API 层 ----
│   │   ├── wait.py                 # SmartWait (三层等待: 隐式/显式/条件)
│   │   ├── assert_.py              # AssertionActions (四类断言 + 自动截图)
│   │   └── recovery.py             # SessionRecovery (异常分级恢复)
│   │
│   ├── infra/                      # ---- 基础设施层 ----
│   │   ├── perf/
│   │   │   └── monitor.py          # PerfMonitor (CPU/内存/FPS/电量采集)
│   │   └── logger.py               # 统一日志 (loguru)
│   │
│   └── plugin/                     # ---- 插件机制 ----
│       ├── base.py                 # AtomXPlugin 基类 (6 个 Hook 点)
│       └── manager.py              # PluginManager
│
├── pages/                          # ========== Page Object 层 ==========
│   ├── __init__.py
│   ├── base_page.py                # BasePage 基类 (通用: tap/fill/assert/wait/scroll)
│   ├── login/                      # 按页面/模块分目录
│   │   ├── __init__.py
│   │   └── login_page.py           # LoginPage (元素定位器 + 操作方法 + 断言方法)
│   ├── order/
│   │   ├── __init__.py
│   │   ├── order_list_page.py      # OrderListPage (含列表/表格行操作)
│   │   └── order_detail_page.py    # OrderDetailPage
│   └── profile/
│       ├── __init__.py
│       └── profile_page.py         # ProfilePage
│
├── models/                         # ========== Models 数据层 ==========
│   ├── __init__.py
│   ├── base_models.py              # BaseModels (ExtractRule/AssertionRule/StepData/CaseData)
│   ├── login/
│   │   ├── __init__.py
│   │   └── login_models.py         # LoginPageData (dataclass, 连接 YAML 和 Page)
│   ├── order/
│   │   ├── __init__.py
│   │   ├── order_list_models.py    # OrderListPageData
│   │   └── order_detail_action_models.py  # OrderDetailActionData
│   └── profile/
│       └── profile_models.py
│
├── testcases/                      # ========== 测试用例 ==========
│   ├── conftest.py                 # 全局 fixture (app 连接/失败截图/Allure/hooks)
│   ├── login/                      # 登录功能用例
│   │   ├── test_login.py           # 三平台通用登录流程
│   │   ├── test_login_ios.py       # iOS 专属功能
│   │   └── test_login_android.py   # Android 专属功能
│   ├── search/                     # 搜索功能用例
│   │   ├── test_search.py
│   │   └── test_search_ios.py
│   ├── order/                      # 订单功能用例
│   │   ├── test_order_list.py
│   │   └── test_order_detail.py
│   └── profile/                    # 个人中心功能用例
│       └── test_profile.py
│
├── data/                           # ========== 测试数据 ==========
│   ├── login_data.yaml             # 登录测试数据 (→ LoginPageData)
│   ├── order_data.yaml             # 订单测试数据 (→ OrderListPageData)
│   └── env_config.yaml             # 环境配置
│
├── script/                         # ========== 脚本/工具 ==========
│   └── generator/                  # ---- 代码生成器 ----
│       ├── __init__.py
│       ├── cli.py                   # 生成器 CLI 入口 (python -m script.generator.cli)
│       ├── core/
│       │   ├── scanner.py           # UI 树扫描器 (连接设备 → dump UI 树 → 提取元素)
│       │   ├── analyzer.py          # 元素分析器 (分类/命名/分组 → 结构化数据)
│       │   ├── code_generator.py   # 代码生成器 (Jinja2 模板渲染 → PO + Models)
│       │   └── constants.py         # 元素类型常量 (input/button/select/text/...)
│       ├── templates/               # Jinja2 模板文件
│       │   ├── page_object.jinja2  # Page 类模板 (元素定位器+操作方法+断言+表格操作)
│       │   └── model.jinja2        # Models 类模板 (dataclass 字段)
│       └── config/
│           └── default_config.yaml  # 扫描配置 (元素类型规则/命名规则)
│
├── config/                         # ========== 配置 ==========
│   └── config.yaml                 # 全局配置 (平台/设备/插件/Allure)
│
├── utils/                          # ========== 工具 ==========
│   ├── logger.py                   # 日志 (loguru)
│   ├── config.py                   # 配置读取
│   └── data_loader.py              # 数据加载 (YAML → dict → Models dataclass)
│
└── docs/                           # ========== 文档 ==========
    └── app自动化方案.md
```

### 3.2 各层调用关系

```
conftest.py                     testcases/                      pages/
┌──────────────┐               ┌──────────────┐               ┌──────────────┐
│ app fixture  │ ←── request ─│test_login.py │ ── import ──→│ login_page.py│
│ (连接设备)    │               │              │               │              │
│ 失败自动截图  │               │ 使用 Page    │               │ 元素定位器    │
│ 标记注册      │               │ + Models     │               │ 操作方法      │
└──────────────┘               │ + YAML 数据  │               │ 断言方法      │
       │                       └──────────────┘               │ 列表/表格操作 │
       │                               │                      └──────┬───────┘
       │                               │ import                      │ import
       ▼                               ▼                             ▼
┌──────────────┐               ┌──────────────┐               ┌──────────────┐
│ atomx/       │               │ models/      │               │ atomx/      │
│ api.AtomX    │               │login_models  │ ←─ dataclass ─│ api.AtomX   │
│ driver/      │               └──────────────┘               │ engine/     │
│ engine/      │                      ▲                       │ actions/    │
│ actions/     │                      │ YAML                   └──────────────┘
│ infra/       │                      │ load                   │     ▲
└──────────────┘               ┌──────────────┐               │     │
                               │ data/         │ ─────────────┘     │
                               │login_data.yaml│                    │
                               └──────────────┘                    │
                                                                   │
script/generator/                                                  │
┌──────────────────────────────────┐                               │
│cli.py                            │                               │
│  ├── Scanner (连接设备,dump UI树) │ ── import atomx ──────────────┘
│  ├── Analyzer (元素分类/命名)      │
│  └── CodeGenerator (Jinja2渲染)   │ ── 生成 ──→ pages/xxx_page.py
│                                  │ ── 生成 ──→ models/xxx_models.py
└──────────────────────────────────┘
```

---

## 四、平台驱动层设计

### 4.1 BaseDriver 抽象基类

```python
# atomx/driver/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseDriver(ABC):
    """平台驱动抽象基类，定义统一接口契约"""

    @abstractmethod
    def connect(self, serial: str = "", **kwargs) -> "BaseDriver":
        """连接设备"""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        ...

    @abstractmethod
    def dump_hierarchy(self) -> str:
        """获取当前 UI 树 (XML/JSON 格式)"""
        ...

    @abstractmethod
    def click(self, x: int, y: int) -> None:
        """坐标点击"""
        ...

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        """滑动"""
        ...

    @abstractmethod
    def input_text(self, text: str) -> None:
        """输入文本"""
        ...

    @abstractmethod
    def screenshot(self) -> bytes:
        """截图，返回图片字节流"""
        ...

    @abstractmethod
    def start_app(self, package: str, activity: str = "") -> None:
        """启动应用"""
        ...

    @abstractmethod
    def stop_app(self, package: str) -> None:
        """停止应用"""
        ...

    @abstractmethod
    def press_key(self, key: str) -> None:
        """按键 (home/back/power 等)"""
        ...

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        ...

    # 以下为可选能力，子类按需实现
    def screen_record(self, **kwargs) -> str:
        """录屏"""
        raise NotImplementedError(f"{self.__class__.__name__} 不支持录屏")

    def install_app(self, path: str) -> None:
        """安装应用"""
        raise NotImplementedError(f"{self.__class__.__name__} 不支持安装应用")
```

### 4.2 AndroidDriver (基于 uiautomator2 方案)

**核心思路**：借鉴 uiautomator2 的直连 RPC 方案，在设备上运行 UiAutomator HTTP 服务，Python 端直接 HTTP 调用，不走 Appium Server 中转。

```python
# atomx/driver/android/driver.py
import adbutils
from atomx.driver.base import BaseDriver
from atomx.driver.android.transport import HttpTransport
from atomx.driver.android.installer import AutoInstaller

class AndroidDriver(BaseDriver):
    """Android 驱动 — 直连 RPC，毫秒级响应"""

    def __init__(self):
        self._transport: Optional[HttpTransport] = None
        self._device: Optional[adbutils.AdbDevice] = None
        self._installer = AutoInstaller()

    def connect(self, serial: str = "", **kwargs) -> "AndroidDriver":
        if not serial:
            devices = adbutils.adb.device_list()
            if not devices:
                raise RuntimeError("未检测到 Android 设备")
            self._device = devices[0]
        else:
            self._device = adbutils.adb.device(serial=serial)

        # 自动检测并推送 uiautomator 服务到设备
        self._installer.ensure_ready(self._device)

        # 建立到设备端 HTTP RPC 服务的连接
        local_port = self._installer.forward_port(self._device)
        self._transport = HttpTransport(f"http://127.0.0.1:{local_port}")
        return self

    def dump_hierarchy(self) -> str:
        # 直接调用设备端 UiAutomator 的 dumpHierarchy 接口
        return self._transport.jsonrpc_call("dumpHierarchy")

    def click(self, x: int, y: int) -> None:
        self._transport.jsonrpc_call("click", x, y)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        self._transport.jsonrpc_call("swipe", x1, y1, x2, y2, int(duration * 200))

    def input_text(self, text: str) -> None:
        self._transport.jsonrpc_call("setText", text)

    def screenshot(self) -> bytes:
        # 优先用 minicap 高速截图，降级走 adb screencap
        return self._transport.jsonrpc_call("takeScreenshot", return_bytes=True)

    def start_app(self, package: str, activity: str = "") -> None:
        if activity:
            self._device.shell(f"am start -n {package}/{activity}")
        else:
            self._device.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

    def stop_app(self, package: str) -> None:
        self._device.shell(f"am force-stop {package}")

    def press_key(self, key: str) -> None:
        key_map = {"home": 3, "back": 4, "menu": 82, "power": 26}
        self._transport.jsonrpc_call("pressKey", key_map.get(key, key))

    def get_device_info(self) -> dict:
        return self._transport.jsonrpc_call("deviceInfo")

    def screen_record(self, **kwargs) -> str:
        # 使用 adb screenrecord 或设备端录制
        ...
```

**优势**：直连 RPC 无中转，元素检测到点击毫秒级。

### 4.3 IOSDriver (基于 WDA 方案)

**核心思路**：借鉴 facebook-wda 的轻量方案，通过 WebDriverAgent 与 iOS 设备通信，支持 USB 直连。

```python
# atomx/driver/ios/driver.py
from atomx.driver.base import BaseDriver
from atomx.driver.ios.usb_client import USBClient

class IOSDriver(BaseDriver):
    """iOS 驱动 — 基于 WebDriverAgent"""

    def __init__(self):
        self._client: Optional["USBClient"] = None

    def connect(self, serial: str = "", **kwargs) -> "IOSDriver":
        # serial 对应 iOS 设备的 UDID
        # USB 直连通过 usbmuxd，无需 iproxy 端口转发
        self._client = USBClient(serial or None, port=8100)
        self._client.wait_ready(timeout=120)
        return self

    def dump_hierarchy(self) -> str:
        # WDA 返回的 UI 树为 XML 或 accessible JSON
        return self._client.source()

    def click(self, x: int, y: int) -> None:
        self._client.tap(x, y)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        self._client.swipe(x1, y1, x2, y2, duration)

    def input_text(self, text: str) -> None:
        # 使用 WDA 的 set_value 或系统输入法
        self._client.set_text(text)

    def screenshot(self) -> bytes:
        return self._client.screenshot_as_png()

    def start_app(self, package: str, activity: str = "") -> None:
        # package 对应 bundle_id
        self._client.session(package).activate()

    def stop_app(self, package: str) -> None:
        self._client.session(package).deactivate()

    def press_key(self, key: str) -> None:
        if key == "home":
            self._client.home()
        elif key == "volume_up":
            self._client.volume_up()
        elif key == "volume_down":
            self._client.volume_down()

    def get_device_info(self) -> dict:
        info = self._client.status()
        info.update(self._client.device_info())
        return info

    def screen_record(self, **kwargs) -> str:
        # WDA 支持 start/preset recording
        return self._client.start_recording(**kwargs)
```

### 4.4 HarmonyDriver (基于 hdc + UiTest)

**核心思路**：HarmonyOS 提供 `hdc`（HarmonyOS Device Connector，类似 adb）和 `UiTest` 框架。通过 hdc 命令调用设备端 UiTest 能力，实现 UI 自动化。

```python
# atomx/driver/harmony/driver.py
import subprocess
import json
from atomx.driver.base import BaseDriver
from atomx.driver.harmony.hdc import HdcClient

class HarmonyDriver(BaseDriver):
    """鸿蒙驱动 — 基于 hdc + UiTest"""

    HARMONY_UITEST_BUNDLE = "com.ohos.uitest"

    def __init__(self):
        self._hdc: Optional[HdcClient] = None
        self._session_id: Optional[str] = None

    def connect(self, serial: str = "", **kwargs) -> "HarmonyDriver":
        self._hdc = HdcClient(serial)
        # 确认设备连接
        info = self._hdc.shell("param get const.ohos.boot.hardware.version")
        if not info:
            raise RuntimeError("未检测到鸿蒙设备")

        # 启动 UiTest 服务
        self._hdc.shell(f"aa start -a ui_test -b {self.HARMONY_UITEST_BUNDLE}")
        return self

    def dump_hierarchy(self) -> str:
        # 方式1: uitest dumpHierarchy (优先)
        result = self._hdc.shell("uitest dumpHierarchy")
        if result:
            return self._normalize_to_xml(json.loads(result))
        # 方式2(备选): accessibility dumpTree
        result = self._hdc.shell("accessibility dumpTree --json")
        if result:
            return self._normalize_to_xml(json.loads(result))
        raise NotImplementedError("无法获取鸿蒙 UI 树, 请使用 ImageEngine 图像识别")

    def click(self, x: int, y: int) -> None:
        # 优先 uitest, 降级 input 命令
        try:
            self._hdc.shell(f"uitest click {x} {y}")
        except Exception:
            self._hdc.shell(f"input tap {x} {y}")

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        speed = int(1000 / max(duration, 0.1))
        self._hdc.shell(f"uitest swipe {x1} {y1} {x2} {y2} {speed}")

    def input_text(self, text: str) -> None:
        # 鸿蒙输入法注入
        self._hdc.shell(f"uitest inputText '{text}'")

    def screenshot(self) -> bytes:
        # hdc shell snapshot
        tmp_path = "/data/local/tmp/atomx_screenshot.png"
        self._hdc.shell(f"snapshot -f {tmp_path}")
        return self._hdc.pull_bytes(tmp_path)

    def start_app(self, package: str, activity: str = "") -> None:
        # 鸿蒙 ability 启动
        if activity:
            self._hdc.shell(f"aa start -a {activity} -b {package}")
        else:
            self._hdc.shell(f"aa start -b {package}")

    def stop_app(self, package: str) -> None:
        self._hdc.shell(f"aa force-stop {package}")

    def press_key(self, key: str) -> None:
        key_map = {
            "home": "uitest pressKey Home",
            "back": "uitest pressKey Back",
            "power": "uitest pressKey Power",
        }
        cmd = key_map.get(key)
        if cmd:
            self._hdc.shell(cmd)

    def get_device_info(self) -> dict:
        return {
            "model": self._hdc.shell("param get const.product.model").strip(),
            "brand": self._hdc.shell("param get const.product.brand").strip(),
            "version": self._hdc.shell("param get const.ohos.fullname").strip(),
            "sdk": self._hdc.shell("param get const.ohos.apiversion").strip(),
        }

    def _normalize_to_xml(self, json_tree: dict) -> str:
        """将鸿蒙 ArkUI 组件树 JSON 转为统一 XML 格式"""
        from lxml import etree
        root = etree.Element("hierarchy")
        self._build_xml_node(json_tree, root)
        return etree.tostring(root, encoding="unicode")

    def _build_xml_node(self, node: dict, parent):
        """递归构建 XML 节点"""
        from lxml import etree
        el = etree.SubElement(parent, node.get("type", "node"))
        for key, val in node.items():
            if key == "children":
                for child in val:
                    self._build_xml_node(child, el)
            else:
                el.set(key, str(val))
```

### 4.5 驱动工厂

驱动工厂负责把 `platform` 参数映射到对应的平台客户端，并统一完成连接动作。

```python
# atomx/driver/factory.py
from atomx.driver.base import BaseDriver
from atomx.driver.android.driver import AndroidDriver
from atomx.driver.ios.driver import IOSDriver
from atomx.driver.harmony.driver import HarmonyDriver

class DriverFactory:
    """根据配置自动创建对应平台驱动"""

    _registry = {
        "android": AndroidDriver,
        "ios": IOSDriver,
        "harmony": HarmonyDriver,
    }

    @classmethod
    def create(cls, platform: str, serial: str = "", **kwargs) -> BaseDriver:
        driver_cls = cls._registry.get(platform)
        if not driver_cls:
            raise ValueError(f"不支持的平台: {platform}，支持: {list(cls._registry.keys())}")

        driver = driver_cls()
        return driver.connect(serial=serial, **kwargs)

    @classmethod
    def validate_platform(cls, platform: str) -> str:
        if platform not in cls._registry:
            raise ValueError(f"不支持的平台: {platform}，支持: {list(cls._registry.keys())}")
        return platform
```

#### 4.5.1 平台客户端创建流程

1. 读取平台参数：`android` / `ios` / `harmony`
2. 校验平台合法性
3. 查找驱动类：
   - `AndroidDriver`
   - `IOSDriver`
   - `HarmonyDriver`
4. 实例化驱动对象
5. 调用 `connect(serial=serial, **kwargs)` 完成设备连接
6. 返回统一的 `BaseDriver` 实例给上层 `AtomX`

这样做的目的是：
- 测试代码不关心具体平台实现
- `AtomX.connect()` 只负责编排，不直接写平台分支
- 后续新增平台只需要注册新的 Driver

#### 4.5.2 平台参数来源

测试执行时的平台来源有两种：
- 命令行参数：`pytest --platform android|ios|harmony`
- 配置文件或环境变量：`config/config.yaml`

推荐优先级：
1. 命令行参数
2. 环境变量
3. 全局配置文件默认值

### 4.6 三平台驱动对照

| 能力 | AndroidDriver | IOSDriver | HarmonyDriver |
|---|---|---|---|
| 底层工具 | uiautomator2 (HTTP RPC) | WebDriverAgent (HTTP) | hdc + uitest |
| 通信方式 | 直连 RPC (无 Server) | USB 直连 (usbmuxd) | hdc shell 命令 |
| UI 树格式 | XML (hierarchy) | XML (WDA source) | JSON → XML 转换 |
| 速度 | 极快 (毫秒级) | 快 | 中等 (shell 命令) |
| 截图 | minicap / screencap | WDA screenshot | hdc snapshot |
| 录屏 | adb screenrecord | WDA recording | hdc shell |
| 风险 | 成熟稳定 | 需 Mac+Xcode 部署 | uitest 命令需验证, 有备选方案 |

> **鸿蒙风险提示**：`uitest` 命令可用性需真机验证。备选方案：`input tap/swipe` + `accessibility dumpTree` + ImageEngine 图像识别兜底。

---

## 五、双引擎设计

### 5.1 引擎架构

```
                    ┌───────────────────┐
                    │    统一 Element     │
                    │  (跨平台元素抽象)   │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │                               │
    ┌─────────▼─────────┐         ┌───────────▼───────────┐
    │   ControlEngine    │         │    ImageEngine        │
    │   (UI 树定位)       │         │    (视觉识别)          │
    │                     │         │                       │
    │  • LocatorAdapter  │         │  • Template 匹配       │
    │    统一→平台属性     │         │  • 多尺度匹配          │
    │  • XPath 定位       │         │  • 阈值可调            │
    │  • text/id 定位    │         │  • 多目标匹配          │
    │  • parent/child   │         │                       │
    │  • AND/OR 组合     │         │                       │
    └─────────────────────┘         └───────────────────────┘
```

**设计要点**：借鉴 Airtest 的双引擎理念 — 控件引擎处理标准 UI 元素，图像引擎处理游戏/Canvas/无法获取控件树的场景。两个引擎产出的 Element 对象统一，上层 API 无感切换。

### 5.2 LocatorAdapter (跨平台定位器适配)

```python
# atomx/engine/control/locator_adapter.py
class LocatorAdapter:
    """跨平台定位器适配器 — 统一语义 → 平台属性"""

    ATTR_MAP = {
        "android": {
            "text": "text", "id": "resource-id", "desc": "content-desc",
            "class": "class", "accessibility": "resource-id",
            "checked": "checked", "enabled": "enabled", "clickable": "clickable",
        },
        "ios": {
            "text": "label", "value": "value", "id": "name",
            "desc": "help", "class": "type", "accessibility": "name",
            "enabled": "enabled", "visible": "visible",
        },
        "harmony": {
            "text": "text", "id": "id", "desc": "description",
            "class": "type", "accessibility": "accessibilityId",
            "enabled": "enabled", "checked": "checked",
        },
    }

    # 统一语义 class 值 → 各平台原始 class 值
    CLASS_VALUE_MAP = {
        "android": {
            "input": "EditText", "textarea": "EditText",
            "checkbox": "CheckBox", "radio": "RadioButton",
            "button": "Button", "text": "TextView",
            "spinner": "Spinner", "list": "RecyclerView",
            "list_item": "RecyclerView",
        },
        "ios": {
            "input": "TextField", "textarea": "TextView",
            "checkbox": "Switch", "radio": "RadioButton",
            "button": "Button", "text": "StaticText",
            "spinner": "Picker", "list": "CollectionView",
            "list_item": "Cell",
        },
        "harmony": {
            "input": "TextInput", "textarea": "TextInput",
            "checkbox": "Toggle", "radio": "Radio",
            "button": "Button", "text": "Text",
            "spinner": "Select", "list": "List",
            "list_item": "ListItem",
        },
    }

    def __init__(self, platform: str):
        self._platform = platform
        self._mapping = self.ATTR_MAP.get(platform, self.ATTR_MAP["android"])
        self._class_map = self.CLASS_VALUE_MAP.get(platform, self.CLASS_VALUE_MAP["android"])

    def to_xpath(self, locator) -> str:
        """统一定位器 → 平台 XPath

        对 class 属性做双重翻译:
          1. 属性名: class → class (Android) / type (iOS/Harmony)
          2. 属性值: checkbox → CheckBox (Android) / Switch (iOS) / Toggle (Harmony)
        """
        if isinstance(locator, str):
            attr = self._mapping["text"]
            return f'//*[@{attr}="{locator}"]'
        if isinstance(locator, dict):
            conditions = []
            for key, val in locator.items():
                attr = self._mapping.get(key, key)
                if key == "class":
                    # class 值翻译: 统一语义 → 平台原始值
                    val = self._class_map.get(val, val)
                conditions.append(f'@{attr}="{val}"')
            return f'//*[{" and ".join(conditions)}]'
        return locator  # 已是 XPath 字符串

    def to_platform_attr(self, attr: str) -> str:
        return self._mapping.get(attr, attr)
```

**跨平台定位示例**：

```python
# 同一行代码, 三平台自动适配
app.find({"id": "username"})
# Android: //*[@resource-id="username"]
# iOS:      //*[@name="username"]
# Harmony:  //*[@id="username"]

app.find("登录")
# Android: //*[@text="登录"]
# iOS:      //*[@label="登录"]
# Harmony:  //*[@text="登录"]

app.find({"text": "搜索", "class": "button"})
# Android: //*[@text="搜索" and @class="Button"]
# iOS:      //*[@label="搜索" and @type="Button"]
# Harmony:  //*[@text="搜索" and @type="Button"]

app.find({"text": "记住我", "class": "checkbox"})
# Android: //*[@text="记住我" and @class="CheckBox"]
# iOS:      //*[@label="记住我" and @type="Switch"]
# Harmony:  //*[@text="记住我" and @type="Toggle"]

# 列表模板化定位 (一份代码, 三平台通用)
# Page Object 中: {"text": "{item_name}", "class": "checkbox"}
# Android 运行时: //*[@text="项目A" and @class="CheckBox"]
# iOS 运行时:      //*[@label="项目A" and @type="Switch"]
# Harmony 运行时:  //*[@text="项目A" and @type="Toggle"]
```

### 5.3 ControlEngine (控件引擎)

```python
# atomx/engine/control/engine.py
from lxml import etree
from atomx.engine.control.element import Element
from atomx.engine.control.locator_adapter import LocatorAdapter

class ControlEngine:
    """控件引擎 — 基于 UI 树 (XML) 的元素定位"""

    def __init__(self, driver):
        self._driver = driver
        self._platform = self._detect_platform(driver)
        self._adapter = LocatorAdapter(self._platform)
        self._cached_hierarchy = None

    def find(self, locator) -> Element:
        """根据定位器查找元素，返回统一 Element"""
        root = self._get_hierarchy_root()
        xpath = self._adapter.to_xpath(locator)
        matches = root.xpath(xpath)
        if not matches:
            raise ElementNotFoundError(f"未找到元素: {locator} (XPath: {xpath})")
        return Element(node=matches[0], driver=self._driver, engine=self)

    def find_all(self, locator) -> list:
        """查找所有匹配元素"""
        root = self._get_hierarchy_root()
        xpath = self._adapter.to_xpath(locator)
        matches = root.xpath(xpath)
        return [Element(node=m, driver=self._driver, engine=self) for m in matches]

    def exists(self, locator) -> bool:
        """元素是否存在（不抛异常）"""
        try:
            self.find(locator)
            return True
        except ElementNotFoundError:
            return False

    def _get_hierarchy_root(self):
        """获取 UI 树根节点 (带缓存, 每次 find 刷新)"""
        xml = self._driver.dump_hierarchy()
        self._cached_hierarchy = etree.fromstring(xml.encode("utf-8"))
        return self._cached_hierarchy

    def _detect_platform(self, driver) -> str:
        """识别驱动平台类型, 保证统一 locator 适配"""
        name = driver.__class__.__name__.lower()
        if "android" in name:
            return "android"
        if "ios" in name:
            return "ios"
        if "harmony" in name:
            return "harmony"
        return "android"  # 默认回退, 便于单测桩对象
```

### 5.4 ImageEngine (图像引擎)

```python
# atomx/engine/image/engine.py
import cv2
import numpy as np

class ImageEngine:
    """图像引擎 — 基于 OpenCV 的视觉识别"""

    def __init__(self, driver, threshold: float = 0.7):
        self._driver = driver
        self._threshold = threshold

    def find(self, template_path: str, threshold: float = None) -> "ImageElement":
        """在当前屏幕中查找模板图片"""
        screen_bytes = self._driver.screenshot()
        screen = cv2.imdecode(np.frombuffer(screen_bytes, np.uint8), cv2.IMREAD_COLOR)
        template = cv2.imread(template_path)
        if template is None:
            raise FileNotFoundError(f"模板图片不存在: {template_path}")

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        thr = threshold or self._threshold
        if max_val < thr:
            raise ElementNotFoundError(
                f"图像未匹配 (相似度 {max_val:.3f} < 阈值 {thr})"
            )

        h, w = template.shape[:2]
        center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        return ImageElement(center=center, rect=(*max_loc, w, h),
                          confidence=max_val, template=template_path)

    def exists(self, template_path: str, threshold: float = None) -> bool:
        """图像是否存在"""
        try:
            self.find(template_path, threshold)
            return True
        except ElementNotFoundError:
            return False
```

**使用方式**（统一前缀 `image:` 区分图像定位）：

```python
app.find("image:submit_btn.png").tap()
app.wait.until_image_present("image:success_page.png", timeout=15)
app.assert_.image_exists("image:success_banner.png")
```

### 5.5 统一 Element

```python
# atomx/engine/control/element.py
class Element:
    """跨平台统一元素抽象 — 控件引擎和图像引擎产出统一"""

    def __init__(self, node=None, driver=None, engine=None,
                 center=None, rect=None, confidence=None):
        self._node = node        # lxml 节点 (控件引擎)
        self._driver = driver
        self._engine = engine
        self._center = center     # 中心坐标 (图像引擎)
        self._rect = rect
        self._confidence = confidence

    # --- 属性 ---
    @property
    def text(self) -> str:
        if self._node is not None:
            return self._node.get("text", "")
        return ""

    @property
    def resource_id(self) -> str:
        return self._node.get("resource-id", "") if self._node else ""

    @property
    def bounds(self) -> tuple:
        """返回 (x, y, width, height) — 跨平台解析"""
        if self._rect:
            return self._rect
        if not self._node:
            return (0, 0, 0, 0)
        import json
        import re

        # iOS WDA: JSON 格式 {"x":0,"y":0,"width":100,"height":50}
        rect_str = self._node.get("rect", "")
        if rect_str:
            try:
                rect = json.loads(rect_str)
                return (rect["x"], rect["y"], rect["width"], rect["height"])
            except (json.JSONDecodeError, KeyError):
                pass

        # HarmonyOS: 可能为 JSON dict {"x":0,"y":0,"width":100,"height":50}
        json_rect = self._node.get("rect", "") or self._node.get("bounds", "")
        if json_rect.startswith("{"):
            try:
                rect = json.loads(json_rect)
                return (rect["x"], rect["y"], rect["width"], rect["height"])
            except (json.JSONDecodeError, KeyError):
                pass

        # Android: "[x1,y1][x2,y2]" 格式
        bounds_str = self._node.get("bounds", "")
        if bounds_str:
            nums = re.findall(r'\d+', bounds_str)
            if len(nums) >= 4:
                x1, y1, x2, y2 = map(int, nums[:4])
                return (x1, y1, x2 - x1, y2 - y1)

        # iOS 旧格式: frame 属性
        frame_str = self._node.get("frame", "")
        if frame_str:
            nums = re.findall(r'-?\d+', frame_str)
            if len(nums) >= 4:
                return tuple(int(n) for n in nums[:4])

        return (0, 0, 0, 0)

    @property
    def center(self) -> tuple:
        if self._center:
            return self._center
        x, y, w, h = self.bounds
        return (x + w // 2, y + h // 2)

    @property
    def is_displayed(self) -> bool:
        bounds = self.bounds
        return bounds[2] > 0 and bounds[3] > 0

    @property
    def is_enabled(self) -> bool:
        if self._node is not None:
            return self._node.get("enabled", "true") == "true"
        return True

    def get_attribute(self, attr: str) -> str:
        if self._node is not None:
            return self._node.get(attr, "")
        return ""

    def find(self, locator):
        """在当前元素下查找子元素"""
        if self._node is None:
            raise RuntimeError("仅控件引擎元素支持子元素查找")
        from atomx.engine.control.locator_adapter import LocatorAdapter
        adapter = self._engine._adapter
        xpath = adapter.to_xpath(locator)
        # 相对查找: 在当前节点下搜索
        matches = self._node.xpath(f".{xpath}")
        if not matches:
            raise ElementNotFoundError(f"未找到子元素: {locator}")
        return Element(node=matches[0], driver=self._driver, engine=self._engine)

    # --- 操作 (链式 API) ---
    def tap(self) -> "Element":
        """点击元素"""
        x, y = self.center
        self._driver.click(x, y)
        return self

    def long_press(self, duration: float = 2.0) -> "Element":
        x, y = self.center
        self._driver.click(x, y)  # 长按通过多次点击或 driver 原生支持
        return self

    def input_text(self, text: str) -> "Element":
        self.tap()  # 先聚焦
        self._driver.input_text(text)
        return self

    def clear(self) -> "Element":
        self.tap()
        self._driver.input_text("")
        return self

    def get_text(self) -> str:
        return self.text
```

---

## 六、API 层 — Facade 设计

### 6.1 AtomX 主入口

```python
# atomx/api.py
import allure
from atomx.driver.factory import DriverFactory
from atomx.engine.control.engine import ControlEngine
from atomx.engine.image.engine import ImageEngine
from atomx.actions.wait import SmartWait
from atomx.actions.assert_ import AssertionActions
from atomx.actions.recovery import SessionRecovery
from atomx.infra.logger import Logger
from atomx.plugin.manager import PluginManager

class AtomX:
    """
    AtomX — 统一 API 入口 (Facade)

    用法:
        from atomx import AtomX

        app = AtomX()
        app.connect(platform="android")
        app.start_app("com.example.app")
        app.find("登录").tap()
        app.find({"id": "username"}).input_text("admin")
        app.find({"id": "password"}).input_text("123456")
        app.find("确认").tap()
        app.assert_.exists("登录成功")
        app.disconnect()
    """

    def __init__(self):
        self._driver = None
        self._control = None
        self._image = None
        self._platform = ""
        self._serial = ""
        self._logger = Logger()
        self._recovery = SessionRecovery(self)
        self._plugins = PluginManager()
        self.wait = None
        self.assert_ = None

    # === 连接管理 ===
    def connect(self, platform: str, serial: str = "", **kwargs) -> "AtomX":
        """连接设备"""
        self._platform = platform
        self._serial = serial
        self._logger.info(f"连接 {platform} 设备: {serial or 'auto'}")
        self._driver = DriverFactory.create(platform, serial, **kwargs)
        self._control = ControlEngine(self._driver)
        self._image = ImageEngine(self._driver)
        self.wait = SmartWait(self._control, self._image)
        self.assert_ = AssertionActions(self._control, self._image, self._driver)
        self._plugins.call_connect(self, platform=platform, serial=serial)
        return self

    def disconnect(self) -> None:
        """断开连接"""
        if self._plugins:
            self._plugins.call_teardown()
        if self._driver:
            self._driver.disconnect()
            self._logger.info("设备已断开")

    @property
    def driver(self):
        return self._driver

    @property
    def logger(self):
        return self._logger

    # === 元素查找 (统一入口, 自动选择引擎) ===
    def find(self, locator):
        """
        查找元素 — 统一入口, 自动区分控件/图像

        支持多种 locator 格式:
          app.find("登录")                     # 纯文本 (LocatorAdapter 自动翻译)
          app.find({"id": "username"})         # 多条件字典
          app.find('//*[@text="登录"]')        # XPath
          app.find("image:login_btn.png")     # 图像识别 (image: 前缀)
          app.find({"accessibility": "submit"}) # accessibility ID
        """
        # 图像识别: "image:" 前缀
        if isinstance(locator, str) and locator.startswith("image:"):
            return self._image.find(locator[6:])
        # 控件引擎 (含错误恢复)
        return self._recovery.execute_with_recovery(self._control.find, locator)

    def find_all(self, locator) -> list:
        """查找所有匹配元素"""
        if isinstance(locator, str) and locator.startswith("image:"):
            return [self._image.find(locator[6:])]
        return self._control.find_all(locator)

    def exists(self, locator) -> bool:
        """判断元素是否存在"""
        try:
            self.find(locator)
            return True
        except Exception:
            return False

    # === 快捷操作 ===
    @allure.step("点击坐标: ({x}, {y})")
    def tap(self, x: int, y: int) -> "AtomX":
        """坐标点击"""
        self._driver.click(x, y)
        return self

    @allure.step("滑动: {direction}")
    def swipe(self, direction: str = "up") -> "AtomX":
        """方向滑动 (up/down/left/right)"""
        info = self._driver.get_device_info()
        w = info.get("displayWidth", 1080)
        h = info.get("displayHeight", 1920)
        cx, cy = w // 2, h // 2
        offsets = {
            "up": (0, h // 3),
            "down": (0, -h // 3),
            "left": (w // 3, 0),
            "right": (-w // 3, 0),
        }
        dx, dy = offsets.get(direction, (0, -h // 3))
        self._driver.swipe(cx, cy, cx + dx, cy + dy)
        return self

    @allure.step("启动应用: {package}")
    def start_app(self, package: str, activity: str = "") -> "AtomX":
        """启动应用"""
        self._driver.start_app(package, activity)
        return self

    @allure.step("停止应用: {package}")
    def stop_app(self, package: str) -> "AtomX":
        """停止应用"""
        self._driver.stop_app(package)
        return self

    @allure.step("按键: {key}")
    def press_key(self, key: str) -> "AtomX":
        """按键 (home/back/power)"""
        self._driver.press_key(key)
        return self

    @allure.step("截图")
    def screenshot(self) -> bytes:
        """截图"""
        return self._driver.screenshot()

    @property
    def info(self) -> dict:
        """设备信息"""
        return self._driver.get_device_info()

    # === 上下文管理器 ===
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()
```

### 6.2 使用示例

```python
from atomx import AtomX

# 简单用法 — 登录测试
app = AtomX()
app.connect(platform="android")
app.start_app("com.example.app", ".MainActivity")
app.find("登录").tap()
app.find({"id": "username"}).input_text("admin")
app.find({"id": "password"}).input_text("123456")
app.find("确认").tap()
app.assert_.exists("登录成功")
app.disconnect()

# 图像识别 — 游戏/Canvas 测试
app = AtomX()
app.connect(platform="android")
app.start_app("com.game.example")
app.find("image:start_btn.png").tap()
app.swipe("up")

# iOS
app = AtomX()
app.connect(platform="ios", serial="auto-udid")
app.start_app("com.example.app")  # bundle_id
app.find({"accessibility": "login_button"}).tap()

# 鸿蒙
app = AtomX()
app.connect(platform="harmony")
app.start_app("com.example.app", "EntryAbility")
app.find("登录").tap()
app.press_key("back")

# 上下文管理器 — 自动断开
with AtomX() as app:
    app.connect(platform="android")
    app.find("搜索").tap()
    app.find({"id": "search_box"}).input_text("hello")
    app.find("搜索").tap()
```

---

## 七、Page Object + Models 分层架构

> 参考 `web_quality_ui_playwright` 项目，按页面生成 Page Object 类和 Models 数据类。

### 7.1 设计思路

| 层 | 职责 | 示例 |
|---|---|---|
| **BasePage** | 封装通用底层操作 (tap/fill/assert/wait/scroll) | `self.tap(locator)`, `self.assert_visible(locator)` |
| **XxxPage** | 元素定位器(常量) + 操作方法 + 断言方法 + 列表/表格操作 | `LOGIN_BUTTON = "登录"`, `def login(self, user, pwd)` |
| **XxxModels** | dataclass 数据契约，连接 YAML 和 Page | `@dataclass class LoginPageData` |

### 7.2 BasePage 设计

```python
# pages/base_page.py
import allure
from typing import Union

class BasePage:
    """App 页面基类 — 封装跨平台通用操作"""

    def __init__(self, app):
        self.app = app
        self._logger = app.logger
        self._page_name = self.__class__.__name__.replace("_", " ")

    @property
    def page_name(self): return self._page_name
    @property
    def logger(self): return self._logger

    # ========== 导航 ==========
    @allure.step("启动应用: {package}")
    def open(self, package: str = "", activity: str = ""):
        pkg = package or getattr(self, "PACKAGE", "")
        act = activity or getattr(self, "ACTIVITY", "")
        self.app.start_app(pkg, act)

    @allure.step("等待页面加载完成")
    def wait_for_page_loaded(self):
        raise NotImplementedError("子类必须实现 wait_for_page_loaded")

    # ========== 元素定位 ==========
    def find(self, locator): return self.app.find(locator)
    def find_all(self, locator): return self.app.find_all(locator)
    def exists(self, locator) -> bool: return self.app.exists(locator)

    # ========== 点击/手势 ==========
    @allure.step("点击: {locator}")
    def tap(self, locator): self.app.find(locator).tap()

    @allure.step("长按: {locator}")
    def long_press(self, locator, duration: float = 2.0):
        self.app.find(locator).long_press(duration)

    @allure.step("滑动: {direction}")
    def swipe(self, direction="up"): self.app.swipe(direction)

    @allure.step("滚动到元素: {locator}")
    def scroll_to_element(self, locator):
        for _ in range(10):
            if self.app.exists(locator): return
            self.app.swipe("up")
        raise ElementNotFoundError(f"滚动后未找到: {locator}")

    # ========== 表单操作 ==========
    @allure.step("输入文本: {text}")
    def fill(self, locator, text: str): self.app.find(locator).input_text(text)

    @allure.step("清空: {locator}")
    def clear(self, locator): self.app.find(locator).clear()

    def get_text(self, locator) -> str: return self.app.find(locator).text
    def get_attribute(self, locator, attr: str) -> str: return self.app.find(locator).get_attribute(attr)
    def is_checked(self, locator) -> bool: return self.app.find(locator).get_attribute("checked") == "true"
    def is_enabled(self, locator) -> bool: return self.app.find(locator).is_enabled

    # ========== 等待 ==========
    @allure.step("等待可见: {locator}")
    def wait_for_visible(self, locator, timeout=10): self.app.wait.until_visible(locator, timeout)

    @allure.step("等待消失: {locator}")
    def wait_for_gone(self, locator, timeout=10): self.app.wait.until_gone(locator, timeout)

    @allure.step("等待文本: {text}")
    def wait_for_text(self, text, timeout=10):
        self.app.wait.until(lambda: self.app.exists(text), timeout)

    # ========== 断言 ==========
    @allure.step("断言存在: {locator}")
    def assert_visible(self, locator): self.app.assert_.exists(locator)

    @allure.step("断言不存在: {locator}")
    def assert_not_visible(self, locator): self.app.assert_.not_exists(locator)

    @allure.step("断言文本: {locator} == '{expected}'")
    def assert_text_equals(self, locator, expected): self.app.assert_.text_equals(locator, expected)

    @allure.step("断言文本包含: {locator} 包含 '{substring}'")
    def assert_text_contains(self, locator, substring): self.app.assert_.text_contains(locator, substring)

    @allure.step("断言数量: {locator} == {count}")
    def assert_count(self, locator, count: int):
        actual = len(self.app.find_all(locator))
        if actual != count:
            raise AssertionError(f"数量: 期望 {count}, 实际 {actual}")

    # ========== 截图 ==========
    @allure.step("截图")
    def screenshot(self, name="screenshot"):
        allure.attach(self.app.driver.screenshot(), name=name,
                      attachment_type=allure.attachment_type.PNG)
```

### 7.3 页面 PO 示例 — 登录页

```python
# pages/login/login_page.py
import allure
from pages.base_page import BasePage

class LoginPage(BasePage):
    """登录页面对象"""

    # ========== 1. 元素定位器 ==========
    PACKAGE = "com.example.app"
    ACTIVITY = ".MainActivity"

    USERNAME_INPUT = {"id": "username"}
    PASSWORD_INPUT = {"id": "password"}
    LOGIN_BUTTON = "登录"
    REMEMBER_SWITCH = {"desc": "记住我"}
    ERROR_MESSAGE = {"id": "error_msg"}

    # ========== 2. 导航 ==========
    @allure.step("打开登录页面")
    def open(self):
        super().open()
        self.wait_for_page_loaded()

    # ========== 3. 等待 ==========
    @allure.step("等待登录页加载完成")
    def wait_for_page_loaded(self):
        self.wait_for_visible(self.USERNAME_INPUT)
        self.wait_for_visible(self.PASSWORD_INPUT)
        self.wait_for_visible(self.LOGIN_BUTTON)

    # ========== 4. 操作 ==========
    @allure.step("输入用户名: {username}")
    def fill_username(self, username: str):
        self.fill(self.USERNAME_INPUT, username)
        return self

    @allure.step("输入密码")
    def fill_password(self, password: str):
        self.fill(self.PASSWORD_INPUT, password)
        return self

    @allure.step("点击登录")
    def click_login(self):
        self.tap(self.LOGIN_BUTTON)
        return self

    @allure.step("执行登录: {username}")
    def login(self, username: str, password: str, remember: bool = False):
        self.fill_username(username)
        self.fill_password(password)
        if remember: self.tap(self.REMEMBER_SWITCH)
        self.click_login()
        return self

    # ========== 5. 断言 ==========
    @allure.step("验证登录成功")
    def should_login_success(self):
        self.assert_visible("首页")

    @allure.step("验证登录失败: {expected_error}")
    def should_show_error(self, expected_error: str):
        self.assert_visible(self.ERROR_MESSAGE)
        self.assert_text_contains(self.ERROR_MESSAGE, expected_error)
```

### 7.4 列表/表格页面 PO 示例

```python
# pages/order/order_list_page.py
import allure
from pages.base_page import BasePage

class OrderListPage(BasePage):
    """订单列表页 — 包含列表/表格操作"""

    PACKAGE = "com.example.app"
    ACTIVITY = ".OrderListActivity"

    # ========== 元素定位器 ==========
    LIST_CONTAINER = {"class": "list"}
    LIST_ITEM = {"class": "list_item"}

    SEARCH_INPUT = {"id": "search_input"}
    SEARCH_BUTTON = {"id": "search_btn"}

    ITEM_TITLE = {"id": "item_title"}
    ITEM_STATUS = {"id": "item_status"}
    ITEM_DETAIL_BUTTON = {"text": "详情"}
    ITEM_EDIT_BUTTON = {"text": "编辑"}
    ITEM_DELETE_BUTTON = {"text": "删除"}

    LOAD_MORE_TEXT = "加载更多"
    NO_MORE_TEXT = "没有更多了"

    # ========== 等待 ==========
    @allure.step("等待订单列表加载")
    def wait_for_page_loaded(self):
        self.wait_for_visible(self.LIST_CONTAINER)

    # ========== 列表操作 ==========
    @allure.step("获取行数")
    def get_row_count(self) -> int:
        return len(self.find_all(self.LIST_ITEM))

    @allure.step("获取第 {row_index} 行")
    def get_row(self, row_index: int = 0):
        items = self.find_all(self.LIST_ITEM)
        if row_index >= len(items):
            raise IndexError(f"行索引超出: {row_index} (共 {len(items)} 行)")
        return items[row_index]

    @allure.step("获取第 {row_index} 行标题")
    def get_row_title(self, row_index: int = 0) -> str:
        return self.get_row(row_index).find(self.ITEM_TITLE).text

    @allure.step("获取第 {row_index} 行状态")
    def get_row_status(self, row_index: int = 0) -> str:
        return self.get_row(row_index).find(self.ITEM_STATUS).text

    @allure.step("点击第 {row_index} 行的{action}")
    def click_row_action(self, row_index: int, action: str):
        action_map = {
            "detail": self.ITEM_DETAIL_BUTTON,
            "edit": self.ITEM_EDIT_BUTTON,
            "delete": self.ITEM_DELETE_BUTTON,
        }
        locator = action_map.get(action)
        if not locator: raise ValueError(f"不支持的操作: {action}")
        self.get_row(row_index).find(locator).tap()

    @allure.step("按标题查找行")
    def find_row_by_title(self, title: str) -> int:
        count = self.get_row_count()
        for i in range(count):
            if self.get_row_title(i) == title: return i
        return -1

    @allure.step("滚动到行")
    def scroll_to_row(self, row_index: int):
        count = self.get_row_count()
        while row_index >= count:
            self.swipe("up")
            count = self.get_row_count()

    @allure.step("下拉刷新")
    def pull_refresh(self):
        self.app.swipe("down")
        self.wait_for_page_loaded()

    # ========== 搜索 ==========
    @allure.step("搜索: {keyword}")
    def search(self, keyword: str):
        self.fill(self.SEARCH_INPUT, keyword)
        self.tap(self.SEARCH_BUTTON)
        self.wait_for_page_loaded()

    # ========== 断言 ==========
    @allure.step("验证行数: {count}")
    def assert_row_count(self, count: int):
        self.assert_count(self.LIST_ITEM, count)
```

### 7.5 Models 数据模型

```python
# models/base_models.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class ExtractRule:
    """数据提取规则"""
    source: str = "element"
    locator: str = ""
    attribute: str = "text"

@dataclass
class AssertionRule:
    """断言规则"""
    assert_method: str = ''
    locator: str = ''
    expected_text: str = ''

@dataclass
class StepData:
    """步骤数据"""
    action: str
    input: dict = field(default_factory=dict)
    expected: Optional[dict] = None
    extract: Optional[Dict[str, ExtractRule]] = None

@dataclass
class CaseData:
    """用例数据"""
    case: str
    steps: list = field(default_factory=list)
```

```python
# models/login/login_models.py
from dataclasses import dataclass, field
from typing import List
from models.base_models import AssertionRule

@dataclass
class LoginPageData:
    """登录页 - 数据模型 (连接 YAML 和 Page)"""
    username: str = ""
    password: str = ""
    remember: bool = False
    expected_url: str = ''
    expected_methods: List[AssertionRule] = field(default_factory=list)
    expected_error: str = ''
    alert_elem: str = ''
```

---

## 八、代码生成器

> 代码生成器的完整设计已拆分到独立文档：[`docs/code_generator.md`](./code_generator.md)。

### 8.1 总体目标

代码生成器负责把 UI 探测结果转换成可维护的 Page Object、Models、测试流程和配置，而不是单纯生成静态元素定位器。

核心能力包括：

- UI 树扫描与元素归一化
- 单页面多步骤 / 多页面多步骤建模
- 自动生成配置，并支持人工配置覆盖
- Page Object、Models、Test Flow、Data Provider 统一生成
- Android / iOS / HarmonyOS 三平台兼容

### 8.2 推荐链路

```text
UI Tree
  -> Detector
  -> Analyzer
  -> FlowBuilder
  -> ConfigResolver
  -> CodeGenerator
  -> pages/ + models/ + testcases/ + data/
```

### 8.3 平台兼容策略

生成器只输出统一语义，不暴露平台原始 class：

- `button`
- `input`
- `checkbox`
- `radio`
- `text`
- `list`
- `list_item`
- `dialog`

运行时再由 LocatorAdapter 翻译为各平台属性。

### 8.4 详细方案

完整实现细节、配置模型、人工配置闭环、生成策略、CLI 设计和分阶段落地建议见：

[`docs/code_generator.md`](./code_generator.md)

---

## 九、CLI 命令行工具

框架提供两个 CLI 入口：

1. **pytest 命令** (运行测试用例，由 pytest 原生提供)
2. **atomx CLI** (生成器、设备管理、UI 检查器)

```python
# atomx/cli/main.py
import click

@click.group()
@click.version_option()
def cli():
    """AtomX — 跨平台 App 自动化测试框架 CLI"""
    pass

@cli.command()
@click.option("--platform", "-p", type=click.Choice(["android", "ios", "harmony"]), required=True)
@click.option("--class-name", "-n", default="AutoPage", help="生成的 Page 类名")
@click.option("--module", "-m", required=True, help="页面模块名 (如 login)")
@click.option("--package", "-a", required=True, help="应用包名 / Bundle ID")
@click.option("--serial", "-s", default="", help="设备序列号")
@click.option("--output", "-o", type=click.Path(), default=".", help="输出目录")
def generate(platform, class_name, module, package, serial, output):
    """自动生成页面对象 (调用 script.generator)

    atomx generate --platform android -a com.example.app -m login
    atomx generate --platform ios -a com.example.app -m login
    atomx generate --platform harmony -a com.example.app -m login
    """
    import subprocess
    subprocess.run([
        "python", "-m", "script.generator.cli",
        "--platform", platform,
        "--package", package,
        "--module", module,
        "--output", output,
        "--serial", serial,
    ], check=True)

@cli.command()
def devices():
    """列出所有已连接设备 (三平台)

    atomx devices
    """
    import subprocess

    # Android
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n")[1:]:
            if "device" in line:
                serial = line.split()[0]
                click.echo(f"  [Android]  {serial}")
    except FileNotFoundError:
        click.echo("  [Android]  未安装 adb")

    # iOS
    try:
        result = subprocess.run(["tidevice", "list"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                click.echo(f"  [iOS]      {line.strip()}")
    except FileNotFoundError:
        click.echo("  [iOS]      未安装 tidevice")

    # HarmonyOS
    try:
        result = subprocess.run(["hdc", "list targets"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                click.echo(f"  [Harmony]  {line.strip()}")
    except FileNotFoundError:
        click.echo("  [Harmony]  未安装 hdc")

if __name__ == "__main__":
    cli()
```

> 运行测试用例通过 pytest + Allure，不需要额外 CLI。代码生成通过 `atomx generate` 调用 `script.generator.cli`，实现三平台一键生成。

---

## 十、多设备并行测试

多设备并行基于 `pytest-xdist` 实现，每个 worker 连接一台设备，独立执行用例：

```python
# examples/multi_device.py
import subprocess
from atomx.api import AtomX


def discover_devices():
    """发现三平台所有已连接设备"""
    devices = []

    # Android
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n")[1:]:
            if "device" in line:
                devices.append({"platform": "android", "serial": line.split()[0]})
    except FileNotFoundError:
        pass

    # iOS
    try:
        result = subprocess.run(["tidevice", "list"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                devices.append({"platform": "ios", "serial": line.strip()})
    except FileNotFoundError:
        pass

    # HarmonyOS
    try:
        result = subprocess.run(["hdc", "list targets"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                devices.append({"platform": "harmony", "serial": line.strip()})
    except FileNotFoundError:
        pass

    return devices


def run_test_on_device(platform: str, serial: str):
    """在单台设备上执行测试"""
    app = AtomX()
    app.connect(platform=platform, serial=serial)
    try:
        app.start_app("com.example.app")
        app.find("搜索").tap()
        app.find({"id": "search_box"}).input_text("test")
        app.find("搜索").tap()
        app.assert_.exists("搜索结果")
        return {"device": serial, "result": "pass"}
    except Exception as e:
        app.screen.screenshot(f"failure_{serial}.png")
        return {"device": serial, "result": "fail", "error": str(e)}
    finally:
        app.disconnect()


def run_parallel():
    """多设备并行测试"""
    devices = discover_devices()
    if not devices:
        print("未检测到设备")
        return

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = [
            executor.submit(run_test_on_device, d["platform"], d["serial"])
            for d in devices
        ]
        results = [f.result() for f in futures]

    for r in results:
        print(f"  {r['device']}: {r['result']}")


# 通过 pytest-xdist 实现并行 (更推荐的方式)
# pytest testcases/ -n <设备数> --platform android --alluredir=./allure-results
```

> **推荐方式**：使用 `pytest -n <workers>` 并行执行。每个 pytest-xdist worker 独立启动，通过 `--platform` 和 `--serial` 参数连接对应设备。详见第十一章 Allure 集成。

---

## 十一、与 pytest + Allure 深度集成

### 11.1 整体方案

```
┌──────────────────────────────────────────────────────────┐
│                    pytest 测试用例                        │
│  test_login.py  /  test_search.py  /  test_cart.py      │
├──────────────────────────────────────────────────────────┤
│                 conftest.py (Fixture 体系)                │
│  app fixture  /  device fixture  /  page fixture         │
│  Allure Hooks (attach screenshot, step, environment)     │
├──────────────────────────────────────────────────────────┤
│              atomx.plugin.pytest (内置插件)               │
│  AtomXPlugin: 自动截图 / 操作步骤记录 / 失败重跑 /       │
│  Allure 装饰器自动注入 / 多设备并行分发                   │
├──────────────────────────────────────────────────────────┤
│                    Allure 报告                            │
│  Epics > Features > Stories 三层结构                     │
│  每步骤截图 + UI 树附件 + 视频 + 日志                    │
│  Trend 趋势图 + 历史对比                                 │
└──────────────────────────────────────────────────────────┘
```

**设计思路**：开发一个 `atomx.plugin.pytest` 内置插件，在 pytest 收集、执行、报告三个阶段注入 Allure 钩子，让用户只写测试逻辑，框架自动完成截图、步骤记录、附件上传、报告美化。

### 11.2 Allure 配置文件

```
testcases/
├── allure_properties/             # Allure 环境信息
│   ├── environment.properties     # 环境变量 (展示在报告首页)
│   └── categories.json            # 缺陷分类定义
```

> pytest 配置、conftest.py、pages/、data/ 已在第三章项目目录结构中定义，此处不再重复。

### 11.3 pytest 配置

```ini
# pytest.ini
[pytest]
# 命令行参数
addopts =
    -v
    --reruns=2
    --reruns-delay=2
    --alluredir=./allure-results
    --clean-alluredir
    --allure-label=platform:${platform}
    --allure-label=device:${serial}

# 测试路径
testpaths = testcases

# 标记
markers =
    smoke: 冒烟测试用例
    regression: 回归测试用例
    login: 登录功能
    search: 搜索功能
    cart: 购物车功能
    android: Android 平台
    ios: iOS 平台
    harmony: 鸿蒙平台
    slow: 耗时较长的用例

# Allure 插件
allure_framework_marker = AtomX
```

### 11.4 全局 conftest.py — Fixture + Allure 深度集成

```python
# testcases/conftest.py
import pytest
import allure
import os
from atomx import AtomX

# ==================== 命令行参数 ====================

def pytest_addoption(parser):
    parser.addoption("--platform", action="store", default="android",
                      choices=["android", "ios", "harmony"],
                      help="目标测试平台")
    parser.addoption("--serial", action="store", default="",
                      help="设备序列号 (留空自动选择)")
    parser.addoption("--app-package", action="store", default="",
                      help="被测应用包名")
    parser.addoption("--reruns", action="store", default=0, type=int,
                      help="失败重跑次数")
    parser.addoption("--reruns-delay", action="store", default=2, type=int,
                      help="重跑间隔 (秒)")

# ==================== Allure 环境信息 ====================

@pytest.fixture(scope="session", autouse=True)
def allure_environment(request):
    """将设备信息写入 Allure 环境变量 — 报告首页展示"""
    platform = request.config.getoption("--platform")
    serial = request.config.getoption("--serial")

    # 写入 environment.properties (Allure 首页 "Environment" 栏)
    allure.attach(
        f"Platform={platform}\n"
        f"DeviceSerial={serial or 'auto'}\n"
        f"Python={os.popen('python --version').read().strip()}\n"
        f"AtomX={AtomX.__version__ if hasattr(AtomX, '__version__') else 'dev'}\n"
        f"TestTime={__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        name="environment.properties",
        attachment_type=allure.attachment_type.PROPERTIES,
    )


# ==================== Session 级 Fixture ====================

@pytest.fixture(scope="session")
def device_info(request):
    """Session 级设备信息 — 全程只查询一次"""
    platform = request.config.getoption("--platform")
    serial = request.config.getoption("--serial")
    return {"platform": platform, "serial": serial}


# ==================== Function 级 App Fixture ====================

@pytest.fixture(scope="function")
def app(request, device_info):
    """
    每个测试函数自动创建/销毁 AtomX 实例
    自动关联 Allure: 截图、步骤、附件
    """
    platform = device_info["platform"]
    serial = device_info.get("serial", "")

    # Allure 标记: 平台 + 设备 + 用例名
    allure.dynamic.label("platform", platform)
    allure.dynamic.label("device", serial)
    allure.dynamic.title(request.node.name.replace("test_", "").replace("_", " ").title())

    # Allure Epic/Feature 层级 (从 markers 读取)
    for marker in request.node.iter_markers():
        if hasattr(allure, marker.name):
            getattr(allure.dynamic, f"label")(
                marker.name, marker.name
            )

    app = AtomX()

    # ====== Allure Hook: 操作步骤自动截图 ======
    # 注册 AtomX 内部操作回调，每次 find/tap/input 自动记录到 Allure step
    _register_allure_hooks(app)

    with allure.step(f"连接 {platform} 设备: {serial or 'auto'}"):
        app.connect(platform=platform, serial=serial)

    yield app

    # ====== Teardown: 失败自动截图 + UI 树附件 ======
    if request.node.rep_call and request.node.rep_call.failed:
        _attach_failure_screenshot(app, request)

    with allure.step("断开设备连接"):
        app.disconnect()


# ==================== Hooks: 测试结果监听 ====================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """监听测试结果 — 失败时自动截图并附加到 Allure"""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


# ==================== 辅助函数 ====================

def _register_allure_hooks(app: AtomX):
    """注册 Allure 操作回调 — 自动将 AtomX 操作记录为 Allure 步骤"""
    original_find = app.find

    @allure.step("查找元素: {locator}")
    def _allure_find(locator):
        return original_find(locator)

    app.find = _allure_find

    # 对 Element.tap / input_text 也自动记录
    from atomx.engine.control.element import Element
    original_tap = Element.tap
    original_input = Element.input_text

    @allure.step("点击元素")
    def _allure_tap(self, timeout=10):
        return original_tap(self, timeout=timeout)

    @allure.step("输入文本: {text}")
    def _allure_input(self, text):
        return original_input(self, text)

    Element.tap = _allure_tap
    Element.input_text = _allure_input


def _attach_failure_screenshot(app: AtomX, request):
    """失败时截图 + UI 树 + 日志附加到 Allure"""
    import traceback

    # 1. 截图
    try:
        screenshot = app.driver.screenshot()
        allure.attach(
            screenshot,
            name="失败截图",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception:
        pass

    # 2. UI 树 (XML)
    try:
        hierarchy = app.driver.dump_hierarchy()
        allure.attach(
            hierarchy,
            name="UI层级树",
            attachment_type=allure.attachment_type.XML,
        )
    except Exception:
        pass

    # 3. 异常信息
    allure.attach(
        traceback.format_exc(),
        name="异常堆栈",
        attachment_type=allure.attachment_type.TEXT,
    )

    # 4. 设备日志 (logcat / syslog)
    try:
        if app.driver.__class__.__name__ == "AndroidDriver":
            logs = app.driver._device.shell("logcat -d -t 200")
        elif app.driver.__class__.__name__ == "IOSDriver":
            logs = app.driver._client.appium_log()
        else:
            logs = "日志获取不支持"
        allure.attach(
            logs,
            name="设备日志",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass
```

#### 11.4.1 App fixture 生命周期说明

`app` fixture 负责把平台参数转成实际可执行的 App 客户端实例，并管理它的完整生命周期。

生命周期分为 5 步：

1. **读取平台与设备信息**
   - `platform = device_info["platform"]`
   - `serial = device_info.get("serial", "")`

2. **创建统一入口实例**
   - `app = AtomX()`
   - 这一步不直接创建 Driver，只创建 Facade

3. **注入平台与设备参数并连接**
   - `app.connect(platform=platform, serial=serial)`
   - 内部通过 `DriverFactory.create(platform, serial)` 创建具体平台客户端

4. **注册报告与诊断钩子**
   - Allure step
   - 自动截图
   - 失败附件
   - UI 树附件

5. **yield 给测试用例后销毁**
   - 用例执行期间共用同一个 `AtomX` 实例
   - teardown 时执行 `app.disconnect()`

#### 11.4.2 session 与 function 的作用域分工

- `device_info`：`session` 级
  - 一次 pytest 运行只读取一次平台和 serial
  - 适合做报告环境信息、全局调试信息

- `app`：`function` 级
  - 每个测试函数独立创建和销毁
  - 避免上一个用例的设备状态污染下一个用例

这样设计的目的是：
- 保证隔离性
- 便于 Allure 按用例粒度收集结果
- 方便后续扩展并行执行和失败重试

### 11.5 Page Object 层 — Allure 装饰器集成

> Page Object 基类和页面类已在第七章定义，此处仅展示如何在页面类中集成 Allure 装饰器。

```python
# pages/base_page.py (追加 Allure 元数据自动注入)
class BasePage:
    # 子类定义
    page_name: str = ""
    feature: str = ""
    story: str = ""

    def __init__(self, app):
        self.app = app
        self._logger = app.logger
        self._page_name = self.__class__.__name__.replace("_", " ")
        # Allure 动态设置层级
        if self.feature:
            allure.dynamic.feature(self.feature)
        if self.story:
            allure.dynamic.story(self.story)
        if self.page_name:
            allure.dynamic.label("page", self.page_name)


# pages/login/login_page.py (追加 Allure feature/story)
@allure.feature("登录功能")
@allure.story("用户登录")
class LoginPage(BasePage):
    page_name = "登录页"
    # ... (元素定位器、操作方法同第七章)
    # wait_until_loaded → wait_for_page_loaded


# pages/profile/profile_page.py (追加 Allure feature/story)
@allure.feature("首页功能")
@allure.story("首页操作")
class HomePage(BasePage):
    page_name = "首页"

    @allure.step("点击搜索入口")
    def go_search(self):
        self.app.find("搜索").tap()
        return self

    @allure.step("退出登录")
    def logout(self):
        self.app.find("我的").tap()
        self.app.find("退出登录").tap()
        self.app.find("确认").tap()
        return self

    def wait_for_page_loaded(self):
        self.app.wait.until(lambda: self.app.exists("首页"), timeout=15)
```

### 11.6 数据驱动测试 — pytest parametrize + Allure

```python
# data/login_data.yaml
- username: "admin"
  password: "123456"
  expected: "首页"
  desc: "正常登录"

- username: ""
  password: "123456"
  expected: "用户名不能为空"
  desc: "空用户名"

- username: "admin"
  password: "wrong"
  expected: "密码错误"
  desc: "错误密码"

- username: "admin"
  password: ""
  expected: "密码不能为空"
  desc: "空密码"
```

```python
# testcases/login/test_login.py
import pytest
import allure
import yaml
from pages.login.login_page import LoginPage
from pages.profile.profile_page import HomePage

# 加载测试数据
with open("data/login_data.yaml", encoding="utf-8") as f:
    LOGIN_CASES = yaml.safe_load(f)


@allure.epic("AtomX 框架示例")
@allure.feature("登录功能")
class TestLogin:

    @pytest.mark.smoke
    @pytest.mark.login
    @allure.story("正常登录流程")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("登录成功: {desc}")
    @pytest.mark.parametrize(
        "case",
        LOGIN_CASES,
        ids=[c["desc"] for c in LOGIN_CASES]
    )
    def test_login(self, app, case):
        """数据驱动登录测试 — 每条用例自动截图 + 步骤"""
        with allure.step("启动应用"):
            app.start_app("com.example.app", ".MainActivity")

        with allure.step("等待登录页加载"):
            login_page = LoginPage(app).wait_until_loaded()

        with allure.step(f"执行登录: {case['username']}"):
            login_page.login(case["username"], case["password"])

        with allure.step(f"验证结果: 期望出现 '{case['expected']}'"):
            app.assert_.exists(case["expected"])

    @allure.story("登录后导航")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("登录后跳转首页并退出")
    def test_login_and_logout(self, app):
        """测试登录 → 首页 → 退出完整流程"""
        with allure.step("登录"):
            login_page = LoginPage(app).wait_until_loaded()
            home_page = login_page.navigate(HomePage)

        with allure.step("验证首页加载"):
            home_page.wait_until_loaded()
            app.assert_.exists("首页")

        with allure.step("退出登录"):
            home_page.logout()
            app.assert_.exists("登录")
```

### 11.7 AtomX pytest 插件 — atomx.plugin.pytest

```python
# atomx/plugin/pytest_plugin.py
"""
AtomX pytest 插件 — 自动注册, pip install 后无需手动配置

功能:
1. 自动截图: 每个操作步骤截图并附加到 Allure
2. 失败重跑: 配合 pytest-rerunfailures, 重跑时清理上次 Allure 步骤
3. 多设备并行: 配合 pytest-xdist, 按 device 分发用例
4. 视频录屏: 测试期间自动录屏, 结束后附加到 Allure
5. 性能指标: 采集每步耗时, 附加到 Allure
6. UI 树快照: 每个关键步骤自动 dump UI 树
"""
import pytest
import allure
import time
import functools
from atomx.infra.logger import logger


# ==================== 1. 操作步骤自动截图 ====================

class ScreenshotContext:
    """上下文管理器: 在 Allure step 内自动截图"""
    _screenshot_enabled = True
    _screenshot_interval = 1.0  # 最小截图间隔, 避免过多

    @classmethod
    def attach_screenshot(cls, app, step_name: str = ""):
        if not cls._screenshot_enabled:
            return
        try:
            screenshot = app.driver.screenshot()
            allure.attach(
                screenshot,
                name=f"{step_name or 'step'}_{time.time():.0f}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass


# ==================== 2. 录屏管理 ====================

class VideoRecorder:
    """测试期间录屏 — 结束后附加到 Allure"""
    _recordings = {}  # test_node_id -> video_path

    @classmethod
    def start(cls, app, node_id: str):
        try:
            path = app.driver.screen_record_start()
            cls._recordings[node_id] = path
        except Exception:
            pass

    @classmethod
    def stop_and_attach(cls, app, node_id: str):
        if node_id not in cls._recordings:
            return
        try:
            video_bytes = app.driver.screen_record_stop()
            allure.attach(
                video_bytes,
                name="录屏",
                attachment_type=allure.attachment_type.MP4,
            )
        except Exception:
            pass


# ==================== 3. 插件入口 ====================

def pytest_configure(config):
    """pytest 配置阶段 — 注册标记"""
    config.addinivalue_line(
        "markers", "android: Android 平台用例"
    )
    config.addinivalue_line(
        "markers", "ios: iOS 平台用例"
    )
    config.addinivalue_line(
        "markers", "harmony: 鸿蒙平台用例"
    )
    config.addinivalue_line(
        "markers", "smoke: 冒烟测试"
    )
    config.addinivalue_line(
        "markers", "regression: 回归测试"
    )


def pytest_collection_modifyitems(config, items):
    """收集后修改: 平台过滤主要通过 -m 标记完成"""
    # 这里不再根据平台目录自动打标
    pass


def pytest_runtest_setup(item):
    """每个用例执行前 — 启动录屏"""
    # 录屏在 app fixture 内启动更合适, 这里做前置检查
    pass


def pytest_runtest_teardown(item, nextitem):
    """每个用例执行后 — 停止录屏并附加"""
    app = getattr(item, "_atomx_app", None)
    if app:
        VideoRecorder.stop_and_attach(app, item.nodeid)


# ==================== 4. Allure 步骤自动截图装饰器 ====================

def atomx_step(name: str = "", screenshot: bool = True):
    """
    AtomX Allure 步骤装饰器 — 自动截图 + 耗时记录

    用法:
        @atomx_step("执行登录", screenshot=True)
        def login(app, user, pwd):
            app.find("登录").tap()
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        @allure.step(name or func.__name__)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start

            # 自动截图
            if screenshot:
                # 从 args 中找 app 对象
                app = None
                for arg in args:
                    if hasattr(arg, "find") and hasattr(arg, "driver"):
                        app = arg
                        break
                if app:
                    ScreenshotContext.attach_screenshot(app, name or func.__name__)

            # 附加耗时信息
            allure.attach(
                f"耗时: {duration:.3f}s",
                name="性能指标",
                attachment_type=allure.attachment_type.TEXT,
            )
            return result
        return wrapper
    return decorator


# ==================== 5. 多设备并行分发 ====================

def pytest_addoption(parser):
    """
    自定义 CLI 参数:
    --serial: 指定单台设备序列号
    --parallel: 多设备并行时设备序列号列表 (逗号分隔)
    """
    parser.addoption("--serial", action="store", default=None, help="设备序列号")
    parser.addoption("--parallel", action="store", default=None, help="多设备并行序列号列表")


def pytest_configure(config):
    """记录设备参数供 app fixture 使用"""
    config._device_serial = config.getoption("--serial")
    config._parallel_devices = config.getoption("--parallel")
```

### 11.8 Allure 配置文件

```json
# testcases/allure_properties/categories.json
[
  {
    "name": "元素未找到",
    "matchedStatuses": ["broken"],
    "messageRegex": ".*ElementNotFoundError.*"
  },
  {
    "name": "断言失败",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*AssertionError.*"
  },
  {
    "name": "设备连接问题",
    "matchedStatuses": ["broken"],
    "messageRegex": ".*RuntimeError.*设备.*"
  },
  {
    "name": "超时",
    "matchedStatuses": ["broken"],
    "messageRegex": ".*Timeout.*"
  }
]
```

```properties
# testcases/allure_properties/environment.properties
Framework=AtomX
Python=3.12
Platform=Android 14
Device=Pixel 7 Pro
AppVersion=2.1.0
TestEnvironment=staging
```

### 11.9 测试用例编写 — 完整示例

```python
# testcases/search/test_search.py
import pytest
import allure
from pages.login.login_page import LoginPage
from pages.profile.profile_page import HomePage
from atomx.plugin.pytest_plugin import atomx_step


@allure.epic("AtomX 框架示例")
@allure.feature("搜索功能")
class TestSearch:

    @allure.story("关键词搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("搜索关键词: {keyword}")
    @pytest.mark.smoke
    @pytest.mark.search
    @pytest.mark.parametrize("keyword", [
        "手机", "电脑", "耳机", "键盘", "鼠标"
    ])
    def test_search_keyword(self, app, keyword):
        """参数化搜索测试 — Allure 自动为每个参数生成独立报告条目"""

        # --- 前置: 登录 ---
        with allure.step("前置: 登录"):
            app.start_app("com.example.app", ".MainActivity")
            LoginPage(app).wait_until_loaded().login("admin", "123456")
            HomePage(app).wait_until_loaded()

        # --- 搜索操作 ---
        with allure.step("点击搜索入口"):
            app.find("搜索").tap()

        @atomx_step("输入搜索词", screenshot=True)
        def _input_keyword():
            app.find({"id": "search_box"}).input_text(keyword)

        _input_keyword()

        with allure.step("点击搜索按钮"):
            app.find("搜索").tap()

        with allure.step("验证搜索结果"):
            app.assert_.exists("搜索结果")

        # --- 附加搜索结果截图 ---
        screenshot = app.driver.screenshot()
        allure.attach(
            screenshot,
            name=f"搜索结果_{keyword}",
            attachment_type=allure.attachment_type.PNG,
        )

    @allure.story("搜索历史")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("搜索历史记录展示")
    @pytest.mark.regression
    def test_search_history(self, app):
        """搜索历史功能测试"""

        with allure.step("执行多次搜索"):
            keywords = ["手机", "电脑"]
            for kw in keywords:
                app.find("搜索").tap()
                app.find({"id": "search_box"}).input_text(kw)
                app.find("搜索").tap()
                app.keys.press("back")

        with allure.step("打开搜索页, 检查历史"):
            app.find("搜索").tap()
            for kw in keywords:
                app.assert_.exists(kw)
```

### 11.10 命令行运行

```bash
# ===== 基本运行 =====
# 跑登录功能通用用例
pytest testcases/login/test_login.py --platform android --alluredir=./allure-results --clean-alluredir
pytest testcases/login/test_login.py --platform ios --serial "auto-udid" --alluredir=./allure-results
pytest testcases/login/test_login.py --platform harmony --alluredir=./allure-results

# 跑指定标记
pytest testcases/login/ -m "smoke and login" --platform android --alluredir=./allure-results

# 跑平台特化用例
pytest -m ios --platform ios --alluredir=./allure-results
pytest -m android --platform android --alluredir=./allure-results
pytest -m harmony --platform harmony --alluredir=./allure-results

# ===== 失败重跑 =====
pytest testcases/login/ --platform android \
    --reruns=2 --reruns-delay=2 \
    --alluredir=./allure-results

# ===== 多线程并行 =====
pytest testcases/ --platform android -n 3 \
    --alluredir=./allure-results

# ===== 生成 Allure 报告 =====
# 安装 allure 命令行: https://allurereport.org/install/

# 生成 HTML 报告并自动打开浏览器
allure serve ./allure-results

# 生成静态 HTML 报告到指定目录
allure generate ./allure-results -o ./allure-report --clean

# 打开已生成的报告
allure open ./allure-report

# ===== 查看 Trend 趋势图 (需配合 CI) =====
# 保留历史 allure-results, 多次运行后自动生成趋势图
allure generate ./allure-results -o ./allure-report --clean
```

### 11.11 Allure 报告效果示意

```
Allure Report
├── 📊 Overview (首页)
│   ├── 总用例数 / 通过率 / 失败数 / 跳过数
│   ├── 趋势图 (Trend) — 多次运行历史
│   ├── Severity 分布饼图 (Blocker/Critical/Normal/Minor/Trivial)
│   └── Duration 耗时分布
│
├── 📁 Suites (测试套件)
│   ├── login/test_login.py
│   │   ├── TestLogin
│   │   │   ├── test_login[正常登录]          ✅ PASS  (含 8 个步骤 + 5 张截图)
│   │   │   ├── test_login[空用户名]           ✅ PASS
│   │   │   ├── test_login[错误密码]           ❌ FAIL  (含失败截图 + UI树 + 日志)
│   │   │   └── test_login[空密码]            ✅ PASS
│   │   └── TestLogin
│   │       └── test_login_and_logout         ✅ PASS  (含录屏)
│   └── search/test_search.py
│       └── TestSearch
│           ├── test_search_keyword[手机]      ✅ PASS
│           ├── test_search_keyword[电脑]      ✅ PASS
│           └── ...
│
├── 🏷️ Categories (缺陷分类)
│   ├── 元素未找到              (3 个)
│   ├── 断言失败                 (1 个)
│   └── 超时                    (2 个)
│
├── ⏱️ Timeline (时间线)
│   └── 按时间轴展示每个用例的执行时间
│
├── 🧩 Behaviors (行为树)
│   ├── Epic: AtomX 框架示例
│   │   ├── Feature: 登录功能
│   │   │   ├── Story: 正常登录流程     (4 条)
│   │   │   └── Story: 登录后导航       (1 条)
│   │   └── Feature: 搜索功能
│   │       ├── Story: 关键词搜索       (5 条)
│   │       └── Story: 搜索历史         (1 条)
│
└── 🔧 Environment (环境信息)
    ├── Platform=Android 14
    ├── Device=Pixel 7 Pro
    ├── Framework=AtomX
    └── AppVersion=2.1.0
```

### 11.12 单个用例的 Allure 报告详情

```
test_login[错误密码]
─────────────────────────
❌ FAIL  | Duration: 12.34s  | Severity: BLOCKER

📋 步骤详情:
  1. [allure.step] 连接 android 设备: emulator-5554         ✅ (0.52s)
  2. [allure.step] 启动应用                                   ✅ (1.23s)
  3. [allure.step] 等待登录页加载                              ✅ (2.10s)
  4. [allure.step] 执行登录: admin                            ✅ (3.45s)
     ├─ [allure.step] 查找元素: {"id": "username"}           ✅
     ├─ [allure.step] 输入文本: admin                        ✅
     ├─ [allure.step] 查找元素: {"id": "password"}           ✅
     ├─ [allure.step] 输入文本: 123456                       ✅
     ├─ [allure.step] 查找元素: 登录                         ✅
     └─ [allure.step] 点击元素                               ✅
  5. [allure.step] 验证结果: 期望出现 '密码错误'              ❌
     └─ ElementNotFoundError: 未找到匹配元素: 密码错误

📎 附件:
  ├─ 📸 失败截图 (PNG)
  ├─ 📄 UI层级树 (XML)
  ├─ 📝 异常堆栈 (TEXT)
  ├─ 📋 设备日志 (TEXT)
  ├─ 🎬 录屏 (MP4)
  └─ 📊 性能指标 (TEXT)

🏷️ 标签:
  platform=android  device=emulator-5554  page=登录页
  severity=BLOCKER  feature=登录功能  story=正常登录流程
```

### 11.13 CI/CD 集成 (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: AtomX App Automation Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  android-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        device: [emulator-5554]  # 多设备可扩展

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install AtomX
        run: |
          pip install -e .
          pip install pytest allure-pytest pytest-rerunfailures pytest-xdist

      - name: Setup Android Emulator
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          script: |
            pytest testcases/android/ \
              --platform android \
              --alluredir=./allure-results \
              --clean-alluredir \
              --reruns=2 --reruns-delay=2

      - name: Get Allure history
        uses: actions/checkout@v4
        if: always()
        with:
          ref: gh-pages
          path: gh-pages

      - name: Generate Allure Report
        if: always()
        run: |
          allure generate ./allure-results -o ./allure-report --clean
          # 合并历史趋势
          cp -r gh-pages/history ./allure-report/ 2>/dev/null || true
          allure report add-history -o ./allure-report

      - name: Deploy Allure Report to GitHub Pages
        if: always()
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./allure-report
          keep_files: true
```

---

## 十二、三平台特性对照表

| 能力 | Android (uiautomator2) | iOS (WDA) | HarmonyOS (hdc+UiTest) |
|---|---|---|---|
| **UI 树获取** | dumpHierarchy (XML) | source (XML/JSON) | uitest dumpHierarchy (JSON→XML) |
| **元素定位** | XPath / text / resource-id | accessibility / label / predicate | text / accessibilityId / type |
| **点击** | RPC click(x,y) | WDA tap(x,y) | uitest click x y |
| **滑动** | RPC swipe | WDA swipe | uitest swipe |
| **输入文本** | RPC setText | WDA set_value | uitest inputText |
| **按键** | RPC pressKey (keycode) | WDA home/volume | uitest pressKey |
| **截图** | minicap/adb screencap | WDA screenshot | hdc snapshot |
| **录屏** | adb screenrecord | WDA recording | hdc shell snapshot (序列) |
| **安装应用** | adb install | WDA install (有限) | hdc install |
| **启动应用** | am start / monkey | session activate | aa start |
| **图像识别** | OpenCV (全平台通用) | OpenCV (全平台通用) | OpenCV (全平台通用) |
| **连接方式** | USB / adb connect | USB (usbmuxd) / WiFi | USB / hdc tconn |
| **底层通信** | HTTP RPC (设备端服务) | HTTP (WDA 服务) | hdc shell 命令 |

---

## 十三、技术选型总结

| 组件 | 技术选型 | 借鉴来源 | 理由 |
|---|---|---|---|
| Android 驱动 | uiautomator2 RPC 方案 | uiautomator2 | 毫秒级响应，无需 Server |
| iOS 驱动 | WebDriverAgent | facebook-wda | 轻量，USB 直连 |
| 鸿蒙驱动 | hdc + UiTest | 鸿蒙原生 | 唯一可行方案 |
| 图像识别 | OpenCV + Template Matching | Airtest | 成熟稳定 |
| OCR | pytesseract (可选) | Airtest | 无需额外依赖 |
| XML 解析 | lxml | uiautomator2 | 高性能 XPath 1.0 |
| 配置 | YAML / JSON | 常见 Python 配置方案 | 简洁、可读、易扩展 |
| HTML 报告 | Jinja2 模板 | Airtest | 灵活可定制 |
| 测试框架 | pytest 原生集成 | Appium 生态 | CI/CD 友好 |
| 日志 | logging + 彩色格式化 | loguru 风格 | 标准库，零额外依赖 |
| CLI | click | Airtest | 命令行体验好 |
| 包管理 | Poetry (pyproject.toml) | 现代 Python | 锁文件 + 依赖管理 |

---

## 十四、依赖清单

```toml
# pyproject.toml (核心依赖)
[tool.poetry.dependencies]
python = "^3.9"

# 平台通信
adbutils = "^2.0"              # Android ADB 封装
lxml = "^5.0"                  # XML 解析 + XPath
requests = "^2.31"             # HTTP 通信 (Android RPC / WDA)

# 图像引擎
opencv-python = "^4.8"         # 图像识别
Pillow = "^10.0"               # 图片处理
pytesseract = "^0.3.10"        # OCR (可选)

# 框架层
Jinja2 = "^3.1"                # 报告模板 / 代码生成模板
PyYAML = "^6.0"                # YAML 配置 / 测试数据

# CLI
click = "^8.1"                 # 命令行框架

# iOS (可选)
facebook-wda = "^1.0"          # iOS WebDriverAgent 客户端

# 鸿蒙 (可选, 系统自带 hdc 命令行)
# 无额外 Python 依赖, 通过 subprocess 调用 hdc

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-html = "^4.0"
pytest-xdist = "^3.0"          # 并行测试
allure-pytest = "^2.0"         # Allure 报告 (可选)
```

---

## 十五、与竞品框架的最终对比

| 能力 | AtomX (本方案) | Appium | uiautomator2 | Airtest |
|---|---|---|---|---|
| **Android** | 直连 RPC (极快) | Server 中转 (慢) | 直连 RPC (极快) | ADB (中) |
| **iOS** | WDA 直连 (快) | Server 中转 (慢) | 不支持 | WDA (中) |
| **鸿蒙** | hdc + UiTest | 不支持 | 不支持 | 不支持 |
| **图像识别** | 内置 (OpenCV) | 需插件 | 不支持 | 内置 (强) |
| **Page Object** | 内置 + 自动生成 | 需自己封装 | 需自己封装 | 需自己封装 |
| **代码生成器** | 内置 (Jinja2) | 无 | 无 | 无 |
| **配置管理** | YAML / JSON | capabilities | 无 | 无 |
| **报告** | HTML + 截图 | 需插件 | 无 | HTML (强) |
| **IDE** | 无 | Appium Inspector | weditor | AirtestIDE |
| **设计模式** | Facade / Page Object / Models | 无 | 无 | 无 |
| **pytest 集成** | 原生 | 原生 | 需适配 | 需适配 |
| **多设备并行** | pytest-xdist | Selenium Grid | 需自己实现 | 需自己实现 |

---

## 十六、路线图

### Phase 1: MVP (核心可用)
- AndroidDriver (基于 uiautomator2 方案直连)
- ControlEngine + Element + XPath 定位
- AtomX Facade + 基础 Actions
- 基础 HTML 报告
- pytest 集成

### Phase 2: 跨平台 + 双引擎
- IOSDriver (基于 WDA)
- ImageEngine (OpenCV 图像识别)
- Watcher 弹窗监控
- ConfigManager (JSON5 级联配置)
- PageBase + PageObjectGenerator

### Phase 3: 鸿蒙 + 高级特性
- HarmonyDriver (hdc + UiTest)
- Navigator (networkx 图导航)
- DeviceManager (多设备并行)
- CLI 工具 (run / inspect / generate / report)
- UI 检查器 (浏览器版)

### Phase 4: 生态 + 云端
- DeviceFarm 对接 (atxserver2 / STF)
- 云测试平台支持 (BrowserStack 等)
- 脚本录制器
- VLM 智能识别 (LLM 增强)
- AirtestIDE 风格桌面 IDE (可选)

---

## 十七、跨平台用例复用策略

> **优先级：高** — 避免同一功能写三份用例

### 17.1 设计思路

> 测试目录按功能模块划分，不单独按平台建目录。平台特化只在文件命名上体现，平台标签仅用于过滤执行和报告分组。

```
testcases/
├── conftest.py                   # 全局 fixture (app 连接/失败截图/Allure/hooks)
├── login/                        # 登录功能模块
│   ├── test_login.py             # 三平台通用登录流程
│   ├── test_login_ios.py         # iOS 专属功能
│   └── test_login_android.py     # Android 专属功能
├── search/                       # 搜索功能模块
│   ├── test_search.py
│   └── test_search_ios.py
├── order/                        # 订单功能模块
│   ├── test_order_list.py
│   └── test_order_detail.py
└── profile/                      # 个人中心功能模块
    └── test_profile.py
```

### 17.2 功能模块用例写法

```python
# testcases/login/test_login.py
import allure
import pytest

class TestLogin:
    """登录测试 — 三平台通用流程"""

    APP_PACKAGE = "com.example.app"
    APP_ACTIVITY = ".MainActivity"

    LOCATORS = {
        "username_field": {"id": "username"},
        "password_field": {"id": "password"},
        "login_button": "登录",
        "success_text": "首页",
    }

    @allure.feature("登录功能")
    @allure.story("正常登录")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.login
    @pytest.mark.parametrize("username,password,expected,desc", [
        ("admin", "123456", "首页", "正常登录"),
        ("", "123456", "用户名不能为空", "空用户名"),
        ("admin", "wrong", "密码错误", "错误密码"),
    ])
    def test_login(self, app, username, password, expected, desc):
        """三平台共用的登录流程"""
        with allure.step("启动应用"):
            app.start_app(self.APP_PACKAGE, self.APP_ACTIVITY)

        with allure.step("等待登录页加载"):
            app.wait.until(lambda: app.exists(self.LOCATORS["login_button"]), timeout=15)

        with allure.step(f"登录: {username}"):
            app.find(self.LOCATORS["username_field"]).input_text(username)
            app.find(self.LOCATORS["password_field"]).input_text(password)
            app.find(self.LOCATORS["login_button"]).tap()

        with allure.step(f"验证: {expected}"):
            app.assert_.exists(expected)

    @allure.feature("登录功能")
    @allure.story("登录后导航")
    @pytest.mark.login
    def test_login_and_logout(self, app):
        """三平台共用的登录后导航流程"""
        app.start_app(self.APP_PACKAGE, self.APP_ACTIVITY)
        app.wait.until(lambda: app.exists(self.LOCATORS["login_button"]), timeout=15)
        app.find(self.LOCATORS["username_field"]).input_text("admin")
        app.find(self.LOCATORS["password_field"]).input_text("123456")
        app.find(self.LOCATORS["login_button"]).tap()
        app.assert_.exists(self.LOCATORS["success_text"])
        app.find("我的").tap()
        app.find("退出登录").tap()
        app.find("确认").tap()
        app.assert_.exists(self.LOCATORS["login_button"])
```

### 17.3 平台特化用例写法

> 平台特化用例放在同功能模块目录中，文件名后缀标记平台，并配合平台标签。

```python
# testcases/login/test_login_ios.py
import pytest

@pytest.mark.ios
@pytest.mark.login
class TestIOSLogin:
    """iOS 专属登录场景"""

    @pytest.mark.login_ios
    def test_face_id_auth(self, app):
        """iOS 独有: Face ID 授权"""
        app.find("Face ID").tap()
        app.assert_.exists("已验证")
```

```python
# testcases/login/test_login_android.py
import pytest

@pytest.mark.android
@pytest.mark.login
class TestAndroidLogin:
    """Android 专属登录场景"""

    @pytest.mark.login_android
    def test_gesture_password(self, app):
        """Android 独有: 手势密码"""
        app.find("手势密码").tap()
        app.assert_.exists("验证成功")
```

```python
# testcases/search/test_search_ios.py
import pytest

@pytest.mark.ios
@pytest.mark.search
class TestIOSSearch:
    """iOS 专属搜索场景"""

    @pytest.mark.search_ios
    def test_search_history(self, app):
        """iOS 专属搜索历史验证"""
        app.find("搜索").tap()
        app.find("历史记录").tap()
        app.assert_.exists("最近搜索")
```

### 17.4 平台过滤执行

> 平台过滤主要通过 pytest 标记执行，不再依赖平台目录层级。

```python
# testcases/conftest.py
import pytest

def pytest_collection_modifyitems(config, items):
    """未指定平台时保留全部用例；指定 -m 时由 pytest 过滤标记"""
    pass
```

```bash
# 通用用例（三平台都跑）
pytest testcases/login/test_login.py --platform android --alluredir=./allure-results
pytest testcases/login/test_login.py --platform ios     --alluredir=./allure-results
pytest testcases/login/test_login.py --platform harmony --alluredir=./allure-results

# 平台特化用例（只跑对应平台）
pytest -m ios --platform ios --alluredir=./allure-results
pytest -m android --platform android --alluredir=./allure-results
pytest -m harmony --platform harmony --alluredir=./allure-results

# 功能模块 + 平台组合
pytest testcases/login/ -m "login and ios" --platform ios --alluredir=./allure-results
```

---
---
---
---

## 十八、性能监控能力

> **优先级：中** — 移动端测试常需采集性能指标

### 18.1 PerfMonitor 设计

```python
# atomx/infra/perf/monitor.py
import time
import json
import threading
from collections import defaultdict

class PerfMonitor:
    """
    性能监控器 — 采集被测 App 的 CPU/内存/FPS/网络/电量指标

    三平台采集方式:
    - Android: adb shell dumpsys / top / gfxinfo
    - iOS:     WDA performance API / instruments
    - Harmony: hdc shell hidumper / uitest perf
    """

    def __init__(self, driver):
        self._driver = driver
        self._platform = driver.__class__.__name__.lower()
        self._collecting = False
        self._thread = None
        self._data = defaultdict(list)  # metric -> [(timestamp, value), ...]
        self._interval = 2.0  # 采集间隔 (秒)

    # === 采集控制 ===
    def start(self, package: str = "", interval: float = 2.0):
        """启动后台性能采集"""
        self._package = package
        self._interval = interval
        self._collecting = True
        self._data.clear()
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        """停止采集, 返回所有指标数据"""
        self._collecting = False
        if self._thread:
            self._thread.join(timeout=5)
        return dict(self._data)

    # === 后台采集循环 ===
    def _collect_loop(self):
        while self._collecting:
            timestamp = time.time()
            try:
                metrics = self._collect_metrics()
                for key, value in metrics.items():
                    self._data[key].append((timestamp, value))
            except Exception:
                pass
            time.sleep(self._interval)

    def _collect_metrics(self) -> dict:
        """采集当前时刻性能指标 — 按平台分发"""
        if "android" in self._platform:
            return self._collect_android()
        elif "ios" in self._platform:
            return self._collect_ios()
        elif "harmony" in self._platform:
            return self._collect_harmony()
        return {}

    # === Android 采集 ===
    def _collect_android(self) -> dict:
        metrics = {}
        pkg = self._package

        # CPU 使用率
        cpu_output = self._driver._device.shell(f"top -n 1 -b | grep {pkg}")
        # 解析 CPU 百分比
        if cpu_output:
            parts = cpu_output.split()
            if len(parts) >= 9:
                metrics["cpu_percent"] = float(parts[8])

        # 内存 (PSS)
        mem_output = self._driver._device.shell(f"dumpsys meminfo {pkg}")
        if "TOTAL PSS:" in mem_output:
            for line in mem_output.split("\n"):
                if "TOTAL PSS:" in line:
                    metrics["memory_pss_kb"] = int(line.split()[-2])

        # FPS (帧率)
        gfx_output = self._driver._device.shell(f"dumpsys gfxinfo {pkg}")
        if "Total frames rendered" in gfx_output:
            for line in gfx_output.split("\n"):
                if "Total frames rendered" in line:
                    metrics["total_frames"] = int(line.split()[-1])
                    break

        # 电量
        battery_output = self._driver._device.shell("dumpsys battery")
        if "level:" in battery_output:
            for line in battery_output.split("\n"):
                if "level:" in line:
                    metrics["battery_level"] = int(line.split()[-1])
                    break

        # 网络流量
        net_output = self._driver._device.shell(
            f"cat /proc/{pkg}/net/dev"
        )
        # 解析网络流量
        ...

        return metrics

    # === iOS 采集 ===
    def _collect_ios(self) -> dict:
        """iOS 通过 WDA 性能 API 采集"""
        metrics = {}
        try:
            perf = self._driver._client.session().app_performance()
            metrics["cpu_percent"] = perf.get("cpu", 0)
            metrics["memory_mb"] = perf.get("memory", 0)
            metrics["fps"] = perf.get("fps", 0)
        except Exception:
            pass
        return metrics

    # === Harmony 采集 ===
    def _collect_harmony(self) -> dict:
        """鸿蒙通过 hidumper 采集"""
        metrics = {}
        try:
            # CPU
            cpu = self._driver._hdc.shell(
                f"hidumper --zipcpu -pid {self._package}"
            )
            # 内存
            mem = self._driver._hdc.shell(
                f"hidumper --mem {self._package}"
            )
            if mem:
                metrics["memory_kb"] = int(mem.split()[-1])
            # 电量
            batt = self._driver._hdc.shell(
                "hidumper -s battery_manager"
            )
        except Exception:
            pass
        return metrics

    # === Allure 集成 ===
    def attach_to_allure(self, name: str = "性能监控报告"):
        """将性能数据附加到 Allure 报告"""
        import allure
        import json as json_module

        data = self.stop()
        allure.attach(
            json_module.dumps(data, indent=2, ensure_ascii=False),
            name=name,
            attachment_type=allure.attachment_type.JSON,
        )

        # 生成简化 CSV (可用 Excel 打开)
        csv_lines = ["timestamp,metric,value"]
        for metric, points in data.items():
            for ts, val in points:
                csv_lines.append(f"{ts:.1f},{metric},{val}")
        allure.attach(
            "\n".join(csv_lines),
            name=f"{name}_csv",
            attachment_type=allure.attachment_type.CSV,
        )
```

### 18.2 使用示例

```python
# 在 pytest 用例中采集性能
def test_heavy_operation(app):
    from atomx.infra.perf.monitor import PerfMonitor

    monitor = PerfMonitor(app.driver)
    monitor.start(package="com.example.app", interval=2)

    # 执行耗时操作
    app.find("导出数据").tap()
    app.wait.until(lambda: app.exists("导出完成"), timeout=60)

    # 停止采集并附加到 Allure
    monitor.attach_to_allure("数据导出性能报告")

    # 断言性能指标
    data = monitor.stop()
    if "cpu_percent" in data:
        max_cpu = max(v for _, v in data["cpu_percent"])
        app.assert_.greater_than(100, max_cpu, "CPU 峰值超过 100%")
    if "memory_pss_kb" in data:
        max_mem = max(v for _, v in data["memory_pss_kb"])
        app.assert_.greater_than(500000, max_mem, "内存峰值超过 500MB")
```

---

## 十九、测试数据管理策略

> **优先级：中**

### 19.1 数据分层架构

```
data/
├── yaml/                      # 静态测试数据 (人工维护)
│   ├── login_data.yaml
│   ├── search_data.yaml
│   └── env_config.yaml
├── factory/                   # 动态数据工厂 (代码生成)
│   ├── user_factory.py
│   └── order_factory.py
├── api/                       # API 数据提供者 (从后端拉取)
│   └── data_provider.py
└── cleanup/                   # 数据清理脚本
    └── teardown.py
```

### 19.2 数据提供者 (DataProvider)

```python
# atomx/infra/data/provider.py
import yaml
import json
import csv
from pathlib import Path
from typing import Any, List, Dict

class DataProvider:
    """
    统一数据提供者 — 支持多格式数据源

    支持格式:
    - YAML (.yaml/.yml) — 推荐用于结构化测试数据
    - JSON (.json) — 适用于 API mock 数据
    - CSV (.csv) — 适用于大量参数化数据
    - Python 函数 — 动态生成数据 (factory)
    """

    def __init__(self, base_dir: str = "data"):
        self._base_dir = Path(base_dir)

    def load(self, filename: str, key: str = None) -> Any:
        """加载测试数据文件, 自动识别格式"""
        path = self._base_dir / filename
        suffix = path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            data = self._load_yaml(path)
        elif suffix == ".json":
            data = self._load_json(path)
        elif suffix == ".csv":
            data = self._load_csv(path)
        else:
            raise ValueError(f"不支持的数据格式: {suffix}")

        if key and isinstance(data, dict):
            return data[key]
        return data

    def _load_yaml(self, path) -> Any:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_json(self, path) -> Any:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_csv(self, path) -> List[Dict]:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    # === 动态数据工厂 ===
    @staticmethod
    def factory(func):
        """装饰器: 将函数标记为数据工厂"""
        func._is_data_factory = True
        return func

    def generate(self, factory_name: str, count: int = 1, **kwargs) -> list:
        """调用数据工厂生成测试数据"""
        module = __import__(f"tests.data.factory.{factory_name}", fromlist=["generate"])
        if hasattr(module, "generate"):
            return [module.generate(**kwargs) for _ in range(count)]
        raise ValueError(f"数据工厂 {factory_name} 未找到 generate 函数")

    # === API 数据拉取 ===
    def from_api(self, endpoint: str, params: dict = None) -> Any:
        """从后端 API 拉取测试数据"""
        import requests
        resp = requests.get(endpoint, params=params, timeout=10)
        return resp.json()
```

### 19.3 pytest 数据驱动集成

```python
# testcases/conftest.py (追加数据 fixture)
import pytest
from atomx.infra.data.provider import DataProvider

@pytest.fixture(scope="session")
def data_provider():
    """Session 级数据提供者"""
    return DataProvider()

@pytest.fixture(scope="function")
def test_data(request, data_provider):
    """Function 级测试数据 — 用例标记 @pytest.mark.data("login_data.yaml") 自动加载"""
    marker = request.node.get_closest_marker("data")
    if marker:
        filename = marker.args[0]
        key = marker.kwargs.get("key")
        return data_provider.load(filename, key)
    return None

def pytest_collection_modifyitems(config, items):
    """注册 data 标记"""
    config.addinivalue_line("markers", "data(filename, key=None): 测试数据文件")
```

### 19.4 使用示例

```python
# YAML 数据文件 (data/yaml/login_data.yaml)
- username: "admin"
  password: "123456"
  expected: "首页"
  desc: "正常登录"

- username: ""
  password: "123456"
  expected: "用户名不能为空"
  desc: "空用户名"

# 数据工厂 (data/factory/user_factory.py)
import random
import string

def generate(**kwargs):
    """动态生成随机用户数据"""
    random_name = ''.join(random.choices(string.ascii_lowercase, k=8))
    return {
        "username": f"user_{random_name}",
        "password": "Test@1234",
        "email": f"{random_name}@test.com",
        **kwargs,  # 允许覆盖默认值
    }

# 测试用例中使用
@pytest.mark.data("yaml/login_data.yaml")
@pytest.mark.parametrize("case", DataProvider().load("yaml/login_data.yaml"))
def test_login_data_driven(app, case):
    app.find({"id": "username"}).input_text(case["username"])
    app.find({"id": "password"}).input_text(case["password"])
    app.find("登录").tap()
    app.assert_.exists(case["expected"])

def test_register_random_user(app, data_provider):
    """使用数据工厂生成随机用户"""
    users = data_provider.generate("user_factory", count=1)
    user = users[0]
    app.find({"id": "username"}).input_text(user["username"])
    app.find({"id": "email"}).input_text(user["email"])
    app.find("注册").tap()
    app.assert_.exists("注册成功")
```

---
## 二十、插件机制

> **优先级：低** — 但对框架可扩展性至关重要

### 20.1 插件架构

```
┌─────────────────────────────────────────┐
│              AtomX 核心                  │
│  (Driver / Engine / Actions / Facade)   │
├─────────────────────────────────────────┤
│           插件注册点 (Hook)              │
│  • on_connect   连接设备后               │
│  • on_find      查找元素时               │
│  • on_action    执行操作时               │
│  • on_assert    断言时                   │
│  • on_error     异常发生时               │
│  • on_report    生成报告时               │
├─────────────────────────────────────────┤
│              插件实现                     │
│  • allure_plugin      Allure 集成        │
│  • perf_plugin        性能监控            │
│  • screenshot_plugin  自动截图           │
│  • watcher_plugin     弹窗监控           │
│  • custom_plugin      用户自定义         │
└─────────────────────────────────────────┘
```

### 20.2 插件基类

```python
# atomx/plugin/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional

class AtomXPlugin(ABC):
    """AtomX 插件基类 — 用户通过继承此类实现自定义插件"""

    name: str = "base"
    priority: int = 0  # 执行优先级 (数字越小越先执行)

    def on_connect(self, app, **kwargs):
        """连接设备后回调"""
        pass

    def on_disconnect(self, app):
        """断开设备前回调"""
        pass

    def on_find(self, app, locator, result: Any = None):
        """查找元素后回调 — 可修改 result"""
        return result

    def on_action(self, app, action: str, args: tuple, kwargs: dict,
                  result: Any = None):
        """执行操作后回调 — 可修改 result"""
        return result

    def on_assert(self, app, assertion: str, passed: bool, **kwargs):
        """断言后回调"""
        pass

    def on_error(self, app, error: Exception, context: dict):
        """异常发生时回调 — 可决定是否恢复"""
        pass

    def on_report(self, app, report_data: dict):
        """生成报告时回调 — 可附加数据"""
        return report_data

    def teardown(self):
        """框架关闭时清理"""
        pass
```

### 20.3 插件管理器

```python
# atomx/plugin/manager.py
from typing import List, Dict
from atomx.plugin.base import AtomXPlugin

class PluginManager:
    """插件管理器 — 注册、排序、分发回调"""

    def __init__(self):
        self._plugins: List[AtomXPlugin] = []

    def register(self, plugin: AtomXPlugin):
        """注册插件"""
        self._plugins.append(plugin)
        # 按优先级排序
        self._plugins.sort(key=lambda p: p.priority)

    def unregister(self, name: str):
        """注销插件"""
        self._plugins = [p for p in self._plugins if p.name != name]

    def get(self, name: str) -> Optional[AtomXPlugin]:
        """获取指定插件"""
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    # === 回调分发 ===
    def call_connect(self, app, **kwargs):
        for plugin in self._plugins:
            plugin.on_connect(app, **kwargs)

    def call_find(self, app, locator, result=None):
        for plugin in self._plugins:
            result = plugin.on_find(app, locator, result)
        return result

    def call_action(self, app, action, args, kwargs, result=None):
        for plugin in self._plugins:
            result = plugin.on_action(app, action, args, kwargs, result)
        return result

    def call_assert(self, app, assertion, passed, **kwargs):
        for plugin in self._plugins:
            plugin.on_assert(app, assertion, passed, **kwargs)

    def call_error(self, app, error, context):
        for plugin in self._plugins:
            plugin.on_error(app, error, context)

    def call_report(self, app, report_data):
        for plugin in self._plugins:
            report_data = plugin.on_report(app, report_data)
        return report_data

    def call_teardown(self):
        for plugin in self._plugins:
            plugin.teardown()
```

### 20.4 内置插件示例 — 自动截图插件

```python
# atomx/plugin/builtin/auto_screenshot.py
import allure
from atomx.plugin.base import AtomXPlugin

class AutoScreenshotPlugin(AtomXPlugin):
    """
    自动截图插件 — 每个操作步骤自动截图并附加到 Allure

    通过配置启用/禁用:
    atomx.json5 → { "plugins": { "auto_screenshot": { "enabled": true } } }
    """

    name = "auto_screenshot"
    priority = 10

    def __init__(self, enabled: bool = True, on_step: bool = True,
                 on_failure: bool = True):
        self._enabled = enabled
        self._on_step = on_step
        self._on_failure = on_failure

    def on_action(self, app, action, args, kwargs, result=None):
        """操作执行后自动截图"""
        if not self._enabled or not self._on_step:
            return result
        try:
            screenshot = app.driver.screenshot()
            allure.attach(
                screenshot,
                name=f"screenshot_{action}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass
        return result

    def on_error(self, app, error, context):
        """异常发生时自动截图"""
        if not self._enabled or not self._on_failure:
            return
        try:
            screenshot = app.driver.screenshot()
            allure.attach(
                screenshot,
                name="error_screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass
```

### 20.5 用户自定义插件示例

```python
# testcases/plugins/my_plugin.py (用户自定义插件)
from atomx.plugin.base import AtomXPlugin
import logging

logger = logging.getLogger("my_plugin")

class MyCustomPlugin(AtomXPlugin):
    """用户自定义插件 — 记录所有操作到自定义日志"""

    name = "my_custom_plugin"
    priority = 20

    def __init__(self, log_file: str = "atomx_actions.log"):
        self._log_file = log_file
        self._file = None

    def on_connect(self, app, **kwargs):
        logger.info(f"设备连接: {kwargs}")
        self._file = open(self._log_file, "a", encoding="utf-8")

    def on_action(self, app, action, args, kwargs, result=None):
        self._file.write(f"{action}({args}, {kwargs})\n")
        self._file.flush()
        return result

    def on_error(self, app, error, context):
        self._file.write(f"ERROR: {error} | context: {context}\n")
        self._file.flush()

    def teardown(self):
        if self._file:
            self._file.close()

# 注册插件
from atomx.plugin.manager import PluginManager
pm = PluginManager()
pm.register(MyCustomPlugin(log_file="custom.log"))
```

### 20.6 配置文件注册插件

```yaml
# config/config.yaml
plugins:
  auto_screenshot:
    enabled: true
    on_step: false      # 步骤截图默认关闭 (避免过多)
    on_failure: true    # 失败截图默认开启
  perf_monitor:
    enabled: false      # 性能监控默认关闭
    interval: 2.0
  my_custom_plugin:
    enabled: true
    log_file: custom_actions.log
```
