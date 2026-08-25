"""Compatibility data for CARTA and carta-python releases."""


COMPATIBILITY_DATA = (
    {"carta_min": "6.1", "carta_max": None, "wrapper": "2.0"},
)
"""The recommended compatibility between CARTA and carta-python versions.

Each entry contains the oldest and newest CARTA series covered by the range and
the latest compatible carta-python series. ``carta_max`` is ``None`` for all
remaining series in the same CARTA major version.

Ranges must be listed from oldest to newest, must not overlap, and must not span
CARTA major versions. The ``wrapper`` value in the final entry must match the
major and minor version in ``VERSION.txt``. Its ``carta_min`` value defines the
minimum CARTA version for which the current carta-python release provides
complete functionality.
"""
