"""统一数据提供者 — 支持多格式数据源。

支持格式:
- YAML (.yaml/.yml)
- JSON (.json)
- CSV (.csv)
- Python 函数 (动态工厂)
- API 拉取
"""
from __future__ import annotations

import csv
import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class DataProvider:
    """统一数据提供者"""

    def __init__(self, base_dir: str = "data") -> None:
        self._base_dir = Path(base_dir)

    def load(self, filename: str, key: Optional[str] = None) -> Any:
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

    def _load_yaml(self, path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_json(self, path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_csv(self, path: Path) -> List[Dict[str, Any]]:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    # === 动态数据工厂 ===

    def generate(self, factory_name: str, count: int = 1, **kwargs: Any) -> list:
        """调用数据工厂生成测试数据

        factory_name 对应 data/factory/<factory_name>.py
        模块内需有 generate(**kwargs) 函数
        """
        import importlib
        import importlib.util

        module_path = f"data.factory.{factory_name}"
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            # 尝试从项目根目录加载
            factory_path = self._base_dir / "factory" / f"{factory_name}.py"
            if factory_path.exists():
                spec = importlib.util.spec_from_file_location(factory_name, factory_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)  # type: ignore
                else:
                    raise ImportError(f"无法加载工厂: {factory_path}")
            else:
                raise ImportError(f"数据工厂 {factory_name} 不存在于 {module_path}")

        if hasattr(module, "generate"):
            return [module.generate(**kwargs) for _ in range(count)]
        raise ValueError(f"数据工厂 {factory_name} 未找到 generate 函数")

    # === API 数据拉取 ===

    def from_api(self, endpoint: str, params: Optional[dict] = None, **kwargs: Any) -> Any:
        """从后端 API 拉取测试数据"""
        import requests

        headers = kwargs.pop("headers", {})
        timeout = kwargs.pop("timeout", 10)
        resp = requests.get(endpoint, params=params, headers=headers, timeout=timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()
