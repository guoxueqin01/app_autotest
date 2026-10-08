"""CodeGenerator — 从 PageConfig 渲染 PageObject / Model / Flow YAML / TestSkeleton。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import yaml

from script.generator.core.schemas import PageConfig


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class CodeGenerator:
    """渲染 PageObject / Model / Flow YAML / TestSkeleton。"""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        self._templates = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self._templates)),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    # ---------------------------------------------------------------
    # 内部：把 Element 列表转成模板可消费的 dict 结构
    # ---------------------------------------------------------------

    @staticmethod
    def _element_payload(el: Any) -> Dict[str, Any]:
        return {
            "field": el.field,
            "display_name": el.display_name or el.field,
            "type": el.type,
            "locator_repr": json.dumps(el.locator, ensure_ascii=False),
            "locator_overrides_repr": json.dumps(el.locator_overrides, ensure_ascii=False),
            "fallback_repr": json.dumps(el.fallback, ensure_ascii=False),
            "confidence": el.confidence,
            "uniqueness": el.uniqueness,
            "text": el.text,
            "resource_id": el.resource_id,
            "content_desc": el.content_desc,
        }

    @staticmethod
    def _action_method(el: Any) -> str:
        """按类型生成 Page Object 语义化方法名。支持 Element 对象或 dict payload。"""
        etype = el.get("type") if isinstance(el, dict) else getattr(el, "type", None)
        mapping = {
            "button": "tap", "checkbox": "check", "switch": "check", "radio": "check",
            "input": "input_text", "password_input": "input_password",
            "text": "get_text", "label": "get_text", "image": "tap",
            "list_item": "tap", "list": "scroll_to", "scroll_view": "scroll",
            "tab": "tap", "navigation_bar": "tap", "progress": "wait_disappear",
            "slider": "set_slider", "spinner": "select_item", "date_picker": "select_date",
            "dialog": "dismiss", "container": "is_displayed",
        }
        return mapping.get(etype, "tap")

    # ---------------------------------------------------------------
    # 渲染
    # ---------------------------------------------------------------

    def render_page_object(self, config: PageConfig, elements: List[Any],
                          semantic_methods: bool = True) -> str:
        template = self._env.get_template("page_object.jinja2")
        enriched = [self._element_payload(e) for e in elements]
        if not enriched:
            enriched = [{"field": "placeholder", "locator_repr": '{"text": "placeholder"}'}]
        return template.render(
            class_name=config.class_name,
            module=config.module,
            package=config.package,
            activity=config.activity,
            platforms=config.platforms,
            elements=enriched,
            semantic_methods=semantic_methods,
            action_for=lambda el: self._action_method(el),
            first_field=enriched[0]["field"],
        )

    def render_model(self, config: PageConfig, elements: List[Any]) -> str:
        template = self._env.get_template("model.jinja2")
        return template.render(
            class_name=config.class_name,
            module=config.module,
            elements=[self._element_payload(e) for e in elements],
            cascade_fields=config.cascade_fields,
            cascade_defaults=config.cascade_defaults,
        )

    def render_flow_yaml(self, steps: List[Dict[str, Any]], case_name: str = "auto",
                         platforms: Optional[List[str]] = None) -> str:
        data = [{
            "case": case_name,
            "platforms": platforms or ["android"],
            "steps": steps,
        }]
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False,
                        Dumper=_NoAliasDumper)

    def render_test_skeleton(self, config: PageConfig, steps: List[Dict[str, Any]],
                             case_name: str = "auto") -> str:
        import json as _json
        template = self._env.get_template("test_flow.jinja2")
        platforms_repr = ", ".join(_json.dumps(p) for p in config.platforms)
        return template.render(
            class_name=config.class_name,
            module=config.module,
            case_name=case_name,
            platforms=config.platforms,
            platforms_repr=platforms_repr,
            steps=steps,
            first_step_field=(steps[0].get("field") if steps else ""),
        )

    # ---------------------------------------------------------------
    # 写盘
    # ---------------------------------------------------------------

    def write_page_object(self, config: PageConfig, elements: List[Any],
                         output_dir: Path, semantic_methods: bool = True) -> Path:
        module_dir = output_dir / "pages" / config.module
        module_dir.mkdir(parents=True, exist_ok=True)
        target = module_dir / f"{config.module}_page.py"
        target.write_text(
            self.render_page_object(config, elements, semantic_methods=semantic_methods),
            encoding="utf-8",
        )
        return target

    def write_model(self, config: PageConfig, elements: List[Any], output_dir: Path) -> Path:
        module_dir = output_dir / "models" / config.module
        module_dir.mkdir(parents=True, exist_ok=True)
        target = module_dir / f"{config.module}_models.py"
        target.write_text(
            self.render_model(config, elements), encoding="utf-8"
        )
        return target

    def write_flow(self, config: PageConfig, steps: List[Dict[str, Any]],
                   output_dir: Path, case_name: str = "auto") -> Path:
        data_dir = output_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        target = data_dir / f"{config.module}_{case_name}.yaml"
        target.write_text(
            self.render_flow_yaml(steps, case_name=case_name, platforms=config.platforms),
            encoding="utf-8",
        )
        return target

    def write_test_skeleton(self, config: PageConfig, steps: List[Dict[str, Any]],
                            output_dir: Path, case_name: str = "auto") -> Path:
        test_dir = output_dir / "testcases" / config.module
        test_dir.mkdir(parents=True, exist_ok=True)
        target = test_dir / f"test_{config.module}_{case_name}.py"
        target.write_text(
            self.render_test_skeleton(config, steps, case_name=case_name),
            encoding="utf-8",
        )
        return target
