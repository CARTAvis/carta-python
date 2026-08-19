import pytest

from carta.version import parse_carta_version, version_mismatch_details


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
    assert version_mismatch_details("5.9.0", "6.0.0") == (
        ["frontend version '5.9.0' is older than the wrapper minimum '6.0.0'."],
        ["Upgrade CARTA to at least '6.0.0'."],
    )


def test_version_mismatch_details_reports_newer_frontend_major():
    assert version_mismatch_details("7.0.0", "6.0.0") == (
        [
            "frontend major version 7 is newer than the wrapper's "
            "supported major version 6."
        ],
        ["Upgrade carta-python to a version supporting CARTA major version 7."],
    )


def test_version_mismatch_details_reports_invalid_frontend_version():
    assert version_mismatch_details("bad.version", "6.0.0") == (
        ["frontend reported invalid CARTA version 'bad.version'."],
        ["Verify that CARTA reports a valid MAJOR.MINOR.PATCH version."],
    )
