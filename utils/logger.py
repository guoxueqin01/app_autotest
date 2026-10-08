"""Project-level logger re-export."""
from __future__ import annotations

from atomx.infra.logger import Logger

logger = Logger("atomx.test")

__all__ = ["logger", "Logger"]
