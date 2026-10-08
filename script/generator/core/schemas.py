"""统一数据模型 — 供 detector / analyzer / config_builder / code_generator 使用。

设计要点：
- 所有下游模块只依赖 schemas.py 定义的对象，不再散抛 dict
- locator 统一为嵌套 dict：{locator: {type: {...}}, locator_overrides: {...}, fallback: [...]},
  与方案文档 §9.6 严格一致
- PageConfig 与 pages/<module>/_config.yaml 结构 1:1 对齐
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

Platform = Literal["android", "ios", "harmony"]


@dataclass
class Element:
    """单个 UI 元素。

    字段说明:
      field:           语义化字段名 (snake_case)
      display_name:    中文显示名（供注释/文档用）
      type:            统一元素类型 (button/input/text/list/...)
      locator:         主定位器 (统一语义形式)
      locator_overrides: 平台覆盖 {android: {...}, ios: {...}, harmony: {...}}
      fallback:        兜底定位链 (list of locator dict)
      raw_class:       原始 class 名（含平台前缀）
      raw_attrs:       原始属性 dict
      confidence:      置信度 0.0-1.0
      uniqueness:      唯一性 (unique/candidate/non_unique)
    """

    field: str
    display_name: str = ""
    type: str = "text"
    locator: Dict[str, Any] = field(default_factory=dict)
    locator_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    fallback: List[Dict[str, Any]] = field(default_factory=list)
    raw_class: str = ""
    raw_attrs: Dict[str, Any] = field(default_factory=dict)
    text: str = ""
    resource_id: str = ""
    content_desc: str = ""
    confidence: float = 1.0
    uniqueness: str = "candidate"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Element":
        known = {f for f in cls.__dataclass_fields__}
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)


@dataclass
class ElementContext:
    """元素上下文 — 记录其在 UI 树中的位置、可见性、祖先链。

    用途：
    - 生成 XPath 时利用 parent/ancestor 缩小范围（避免同页同名重复）
    - 判断是否弹窗 / 是否列表项 / 是否 tab 项
    - 辅助命名（例如 tab 项取父级 label）
    """

    element_id: str = ""  # 对应 Element.field
    ancestors: List[str] = field(default_factory=list)  # 祖先 tag 链
    depth: int = 0
    parent_index: int = 0  # 在父节点下的索引
    bounds: str = ""  # "left,top,right,bottom"
    is_visible: bool = True
    is_enabled: bool = True
    is_clickable: bool = False
    is_focused: bool = False
    platform: str = "android"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PageConfig:
    """Page 配置 — 与 pages/<module>/_config.yaml 结构一致。

    cascade_fields: 用例数据里必须传的参数（框架会走 DataProvider）
    platforms:      需要生成的平台列表
    locator_overrides: 平台级定位器覆盖
    extra_elements: 人工追加的元素
    exclude:        需要排除的元素
    """

    module: str = ""
    package: str = ""
    activity: str = ""
    class_name: str = ""
    platforms: List[str] = field(default_factory=lambda: ["android"])
    cascade_fields: List[str] = field(default_factory=list)
    locator_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cascade_defaults: Dict[str, Any] = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)
    extra_elements: List[Element] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    flow: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "package": self.package,
            "activity": self.activity,
            "class_name": self.class_name,
            "platforms": self.platforms,
            "cascade_fields": self.cascade_fields,
            "cascade_defaults": self.cascade_defaults,
            "locator_overrides": self.locator_overrides,
            "elements": [e.to_dict() for e in self.elements],
            "extra_elements": [e.to_dict() for e in self.extra_elements],
            "exclude": self.exclude,
            "flow": self.flow,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageConfig":
        return cls(
            module=data.get("module", ""),
            package=data.get("package", ""),
            activity=data.get("activity", ""),
            class_name=data.get("class_name", ""),
            platforms=list(data.get("platforms") or ["android"]),
            cascade_fields=list(data.get("cascade_fields") or []),
            cascade_defaults=dict(data.get("cascade_defaults") or {}),
            locator_overrides=dict(data.get("locator_overrides") or {}),
            elements=[Element.from_dict(e) for e in (data.get("elements") or [])],
            extra_elements=[Element.from_dict(e) for e in (data.get("extra_elements") or [])],
            exclude=list(data.get("exclude") or []),
            flow=list(data.get("flow") or []),
        )
