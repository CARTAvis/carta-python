import pytest

from carta.session import Session
from carta.image import Image
from carta.util import CartaValidationFailed


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


@pytest.mark.parametrize("channel,error_contains", [(20, "must be smaller"), (1.5, "not an increment of 1"), (-3, "must be greater or equal")])
def test_set_channel_invalid(image, channel, error_contains, mock_property):
    mock_property("depth", 20)

    with pytest.raises(CartaValidationFailed) as e:
        image.set_channel(channel)
        assert error_contains in e


@pytest.mark.parametrize("x", [0, 10, 19])
@pytest.mark.parametrize("y", [0, 10, 19])
def test_set_center_valid_pixels(image, mock_property, mock_call_action, x, y):
    mock_property("width", 20)
    mock_property("height", 20)

    image.set_center(f"{x}px", f"{y}px")
    mock_call_action.assert_called_with("setCenter", x, y)


@pytest.mark.parametrize("x,y,x_fmt,y_fmt,x_norm,y_norm", [
    ("123", "123", "d", "d", "123.0", "123.0"),
    (123, 123, "d", "d", "123.0", "123.0"),
    ("123deg", "123 deg", "d", "d", "123", "123"),
    ("12:34:56.789", "12:34:56.789", "hms", "dms", "12:34:56.789", "12:34:56.789"),
    ("12h34m56.789s", "12d34m56.789s", "hms", "dms", "12:34:56.789", "12:34:56.789"),
])
def test_set_center_valid_wcs(image, mock_property, mock_session_method, mock_call_action, x, y, x_fmt, y_fmt, x_norm, y_norm):
    mock_property("valid_wcs", True)
    mock_session_method("get_overlay_value", [x_fmt, y_fmt])

    image.set_center(x, y)
    mock_call_action.assert_called_with("setCenterWcs", x_norm, y_norm)

# def test_set_center_valid_wcs_change_system():
    # pass

# def test_set_center_invalid():
    # pass # validation failure, wrong format, no wcs info, xy mismatch, pixels outside image
