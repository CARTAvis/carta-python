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


def validate_carta_version(version, parameter_name="CARTA version"):
    """Validate and parse a single CARTA version supplied by a caller.

    Version requirements are deliberately represented by one version. Callers
    interpret it as a minimum supported version; comparison operators and
    version ranges are not accepted.

    Parameters
    ----------
    version : string
        A version string of the form ``MAJOR.MINOR.PATCH`` with an optional
        prerelease suffix.
    parameter_name : string, optional
        Name to include in the validation error.

    Returns
    -------
    tuple
        The parsed ``(major, minor, patch)`` tuple.

    Raises
    ------
    CartaValidationFailed
        If ``version`` is not a valid CARTA version.
    """
    parsed = parse_carta_version(version)
    if parsed is None:
        raise CartaValidationFailed(
            f"{parameter_name} must be a version in MAJOR.MINOR.PATCH format."
        )
    return parsed


def version_mismatch_details(
    version, wrapper_minimum_version, minimum_carta_version=None
):
    """Return compatibility problems and suggested actions for a CARTA version."""
    version_base = parse_carta_version(version)
    if version_base is None:
        return (
            [f"frontend reported invalid CARTA version {version!r}."],
            ["Verify that CARTA reports a valid MAJOR.MINOR.PATCH version."],
        )

    requirements = [
        (
            "wrapper",
            validate_carta_version(
                wrapper_minimum_version,
                parameter_name="MINIMUM_CARTA_VERSION",
            ),
            wrapper_minimum_version,
        )
    ]
    if minimum_carta_version is not None:
        requirements.append(
            (
                "script",
                validate_carta_version(
                    minimum_carta_version,
                    parameter_name="minimum_carta_version",
                ),
                minimum_carta_version,
            )
        )

    mismatches = []
    suggestions = []
    carta_minimums = []
    for requirement_name, requirement_base, requirement in requirements:
        if version_base < requirement_base:
            mismatches.append(
                f"frontend version {version!r} is older than the "
                f"{requirement_name} minimum {requirement!r}."
            )
            carta_minimums.append((requirement_base, requirement))
        elif version_base[0] > requirement_base[0]:
            if requirement_name == "wrapper":
                mismatches.append(
                    f"frontend major version {version_base[0]} is newer than "
                    f"the wrapper's supported major version {requirement_base[0]}."
                )
                suggestions.append(
                    "Upgrade carta-python to a version supporting "
                    f"CARTA major version {version_base[0]}."
                )
            else:
                mismatches.append(
                    f"frontend major version {version_base[0]} is newer than "
                    f"the script target major version {requirement_base[0]}."
                )
                suggestions.append(
                    "Update the script's `minimum_carta_version` to a "
                    "compatible CARTA major version after verifying "
                    "compatibility."
                )

    if carta_minimums:
        _, required_version = max(carta_minimums, key=lambda item: item[0])
        if len(carta_minimums) > 1:
            suggestions.append(
                f"Upgrade CARTA to at least {required_version!r} "
                "to satisfy both the carta-python and script minimums."
            )
        else:
            suggestions.append(f"Upgrade CARTA to at least {required_version!r}.")

    return mismatches, suggestions
