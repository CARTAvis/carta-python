import pytest

from carta.contours import Contours
from carta.constants import Colormap as CM, SmoothingMode as SM, ContourDashMode as CDM

# FIXTURES


@pytest.fixture
def contours(image):
    return Contours(image)


@pytest.fixture
def call_action(contours, mock_call_action):
    return mock_call_action(contours)


@pytest.fixture
def method(contours, mock_method):
    return mock_method(contours)


@pytest.fixture
def image_call_action(image, mock_call_action):
    return mock_call_action(image)


# TESTS
@pytest.mark.parametrize("args,kwargs,expected_args", [
    ([], {}, None),
    ([[1, 2, 3], SM.GAUSSIAN_BLUR, 4], {}, [[1, 2, 3], SM.GAUSSIAN_BLUR, 4]),
    ([], {"levels": [1, 2, 3]}, [[1, 2, 3], "M(smoothingMode)", "M(smoothingFactor)"]),
    ([], {"smoothing_mode": SM.GAUSSIAN_BLUR}, ["M(levels)", SM.GAUSSIAN_BLUR, "M(smoothingFactor)"]),
    ([], {"smoothing_factor": 4}, ["M(levels)", "M(smoothingMode)", 4]),
])
def test_configure(contours, call_action, method, args, kwargs, expected_args):
    method("macro", lambda _, v: f"M({v})")
    contours.configure(*args, **kwargs)
    if expected_args is None:
        call_action.assert_not_called()
    else:
        call_action.assert_called_with("setContourConfiguration", *expected_args)


def test_set_dash_mode(mocker, contours, call_action):
    contours.set_dash_mode(CDM.DASHED)
    call_action.assert_called_with("setDashMode", CDM.DASHED)


def test_set_thickness(mocker, contours, call_action):
    contours.set_thickness(2)
    call_action.assert_called_with("setThickness", 2)


def test_set_color(mocker, contours, call_action):
    contours.set_color("blue")
    call_action.assert_has_calls([
        mocker.call("setColor", "blue"),
        mocker.call("setColormapEnabled", False),
    ])


def test_set_colormap(mocker, contours, call_action):
    contours.set_colormap(CM.VIRIDIS)
    call_action.assert_has_calls([
        mocker.call("setColormap", CM.VIRIDIS),
        mocker.call("setColormapEnabled", True),
    ])


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([0.5, 1.5], {}, [("setColormapBias", 0.5), ("setColormapContrast", 1.5)]),
    ([], {"bias": 0.5}, [("setColormapBias", 0.5)]),
    ([], {"contrast": 1.5}, [("setColormapContrast", 1.5)]),
])
def test_set_bias_and_contrast(mocker, contours, call_action, args, kwargs, expected_calls):
    contours.set_bias_and_contrast(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


def test_apply(contours, image_call_action):
    contours.apply()
    image_call_action.assert_called_with("applyContours")


def test_clear(contours, image_call_action):
    contours.clear()
    image_call_action.assert_called_with("clearContours", True)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([[1, 2, 3], SM.GAUSSIAN_BLUR, 4, CDM.DASHED, 2, "blue", CM.VIRIDIS, 0.5, 1.5], {}, [("configure", [1, 2, 3], SM.GAUSSIAN_BLUR, 4), ("set_dash_mode", CDM.DASHED), ("set_thickness", 2), ("set_color", "blue"), ("set_colormap", CM.VIRIDIS), ("set_bias_and_contrast", 0.5, 1.5), ("apply",)]),
    ([], {"smoothing_mode": SM.GAUSSIAN_BLUR}, [("configure", None, SM.GAUSSIAN_BLUR, None), ("apply",)]),
    ([], {"dash_mode": CDM.DASHED}, [("set_dash_mode", CDM.DASHED), ("apply",)]),
    ([], {"thickness": 2}, [("set_thickness", 2), ("apply",)]),
    ([], {"color": "blue"}, [("set_color", "blue"), ("apply",)]),
    ([], {"colormap": CM.VIRIDIS}, [("set_colormap", CM.VIRIDIS), ("apply",)]),
    ([], {"bias": 0.5}, [("set_bias_and_contrast", 0.5, None), ("apply",)]),
])
def test_plot(contours, method, args, kwargs, expected_calls):
    mocks = {}
    for method_name in ("configure", "set_dash_mode", "set_thickness", "set_color", "set_colormap", "set_bias_and_contrast", "apply"):
        mocks[method_name] = method(method_name, None)

    contours.plot(*args, **kwargs)

    for method_name, *expected_args in expected_calls:
        mocks[method_name].assert_called_with(*expected_args)


@pytest.mark.parametrize("state", [True, False])
def test_set_visible(contours, call_action, state):
    contours.set_visible(state)
    call_action.assert_called_with("setVisible", state)


def test_show(contours, method):
    mock_set_visible = method("set_visible", None)
    contours.show()
    mock_set_visible.assert_called_with(True)


def test_hide(contours, method):
    mock_set_visible = method("set_visible", None)
    contours.hide()
    mock_set_visible.assert_called_with(False)
