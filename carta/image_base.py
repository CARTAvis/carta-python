"""This module contains the shared base class for image-view items (frame-backed images and color blendings).

The class in this module should not be instantiated directly. It exists so that :obj:`carta.image.Image` and :obj:`carta.color_blending.ColorBlending` can share a common protocol without one having to import the other.
"""


from abc import ABC, abstractmethod

from .constants import ImageType
from .validation import Constant, validate


class ImageBase(ABC):
    """Base class for image-view items (frame-backed images and color blendings).

    This class is not intended to be instantiated directly.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image-view item.
    """

    CUSTOM_CLASS = {}
    """Mapping of image-view types to their concrete wrapper classes."""

    def __init_subclass__(cls, **kwargs):
        """Register concrete image-view wrapper subclasses by image type."""
        super().__init_subclass__(**kwargs)
        ImageBase.CUSTOM_CLASS[cls.IMAGE_TYPE] = cls

    def __init__(self, session):
        self.session = session

    @property
    @abstractmethod
    def _stable_id(self):
        """The stable identifier of this image-view item."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @validate(Constant(ImageType))
    def image_class(cls, image_type):
        """The image class associated with an image-view type.

        Parameters
        ----------
        image_type : {0}
            The image-view type.

        Returns
        -------
        class object
            The concrete image-view wrapper class.
        """
        image_type = ImageType(image_type)
        image_class = cls.CUSTOM_CLASS.get(image_type)
        if image_class is None:
            raise NotImplementedError(
                f"No ImageBase subclass is registered for image-view type "
                f"{image_type!r}."
            )
        return image_class

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
        return self.session._find_image_view_order(
            self.IMAGE_TYPE, self._stable_id
        )

    def make_active(self):
        """Make this the active image-view item."""
        self.session.call_action(
            "setActiveImageById", self.IMAGE_TYPE, self._stable_id
        )
