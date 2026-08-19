"""Helpers for validating CARTA version compatibility."""

import re

from .util import CartaValidationFailed


_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9.]+)?")


def parse_carta_version(version):
    """Parse a CARTA version string into a ``(major, minor, patch)`` tuple.

    Any prerelease suffix (e.g. ``"-dev"``, ``"-beta.1"``) is ignored.

    Parameters
    ----------
    version : string
        A version string of the form ``"MAJOR.MINOR.PATCH"`` with an optional
        ``"-SUFFIX"`` (e.g. ``"6.0.0"`` or ``"6.0.0-dev"``).

    Returns
    -------
    tuple or None
        ``(major, minor, patch)`` or ``None`` if the version string cannot be
        parsed.
    """
    match = _VERSION_PATTERN.fullmatch(str(version))
    if not match:
        return None

    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


def _parse_required_version(version):
    parsed = parse_carta_version(version)
    if parsed is None:
        raise CartaValidationFailed(
            "MINIMUM_CARTA_VERSION must be a version in "
            "MAJOR.MINOR.PATCH format."
        )
    return parsed


def version_mismatch_details(version, minimum_version):
    """Return compatibility problems and suggested actions for a CARTA version."""
    version_base = parse_carta_version(version)
    if version_base is None:
        return (
            [f"frontend reported invalid CARTA version {version!r}."],
            ["Verify that CARTA reports a valid MAJOR.MINOR.PATCH version."],
        )

    minimum_base = _parse_required_version(minimum_version)
    mismatches = []
    suggestions = []
    if version_base < minimum_base:
        mismatches.append(
            f"frontend version {version!r} is older than the wrapper minimum "
            f"{minimum_version!r}."
        )
        suggestions.append(f"Upgrade CARTA to at least {minimum_version!r}.")
    elif version_base[0] > minimum_base[0]:
        mismatches.append(
            f"frontend major version {version_base[0]} is newer than "
            f"the wrapper's supported major version {minimum_base[0]}."
        )
        suggestions.append(
            "Upgrade carta-python to a version supporting "
            f"CARTA major version {version_base[0]}.")

    return mismatches, suggestions
