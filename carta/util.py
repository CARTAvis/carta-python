"""This module provides miscellaneous utility classes and functions used by the wrapper."""

import logging
import json
import functools
import re
import math

from .constants import NumberFormat, SpatialAxis

logger = logging.getLogger("carta_scripting")
logger.setLevel(logging.WARN)
logger.addHandler(logging.StreamHandler())


class CartaScriptingException(Exception):
    """The top-level exception for all scripting errors."""
    pass


class CartaBadSession(CartaScriptingException):
    """A session could not be constructed."""
    pass


class CartaBadID(CartaScriptingException):
    """A session ID is invalid."""
    pass


class CartaBadToken(CartaScriptingException):
    """A token has expired or is invalid."""
    pass


class CartaBadUrl(CartaScriptingException):
    """An URL is invalid."""
    pass


class CartaValidationFailed(CartaScriptingException):
    """Invalid parameters were passed to a function with a :obj:`carta.validation.validate` decorator."""
    pass


class CartaBadRequest(CartaScriptingException):
    """A request sent to the CARTA backend was rejected."""
    pass


class CartaRequestFailed(CartaScriptingException):
    """A request received a failure response from the CARTA backend."""
    pass


class CartaActionFailed(CartaScriptingException):
    """An action request received a failure response from the CARTA frontend."""
    pass


class CartaBadResponse(CartaScriptingException):
    """An action request received an unexpected response from the CARTA frontend."""
    pass


class Macro:
    """A placeholder for a target and a variable which will be evaluated dynamically by the frontend.

    Parameters
    ----------
    target : str
        The target frontend object.
    variable : str
        The variable on the target object.

    Attributes
    ----------
    target : str
        The target frontend object.
    variable : str
        The variable on the target object.
    """

    def __init__(self, target, variable):
        self.target = target
        self.variable = variable

    def __repr__(self):
        return f"Macro('{self.target}', '{self.variable}')"

    def __eq__(self, other):
        return repr(self) == repr(other)

    def json(self):
        """The JSON serialization of this object."""
        return {"macroTarget": self.target, "macroVariable": self.variable}


class Undefined(Macro):
    """
    A subclass of Macro to construct a placeholder for `"undefined"`.
    """

    def __init__(self):
        super().__init__(target="", variable="undefined")


class CartaEncoder(json.JSONEncoder):
    """A custom encoder to JSON which correctly serialises custom objects with a ``json`` method, and numpy arrays."""

    def default(self, obj):
        """ This method is overridden from the parent class and performs the substitution."""
        if hasattr(obj, "json") and callable(obj.json):
            return obj.json()
        if type(obj).__module__ == "numpy" and type(obj).__name__ == "ndarray":
            # The condition is a workaround to avoid importing numpy
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def cached(func):
    """A decorator which transparently caches the return value of the decorated method on the parent object.

    This should only be used on methods with return values which are not expected to change for the lifetime of the object.
    """
    @functools.wraps(func)
    def newfunc(self, *args):
        if not hasattr(self, "_cache"):
            self._cache = {}

        if func.__name__ not in self._cache:
            self._cache[func.__name__] = func(self, *args)

        return self._cache[func.__name__]

    if newfunc.__doc__ is not None:
        newfunc.__doc__ = re.sub(r"($|\n)", r" This value is transparently cached on the parent object.\1", newfunc.__doc__, 1)

    return newfunc


def split_action_path(path):
    """Extracts a path to a frontend object store and an action from a combined path.
    """
    parts = path.split('.')
    return '.'.join(parts[:-1]), parts[-1]


class PixelValue:
    """Parses pixel values."""

    UNITS = {"px", "pix", "pixel", "pixels"}
    UNIT_REGEX = rf"^(-?\d+(?:\.\d+)?)\s*(?:{'|'.join(UNITS)})$"

    @classmethod
    def valid(cls, value):
        """Whether the input string is a numeric value followed by a pixel unit.

        Permitted pixel unit strings are stored in :obj:`carta.util.PixelValue.UNITS`. Whitespace is permitted after the number and before the unit. Pixel values may be negative.

        Parameters
        ----------
        value : string
            The input string.

        Returns
        -------
        boolean
            Whether the input string is a pixel value.
        """
        m = re.match(cls.UNIT_REGEX, value, re.IGNORECASE)
        return m is not None

    @classmethod
    def as_float(cls, value):
        """Parse a string containing a numeric value followed by a pixel unit, and return the numeric part as a float.

        Permitted pixel unit strings are stored in :obj:`carta.util.PixelValue.UNITS`. Whitespace is permitted after the number and before the unit.

        Parameters
        ----------
        value : string
            The string representation of the pixel value.

        Returns
        -------
        float
            The numeric portion of the pixel value.

        Raises
        ------
        ValueError
            If the input string is not in a recognized format.
        """
        m = re.match(cls.UNIT_REGEX, value, re.IGNORECASE)
        if m is None:
            raise ValueError(f"{repr(value)} is not in a recognized pixel format.")
        return float(m.group(1))


class AngularSize:
    """An angular size.

    This class provides methods for parsing angular sizes with any known unit, and should not be instantiated directly. Child classes can be used directly if the unit is known.

    Child class instances have a string representation in a normalized format which can be parsed by the frontend.
    """
    FORMATS = {}
    NAME = "angular size"

    def __init__(self, value):
        self.value = value

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._update_unit_regex(cls.INPUT_UNITS)

        for unit in cls.INPUT_UNITS:
            AngularSize.FORMATS[unit] = cls

        AngularSize._update_unit_regex(AngularSize.FORMATS.keys())

    @classmethod
    def _update_unit_regex(cls, units):
        """Update the unit regexes using the provided unit set."""
        symbols = {u for u in units if len(u) <= 1}
        words = units - symbols

        cls.SYMBOL_UNIT_REGEX = rf"^(\d+(?:\.\d+)?)({'|'.join(symbols)})$"
        cls.WORD_UNIT_REGEX = rf"^(\d+(?:\.\d+)?)\s*({'|'.join(words)})$"

    @classmethod
    def valid(cls, value):
        """Whether the input string is a numeric value followed by an angular size unit.

        A number without a unit is assumed to be in arcseconds. Permitted unit strings and their mappings to normalized units are stored in subclasses of :obj:`carta.util.AngularSize`. Whitespace is permitted after the number and before a unit which is a word, but not before a single-character unit.

        This method may also be used from child classes if a specific format is required.

        Parameters
        ----------
        value : string
            The input string.

        Returns
        -------
        boolean
            Whether the input string is an angular size.
        """
        return any((re.match(cls.WORD_UNIT_REGEX, value, re.IGNORECASE), re.match(cls.SYMBOL_UNIT_REGEX, value, re.IGNORECASE)))

    @classmethod
    def from_string(cls, value):
        """Construct an angular size object from a string.

        A number without a unit is assumed to be in arcseconds. Permitted unit strings and their mappings to normalized units are stored in subclasses of :obj:`carta.util.AngularSize`. Whitespace is permitted after the number and before a unit which is a word, but not before a single-character unit.

        This method may also be used from child classes if a specific format is required.

        Parameters
        ----------
        value : string
            The string representation of the angular size.

        Returns
        -------
        :obj:`carta.util.AngularSize`
            The angular size object.

        Raises
        ------
        ValueError
            If the angular size string is not in a recognized format.
        """
        m = re.match(cls.WORD_UNIT_REGEX, value, re.IGNORECASE)
        if m is None:
            m = re.match(cls.SYMBOL_UNIT_REGEX, value, re.IGNORECASE)
            if m is None:
                raise ValueError(f"{repr(value)} is not in a recognized {cls.NAME} format.")
        value, unit = m.groups()
        if cls is AngularSize:
            return cls.FORMATS[unit](float(value))
        return cls(float(value))

    def __str__(self):
        if type(self) is AngularSize:
            raise NotImplementedError()
        value = self.value * self.FACTOR
        return f"{value:g}{self.OUTPUT_UNIT}"


class DegreesSize(AngularSize):
    """An angular size in degrees."""
    NAME = "degree"
    INPUT_UNITS = {"deg", "degree", "degrees"}
    OUTPUT_UNIT = "deg"
    FACTOR = 1


class ArcminSize(AngularSize):
    """An angular size in arcminutes."""
    NAME = "arcminute"
    INPUT_UNITS = {"'", "arcminutes", "arcminute", "arcmin", "amin", "′"}
    OUTPUT_UNIT = "'"
    FACTOR = 1


class ArcsecSize(AngularSize):
    """An angular size in arcseconds."""
    NAME = "arcsecond"
    INPUT_UNITS = {"\"", "", "arcseconds", "arcsecond", "arcsec", "asec", "″"}
    OUTPUT_UNIT = "\""
    FACTOR = 1


class MilliarcsecSize(AngularSize):
    """An angular size in milliarcseconds."""
    NAME = "milliarcsecond"
    INPUT_UNITS = {"milliarcseconds", "milliarcsecond", "milliarcsec", "mas"}
    OUTPUT_UNIT = "\""
    FACTOR = 1e-3


class MicroarcsecSize(AngularSize):
    """An angular size in microarcseconds."""
    NAME = "microarcsecond"
    INPUT_UNITS = {"microarcseconds", "microarcsecond", "microarcsec", "µas", "uas"}
    OUTPUT_UNIT = "\""
    FACTOR = 1e-6


class WorldCoordinate:
    """A world coordinate."""

    FMT = None
    FORMATS = {}

    def __init_subclass__(cls, **kwargs):
        """Automatically register subclasses corresponding to number formats."""
        super().__init_subclass__(**kwargs)
        if isinstance(cls.FMT, NumberFormat):
            super(cls, cls).FORMATS[cls.FMT] = cls

    @classmethod
    def valid(cls, value):
        """Whether the input string is a world coordinate string in any of the recognised formats.

        Coordinates may be provided in HMS or DMS format (with colons or letters as separators), or in degrees (with or without an explicit unit). Permitted degree unit strings are stored in :obj:`carta.util.DegreesCoordinate.DEGREE_UNITS`.

        Parameters
        ----------
        value : string
            The input string.

        Returns
        -------
        boolean
            Whether the input string is a valid world coordinate.
        """
        if cls is WorldCoordinate:
            return any(fmt.valid(value) for fmt in cls.FORMATS.values())
        return any(re.match(exp, value, re.IGNORECASE) for exp in cls.REGEX.values())

    @classmethod
    def with_format(cls, fmt):
        """Return the subclass of :obj:`carta.util.WorldCoordinate` corresponding to the specified format."""
        if isinstance(fmt, NumberFormat):
            return cls.FORMATS[fmt]
        raise ValueError(f"Unknown number format: {fmt}")

    @classmethod
    def from_string(cls, value, axis):
        """Construct a world coordinate object from a string.

        This is implemented in subclasses corresponding to different formats.

        Parameters
        ----------
        value : string
            The input string.
        axis : :obj:`carta.constants.SpatialAxis`
            The spatial axis of this coordinate.

        Returns
        -------
        :obj:`carta.util.WorldCoordinate`
            The coordinate object.
        """
        raise NotImplementedError()


class DegreesCoordinate(WorldCoordinate):
    """A world coordinate in decimal degree format."""
    FMT = NumberFormat.DEGREES
    DEGREE_UNITS = DegreesSize.INPUT_UNITS
    REGEX = {
        "DEGREE_UNIT": rf"^-?(\d+(?:\.\d+)?)\s*({'|'.join(DEGREE_UNITS)})$",
        "DECIMAL": r"^-?\d+(\.\d+)?$",
    }

    @classmethod
    def from_string(cls, value, axis):
        """Construct a world coordinate object in decimal degree format from a string.

        Coordinates may be provided with or without an explicit unit. Permitted degree unit strings are stored in :obj:`carta.util.DegreesCoordinate.DEGREE_UNITS`.

        Parameters
        ----------
        value : string
            The input string.
        axis : :obj:`carta.constants.SpatialAxis`
            The spatial axis of this coordinate.

        Returns
        -------
        :obj:`carta.util.DegreesCoordinate`
            The coordinate object.
        """
        m = re.match(cls.REGEX["DECIMAL"], value, re.IGNORECASE)
        if m is not None:
            fvalue = float(value)
        else:
            m = re.match(cls.REGEX["DEGREE_UNIT"], value, re.IGNORECASE)
            if m is not None:
                fvalue = float(m.group(1))
            else:
                raise ValueError(f"Coordinate string {value} does not match expected format {cls.FMT}.")

        if axis == SpatialAxis.X and not 0 <= fvalue < 360:
            raise ValueError(f"Degrees coordinate string {value} is outside the permitted longitude range [0, 360).")
        if axis == SpatialAxis.Y and not -90 <= fvalue <= 90:
            raise ValueError(f"Degrees coordinate string {value} is outside the permitted latitude range [-90, 90].")

        return cls(fvalue)

    def __init__(self, degrees):
        self.degrees = degrees

    def __str__(self):
        return f"{self.degrees:g}"


class SexagesimalCoordinate(WorldCoordinate):
    """A world coordinate in sexagesimal format.

    This class contains common functionality for parsing the HMS and DMS formats.
    """

    @classmethod
    def from_string(cls, value, axis):
        """Construct a world coordinate object in sexagesimal format from a string.

        Coordinates may be provided in HMS or DMS format with colons or letters as separators. The value range will be validated for the provided spatial axis.

        Parameters
        ----------
        value : string
            The input string.
        axis : :obj:`carta.constants.SpatialAxis`
            The spatial axis of this coordinate.

        Returns
        -------
        :obj:`carta.util.SexagesimalCoordinate`
            The coordinate object.
        """
        def to_float(strs):
            return tuple(0 if s is None else float(s) for s in strs)

        m = re.match(cls.REGEX["COLON"], value, re.IGNORECASE)
        if m is not None:
            return cls(*to_float(m.groups()))

        m = re.match(cls.REGEX["LETTER"], value, re.IGNORECASE)
        if m is not None:
            return cls(*to_float(m.groups()))

        raise ValueError(f"Coordinate string {value} does not match expected format {cls.FMT}.")

    def __init__(self, hours_or_degrees, minutes, seconds):
        self.hours_or_degrees = hours_or_degrees
        self.minutes = minutes
        self.seconds = seconds

    def __str__(self):
        fractional_seconds, whole_seconds = math.modf(self.seconds)
        fraction_string = f"{fractional_seconds:g}".lstrip("0") if fractional_seconds else ""
        return f"{self.hours_or_degrees:g}:{self.minutes:0>2.0f}:{whole_seconds:0>2.0f}{fraction_string}"

    def as_tuple(self):
        return self.hours_or_degrees, self.minutes, self.seconds


class HMSCoordinate(SexagesimalCoordinate):
    """A world coordinate in HMS format."""
    FMT = NumberFormat.HMS
    # Temporarily allow negative H values to account for frontend custom format oddity
    REGEX = {
        "COLON": r"^(-?(?:\d|[01]\d|2[0-3]))?:([0-5]?\d)?:([0-5]?\d(?:\.\d+)?)?$",
        "LETTER": r"^(?:(-?(?:\d|[01]\d|2[0-3]))h)?(?:([0-5]?\d)m)?(?:([0-5]?\d(?:\.\d+)?)s)?$",
    }

    @classmethod
    def from_string(cls, value, axis):
        """Construct a world coordinate object in HMS format from a string.

        Coordinates may be provided in HMS format with colons or letters as separators. The value range will be validated for the provided spatial axis.

        Parameters
        ----------
        value : string
            The input string.
        axis : :obj:`carta.constants.SpatialAxis`
            The spatial axis of this coordinate.

        Returns
        -------
        :obj:`carta.util.HMSCoordinate`
            The coordinate object.
        """
        H, M, S = super().from_string(value, axis).as_tuple()

        if axis == SpatialAxis.X and not 0 <= H < 24:
            raise ValueError(f"HMS coordinate string {value} is outside the permitted longitude range [0:00:00, 24:00:00).")

        if axis == SpatialAxis.Y:  # Temporary; we can make this whole option invalid
            if H < -6 or H > 6 or ((H in (-6, 6)) and (M or S)):
                raise ValueError(f"HMS coordinate string {value} is outside the permitted latitude range [-6:00:00, 6:00:00].")

        return cls(H, M, S)


class DMSCoordinate(SexagesimalCoordinate):
    """A world coordinate in DMS format."""
    FMT = NumberFormat.DMS
    REGEX = {
        "COLON": r"^(-?\d+)?:([0-5]?\d)?:([0-5]?\d(?:\.\d+)?)?$",
        "LETTER": r"^(?:(-?\d+)d)?(?:([0-5]?\d)m)?(?:([0-5]?\d(?:\.\d+)?)s)?$",
    }

    @classmethod
    def from_string(cls, value, axis):
        """Construct a world coordinate object in DMS format from a string.

        Coordinates may be provided in DMS format with colons or letters as separators. The value range will be validated for the provided spatial axis.

        Parameters
        ----------
        value : string
            The input string.
        axis : :obj:`carta.constants.SpatialAxis`
            The spatial axis of this coordinate.

        Returns
        -------
        :obj:`carta.util.DMSCoordinate`
            The coordinate object.
        """
        D, M, S = super().from_string(value, axis).as_tuple()

        if axis == SpatialAxis.X and not 0 <= D < 360:
            raise ValueError(f"DMS coordinate string {value} is outside the permitted longitude range [0:00:00, 360:00:00).")

        if axis == SpatialAxis.Y:
            if D < -90 or D > 90 or ((D in (-90, 90)) and (M or S)):
                raise ValueError(f"DMS coordinate string {value} is outside the permitted latitude range [-90:00:00, 90:00:00].")

        return cls(D, M, S)
