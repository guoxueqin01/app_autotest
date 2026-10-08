"""AtomX — cross-platform App automation framework.

Public API:
    from atomx import AtomX

    app = AtomX()
    app.connect(platform="android")
    ...
"""
from atomx.api import AtomX
from atomx.engine.control.element import Element, ElementNotFoundError
from atomx.engine.control.locator_adapter import LocatorAdapter

__version__ = "0.1.0"

__all__ = ["AtomX", "Element", "ElementNotFoundError", "LocatorAdapter", "__version__"]
