"""LocatorAdapter — translate unified semantic locators to platform XPath.

Locators accepted:
  * str: treated as text label.
  * dict: mapping from unified semantic attr (text/id/desc/class/...) to value.
  * raw XPath (starts with "/"): passed through.

The `class` attribute is translated twice:
  1. attribute name: class → class/type/type
  2. attribute value: checkbox → CheckBox/Switch/Toggle
"""
from __future__ import annotations

from typing import Any, Dict, Union

Locator = Union[str, Dict[str, Any]]

SUPPORTED_PLATFORMS = ("android", "ios", "harmony")


class LocatorAdapter:
    """Translate unified semantic locator into a platform-specific XPath."""

    ATTR_MAP: Dict[str, Dict[str, str]] = {
        "android": {
            "text": "text",
            "value": "text",
            "id": "resource-id",
            "desc": "content-desc",
            "class": "class",
            "accessibility": "resource-id",
            "checked": "checked",
            "enabled": "enabled",
            "clickable": "clickable",
            "visible": "visible-to-user",
        },
        "ios": {
            "text": "label",
            "value": "value",
            "id": "name",
            "desc": "help",
            "class": "type",
            "accessibility": "name",
            "enabled": "enabled",
            "visible": "visible",
            "checked": "value",
        },
        "harmony": {
            "text": "text",
            "value": "text",
            "id": "id",
            "desc": "description",
            "class": "type",
            "accessibility": "accessibilityId",
            "enabled": "enabled",
            "checked": "checked",
            "visible": "visible",
        },
    }

    CLASS_VALUE_MAP: Dict[str, Dict[str, str]] = {
        "android": {
            "input": "EditText",
            "textarea": "EditText",
            "checkbox": "CheckBox",
            "radio": "RadioButton",
            "button": "Button",
            "text": "TextView",
            "spinner": "Spinner",
            "list": "RecyclerView",
            "list_item": "LinearLayout",
            "dialog": "FrameLayout",
        },
        "ios": {
            "input": "TextField",
            "textarea": "TextView",
            "checkbox": "Switch",
            "radio": "RadioButton",
            "button": "Button",
            "text": "StaticText",
            "spinner": "Picker",
            "list": "CollectionView",
            "list_item": "Cell",
            "dialog": "Window",
        },
        "harmony": {
            "input": "TextInput",
            "textarea": "TextInput",
            "checkbox": "Toggle",
            "radio": "Radio",
            "button": "Button",
            "text": "Text",
            "spinner": "Select",
            "list": "List",
            "list_item": "ListItem",
            "dialog": "Dialog",
        },
    }

    def __init__(self, platform: str) -> None:
        platform = platform.lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {SUPPORTED_PLATFORMS}")
        self._platform = platform
        self._mapping = self.ATTR_MAP[platform]
        self._class_map = self.CLASS_VALUE_MAP[platform]

    @property
    def platform(self) -> str:
        return self._platform

    def to_platform_attr(self, attr: str) -> str:
        return self._mapping.get(attr, attr)

    def translate_class_value(self, value: str) -> str:
        return self._class_map.get(value, value)

    def to_xpath(self, locator: Locator) -> str:
        if isinstance(locator, str):
            if locator.startswith("/"):
                return locator
            attr = self._mapping.get("text", "text")
            return f'//*[@{attr}="{locator}"]'

        if isinstance(locator, dict):
            conditions = []
            for key, val in locator.items():
                attr = self._mapping.get(key, key)
                if key == "class":
                    val = self.translate_class_value(str(val))
                sval = str(val).replace('"', '\\"')
                conditions.append(f'@{attr}="{sval}"')
            if not conditions:
                raise ValueError(f"Empty locator dict: {locator!r}")
            return f'//*[{" and ".join(conditions)}]'

        raise TypeError(f"Unsupported locator type: {type(locator).__name__}")
