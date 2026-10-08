"""[Deprecated] scanner.py — 保留作为向后兼容 shim。

请使用 detector.detect() 或 detector.detect_hierarchy() 代替。
"""
from __future__ import annotations

from typing import Any, Dict, List

from script.generator.core.detector import (
    RawNode,
    detect,
    parse_json_hierarchy,
    parse_xml_hierarchy,
)


def scan_hierarchy(xml: str) -> List[Dict[str, Any]]:
    """兼容旧接口 — 把 XML 扁平化成 dict 列表（不再推荐使用）。"""
    root = parse_xml_hierarchy(xml)
    nodes = detect(xml, platform="android")
    result: List[Dict[str, Any]] = []
    for node, ctx in nodes:
        attrs = node.attrs or {}
        result.append({
            "tag": node.tag,
            "attrs": dict(attrs),
            "text": str(attrs.get("text", "")),
            "resource_id": str(attrs.get("resource_id", "")),
            "content_desc": str(attrs.get("content_desc", "")),
            "depth": ctx.depth,
            "parent_index": ctx.parent_index,
        })
    return result
