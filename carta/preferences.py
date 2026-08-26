"""This module contains functionality for interacting with the CARTA UI preferences. The class in this module should not be instantiated directly. When a session object is created, a preferences object is automatically created as a property."""

from .util import BasePathMixin
from .validation import validate, String, Any


class Preferences(BasePathMixin):
    """This class is a low-level interface to the CARTA UI preferences.

    No validation is performed on any of the preference names or values passed as parameters to the functions in this class.

    Parameters
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this component.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this component.
    """

    def __init__(self, session):
        self.session = session
        self._base_path = "preferenceStore"

    @validate(String())
    def get(self, name):
        """Get the value of a preference.

        Parameters
        ----------
        name : {0}
            The name of the preference.

        Returns
        -------
        any value
            The value of the preference.
        """
        # carta-api:dynamic path=*
        return self.get_value(name)

    @validate(String(), Any())
    def set(self, name, value):
        """Set the value of a preference.

        Parameters
        ----------
        name : {0}
            The name of the preference.
        value : {1}
            The new value for the preference.
        """
        self.call_action("setPreference", name, value)
