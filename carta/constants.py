"""This module provides a collection of enums corresponding to various enumerated types and other literal lists of options defined in the frontend. The members of these enums should be used in place of literal strings and numbers to represent these values; for example: ``Colormap.VIRIDIS`` rather than ``"viridis"``. """

from enum import Enum, IntEnum

# Fix for breaking change in 3.11
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Backwards-compatible base class for string enums."""
        pass


class ComplexComponent(StrEnum):
    """Complex component."""
    AMPLITUDE = "AMPLITUDE"
    PHASE = "PHASE"
    REAL = "REAL"
    IMAG = "IMAG"


Colormap = StrEnum('Colormap', {c.upper(): c for c in ('copper', 'paired', 'gist_heat', 'brg', 'cool', 'summer', 'OrRd', 'tab20c', 'purples', 'gray', 'terrain', 'RdPu', 'set2', 'spring', 'gist_yarg', 'RdYlBu', 'reds', 'winter', 'Wistia', 'rainbow', 'dark2', 'oranges', 'BuPu', 'gist_earth', 'PuBu', 'pink', 'PuOr', 'pastel2', 'PiYG', 'gist_ncar', 'PuRd', 'plasma', 'gist_stern', 'hot', 'PuBuGn', 'YlOrRd', 'accent', 'magma', 'set1', 'GnBu', 'greens', 'CMRmap', 'gist_rainbow', 'prism', 'hsv', 'Blues', 'viridis', 'YlGn', 'spectral', 'RdBu', 'tab20', 'greys', 'flag', 'jet', 'seismic', 'PRGn', 'coolwarm', 'YlOrBr', 'RdYlGn', 'bone', 'autumn', 'BrBG', 'gnuplot2', 'RdGy', 'binary', 'gnuplot', 'BuGn', 'gist_gray', 'nipy_spectral', 'set3', 'tab20b', 'pastel1', 'afmhot', 'cubehelix', 'YlGnBu', 'ocean', 'tab10', 'bwr', 'inferno')})
Colormap.__doc__ = """All available colormaps."""


Scaling = IntEnum('Scaling', ('LINEAR', 'LOG', 'SQRT', 'SQUARE', 'POWER', 'GAMMA'), start=0)
Scaling.__doc__ = """Colormap scaling types."""


CoordinateSystem = StrEnum('CoordinateSystem', {c: c for c in ("AUTO", "ECLIPTIC", "FK4", "FK5", "GALACTIC", "ICRS")})
CoordinateSystem.__doc__ = """Coordinate systems."""


class NumberFormat(StrEnum):
    """Number formats."""
    DEGREES = "d"
    HMS = "hms"
    DMS = "dms"


class SpatialAxis(StrEnum):
    """Spatial axes."""
    X = "x"
    Y = "y"


class LabelType(StrEnum):
    """Label types."""
    INTERIOR = "Interior"
    EXTERIOR = "Exterior"


class BeamType(StrEnum):
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


class PaletteColor(StrEnum):
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


Overlay = StrEnum('Overlay', [(c.upper(), c) for c in ("global", "title", "grid", "border", "ticks", "axes", "numbers", "labels", "colorbar")] + [('BEAM', 'beam.settingsForDisplay')])
Overlay.__doc__ = """Overlay elements.

    Member values are paths to stores corresponding to these elements, relative to the overlay store.
    """


class SmoothingMode(IntEnum):
    """Contour smoothing modes."""
    NO_SMOOTHING = 0
    BLOCK_AVERAGE = 1
    GAUSSIAN_BLUR = 2


class Auto(StrEnum):
    """Special value for parameters to be calculated automatically."""
    AUTO = "Auto"


class ContourDashMode(StrEnum):
    """Contour dash modes."""
    NONE = "None"
    DASHED = "Dashed"
    NEGATIVE_ONLY = "NegativeOnly"


PROTO_POLARIZATION = {
    "I": 1,
    "Q": 2,
    "U": 3,
    "V": 4,
    "RR": 5,
    "LL": 6,
    "RL": 7,
    "LR": 8,
    "XX": 9,
    "YY": 10,
    "XY": 11,
    "YX": 12,
    "PTOTAL": 13,
    "PLINEAR": 14,
    "PFTOTAL": 15,
    "PFLINEAR": 16,
    "PANGLE": 17,
}


class Polarization(IntEnum):
    """Polarizations, corresponding to the POLARIZATIONS enum in the frontend."""

    def __init__(self, value):
        self.proto_index = PROTO_POLARIZATION[self.name]

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


class PanelMode(IntEnum):
    """Panel modes."""
    SINGLE = 0
    MULTIPLE = 1


class GridMode(StrEnum):
    """Grid modes."""
    DYNAMIC = "dynamic"
    FIXED = "fixed"


class FileType(IntEnum):
    """File types corresponding to the protobuf enum."""
    CASA = 0
    CRTF = 1
    DS9_REG = 2
    FITS = 3
    HDF5 = 4
    MIRIAD = 5
    UNKNOWN = 6


class RegionType(IntEnum):
    """Region types corresponding to the protobuf enum."""

    def __init__(self, value):
        self.is_annotation = self.name.startswith("ANN")
        self.label = f"{self.name[3:].title()} - Ann" if self.is_annotation else self.name.title()

    POINT = 0
    LINE = 1
    POLYLINE = 2
    RECTANGLE = 3
    ELLIPSE = 4
    ANNULUS = 5
    POLYGON = 6
    ANNPOINT = 7
    ANNLINE = 8
    ANNPOLYLINE = 9
    ANNRECTANGLE = 10
    ANNELLIPSE = 11
    ANNPOLYGON = 12
    ANNVECTOR = 13
    ANNRULER = 14
    ANNTEXT = 15
    ANNCOMPASS = 16


class CoordinateType(IntEnum):
    """Coordinate types corresponding to the protobuf enum."""
    PIXEL = 0
    WORLD = 1


class PointShape(IntEnum):
    """Point annotation shapes corresponding to the protobuf enum."""
    SQUARE = 0
    BOX = 1
    CIRCLE = 2
    CIRCLE_LINED = 3
    DIAMOND = 4
    DIAMOND_LINED = 5
    CROSS = 6
    X = 7


class TextPosition(IntEnum):
    """Text annotation positions corresponding to the protobuf enum."""
    CENTER = 0
    UPPER_LEFT = 1
    UPPER_RIGHT = 2
    LOWER_LEFT = 3
    LOWER_RIGHT = 4
    TOP = 5
    BOTTOM = 6
    LEFT = 7
    RIGHT = 8


class AnnotationFontStyle(StrEnum):
    """Font styles which may be used in annotations."""
    NORMAL = "Normal"
    BOLD = "Bold"
    ITALIC = "Italic"
    BOLD_ITALIC = "Italic Bold"


class AnnotationFont(StrEnum):
    """Fonts which may be used in annotations."""
    HELVETICA = "Helvetica"
    TIMES = "Times"
    COURIER = "Courier"
