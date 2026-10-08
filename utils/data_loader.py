"""YAML test-data loader — turn YAML files into dataclasses."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Type, TypeVar

import yaml

T = TypeVar("T")


def load_yaml(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_cases(path: str | Path) -> List[Dict[str, Any]]:
    """Load a list of case dicts from a YAML file.

    Expects top-level list or a mapping with a 'cases' key.
    """
    data = load_yaml(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cases" in data:
        return list(data["cases"])
    return [data]


def to_dataclass(cls: Type[T], data: Dict[str, Any]) -> T:
    """Instantiate a dataclass from a dict, ignoring unknown keys."""
    if not is_dataclass(cls):
        raise TypeError(f"{cls} is not a dataclass")
    known = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in known}
    return cls(**kwargs)


def load_cases_as(path: str | Path, model_cls: Type[T]) -> List[T]:
    return [to_dataclass(model_cls, item) for item in load_cases(path)]


def case_ids(cases: Iterable[Any]) -> List[str]:
    return [getattr(c, "case", getattr(c, "name", "")) for c in cases]
