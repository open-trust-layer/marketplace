"""Compatibility import path for the packaged Marketplace M3 reference helper.

The implementation lives in :mod:`marketplace.reference.record_v1`.
"""
from marketplace.reference import record_v1 as _implementation

for _name in dir(_implementation):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_implementation, _name)

del _name
del _implementation
