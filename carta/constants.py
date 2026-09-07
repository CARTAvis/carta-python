"""This module provides a collection of enums corresponding to various enumerated types and other literal lists of options defined in the frontend. The members of these enums should be used in place of literal strings and numbers to represent these values; for example: ``Colormap.VIRIDIS`` rather than ``"viridis"``. """

from enum import Enum, IntEnum

# Fix for breaking change in 3.11
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Backwards-compatible base class for string enums."""
        pass


class _RegisteredEnum:
    """Mixin implementation shared by externally defined enum registries."""

    ENUMS = {}

    def __init_subclass__(cls, *, external_name=None, **kwargs):
        """Register an enum subclass by its external name."""
        super().__init_subclass__(**kwargs)
        if _RegisteredEnum in cls.__bases__:
            return
        external_name = external_name or cls.__name__
        if external_name in cls.ENUMS:
            raise ValueError(f"Duplicate enum external name {external_name!r} in {cls.__mro__[1].__name__}")
        cls.EXTERNAL_NAME = external_name
        cls.ENUMS[external_name] = cls


class FrontendEnum(_RegisteredEnum):
    """Mixin for enums defined and validated by the CARTA frontend."""

    ENUMS = {}


class ProtobufEnum(_RegisteredEnum):
    """Mixin for enums defined and validated by CARTA protobuf messages."""

    ENUMS = {}


class CartaPythonEnum(_RegisteredEnum):
    """Mixin for enums defined and used only by carta-python."""

    ENUMS = {}


def _registered_enum(registry, enum_type, enum_name, names, external_name=None, **kwargs):
    """Create a functional enum and register it with the requested mixin."""
    enum_ = enum_type(enum_name, names, type=registry, **kwargs)
    if external_name is not None:
        _set_external_name(enum_, registry, external_name)
    return enum_


def _set_external_name(enum_, registry, external_name):
    """Set a custom name after EnumMeta has constructed an enum class."""
    existing = registry.ENUMS.get(external_name)
    if existing is not None and existing is not enum_:
        del registry.ENUMS[enum_.__name__]
        raise ValueError(f"Duplicate enum external name {external_name!r} in {registry.__name__}")
    del registry.ENUMS[enum_.__name__]
    enum_.EXTERNAL_NAME = external_name
    registry.ENUMS[external_name] = enum_


class ComplexComponent(CartaPythonEnum, StrEnum):
    """Complex component."""
    AMPLITUDE = "AMPLITUDE"
    PHASE = "PHASE"
    REAL = "REAL"
    IMAG = "IMAG"


Colormap = _registered_enum(FrontendEnum, StrEnum, 'Colormap', {c.upper(): c for c in ('copper', 'paired', 'gist_heat', 'brg', 'cool', 'summer', 'OrRd', 'tab20c', 'purples', 'gray', 'terrain', 'RdPu', 'set2', 'spring', 'gist_yarg', 'RdYlBu', 'reds', 'winter', 'Wistia', 'rainbow', 'dark2', 'oranges', 'BuPu', 'gist_earth', 'PuBu', 'pink', 'PuOr', 'pastel2', 'PiYG', 'gist_ncar', 'PuRd', 'plasma', 'gist_stern', 'hot', 'PuBuGn', 'YlOrRd', 'accent', 'magma', 'set1', 'GnBu', 'greens', 'CMRmap', 'gist_rainbow', 'prism', 'hsv', 'Blues', 'viridis', 'YlGn', 'spectral', 'RdBu', 'tab20', 'greys', 'flag', 'jet', 'seismic', 'PRGn', 'coolwarm', 'YlOrBr', 'RdYlGn', 'bone', 'autumn', 'BrBG', 'gnuplot2', 'RdGy', 'binary', 'gnuplot', 'BuGn', 'gist_gray', 'nipy_spectral', 'set3', 'tab20b', 'pastel1', 'afmhot', 'cubehelix', 'YlGnBu', 'ocean', 'tab10', 'bwr', 'inferno', 'Blue', 'Cyan', 'Green', 'Magenta', 'Orange', 'Red', 'Violet', 'Yellow')}, external_name="ColorMap")
Colormap.__doc__ = """All available colormaps."""


class ColormapSet(FrontendEnum, StrEnum):
    """Colormap sets for color blending."""
    RGB = "RGB"
    CMY = "CMY"
    RAINBOW = "Rainbow"


class ImageType(FrontendEnum, IntEnum):
    """Image view item types, corresponding to the frontend ImageType enum."""
    FRAME = 0
    COLOR_BLENDING = 1
    PV_PREVIEW = 2


Scaling = _registered_enum(FrontendEnum, IntEnum, 'Scaling', ('LINEAR', 'LOG', 'SQRT', 'SQUARE', 'POWER', 'GAMMA', 'EXP', 'CUSTOM', 'SINH', 'ASINH'), external_name="FrameScaling", start=0)
Scaling.__doc__ = """Colormap scaling types."""
CoordinateSystem = _registered_enum(FrontendEnum, StrEnum, 'CoordinateSystem', {c: c for c in ("AUTO", "ECLIPTIC", "FK4", "FK5", "GALACTIC", "ICRS")} | {"IMAGE": "CARTESIAN"}, external_name="SystemType")
CoordinateSystem.__doc__ = """Coordinate systems."""


class NumberFormat(FrontendEnum, StrEnum, external_name="NumberFormatType"):
    """Number formats."""
    DEGREES = "d"
    HMS = "hms"
    DMS = "dms"


class SpatialAxis(CartaPythonEnum, StrEnum):
    """Spatial axes."""
    X = "x"
    Y = "y"


class LabelType(FrontendEnum, StrEnum):
    """Label types."""
    INTERIOR = "Interior"
    EXTERIOR = "Exterior"


class BeamType(FrontendEnum, StrEnum):
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


class PaletteColor(CartaPythonEnum, StrEnum):
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


Overlay = _registered_enum(CartaPythonEnum, StrEnum, 'Overlay', [(c.upper(), c) for c in ("global", "title", "grid", "border", "ticks", "axes", "numbers", "labels", "colorbar")] + [('BEAM', 'beam.settingsForDisplay')])
Overlay.__doc__ = """WCS overlay elements.

    Member values are paths to stores corresponding to these elements, relative to the WCS overlay store.
    """
class SmoothingMode(ProtobufEnum, IntEnum, external_name="SmoothingMode"):
    """Contour smoothing modes."""
    NO_SMOOTHING = 0
    BLOCK_AVERAGE = 1
    GAUSSIAN_BLUR = 2


VectorOverlaySource = _registered_enum(FrontendEnum, Enum, 'VectorOverlaySource', ('NONE', 'CURRENT', 'COMPUTED'), start=-1)
VectorOverlaySource.__doc__ = """Vector overlay source."""


class Auto(CartaPythonEnum, StrEnum):
    """Special value for parameters to be calculated automatically."""
    AUTO = "Auto"


class ContourDashMode(FrontendEnum, StrEnum):
    """Contour dash modes."""
    NONE = "None"
    DASHED = "Dashed"
    NEGATIVE_ONLY = "Negative only"


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


class Polarization(FrontendEnum, IntEnum, external_name="Polarizations"):
    """Polarizations."""
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


class PanelMode(CartaPythonEnum, IntEnum):
    """Panel modes."""
    SINGLE = 0
    MULTIPLE = 1


class GridMode(FrontendEnum, StrEnum, external_name="ImagePanelMode"):
    """Grid modes."""
    DYNAMIC = "dynamic"
    FIXED = "fixed"
    NONE = "none"


class FileType(ProtobufEnum, IntEnum, external_name="FileType"):
    """File types corresponding to the protobuf enum."""
    CASA = 0
    CRTF = 1
    DS9_REG = 2
    FITS = 3
    HDF5 = 4
    MIRIAD = 5
    UNKNOWN = 6


class RegionType(ProtobufEnum, IntEnum, external_name="RegionType"):
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


class CoordinateType(ProtobufEnum, IntEnum, external_name="CoordinateType"):
    """Coordinate types corresponding to the protobuf enum."""
    PIXEL = 0
    WORLD = 1


class PointShape(ProtobufEnum, IntEnum, external_name="PointAnnotationShape"):
    """Point annotation shapes corresponding to the protobuf enum."""
    SQUARE = 0
    BOX = 1
    CIRCLE = 2
    CIRCLE_LINED = 3
    DIAMOND = 4
    DIAMOND_LINED = 5
    CROSS = 6
    X = 7


class TextPosition(ProtobufEnum, IntEnum, external_name="TextAnnotationPosition"):
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


class AnnotationFontStyle(FrontendEnum, StrEnum, external_name="FontStyle"):
    """Font styles which may be used in annotations."""
    NORMAL = "Normal"
    BOLD = "Bold"
    ITALIC = "Italic"
    BOLD_ITALIC = "Italic Bold"


class AnnotationFont(FrontendEnum, StrEnum, external_name="Font"):
    """Fonts which may be used in annotations."""
    HELVETICA = "Helvetica"
    TIMES = "Times"
    COURIER = "Courier"


class FontFamily(CartaPythonEnum, IntEnum):
    """Font family used in WCS overlay components."""
    SANS_SERIF = 0
    TIMES = 1
    ARIAL = 2
    PALATINO = 3
    COURIER_NEW = 4


class FontStyle(CartaPythonEnum, IntEnum):
    """Font style used in WCS overlay components."""
    NORMAL = 0
    ITALIC = 1
    BOLD = 2
    BOLD_ITALIC = 3


class ColorbarPosition(CartaPythonEnum, StrEnum):
    """Colorbar positions."""
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class SpectralSystem(FrontendEnum, StrEnum):
    """Spectral systems."""
    LSRK = "LSRK"
    LSRD = "LSRD"
    BARY = "BARYCENT"
    TOPO = "TOPOCENT"


class SpectralUnit(FrontendEnum, StrEnum):
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
    M_SQUARE = "m^2"
    MM_SQUARE = "mm^2"
    UM_SQUARE = "um^2"
    NM_SQUARE = "nm^2"
    ANGSTROM_SQUARE = "Angstrom^2"


SPECTRAL_TYPE_DESCRIPTION = {
    "CHANNEL": "Channel",
    "NATIVE": "Native",
    "VRAD": "Radio velocity",
    "VOPT": "Optical velocity",
    "FREQ": "Frequency",
    "WAVE": "Vacuum wavelength",
    "AWAV": "Air wavelength",
}


SPECTRAL_TYPE_UNITS = {
    "CHANNEL": tuple(),
    "NATIVE": tuple(),
    "VRAD": (SpectralUnit.KMS, SpectralUnit.MS),
    "VOPT": (SpectralUnit.KMS, SpectralUnit.MS),
    "FREQ": (SpectralUnit.GHZ, SpectralUnit.MHZ, SpectralUnit.KHZ, SpectralUnit.HZ),
    "WAVE": (SpectralUnit.MM, SpectralUnit.M, SpectralUnit.UM, SpectralUnit.NM, SpectralUnit.ANGSTROM),
    "AWAV": (SpectralUnit.MM, SpectralUnit.M, SpectralUnit.UM, SpectralUnit.NM, SpectralUnit.ANGSTROM),
}


class SpectralType(FrontendEnum, StrEnum):
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
        units = SPECTRAL_TYPE_UNITS[self.name]
        self.description = SPECTRAL_TYPE_DESCRIPTION[self.name]
        self.units = set(units)
        self.default_unit = units[0] if units else None

    CHANNEL = "CHANNEL",
    NATIVE = "NATIVE",
    VRAD = "VRAD",
    VOPT = "VOPT",
    FREQ = "FREQ",
    WAVE = "WAVE",
    AWAV = "AWAV",
