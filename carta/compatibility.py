"""Compatibility data for CARTA and carta-python releases."""


COMPATIBILITY_DATA = (
    {"carta_min": "6.1", "carta_max": None, "wrapper": "2.0"},
)
"""The recommended compatibility between CARTA and carta-python versions.

Each entry contains the oldest and newest CARTA series covered by the range and
the latest compatible carta-python series. ``carta_max=None`` means that the
range remains compatible with all later CARTA series until a known breaking
change requires an explicit upper bound and a new entry.

Ranges must be listed from oldest to newest and must not overlap. Only the final
entry may omit ``carta_max``. The ``wrapper`` value in the final entry must
match the major and minor version in ``VERSION.txt``. Its ``carta_min`` value
defines the minimum CARTA version for which the current carta-python release
provides complete functionality.
"""
