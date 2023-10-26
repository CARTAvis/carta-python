import pytest

from carta.raster import Raster
from carta.constants import Colormap as CM, Scaling as SC, Auto
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
    # Nothing
    ((), {},
     [
    ]),
    # Everything (min and max will be ignored)
    ((SC.LINEAR, 5, 0.5, 99, 10, 1000, 0.5, 0.5), {},
     [
        ("setScaling", SC.LINEAR),
        ("setAlpha", 5),
        ("setGamma", 0.5),
        ("setPercentileRank", 99),
        ("setBias", 0.5),
        ("setContrast", 0.5),
    ]),
    # Custom min and max (no rank)
    ((), {"min": 10, "max": 1000},
     [
        ("setCustomScale", 10, 1000),
    ]),
    # Min only (no effect)
    ((), {"min": 10},
     [
    ]),
    # Max only (no effect)
    ((), {"max": 1000},
     [
    ]),
    # Reset bias and contrast
    ((), {"bias": Auto.AUTO, "contrast": Auto.AUTO},
     [
        ("resetBias",),
        ("resetContrast",),
    ]),
])
def test_set_scaling_valid(mocker, raster, call_action, args, kwargs, expected_calls):
    raster.set_scaling(*args, **kwargs)
    call_action.assert_has_calls([mocker.call(*call) for call in expected_calls])


@pytest.mark.parametrize("kwargs", [
    {"alpha": 0},
    {"gamma": 0},
    {"rank": -1},
    {"bias": -5},
    {"contrast": -1},
    {"alpha": 2000000},
    {"gamma": 5},
    {"rank": 101},
    {"bias": 2},
    {"contrast": 5},
])
def test_set_scaling_invalid(mocker, raster, kwargs):
    with pytest.raises(CartaValidationFailed):
        raster.set_scaling(**kwargs)
