"""ConfigResolver — 深度合并人工配置与自动分析结果。

与旧版本区别:
1. 深度合并（原为浅 merge）— 支持 locator_overrides / cascade_defaults 等嵌套 dict 递归合并
2. 冲突日志 — 覆盖时输出 INFO，便于人工复核
3. 支持 exclude / extra_elements / cascade_fields 等所有 PageConfig 字段
4. 输入输出统一为 PageConfig / Element（不再抛 dict）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from script.generator.core.schemas import Element, PageConfig

logger = logging.getLogger("generator.config_resolver")


class ConfigResolver:
    """用人工 _config.yaml 覆盖自动分析得到的 PageConfig。"""

    def __init__(self, base_dir: str = "pages") -> None:
        self._base_dir = Path(base_dir)

    def resolve(self, auto_config: PageConfig) -> PageConfig:
        """合并 base_dir/<module>/_config.yaml 到 auto_config 上。"""
        user_cfg = self._load_module_config(auto_config.module)
        if not user_cfg:
            return auto_config

        merged = PageConfig(
            module=auto_config.module,
            package=user_cfg.package or auto_config.package,
            activity=user_cfg.activity or auto_config.activity,
            class_name=user_cfg.class_name or auto_config.class_name,
            platforms=user_cfg.platforms or auto_config.platforms,
            cascade_fields=_deep_merge_list(auto_config.cascade_fields, user_cfg.cascade_fields),
            cascade_defaults=_deep_merge_dict(auto_config.cascade_defaults, user_cfg.cascade_defaults),
            locator_overrides=_deep_merge_dict(auto_config.locator_overrides, user_cfg.locator_overrides),
            elements=list(auto_config.elements),
            extra_elements=list(auto_config.extra_elements) + list(user_cfg.extra_elements),
            exclude=_deep_merge_list(auto_config.exclude, user_cfg.exclude),
            flow=_deep_merge_list(auto_config.flow, user_cfg.flow),
        )

        # 1. 应用 exclude
        if merged.exclude:
            merged.elements = [
                e for e in merged.elements if e.field not in merged.exclude
            ]
            logger.info("excluded %d elements by config", len(merged.exclude))

        # 2. 覆盖每个元素的 locator / display_name / type
        user_elements = {e.field: e for e in user_cfg.elements}
        for el in merged.elements:
            if el.field not in user_elements:
                continue
            user_el = user_elements[el.field]
            if user_el.locator:
                logger.info("override locator for '%s'", el.field)
                el.locator = user_el.locator
            if user_el.locator_overrides:
                el.locator_overrides = _deep_merge_dict(el.locator_overrides, user_el.locator_overrides)
            if user_el.fallback:
                el.fallback = user_el.fallback
            if user_el.display_name:
                el.display_name = user_el.display_name
            if user_el.type:
                el.type = user_el.type
        # 3. 追加人工新增元素
        for extra in user_cfg.extra_elements:
            if not any(e.field == extra.field for e in merged.elements):
                merged.elements.append(extra)

        return merged

    def _load_module_config(self, module: str) -> Optional[PageConfig]:
        path = self._base_dir / module / "_config.yaml"
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to load config %s: %s", path, exc)
            return None
        if data.get("module") != module:
            data["module"] = module
        return PageConfig.from_dict(data)


# ================================================================
# 深度合并工具
# ================================================================

def _deep_merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并 dict，b 覆盖 a。"""
    out = dict(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _deep_merge_list(a: List[Any], b: List[Any]) -> List[Any]:
    """列表按元素合并（去重，b 追加到末尾）。"""
    out = list(a)
    for item in b or []:
        if item not in out:
            out.append(item)
    return out
