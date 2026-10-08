"""Order list case data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from models.base_models import AssertionRule


@dataclass
class OrderListPageData:
    case: str = ""
    expected_rows: int = 0
    keyword: str = ""
    expected_status: str = ""
    expected_methods: List[AssertionRule] = field(default_factory=list)
