import pytest

from carta.vector_overlay import VectorOverlay
from carta.util import Macro
from carta.constants import VectorOverlaySource as VOS, Auto, Colormap as CM


@pytest.fixture
def vector_overlay(image):
    return VectorOverlay(image)


@pytest.fixture
def get_value(vector_overlay, mock_get_value):
    return mock_get_value(vector_overlay)


@pytest.fixture
def call_action(vector_overlay, mock_call_action):
    return mock_call_action(vector_overlay)


@pytest.fixture
def image_call_action(image, mock_call_action):
    return mock_call_action(image)


@pytest.fixture
def property_(mock_property):
    return mock_property("carta.vector_overlay.VectorOverlay")


@pytest.fixture
def method(vector_overlay, mock_method):
    return mock_method(vector_overlay)


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


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    # Nothing
    ((), {}, ()),
    # Everything
    ((1, 2, 3, 4, 5, 6), {}, (
        ("setThickness", 1),
        ("setIntensityRange", 2, 3),
        ("setLengthRange", 4, 5),
        ("setRotationOffset", 6),
    )),
    # No intensity min; auto intensity max
    ((), {"intensity_max": Auto.AUTO}, (("setIntensityRange", "M(intensityMin)", Macro.UNDEFINED),)),
    # Auto intensity min; no intensity max
    ((), {"intensity_min": Auto.AUTO}, (("setIntensityRange", Macro.UNDEFINED, "M(intensityMax)"),)),
])
def test_set_style(mocker, vector_overlay, call_action, method, args, kwargs, expected_calls):
    method("macro", lambda _, v: f"M({v})")
    vector_overlay.set_style(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


def test_set_color(mocker, vector_overlay, call_action):
    vector_overlay.set_color("blue")
    call_action.assert_has_calls([
        mocker.call("setColor", "blue"),
        mocker.call("setColormapEnabled", False),
    ])


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([CM.VIRIDIS, 0.5, 1.5], {}, [("setColormap", CM.VIRIDIS), ("setColormapEnabled", True), ("setColormapBias", 0.5), ("setColormapContrast", 1.5)]),
    ([CM.VIRIDIS], {}, [("setColormap", CM.VIRIDIS), ("setColormapEnabled", True)]),
    ([], {"bias": 0.5}, [("setColormapBias", 0.5)]),
    ([], {"contrast": 1.5}, [("setColormapContrast", 1.5)]),
])
def test_set_colormap(mocker, vector_overlay, call_action, args, kwargs, expected_calls):
    vector_overlay.set_colormap(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


def test_apply(vector_overlay, image_call_action):
    vector_overlay.apply()
    image_call_action.assert_called_with("applyVectorOverlay")


def test_clear(vector_overlay, image_call_action):
    vector_overlay.clear()
    image_call_action.assert_called_with("clearVectorOverlay", True)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([VOS.CURRENT, VOS.CURRENT, True, 1, 2, True, 3, True, 4, 5, 1, 2, 3, 4, 5, 6, "blue", CM.VIRIDIS, 0.5, 1.5], {}, [("configure", VOS.CURRENT, VOS.CURRENT, True, 1, 2, True, 3, True, 4, 5), ("set_style", 1, 2, 3, 4, 5, 6), ("set_color", "blue"), ("set_colormap", CM.VIRIDIS, 0.5, 1.5), ("apply",)]),
    ([], {"pixel_averaging": 1, "thickness": 2, "color": "blue", "bias": 0.5}, [("configure", None, None, None, 1, None, None, None, None, None, None), ("set_style", 2, None, None, None, None, None), ("set_color", "blue"), ("set_colormap", None, 0.5, None), ("apply",)]),
    ([], {"thickness": 2}, [("set_style", 2, None, None, None, None, None), ("apply",)]),
])
def test_plot(vector_overlay, method, args, kwargs, expected_calls):
    mocks = {}
    for method_name in ("configure", "set_style", "set_color", "set_colormap", "apply"):
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
