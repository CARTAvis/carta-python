import types
import pytest

from carta.session import Session
from carta.image import Image
from carta.util import CartaValidationFailed, Macro
from carta.constants import CoordinateSystem, NumberFormat as NF, ComplexExpression as CE

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

# PATHS

@pytest.mark.parametrize("path, expected_path", [
    ("foo", "/current/dir/foo"),
    ("/foo", "/foo"),
    ("..", "/current"),
    (".", "/current/dir"),
    ("foo/..", "/current/dir"),
    ("foo/../bar", "/current/dir/bar"),
])
def test_resolve_file_path(session, mock_method, path, expected_path):
    mock_method("pwd", ["/current/dir"])
    assert session.resolve_file_path(path) == expected_path


def test_pwd(session, mock_call_action, mock_get_value):
    mock_get_value.side_effect = ["current/dir/"]
    pwd = session.pwd()
    mock_call_action.assert_called_with("fileBrowserStore.getFileList", Macro('fileBrowserStore', 'startingDirectory'))
    mock_get_value.assert_called_with("fileBrowserStore.fileList.directory")
    assert pwd == "/current/dir"


def test_ls(session, mock_method, mock_call_action, mock_get_value):
    mock_method("pwd", ["/current/dir"])
    mock_get_value.side_effect = [{"files": [{"name": "foo.fits"}, {"name": "bar.fits"}], "subdirectories": [{"name": "baz"}]}]
    ls = session.ls()
    mock_call_action.assert_called_with("fileBrowserStore.getFileList", "/current/dir")
    mock_get_value.assert_called_with("fileBrowserStore.fileList")
    assert ls == ["bar.fits", "baz/", "foo.fits"]


def test_cd(session, mock_method, mock_call_action):
    mock_method("resolve_file_path", ["/resolved/file/path"])
    session.cd("original/path")
    mock_call_action.assert_called_with("fileBrowserStore.saveStartingDirectory", "/resolved/file/path")

# OPENING IMAGES


@pytest.mark.parametrize("args,kwargs,expected_args,expected_kwargs", [
    # Open plain image
    (["subdir/image.fits"], {},
     ["subdir", "image.fits", "", False, False], {"update_directory": False}),
    # Append plain image
    (["subdir/image.fits"], {"append": True},
     ["subdir", "image.fits", "", True, False], {"update_directory": False}),
    # Open plain image; select different HDU
    (["subdir/image.fits"], {"hdu": "3"},
     ["subdir", "image.fits", "3", False, False], {"update_directory": False}),
    # Open plain image; update file browser directory
    (["subdir/image.fits"], {"update_directory": True},
     ["subdir", "image.fits", "", False, False], {"update_directory": True}),
])
def test_open_image(mocker, session, args, kwargs, expected_args, expected_kwargs):
    mock_image_new = mocker.patch.object(Image, "new")
    session.open_image(*args, **kwargs)
    mock_image_new.assert_called_with(session, *expected_args, **expected_kwargs)

# TODO this should be merged with the test above when this separate function is removed


@pytest.mark.parametrize("args,kwargs,expected_args,expected_kwargs", [
    # Open complex image (AMPLITUDE)
    (["subdir/image.fits"], {"expression": CE.AMPLITUDE},
     ["subdir", 'AMPLITUDE("image.fits")', "", False, True], {"update_directory": False}),
    # Append complex image (PHASE)
    (["subdir/image.fits"], {"expression": CE.PHASE, "append": True},
     ["subdir", 'PHASE("image.fits")', "", True, True], {"update_directory": False}),
    # Open complex image (REAL); update file browser directory
    (["subdir/image.fits"], {"expression": CE.REAL, "update_directory": True},
     ["subdir", 'REAL("image.fits")', "", False, True], {"update_directory": True}),
])
def test_open_complex_image(mocker, session, args, kwargs, expected_args, expected_kwargs):
    mock_image_new = mocker.patch.object(Image, "new")
    session.open_complex_image(*args, **kwargs)
    mock_image_new.assert_called_with(session, *expected_args, **expected_kwargs)


@pytest.mark.parametrize("args,kwargs,expected_args,expected_kwargs", [
    # Open LEL image
    (["2*image.fits"], {},
     [".", '2*image.fits', "", False, True], {"update_directory": False}),
    # Append LEL image
    (["2*image.fits+image.fits"], {"append": True},
     [".", '2*image.fits+image.fits', "", True, True], {"update_directory": False}),
    # Open LEL image; update file browser directory
    (["2*image.fits/image.fits"], {"update_directory": True},
     [".", '2*image.fits/image.fits', "", False, True], {"update_directory": True}),
])
def test_open_LEL_image(mocker, session, args, kwargs, expected_args, expected_kwargs):
    mock_image_new = mocker.patch.object(Image, "new")
    session.open_LEL_image(*args, **kwargs)
    mock_image_new.assert_called_with(session, *expected_args, **expected_kwargs)


# OVERLAY


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
        mocker.call("overlayStore.numbers.setFormatX", x),
        mocker.call("overlayStore.numbers.setFormatY", y),
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


def test_number_format(session, mock_get_value, mocker):
    mock_get_value.side_effect = [NF.DEGREES, NF.DEGREES, False]
    x, y, _ = session.number_format()
    mock_get_value.assert_has_calls([
        mocker.call("overlayStore.numbers.formatTypeX"),
        mocker.call("overlayStore.numbers.formatTypeY"),
        mocker.call("overlayStore.numbers.customFormat"),
    ])
    assert isinstance(x, NF)
    assert isinstance(y, NF)
