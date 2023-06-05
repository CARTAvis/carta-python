import types
import pytest

from carta.util import PixelValue, AngularSize, DegreesSize, ArcminSize, ArcsecSize, MilliarcsecSize, MicroarcsecSize, WorldCoordinate, DegreesCoordinate, HMSCoordinate, DMSCoordinate
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
    ("123deg", True),
    ("123degree", True),
    ("123degrees", True),
    ("123 deg", True),
    ("123 degree", True),
    ("123 degrees", True),

    ("123 arcmin", False),
    ("123cm", False),
    ("abc", False),
    ("-123", False),
    ("123px", False),
])
def test_degrees_size_valid(size, valid):
    assert DegreesSize.valid(size) == valid
    if valid:
        assert AngularSize.valid(size) == valid


@pytest.mark.parametrize("size,valid", [
    ("123arcminutes", True),
    ("123arcminute", True),
    ("123arcmin", True),
    ("123amin", True),
    ("123 arcminutes", True),
    ("123 arcminute", True),
    ("123 arcmin", True),
    ("123 amin", True),
    ("123'", True),
    ("123′", True),

    ("123 degrees", False),
    ("123cm", False),
    ("abc", False),
    ("-123", False),
    ("123px", False),
])
def test_arcmin_size_valid(size, valid):
    assert ArcminSize.valid(size) == valid
    if valid:
        assert AngularSize.valid(size) == valid


@pytest.mark.parametrize("size,valid", [
    ("123arcseconds", True),
    ("123arcsecond", True),
    ("123arcsec", True),
    ("123asec", True),
    ("123 arcseconds", True),
    ("123 arcsecond", True),
    ("123 arcsec", True),
    ("123 asec", True),
    ("123", True),
    ("123\"", True),
    ("123″", True),

    ("123 degrees", False),
    ("123cm", False),
    ("abc", False),
    ("-123", False),
    ("123px", False),
])
def test_arcsec_size_valid(size, valid):
    assert ArcsecSize.valid(size) == valid
    if valid:
        assert AngularSize.valid(size) == valid


@pytest.mark.parametrize("size,valid", [
    ("123milliarcseconds", True),
    ("123milliarcsecond", True),
    ("123milliarcsec", True),
    ("123mas", True),
    ("123 milliarcseconds", True),
    ("123 milliarcsecond", True),
    ("123 milliarcsec", True),
    ("123 mas", True),

    ("123 degrees", False),
    ("123cm", False),
    ("abc", False),
    ("-123", False),
    ("123px", False),
])
def test_milliarcsec_size_valid(size, valid):
    assert MilliarcsecSize.valid(size) == valid
    if valid:
        assert AngularSize.valid(size) == valid


@pytest.mark.parametrize("size,valid", [
    ("123microarcseconds", True),
    ("123microarcsecond", True),
    ("123microarcsec", True),
    ("123µas", True),
    ("123uas", True),
    ("123 microarcseconds", True),
    ("123 microarcsecond", True),
    ("123 microarcsec", True),
    ("123 µas", True),
    ("123 uas", True),

    ("123 degrees", False),
    ("123cm", False),
    ("abc", False),
    ("-123", False),
    ("123px", False),
])
def test_microarcsec_size_valid(size, valid):
    assert MicroarcsecSize.valid(size) == valid
    if valid:
        assert AngularSize.valid(size) == valid


@pytest.mark.parametrize("size,norm", [
    ("123arcminutes", "123'"),
    ("123arcminute", "123'"),
    ("123arcmin", "123'"),
    ("123amin", "123'"),
    ("123 arcminutes", "123'"),
    ("123 arcminute", "123'"),
    ("123 arcmin", "123'"),
    ("123 amin", "123'"),
    ("123'", "123'"),
    ("123′", "123'"),
])
def test_arcmin_size_from_string(size, norm):
    assert str(ArcminSize.from_string(size)) == norm
    assert str(AngularSize.from_string(size)) == norm


@pytest.mark.parametrize("size,norm", [
    ("123arcseconds", "123\""),
    ("123arcsecond", "123\""),
    ("123arcsec", "123\""),
    ("123asec", "123\""),
    ("123 arcseconds", "123\""),
    ("123 arcsecond", "123\""),
    ("123 arcsec", "123\""),
    ("123 asec", "123\""),
    ("123", "123\""),
    ("123\"", "123\""),
    ("123″", "123\""),
])
def test_arcsec_size_from_string(size, norm):
    assert str(ArcsecSize.from_string(size)) == norm
    assert str(AngularSize.from_string(size)) == norm


@pytest.mark.parametrize("size,norm", [
    ("123deg", "123deg"),
    ("123degree", "123deg"),
    ("123degrees", "123deg"),
    ("123 deg", "123deg"),
    ("123 degree", "123deg"),
    ("123 degrees", "123deg"),
])
def test_degrees_size_from_string(size, norm):
    assert str(DegreesSize.from_string(size)) == norm
    assert str(AngularSize.from_string(size)) == norm


@pytest.mark.parametrize("size,norm", [
    ("123milliarcseconds", "0.123\""),
    ("123milliarcsecond", "0.123\""),
    ("123milliarcsec", "0.123\""),
    ("123mas", "0.123\""),
    ("123 milliarcseconds", "0.123\""),
    ("123 milliarcsecond", "0.123\""),
    ("123 milliarcsec", "0.123\""),
    ("123 mas", "0.123\""),
])
def test_milliarcsec_size_from_string(size, norm):
    assert str(MilliarcsecSize.from_string(size)) == norm
    assert str(AngularSize.from_string(size)) == norm


@pytest.mark.parametrize("size,norm", [
    ("123microarcseconds", "0.000123\""),
    ("123microarcsecond", "0.000123\""),
    ("123microarcsec", "0.000123\""),
    ("123µas", "0.000123\""),
    ("123uas", "0.000123\""),
    ("123 microarcseconds", "0.000123\""),
    ("123 microarcsecond", "0.000123\""),
    ("123 microarcsec", "0.000123\""),
    ("123 µas", "0.000123\""),
    ("123 uas", "0.000123\""),
])
def test_microarcsec_size_from_string(size, norm):
    assert str(MicroarcsecSize.from_string(size)) == norm
    assert str(AngularSize.from_string(size)) == norm


@pytest.mark.parametrize("clazz,size", [
    (DegreesSize, "123arcsec"),
    (ArcminSize, "123degrees"),
    (ArcsecSize, "123degrees"),
    (MilliarcsecSize, "123degrees"),
    (MicroarcsecSize, "123degrees"),
])
def test_angular_size_from_string_one_invalid(clazz, size):
    with pytest.raises(ValueError) as e:
        clazz.from_string(size)
    assert "not in a recognized" in str(e.value)


@pytest.mark.parametrize("size", ["123cm", "abc", "-123", "123px"])
def test_angular_size_from_string_all_invalid(size):
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
    ("1:2:3", True),
    ("12h34m", True),
    ("12m34s", True),
    ("12h34s", True),
    ("12h", True),
    ("12m", True),
    ("12s", True),
    ("::", True),
    ("", True),

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
    ("12d34m56.789s", False),
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
    ("1:2:3", True),
    ("12d34m", True),
    ("12m34s", True),
    ("12d34s", True),
    ("12d", True),
    ("12m", True),
    ("12s", True),
    ("::", True),
    ("", True),

    ("10:00:60", False),
    ("10:00:65", False),
    ("10:60:00", False),
    ("10:65:00", False),
    ("12:34:56,7", False),
    ("12:34:567", False),
    ("12:345:67", False),
    ("12:34", False),
    ("123abc", False),
    ("12h34m56.789s", False),
    ("abc", False),
])
def test_dms_coordinate_valid(coord, valid):
    assert DMSCoordinate.valid(coord) == valid


def test_world_coordinate_valid(mocker):
    degrees_valid = mocker.patch.object(DegreesCoordinate, "valid", return_value=True)
    hms_valid = mocker.patch.object(HMSCoordinate, "valid", return_value=True)
    dms_valid = mocker.patch.object(DMSCoordinate, "valid", return_value=True)

    assert WorldCoordinate.valid("example")  # Valid because first child returned true

    degrees_valid.assert_called_with("example")  # First child should have been called
    assert not hms_valid.called  # Subsequent children not called because any short-circuits
    assert not dms_valid.called


def test_world_coordinate_invalid(mocker):
    degrees_valid = mocker.patch.object(DegreesCoordinate, "valid", return_value=False)
    hms_valid = mocker.patch.object(HMSCoordinate, "valid", return_value=False)
    dms_valid = mocker.patch.object(DMSCoordinate, "valid", return_value=False)

    assert not WorldCoordinate.valid("example")  # Invalid because all children returned false

    degrees_valid.assert_called_with("example")  # All children should have been called
    hms_valid.assert_called_with("example")
    dms_valid.assert_called_with("example")


@pytest.mark.parametrize("coord,axis,norm,error", [
    ("123", SA.X, "123", None),
    ("400", SA.X, None, "outside the permitted longitude range"),
    ("-123", SA.X, None, "outside the permitted longitude range"),
    ("12", SA.Y, "12", None),
    ("-34.5", SA.Y, "-34.5", None),
    ("123", SA.Y, None, "outside the permitted latitude range"),
    ("-123", SA.Y, None, "outside the permitted latitude range"),
])
def test_degrees_coordinate_from_string(coord, axis, norm, error):
    if norm is not None:
        assert str(DegreesCoordinate.from_string(coord, axis)) == norm
    else:
        with pytest.raises(ValueError) as e:
            DegreesCoordinate.from_string(coord, axis)
        assert error in str(e.value)


@pytest.mark.parametrize("coord,axis,norm,error", [
    ("12:34:56.7", SA.X, "12:34:56.7", None),
    ("-12:34:56.7", SA.X, None, "outside the permitted longitude range"),
    ("5:34:56.7", SA.Y, "5:34:56.7", None),
    ("-5:34:56.7", SA.Y, "-5:34:56.7", None),
    ("12:34:56.7", SA.Y, None, "outside the permitted latitude range"),
    ("-12:34:56.7", SA.Y, None, "outside the permitted latitude range"),
    ("1:2:3", SA.X, "1:02:03", None),
    ("12h34m", SA.X, "12:34:00", None),
    ("12m34s", SA.X, "0:12:34", None),
    ("12h34s", SA.X, "12:00:34", None),
    ("12h", SA.X, "12:00:00", None),
    ("12m", SA.X, "0:12:00", None),
    ("12s", SA.X, "0:00:12", None),
    ("::", SA.X, "0:00:00", None),
    ("", SA.X, "0:00:00", None),
])
def test_hms_coordinate_from_string(coord, axis, norm, error):
    if norm is not None:
        assert str(HMSCoordinate.from_string(coord, axis)) == norm
    else:
        with pytest.raises(ValueError) as e:
            HMSCoordinate.from_string(coord, axis)
        assert error in str(e.value)


@pytest.mark.parametrize("coord,axis,norm,error", [
    ("12:34:56.7", SA.X, "12:34:56.7", None),
    ("400:34:56.7", SA.X, None, "outside the permitted longitude range"),
    ("-12:34:56.7", SA.X, None, "outside the permitted longitude range"),
    ("12:34:56.7", SA.Y, "12:34:56.7", None),
    ("-12:34:56.7", SA.Y, "-12:34:56.7", None),
    ("100:34:56.7", SA.Y, None, "outside the permitted latitude range"),
    ("-100:34:56.7", SA.Y, None, "outside the permitted latitude range"),
    ("1:2:3", SA.X, "1:02:03", None),
    ("12d34m", SA.X, "12:34:00", None),
    ("12m34s", SA.X, "0:12:34", None),
    ("12d34s", SA.X, "12:00:34", None),
    ("12d", SA.X, "12:00:00", None),
    ("12m", SA.X, "0:12:00", None),
    ("12s", SA.X, "0:00:12", None),
    ("::", SA.X, "0:00:00", None),
    ("", SA.X, "0:00:00", None),
])
def test_dms_coordinate_from_string(coord, axis, norm, error):
    if norm is not None:
        assert str(DMSCoordinate.from_string(coord, axis)) == norm
    else:
        with pytest.raises(ValueError) as e:
            DMSCoordinate.from_string(coord, axis)
        assert error in str(e.value)


@pytest.mark.parametrize("fmt,expected_child", [
    (NF.DEGREES, DegreesCoordinate),
    (NF.HMS, HMSCoordinate),
    (NF.DMS, DMSCoordinate),
])
def test_world_coordinate_with_format(fmt, expected_child):
    assert WorldCoordinate.with_format(fmt) == expected_child
