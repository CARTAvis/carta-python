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


class ColormapSet(StrEnum):
    """Colormap sets for color blending."""
    RGB = "RGB"
    CMY = "CMY"
    Rainbow = "Rainbow"


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
    OPEN = "open"
    SOLID = "solid"


# BlueprintJS colour palettes (2 and 4)
LIGHT_THEME = {
    "BLACK": "#10161a",
    "BLUE": "#106ba3",
    "COBALT": "#2458b3",
    "DARK_GRAY": "#202b33",
    "FOREST": "#238c2c",
    "GOLD": "#bf8c0a",
    "GRAY": "#738694",
    "GREEN": "#0d8050",
    "INDIGO": "#634dbf",
    "LIGHT_GRAY": "#d8e1e8",
    "LIME": "#87a629",
    "ORANGE": "#bf7326",
    "RED": "#c23030",
    "ROSE": "#c22762",
    "SEPIA": "#7d5125",
    "TURQUOISE": "#00998c",
    "VERMILION": "#b83211",
    "VIOLET": "#752f75",
    "WHITE": "#ffffff",
}

DARK_THEME = {
    "BLACK": "#10161a",
    "BLUE": "#2b95d6",
    "COBALT": "#4580e6",
    "DARK_GRAY": "#30404d",
    "FOREST": "#43bf4d",
    "GOLD": "#f2b824",
    "GRAY": "#a7b6c2",
    "GREEN": "#15b371",
    "INDIGO": "#9179f2",
    "LIGHT_GRAY": "#ebf1f5",
    "LIME": "#b6d94c",
    "ORANGE": "#f29d49",
    "RED": "#f55656",
    "ROSE": "#f5498b",
    "SEPIA": "#b07b46",
    "TURQUOISE": "#14ccbd",
    "VERMILION": "#eb532d",
    "VIOLET": "#a854a8",
    "WHITE": "#ffffff",
}


class PaletteColor(StrEnum):
    """Palette colours used for WCS overlay elements.

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
Overlay.__doc__ = """WCS overlay elements.

    Member values are paths to stores corresponding to these elements, relative to the WCS overlay store.
    """


class SmoothingMode(IntEnum):
    """Contour smoothing modes."""
    NO_SMOOTHING = 0
    BLOCK_AVERAGE = 1
    GAUSSIAN_BLUR = 2


VectorOverlaySource = Enum('VectorOverlaySource', ('NONE', 'CURRENT', 'COMPUTED'), type=int, start=-1)
VectorOverlaySource.__doc__ = """Vector overlay source."""


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


class FontFamily(IntEnum):
    """Font family used in WCS overlay components."""
    SANS_SERIF = 0
    TIMES = 1
    ARIAL = 2
    PALATINO = 3
    COURIER_NEW = 4


class FontStyle(IntEnum):
    """Font style used in WCS overlay components."""
    NORMAL = 0
    ITALIC = 1
    BOLD = 2
    BOLD_ITALIC = 3


class ColorbarPosition(StrEnum):
    """Colorbar positions."""
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class SpectralSystem(StrEnum):
    """Spectral systems."""
    LSRK = "LSRK"
    LSRD = "LSRD"
    BARY = "BARYCENT"
    TOPO = "TOPOCENT"


class SpectralUnit(StrEnum):
    """Spectral units."""
    KMS = "km/s"
    MS = "m/s"
    GHZ = "GHz"
    MHZ = "MHz"
    KHZ = "kHz"
    HZ = "Hz"
    M = "m"
    MM = "mm"
    UM = "um"
    NM = "nm"
    ANGSTROM = "Angstrom"


SPECTRAL_TYPE_DESCRIPTION = {
    "VRAD": "Radio velocity",
    "VOPT": "Optical velocity",
    "FREQ": "Frequency",
    "WAVE": "Vacuum wavelength",
    "AWAV": "Air wavelength",
}


SPECTRAL_TYPE_UNITS = {
    "VRAD": (SpectralUnit.KMS, SpectralUnit.MS),
    "VOPT": (SpectralUnit.KMS, SpectralUnit.MS),
    "FREQ": (SpectralUnit.GHZ, SpectralUnit.MHZ, SpectralUnit.KHZ, SpectralUnit.HZ),
    "WAVE": (SpectralUnit.MM, SpectralUnit.M, SpectralUnit.UM, SpectralUnit.NM, SpectralUnit.ANGSTROM),
    "AWAV": (SpectralUnit.MM, SpectralUnit.M, SpectralUnit.UM, SpectralUnit.NM, SpectralUnit.ANGSTROM),
}


class SpectralType(StrEnum):
    """Spectral types.

    Members of this enum class have additional attributes.

    Attributes
    ----------
    description : string
        The human-readable description of this type.
    units : set of :obj:`carta.constants.SpectralUnit`
        The units supported for this type.
    default_unit : :obj:`carta.constants.SpectralUnit`
        The default unit for this type.
    """

    def __init__(self, value):
        self.description = SPECTRAL_TYPE_DESCRIPTION[self.name]
        self.units = set(SPECTRAL_TYPE_UNITS[self.name])
        self.default_unit = SPECTRAL_TYPE_UNITS[self.name][0]

    VRAD = "VRAD",
    VOPT = "VOPT",
    FREQ = "FREQ",
    WAVE = "WAVE",
    AWAV = "AWAV",
