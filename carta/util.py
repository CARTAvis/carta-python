"""This module provides miscellaneous utility classes and functions used by the wrapper."""

import logging
import json
import functools
import re

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


Macro.UNDEFINED = Macro("", "undefined")
Macro.UNDEFINED.__doc__ = """A :obj:`carta.util.Macro` instance which is deserialized as ``undefined`` by the frontend."""


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


class BasePathMixin:
    """A mixin which provides ``call_action`` and ``get_value`` methods which prepend the object's base path to the path before calling the corresponding :obj:`carta.session.Session` methods.

    It also provides a ``macro`` method which prepends the path when creating a :obj:`carta.util.Macro`.

    A class inheriting from this mixin must define a `_base_path` attribute (the string prefix) and a `session` attribute (a :obj:`carta.session.Session` object).
    """

    def call_action(self, path, *args, **kwargs):
        """Convenience wrapper for the session object's generic action method.

        This method calls :obj:`carta.session.Session.call_action` after prepending this object's base path to the path parameter.

        Parameters
        ----------
        path : string
            The path to an action relative to this object's store.
        *args
            A variable-length list of parameters. These are passed unmodified to the session method.
        **kwargs
            Arbitrary keyword parameters. These are passed unmodified to the session method.

        Returns
        -------
        object or None
            The unmodified return value of the session method.
        """
        return self.session.call_action(f"{self._base_path}.{path}", *args, **kwargs)

    def get_value(self, path, return_path=None):
        """Convenience wrapper for the session object's generic method for retrieving attribute values.

        This method calls :obj:`carta.session.Session.get_value` after prepending this object's base path to the *path* parameter.

        Parameters
        ----------
        path : string
            The path to an attribute relative to this object's store.
        return_path : string, optional
            Specifies a subobject of the attribute value which should be returned instead of the whole object.

        Returns
        -------
        object
            The unmodified return value of the session method.
        """
        return self.session.get_value(f"{self._base_path}.{path}", return_path=return_path)

    def macro(self, target, variable):
        """Convenience wrapper for creating a :obj:`carta.util.Macro` for an object property.

        This method prepends this object's base path to the *target* parameter. If *target* is the empty string, the base path will be substituted.

        Parameters
        ----------
        target : str
            The target frontend object.
        variable : str
            The variable on the target object.

        Returns
        -------
        :obj:carta.util.Macro
            A placeholder for a variable which will be evaluated dynamically by the frontend.
        """
        target = f"{self._base_path}.{target}" if target else self._base_path
        return Macro(target, variable)
