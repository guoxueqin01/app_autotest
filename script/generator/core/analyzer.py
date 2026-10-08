"""Analyzer — 把 Detector 输出的节点分析成 Element 列表。

核心能力:
1. 细粒度类型推断（button/input/text/list/scroll_view/tab/dialog/...）
2. 中文 display_name 生成（基于 CN_LABEL_MAP + 词切）
3. snake_case 字段命名 + 拼音兜底（可选 pypinyin）
4. 置信度评估（依据是否有 id/text/desc + 是否 clickable）
5. 唯一性检查（同页内 field / locator 重复标记）
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from script.generator.core.constants import (
    CN_LABEL_MAP,
    LOCATOR_TYPE_PRIORITY,
    UNIFIED_TYPES,
)
from script.generator.core.schemas import Element, ElementContext


# ==================================================================
# 命名工具
# ==================================================================

_CN_CHARS_RE = re.compile(r"[\u4e00-\u9fff]+")
_EN_WORDS_RE = re.compile(r"[a-zA-Z0-9]+")


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return re.sub(r"_+", "_", s).strip("_")


def _sanitize(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name).strip("_").lower()


def _to_pinyin(text: str) -> str:
    """中文 -> 拼音兜底。pypinyin 未安装则退化为 hash 前缀。"""
    if not _CN_CHARS_RE.search(text or ""):
        return ""
    try:
        from pypinyin import lazy_pinyin  # type: ignore
        return "_".join(lazy_pinyin(text)).replace(" ", "_")
    except Exception:
        return f"cn_{abs(hash(text)) % 100000}"


def _infer_display_name(raw_class: str, text: str, resource_id: str, desc: str) -> str:
    """中文显示名：优先用 text/desc，其次走 CN_LABEL_MAP 映射 resource_id 尾段。"""
    if text and not _CN_CHARS_RE.fullmatch(text.strip()):
        # 英文原文
        slug = _sanitize(_camel_to_snake(text.strip()[:24]))
        if slug in CN_LABEL_MAP:
            return CN_LABEL_MAP[slug]
        return text.strip()[:24]
    if text:
        return text.strip()[:24]
    if desc:
        return desc.strip()[:24]
    # 从 resource_id 尾段映射（如 com.app:id/btn_login -> login -> 登录）
    tail = resource_id.split("/")[-1] if "/" in resource_id else resource_id
    tail = _sanitize(_camel_to_snake(tail))
    return CN_LABEL_MAP.get(tail, tail)


def _infer_field_name(resource_id: str, text: str, desc: str, unified_type: str, platform: str) -> str:
    """生成 snake_case 字段名。"""
    # 1. resource_id 尾段优先
    if resource_id:
        tail = resource_id.split("/")[-1] if "/" in resource_id else resource_id
        name = _sanitize(_camel_to_snake(tail))
        if name:
            return name
    # 2. text / desc
    for candidate in (text, desc):
        if not candidate:
            continue
        stripped = candidate.strip()
        if _EN_WORDS_RE.fullmatch(stripped[:24]):
            name = _sanitize(_camel_to_snake(stripped[:24]))
            if name:
                return name
        # 中文：查词表或走拼音
        cn = _CN_CHARS_RE.search(stripped)
        if cn:
            cn_word = cn.group()
            # 尝试整词命中词表（把中文当 keyword 查 CN_LABEL_MAP）
            pinyin = _to_pinyin(cn_word)
            if pinyin and pinyin not in ("", "cn"):
                return pinyin

    # 3. 兜底
    if platform == "ios":
        return f"el_{unified_type}"
    return f"{unified_type}_element"


def _infer_type(raw_class: str, attrs: Dict[str, Any]) -> str:
    """先精确匹配 UNIFIED_TYPES，再启发式兜底。"""
    if not raw_class:
        return "container"
    for unified, variants in UNIFIED_TYPES.items():
        if raw_class in variants:
            return unified
    lower = raw_class.lower()
    if "edit" in lower or "input" in lower or "textfield" in lower:
        return "input"
    if "secure" in lower or "password" in lower:
        return "password_input"
    if "button" in lower:
        return "button"
    if "check" in lower and "box" in lower:
        return "checkbox"
    if "switch" in lower or "toggle" in lower:
        return "switch"
    if "radio" in lower:
        return "radio"
    if "image" in lower:
        return "image"
    if "progressbar" in lower or "progress" in lower or "activityindicator" in lower:
        return "progress"
    if "seek" in lower or "slider" in lower:
        return "slider"
    if "recycler" in lower or "listview" in lower or "collection" in lower:
        return "list"
    if "scroll" in lower:
        return "scroll_view"
    if "spinner" in lower or "picker" in lower:
        return "spinner"
    if "dialog" in lower or "popup" in lower or "alert" in lower:
        return "dialog"
    if "tab" in lower:
        return "tab"
    if "navigation" in lower or "toolbar" in lower or "actionbar" in lower:
        return "navigation_bar"
    if "text" in lower:
        return "text"
    return "container"


# ==================================================================
# 唯一性 / 置信度
# ==================================================================

def _assess_confidence(raw_id: str, text: str, desc: str, is_clickable: bool,
                       is_visible: bool, is_enabled: bool, uniqueness: str) -> float:
    score = 0.0
    if raw_id:
        score += 0.5
    if text:
        score += 0.3
    if desc:
        score += 0.2
    if is_clickable:
        score += 0.1
    if not (is_visible and is_enabled):
        score -= 0.3
    if uniqueness == "non_unique":
        score -= 0.4
    elif uniqueness == "unique":
        score += 0.1
    return round(max(0.0, min(1.0, score)), 3)


# ==================================================================
# 主入口
# ==================================================================

def analyze(nodes: List[Tuple[Any, ElementContext]]) -> List[Element]:
    """把 Detector 的 (RawNode, ElementContext) 列表分析成 Element 列表。"""
    candidates: List[Element] = []
    for node, ctx in nodes:
        attrs = node.attrs or {}
        raw_class = attrs.get("raw_class", "") or node.tag or ""
        resource_id = str(attrs.get("resource_id", "") or "")
        text = str(attrs.get("text", "") or "")
        desc = str(attrs.get("content_desc", "") or "")
        platform = ctx.platform or "android"

        unified_type = _infer_type(raw_class, attrs)
        # 容器 & 不可见 & 非列表项 → 跳过
        if unified_type == "container" and not (isinstance(attrs.get("clickable"), str) and attrs.get("clickable") == "true"):
            continue
        if not ctx.is_visible and not (raw_class and ("Button" in raw_class or "Text" in raw_class)):
            continue
        if not text and not resource_id and not desc and not ctx.is_clickable:
            continue

        field = _infer_field_name(resource_id, text, desc, unified_type, platform)
        display = _infer_display_name(raw_class, text, resource_id, desc)

        elem = Element(
            field=field,
            display_name=display,
            type=unified_type,
            locator={},  # 后续由 locator_builder 填
            raw_class=raw_class,
            raw_attrs=dict(attrs),
            text=text,
            resource_id=resource_id,
            content_desc=desc,
        )
        candidates.append(elem)

    _mark_uniqueness(candidates)
    for el in candidates:
        el.confidence = _assess_confidence(
            el.resource_id, el.text, el.content_desc,
            is_clickable=bool(el.raw_attrs.get("clickable") in ("true", True, "True")),
            is_visible=True,
            is_enabled=True,
            uniqueness=el.uniqueness,
        )
    return candidates


def _mark_uniqueness(elements: List[Element]) -> None:
    """按 (locator_signature, type) 标记 unique / candidate / non_unique。"""
    from collections import Counter
    sig_counter = Counter(
        _signature(el) for el in elements if _signature(el)
    )
    for el in elements:
        sig = _signature(el)
        if not sig:
            el.uniqueness = "non_unique"
        elif sig_counter[sig] == 1:
            el.uniqueness = "unique"
        else:
            el.uniqueness = "non_unique" if sig_counter[sig] > 2 else "candidate"


def _signature(el: Element) -> str:
    key = el.resource_id or el.text or el.content_desc
    return f"{el.type}|{key}"
