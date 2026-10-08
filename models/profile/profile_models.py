"""Profile page data."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProfilePageData:
    case: str = ""
    expected_nickname: str = ""
