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
        return mocker.patch.object(overlay.components[component], "get_value", return_value=mock_value)
    return func


@pytest.fixture
def call_action(overlay, mock_call_action):
    return mock_call_action(overlay)


@pytest.fixture
def component_call_action(overlay, mock_call_action):
    def func(component):
        return mock_call_action(overlay.components[component])
    return func


@pytest.fixture
def method(overlay, mock_method):
    return mock_method(overlay)

# TESTS


@pytest.mark.parametrize("system", CS)
def test_global_set_coordinate_system(overlay, component_call_action, system):
    global_call_action = component_call_action(O.GLOBAL)
    overlay.global_.set_coordinate_system(system)
    global_call_action.assert_called_with("setSystem", system)


def test_global_set_coordinate_system_invalid(overlay):
    with pytest.raises(CartaValidationFailed) as e:
        overlay.global_.set_coordinate_system("invalid")
    assert "Invalid function parameter" in str(e.value)


def test_global_coordinate_system(overlay, component_get_value):
    global_get_value = component_get_value(O.GLOBAL, "AUTO")
    system = overlay.global_.coordinate_system
    global_get_value.assert_called_with("system")
    assert isinstance(system, CS)


@pytest.mark.parametrize("x", NF)
@pytest.mark.parametrize("y", NF)
def test_numbers_set_format(mocker, overlay, component_call_action, x, y):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.numbers.set_format(x, y)
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
def test_numbers_set_format_invalid(overlay, x, y):
    with pytest.raises(CartaValidationFailed) as e:
        overlay.numbers.set_format(x, y)
    assert "Invalid function parameter" in str(e.value)


@pytest.mark.parametrize("val", [True, False])
def test_numbers_set_custom_format(overlay, component_call_action, val):
    numbers_call_action = component_call_action(O.NUMBERS)
    overlay.numbers.set_custom_format(val)
    numbers_call_action.assert_called_with("setCustomFormat", val)


def test_numbers_format(overlay, component_get_value, mocker):
    numbers_get_value = component_get_value(O.NUMBERS)
    numbers_get_value.side_effect = [NF.DEGREES, NF.DEGREES]
    x, y = overlay.numbers.format
    numbers_get_value.assert_has_calls([
        mocker.call("formatTypeX"),
        mocker.call("formatTypeY"),
    ])
    assert isinstance(x, NF)
    assert isinstance(y, NF)
