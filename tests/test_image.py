import types
import pytest

from carta.session import Session
from carta.image import Image
from carta.util import CartaValidationFailed
from carta.constants import NumberFormat as NF, SpatialAxis as SA


# FIXTURES


@pytest.fixture
def session():
    """Return a session object.

    The session's protocol is set to None, so any tests that use this must also mock the session's call_action and/or higher-level functions which call it.
    """
    return Session(0, None)


@pytest.fixture
def image(session):
    """Return an image object which uses the session fixture.
    """
    return Image(session, 0)


@pytest.fixture
def get_value(image, mocker):
    """Return a mock for image's get_value."""
    return mocker.patch.object(image, "get_value")


@pytest.fixture
def call_action(image, mocker):
    """Return a mock for image's call_action."""
    return mocker.patch.object(image, "call_action")


@pytest.fixture
def session_call_action(session, mocker):
    """Return a mock for session's call_action."""
    return mocker.patch.object(session, "call_action")


@pytest.fixture
def property_(mocker):
    """Return a helper function to mock the value of a decorated image property using a simple syntax."""
    def func(property_name, mock_value):
        return mocker.patch(f"carta.image.Image.{property_name}", new_callable=mocker.PropertyMock, return_value=mock_value)
    return func


@pytest.fixture
def method(image, mocker):
    """Return a helper function to mock the return value(s) of an image method using a simple syntax."""
    def func(method_name, return_values):
        return mocker.patch.object(image, method_name, side_effect=return_values)
    return func


@pytest.fixture
def session_method(session, mocker):
    """Return a helper function to mock the return value(s) of a session method using a simple syntax."""
    def func(method_name, return_values):
        return mocker.patch.object(session, method_name, side_effect=return_values)
    return func

# TESTS

# DOCSTRINGS


def test_image_class_has_docstring():
    assert Image.__doc__ is not None


def find_members(*classes, member_type=types.FunctionType):
    for clazz in classes:
        for name in dir(clazz):
            if not name.startswith('__') and isinstance(getattr(clazz, name), member_type):
                yield getattr(clazz, name)


@pytest.mark.parametrize("member", find_members(Image))
def test_image_methods_have_docstrings(member):
    assert member.__doc__ is not None


@pytest.mark.parametrize("member", find_members(Image, member_type=types.MethodType))
def test_image_classmethods_have_docstrings(member):
    assert member.__doc__ is not None


@pytest.mark.parametrize("member", [m.fget for m in find_members(Image, member_type=property)])
def test_image_properties_have_docstrings(member):
    assert member.__doc__ is not None


# CREATING AN IMAGE

@pytest.mark.parametrize("args,kwargs,expected_params", [
    # Open a plain image
    (["subdir", "image.fits", "", False, False], {},
     ["openFile", "/my_data/subdir", "image.fits", "", False, False]),
    # Open an expression
    (["subdir", '2*image.fits', "", False, True], {},
     ["openFile", "/my_data/subdir", '2*image.fits', "", True, False]),
    # Append a plain image
    (["subdir", "image.fits", "", True, False], {},
     ["appendFile", "/my_data/subdir", "image.fits", "", False, True, False]),
    # Append an expression
    (["subdir", "2*image.fits", "", True, True], {},
     ["appendFile", "/my_data/subdir", "2*image.fits", "", True, True, False]),
    # Open a plain image; update the file browser directory
    (["subdir", "image.fits", "", False, False], {"update_directory": True},
     ["openFile", "/my_data/subdir", "image.fits", "", False, True]),
    # Append a plain image; don't set it to active
    (["subdir", "image.fits", "", True, False], {"make_active": False},
     ["appendFile", "/my_data/subdir", "image.fits", "", False, False, False]),
])
def test_new(session, session_call_action, session_method, args, kwargs, expected_params):
    session_method("pwd", ["/my_data"])
    session_call_action.side_effect = [123]

    image_object = Image.new(session, *args, **kwargs)

    session_call_action.assert_called_with(*expected_params, return_path='frameInfo.fileId')

    assert type(image_object) is Image
    assert image_object.session == session
    assert image_object.image_id == 123


# SUBOBJECTS


@pytest.mark.parametrize("name,classname", [
    ("vectors", "VectorOverlay"),
])
def test_subobjects(image, name, classname):
    assert getattr(image, name).__class__.__name__ == classname


# SIMPLE PROPERTIES TODO to be completed.

@pytest.mark.parametrize("property_name,expected_path", [
    ("file_name", "frameInfo.fileInfo.name"),
    ("directory", "frameInfo.directory"),
    ("width", "frameInfo.fileInfoExtended.width"),
])
def test_simple_properties(image, property_name, expected_path, get_value):
    getattr(image, property_name)
    get_value.assert_called_with(expected_path)

# TODO tests for all existing functions to be filled in


def test_make_active(image, session_call_action):
    image.make_active()
    session_call_action.assert_called_with("setActiveFrameById", 0)


@pytest.mark.parametrize("channel", [0, 10, 19])
def test_set_channel_valid(image, channel, call_action, property_):
    property_("depth", 20)

    image.set_channel(channel)
    call_action.assert_called_with("setChannels", channel, image.macro("", "requiredStokes"), True)


@pytest.mark.parametrize("channel,error_contains", [
    (20, "must be smaller"),
    (1.5, "not an increment of 1"),
    (-3, "must be greater or equal"),
])
def test_set_channel_invalid(image, channel, error_contains, property_):
    property_("depth", 20)

    with pytest.raises(CartaValidationFailed) as e:
        image.set_channel(channel)
    assert error_contains in str(e.value)


@pytest.mark.parametrize("x", [-30, 0, 10, 12.3, 30])
@pytest.mark.parametrize("y", [-30, 0, 10, 12.3, 30])
def test_set_center_valid_pixels(image, property_, call_action, x, y):
    # Currently we have no range validation, for consistency with WCS coordinates.
    property_("width", 20)
    property_("height", 20)

    image.set_center(x, y)
    call_action.assert_called_with("setCenter", x, y)


@pytest.mark.parametrize("x,y,x_fmt,y_fmt,x_norm,y_norm", [
    ("123", "12", NF.DEGREES, NF.DEGREES, "123", "12"),
    ("123deg", "12 deg", NF.DEGREES, NF.DEGREES, "123", "12"),
    ("12:34:56.789", "12:34:56.789", NF.HMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
    ("12h34m56.789s", "12d34m56.789s", NF.HMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
    ("12h34m56.789s", "5h34m56.789s", NF.HMS, NF.HMS, "12:34:56.789", "5:34:56.789"),
    ("12d34m56.789s", "12d34m56.789s", NF.DMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
])
def test_set_center_valid_wcs(image, property_, session_method, call_action, x, y, x_fmt, y_fmt, x_norm, y_norm):
    property_("valid_wcs", True)
    session_method("number_format", [(x_fmt, y_fmt, None)])

    image.set_center(x, y)
    call_action.assert_called_with("setCenterWcs", x_norm, y_norm)


@pytest.mark.parametrize("x,y,wcs,x_fmt,y_fmt,error_contains", [
    ("abc", "def", True, NF.DEGREES, NF.DEGREES, "Invalid function parameter"),
    ("123", "123", False, NF.DEGREES, NF.DEGREES, "does not contain valid WCS information"),
    ("123", "123", True, NF.HMS, NF.DMS, "does not match expected format"),
    ("123", "123", True, NF.DEGREES, NF.DMS, "does not match expected format"),
    (123, "123", True, NF.DEGREES, NF.DEGREES, "Cannot mix image and world coordinates"),
    ("123", 123, True, NF.DEGREES, NF.DEGREES, "Cannot mix image and world coordinates"),
])
def test_set_center_invalid(image, property_, session_method, call_action, x, y, wcs, x_fmt, y_fmt, error_contains):
    property_("width", 200)
    property_("height", 200)
    property_("valid_wcs", wcs)
    session_method("number_format", [(x_fmt, y_fmt, None)])

    with pytest.raises(Exception) as e:
        image.set_center(x, y)
    assert error_contains in str(e.value)


@pytest.mark.parametrize("axis", [SA.X, SA.Y])
@pytest.mark.parametrize("val,action,norm", [
    (123, "zoomToSize{0}", 123.0),
    ("123arcsec", "zoomToSize{0}Wcs", "123\""),
    ("123\"", "zoomToSize{0}Wcs", "123\""),
    ("123", "zoomToSize{0}Wcs", "123\""),
    ("123arcmin", "zoomToSize{0}Wcs", "123'"),
    ("123deg", "zoomToSize{0}Wcs", "123deg"),
    ("123 deg", "zoomToSize{0}Wcs", "123deg"),
])
def test_zoom_to_size(image, property_, call_action, axis, val, action, norm):
    property_("valid_wcs", True)
    image.zoom_to_size(val, axis)
    call_action.assert_called_with(action.format(axis.upper()), norm)


@pytest.mark.parametrize("axis", [SA.X, SA.Y])
@pytest.mark.parametrize("val,wcs,error_contains", [
    ("123px", True, "Invalid function parameter"),
    ("abc", True, "Invalid function parameter"),
    ("123arcsec", False, "does not contain valid WCS information"),
])
def test_zoom_to_size_invalid(image, property_, axis, val, wcs, error_contains):
    property_("valid_wcs", wcs)
    with pytest.raises(Exception) as e:
        image.zoom_to_size(val, axis)
    assert error_contains in str(e.value)
