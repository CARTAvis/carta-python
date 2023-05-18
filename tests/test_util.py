import types
import pytest

from carta.util import SizeUnit, CoordinateUnit
from carta.constants import NumberFormat as NF


@pytest.mark.parametrize("clazz", [SizeUnit, CoordinateUnit])
def test_class_has_docstring(clazz):
    assert clazz.__doc__ is not None


def find_members(*classes, member_type=types.MethodType):
    for clazz in classes:
        for name in dir(clazz):
            if not name.startswith('__') and isinstance(getattr(clazz, name), member_type):
                yield getattr(clazz, name)


@pytest.mark.parametrize("member", find_members(SizeUnit, CoordinateUnit))
def test_class_classmethods_have_docstrings(member):
    assert member.__doc__ is not None


@pytest.mark.parametrize("size,num,unit", [
    ("123arcmin", "123", "'"),
    ("123arcsec", "123", "\""),
    ("123deg", "123", "deg"),
    ("123degree", "123", "deg"),
    ("123degrees", "123", "deg"),
    ("123px", "123", "px"),
    ("123pix", "123", "px"),
    ("123pixel", "123", "px"),
    ("123pixels", "123", "px"),
    ("123 arcmin", "123", "'"),
    ("123 arcsec", "123", "\""),
    ("123 deg", "123", "deg"),
    ("123 degree", "123", "deg"),
    ("123 degrees", "123", "deg"),
    ("123 px", "123", "px"),
    ("123 pix", "123", "px"),
    ("123 pixel", "123", "px"),
    ("123 pixels", "123", "px"),
    ("123", "123", "\""),
    ("123\"", "123", "\""),
    ("123'", "123", "'"),
])
def test_size_unit_normalized(size, num, unit):
    assert SizeUnit.normalized(size) == (num, unit)


@pytest.mark.parametrize("size", ["123cm", "abc", "-123"])
def test_size_unit_normalized_invalid(size):
    with pytest.raises(ValueError) as e:
        SizeUnit.normalized(size)
    assert "not in a recognized size format" in str(e.value)


@pytest.mark.parametrize("coord,num", [
    ("123px", "123"),
    ("123pix", "123"),
    ("123pixel", "123"),
    ("123pixels", "123"),
    ("123 px", "123"),
    ("123 pix", "123"),
    ("123 pixel", "123"),
    ("123 pixels", "123"),
])
def test_coordinate_unit_pixel_value(coord, num):
    assert CoordinateUnit.pixel_value(coord) == num


@pytest.mark.parametrize("coord", ["123deg", "123", "-123px"])
def test_coordinate_unit_pixel_value_invalid(coord):
    with pytest.raises(ValueError) as e:
        CoordinateUnit.pixel_value(coord)
    assert "could not be parsed as a pixel coordinate" in str(e.value)


@pytest.mark.parametrize("coord,fmt,norm", [
    ("123deg", NF.DEGREES, "123"),
    ("123degree", NF.DEGREES, "123"),
    ("123degrees", NF.DEGREES, "123"),
    ("123 deg", NF.DEGREES, "123"),
    ("123 degree", NF.DEGREES, "123"),
    ("123 degrees", NF.DEGREES, "123"),
    ("123", NF.DEGREES, "123"),
    ("12:34:56.789", NF.HMS, "12:34:56.789"),
    ("12:34:56.789", NF.DMS, "12:34:56.789"),
    ("12h34m56.789s", NF.HMS, "12:34:56.789"),
    ("12d34m56.789s", NF.DMS, "12:34:56.789"),
    ("12h34m56s", NF.HMS, "12:34:56"),
    ("12h34m", NF.HMS, "12:34:"),
    ("34m56.789s", NF.HMS, ":34:56.789"),
    ("12h", NF.HMS, "12::"),
    ("34m", NF.HMS, ":34:"),
    ("56.789s", NF.HMS, "::56.789"),
    ("12h56.789s", NF.HMS, "12::56.789"),
    ("", NF.HMS, "::"),
    ("12d34m56s", NF.DMS, "12:34:56"),
    ("12d34m", NF.DMS, "12:34:"),
    ("34m56.789s", NF.DMS, ":34:56.789"),
    ("12d", NF.DMS, "12::"),
    ("34m", NF.DMS, ":34:"),
    ("56.789s", NF.DMS, "::56.789"),
    ("12d56.789s", NF.DMS, "12::56.789"),
    ("", NF.DMS, "::"),
    ("123d", NF.DMS, "123::"),
])
def test_size_unit_normalized(coord, fmt, norm):
    assert CoordinateUnit.normalized(coord, fmt) == norm


@pytest.mark.parametrize("coord,fmt", [
    ("123deg", NF.HMS),
    ("12:34:56.789", NF.DEGREES),
    ("123:45:67", NF.HMS),
    ("123h45m67s", NF.HMS),
    ("123d45m67s", NF.HMS),
])
def test_size_unit_normalized_invalid(coord, fmt):
    with pytest.raises(ValueError) as e:
        CoordinateUnit.normalized(coord, fmt)
    assert "does not match expected format" in str(e.value)
