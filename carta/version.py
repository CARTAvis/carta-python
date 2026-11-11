"""Helpers for validating CARTA version compatibility."""

import re
from dataclasses import dataclass, field

from .compatibility import COMPATIBILITY_DATA


_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9.]+)?")
_SERIES_PATTERN = re.compile(r"(\d+)\.(\d+)")

def parse_carta_version(version):
    """Parse a CARTA version, ignoring any prerelease suffix."""
    match = _VERSION_PATTERN.fullmatch(str(version))
    if match is None:
        return None

    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def parse_version_series(series):
    """Parse a ``MAJOR.MINOR`` version series."""
    match = _SERIES_PATTERN.fullmatch(str(series))
    if match is None:
        return None

    major, minor = match.groups()
    return int(major), int(minor)


def _require_series(name, value):
    parsed = parse_version_series(value)
    if parsed is None:
        raise ValueError(f"{name} must be in MAJOR.MINOR format, got {value!r}")
    return parsed


@dataclass(frozen=True)
class CompatibilityRange:
    """CARTA version range and its recommended carta-python series.

    Bounds use ``MAJOR.MINOR`` granularity and are inclusive. An omitted upper
    bound covers every later CARTA series until a known incompatibility closes
    the range.
    """

    carta_min: str
    carta_max: str | None
    wrapper: str
    _minimum: tuple[int, int] = field(init=False, repr=False, compare=False)
    _maximum: tuple[int, int] | None = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self):
        """Validate and cache the numeric version series."""
        minimum = _require_series("carta_min", self.carta_min)
        maximum = (
            None
            if self.carta_max is None
            else _require_series("carta_max", self.carta_max)
        )
        _require_series("wrapper", self.wrapper)

        if maximum is not None and maximum < minimum:
            raise ValueError("carta_max must not be earlier than carta_min")

        object.__setattr__(self, "_minimum", minimum)
        object.__setattr__(self, "_maximum", maximum)

    def covers_carta(self, version):
        """Return whether this range covers a CARTA version."""
        parsed_version = parse_carta_version(version)
        if parsed_version is None:
            return False

        series = parsed_version[:2]
        if series < self._minimum:
            return False
        return self._maximum is None or series <= self._maximum

    @property
    def carta_label(self):
        """Return a human-readable CARTA version range."""
        if self.carta_max is None:
            return f"{self.carta_min}+"
        return f"{self.carta_min} - {self.carta_max}"

    @property
    def wrapper_label(self):
        """Return the recommended carta-python series label."""
        return f"{self.wrapper}.x"

    @property
    def carta_minimum_version(self):
        """Return the oldest full CARTA version covered by this range."""
        return f"{self.carta_min}.0"


def _validate_compatibility_table(table):
    """Validate ordering and coverage invariants for a compatibility table."""
    if not table:
        raise ValueError("compatibility table must not be empty")
    if table[-1].carta_max is not None:
        raise ValueError("the final compatibility range must be open-ended")

    for previous, current in zip(table, table[1:]):
        if previous._minimum >= current._minimum:
            raise ValueError("compatibility ranges must be ordered from oldest to newest")
        if previous.carta_max is None:
            raise ValueError("only the final compatibility range may be open-ended")
        if previous._maximum >= current._minimum:
            raise ValueError("compatibility ranges must not overlap")
        if _require_series("wrapper", previous.wrapper) >= _require_series(
            "wrapper", current.wrapper
        ):
            raise ValueError("compatibility wrapper series must be strictly increasing")


COMPATIBILITY = tuple(CompatibilityRange(**entry) for entry in COMPATIBILITY_DATA)
"""Recommended CARTA and carta-python version combinations."""
_validate_compatibility_table(COMPATIBILITY)


def latest_compatibility():
    """Return the newest range in the compatibility table."""
    return COMPATIBILITY[-1]


def compatibility_for_carta(version):
    """Return the compatibility range covering a CARTA version."""
    for compatibility in COMPATIBILITY:
        if compatibility.covers_carta(version):
            return compatibility
    return None


def _older_carta_suggestions(
    version, current
):
    suggestions = [f"Upgrade CARTA to at least {current.carta_minimum_version!r}."]

    recommended = compatibility_for_carta(version)
    if recommended is not None:
        suggestions.append(
            f"If CARTA cannot be upgraded, use carta-python {recommended.wrapper_label}, "
            f"the recommended series for CARTA {recommended.carta_label}:\n"
            f"  python -m pip install --upgrade \"carta-python~={recommended.wrapper}.0\"\n"
            "  or, for a uv-managed script:\n"
            f"  uv add --script your_script.py \"carta-python~={recommended.wrapper}.0\" "
            "--upgrade-package carta-python\n"
            "  uv run your_script.py"
        )

    return suggestions


def version_mismatch_details(version):
    """Return connection problems and suggestions for a CARTA version."""
    parsed_version = parse_carta_version(version)
    if parsed_version is None:
        return (
            [f"frontend reported invalid CARTA version {version!r}."],
            ["Verify that CARTA reports a valid MAJOR.MINOR.PATCH version."],
        )

    current = latest_compatibility()
    if parsed_version[:2] >= current._minimum:
        return [], []

    mismatches = [
        f"CARTA version {version!r} is older than the minimum "
        f"{current.carta_minimum_version!r} required for complete "
        f"functionality with carta-python {current.wrapper_label}."
    ]
    return mismatches, _older_carta_suggestions(version, current)
