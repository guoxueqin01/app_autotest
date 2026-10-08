"""ConfigBuilder — 把分析结果写成 pages/<module>/_config.yaml。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from script.generator.core.schemas import PageConfig


def dump_config(config: PageConfig, output_dir: Path) -> Path:
    """输出 pages/<module>/_config.yaml"""
    module_dir = output_dir / "pages" / config.module
    module_dir.mkdir(parents=True, exist_ok=True)
    target = module_dir / "_config.yaml"
    data = _to_yaml_dict(config)
    target.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return target


def _to_yaml_dict(config: PageConfig) -> Dict[str, Any]:
    def _el_to_dict(el) -> Dict[str, Any]:
        d = el.to_dict()
        # 只保留有用字段，避免 YAML 冗余
        return {
            "field": d["field"],
            "display_name": d.get("display_name", ""),
            "type": d.get("type", "text"),
            "locator": d.get("locator", {}),
            "locator_overrides": d.get("locator_overrides", {}),
            "fallback": d.get("fallback", []),
            "confidence": d.get("confidence", 1.0),
            "uniqueness": d.get("uniqueness", "candidate"),
        }

    return {
        "module": config.module,
        "package": config.package,
        "activity": config.activity,
        "class_name": config.class_name or f"{config.module.capitalize()}Page",
        "platforms": config.platforms,
        "cascade_fields": config.cascade_fields,
        "cascade_defaults": config.cascade_defaults,
        "locator_overrides": config.locator_overrides,
        "exclude": config.exclude,
        "extra_elements": [_el_to_dict(e) for e in config.extra_elements],
        "elements": [_el_to_dict(e) for e in config.elements],
        "flow": config.flow,
    }


def load_config(path: Path) -> PageConfig:
    """从 YAML 加载回 PageConfig。"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return PageConfig.from_dict(data)
