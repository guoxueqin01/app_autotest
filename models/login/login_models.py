"""Login data models — bridge between YAML and LoginPage."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from models.base_models import AssertionRule


@dataclass
class LoginPageData:
    """Login case data."""

    case: str = ""
    username: str = ""
    password: str = ""
    remember: bool = False
    expected_methods: List[AssertionRule] = field(default_factory=list)
    expected_error: str = ""
    alert_elem: str = ""
