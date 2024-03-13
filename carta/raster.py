"""This module contains functionality for interacting with the raster component of an image. The class in this module should not be instantiated directly. When an image object is created, a raster object is automatically created as a property."""

from .util import BasePathMixin
from .constants import Colormap, Scaling, Auto
from .validation import validate, Number, Constant, Boolean, all_optional, Union


class Raster(BasePathMixin):
    """Utility object for collecting image functions related to the raster component.

    Parameters
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this raster component.

    Attributes
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this raster component.
    session : :obj:`carta.session.Session` object
        The session object associated with this raster component.
    """

    def __init__(self, image):
        self.image = image
        self.session = image.session
        self._base_path = f"{image._base_path}.renderConfig"

    @validate(Constant(Colormap), Boolean())
    def set_colormap(self, colormap, invert=False):
        """Set the raster colormap.

        Parameters
        ----------
        colormap : {0}
            The colormap.
        invert : {1}
            Whether the colormap should be inverted. This is false by default.
        """
        self.call_action("setColorMap", colormap)
        self.call_action("setInverted", invert)

    @validate(*all_optional(Constant(Scaling), Number(0.1, 1000000), Number(0.1, 2)))
    def set_scaling(self, scaling=None, alpha=None, gamma=None):
        """Set the raster colormap scaling options.

        Parameters
        ----------
        scaling : {0}
            The scaling type.
        alpha : {1}
            The alpha value (only applicable to ``LOG`` and ``POWER`` scaling types, but set regardless of the scaling parameter provided).
        gamma : {2}
            The gamma value (only applicable to the ``GAMMA`` scaling type, but set regardless of the scaling parameter provided).
        """
        if scaling is not None:
            self.call_action("setScaling", scaling)

        if alpha is not None:
            self.call_action("setAlpha", alpha)

        if gamma is not None:
            self.call_action("setGamma", gamma)

    @validate(*all_optional(Number(0, 100), Number(), Number()))
    def set_clip(self, rank=None, min=None, max=None):
        """Set the raster clip options.

        Parameters
        ----------
        rank : {0}
            The clip percentile rank. If this is set, *min* and *max* are ignored, and will be calculated automatically.
        min : {1}
            Custom clip minimum. Only used if both *min* and *max* are set. Ignored if *rank* is set.
        max : {2}
            Custom clip maximum. Only used if both *min* and *max* are set. Ignored if *rank* is set.
        """

        preset_ranks = [90, 95, 99, 99.5, 99.9, 99.95, 99.99, 100]

        if rank is not None:
            self.call_action("setPercentileRank", rank)
            if rank not in preset_ranks:
                self.call_action("setPercentileRank", -1)  # select 'custom' rank button

        elif min is not None and max is not None:
            self.call_action("setCustomScale", min, max)

    @validate(*all_optional(Union(Number(-1, 1), Constant(Auto)), Union(Number(0, 2), Constant(Auto))))
    def set_bias_and_contrast(self, bias=None, contrast=None):
        """Set the raster bias and contrast.

        Parameters
        ----------
        bias : {0}
            A custom bias. Use :obj:`carta.constants.Auto.AUTO` to reset the bias to the frontend default of ``0``.
        contrast : {1}
            A custom contrast. Use :obj:`carta.constants.Auto.AUTO` to reset the contrast to the frontend default of ``1``.
        """
        if bias is Auto.AUTO:
            self.call_action("resetBias")
        elif bias is not None:
            self.call_action("setBias", bias)

        if contrast is Auto.AUTO:
            self.call_action("resetContrast")
        elif contrast is not None:
            self.call_action("setContrast", contrast)

    @validate(Boolean())
    def set_visible(self, state):
        """Set the raster component visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        self.call_action("setVisible", state)

    def show(self):
        """Show the raster component."""
        self.set_visible(True)

    def hide(self):
        """Hide the raster component."""
        self.set_visible(False)
