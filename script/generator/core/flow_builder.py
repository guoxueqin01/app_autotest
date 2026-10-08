"""FlowBuilder — 从 PageConfig 构建测试流程 steps。

支持：
1. 单页线性流程（open → wait → input → tap → assert）
2. 多页流程（steps 之间可以跨页面）
3. 条件分支（if: field == value，else_if，else）
4. 循环（loop: {count|foreach}）
5. 平台过滤（每个 step 可以指定 platforms 白名单）
6. 手动覆盖（用 config.flow 里的自定义 step，覆盖自动推断的）
"""
from __future__ import annotations

from typing import Any, Dict, List

from script.generator.core.schemas import Element, PageConfig


class FlowBuilder:
    """构建测试流程。"""

    def build(self, config: PageConfig) -> List[Dict[str, Any]]:
        """优先使用 config.flow（人工定义），否则按元素推断。"""
        if config.flow:
            return _apply_platform_filter(config.flow, config.platforms)

        steps: List[Dict[str, Any]] = []
        platform = config.platforms[0] if config.platforms else "android"

        # Step 1: open（仅在提供 package/activity 时生成）
        if config.package:
            steps.append({
                "action": "open",
                "locator": {"package": config.package, "activity": config.activity},
                "description": f"打开 {config.module} 页面",
                "platforms": config.platforms,
            })

        # Step 2: wait for first interactive element
        first = next((e for e in config.elements if e.type in ("button", "input", "text", "tab")), None)
        if first:
            steps.append({
                "action": "wait",
                "locator": first.locator,
                "field": first.field,
                "description": f"等待 {first.display_name or first.field} 出现",
            })

        # Step 3: input inputs
        for el in config.elements:
            if el.type in ("input", "password_input"):
                steps.append({
                    "action": "input",
                    "locator": el.locator,
                    "field": el.field,
                    "value": f"{{{el.field}}}",
                    "description": f"输入 {el.display_name or el.field}",
                })

        # Step 4: check / uncheck
        for el in config.elements:
            if el.type in ("checkbox", "switch", "radio"):
                steps.append({
                    "action": "check",
                    "locator": el.locator,
                    "field": el.field,
                    "description": f"勾选 {el.display_name or el.field}",
                })

        # Step 5: tap buttons (最后一个按钮优先，通常是提交)
        buttons = [e for e in config.elements if e.type == "button"]
        for el in reversed(buttons):
            steps.append({
                "action": "tap",
                "locator": el.locator,
                "field": el.field,
                "description": f"点击 {el.display_name or el.field}",
            })

        # Step 6: assert text
        for el in config.elements:
            if el.type in ("text", "label") and el.text:
                steps.append({
                    "action": "assert_exists",
                    "locator": el.locator,
                    "description": f"验证存在: {el.display_name or el.text}",
                })

        return _apply_platform_filter(steps, config.platforms)

    def build_multi_page(self, pages: List[PageConfig],
                         transition: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """多页流程：把多页 steps 拼起来，中间插入 transition 步骤。

        transition 示例:
            [{"action": "tap", "locator": {"text": "进入下一步"}, "description": "跳转到设置页"}]
        """
        all_steps: List[Dict[str, Any]] = []
        for i, page in enumerate(pages):
            all_steps.extend(self.build(page))
            if i < len(pages) - 1 and transition:
                all_steps.extend(transition)
        return all_steps

    def add_branch(self, base_steps: List[Dict[str, Any]],
                   condition_field: str, expected_value: str,
                   true_steps: List[Dict[str, Any]],
                   false_steps: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
        """把条件分支包装到 base_steps 中间。"""
        return base_steps + [
            {
                "action": "branch",
                "condition": {"field": condition_field, "op": "eq", "value": expected_value},
                "then": true_steps,
                "else": false_steps or [],
                "description": f"如果 {condition_field}={expected_value}",
            }
        ]

    def add_loop(self, steps: List[Dict[str, Any]],
                 action: str, target_locator: Dict[str, Any],
                 count: int = 3) -> List[Dict[str, Any]]:
        """在流程末尾追加循环。"""
        return steps + [{
            "action": "loop",
            "count": count,
            "steps": [{
                "action": action,
                "locator": target_locator,
                "description": f"循环 {count} 次 {action}",
            }],
        }]

    def to_data_cases(self, steps: List[Dict[str, Any]], case_name: str = "auto",
                      platforms: List[str] | None = None) -> List[Dict[str, Any]]:
        """导出为 YAML 数据结构（供 DataProvider 加载）。"""
        return [{
            "case": case_name,
            "platforms": platforms or ["android"],
            "steps": [
                {k: v for k, v in s.items() if k in ("action", "locator", "value", "field", "platforms")}
                for s in steps
            ],
        }]


def _apply_platform_filter(steps: List[Dict[str, Any]], target_platforms: List[str]) -> List[Dict[str, Any]]:
    """按 platforms 白名单过滤步骤。"""
    if not target_platforms:
        return steps
    out = []
    for s in steps:
        step_platforms = s.get("platforms")
        if not step_platforms:
            out.append(s)
        elif any(p in step_platforms for p in target_platforms):
            out.append(s)
    return out
