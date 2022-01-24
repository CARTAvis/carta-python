"""This module provides miscellaneous utility classes and functions used by the wrapper."""

import logging
import json
import functools

logger = logging.getLogger("carta_scripting")
logger.setLevel(logging.WARN)
logger.addHandler(logging.StreamHandler())


class CartaScriptingException(Exception):
    """The top-level exception for all scripting errors."""
    pass


class CartaBadSession(CartaScriptingException):
    """An exception for invalid session specifications."""
    pass


class CartaValidationFailed(CartaScriptingException):
    """An exception for parameter validation errors."""
    pass


class CartaActionFailed(CartaScriptingException):
    """An exception for action failures."""
    pass


class CartaBadResponse(CartaScriptingException):
    """An exception for unexpected responses."""
    pass

class CartaBadToken(CartaScriptingException):
    """An exception for expired and invalid tokens"""
    pass

class CartaBadUrl(CartaScriptingException):
    """An exception for invalid URLs"""
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


class CartaEncoder(json.JSONEncoder):
    """A custom encoder to JSON which correctly serialises :obj:`carta.util.Macro` objects and numpy arrays."""
    def default(self, obj):
        """ This method is overridden from the parent class and performs the substitution."""
        if isinstance(obj, Macro):
            return {"macroTarget" : obj.target, "macroVariable" : obj.variable}
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
        newfunc.__doc__ = newfunc.__doc__ + "\n\nThis value is transparently cached on the parent object."
        
    return newfunc


def split_action_path(path):
    """Extracts a path to a frontend object store and an action from a combined path.
    """
    parts = path.split('.')
    return '.'.join(parts[:-1]), parts[-1]
