"""External synthetic trial fence, imported before any custom integration.

This file belongs to the trial environment, never the HomeCircle package.
Home Assistant's standard custom-component discovery imports this parent before
resolving the unchanged HomeCircle manifest or importing product code.
"""
from . import _ordinary_boundary

_ordinary_boundary.install()
