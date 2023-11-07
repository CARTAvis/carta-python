import pytest

from carta.util import CartaValidationFailed
from carta.wcs_overlay import WCSOverlay
from carta.constants import NumberFormat as NF, Overlay as O, CoordinateSystem as CS


# FIXTURES


@pytest.fixture
def overlay(session):
    return WCSOverlay(session)


@pytest.fixture
def get_value(overlay, mock_get_value):
    return mock_get_value(overlay)


@pytest.fixture
def component_get_value(overlay, mocker):
    def func(component, mock_value=None):
        return mocker.patch.object(overlay._components[component], "get_value", return_value=mock_value)
    return func


@pytest.fixture
def call_action(overlay, mock_call_action):
    return mock_call_action(overlay)


@pytest.fixture
def component_call_action(overlay, mock_call_action):
    def func(component):
        return mock_call_action(overlay._components[component])
    return func


@pytest.fixture
def method(overlay, mock_method):
    return mock_method(overlay)

# TESTS


@pytest.mark.parametrize("system", CS)
def test_set_coordinate_system(overlay, component_call_action, system):
    global_call_action = component_call_action(O.GLOBAL)
    overlay.set_coordinate_system(system)
    global_call_action.assert_called_with("setSystem", system)


def test_set_coordinate_system_invalid(overlay):
    with pytest.raises(CartaValidationFailed) as e:
        overlay.set_coordinate_system("invalid")
    assert "Invalid function parameter" in str(e.value)


def test_coordinate_system(overlay, component_get_value):
    global_get_value = component_get_value(O.GLOBAL, "AUTO")
    system = overlay.coordinate_system
    global_get_value.assert_called_with("system")
    assert isinstance(system, CS)


@pytest.mark.parametrize("x", NF)
@pytest.mark.parametrize("y", NF)
def test_set_custom_number_format(mocker, overlay, component_call_action, x, y):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.set_custom_number_format(x, y)
    numbers_call_action.assert_has_calls([
        mocker.call("setFormatX", x),
        mocker.call("setFormatY", y),
        mocker.call("setCustomFormat", True),
    ])


@pytest.mark.parametrize("x,y", [
    ("invalid", "invalid"),
    (NF.DEGREES, "invalid"),
    ("invalid", NF.DEGREES),
])
def test_set_custom_number_format_invalid(overlay, x, y):
    with pytest.raises(CartaValidationFailed) as e:
        overlay.set_custom_number_format(x, y)
    assert "Invalid function parameter" in str(e.value)


def test_clear_custom_number_format(overlay, component_call_action):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.clear_custom_number_format()
    numbers_call_action.assert_called_with("setCustomFormat", False)


def test_number_format(overlay, component_get_value, mocker):
    numbers_get_value = component_get_value(O.NUMBERS)
    numbers_get_value.side_effect = [NF.DEGREES, NF.DEGREES, False]
    x, y, _ = overlay.number_format
    numbers_get_value.assert_has_calls([
        mocker.call("formatTypeX"),
        mocker.call("formatTypeY"),
        mocker.call("customFormat"),
    ])
    assert isinstance(x, NF)
    assert isinstance(y, NF)
