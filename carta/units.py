"""This module provides helper objects for unit conversion."""

import re
import math

from .constants import NumberFormat, SpatialAxis


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

    def arcsec(self):
        """The numeric value in arcseconds.

        Returns
        -------
        float
            The numeric value of this angular size, in arcseconds.
        """
        if type(self) is AngularSize:
            raise NotImplementedError()
        return self.value * self.ARCSEC_FACTOR


class DegreesSize(AngularSize):
    """An angular size in degrees."""
    NAME = "degree"
    INPUT_UNITS = {"deg", "degree", "degrees"}
    OUTPUT_UNIT = "deg"
    FACTOR = 1
    ARCSEC_FACTOR = 3600


class ArcminSize(AngularSize):
    """An angular size in arcminutes."""
    NAME = "arcminute"
    INPUT_UNITS = {"'", "arcminutes", "arcminute", "arcmin", "amin", "′"}
    OUTPUT_UNIT = "'"
    FACTOR = 1
    ARCSEC_FACTOR = 60


class ArcsecSize(AngularSize):
    """An angular size in arcseconds."""
    NAME = "arcsecond"
    INPUT_UNITS = {"\"", "", "arcseconds", "arcsecond", "arcsec", "asec", "″"}
    OUTPUT_UNIT = "\""
    FACTOR = 1
    ARCSEC_FACTOR = FACTOR


class MilliarcsecSize(AngularSize):
    """An angular size in milliarcseconds."""
    NAME = "milliarcsecond"
    INPUT_UNITS = {"milliarcseconds", "milliarcsecond", "milliarcsec", "mas"}
    OUTPUT_UNIT = "\""
    FACTOR = 1e-3
    ARCSEC_FACTOR = FACTOR


class MicroarcsecSize(AngularSize):
    """An angular size in microarcseconds."""
    NAME = "microarcsecond"
    INPUT_UNITS = {"microarcseconds", "microarcsecond", "microarcsec", "µas", "uas"}
    OUTPUT_UNIT = "\""
    FACTOR = 1e-6
    ARCSEC_FACTOR = FACTOR


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
