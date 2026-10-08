"""HarmonyDriver — hdc + uitest based implementation."""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Dict, Optional

from atomx.driver.base import BaseDriver
from atomx.driver.harmony.hdc import HdcClient, HdcError


class HarmonyDriver(BaseDriver):
    """HarmonyOS driver wrapping hdc + uitest commands."""

    HARMONY_UITEST_BUNDLE = "com.ohos.uitest"

    def __init__(self) -> None:
        self._hdc: Optional[HdcClient] = None
        self._session_id: Optional[str] = None
        self._serial: str = ""

    def connect(self, serial: str = "", **kwargs: Any) -> "HarmonyDriver":
        self._serial = serial
        self._hdc = HdcClient(serial)
        try:
            info = self._hdc.shell("param get const.ohos.boot.hardware.version")
        except HdcError as exc:
            raise RuntimeError("Harmony device not reachable. Is hdc installed and device plugged in?") from exc
        if not info:
            raise RuntimeError("Empty Harmony device info. Check device connection.")
        try:
            self._hdc.shell(f"aa start -a ui_test -b {self.HARMONY_UITEST_BUNDLE}")
        except HdcError:
            # uitest service may not exist on this device version; operations
            # will fall back to `input` commands.
            pass
        return self

    def disconnect(self) -> None:
        self._hdc = None
        self._session_id = None

    def _require_hdc(self) -> HdcClient:
        if self._hdc is None:
            raise RuntimeError("HarmonyDriver not connected. Call connect() first.")
        return self._hdc

    # --- BaseDriver contract ---

    def dump_hierarchy(self) -> str:
        hdc = self._require_hdc()
        # 1st: uitest dumpHierarchy
        try:
            result = hdc.shell("uitest dump -p /data/local/tmp/uitest_hierarchy.json")
        except HdcError:
            result = ""
        try:
            raw = hdc.shell("cat /data/local/tmp/uitest_hierarchy.json")
            if raw.strip():
                tree = json.loads(raw)
                return self._normalize_to_xml(tree)
        except (HdcError, json.JSONDecodeError):
            pass

        # 2nd: accessibility dumpTree
        try:
            raw = hdc.shell("accessibility dumpTree --json")
            tree = json.loads(raw)
            return self._normalize_to_xml(tree)
        except Exception as exc:
            raise RuntimeError(f"Unable to fetch Harmony hierarchy: {exc}") from exc

    def click(self, x: int, y: int) -> None:
        hdc = self._require_hdc()
        try:
            hdc.shell(f"uitest click {x} {y}")
        except HdcError:
            hdc.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        hdc = self._require_hdc()
        speed = int(1000 / max(duration, 0.1))
        try:
            hdc.shell(f"uitest swipe {x1} {y1} {x2} {y2} {speed}")
        except HdcError:
            hdc.shell(f"input swipe {x1} {y1} {x2} {y2} {speed}")

    def input_text(self, text: str) -> None:
        hdc = self._require_hdc()
        safe = text.replace("'", "\\'")
        hdc.shell(f"uitest inputText '{safe}'")

    def screenshot(self) -> bytes:
        hdc = self._require_hdc()
        tmp = "/data/local/tmp/atomx_screenshot.png"
        hdc.shell(f"snapshot -f {tmp}")
        return hdc.pull_bytes(tmp)

    def start_app(self, package: str, activity: str = "") -> None:
        hdc = self._require_hdc()
        if activity:
            hdc.shell(f"aa start -a {activity} -b {package}")
        else:
            hdc.shell(f"aa start -b {package}")

    def stop_app(self, package: str) -> None:
        self._require_hdc().shell(f"aa force-stop {package}")

    def press_key(self, key: str) -> None:
        hdc = self._require_hdc()
        key = key.lower()
        cmd_map = {
            "home": "uitest pressKey Home",
            "back": "uitest pressKey Back",
            "power": "uitest pressKey Power",
            "menu": "uitest pressKey Menu",
        }
        cmd = cmd_map.get(key)
        if cmd:
            hdc.shell(cmd)
        else:
            raise NotImplementedError(f"HarmonyOS press_key does not support {key}")

    def get_device_info(self) -> Dict[str, Any]:
        hdc = self._require_hdc()
        def _get(cmd: str) -> str:
            try:
                return hdc.shell(cmd).strip()
            except HdcError:
                return ""
        return {
            "platform": "harmony",
            "serial": self._serial,
            "model": _get("param get const.product.model"),
            "brand": _get("param get const.product.brand"),
            "version": _get("param get const.ohos.fullname"),
            "sdk": _get("param get const.ohos.apiversion"),
        }

    # --- 录屏 ---

    def screen_record_start(self, **kwargs: Any) -> Optional[str]:
        """开始录屏 — 鸿蒙通过 hdc shell screenrecord"""
        hdc = self._require_hdc()
        self._record_path = "/data/local/tmp/atomx_record.mp4"
        time_limit = kwargs.get("time_limit", 180)
        try:
            hdc.shell(f"screenrecord --time-limit {time_limit} {self._record_path}")
        except Exception:  # noqa: BLE001
            pass
        return self._record_path

    def screen_record_stop(self) -> bytes:
        """停止录屏 — 返回视频字节流"""
        hdc = self._require_hdc()
        path = getattr(self, "_record_path", "/data/local/tmp/atomx_record.mp4")
        # 1. 停止录屏进程
        try:
            hdc.shell("pkill -SIGINT screenrecord")
        except Exception:  # noqa: BLE001
            pass
        # 2. 拉取录屏文件
        try:
            return hdc.pull_bytes(path)
        except Exception:  # noqa: BLE001
            return b""

    # --- Helpers ---

    def _normalize_to_xml(self, json_tree: Any) -> str:
        """Convert HarmonyOS component tree JSON to a unified XML string."""
        from lxml import etree

        root = etree.Element("hierarchy")
        if isinstance(json_tree, dict):
            self._build_xml_node(json_tree, root)
        elif isinstance(json_tree, list):
            for item in json_tree:
                self._build_xml_node(item, root)
        return etree.tostring(root, encoding="unicode")

    def _build_xml_node(self, node: Dict[str, Any], parent: Any) -> None:
        from lxml import etree

        if not isinstance(node, dict):
            return
        tag = node.get("type") or node.get("class") or "node"
        # Strip package prefixes like "com.example.Foo"
        tag = str(tag).split(".")[-1].replace("/", "_") or "node"
        el = etree.SubElement(parent, tag)
        for key, val in node.items():
            if key == "children":
                for child in val or []:
                    self._build_xml_node(child, el)
            else:
                el.set(str(key), "" if val is None else str(val))

    def _which(self, binary: str) -> Optional[str]:
        return shutil.which(binary)
