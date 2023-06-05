import types
import pytest

from carta.util import PixelValue, AngularSize, WorldCoordinate, DegreesCoordinate, HMSCoordinate, DMSCoordinate
from carta.constants import NumberFormat as NF, SpatialAxis as SA


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
    ("123′", True),
    ("123″", True),
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
    ("123″", "123\""),
    ("123′", "123'"),
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
def test_angular_size_from_string(size, norm):
    assert str(AngularSize.from_string(size)) == norm


@pytest.mark.parametrize("size", ["123cm", "abc", "-123", "123px"])
def test_angular_size_from_string_invalid(size):
    with pytest.raises(ValueError) as e:
        AngularSize.from_string(size)
    assert "not in a recognized angular size format" in str(e.value)


@pytest.mark.parametrize("coord,valid", [
    ("0deg", True),
    ("123 degrees", True),
    ("123degrees", True),
    ("123 degree", True),
    ("123degree", True),
    ("123 deg", True),
    ("123deg", True),
    ("123", True),
    ("1deg", True),

    ("12:34:56.789", False),
    ("123abc", False),
    ("12d34m56.789s", False),
    ("12h34m56.789s", False),
    ("abc", False),
])
def test_degrees_coordinate_valid(coord, valid):
    assert DegreesCoordinate.valid(coord) == valid

@pytest.mark.parametrize("coord,valid", [
    ("00:00:00.0", True),
    ("00:00:00", True),
    ("0:00:00", True),
    ("-12:34:56.789", True),
    ("12:34:56.789", True),
    ("12:34:56", True),
    ("12h04m05s", True),
    ("-12h34m56.789s", True),
    ("12h34m56.789s", True),
    ("12h34m56s", True),
    
    ("100:00:00", False),
    ("10:00:60", False),
    ("10:00:65", False),
    ("10:60:00", False),
    ("10:65:00", False),
    ("12:34:56,7", False),
    ("12:34:567", False),
    ("12:345:67", False),
    ("12:34", False),
    ("123abc", False),
    ("1:2:3", False),
    ("12d34m56.789s", False),
    ("12h34m", False),
    ("12m34s", False),
    ("24:00:00", False),
    ("30:00:00", False),
    ("abc", False),
])
def test_hms_coordinate_valid(coord, valid):
    assert HMSCoordinate.valid(coord) == valid


@pytest.mark.parametrize("coord,valid", [
    ("00:00:00.0", True),
    ("00:00:00", True),
    ("0:00:00", True),
    ("100:00:00", True),
    ("-12:34:56.789", True),
    ("12:34:56.789", True),
    ("12:34:56", True),
    ("12d04m05s", True),
    ("-12d34m56.789s", True),
    ("12d34m56.789s", True),
    ("12d34m56s", True),
    ("360:00:00", True),
    ("400:00:00", True),
    
    ("10:00:60", False),
    ("10:00:65", False),
    ("10:60:00", False),
    ("10:65:00", False),
    ("12:34:56,7", False),
    ("12:34:567", False),
    ("12:345:67", False),
    ("12:34", False),
    ("123abc", False),
    ("1:2:3", False),
    ("12d34m", False),
    ("12h34m56.789s", False),
    ("12m34s", False),
    ("abc", False),
])
def test_dms_coordinate_valid(coord, valid):
    assert DMSCoordinate.valid(coord) == valid


def test_world_coordinate_valid(mocker):
    degrees_valid = mocker.patch.object(DegreesCoordinate, "valid", return_value=True)
    hms_valid = mocker.patch.object(HMSCoordinate, "valid", return_value=True)
    dms_valid = mocker.patch.object(DMSCoordinate, "valid", return_value=True)
    
    assert WorldCoordinate.valid("example") # Valid because first child returned true
    
    degrees_valid.assert_called_with("example") # First child should have been called
    assert not hms_valid.called # Subsequent children not called because any short-circuits
    assert not dms_valid.called


def test_world_coordinate_invalid(mocker):
    degrees_valid = mocker.patch.object(DegreesCoordinate, "valid", return_value=False)
    hms_valid = mocker.patch.object(HMSCoordinate, "valid", return_value=False)
    dms_valid = mocker.patch.object(DMSCoordinate, "valid", return_value=False)
    
    assert not WorldCoordinate.valid("example") # Invalid because all children returned false
    
    degrees_valid.assert_called_with("example") # All children should have been called
    hms_valid.assert_called_with("example")
    dms_valid.assert_called_with("example")
    

#@pytest.mark.parametrize("coord,axis,fmt,norm", [
#])
#def test_degrees_coordinate_from_string(coord, axis, fmt, norm):
    #assert str(DegreesCoordinate.with_format(fmt).from_string(coord, axis)) == norm


#@pytest.mark.parametrize("coord,axis,fmt,error", [
#])
#def test_degrees_coordinate_from_string_invalid(coord, axis, fmt, norm):
    #assert str(DegreesCoordinate.with_format(fmt).from_string(coord, axis)) == norm



# TODO: this needs a complete refactoring. Use the individual subclasses.

#@pytest.mark.parametrize("axis", [SA.X, SA.Y])
#@pytest.mark.parametrize("coord,fmt,norm", [
    #("123deg", NF.DEGREES, "123"),
    #("123degree", NF.DEGREES, "123"),
    #("123degrees", NF.DEGREES, "123"),
    #("123 deg", NF.DEGREES, "123"),
    #("123 degree", NF.DEGREES, "123"),
    #("123 degrees", NF.DEGREES, "123"),
    #("123", NF.DEGREES, "123"),
    #("12:34:56.789", NF.HMS, "12:34:56.789"),
    #("12:34:56.789", NF.DMS, "12:34:56.789"),
    #("12h34m56.789s", NF.HMS, "12:34:56.789"),
    #("12d34m56.789s", NF.DMS, "12:34:56.789"),
    #("12h34m56s", NF.HMS, "12:34:56"),
    #("12h34m", NF.HMS, "12:34:"),
    #("34m56.789s", NF.HMS, ":34:56.789"),
    #("12h", NF.HMS, "12::"),
    #("34m", NF.HMS, ":34:"),
    #("56.789s", NF.HMS, "::56.789"),
    #("12h56.789s", NF.HMS, "12::56.789"),
    #("", NF.HMS, "::"),
    #("12d34m56s", NF.DMS, "12:34:56"),
    #("12d34m", NF.DMS, "12:34:"),
    #("34m56.789s", NF.DMS, ":34:56.789"),
    #("12d", NF.DMS, "12::"),
    #("34m", NF.DMS, ":34:"),
    #("56.789s", NF.DMS, "::56.789"),
    #("12d56.789s", NF.DMS, "12::56.789"),
    #("", NF.DMS, "::"),
    #("123d", NF.DMS, "123::"),
#])
#def test_world_coordinate_from_string_both_axes(coord, axis, fmt, norm):
    #assert str(WorldCoordinate.with_format(fmt).from_string(coord, axis)) == norm


#@pytest.mark.parametrize("coord,axis,fmt,norm", [
    
#])
#def test_world_coordinate_from_string_one_axis(coord, axis, fmt, norm):
    #assert str(WorldCoordinate.with_format(fmt).from_string(coord, axis)) == norm


#@pytest.mark.parametrize("axis", [SA.X, SA.Y])
#@pytest.mark.parametrize("coord,fmt", [
    #("123deg", NF.HMS),
    #("12:34:56.789", NF.DEGREES),
    #("123:45:67", NF.HMS),
    #("123h45m67s", NF.HMS),
    #("123d45m67s", NF.HMS),
#])
#def test_world_coordinate_from_string_invalid_both_axes(coord, axis, fmt):
    #with pytest.raises(ValueError) as e:
        #WorldCoordinate.with_format(fmt).from_string(coord, axis)
    #assert any((
            #"does not match expected format" in str(e.value),
            #"has invalid" in str(e.value)
            #))


#@pytest.mark.parametrize("coord,axis,fmt", [
    #("", SA.X, NF.DEGREES),
    #("", SA.X, NF.DEGREES),
    #("", SA.Y, NF.DEGREES),
    #("", SA.Y, NF.DEGREES),
    #("", SA.Y, NF.DEGREES),
#])
#def test_world_coordinate_from_string_invalid(coord, axis, fmt):
    #with pytest.raises(ValueError) as e:
        #WorldCoordinate.with_format(fmt).from_string(coord)
    #assert 
