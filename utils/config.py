"""Configuration reader — loads config.yaml + env overrides."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(path: Path | str | None = None) -> Dict[str, Any]:
    """Load config with env-var overrides.

    Supported env vars (override config.yaml values):
      ATOMX_PLATFORM, ATOMX_SERIAL, ATOMX_PACKAGE, ATOMX_ACTIVITY,
      ATOMX_WAIT_TIMEOUT, ATOMX_ALLURE
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data = _load_yaml(cfg_path)

    env_map = {
        "ATOMX_PLATFORM": ("platform", str),
        "ATOMX_SERIAL": ("serial", str),
        "ATOMX_PACKAGE": ("package", str),
        "ATOMX_ACTIVITY": ("activity", str),
        "ATOMX_WAIT_TIMEOUT": ("wait_timeout", float),
        "ATOMX_ALLURE": ("allure", lambda v: v.lower() in ("1", "true", "yes")),
    }
    for env, (key, cast) in env_map.items():
        if env in os.environ:
            try:
                data[key] = cast(os.environ[env])
            except ValueError:
                data[key] = os.environ[env]

    data.setdefault("platform", "android")
    data.setdefault("serial", "")
    data.setdefault("package", "")
    data.setdefault("activity", "")
    data.setdefault("wait_timeout", 10.0)
    data.setdefault("allure", True)

    # 解析 diagnostics 段
    diagnostics = data.get("diagnostics", {})
    diagnostics.setdefault("failure_screenshot", True)
    diagnostics.setdefault("failure_video", True)
    diagnostics.setdefault("operation_trace", True)
    data["diagnostics"] = diagnostics

    return data
