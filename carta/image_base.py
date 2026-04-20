"""This module contains the shared base class for image-view items (frame-backed images and color blendings).

The class in this module should not be instantiated directly. It exists so that :obj:`carta.image.Image` and :obj:`carta.colorblending.ColorBlending` can share a common protocol without one having to import the other.
"""


from .constants import ImageType


class ImageBase:
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
    def _stable_id(self):
        """The stable identifier of this image-view item."""
        raise NotImplementedError

    @property
    def image_view_order(self):
        """The index of this item in image list."""
        raise NotImplementedError

    def make_active(self):
        """Make this the active image-view item."""
        self.session.call_action(
            "setActiveImageById", self._image_type, self._stable_id
        )
