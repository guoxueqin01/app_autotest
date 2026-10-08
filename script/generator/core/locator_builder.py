"""LocatorBuilder — 为每个 Element 生成统一语义定位器 + 平台覆盖 + fallback 链。

产出结构:
{
  "field": "btn_login",
  "type": "button",
  "locator": {"resource_id": "com.app:id/btn_login"},   # 主定位器（单键）
  "locator_overrides": {
      "android": {"resource_id": "com.app:id/btn_login"},
      "ios": {"accessibility_id": "login_btn"},
      "harmony": {"id": "btn_login"}
  },
  "fallback": [
      {"text": "登录"},
      {"xpath": "//Button[@text='登录']"},
      {"image": "assets/login_btn.png"}
  ]
}
"""
from __future__ import annotations

from typing import Any, Dict, List

from script.generator.core.schemas import Element


# ================================================================
# 平台 -> 统一 locator key 映射
# ================================================================
PLATFORM_KEY_MAP: Dict[str, Dict[str, str]] = {
    # 平台 -> {source_attr -> unified_locator_key}
    "android": {
        "resource_id": "resource_id",
        "text": "text",
        "content_desc": "desc",
        "class": "class",
        "xpath": "xpath",
    },
    "ios": {
        "identifier": "accessibility_id",
        "text": "text",
        "value": "value",
        "name": "accessibility_id",
        "class": "class",
        "xpath": "xpath",
    },
    "harmony": {
        "id": "id",
        "text": "text",
        "description": "desc",
        "role": "class",
        "xpath": "xpath",
    },
}


def build_primary_locator(el: Element, platform: str) -> Dict[str, Any]:
    """根据元素属性生成主定位器（单键 dict）。"""
    key_map = PLATFORM_KEY_MAP.get(platform, PLATFORM_KEY_MAP["android"])

    # 优先级：resource_id > text > desc > class+text > xpath
    if el.resource_id:
        key = key_map.get("resource_id", "resource_id")
        return {key: el.resource_id}
    if el.text:
        key = key_map.get("text", "text")
        return {key: el.text}
    if el.content_desc:
        key = key_map.get("content_desc", "desc")
        return {key: el.content_desc}
    if el.raw_class and el.text:
        return {"class_text": f"{el.raw_class}=={el.text}"}
    if el.raw_class:
        return {"class": el.raw_class}
    return {}


def build_android_locator(el: Element) -> Dict[str, Any]:
    return build_primary_locator(el, "android")


def build_ios_locator(el: Element) -> Dict[str, Any]:
    """iOS: identifier > label > value > class chain"""
    if el.resource_id:
        return {"accessibility_id": el.resource_id}
    if el.text:
        return {"text": el.text}
    if el.content_desc:
        return {"text": el.content_desc}
    if el.raw_class:
        return {"class": el.raw_class}
    return {}


def build_harmony_locator(el: Element) -> Dict[str, Any]:
    if el.resource_id:
        return {"id": el.resource_id}
    if el.text:
        return {"text": el.text}
    if el.content_desc:
        return {"desc": el.content_desc}
    if el.raw_class:
        return {"class": el.raw_class}
    return {}


def build_fallback_chain(el: Element, platform: str = "android") -> List[Dict[str, Any]]:
    """生成 fallback 定位链 — 按优先级从主定位器退化。"""
    fallback: List[Dict[str, Any]] = []

    # 1. 若主定位是 resource_id，则 fallback 用 text / desc
    if el.resource_id and el.text:
        fallback.append({"text": el.text})
    if el.resource_id and el.content_desc:
        fallback.append({"desc": el.content_desc})

    # 2. 若主定位是 text，则 fallback 用 xpath / image
    if el.text and el.raw_class:
        xp = _build_xpath(el, platform)
        if xp:
            fallback.append({"xpath": xp})
        if el.display_name:
            fallback.append({"image": f"assets/{el.field}.png"})

    # 3. 若只有 desc，也生成 xpath 兜底
    if el.content_desc and el.text:
        fallback.append({"text": el.text})

    # 4. 最后保底：class-only（用于列表场景索引）
    if el.raw_class and not fallback:
        fallback.append({"class": el.raw_class})

    return fallback


def _build_xpath(el: Element, platform: str) -> str:
    """基于 raw_class + text/desc 生成 XPath。"""
    cls = el.raw_class
    # 剥掉包前缀，例如 android.widget.Button -> Button
    if "." in cls:
        cls = cls.split(".")[-1]
    if el.text:
        safe = el.text.replace("'", "\\'")[:60]
        return f"//{cls}[@text='{safe}']"
    if el.content_desc:
        safe = el.content_desc.replace("'", "\\'")[:60]
        return f"//{cls}[@content-desc='{safe}']"
    return ""


def build_for_element(el: Element, target_platforms: List[str]) -> Element:
    """就地更新 el.locator / locator_overrides / fallback。"""
    overrides: Dict[str, Dict[str, Any]] = {}
    for p in target_platforms:
        if p == "android":
            overrides["android"] = build_android_locator(el)
        elif p == "ios":
            overrides["ios"] = build_ios_locator(el)
        elif p == "harmony":
            overrides["harmony"] = build_harmony_locator(el)

    # 主定位器：优先用 android（大部分场景以 Android 为基准）
    primary_platform = "android" if "android" in target_platforms else target_platforms[0]
    el.locator = overrides.get(primary_platform, {})
    el.locator_overrides = overrides
    el.fallback = build_fallback_chain(el, primary_platform)
    return el


def build_all(elements: List[Element], target_platforms: List[str]) -> List[Element]:
    """对全部元素构建 locator。"""
    if not target_platforms:
        target_platforms = ["android"]
    for el in elements:
        build_for_element(el, target_platforms)
    return elements
