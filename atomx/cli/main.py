"""AtomX CLI entrypoint: device discovery + codegen forwarding."""
from __future__ import annotations

import subprocess
import sys
from typing import Optional

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="atomx")
def cli() -> None:
    """AtomX — cross-platform App automation CLI."""


@cli.command()
@click.option("--platform", "-p", type=click.Choice(["android", "ios", "harmony"]), required=True)
@click.option("--class-name", "-n", default="AutoPage", help="Generated page class name")
@click.option("--module", "-m", required=True, help="Module name (e.g. login)")
@click.option("--package", "-a", required=True, help="App package / bundle id")
@click.option("--serial", "-s", default="", help="Device serial")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
def generate(platform: str, class_name: str, module: str, package: str, serial: str, output: str) -> None:
    """Generate page objects via the built-in generator."""
    cmd = [
        sys.executable,
        "-m",
        "script.generator.cli",
        "--platform",
        platform,
        "--package",
        package,
        "--module",
        module,
        "--output",
        output,
        "--serial",
        serial,
    ]
    if class_name:
        cmd += ["--class-name", class_name]
    subprocess.run(cmd, check=True)


@cli.command("devices")
def devices_cmd() -> None:
    """List connected devices across platforms."""
    # Android
    try:
        r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        for line in r.stdout.strip().splitlines()[1:]:
            if "device" in line:
                click.echo(f"  [Android]  {line.split()[0]}")
    except (FileNotFoundError, subprocess.SubprocessError):
        click.echo("  [Android]  adb not installed")

    # iOS
    try:
        r = subprocess.run(["tidevice", "list"], capture_output=True, text=True, timeout=10)
        for line in r.stdout.strip().splitlines():
            if line.strip():
                click.echo(f"  [iOS]      {line.strip()}")
    except (FileNotFoundError, subprocess.SubprocessError):
        click.echo("  [iOS]      tidevice not installed")

    # HarmonyOS
    try:
        r = subprocess.run(["hdc", "list", "targets"], capture_output=True, text=True, timeout=10)
        for line in r.stdout.strip().splitlines():
            if line.strip():
                click.echo(f"  [Harmony]  {line.strip()}")
    except (FileNotFoundError, subprocess.SubprocessError):
        click.echo("  [Harmony]  hdc not installed")


if __name__ == "__main__":
    cli()
