"""Validator — 生成代码前的静态校验。

覆盖项:
1. 空 locator（未提供定位方式）
2. 重复字段名 / 重复 locator
3. cascade_fields 引用缺失（cascade 里的字段必须能在 elements 找到）
4. 低置信度元素（< 0.5）发出 warning，建议人工复核
5. 目标平台覆盖缺失（platforms 里指定的平台必须在 locator_overrides 出现）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from script.generator.core.schemas import PageConfig

logger = logging.getLogger("generator.validator")


@dataclass
class ValidationIssue:
    """校验问题条目。"""

    level: str          # error / warning / info
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper():<7}] {self.field}: {self.message}"


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "warning")

    def render(self) -> str:
        if not self.issues:
            return "OK — no issues."
        return "\n".join(str(i) for i in self.issues)


def validate(config: PageConfig) -> ValidationResult:
    """主入口 — 返回 ValidationResult。"""
    result = ValidationResult()

    # 1. 空 locator
    for el in config.elements:
        if not el.locator and not el.locator_overrides:
            result.issues.append(ValidationIssue("error", el.field, "empty locator"))

    # 2. 重复字段名
    seen_fields = {}
    for el in config.elements:
        if el.field in seen_fields:
            result.issues.append(ValidationIssue("error", el.field, f"duplicate field (also on '{seen_fields[el.field]}')"))
        else:
            seen_fields[el.field] = el.field

    # 3. 重复主定位器
    seen_locators = {}
    for el in config.elements:
        sig = _locator_sig(el.locator)
        if sig and sig in seen_locators:
            result.issues.append(
                ValidationIssue("warning", el.field,
                                f"same locator as '{seen_locators[sig]}' (locator={sig})")
            )
        else:
            seen_locators[sig] = el.field

    # 4. cascade_fields 引用完整性
    element_fields = {e.field for e in config.elements}
    for cf in config.cascade_fields:
        if cf not in element_fields:
            result.issues.append(
                ValidationIssue("error", cf, f"cascade_field not found in elements")
            )

    # 5. 低置信度
    for el in config.elements:
        if el.confidence < 0.5:
            result.issues.append(
                ValidationIssue("warning", el.field,
                                f"low confidence={el.confidence} (auto-locator may be unstable)")
            )

    # 6. 目标平台覆盖
    for el in config.elements:
        for p in config.platforms:
            if p not in el.locator_overrides:
                result.issues.append(
                    ValidationIssue("warning", el.field,
                                    f"missing locator_overrides[{p}]")
                )

    # 7. 空 elements（可能是空 dump 或全被 exclude）
    if not config.elements:
        result.issues.append(
            ValidationIssue("warning", "-", "no elements to generate (empty dump or all excluded)")
        )

    return result


def _locator_sig(locator: dict) -> str:
    if not locator:
        return ""
    return "|".join(f"{k}={v}" for k, v in sorted(locator.items()))
