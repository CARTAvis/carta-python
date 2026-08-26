import pathlib

import pytest

from carta.version import (
    COMPATIBILITY,
    CompatibilityRange,
    action_failure_compatibility_suggestions,
    compatibility_for_carta,
    latest_compatibility,
    parse_carta_version,
    parse_version_series,
    version_mismatch_details,
)

VERSION_FILE = pathlib.Path(__file__).parent.parent / "VERSION.txt"


@pytest.mark.parametrize(
    "version",
    [
        "6.1.0",
        "6.1.0-dev",
        "6.1.0-beta.1",
        "6.1.0-rc.1",
    ],
)
def test_parse_carta_version_accepts_single_versions(version):
    assert parse_carta_version(version) == (6, 1, 0)


@pytest.mark.parametrize(
    "version",
    [
        "",
        "6.1",
        ">=6.1.0",
        "6.1.0,<7.0.0",
        "bad.version",
    ],
)
def test_parse_carta_version_rejects_invalid_versions(version):
    assert parse_carta_version(version) is None


def test_version_mismatch_details_reports_old_frontend_version():
    assert version_mismatch_details("5.9.0") == (
        [
            "CARTA version '5.9.0' is older than the minimum '6.1.0' required "
            "for complete functionality with carta-python 2.0.x."
        ],
        ["Upgrade CARTA to at least '6.1.0'."],
    )


def test_version_mismatch_details_uses_table_for_downgrade_suggestion(mocker):
    table = (
        CompatibilityRange(carta_min="5.0", carta_max="5.9", wrapper="1.0"),
        CompatibilityRange(carta_min="6.1", carta_max=None, wrapper="2.0"),
    )
    mocker.patch("carta.version.COMPATIBILITY", table)

    assert version_mismatch_details("5.9.0") == (
        [
            "CARTA version '5.9.0' is older than the minimum '6.1.0' required "
            "for complete functionality with carta-python 2.0.x."
        ],
        [
            "Upgrade CARTA to at least '6.1.0'.",
            "If CARTA cannot be upgraded, use carta-python 1.0.x, the recommended series "
            "for CARTA 5.0 - 5.9:\n"
            "  python -m pip install --upgrade \"carta-python~=1.0.0\"\n"
            "  or, for a uv-managed script:\n"
            "  uv add --script your_script.py \"carta-python~=1.0.0\" "
            "--upgrade-package carta-python\n"
            "  uv run your_script.py.",
        ],
    )


@pytest.mark.parametrize("version", ["6.1.0", "6.9.9", "7.0.0", "8.1.0"])
def test_version_mismatch_details_accepts_current_and_newer_carta(version):
    assert version_mismatch_details(version) == ([], [])


def test_version_mismatch_details_reports_invalid_frontend_version():
    assert version_mismatch_details("bad.version") == (
        ["frontend reported invalid CARTA version 'bad.version'."],
        ["Verify that CARTA reports a valid MAJOR.MINOR.PATCH version."],
    )


def test_action_failure_suggests_latest_carta_python_for_supported_carta():
    assert action_failure_compatibility_suggestions("6.1.0") == [
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


def test_action_failure_suggests_latest_carta_python_for_newer_carta():
    assert action_failure_compatibility_suggestions("7.0.0") == [
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


def test_action_failure_uses_table_for_older_carta(mocker):
    table = (
        CompatibilityRange(carta_min="5.0", carta_max="5.9", wrapper="1.0"),
        CompatibilityRange(carta_min="6.1", carta_max=None, wrapper="2.0"),
    )
    mocker.patch("carta.version.COMPATIBILITY", table)

    assert action_failure_compatibility_suggestions("5.9.0") == [
        "Upgrade CARTA to at least '6.1.0'.",
        "If CARTA cannot be upgraded, use carta-python 1.0.x, the recommended series for "
        "CARTA 5.0 - 5.9:\n"
        "  python -m pip install --upgrade \"carta-python~=1.0.0\"\n"
        "  or, for a uv-managed script:\n"
        "  uv add --script your_script.py \"carta-python~=1.0.0\" "
        "--upgrade-package carta-python\n"
        "  uv run your_script.py.",
    ]


def test_action_failure_ignores_unknown_carta_version():
    assert action_failure_compatibility_suggestions("bad.version") == []


def assert_table_is_ordered(table):
    for previous, current in zip(table, table[1:]):
        current_min = parse_version_series(current.carta_min)
        assert previous.carta_max is not None
        assert parse_version_series(previous.carta_max) < current_min
        assert parse_version_series(previous.wrapper) < parse_version_series(current.wrapper)


def test_compatibility_table_is_ordered_and_does_not_overlap():
    assert_table_is_ordered(COMPATIBILITY)


def test_open_ended_range_must_be_the_final_entry():
    table = (
        CompatibilityRange(carta_min="6.1", carta_max=None, wrapper="2.0"),
        CompatibilityRange(carta_min="7.0", carta_max=None, wrapper="3.0"),
    )

    with pytest.raises(AssertionError):
        assert_table_is_ordered(table)


def test_open_ended_range_covers_later_carta_major_versions():
    entry = CompatibilityRange(carta_min="6.1", carta_max=None, wrapper="2.0")

    assert entry.covers_carta("6.9.0")
    assert entry.covers_carta("7.0.0")
    assert entry.covers_carta("8.1.0")


def test_compatibility_table_bounds_are_valid_series():
    for entry in COMPATIBILITY:
        for bound in (entry.carta_min, entry.wrapper):
            assert parse_version_series(bound) is not None
        assert entry.carta_max is None or parse_version_series(entry.carta_max) is not None


def test_explicit_compatibility_range_may_span_carta_major_versions():
    entry = CompatibilityRange(carta_min="6.1", carta_max="7.2", wrapper="2.0")

    assert entry.covers_carta("7.2.9")
    assert not entry.covers_carta("7.3.0")


def test_package_version_matches_latest_compatibility():
    package_version = parse_carta_version(VERSION_FILE.read_text().strip())
    recommended_series = parse_version_series(latest_compatibility().wrapper)

    assert package_version[:2] == recommended_series


@pytest.mark.parametrize(
    "version", ["6.1.0", "6.1.0-dev", "6.9.9", "7.0.0", "8.1.0"]
)
def test_compatibility_for_carta_finds_supported_versions(version):
    assert compatibility_for_carta(version) is latest_compatibility()


@pytest.mark.parametrize("version", ["6.0.0", "5.9.0", "bad.version"])
def test_compatibility_for_carta_rejects_unsupported_versions(version):
    assert compatibility_for_carta(version) is None


def test_compatibility_labels():
    entry = latest_compatibility()

    assert entry.carta_label == "6.1+"
    assert entry.wrapper_label == "2.0.x"


def test_compatibility_label_with_explicit_cross_major_maximum():
    entry = CompatibilityRange(carta_min="6.0", carta_max="7.2", wrapper="1.2")

    assert entry.carta_label == "6.0 - 7.2"
    assert entry.wrapper_label == "1.2.x"
    assert entry.covers_carta("7.2.5")
    assert not entry.covers_carta("7.3.0")


@pytest.mark.parametrize(
    "series",
    ["", "6", "6.1.0", "6.x", "bad.series"],
)
def test_parse_version_series_rejects_invalid_series(series):
    assert parse_version_series(series) is None
