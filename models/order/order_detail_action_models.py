"""Order detail action data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderDetailActionData:
    case: str = ""
    order_id: str = ""
    expected_status: str = ""
    action: Optional[str] = None  # "cancel" / "pay" / None
