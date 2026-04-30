import pytest

from carta.util import (
    CartaValidationFailed,
    Point as Pt,
    carta_version_satisfies_requirement,
)


def test_point_equality():
    assert Pt(1, 2) == Pt(1, 2)
    assert Pt("1", "2") == Pt("1", "2")
    assert Pt(1, 2) != Pt("1", "2")
    assert Pt(1, 2) != (1, 2)


def test_point_is_pixel():
    assert Pt.is_pixel(1, 2)
    assert not Pt.is_pixel("1", 2)
    assert not Pt.is_pixel("1", "2")


def test_point_is_wcs():
    assert Pt.is_wcs_coordinate("123", "123")
    assert Pt.is_wcs_coordinate("12:34:56", "12:34:56")
    assert not Pt.is_wcs_coordinate(1, 2)


def test_point_is_angular():
    assert Pt.is_angular_size("123", "123")
    assert Pt.is_angular_size("123'", "123'")
    assert not Pt.is_angular_size(1, 2)


def test_point_json():
    assert Pt(1, 2).json() == {"x": 1, "y": 2}
    assert Pt("1", "2").json() == {"x": "1", "y": "2"}


def test_point_tuple():
    assert Pt(1, 2).as_tuple() == (1, 2)
    assert Pt("1", "2").as_tuple() == ("1", "2")


@pytest.mark.parametrize("requirement", [
    ">=6.1.0",
    ">6.0.0",
    "<=6.1.0",
    "<6.2.0",
    "==6.1.0",
    ">=6.0.0,<7.0.0",
    " >= 6.0.0 , < 7.0.0 ",
])
def test_carta_version_satisfies_requirement_accepts_matching_versions(requirement):
    assert carta_version_satisfies_requirement("6.1.0", requirement)


@pytest.mark.parametrize("requirement", [
    ">=6.2.0",
    ">6.1.0",
    "<=6.0.0",
    "<6.1.0",
    "==6.2.0",
    ">=6.0.0,<6.1.0",
])
def test_carta_version_satisfies_requirement_rejects_nonmatching_versions(requirement):
    assert not carta_version_satisfies_requirement("6.1.0", requirement)


@pytest.mark.parametrize("version", [
    "6.1.0-dev",
    "6.1.0-beta.1",
    "6.1.0-rc.1",
])
def test_carta_version_satisfies_requirement_ignores_suffix(version):
    assert carta_version_satisfies_requirement(version, "==6.1.0")


def test_carta_version_satisfies_requirement_rejects_bad_detected_version():
    assert not carta_version_satisfies_requirement("bad.version", ">=6.1.0")


def test_carta_version_satisfies_requirement_validates_requirement_first():
    with pytest.raises(CartaValidationFailed):
        carta_version_satisfies_requirement("bad.version", "6.1.0")


@pytest.mark.parametrize("requirement", [
    "",
    "6.1.0",
    "=6.1.0",
    "!=6.1.0",
    ">=bad.version",
    ">=6.1.0,",
])
def test_carta_version_satisfies_requirement_raises_for_bad_requirement(requirement):
    with pytest.raises(CartaValidationFailed):
        carta_version_satisfies_requirement("6.1.0", requirement)
