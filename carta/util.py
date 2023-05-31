"""This module provides miscellaneous utility classes and functions used by the wrapper."""

import logging
import json
import functools
import re

from .constants import NumberFormat

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


class PixelString:
    """Parses pixel values."""

    UNITS = {"px", "pix", "pixel", "pixels"}
    UNIT_REGEX = rf"^(\d+(?:\.\d+)?)\s*(?:{'|'.join(UNITS)})$"

    @classmethod
    def valid(cls, value):
        """Whether the input string is a numeric value followed by a pixel unit.

        Permitted pixel unit strings are stored in :obj:`carta.util.PixelString.UNITS`. Whitespace is permitted after the number and before the unit.

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
    def normalized(cls, value):
        """Parse a string containing a numeric value followed by a pixel unit, and return the numeric part (as a string).

        Permitted pixel unit strings are stored in :obj:`carta.util.PixelString.UNITS`. Whitespace is permitted after the number and before the unit.

        Parameters
        ----------
        value : string
            The string representation of the pixel value.

        Returns
        -------
        string
            The numeric portion of the pixel value.

        Raises
        ------
        ValueError
            If the input string is not in a recognized format.
        """
        m = re.match(cls.UNIT_REGEX, value, re.IGNORECASE)
        if m is None:
            raise ValueError(f"{repr(value)} is not in a recognized pixel format.")
        return m.group(1)


class AngularSizeString:
    """Parses angular sizes."""

    NORMALIZED_UNIT = {
        "arcminutes": "'",
        "arcminute": "'",
        "arcmin": "'",
        "amin": "'",
        "arcseconds": "\"",
        "arcsecond": "\"",
        "arcsec": "\"",
        "asec": "\"",
        "deg": "deg",
        "degree": "deg",
        "degrees": "deg",
        "": "\"",  # No units = arcsec
        "\"": "\"",
        "'": "'",
    }

    SYMBOL_UNITS = {"", "'", "\""}
    WORD_UNITS = NORMALIZED_UNIT.keys() - SYMBOL_UNITS

    SYMBOL_UNIT_REGEX = rf"^(\d+(?:\.\d+)?)({'|'.join(SYMBOL_UNITS)})$"
    WORD_UNIT_REGEX = rf"^(\d+(?:\.\d+)?)\s*({'|'.join(WORD_UNITS)})$"

    @classmethod
    def valid(cls, value):
        """Whether the input string is a numeric value followed by an angular size unit.

        A number without a unit is assumed to be in arcseconds. Permitted unit strings and their mappings to normalized units are stored in :obj:`carta.util.AngularSizeString.NORMALIZED_UNIT`. Whitespace is permitted after the number and before a unit which is a word, but not before ``'`` or ``"``.

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
    def normalized(cls, value):
        """Parse a string containing a numeric size and a unit, and return the size and the normalized unit.

        A number without a unit is assumed to be in arcseconds. Permitted unit strings and their mappings to normalized units are stored in :obj:`carta.util.AngularSizeString.NORMALIZED_UNIT`. Whitespace is permitted after the number and before a unit which is a word, but not before ``'`` or ``"``.

        Parameters
        ----------
        value : string
            The string representation of the angular size.

        Returns
        -------
        string
            The numeric portion of the angular size string.
        string
            The normalized unit.

        Raises
        ------
        ValueError
            If the angular size string is not in a recognized format.
        """
        m = re.match(cls.WORD_UNIT_REGEX, value, re.IGNORECASE)
        if m is None:
            m = re.match(cls.SYMBOL_UNIT_REGEX, value, re.IGNORECASE)
            if m is None:
                raise ValueError(f"{repr(value)} is not in a recognized angular size format.")
        value, unit = m.groups()
        unit = cls.NORMALIZED_UNIT[unit]
        return value, unit


class WorldCoordinateString:
    """Parses world coordinates."""

    DEGREE_UNITS = {k for k, v in AngularSizeString.NORMALIZED_UNIT.items() if v == "deg"}

    REGEX = {
        "DEGREE_UNIT": rf"^-?(\d+(?:\.\d+)?)\s*({'|'.join(DEGREE_UNITS)})$",
        "HMS_COLON": r"^-?\d{0,2}:\d{0,2}:(\d{1,2}(\.\d+)?)?$",
        "HMS_LETTER": r"^(?:(-?\d{1,2})h)?(?:(\d{1,2})m)?(?:(\d{1,2}(?:\.\d+)?)s)?$",
        "DMS_COLON": r"^-?\d*:\d{0,2}:(\d{1,2}(\.\d+)?)?$",
        "DMS_LETTER": r"^(?:(-?\d+)d)?(?:(\d{1,2})m)?(?:(\d{1,2}(?:\.\d+)?)s)?$",
        "DECIMAL": r"^-?\d+(\.\d+)?$",  # No units = degrees
    }

    @classmethod
    def valid(cls, value):
        """Whether the input string is a world coordinate string in any of the recognised formats.

        Coordinates may be provided in HMS or DMS format (with colons or letters as separators), or in degrees (with or without an explicit unit). Permitted degree unit strings are stored in :obj:`carta.util.WorldCoordinateString.DEGREE_UNITS`.

        Parameters
        ----------
        value : string
            The input string.

        Returns
        -------
        boolean
            Whether the input string is an world coordinate.
        """
        return any(re.match(exp, value, re.IGNORECASE) for exp in cls.REGEX.values())

    @classmethod
    def normalized(cls, value, fmt):
        """Parse a world coordinate string using the specified format.

        Coordinates may be provided in HMS or DMS format (with colons or letters as separators), or in degrees (with or without an explicit unit). Permitted degree unit strings are stored in :obj:`carta.util.WorldCoordinateString.DEGREE_UNITS`.

        Parameters
        ----------
        value : string
            The string representation of the coordinate.
        fmt : :obj:`carta.constants.NumberFormat`
            The expected number format of the coordinate string.

        Returns
        -------
        string
            The normalized coordinate string.

        Raises
        ------
        ValueError
            If the coordinate string could not be parsed using the specified number format.
        """
        if fmt == NumberFormat.DEGREES:
            m = re.match(cls.REGEX["DECIMAL"], value, re.IGNORECASE)
            if m is not None:
                return value
            m = re.match(cls.REGEX["DEGREE_UNIT"], value, re.IGNORECASE)
            if m is not None:
                return m.group(1)
            raise ValueError(f"Coordinate string {value} does not match expected format {fmt}.")

        def empty_if_none(*strs):
            return tuple("" if s is None else s for s in strs)

        if fmt == NumberFormat.HMS:
            m = re.match(cls.REGEX["HMS_COLON"], value, re.IGNORECASE)
            if m is not None:
                return value
            m = re.match(cls.REGEX["HMS_LETTER"], value, re.IGNORECASE)
            if m is not None:
                H, M, S = empty_if_none(*m.groups())
                return f"{H}:{M}:{S}"
            raise ValueError(f"Coordinate string {value} does not match expected format {fmt}.")

        if fmt == NumberFormat.DMS:
            m = re.match(cls.REGEX["DMS_COLON"], value, re.IGNORECASE)
            if m is not None:
                return value
            m = re.match(cls.REGEX["DMS_LETTER"], value, re.IGNORECASE)
            if m is not None:
                D, M, S = empty_if_none(*m.groups())
                return f"{D}:{M}:{S}"
            raise ValueError(f"Coordinate string {value} does not match expected format {fmt}.")
