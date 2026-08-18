"""Shared wrapper for heterogeneous views in a CARTA session.

The class in this module should not be instantiated directly. It exists so
that :obj:`carta.image.Image` and :obj:`carta.color_blending.ColorBlending`
can share a common protocol without one having to import the other.
"""


from abc import ABC, abstractmethod

from .constants import ImageType
from .validation import Constant, validate


class View(ABC):
    """Base class for views (images and color blendings).

    This class is not intended to be instantiated directly.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this view.
    """

    CUSTOM_CLASS = {}
    """Mapping of view types to their concrete wrapper classes."""

    def __init_subclass__(cls, **kwargs):
        """Register concrete view wrapper subclasses by view type."""
        super().__init_subclass__(**kwargs)
        View.CUSTOM_CLASS[cls.VIEW_TYPE] = cls

    def __init__(self, session):
        self.session = session

    @property
    @abstractmethod
    def _stable_id(self):
        """The stable identifier of this view."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @validate(Constant(ImageType))
    def view_class(cls, view_type):
        """The wrapper class associated with a view type.

        Parameters
        ----------
        view_type : {0}
            The view type.

        Returns
        -------
        class object
            The concrete view wrapper class.
        """
        view_type = ImageType(view_type)
        view_class = cls.CUSTOM_CLASS.get(view_type)
        if view_class is None:
            raise NotImplementedError(
                f"No View subclass is registered for view type {view_type!r}."
            )
        return view_class

    @property
    def view_index(self):
        """The current index of this view in the session's views."""
        return self.session._find_view_index(self.VIEW_TYPE, self._stable_id)

    def make_active(self):
        """Make this view the active view."""
        self.session.call_action(
            "setActiveImageById", self.VIEW_TYPE, self._stable_id
        )
