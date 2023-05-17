import pytest

from carta.session import Session
from carta.image import Image
from carta.util import CartaValidationFailed
from carta.constants import NumberFormat as NF, CoordinateSystem

# FIXTURES


@pytest.fixture
def session():
    return Session(0, None)


@pytest.fixture
def image(session):
    return Image(session, 0, "")


@pytest.fixture
def mock_get_value(image, mocker):
    return mocker.patch.object(image, "get_value")


@pytest.fixture
def mock_call_action(image, mocker):
    return mocker.patch.object(image, "call_action")


@pytest.fixture
def mock_session_call_action(session, mocker):
    return mocker.patch.object(session, "call_action")


@pytest.fixture
def mock_property(mocker):
    def func(property_name, mock_value):
        mocker.patch(f"carta.image.Image.{property_name}", new_callable=mocker.PropertyMock, return_value=mock_value)
    return func


@pytest.fixture
def mock_method(image, mocker):
    def func(method_name, return_values):
        mocker.patch.object(image, method_name, side_effect=return_values)
    return func


@pytest.fixture
def mock_session_method(session, mocker):
    def func(method_name, return_values):
        mocker.patch.object(session, method_name, side_effect=return_values)
    return func

# TESTS


@pytest.mark.parametrize("property_name,expected_path", [
    ("directory", "frameInfo.directory"),
    ("width", "frameInfo.fileInfoExtended.width"),
])
def test_simple_parameters(image, property_name, expected_path, mock_get_value):
    getattr(image, property_name)
    mock_get_value.assert_called_with(expected_path)


def test_make_active(image, mock_session_call_action):
    image.make_active()
    mock_session_call_action.assert_called_with("setActiveFrameById", 0)


@pytest.mark.parametrize("channel", [0, 10, 19])
def test_set_channel_valid(image, channel, mock_call_action, mock_property):
    mock_property("depth", 20)

    image.set_channel(channel)
    mock_call_action.assert_called_with("setChannels", channel, image.macro("", "requiredStokes"), True)


@pytest.mark.parametrize("channel,error_contains", [
    (20, "must be smaller"),
    (1.5, "not an increment of 1"),
    (-3, "must be greater or equal"),
])
def test_set_channel_invalid(image, channel, error_contains, mock_property):
    mock_property("depth", 20)

    with pytest.raises(CartaValidationFailed) as e:
        image.set_channel(channel)
    assert error_contains in str(e.value)


@pytest.mark.parametrize("x", [0, 10, 19])
@pytest.mark.parametrize("y", [0, 10, 19])
def test_set_center_valid_pixels(image, mock_property, mock_call_action, x, y):
    mock_property("width", 20)
    mock_property("height", 20)

    image.set_center(f"{x}px", f"{y}px")
    mock_call_action.assert_called_with("setCenter", x, y)


@pytest.mark.parametrize("x,y,x_fmt,y_fmt,x_norm,y_norm", [
    ("123", "123", NF.DEGREES, NF.DEGREES, "123", "123"),
    (123, 123, NF.DEGREES, NF.DEGREES, "123", "123"),
    ("123deg", "123 deg", NF.DEGREES, NF.DEGREES, "123", "123"),
    ("12:34:56.789", "12:34:56.789", NF.HMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
    ("12h34m56.789s", "12d34m56.789s", NF.HMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
])
def test_set_center_valid_wcs(image, mock_property, mock_session_method, mock_call_action, x, y, x_fmt, y_fmt, x_norm, y_norm):
    mock_property("valid_wcs", True)
    mock_session_method("get_overlay_value", [x_fmt, y_fmt])

    image.set_center(x, y)
    mock_call_action.assert_called_with("setCenterWcs", x_norm, y_norm)


def test_set_center_valid_change_system(image, mock_property, mock_session_method, mock_call_action, mock_session_call_action):
    mock_property("valid_wcs", True)
    mock_session_method("get_overlay_value", [NF.DEGREES, NF.DEGREES])

    image.set_center("123", "123", CoordinateSystem.GALACTIC)

    # We're not testing if this system has the correct format; just that the function is called
    mock_session_call_action.assert_called_with("overlayStore.global.setSystem", CoordinateSystem.GALACTIC)
    mock_call_action.assert_called_with("setCenterWcs", "123", "123")


@pytest.mark.parametrize("x,y,wcs,x_fmt,y_fmt,error_contains", [
    ("abc", "def", True, NF.DEGREES, NF.DEGREES, "Invalid function parameter"),
    ("123", "123", False, NF.DEGREES, NF.DEGREES, "does not contain valid WCS information"),
    ("123", "123", True, NF.HMS, NF.DMS, "X coordinate does not match expected format"),
    ("123", "123", True, NF.DEGREES, NF.DMS, "Y coordinate does not match expected format"),
    ("123px", "123", True, NF.DEGREES, NF.DEGREES, "Cannot mix image and world coordinates"),
    ("123", "123px", True, NF.DEGREES, NF.DEGREES, "Cannot mix image and world coordinates"),
    ("123px", "2000px", True, NF.DEGREES, NF.DEGREES, "outside the bounds of the image"),
    ("2000px", "123px", True, NF.DEGREES, NF.DEGREES, "outside the bounds of the image"),
])
def test_set_center_invalid(image, mock_property, mock_session_method, mock_call_action, x, y, wcs, x_fmt, y_fmt, error_contains):
    mock_property("width", 200)
    mock_property("height", 200)
    mock_property("valid_wcs", wcs)
    mock_session_method("get_overlay_value", [x_fmt, y_fmt])

    with pytest.raises(Exception) as e:
        image.set_center(x, y)
    assert error_contains in str(e.value)
