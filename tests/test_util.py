import warnings

import pytest

from carta.util import (
    Point as Pt,
    deprecated,
)


def test_deprecated_warns_and_preserves_function_metadata():
    message = "use replacement instead"

    @deprecated(message)
    def legacy(value, *, increment=0):
        """The legacy function."""
        return value + increment

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert legacy(2, increment=3) == 5
        assert legacy(4) == 4

    assert [warning.category for warning in caught] == [DeprecationWarning, DeprecationWarning]
    assert [str(warning.message) for warning in caught] == [message, message]
    assert legacy.__name__ == "legacy"
    assert legacy.__doc__ == "The legacy function."


def test_deprecated_preserves_exceptions():
    @deprecated("use replacement instead")
    def legacy():
        raise RuntimeError("failure")

    with pytest.warns(DeprecationWarning, match="use replacement instead"):
        with pytest.raises(RuntimeError, match="failure"):
            legacy()


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
