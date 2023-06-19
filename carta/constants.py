"""This module provides a collection of enums corresponding to various enumerated types and other literal lists of options defined in the frontend. The members of these enums should be used in place of literal strings and numbers to represent these values; for example: ``Colormap.VIRIDIS`` rather than ``"viridis"``. """

from enum import Enum, IntEnum


# TODO make sure the __str__ is right for all the string values

class ArithmeticExpression(str, Enum):
    """Arithmetic expression."""
    AMPLITUDE = "AMPLITUDE"
    PHASE = "PHASE"
    REAL = "REAL"
    IMAG = "IMAG"


Colormap = Enum('Colormap', {c.upper(): c for c in ('copper', 'paired', 'gist_heat', 'brg', 'cool', 'summer', 'OrRd', 'tab20c', 'purples', 'gray', 'terrain', 'RdPu', 'set2', 'spring', 'gist_yarg', 'RdYlBu', 'reds', 'winter', 'Wistia', 'rainbow', 'dark2', 'oranges', 'BuPu', 'gist_earth', 'PuBu', 'pink', 'PuOr', 'pastel2', 'PiYG', 'gist_ncar', 'PuRd', 'plasma', 'gist_stern', 'hot', 'PuBuGn', 'YlOrRd', 'accent', 'magma', 'set1', 'GnBu', 'greens', 'CMRmap', 'gist_rainbow', 'prism', 'hsv', 'Blues', 'viridis', 'YlGn', 'spectral', 'RdBu', 'tab20', 'greys', 'flag', 'jet', 'seismic', 'PRGn', 'coolwarm', 'YlOrBr', 'RdYlGn', 'bone', 'autumn', 'BrBG', 'gnuplot2', 'RdGy', 'binary', 'gnuplot', 'BuGn', 'gist_gray', 'nipy_spectral', 'set3', 'tab20b', 'pastel1', 'afmhot', 'cubehelix', 'YlGnBu', 'ocean', 'tab10', 'bwr', 'inferno')}, type=str)
Colormap.__doc__ = """All available colormaps."""


Scaling = Enum('Scaling', ('LINEAR', 'LOG', 'SQRT', 'SQUARE', 'POWER', 'GAMMA'), type=int, start=0)
Scaling.__doc__ = """Colormap scaling types."""


CoordinateSystem = Enum('CoordinateSystem', {c.upper(): c for c in ("Auto", "Ecliptic", "FK4", "FK5", "Galactic", "ICRS")}, type=str)
CoordinateSystem.__doc__ = """Coordinate systems."""


class LabelType(str, Enum):
    """Label types."""
    INTERIOR = "Interior"
    EXTERIOR = "Exterior"


class BeamType(str, Enum):
    """Beam types."""
    OPEN = "Open"
    SOLID = "Solid"


# BlueprintJS colour palettes (2 and 4)
LIGHT_THEME = {
    "DARK_GRAY": "#252a31",
    "GRAY": "#738091",
    "LIGHT_GRAY": "#dce0e5",
    "BLUE": "#215db0",
    "GREEN": "#1c6e42",
    "ORANGE": "#935610",
    "RED": "#ac2f33",
    "VERMILION": "#b83211",
    "ROSE": "#c22762",
    "VIOLET": "#7c327c",
    "INDIGO": "#634dbf",
    "COBALT": "#2458b3",
    "TURQUOISE": "#007067",
    "FOREST": "#238c2c",
    "LIME": "#5a701a",
    "GOLD": "#866103",
    "SEPIA": "#7a542e",
    "WHITE": "#ffffff",
    "BLACK": "#000000",
}

DARK_THEME = {
    "DARK_GRAY": "#383e47",
    "GRAY": "#abb3bf",
    "LIGHT_GRAY": "#edeff2",
    "BLUE": "#4c90f0",
    "GREEN": "#32a467",
    "ORANGE": "#ec9a3c",
    "RED": "#e76a6e",
    "VERMILION": "#eb6847",
    "ROSE": "#f5498b",
    "VIOLET": "#bd6bbd",
    "INDIGO": "#9881f3",
    "COBALT": "#4580e6",
    "TURQUOISE": "#13c9ba",
    "FOREST": "#43bf4d",
    "LIME": "#b6d94c",
    "GOLD": "#f0b726",
    "SEPIA": "#af855a",
    "WHITE": "#ffffff",
    "BLACK": "#000000",
}


class PaletteColor(str, Enum):
    """Palette colours used for overlay elements.

    Members of this enum class have additional attributes.

    Attributes
    ----------
    rgb_light : string
        The RGB value of this palette colour in the light theme.
    rgb_dark : string
        The RGB value of this palette colour in the dark theme.

    """

    def __init__(self, value):
        self.rgb_light = LIGHT_THEME[self.name]
        self.rgb_dark = DARK_THEME[self.name]

    _ignore_ = "PaletteColor c"

    PaletteColor = vars()

    for c in ('BLUE', 'ORANGE', 'GREEN', 'RED', 'VERMILION', 'ROSE', 'VIOLET', 'SEPIA', 'INDIGO', 'GRAY', 'LIME', 'TURQUOISE', 'FOREST', 'GOLD', 'COBALT', 'LIGHT_GRAY', 'DARK_GRAY', 'WHITE', 'BLACK'):
        PaletteColor[c] = f"auto-{c.lower()}"


Overlay = Enum('Overlay', [(c.upper(), c) for c in ("global", "title", "grid", "border", "ticks", "axes", "numbers", "labels", "colorbar")] + [('BEAM', 'beam.settingsForDisplay')], type=str)
Overlay.__doc__ = """Overlay elements.

    Member values are paths to stores corresponding to these elements, relative to the overlay store.
    """


SmoothingMode = Enum('SmoothingMode', ('NO_SMOOTHING', 'BLOCK_AVERAGE', 'GAUSSIAN_BLUR'), type=int, start=0)
SmoothingMode.__doc__ = """Contour smoothing modes."""


class ContourDashMode(str, Enum):
    """Contour dash modes."""
    NONE = "None"
    DASHED = "Dashed"
    NEGATIVE_ONLY = "NegativeOnly"


class Polarization(IntEnum):
    """Polarizations, corresponding to the POLARIZATIONS enum in the frontend."""
    YX = -8
    XY = -7
    YY = -6
    XX = -5
    LR = -4
    RL = -3
    LL = -2
    RR = -1
    I = 1
    Q = 2
    U = 3
    V = 4
    PTOTAL = 13
    PLINEAR = 14
    PFTOTAL = 15
    PFLINEAR = 16
    PANGLE = 17


PanelMode = Enum('PanelMode', ('SINGLE', 'MULTIPLE'), type=int, start=0)
PanelMode.__doc__ = """Panel modes."""


class GridMode(str, Enum):
    """Grid modes."""
    DYNAMIC = "dynamic"
    FIXED = "fixed"


class ColorbarPosition (str, Enum):
    """Colorbar position"""
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"

class ColorbarLabelRotation(IntEnum):
    MINUS90 = -90
    POSITIVE90 = 90
