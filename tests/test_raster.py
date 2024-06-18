import pytest

from carta.raster import Raster, SessionRaster
from carta.constants import Colormap as CM, Scaling as SC, Auto, PaletteColor as PC
from carta.util import CartaValidationFailed

# FIXTURES


@pytest.fixture
def raster(image):
    """Return a vector overlay object which uses the image fixture.
    """
    return Raster(image)


@pytest.fixture
def call_action(raster, mock_call_action):
    return mock_call_action(raster)


@pytest.fixture
def method(raster, mock_method):
    return mock_method(raster)


@pytest.fixture
def session_raster(session):
    return SessionRaster(session)


@pytest.fixture
def session_raster_method(session_raster, mock_method):
    return mock_method(session_raster)


@pytest.fixture
def session_call_action(session, mock_call_action):
    return mock_call_action(session)


@pytest.fixture
def session_get_value(session, mock_get_value):
    return mock_get_value(session)

# TESTS


@pytest.mark.parametrize("colormap", [CM.VIRIDIS])
@pytest.mark.parametrize("invert", [True, False])
def test_set_colormap(mocker, raster, call_action, colormap, invert):
    raster.set_colormap(colormap, invert)
    call_action.assert_has_calls([
        mocker.call("setColorMap", colormap),
        mocker.call("setInverted", invert),
    ])


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ((SC.LINEAR, 5, 0.5), {}, [("setScaling", SC.LINEAR), ("setAlpha", 5), ("setGamma", 0.5), ]),
    ([], {"scaling": SC.LINEAR}, [("setScaling", SC.LINEAR)]),
    ([], {"alpha": 5}, [("setAlpha", 5)]),
    ([], {"gamma": 0.5}, [("setGamma", 0.5)]),
])
def test_set_scaling_valid(mocker, raster, call_action, args, kwargs, expected_calls):
    raster.set_scaling(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


@pytest.mark.parametrize("kwargs", [
    {"alpha": 0},
    {"gamma": 0},
    {"alpha": 2000000},
    {"gamma": 5},
])
def test_set_scaling_invalid(raster, kwargs):
    with pytest.raises(CartaValidationFailed):
        raster.set_scaling(**kwargs)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ((99, 10, 1000), {}, [("setPercentileRank", 99)]),
    ([], {"rank": 98}, [("setPercentileRank", 98), ("setPercentileRank", -1)]),
    ([], {"min": 10, "max": 1000}, [("setCustomScale", 10, 1000)]),
    ([], {"min": 10}, []),
    ([], {"max": 1000}, []),
])
def test_set_clip_valid(mocker, raster, call_action, args, kwargs, expected_calls):
    raster.set_clip(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


@pytest.mark.parametrize("kwargs", [
    {"rank": -1},
    {"rank": 101},
])
def test_set_clip_invalid(raster, kwargs):
    with pytest.raises(CartaValidationFailed):
        raster.set_clip(**kwargs)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([0.5, 0.5], {}, [("setBias", 0.5), ("setContrast", 0.5)]),
    ([], {"bias": Auto.AUTO, "contrast": Auto.AUTO}, [("resetBias",), ("resetContrast",)]),
])
def test_set_bias_and_contrast_valid(mocker, raster, call_action, args, kwargs, expected_calls):
    raster.set_bias_and_contrast(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


@pytest.mark.parametrize("kwargs", [
    {"bias": -5},
    {"contrast": -1},
    {"bias": 2},
    {"contrast": 5},
])
def test_set_bias_and_contrast_invalid(raster, kwargs):
    with pytest.raises(CartaValidationFailed):
        raster.set_bias_and_contrast(**kwargs)


@pytest.mark.parametrize("state", [True, False])
def test_set_visible(raster, call_action, state):
    raster.set_visible(state)
    call_action.assert_called_with("setVisible", state)


def test_show(raster, method):
    mock_set_visible = method("set_visible", None)
    raster.show()
    mock_set_visible.assert_called_with(True)


def test_hide(raster, method):
    mock_set_visible = method("set_visible", None)
    raster.hide()
    mock_set_visible.assert_called_with(False)

# GLOBAL RASTER SETTINGS


def test_pixel_grid_visible(session_raster, session_get_value):
    session_get_value.side_effect = [True]
    visible = session_raster.pixel_grid_visible
    session_get_value.assert_called_with("preferenceStore.pixelGridVisible", return_path=None)
    assert visible


@pytest.mark.parametrize("state", [True, False])
def test_set_pixel_grid_visible(session_raster, session_call_action, state):
    session_raster.set_pixel_grid_visible(state)
    session_call_action.assert_called_with("preferenceStore.setPreference", "pixelGridVisible", state)


def test_show_hide_pixel_grid(mocker, session_raster, session_raster_method):
    set_visible = session_raster_method("set_pixel_grid_visible", None)
    session_raster.show_pixel_grid()
    session_raster.hide_pixel_grid()
    set_visible.assert_has_calls([
        mocker.call(True),
        mocker.call(False),
    ])


def test_pixel_grid_color(session_raster, session_get_value):
    session_get_value.side_effect = [PC.BLUE]
    color = session_raster.pixel_grid_color
    session_get_value.assert_called_with("preferenceStore.pixelGridColor", return_path=None)
    assert color is PC.BLUE


def test_set_pixel_grid_color(session_raster, session_call_action):
    session_raster.set_pixel_grid_color(PC.BLUE)
    session_call_action.assert_called_with("preferenceStore.setPreference", "pixelGridColor", PC.BLUE)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([True, PC.BLUE], {}, [("preferenceStore.setPreference", "pixelGridVisible", True), ("preferenceStore.setPreference", "pixelGridColor", PC.BLUE)]),
    ([], {"visible": True}, [("preferenceStore.setPreference", "pixelGridVisible", True)]),
    ([], {"color": PC.BLUE}, [("preferenceStore.setPreference", "pixelGridColor", PC.BLUE)]),
])
def test_set_pixel_grid(mocker, session_raster, session_call_action, args, kwargs, expected_calls):
    session_raster.set_pixel_grid(*args, **kwargs)
    session_call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])
