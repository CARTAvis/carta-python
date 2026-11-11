"""Compatibility data for CARTA and carta-python releases."""


COMPATIBILITY_DATA = (
    {"carta_min": "6.1", "carta_max": None, "wrapper": "2.0"},
)
"""The recommended compatibility between CARTA and carta-python versions.

Each entry contains the oldest and newest CARTA series covered by the range and
the latest compatible carta-python series. ``carta_max=None`` means that the
range remains compatible with all later CARTA series until a known breaking
change requires an explicit upper bound and a new entry.

Ranges must be listed from oldest to newest and must be contiguous: each
``carta_min`` must be the series directly after the previous ``carta_max``
(the next minor version, or ``X.0`` of the next major version), so that no CARTA
series is left without a recommendation. The final
entry must omit ``carta_max``; every earlier entry must set it. The ``wrapper``
value in the final entry must match the major and minor version in ``VERSION.txt``.
Its ``carta_min`` value defines the minimum CARTA version for which the current
carta-python release provides complete functionality.
"""
