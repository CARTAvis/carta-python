"""This module provides a collection of classes corresponding to various enumerated types and other literal lists of options defined in the frontend. The properties of these classes should be used in place of literal strings and numbers to represent these values; for example: ``Colormap.VIRIDIS`` rather than ``"viridis"``. """


class Colormap:
    """All available colormaps."""
    pass


for colormap in ('copper', 'paired', 'gist_heat', 'brg', 'cool', 'summer', 'OrRd', 'tab20c', 'purples', 'gray', 'terrain', 'RdPu', 'set2', 'spring', 'gist_yarg', 'RdYlBu', 'reds', 'winter', 'Wistia', 'rainbow', 'dark2', 'oranges', 'BuPu', 'gist_earth', 'PuBu', 'pink', 'PuOr', 'pastel2', 'PiYG', 'gist_ncar', 'PuRd', 'plasma', 'gist_stern', 'hot', 'PuBuGn', 'YlOrRd', 'accent', 'magma', 'set1', 'GnBu', 'greens', 'CMRmap', 'gist_rainbow', 'prism', 'hsv', 'Blues', 'viridis', 'YlGn', 'spectral', 'RdBu', 'tab20', 'greys', 'flag', 'jet', 'seismic', 'PRGn', 'coolwarm', 'YlOrBr', 'RdYlGn', 'bone', 'autumn', 'BrBG', 'gnuplot2', 'RdGy', 'binary', 'gnuplot', 'BuGn', 'gist_gray', 'nipy_spectral', 'set3', 'tab20b', 'pastel1', 'afmhot', 'cubehelix', 'YlGnBu', 'ocean', 'tab10', 'bwr', 'inferno'):
    setattr(Colormap, colormap.upper(), colormap)


class Scaling:
    """Colormap scaling types."""
    LINEAR, LOG, SQRT, SQUARE, POWER, GAMMA = range(6)


class CoordinateSystem:
    """Coordinate systems."""
    pass


for system in ("Auto", "Ecliptic", "FK4", "FK5", "Galactic", "ICRS"):
    setattr(CoordinateSystem, system.upper(), system)


class LabelType:
    """Label types."""
    INTERNAL = "Internal"
    EXTERNAL = "External"


class BeamType:
    """Beam types."""
    OPEN = "Open"
    SOLID = "Solid"


class PaletteColor:
    """Palette colours used for overlay elements."""

    # Added manually so that they're available in the namespace for the dictionaries
    BLUE, ORANGE, GREEN, RED, VERMILION, ROSE, VIOLET, SEPIA, INDIGO, GRAY, LIME, TURQUOISE, FOREST, GOLD, COBALT, LIGHT_GRAY, DARK_GRAY, WHITE, BLACK = "auto-blue", "auto-orange", "auto-green", "auto-red", "auto-vermilion", "auto-rose", "auto-violet", "auto-sepia", "auto-indigo", "auto-gray", "auto-lime", "auto-turquoise", "auto-forest", "auto-gold", "auto-cobalt", "auto-light_gray", "auto-dark_gray", "auto-white", "auto-black"

    # BlueprintJS colour palettes (2 and 4)
    LIGHT = {
        DARK_GRAY: "#252a31",
        GRAY: "#738091",
        LIGHT_GRAY: "#dce0e5",
        BLUE: "#215db0",
        GREEN: "#1c6e42",
        ORANGE: "#935610",
        RED: "#ac2f33",
        VERMILION: "#b83211",
        ROSE: "#c22762",
        VIOLET: "#7c327c",
        INDIGO: "#634dbf",
        COBALT: "#2458b3",
        TURQUOISE: "#007067",
        FOREST: "#238c2c",
        LIME: "#5a701a",
        GOLD: "#866103",
        SEPIA: "#7a542e",
        WHITE: "#ffffff",
        BLACK: "#000000",
    }

    DARK = {
        DARK_GRAY: "#383e47",
        GRAY: "#abb3bf",
        LIGHT_GRAY: "#edeff2",
        BLUE: "#4c90f0",
        GREEN: "#32a467",
        ORANGE: "#ec9a3c",
        RED: "#e76a6e",
        VERMILION: "#eb6847",
        ROSE: "#f5498b",
        VIOLET: "#bd6bbd",
        INDIGO: "#9881f3",
        COBALT: "#4580e6",
        TURQUOISE: "#13c9ba",
        FOREST: "#43bf4d",
        LIME: "#b6d94c",
        GOLD: "#f0b726",
        SEPIA: "#af855a",
        WHITE: "#ffffff",
        BLACK: "#000000",
    }

    # Exclude these from validation of PaletteColor constants
    IGNORE = {"LIGHT", "DARK"}


class Overlay:
    """Overlay elements.

    The values of these properties are paths to stores corresponding to these elements, relative to the overlay store.
    """
    BEAM = "beam.settingsForDisplay"  # special case: an extra layer of indirection


for component in ("global", "title", "grid", "border", "ticks", "axes", "numbers", "labels", "colorbar"):
    setattr(Overlay, component.upper(), component)


class SmoothingMode:
    """Contour smoothing modes."""
    NO_SMOOTHING, BLOCK_AVERAGE, GAUSSIAN_BLUR = range(3)


class ContourDashMode:
    """Contour dash modes."""
    NONE = "None"
    DASHED = "Dashed"
    NEGATIVE_ONLY = "NegativeOnly"


class Polarization:
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
