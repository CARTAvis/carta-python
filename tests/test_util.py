import types
import pytest

from carta.util import PixelValue, AngularSize, WorldCoordinate
from carta.constants import NumberFormat as NF


@pytest.mark.parametrize("clazz", [PixelValue, AngularSize, WorldCoordinate])
def test_class_has_docstring(clazz):
    assert clazz.__doc__ is not None


def find_members(*classes, member_type=types.MethodType):
    for clazz in classes:
        for name in dir(clazz):
            if not name.startswith('__') and isinstance(getattr(clazz, name), member_type):
                yield getattr(clazz, name)


@pytest.mark.parametrize("member", find_members(PixelValue, AngularSize, WorldCoordinate))
def test_class_classmethods_have_docstrings(member):
    assert member.__doc__ is not None


@pytest.mark.parametrize("value,valid", [
    ("123px", True),
    ("123pix", True),
    ("123pixel", True),
    ("123pixels", True),
    ("123 px", True),
    ("123 pix", True),
    ("123 pixel", True),
    ("123 pixels", True),
    ("123arcmin", False),
    ("123deg", False),
    ("abc", False),
    ("123", False),
    ("123abc", False),
    ("-123px", False),
])
def test_pixel_value_valid(value, valid):
    assert PixelValue.valid(value) == valid


@pytest.mark.parametrize("value,num", [
    ("123px", 123),
    ("123pix", 123),
    ("123pixel", 123),
    ("123pixels", 123),
    ("123 px", 123),
    ("123 pix", 123),
    ("123 pixel", 123),
    ("123 pixels", 123),
    ("123.45px", 123.45),
    ("123.45 px", 123.45),
])
def test_pixel_value_as_float(value, num):
    assert PixelValue.as_float(value) == num


@pytest.mark.parametrize("value", ["123arcmin", "123deg", "abc", "123", "123abc", "-123px"])
def test_pixel_value_as_float_invalid(value):
    with pytest.raises(ValueError) as e:
        PixelValue.as_float(value)
    assert "not in a recognized pixel format" in str(e.value)


@pytest.mark.parametrize("size,valid", [
    ("123arcminutes", True),
    ("123arcseconds", True),
    ("123arcminute", True),
    ("123arcsecond", True),
    ("123arcmin", True),
    ("123arcsec", True),
    ("123amin", True),
    ("123asec", True),
    ("123deg", True),
    ("123degree", True),
    ("123degrees", True),
    ("123milliarcseconds", True),
    ("123milliarcsecond", True),
    ("123milliarcsec", True),
    ("123mas", True),
    ("123microarcseconds", True),
    ("123microarcsecond", True),
    ("123microarcsec", True),
    ("123µas", True),
    ("123uas", True),
    ("123 arcminutes", True),
    ("123 arcseconds", True),
    ("123 arcminute", True),
    ("123 arcsecond", True),
    ("123 arcmin", True),
    ("123 arcsec", True),
    ("123 amin", True),
    ("123 asec", True),
    ("123 deg", True),
    ("123 degree", True),
    ("123 degrees", True),
    ("123 milliarcseconds", True),
    ("123 milliarcsecond", True),
    ("123 milliarcsec", True),
    ("123 mas", True),
    ("123 microarcseconds", True),
    ("123 microarcsecond", True),
    ("123 microarcsec", True),
    ("123 µas", True),
    ("123 uas", True),
    ("123", True),
    ("123\"", True),
    ("123'", True),
    ("123cm", False),
    ("abc", False),
    ("-123", False),
    ("123px", False),
])
def test_angular_size_valid(size, valid):
    assert AngularSize.valid(size) == valid


@pytest.mark.parametrize("size,norm", [
    ("123arcminutes", "123'"),
    ("123arcseconds", "123\""),
    ("123arcminute", "123'"),
    ("123arcsecond", "123\""),
    ("123arcmin", "123'"),
    ("123arcsec", "123\""),
    ("123amin", "123'"),
    ("123asec", "123\""),
    ("123deg", "123deg"),
    ("123degree", "123deg"),
    ("123degrees", "123deg"),
    ("123milliarcseconds", "0.123\""),
    ("123milliarcsecond", "0.123\""),
    ("123milliarcsec", "0.123\""),
    ("123mas", "0.123\""),
    ("123microarcseconds", "0.000123\""),
    ("123microarcsecond", "0.000123\""),
    ("123microarcsec", "0.000123\""),
    ("123µas", "0.000123\""),
    ("123uas", "0.000123\""),
    ("123 arcminutes", "123'"),
    ("123 arcseconds", "123\""),
    ("123 arcminute", "123'"),
    ("123 arcsecond", "123\""),
    ("123 arcmin", "123'"),
    ("123 arcsec", "123\""),
    ("123 amin", "123'"),
    ("123 asec", "123\""),
    ("123 deg", "123deg"),
    ("123 degree", "123deg"),
    ("123 degrees", "123deg"),
    ("123", "123\""),
    ("123\"", "123\""),
    ("123'", "123'"),
    ("123 milliarcseconds", "0.123\""),
    ("123 milliarcsecond", "0.123\""),
    ("123 milliarcsec", "0.123\""),
    ("123 mas", "0.123\""),
    ("123 microarcseconds", "0.000123\""),
    ("123 microarcsecond", "0.000123\""),
    ("123 microarcsec", "0.000123\""),
    ("123 µas", "0.000123\""),
    ("123 uas", "0.000123\""),
])
def test_angular_size_normalized(size, norm):
    assert AngularSize.normalized(size) == norm


@pytest.mark.parametrize("size", ["123cm", "abc", "-123", "123px"])
def test_angular_size_normalized_invalid(size):
    with pytest.raises(ValueError) as e:
        AngularSize.normalized(size)
    assert "not in a recognized angular size format" in str(e.value)


@pytest.mark.parametrize("coord,valid", [
    ("123deg", True),
    ("123degree", True),
    ("123degrees", True),
    ("123 deg", True),
    ("123 degree", True),
    ("123 degrees", True),
    ("123", True),
    ("12:34:56.789", True),
    ("12:34:56.789", True),
    ("12h34m56.789s", True),
    ("12d34m56.789s", True),
    ("12h34m56s", True),
    ("12h34m", True),
    ("34m56.789s", True),
    ("12h", True),
    ("34m", True),
    ("56.789s", True),
    ("12h56.789s", True),
    ("", True),
    ("12d34m56s", True),
    ("12d34m", True),
    ("34m56.789s", True),
    ("12d", True),
    ("34m", True),
    ("56.789s", True),
    ("12d56.789s", True),
    ("", True),
    ("123d", True),
    ("123abc", False),
    ("abc", False),
    ("12:345:67", False),
    ("12:34:567", False),
    ("12:34", False),
    ("hms", False),
    ("hm", False),
    ("ms", False),
    ("h", False),
    ("m", False),
    ("s", False),
    ("hs", False),
    ("12hms", False),
    ("12h34ms", False),
    ("h12m34s", False),
    ("100h", False),
    ("12:34:56,7", False),
])
def test_world_coordinate_valid(coord, valid):
    assert WorldCoordinate.valid(coord) == valid


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
def test_world_coordinate_from_string(coord, fmt, norm):
    assert str(WorldCoordinate.with_format(fmt).from_string(coord)) == norm


@pytest.mark.parametrize("coord,fmt", [
    ("123deg", NF.HMS),
    ("12:34:56.789", NF.DEGREES),
    ("123:45:67", NF.HMS),
    ("123h45m67s", NF.HMS),
    ("123d45m67s", NF.HMS),
])
def test_world_coordinate_normalized_invalid(coord, fmt):
    with pytest.raises(ValueError) as e:
        WorldCoordinate.with_format(fmt).from_string(coord)
    assert "does not match expected format" in str(e.value)
