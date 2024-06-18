import pytest

from carta.vector_overlay import VectorOverlay
from carta.util import Macro
from carta.constants import VectorOverlaySource as VOS, Auto, Colormap as CM

# FIXTURES


@pytest.fixture
def vector_overlay(image):
    return VectorOverlay(image)


@pytest.fixture
def call_action(vector_overlay, mock_call_action):
    return mock_call_action(vector_overlay)


@pytest.fixture
def method(vector_overlay, mock_method):
    return mock_method(vector_overlay)


@pytest.fixture
def image_call_action(image, mock_call_action):
    return mock_call_action(image)


# TESTS


@pytest.mark.parametrize("args,kwargs,expected_args", [
    # Nothing
    ((), {}, None),
    # Everything
    ((VOS.CURRENT, VOS.CURRENT, True, 1, 2, True, 3, True, 4, 5), {}, (VOS.CURRENT, VOS.CURRENT, True, 1, 2, True, 3, True, 4, 5)),
    # Deduce pixel averaging flag
    ((), {"pixel_averaging": 1},
     ("M(angularSource)", "M(intensitySource)", True, 1, "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", "M(debiasing)", "M(qError)", "M(uError)")),
    # Don't deduce pixel averaging flag
    ((), {"pixel_averaging": 1, "pixel_averaging_enabled": False},
     ("M(angularSource)", "M(intensitySource)", False, 1, "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", "M(debiasing)", "M(qError)", "M(uError)")),
    # Deduce threshold flag
    ((), {"threshold": 2},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", True, 2, "M(debiasing)", "M(qError)", "M(uError)")),
    # Don't deduce threshold flag
    ((), {"threshold": 2, "threshold_enabled": False},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", False, 2, "M(debiasing)", "M(qError)", "M(uError)")),
    # Deduce debiasing flag
    ((), {"q_error": 3, "u_error": 4},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", True, 3, 4)),
    # Don't deduce debiasing flag
    ((), {"q_error": 3, "u_error": 4, "debiasing": False},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", False, 3, 4)),
    # Disable debiasing (no q_error)
    ((), {"u_error": 4, "debiasing": True},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", False, "M(qError)", 4)),
    # Disable debiasing (no u_error)
    ((), {"q_error": 3, "debiasing": True},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", False, 3, "M(uError)")),
])
def test_configure(vector_overlay, call_action, method, args, kwargs, expected_args):
    method("macro", lambda _, v: f"M({v})")
    vector_overlay.configure(*args, **kwargs)
    if expected_args is None:
        call_action.assert_not_called()
    else:
        call_action.assert_called_with("setVectorOverlayConfiguration", *expected_args)


def test_set_thickness(vector_overlay, call_action):
    vector_overlay.set_thickness(5)
    call_action.assert_called_with("setThickness", 5)


@pytest.mark.parametrize("args,kwargs,expected_args", [
    # Nothing
    ((), {}, None),
    # Everything
    ((2, 3), {}, ("setIntensityRange", 2, 3)),
    # No intensity min; auto intensity max
    ((), {"intensity_max": Auto.AUTO}, ("setIntensityRange", "M(intensityMin)", Macro.UNDEFINED)),
    # Auto intensity min; no intensity max
    ((), {"intensity_min": Auto.AUTO}, ("setIntensityRange", Macro.UNDEFINED, "M(intensityMax)")),
])
def test_set_intensity_range(vector_overlay, call_action, method, args, kwargs, expected_args):
    method("macro", lambda _, v: f"M({v})")
    vector_overlay.set_intensity_range(*args, **kwargs)
    if expected_args is not None:
        call_action.assert_called_with(*expected_args)
    else:
        call_action.assert_not_called()


def test_set_length_range(vector_overlay, call_action):
    vector_overlay.set_length_range(2, 3)
    call_action.assert_called_with("setLengthRange", 2, 3)


def test_set_rotation_offset(vector_overlay, call_action):
    vector_overlay.set_rotation_offset(5)
    call_action.assert_called_with("setRotationOffset", 5)


def test_set_color(mocker, vector_overlay, call_action):
    vector_overlay.set_color("blue")
    call_action.assert_has_calls([
        mocker.call("setColor", "blue"),
        mocker.call("setColormapEnabled", False),
    ])


def test_set_colormap(mocker, vector_overlay, call_action):
    vector_overlay.set_colormap(CM.VIRIDIS)
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
def test_set_bias_and_contrast(mocker, vector_overlay, call_action, args, kwargs, expected_calls):
    vector_overlay.set_bias_and_contrast(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


def test_apply(vector_overlay, image_call_action):
    vector_overlay.apply()
    image_call_action.assert_called_with("applyVectorOverlay")


def test_clear(vector_overlay, image_call_action):
    vector_overlay.clear()
    image_call_action.assert_called_with("clearVectorOverlay", True)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([VOS.CURRENT, VOS.CURRENT, True, 1, 2, True, 3, True, 4, 5, 1, 2, 3, 4, 5, 6, "blue", CM.VIRIDIS, 0.5, 1.5], {}, [("configure", VOS.CURRENT, VOS.CURRENT, True, 1, 2, True, 3, True, 4, 5), ("set_thickness", 1), ("set_intensity_range", 2, 3), ("set_length_range", 4, 5), ("set_rotation_offset", 6), ("set_color", "blue"), ("set_colormap", CM.VIRIDIS), ("set_bias_and_contrast", 0.5, 1.5), ("apply",)]),
    ([], {"pixel_averaging": 1, "thickness": 2, "color": "blue", "bias": 0.5}, [("configure", None, None, None, 1, None, None, None, None, None, None), ("set_thickness", 2), ("set_color", "blue"), ("set_bias_and_contrast", 0.5, None), ("apply",)]),
    ([], {"thickness": 2}, [("set_thickness", 2), ("apply",)]),
])
def test_plot(vector_overlay, method, args, kwargs, expected_calls):
    mocks = {}
    for method_name in ("configure", "set_thickness", "set_intensity_range", "set_length_range", "set_rotation_offset", "set_color", "set_colormap", "set_bias_and_contrast", "apply"):
        mocks[method_name] = method(method_name, None)

    vector_overlay.plot(*args, **kwargs)

    for method_name, *expected_args in expected_calls:
        mocks[method_name].assert_called_with(*expected_args)


@pytest.mark.parametrize("state", [True, False])
def test_set_visible(vector_overlay, call_action, state):
    vector_overlay.set_visible(state)
    call_action.assert_called_with("setVisible", state)


def test_show(vector_overlay, method):
    mock_set_visible = method("set_visible", None)
    vector_overlay.show()
    mock_set_visible.assert_called_with(True)


def test_hide(vector_overlay, method):
    mock_set_visible = method("set_visible", None)
    vector_overlay.hide()
    mock_set_visible.assert_called_with(False)
