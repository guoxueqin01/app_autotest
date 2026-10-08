"""多设备并行测试示例。

Usage:
    python examples/multi_device.py

推荐方式: 使用 pytest -n <workers> 并行执行:
    pytest testcases/ --platform android -n 3 --alluredir=./allure-results
"""
from __future__ import annotations

import concurrent.futures
import subprocess
from typing import List


def discover_devices() -> List[dict]:
    """发现三平台所有已连接设备"""
    devices: List[dict] = []

    # Android
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        for line in result.stdout.strip().split("\n")[1:]:
            if "device" in line:
                devices.append({"platform": "android", "serial": line.split()[0]})
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # iOS
    try:
        result = subprocess.run(["tidevice", "list"], capture_output=True, text=True, timeout=10)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                devices.append({"platform": "ios", "serial": line.strip()})
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # HarmonyOS
    try:
        result = subprocess.run(["hdc", "list", "targets"], capture_output=True, text=True, timeout=10)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                devices.append({"platform": "harmony", "serial": line.strip()})
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    return devices


def run_test_on_device(platform: str, serial: str) -> dict:
    """在单台设备上执行测试"""
    from atomx import AtomX

    app = AtomX()
    app.connect(platform=platform, serial=serial)
    try:
        app.start_app("com.example.app")
        app.find("搜索").tap()
        app.find({"id": "search_box"}).input_text("test")
        app.find("搜索").tap()
        app.assert_.exists("搜索结果")
        return {"device": serial, "result": "pass"}
    except Exception as exc:
        try:
            app.screenshot(f"failure_{serial}")
        except Exception:  # noqa: BLE001
            pass
        return {"device": serial, "result": "fail", "error": str(exc)}
    finally:
        app.disconnect()


def run_parallel() -> None:
    """多设备并行测试"""
    devices = discover_devices()
    if not devices:
        print("未检测到设备")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = [
            executor.submit(run_test_on_device, d["platform"], d["serial"])
            for d in devices
        ]
        results = [f.result() for f in futures]

    for r in results:
        status = f"{r['result']}" + (f" ({r.get('error', '')})" if r.get("error") else "")
        print(f"  {r['device']}: {status}")


if __name__ == "__main__":
    run_parallel()
