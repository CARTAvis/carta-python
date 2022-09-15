"""This module provides a collection of enums corresponding to various enumerated types and other literal lists of options defined in the frontend. The members of these enums should be used in place of literal strings and numbers to represent these values; for example: ``Colormap.VIRIDIS`` rather than ``"viridis"``. """

from enum import Enum, IntEnum


# TODO make sure the __str__ is right for all the string values


Colormap = Enum('Colormap', {c.upper(): c for c in ('copper', 'paired', 'gist_heat', 'brg', 'cool', 'summer', 'OrRd', 'tab20c', 'purples', 'gray', 'terrain', 'RdPu', 'set2', 'spring', 'gist_yarg', 'RdYlBu', 'reds', 'winter', 'Wistia', 'rainbow', 'dark2', 'oranges', 'BuPu', 'gist_earth', 'PuBu', 'pink', 'PuOr', 'pastel2', 'PiYG', 'gist_ncar', 'PuRd', 'plasma', 'gist_stern', 'hot', 'PuBuGn', 'YlOrRd', 'accent', 'magma', 'set1', 'GnBu', 'greens', 'CMRmap', 'gist_rainbow', 'prism', 'hsv', 'Blues', 'viridis', 'YlGn', 'spectral', 'RdBu', 'tab20', 'greys', 'flag', 'jet', 'seismic', 'PRGn', 'coolwarm', 'YlOrBr', 'RdYlGn', 'bone', 'autumn', 'BrBG', 'gnuplot2', 'RdGy', 'binary', 'gnuplot', 'BuGn', 'gist_gray', 'nipy_spectral', 'set3', 'tab20b', 'pastel1', 'afmhot', 'cubehelix', 'YlGnBu', 'ocean', 'tab10', 'bwr', 'inferno')}, type=str)
Colormap.__doc__ = """All available colormaps."""


Scaling = Enum('Scaling', ('LINEAR', 'LOG', 'SQRT', 'SQUARE', 'POWER', 'GAMMA'), type=int, start=0)
Scaling.__doc__ = """Colormap scaling types."""


CoordinateSystem = Enum('CoordinateSystem', {c.upper(): c for c in ("Auto", "Ecliptic", "FK4", "FK5", "Galactic", "ICRS")}, type=str)
CoordinateSystem.__doc__ = """Coordinate systems."""


class LabelType(str, Enum):
    """Label types."""
    INTERNAL = "Internal"
    EXTERNAL = "External"


class BeamType(str, Enum):
    """Beam types."""
    OPEN = "Open"
    SOLID = "Solid"


PaletteColor = Enum("PaletteColor", {c.upper(): f"auto-{c}" for c in ("blue", "orange", "green", "red", "vermilion", "rose", "violet", "sepia", "indigo", "gray", "lime", "turquoise", "forest", "gold", "cobalt", "light_gray", "dark_gray", "white", "black")}, type=str)
PaletteColor.__doc__ = """Palette colours used for overlay elements."""

# BlueprintJS colour palettes (2 and 4)
LIGHT_THEME = {
    PaletteColor.DARK_GRAY: "#252a31",
    PaletteColor.GRAY: "#738091",
    PaletteColor.LIGHT_GRAY: "#dce0e5",
    PaletteColor.BLUE: "#215db0",
    PaletteColor.GREEN: "#1c6e42",
    PaletteColor.ORANGE: "#935610",
    PaletteColor.RED: "#ac2f33",
    PaletteColor.VERMILION: "#b83211",
    PaletteColor.ROSE: "#c22762",
    PaletteColor.VIOLET: "#7c327c",
    PaletteColor.INDIGO: "#634dbf",
    PaletteColor.COBALT: "#2458b3",
    PaletteColor.TURQUOISE: "#007067",
    PaletteColor.FOREST: "#238c2c",
    PaletteColor.LIME: "#5a701a",
    PaletteColor.GOLD: "#866103",
    PaletteColor.SEPIA: "#7a542e",
    PaletteColor.WHITE: "#ffffff",
    PaletteColor.BLACK: "#000000",
}

DARK_THEME = {
    PaletteColor.DARK_GRAY: "#383e47",
    PaletteColor.GRAY: "#abb3bf",
    PaletteColor.LIGHT_GRAY: "#edeff2",
    PaletteColor.BLUE: "#4c90f0",
    PaletteColor.GREEN: "#32a467",
    PaletteColor.ORANGE: "#ec9a3c",
    PaletteColor.RED: "#e76a6e",
    PaletteColor.VERMILION: "#eb6847",
    PaletteColor.ROSE: "#f5498b",
    PaletteColor.VIOLET: "#bd6bbd",
    PaletteColor.INDIGO: "#9881f3",
    PaletteColor.COBALT: "#4580e6",
    PaletteColor.TURQUOISE: "#13c9ba",
    PaletteColor.FOREST: "#43bf4d",
    PaletteColor.LIME: "#b6d94c",
    PaletteColor.GOLD: "#f0b726",
    PaletteColor.SEPIA: "#af855a",
    PaletteColor.WHITE: "#ffffff",
    PaletteColor.BLACK: "#000000",
}


Overlay = Enum('Overlay', [(c.upper(), c) for c in ("global", "title", "grid", "border", "ticks", "axes", "numbers", "labels", "colorbar")] + [('BEAM', 'beam.settingsForDisplay')], type=str)
Overlay.__doc__ = """Overlay elements.

    The values of these properties are paths to stores corresponding to these elements, relative to the overlay store.
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
