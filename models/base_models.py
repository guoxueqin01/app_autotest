"""Base dataclasses used by generated model files."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExtractRule:
    """Extraction rule for a field."""

    source: str = "element"
    locator: str = ""
    attribute: str = "text"


@dataclass
class AssertionRule:
    """Assertion rule for a step."""

    assert_method: str = ""
    locator: str = ""
    expected_text: str = ""


@dataclass
class StepData:
    """One step in a test case."""

    action: str
    input: dict = field(default_factory=dict)
    expected: Optional[dict] = None
    extract: Optional[Dict[str, ExtractRule]] = None


@dataclass
class CaseData:
    """A test case container."""

    case: str
    steps: List[StepData] = field(default_factory=list)
