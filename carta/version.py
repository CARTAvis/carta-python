"""Helpers for validating CARTA version compatibility."""

import re
from dataclasses import dataclass, field

from .compatibility import COMPATIBILITY_DATA


_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9.]+)?")
_SERIES_PATTERN = re.compile(r"(\d+)\.(\d+)")

Version = tuple[int, int, int]
VersionSeries = tuple[int, int]


def parse_carta_version(version: object) -> Version | None:
    """Parse a CARTA version, ignoring any prerelease suffix."""
    match = _VERSION_PATTERN.fullmatch(str(version))
    if match is None:
        return None

    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def parse_version_series(series: object) -> VersionSeries | None:
    """Parse a ``MAJOR.MINOR`` version series."""
    match = _SERIES_PATTERN.fullmatch(str(series))
    if match is None:
        return None

    major, minor = match.groups()
    return int(major), int(minor)


def _require_series(name: str, value: str) -> VersionSeries:
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
    _minimum: VersionSeries = field(init=False, repr=False, compare=False)
    _maximum: VersionSeries | None = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
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

    def covers_carta(self, version: object) -> bool:
        """Return whether this range covers a CARTA version."""
        parsed_version = parse_carta_version(version)
        if parsed_version is None:
            return False

        series = parsed_version[:2]
        if series < self._minimum:
            return False
        return self._maximum is None or series <= self._maximum

    @property
    def carta_label(self) -> str:
        """Return a human-readable CARTA version range."""
        if self.carta_max is None:
            return f"{self.carta_min}+"
        return f"{self.carta_min} - {self.carta_max}"

    @property
    def wrapper_label(self) -> str:
        """Return the recommended carta-python series label."""
        return f"{self.wrapper}.x"

    @property
    def carta_minimum_version(self) -> str:
        """Return the oldest full CARTA version covered by this range."""
        return f"{self.carta_min}.0"


COMPATIBILITY = tuple(CompatibilityRange(**entry) for entry in COMPATIBILITY_DATA)
"""Recommended CARTA and carta-python version combinations."""


def latest_compatibility() -> CompatibilityRange:
    """Return the newest range in the compatibility table."""
    return COMPATIBILITY[-1]


def compatibility_for_carta(version: object) -> CompatibilityRange | None:
    """Return the compatibility range covering a CARTA version."""
    for compatibility in COMPATIBILITY:
        if compatibility.covers_carta(version):
            return compatibility
    return None


def _older_carta_suggestions(
    version: object, current: CompatibilityRange
) -> list[str]:
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
            "  uv run your_script.py."
        )

    return suggestions


def version_mismatch_details(version: object) -> tuple[list[str], list[str]]:
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


def action_failure_compatibility_suggestions(version: object) -> list[str]:
    """Return compatibility suggestions after a frontend action failure."""
    parsed_version = parse_carta_version(version)
    if parsed_version is None:
        return []

    current = latest_compatibility()
    if parsed_version[:2] < current._minimum:
        return _older_carta_suggestions(version, current)

    return [
        "For direct scripting calls, verify that the frontend action, attribute, "
        "or response path exists.",
        "If this failure started after a CARTA upgrade, upgrade carta-python to "
        "the latest available release and retry. For a regular Python environment:\n"
        "  python -m pip install --upgrade carta-python\n"
        "For a uv-managed script:\n"
        "  uv add --script your_script.py carta-python --upgrade-package carta-python\n"
        "  uv run your_script.py",
        "If the failure persists after upgrading, check whether your script uses "
        "a renamed carta-python function or argument, a direct `call_action()` "
        "API path, or a changed response structure. Updating carta-python does "
        "not rewrite hard-coded API paths in your script.",
    ]
