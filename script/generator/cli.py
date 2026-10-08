"""Generator CLI — 子命令模式。

子命令:
  detect          连接设备，dump UI 树，仅输出检测到的元素（不生成代码）
  detect-config   连接设备 + 分析 + 生成 _config.yaml（人工可编辑）
  detect-modal    针对弹窗/浮层的检测（过滤祖先含 Dialog/Popup 的元素）
  generate-code   基于已有 _config.yaml 生成 PageObject + Model + Flow YAML + Test 骨架
  detect-batch    批量：给多个 module 依次执行 detect-config
  generate-all    批量：给多个 module 依次执行 generate-code

典型用法:
  python -m script.generator.cli detect --platform android --package com.x --module login --serial XXX
  python -m script.generator.cli detect-config --platform android --package com.x --module login
  python -m script.generator.cli generate-code --module login
  python -m script.generator.cli generate-all --modules login,home,search --platform android --package com.x
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from script.generator.core.analyzer import analyze
from script.generator.core.code_generator import CodeGenerator
from script.generator.core.config_builder import dump_config, load_config
from script.generator.core.config_resolver import ConfigResolver
from script.generator.core.detector import detect as detect_nodes
from script.generator.core.flow_builder import FlowBuilder
from script.generator.core.locator_builder import build_all as build_locators
from script.generator.core.schemas import PageConfig
from script.generator.core.validator import validate


logger = logging.getLogger("generator.cli")


# ==================================================================
# 公共子过程
# ==================================================================

def _connect_and_dump(platform: str, serial: str, package: str, activity: str = "") -> str:
    """连接设备并返回当前 UI 树 dump 字符串。"""
    from atomx.driver.factory import DriverFactory

    driver = DriverFactory.create(platform, serial)
    try:
        if package:
            try:
                driver.start_app(package)
            except Exception as exc:  # noqa: BLE001
                logger.warning("start_app failed: %s", exc)
        xml = driver.dump_hierarchy()
    finally:
        driver.disconnect()
    return xml or ""


def _analyze_xml(xml: str, platform: str) -> List[Any]:
    nodes = detect_nodes(xml, platform=platform)
    return analyze(nodes)


def _build_config(elements: List[Any], module: str, package: str, activity: str,
                  platforms: List[str], class_name: str = "") -> PageConfig:
    build_locators(elements, target_platforms=platforms)
    config = PageConfig(
        module=module,
        package=package,
        activity=activity,
        class_name=class_name or f"{module.capitalize()}Page",
        platforms=platforms,
        elements=elements,
    )
    return config


def _print_elements(elements: List[Any]) -> None:
    print(f"Detected {len(elements)} elements:")
    for el in elements:
        conf = el.confidence
        uniq = el.uniqueness
        loc = json.dumps(el.locator, ensure_ascii=False)
        print(f"  - [{el.type:<16}] {el.field:<28} conf={conf:.2f} uniq={uniq:<9} {loc}")


def _print_validation(config: PageConfig) -> bool:
    result = validate(config)
    if not result.ok:
        print("\n[validator] —")
        print(result.render())
    if result.warning_count:
        print(f"[validator] warnings={result.warning_count}")
    return result.ok


# ==================================================================
# 子命令实现
# ==================================================================

def cmd_detect(args: argparse.Namespace) -> int:
    """detect: 仅输出检测到的元素，不生成文件。"""
    xml = _connect_and_dump(args.platform, args.serial, args.package, args.activity)
    elements = _analyze_xml(xml, args.platform)
    _print_elements(elements)
    return 0


def cmd_detect_config(args: argparse.Namespace) -> int:
    """detect-config: 生成 pages/<module>/_config.yaml。"""
    output = Path(args.output).resolve()
    xml = _connect_and_dump(args.platform, args.serial, args.package, args.activity)
    elements = _analyze_xml(xml, args.platform)
    config = _build_config(elements, args.module, args.package, args.activity,
                           platforms=[args.platform], class_name=args.class_name)

    # 应用人工配置覆盖（若已存在）
    resolver = ConfigResolver(base_dir=str(output / "pages"))
    config = resolver.resolve(config)

    if not _print_validation(config):
        print("[warn] validation has errors — please review the config before generating code")

    path = dump_config(config, output)
    print(f"[ok] config written to {path}")
    return 0


def cmd_detect_modal(args: argparse.Namespace) -> int:
    """detect-modal: 只关注弹窗/浮层元素（祖先含 Dialog/Popup/Alert）。"""
    xml = _connect_and_dump(args.platform, args.serial, args.package, args.activity)
    nodes = detect_nodes(xml, platform=args.platform)
    modal_nodes = [
        (n, ctx) for (n, ctx) in nodes
        if any(k in " ".join(ctx.ancestors).lower() for k in ("dialog", "popup", "alert", "sheet"))
    ]
    elements = analyze(modal_nodes)
    _print_elements(elements)
    return 0


def cmd_generate_code(args: argparse.Namespace) -> int:
    """generate-code: 基于已有 _config.yaml 生成代码。"""
    output = Path(args.output).resolve()
    config_path = output / "pages" / args.module / "_config.yaml"
    if not config_path.exists():
        print(f"[error] config not found: {config_path}")
        print("please run 'detect-config' first")
        return 1

    config = load_config(config_path)
    if not config.class_name:
        config.class_name = f"{args.module.capitalize()}Page"

    if not _print_validation(config):
        if not args.force:
            print("[error] validation failed — use --force to bypass")
            return 2
        print("[warn] bypassing validation errors via --force")

    gen = CodeGenerator()
    flow_builder = FlowBuilder()
    steps = flow_builder.build(config)

    written: List[Path] = [
        gen.write_page_object(config, config.elements, output, semantic_methods=True),
        gen.write_model(config, config.elements, output),
        gen.write_flow(config, steps, output, case_name=args.case_name),
    ]
    if args.generate_test:
        written.append(gen.write_test_skeleton(config, steps, output, case_name=args.case_name))

    print("Generated:")
    for p in written:
        print(f"  - {p}")
    return 0


def cmd_detect_batch(args: argparse.Namespace) -> int:
    """detect-batch: 批量 detect-config。"""
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    failures = 0
    for module in modules:
        print(f"\n=== detecting: {module} ===")
        cfg = argparse.Namespace(
            platform=args.platform, serial=args.serial, package=args.package,
            activity="", module=module, class_name="", output=args.output,
        )
        if cmd_detect_config(cfg) != 0:
            failures += 1
    return 1 if failures else 0


def cmd_generate_all(args: argparse.Namespace) -> int:
    """generate-all: 批量 generate-code（可先自动 detect）。"""
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    failures = 0
    for module in modules:
        print(f"\n=== generating: {module} ===")
        if args.auto_detect:
            dc = argparse.Namespace(
                platform=args.platform, serial=args.serial, package=args.package,
                activity="", module=module, class_name="", output=args.output,
            )
            cmd_detect_config(dc)
        gc = argparse.Namespace(
            module=module, output=args.output, case_name="auto",
            generate_test=args.generate_test, force=args.force,
        )
        if cmd_generate_code(gc) != 0:
            failures += 1
    return 1 if failures else 0


# ==================================================================
# 主入口
# ==================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m script.generator.cli",
        description="AtomX code generator (subcommand mode)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # detect
    p = sub.add_parser("detect", help="connect device and print detected elements")
    p.add_argument("--platform", required=True, choices=["android", "ios", "harmony"])
    p.add_argument("--serial", default="")
    p.add_argument("--package", required=True)
    p.add_argument("--activity", default="")
    p.add_argument("--module", default="")
    p.set_defaults(func=cmd_detect)

    # detect-config
    p = sub.add_parser("detect-config", help="generate pages/<module>/_config.yaml")
    p.add_argument("--platform", required=True, choices=["android", "ios", "harmony"])
    p.add_argument("--serial", default="")
    p.add_argument("--package", required=True)
    p.add_argument("--activity", default="")
    p.add_argument("--module", required=True)
    p.add_argument("--class-name", default="")
    p.add_argument("--output", default=".")
    p.set_defaults(func=cmd_detect_config)

    # detect-modal
    p = sub.add_parser("detect-modal", help="detect only dialog/modal elements")
    p.add_argument("--platform", required=True, choices=["android", "ios", "harmony"])
    p.add_argument("--serial", default="")
    p.add_argument("--package", required=True)
    p.add_argument("--activity", default="")
    p.add_argument("--module", default="")
    p.set_defaults(func=cmd_detect_modal)

    # generate-code
    p = sub.add_parser("generate-code", help="generate PageObject/Model/Flow/Test from config")
    p.add_argument("--module", required=True)
    p.add_argument("--output", default=".")
    p.add_argument("--case-name", default="auto")
    p.add_argument("--generate-test", action="store_true", help="also write test skeleton")
    p.add_argument("--force", action="store_true", help="bypass validation errors")
    p.set_defaults(func=cmd_generate_code)

    # detect-batch
    p = sub.add_parser("detect-batch", help="batch detect-config for multiple modules")
    p.add_argument("--platform", required=True, choices=["android", "ios", "harmony"])
    p.add_argument("--serial", default="")
    p.add_argument("--package", required=True)
    p.add_argument("--modules", required=True, help="comma-separated, e.g. login,home,search")
    p.add_argument("--output", default=".")
    p.set_defaults(func=cmd_detect_batch)

    # generate-all
    p = sub.add_parser("generate-all", help="batch generate-code for multiple modules")
    p.add_argument("--modules", required=True)
    p.add_argument("--output", default=".")
    p.add_argument("--platform", default="android", choices=["android", "ios", "harmony"])
    p.add_argument("--serial", default="")
    p.add_argument("--package", default="")
    p.add_argument("--auto-detect", action="store_true", help="run detect-config before generating")
    p.add_argument("--generate-test", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_generate_all)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
