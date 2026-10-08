"""Detector — UI 树分层扫描，输出 Element + ElementContext。

与旧 scanner.scan_hierarchy 区别:
1. 保留祖先链、深度、索引等上下文（用于生成 XPath）
2. 支持 XML（Android / HarmonyOS）和 JSON（iOS WDA source）两种输入
3. 属性统一通过 UNIFIED_ATTR_MAP 转成 resource_id / text / content_desc / raw_class
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree

from script.generator.core.constants import UNIFIED_ATTR_MAP
from script.generator.core.schemas import ElementContext


@dataclass
class RawNode:
    """原始 UI 树节点。"""

    tag: str
    attrs: Dict[str, Any] = field(default_factory=dict)
    children: List["RawNode"] = field(default_factory=list)


def _map_attrs(raw: Dict[str, str]) -> Dict[str, Any]:
    """把平台原生属性键统一映射。"""
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        key = UNIFIED_ATTR_MAP.get(k, k)
        if key in out:
            # 已存在优先保留（如 iOS 的 label 与 value 都映射到 text，先出现的胜出）
            continue
        out[key] = v
    return out


def _extract_bounds(bounds: str) -> Optional[Tuple[int, int, int, int]]:
    if not bounds or bounds == "[0,0][0,0]":
        return None
    try:
        parts = [int(x) for x in bounds.replace("[", ",").replace("]", ",").replace("][", ",").split(",") if x.strip()]
        if len(parts) == 4:
            return tuple(parts)  # type: ignore[return-value]
    except Exception:
        pass
    return None


def parse_xml_hierarchy(xml: str) -> RawNode:
    """解析 Android / HarmonyOS 的 XML dump。"""
    if not xml or not xml.strip():
        return RawNode(tag="<empty>")
    root = etree.fromstring(xml.encode("utf-8"))

    def _walk(el: etree._Element) -> RawNode:
        node = RawNode(tag=el.tag or "node", attrs=_map_attrs(dict(el.attrib)))
        for child in list(el):
            node.children.append(_walk(child))
        return node

    return _walk(root)


def parse_json_hierarchy(source_json: str) -> RawNode:
    """解析 iOS WDA 的 source JSON。

    典型结构:
      {"value": {"type": "XCUIElementTypeApplication", "children": [...], ...}, "sessionId": "..."}
    """
    if not source_json or not source_json.strip():
        return RawNode(tag="<empty>")
    data = json.loads(source_json)
    root_value = data.get("value", data) if isinstance(data, dict) else data

    def _walk(obj: Dict[str, Any]) -> RawNode:
        attrs: Dict[str, Any] = {}
        for k in ("type", "identifier", "label", "value", "name", "traits",
                  "enabled", "visible", "frame", "accessible"):
            if k in obj:
                attrs[k] = obj[k]
        # frame -> bounds 归一
        frame = obj.get("frame") or obj.get("rect")
        if isinstance(frame, dict):
            try:
                attrs["bounds"] = f"{int(frame['x'])},{int(frame['y'])},{int(frame['x'] + frame['width'])},{int(frame['y'] + frame['height'])}"
            except Exception:
                pass
        node = RawNode(tag=obj.get("type", "node"), attrs=_map_attrs(attrs))
        for child in obj.get("children", []) or []:
            node.children.append(_walk(child))
        return node

    return _walk(root_value)


def walk_with_context(root: RawNode, platform: str = "android") -> List[Tuple[RawNode, ElementContext]]:
    """遍历 UI 树，为每个节点输出 (node, context)。"""
    results: List[Tuple[RawNode, ElementContext]] = []

    def _walk(node: RawNode, ancestors: List[str], depth: int, parent_index: int) -> None:
        attrs = node.attrs or {}
        bounds = attrs.get("bounds", "")
        ctx = ElementContext(
            element_id="",  # 由 analyzer 后填
            ancestors=list(ancestors),
            depth=depth,
            parent_index=parent_index,
            bounds=bounds if isinstance(bounds, str) else "",
            is_visible=str(attrs.get("visible", attrs.get("visible_to_user", "true"))).lower() in ("true", "1", "yes"),
            is_enabled=str(attrs.get("enabled", "true")).lower() in ("true", "1", "yes"),
            is_clickable=str(attrs.get("clickable", "false")).lower() in ("true", "1", "yes"),
            is_focused=str(attrs.get("focused", "false")).lower() in ("true", "1", "yes"),
            platform=platform,
        )
        results.append((node, ctx))
        for i, child in enumerate(node.children):
            _walk(child, ancestors + [node.tag], depth + 1, i)

    _walk(root, [], 0, 0)
    return results


def detect(xml_or_json: str, platform: str = "android") -> List[Tuple[RawNode, ElementContext]]:
    """主入口：根据平台选择解析方式并返回带上下文的节点列表。"""
    if not xml_or_json or not xml_or_json.strip():
        return []
    first = xml_or_json.lstrip()[:1].lower()
    if first == "{":
        root = parse_json_hierarchy(xml_or_json)
    else:
        root = parse_xml_hierarchy(xml_or_json)
    return walk_with_context(root, platform=platform)
