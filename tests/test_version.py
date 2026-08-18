import pytest

from carta.util import CartaValidationFailed
from carta.version import parse_carta_version, validate_carta_version


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


@pytest.mark.parametrize(
    "version",
    [
        "6.1.0",
        "6.1.0-dev",
        "6.1.0-beta.1",
        "6.1.0-rc.1",
    ],
)
def test_validate_carta_version_accepts_single_versions(version):
    assert validate_carta_version(version) == (6, 1, 0)


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
def test_validate_carta_version_rejects_invalid_versions(version):
    with pytest.raises(CartaValidationFailed):
        validate_carta_version(version)


def test_validate_carta_version_uses_parameter_name_in_error():
    with pytest.raises(CartaValidationFailed) as error:
        validate_carta_version("bad.version", parameter_name="minimum_carta_version")

    assert "minimum_carta_version" in str(error.value)
