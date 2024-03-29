"""This module provides a collection of descriptors of the permitted types and values of parameters passed to :obj:`carta.session.Session` and :obj:`carta.image.Image` methods. They are associated with methods through a decorator which performs the validation at runtime and also injects parameter descriptions into the methods' docstrings."""

import re
import functools
import inspect

from .util import CartaValidationFailed
from .units import AngularSize, WorldCoordinate


class Parameter:
    """The top-level class for parameter validation."""

    def validate(self, value, parent):
        """Validate the value provided.

        Parameters
        ----------
        value
            The value to be validated.
        parent
            The object which owns the decorated method.

        Raises
        ------
        TypeError
            If the value provided is not of the correct type.
        ValueError
            If the value provided is of the correct type but has an invalid value.
        AttributeError
            If the check depends on an attribute on the parent object of the decorated method, and it does not exist.
        """
        raise NotImplementedError

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        return "UNKNOWN"


class InstanceOf(Parameter):
    """A parameter which is an instance of the provided type or tuple of types.

    This validator uses ``isinstance``, and has the same behaviour. An instance of a child class is also an instance of a parent class.

    Parameters
    ----------
    types : type or tuple of types
    """

    def __init__(self, types):
        if not isinstance(types, tuple):
            types = (types,)
        self.types = types

    def validate(self, value, parent):
        """Check if the value is an instance of the provided type or types.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        if not isinstance(value, self.types):
            raise TypeError(f"{value} has type {type(value)} but {self.description} was expected.")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        names = []
        for t in self.types:
            if t.__module__.startswith("carta."):
                names.append(f":obj:`{t.__module__}.{t.__name__}`")
            else:
                names.append(t.__name__)

        if len(names) == 1:
            return f"an instance of {names[0]}"

        names = names[:-2] + [" or ".join(names[-2:])]
        return f"an instance of {', '.join(names)}"


class String(Parameter):
    """A string parameter.

    Parameters
    ----------
    regex : str, optional
        A regular expression string which the parameter must match.
    flags : int, optional
        The flags to use when matching the regular expression. Set to zero (no flags) by default.

    Attributes
    ----------
    regex : str
        A regular expression string which the parameter must match.
    flags : int
        The flags to use when matching the regular expression.
    """

    def __init__(self, regex=None, flags=0):
        self.regex = regex
        self.flags = flags

    def validate(self, value, parent):
        """Check if the value is a string and if it matches a regex if one was provided.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        if not isinstance(value, str):
            raise TypeError(f"{value} has type {type(value)} but a string was expected.")

        if self.regex is not None and not re.search(self.regex, value, self.flags):
            raise ValueError(f"{value} does not match {self.regex}")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        if self.regex:
            return f"a string matching ``{self.regex}``"
        return "a string"


class Number(Parameter):
    """An integer or floating point scalar numeric parameter.

    Parameters
    ----------
    min : number, optional
        The lower bound.
    max : number, optional
        The upper bound.
    interval : int
        A bitmask which describes whether the bounds are included or excluded. The constant attributes defined on this class should be used. By default both bounds are included.
    step : number, optional
        A step size to which the value must conform. May be a fractional value. If this is unset, any value within the range is permitted.
    offset : number, optional
        A step offset. Ignored if a step size is not set. By default permitted values are aligned with the lower bound if it is set, otherwise with zero.

    Attributes
    ----------
    min : number
        The lower bound.
    max : number
        The upper bound.
    min_included : bool
        Whether the lower bound is included.
    max_included : bool
        Whether the upper bound is included.
    step : number, optional
        The step size.
    offset : number, optional
        The step offset.
    """

    EXCLUDE, INCLUDE_MIN, INCLUDE_MAX, INCLUDE = range(4)

    def __init__(self, min=None, max=None, interval=INCLUDE, step=None, offset=None):
        self.min = min
        self.max = max
        self.min_included = bool(interval & self.INCLUDE_MIN)
        self.max_included = bool(interval & self.INCLUDE_MAX)
        if step is not None:
            self.step = step
            if offset is not None:
                self.offset = offset
            elif min is not None:
                self.offset = min % step
            else:
                self.offset = 0
        else:
            self.step = None
            self.offset = None

    def validate(self, value, parent):
        """Check if the value is a number and falls within any bounds that were provided.

        We check the type by attempting to convert the value to ``float``. We do this instead of comparing types directly to support compatible numeric types from e.g. the numpy library without having to anticipate and check for them explicitly and without introducing import dependencies.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        if not isinstance(value, (int, float)):
            raise TypeError(f"{value} has type {type(value)} but a number was expected.")

        if self.min is not None:
            if self.min_included:
                if value < self.min:
                    raise ValueError(f"{value} is smaller than lower bound {self.min}, but must be greater or equal.")
            else:
                if value == self.min:
                    raise ValueError(f"{value} is equal to lower bound {self.min}, but must be greater.")
                if value < self.min:
                    raise ValueError(f"{value} is smaller than lower bound {self.min}, but must be greater.")

        if self.max is not None:
            if self.max_included:
                if value > self.max:
                    raise ValueError(f"{value} is greater than upper bound {self.max}, but must be smaller or equal.")
            else:
                if value == self.max:
                    raise ValueError(f"{value} is equal to upper bound {self.max}, but must be smaller.")
                if value > self.max:
                    raise ValueError(f"{value} is greater than upper bound {self.max}, but must be smaller.")

        if self.step is not None:
            if (value - self.offset) % self.step:
                offset = f" offset by {self.offset}" if self.offset else ""
                raise ValueError(f"{value} is not an increment of {self.step}{offset}.")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        desc = ["a number"]

        if self.min is not None:
            desc.append(f"greater than{' or equal to' if self.min_included else ''} ``{self.min}``")

            if self.max is not None:
                desc.append("and")

        if self.max is not None:
            desc.append(f"smaller than{' or equal to' if self.max_included else ''} ``{self.max}``")

        if self.step is not None:
            offset = f" offset by {self.offset}" if self.offset else ""
            desc.append(f", in increments of {self.step}{offset}")

        return " ".join(desc)


class Boolean(Parameter):
    """A boolean parameter."""

    def validate(self, value, parent):
        """Check if the value is boolean. It may be expressed as a numeric 1 or 0 value.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        if value not in (0, 1):
            raise TypeError(f"{value} is not a boolean value.")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        return "a boolean"


class NoneParameter(Parameter):
    """A parameter which must be ``None``. This is not intended to be used directly; it is used together with :obj:`carta.validation.Union` for optional parameters with a default value of ``None``."""

    def validate(self, value, parent):
        """Check if the value is ``None``.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        if value is not None:
            raise ValueError(f"{value} is not None.")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        return "``None``"


class OneOf(Parameter):
    """A parameter which must be one of several discrete values.

    Parameters
    ----------
    *options : iterable
        An iterable of permitted values.
    normalize : function, optional
        A function for applying a transformation to the value before the comparison: for example, ``lambda x: x.lower()``.

    Attributes
    ----------
    options : iterable
        An iterable of permitted values.
    normalize : function, optional
        A function for applying a transformation to the value before the comparison.
    """

    def __init__(self, *options, normalize=None):
        self.options = options
        self.normalize = normalize

    def validate(self, value, parent):
        """Check if the value is equal to one of the provided options. If a normalization function is given, this is first used to transform the value.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        if self.normalize is not None:
            value = self.normalize(value)

        if value not in self.options:
            raise ValueError(f"{value} is not {self.description}")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        return f"one of {', '.join(str(o) for o in self.options)}"


class Union(Parameter):
    """A union of other parameter descriptors.

    Parameters
    ----------
    *options : iterable of :obj:`carta.validation.Parameter` objects
        An iterable of valid descriptors for this parameter.
    description : str, optional
        A custom description. The default is generated from the descriptions of the provided options.

    Attributes
    ----------
    options : iterable of :obj:`carta.validation.Parameter` objects
        An iterable of valid descriptors for this parameter.
    """

    def __init__(self, *options, description=None):
        self.options = options
        self._description = description

    def validate(self, value, parent):
        """Check if the value can be validated with one of the provided descriptors. The descriptors are evaluated in the order that they are given, and the function exits after the first successful validation.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        valid = False

        for option in self.options:
            try:
                option.validate(value, parent)
            except (ValueError, TypeError):
                pass
            else:
                valid = True
                break

        if not valid:
            raise ValueError(f"{value} is not {self.description}.")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        return self._description or " or ".join(o.description for o in self.options)


class Constant(OneOf):
    """A parameter which must be a member of the given enum class. For consistency and compatibility, a parameter will be accepted if it evaluates as equal to a member of the enum. Intended for use with the string and integer constants defined in :obj:`carta.constants`.

    Parameters
    ----------
    clazz : enum class
        The parameter must be a member of this enum class or have the same value as a member of this enum class.
    exclude : iterable, optional
        An iterable of members to exclude.

    Attributes
    ----------
    options : iterable
        An iterable of the permitted options.
    clazz : enum class
        The parameter must be a member of this enum class or have the same value as a member of this enum class.
    exclude : iterable
        An iterable of members which are excluded.
    """

    def __init__(self, clazz, exclude=()):
        options = set(e for e in clazz)
        options -= set(exclude)
        super().__init__(*options)
        self.clazz = clazz
        self.exclude = exclude

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        if self.clazz.__module__ is None or self.clazz.__module__ == str.__class__.__module__:
            fullname = self.clazz.__name__  # Avoid reporting __builtin__
        else:
            fullname = self.clazz.__module__ + '.' + self.clazz.__name__
        if self.exclude:
            exclude_list = ",".join(f"``{repr(e)}``" for e in self.exclude)
            excluding = f" excluding {exclude_list}"
        else:
            excluding = ""
        return f"a member of :obj:`{fullname}`{excluding}"


class NoneOr(Union):
    """A union of other parameter descriptors as well as ``None``.

    In the most common use case, this is used with a single other parameter type for optional parameters which are ``None`` by default. In more complex cases this can be used as shorthand in place of a :obj:`carta.validation.Union` with an explicit :obj:`carta.validation.NoneParameter` option. Also see :obj:`carta.validation.all_optional` for a less verbose way to specify multiple sequential optional parameters.

    Parameters
    ----------
    *options : iterable of :obj:`carta.validation.Parameter` objects
        An iterable of valid descriptors for this parameter, in addition to ``None``.
    description : str, optional
        A custom description. The default is generated from the descriptions of the provided options.

    Attributes
    ----------
    options : iterable of :obj:`carta.validation.Parameter` objects
        An iterable of valid descriptors for this parameter, in addition to ``None``.
    """

    def __init__(self, *options, description=None):
        options = (
            *options,
            NoneParameter(),
        )
        super().__init__(*options, description=description)


class IterableOf(Parameter):
    """An iterable of values which must match the given descriptor.

    Parameters
    ----------
    param : :obj:`carta.validation.Parameter`
        The parameter descriptor.
    min_size : integer, optional
        The minimum size.
    max_size : integer, optional
        The maximum size.

    Attributes
    ----------
    param : :obj:`carta.validation.Parameter`
        The parameter descriptor.
    min_size : integer, optional
        The minimum size.
    max_size : integer, optional
        The maximum size.
    """

    def __init__(self, param, min_size=None, max_size=None):
        self.param = param
        self.min_size = min_size
        self.max_size = max_size

    def validate(self, value, parent):
        """Check if each element of the iterable can be validated with the given descriptor.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """

        try:
            for v in value:
                self.param.validate(v, parent)
        except TypeError as e:
            if str(e).endswith("object is not iterable"):
                raise ValueError(f"{value} is not iterable, but {self.description} was expected.")
            raise e

        if self.min_size is not None:
            if len(value) < self.min_size:
                raise ValueError(f"{value} has {len(value)} elements, but must have at least {self.min_size}.")

        if self.max_size is not None:
            if len(value) > self.max_size:
                raise ValueError(f"{value} has {len(value)} elements, but may have at most {self.max_size}.")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        size = []
        size_desc = ""

        if self.min_size is not None:
            size.append(f"at least {self.min_size} elements")
        if self.max_size is not None:
            size.append(f"at most {self.max_size} elements")

        if size:
            size_desc = f"with {' and '.join(size)} "
        return f"an iterable {size_desc}in which each element is {self.param.description}"


class MapOf(IterableOf):
    """A dictionary of keys and values which must match the given descriptors.

    Parameters
    ----------
    value_param : :obj:`carta.validation.Parameter`
        The value parameter descriptor.

    Attributes
    ----------
    value_param : :obj:`carta.validation.Parameter`
        The value parameter descriptor.
    """

    def __init__(self, key_param, value_param, min_size=None, max_size=None):
        self.value_param = value_param
        super().__init__(key_param, min_size, max_size)

    def validate(self, value, parent):
        """Check if each element of the iterable can be validated with the given descriptor.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """

        try:
            for v in value.values():
                self.value_param.validate(v, parent)
        except AttributeError as e:
            if str(e).endswith("has no attribute 'values'"):
                raise ValueError(f"{value} is not a dictionary, but {self.description} was expected.")
            raise e

        super().validate(value, parent)

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """

        return re.sub("^an iterable (.*?)in which each element is (.*)$", rf"a dictionary \1in which each key is {self.param.description} and each value is {self.value_param.description}", super().description)


COLORNAMES = ('aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure', 'beige', 'bisque', 'black', 'blanchedalmond', 'blue', 'blueviolet', 'brown', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgrey', 'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange', 'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue', 'darkslategray', 'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink', 'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'gray', 'grey', 'green', 'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo', 'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue', 'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgray', 'lightgrey', 'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey', 'lightsteelblue', 'lightyellow', 'lime', 'limegreen', 'linen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 'mediumpurple', 'mediumseagreen', 'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy', 'oldlace', 'olive', 'olivedrab', 'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink', 'plum', 'powderblue', 'purple', 'red', 'rosybrown', 'royalblue', 'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver', 'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen', 'steelblue', 'tan', 'teal', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'white', 'whitesmoke', 'yellow', 'yellowgreen')


class TupleColor(Parameter):
    """An HTML color tuple. Not intended to be used directly; you probably want :obj:`carta.validation.Color` instead."""

    def _assert_length(self, params, number):
        if len(params) != number:
            raise ValueError(f"expected {number} parameters but got {len(params)}.")

    def _assert_percentage(self, param):
        if not param.endswith("%") or not 0 <= float(param[:-1]) <= 100:
            raise ValueError(f"{param} is not a valid percentage.")

    def _assert_between(self, param, min, max):
        if not min <= float(param) <= max:
            raise ValueError(f"{param} is not a number between {min} and {max}.")

    def _validate_rgb(self, params):
        self._assert_length(params, 3)

        try:
            for p in params:
                self._assert_percentage(p)
        except ValueError:
            try:
                for p in params:
                    self._assert_between(p, 0, 255)
            except ValueError:
                raise ValueError("parameters must either all be percentages or all be numbers between 0 and 255.")

    def _validate_rgba(self, params):
        self._assert_length(params, 4)
        self._validate_rgb(params[:3])
        self._assert_between(params[3], 0, 1)

    def _validate_hsl(self, params):
        self._assert_length(params, 3)
        self._assert_between(params[0], 0, 360)
        self._assert_percentage(params[1])
        self._assert_percentage(params[2])

    def _validate_hsla(self, params):
        self._assert_length(params, 4)
        self._validate_hsl(params[:3])
        self._assert_between(params[3], 0, 1)

    def validate(self, value, parent):
        """Check if the value can be parsed as a color tuple, and validate the tuple elements.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        value = re.sub(r'\s', '', value)

        m = re.match(r'(hsla?|rgba?)\((.*)\)', value)
        if m is None:
            raise ValueError(f"{value} is not {self.description}.")

        func, params = m.groups()
        try:
            getattr(self, f"_validate_{func}")(params.split(","))
        except (TypeError, ValueError) as e:
            raise ValueError(f"{value} is not a valid {func.upper()} color tuple: {e}")

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        return "an HTML color tuple"


class Color(Union):
    """Any valid HTML color specification: a 3- or 6-digit hex triplet, an RBG(A) or HSL(A) tuple, or one of the 147 named colors."""

    def __init__(self):
        options = (
            OneOf(*COLORNAMES, lambda v: v.lower()),  # Named color
            String("#[0-9a-f]{6}", re.IGNORECASE),  # 6-digit hex
            String("#[0-9a-f]{3}", re.IGNORECASE),  # 3-digit hex
            TupleColor(),  # RGB, RGBA, HSL, HSLA
        )
        super().__init__(*options, description="an HTML color specification")


class Size(Union):
    """A representation of an angular size or a size in pixels. Can be a number or a numeric string with valid size units. A number is assumed to be a pixel value. Validates strings using :obj:`carta.util.AngularSize`."""

    class AngularSize(String):
        """Helper validator class which uses :obj:`carta.util.AngularSize` to validate strings."""

        def validate(self, value, parent):
            """Check if the value can be parsed as an angular size.

            See :obj:`carta.validation.Parameter.validate` for general information about this method.
            """
            super().validate(value, parent)
            if not AngularSize.valid(value):
                raise ValueError(f"{value} is not an angular size.")

    def __init__(self):
        options = (
            Number(),
            self.AngularSize(),
        )
        super().__init__(*options, description="a number or a numeric string with valid size units")


class Coordinate(Union):
    """A representation of a world coordinate or image coordinate. Can be a number, a string in H:M:S or D:M:S format, or a numeric string with degree units. A number is assumed to be a pixel value. Validates strings using :obj:`carta.util.WorldCoordinate`."""

    class WorldCoordinate(String):
        """Helper validator class which uses :obj:`carta.util.WorldCoordinate` to validate strings."""

        def validate(self, value, parent):
            """Check if the value can be parsed as a world coordinate.

            See :obj:`carta.validation.Parameter.validate` for general information about this method.
            """
            super().validate(value, parent)
            if not WorldCoordinate.valid(value):
                raise ValueError(f"{value} is not a world coordinate.")

    def __init__(self):
        options = (
            Number(),
            self.WorldCoordinate(),
        )
        super().__init__(*options, description="a number, a string in H:M:S or D:M:S format, or a numeric string with degree units")


class Attr(str):
    """A wrapper for arguments to be passed to the :obj:`carta.validation.Evaluate` descriptor. These arguments are string names of properties on the parent object of the decorated method, which will be evaluated at runtime."""
    pass


class Attrs(str):
    """A wrapper for arguments to be passed to the :obj:`carta.validation.Evaluate` descriptor. These arguments are string names of properties on the parent object of the decorated method, which will be evaluated at runtime. Unlike `carta.validation.Attr`, the wrapped property is assumed to be an iterable which should be unpacked."""
    pass


class Evaluate(Parameter):
    """A descriptor which is constructed at runtime using properties of the parent object of the decorated method.

    Parameters
    ----------
    paramclass : a :obj:`carta.validation.Parameter` class
        The class of the parameter descriptor to construct.
    *args : iterable
        Positional arguments to pass to the constructor; either literals or :obj:`carta.validation.Attr` objects which will be evaluated from properties on the parent object at runtime.
    **kwargs : iterable
        Keyword arguments to pass to the constructor; either literals or :obj:`carta.validation.Attr` objects which will be evaluated from properties on the parent object at runtime.

    Attributes
    ----------
    paramclass : a :obj:`carta.validation.Parameter` class
        The class of the parameter descriptor to construct.
    args : iterable
        Positional arguments to pass to the constructor.
    kwargs : iterable
        Keyword arguments to pass to the constructor.
    """

    def __init__(self, paramclass, *args, **kwargs):
        self.paramclass = paramclass
        self.args = args
        self.kwargs = kwargs

    def validate(self, value, parent):
        """Validate the value after constructing the parameter descriptor object.

        See :obj:`carta.validation.Parameter.validate` for general information about this method.
        """
        args = []
        for arg in self.args:
            if isinstance(arg, Attr):
                args.append(getattr(parent, arg))
            elif isinstance(arg, Attrs):
                args.extend(getattr(parent, arg))
            else:
                args.append(arg)

        kwargs = {}
        for key, arg in self.kwargs.items():
            if isinstance(arg, Attr):
                kwargs[key] = getattr(parent, arg)
            else:
                kwargs[key] = arg

        param = self.paramclass(*args, **kwargs)
        param.validate(value, parent)

    @property
    def description(self):
        """A human-readable description of this parameter descriptor.

        Returns
        -------
        string
            The description.
        """
        args = list(self.args)
        for i, arg in enumerate(args):
            if isinstance(arg, Attr):
                args[i] = f"self.{arg}"
            elif isinstance(arg, Attrs):
                args[i] = f"*self.{arg}"

        kwargs = dict(self.kwargs)
        for key, arg in self.kwargs.items():
            if isinstance(arg, Attr):
                kwargs[key] = f"self.{arg}"

        # This is a bit magic, and relies on the lack of any kind of type checking in the constructors
        param = self.paramclass(*args, **kwargs)
        return f"{param.description}, evaluated at runtime"


def validate(*vargs):
    """The function which returns the decorator used to validate method parameters.

    It is assumed that the function to be decorated is an object method and the first parameter is ``self``; this parameter is therefore ignored by the decorator. The remaining positional parameters are validated in order using the provided descriptors. The descriptors are also combined pairwise with the parameter names in the signature of the original function to create a dictionary for validating keyword parameters.

    Functions with ``*args`` or ``**kwargs`` are not currently supported: use iterables and explicit keyword parameters instead.

    The decorator inserts the descriptions of the parameters into the docstring of the decorated function, if placeholders have been left for them in the original docstring. The descriptions are passed as positional parameters to :obj:`str.format`.

    The ``self`` parameter is passed into the validation method of each descriptor, so that checks can depend on properties to be evaluated at runtime (this is currently used by :obj:`carta.validation.Evaluate`).

    The decorated function raises a :obj:`carta.util.CartaValidationFailed` if one of the parameters fails to validate.

    Parameters
    ----------
    *vargs : iterable of :obj:`carta.validation.Parameter` objects
        Descriptors to be used to validate the function parameters, in the same order as the parameters.

    Returns
    -------
    function
        The decorator function.
    """

    def decorator(func):
        kwvargs = {k: v for (k, v) in zip(inspect.getfullargspec(func).args[1:], vargs)}
        STRIP_OBJ = re.compile(":obj:`(.*)`")
        STRIP_CODE = re.compile("``(.*)``")
        PRESERVE = re.compile("(:obj:`.+?`|``.+?``)")
        ITALICISE = re.compile(r"^([\s.,]*)(.+?)([\s.,]*)$")

        @functools.wraps(func)
        def newfunc(self, *args, **kwargs):
            try:
                for param, value in zip(vargs, args):
                    param.validate(value, self)
                for key, value in kwargs.items():
                    try:
                        param = kwvargs[key]
                        param.validate(value, self)
                    except KeyError:
                        raise CartaValidationFailed(f"Unexpected keyword parameter passed to {func.__name__}: {key}")
            except (TypeError, ValueError, AttributeError) as e:
                # Strip out any documentation formatting from the descriptions
                msg = str(e)
                msg = STRIP_OBJ.sub(r"\1", msg)
                msg = STRIP_CODE.sub(r"\1", msg)
                raise CartaValidationFailed(f"Invalid function parameter passed to {func.__name__}: {msg}")
            return func(self, *args, **kwargs)

        # If descriptions contain formatting they are not formatted correctly by Sphinx
        def fix_description(s):
            parts = PRESERVE.split(s)
            if len(parts) == 1:
                return s
            for i, p in enumerate(parts):
                if PRESERVE.match(p):
                    continue
                parts[i] = ITALICISE.sub(r"\1*\2*\3", p)
            return "".join(parts)

        if newfunc.__doc__ is not None:
            newfunc.__doc__ = newfunc.__doc__.format(*(fix_description(p.description) for p in vargs))

        # Add a handle to the validation parameters to allow functions which call other functions to reuse parameters
        newfunc.VARGS = vargs

        return newfunc
    return decorator


def all_optional(*vargs):
    """Wrapper to make all parameters in an iterable optional.

    For improved legibility in functions with many sequential optional parameters. Can also enable reuse of validation parameters in functions which call other functions.

    Parameters
    ----------
    *vargs : iterable of :obj:`carta.validation.Parameter` objects

    Returns
    -------
    iterable of :obj:`carta.validation.Parameter` objects
        The same parameters in the same order, but with all non-optional parameters made optional (that is, wrapped in a obj:`carta.validation.NoneOr` parameter).
    """
    return tuple(NoneOr(param) if not isinstance(param, NoneOr) else param for param in vargs)
