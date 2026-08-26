"""Compatibility wrapper for the packaged M8 federation reference helpers.

The single implementation source lives in ``marketplace.reference.federation_v1``.
This historical tool path remains for generators, validators, and developer
commands that predate the package boundary.
"""
from marketplace.reference.federation_v1 import *  # noqa: F401,F403
