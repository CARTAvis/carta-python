import pytest

from carta.session import Session
from carta.image import Image
from carta.vector_overlay import VectorOverlay
from carta.util import Macro
from carta.constants import VectorOverlaySource as VOS, Auto


@pytest.fixture
def session():
    """Return a session object.

    The session's protocol is set to None, so any tests that use this must also mock the session's call_action and/or higher-level functions which call it.
    """
    return Session(0, None)


@pytest.fixture
def image(session):
    """Return an image object which uses the session fixture.
    """
    return Image(session, 0)


@pytest.fixture
def vector_overlay(image):
    """Return a vector overlay object which uses the image fixture.
    """
    return VectorOverlay(image)


@pytest.fixture
def mock_get_value(vector_overlay, mocker):
    """Return a mock for vector overlay's get_value."""
    return mocker.patch.object(vector_overlay, "get_value")


@pytest.fixture
def mock_call_action(vector_overlay, mocker):
    """Return a mock for vector overlay's call_action."""
    return mocker.patch.object(vector_overlay, "call_action")


@pytest.fixture
def mock_image_call_action(image, mocker):
    """Return a mock for image's call_action."""
    return mocker.patch.object(image, "call_action")


@pytest.fixture
def mock_property(mocker):
    """Return a helper function to mock the value of a decorated vector overlay property using a simple syntax."""
    def func(property_name, mock_value):
        return mocker.patch(f"carta.vector_overlay.VectorOverlay.{property_name}", new_callable=mocker.PropertyMock, return_value=mock_value)
    return func


@pytest.fixture
def mock_method(vector_overlay, mocker):
    """Return a helper function to mock the return value(s) of an vector overlay method using a simple syntax."""
    def func(method_name, return_values):
        return mocker.patch.object(vector_overlay, method_name, side_effect=return_values)
    return func


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
    # Don'teduce debiasing flag
    ((), {"q_error": 3, "u_error": 4, "debiasing": False},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", False, 3, 4)),
    # Disable debiasing (no q_error)
    ((), {"u_error": 4, "debiasing": True},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", False, "M(qError)", 4)),
    # Disable debiasing (no u_error)
    ((), {"q_error": 3, "debiasing": True},
     ("M(angularSource)", "M(intensitySource)", "M(pixelAveragingEnabled)", "M(pixelAveraging)", "M(fractionalIntensity)", "M(thresholdEnabled)", "M(threshold)", False, 3, "M(uError)")),
])
def test_configure(vector_overlay, mock_call_action, mock_method, args, kwargs, expected_args):
    mock_method("macro", lambda _, v: f"M({v})")
    vector_overlay.configure(*args, **kwargs)
    if expected_args is None:
        mock_call_action.assert_not_called()
    else:
        mock_call_action.assert_called_with("setVectorOverlayConfiguration", *expected_args)


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
def test_set_style(mocker, vector_overlay, mock_call_action, mock_method, args, kwargs, expected_calls):
    mock_method("macro", lambda _, v: f"M({v})")
    vector_overlay.set_style(*args, **kwargs)
    mock_call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


# TODO test_set_color
# TODO test_set_colormap
# TODO test_apply
# TODO test_plot
# TODO test_clear
# TODO test_set_visible
# TODO test_show
# TODO test_hide