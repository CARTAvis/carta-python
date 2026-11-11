import pytest

from carta.vector_overlay import VectorOverlay
from carta.util import Macro, CartaValidationFailed
from carta.constants import VectorOverlaySource as VOS, Polarization as Pol, Auto, Colormap as CM

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
    ((VOS.CURRENT, VOS.CURRENT), {"pixel_averaging": 1, "fractional_intensity": True, "threshold_enabled": True, "threshold": 3, "threshold_option": Pol.I, "debiasing": True, "q_error": 4, "u_error": 5}, (VOS.CURRENT, VOS.CURRENT, 1, True, True, 3, True, 4, 5, Pol.I)),
    # Pixel averaging is passed directly to the frontend
    ((), {"pixel_averaging": 1},
     ("M(angularSource)", "M(intensitySource)", 1, "M(isFractionalIntensity)", "M(isThresholdEnabled)", "M(threshold)", "M(isDebiasing)", "M(qError)", "M(uError)", "M(thresholdOption)")),
    # Deduce threshold flag
    ((), {"threshold": 2},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveraging)", "M(isFractionalIntensity)", True, 2, "M(isDebiasing)", "M(qError)", "M(uError)", "M(thresholdOption)")),
    # Don't deduce threshold flag
    ((), {"threshold": 2, "threshold_enabled": False},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveraging)", "M(isFractionalIntensity)", False, 2, "M(isDebiasing)", "M(qError)", "M(uError)", "M(thresholdOption)")),
    # Deduce debiasing flag
    ((), {"q_error": 3, "u_error": 4},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveraging)", "M(isFractionalIntensity)", "M(isThresholdEnabled)", "M(threshold)", True, 3, 4, "M(thresholdOption)")),
    # Don't deduce debiasing flag
    ((), {"q_error": 3, "u_error": 4, "debiasing": False},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveraging)", "M(isFractionalIntensity)", "M(isThresholdEnabled)", "M(threshold)", False, 3, 4, "M(thresholdOption)")),
    # Disable debiasing (no q_error)
    ((), {"u_error": 4, "debiasing": True},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveraging)", "M(isFractionalIntensity)", "M(isThresholdEnabled)", "M(threshold)", False, "M(qError)", 4, "M(thresholdOption)")),
    # Disable debiasing (no u_error)
    ((), {"q_error": 3, "debiasing": True},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveraging)", "M(isFractionalIntensity)", "M(isThresholdEnabled)", "M(threshold)", False, 3, "M(uError)", "M(thresholdOption)")),
])
def test_configure(vector_overlay, call_action, method, args, kwargs, expected_args):
    method("macro", lambda _, v: f"M({v})")
    vector_overlay.configure(*args, **kwargs)
    if expected_args is None:
        call_action.assert_not_called()
    else:
        call_action.assert_called_with("setVectorOverlayConfiguration", *expected_args)


@pytest.mark.parametrize("name", ["configure", "plot"])
@pytest.mark.parametrize("value", [True, False, 0, 1, None])
def test_fractional_intensity_accepts_boolean_or_preserves_current(name, value, vector_overlay, call_action, image_call_action, method):
    method("macro", lambda _, attribute: f"M({attribute})")

    getattr(vector_overlay, name)(pixel_averaging=4, fractional_intensity=value)

    fractional = "M(isFractionalIntensity)" if value is None else bool(value)
    call_action.assert_called_once_with(
        "setVectorOverlayConfiguration", "M(angularSource)", "M(intensitySource)", 4,
        fractional, "M(isThresholdEnabled)", "M(threshold)",
        "M(isDebiasing)", "M(qError)", "M(uError)", "M(thresholdOption)",
    )
    if value is not None:
        assert call_action.call_args.args[4] is fractional


@pytest.mark.parametrize("name", ["configure", "plot"])
@pytest.mark.parametrize("value", [2, -1, 0.5, "true"])
def test_fractional_intensity_rejects_non_boolean(name, value, vector_overlay, call_action, image_call_action):
    with pytest.raises(CartaValidationFailed, match="boolean"):
        getattr(vector_overlay, name)(fractional_intensity=value)

    call_action.assert_not_called()
    image_call_action.assert_not_called()


@pytest.mark.parametrize("name", ["configure", "plot"])
@pytest.mark.parametrize("args", [
    # The removed pixel_averaging_enabled flag followed by a width, as in 1.x
    (None, None, True, 4),
    (None, None, 4),
])
def test_options_after_sources_are_keyword_only(name, args, vector_overlay, call_action, image_call_action):
    with pytest.raises(TypeError, match="positional"):
        getattr(vector_overlay, name)(*args)

    call_action.assert_not_called()
    image_call_action.assert_not_called()


@pytest.mark.parametrize("name", ["configure", "plot"])
def test_pixel_averaging_enabled_is_removed(name, vector_overlay, call_action, image_call_action):
    with pytest.raises(CartaValidationFailed, match="pixel_averaging_enabled"):
        getattr(vector_overlay, name)(pixel_averaging_enabled=False)

    call_action.assert_not_called()
    image_call_action.assert_not_called()


@pytest.mark.parametrize("name", ["configure", "plot"])
def test_threshold_option_is_forwarded_by_keyword(name, vector_overlay, call_action, image_call_action, method):
    method("macro", lambda _, value: f"M({value})")

    getattr(vector_overlay, name)(threshold_option=Pol.PLINEAR)

    call_action.assert_called_once_with(
        "setVectorOverlayConfiguration", "M(angularSource)", "M(intensitySource)", "M(pixelAveraging)",
        "M(isFractionalIntensity)", "M(isThresholdEnabled)", "M(threshold)",
        "M(isDebiasing)", "M(qError)", "M(uError)", Pol.PLINEAR,
    )


@pytest.mark.parametrize("name", ["configure", "plot"])
def test_threshold_option_rejects_unsupported_polarization(name, vector_overlay, call_action):
    with pytest.raises(CartaValidationFailed):
        getattr(vector_overlay, name)(threshold_option=Pol.Q)
    call_action.assert_not_called()


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


CONFIGURATION_NONE = {
    "pixel_averaging": None, "fractional_intensity": None, "threshold_enabled": None, "threshold": None,
    "threshold_option": None, "debiasing": None, "q_error": None, "u_error": None,
}


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([VOS.CURRENT, VOS.CURRENT], {"pixel_averaging": 1, "fractional_intensity": True, "threshold_enabled": True, "threshold": 3, "threshold_option": Pol.I, "debiasing": True, "q_error": 4, "u_error": 5, "thickness": 1, "intensity_min": 2, "intensity_max": 3, "length_min": 4, "length_max": 5, "rotation_offset": 6, "color": "blue", "colormap": CM.VIRIDIS, "bias": 0.5, "contrast": 1.5},
     [("configure", (VOS.CURRENT, VOS.CURRENT), {"pixel_averaging": 1, "fractional_intensity": True, "threshold_enabled": True, "threshold": 3, "threshold_option": Pol.I, "debiasing": True, "q_error": 4, "u_error": 5}), ("set_thickness", 1), ("set_intensity_range", 2, 3), ("set_length_range", 4, 5), ("set_rotation_offset", 6), ("set_color", "blue"), ("set_colormap", CM.VIRIDIS), ("set_bias_and_contrast", 0.5, 1.5), ("apply",)]),
    ([], {"pixel_averaging": 1, "thickness": 2, "color": "blue", "bias": 0.5},
     [("configure", (None, None), {**CONFIGURATION_NONE, "pixel_averaging": 1}), ("set_thickness", 2), ("set_color", "blue"), ("set_bias_and_contrast", 0.5, None), ("apply",)]),
    ([VOS.COMPUTED], {}, [("configure", (VOS.COMPUTED, None), CONFIGURATION_NONE), ("apply",)]),
    ([], {"thickness": 2}, [("set_thickness", 2), ("apply",)]),
])
def test_plot(vector_overlay, method, args, kwargs, expected_calls):
    mocks = {}
    for method_name in ("configure", "set_thickness", "set_intensity_range", "set_length_range", "set_rotation_offset", "set_color", "set_colormap", "set_bias_and_contrast", "apply"):
        mocks[method_name] = method(method_name, None)

    vector_overlay.plot(*args, **kwargs)

    for method_name, *expected_args in expected_calls:
        if method_name == "configure":
            expected_positional, expected_keywords = expected_args
            mocks[method_name].assert_called_with(*expected_positional, **expected_keywords)
        else:
            mocks[method_name].assert_called_with(*expected_args)
    if not any(name == "configure" for name, *_ in expected_calls):
        mocks["configure"].assert_not_called()


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
