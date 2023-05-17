import types
import pytest

from carta.session import Session
from carta.util import CartaValidationFailed
from carta.constants import CoordinateSystem, NumberFormat as NF

# FIXTURES


@pytest.fixture
def session():
    """Return a session object.

    The session's protocol is set to None, so any tests that use this must also mock the session's call_action and/or higher-level functions which call it.
    """
    return Session(0, None)


@pytest.fixture
def mock_get_value(session, mocker):
    """Return a mock for session's get_value."""
    return mocker.patch.object(session, "get_value")


@pytest.fixture
def mock_call_action(session, mocker):
    """Return a mock for session's call_action."""
    return mocker.patch.object(session, "call_action")


@pytest.fixture
def mock_property(mocker):
    """Return a helper function to mock the value of a decorated session property using a simple syntax."""
    def func(property_name, mock_value):
        mocker.patch(f"carta.session.Session.{property_name}", new_callable=mocker.PropertyMock, return_value=mock_value)
    return func


@pytest.fixture
def mock_method(session, mocker):
    """Return a helper function to mock the return value(s) of an session method using a simple syntax."""
    def func(method_name, return_values):
        mocker.patch.object(session, method_name, side_effect=return_values)
    return func


# TESTS


def test_session_class_has_docstring():
    assert Session.__doc__ is not None


def find_members(*classes, member_type=types.FunctionType):
    for clazz in classes:
        for name in dir(clazz):
            if not name.startswith('__') and isinstance(getattr(clazz, name), member_type):
                yield getattr(clazz, name)


@pytest.mark.parametrize("member", find_members(Session))
def test_session_methods_have_docstrings(member):
    assert member.__doc__ is not None


@pytest.mark.parametrize("member", find_members(Session, member_type=types.MethodType))
def test_session_classmethods_have_docstrings(member):
    assert member.__doc__ is not None


# TODO fill in missing session tests


@pytest.mark.parametrize("system", CoordinateSystem)
def test_set_coordinate_system(session, mock_call_action, system):
    session.set_coordinate_system(system)
    mock_call_action.assert_called_with("overlayStore.global.setSystem", system)


def test_set_coordinate_system_invalid(session):
    with pytest.raises(CartaValidationFailed) as e:
        session.set_coordinate_system("invalid")
    assert "Invalid function parameter" in str(e.value)

def test_coordinate_system(session, mock_get_value):
    mock_get_value.return_value = "AUTO"
    system = session.coordinate_system()
    mock_get_value.assert_called_with("overlayStore.global.system")
    assert isinstance(system, CoordinateSystem)

@pytest.mark.parametrize("x", NF)
@pytest.mark.parametrize("y", NF)
def test_set_custom_number_format(mocker, session, mock_call_action, x, y):
    session.set_custom_number_format(x, y)
    mock_call_action.assert_has_calls([
        mocker.call("overlayStore.numbers.setXFormat", x),
        mocker.call("overlayStore.numbers.setYFormat", y),
        mocker.call("overlayStore.numbers.setCustomFormat", True),
    ])


@pytest.mark.parametrize("x,y", [
    ("invalid", "invalid"),
    (NF.DEGREES, "invalid"),
    ("invalid", NF.DEGREES),
])
def test_set_custom_number_format_invalid(session, x, y):
    with pytest.raises(CartaValidationFailed) as e:
        session.set_custom_number_format(x, y)
    assert "Invalid function parameter" in str(e.value)


def test_clear_custom_number_format(session, mock_call_action):
    session.clear_custom_number_format()
    mock_call_action.assert_called_with("overlayStore.numbers.setCustomFormat", False)

def test_number_system(session, mock_get_value, mocker):
    session.number_format()
    mock_get_value.assert_has_calls([
        mocker.call("overlayStore.numbers.formatTypeX"),
        mocker.call("overlayStore.numbers.formatTypeY"),
        mocker.call("overlayStore.numbers.customFormat"),
    ])
