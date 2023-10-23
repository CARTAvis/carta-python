from carta.util import Point as Pt


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
