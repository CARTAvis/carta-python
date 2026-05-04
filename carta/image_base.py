"""This module contains the shared base class for image-view items (frame-backed images and color blendings).

The class in this module should not be instantiated directly. It exists so that :obj:`carta.image.Image` and :obj:`carta.color_blending.ColorBlending` can share a common protocol without one having to import the other.
"""


from abc import ABC, abstractmethod

from .constants import ImageType


class ImageBase(ABC):
    """Base class for image-view items (frame-backed images and color blendings).

    This class is not intended to be instantiated directly.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image-view item.
    """

    _image_type: ImageType = None

    def __init__(self, session):
        self.session = session

    @property
    @abstractmethod
    def _stable_id(self):
        """The stable identifier of this image-view item."""
        raise NotImplementedError  # pragma: no cover

    def _require_image_type(self):
        if self._image_type is None:
            raise NotImplementedError(
                "Subclasses must define _image_type."
            )

    @property
    def image_view_order(self):
        """The current index of this item in image list.

        Returns
        -------
        integer
            The image view order.

        Raises
        ------
        RuntimeError
            If no matching entry exists in the image list.
        """
        self._require_image_type()
        return self.session._find_image_view_order(
            self._image_type, self._stable_id
        )

    def make_active(self):
        """Make this the active image-view item."""
        self._require_image_type()
        self.session.call_action(
            "setActiveImageById", self._image_type, self._stable_id
        )
