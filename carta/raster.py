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
        """Set the colormap.

        By default the colormap is not inverted.

        Parameters
        ----------
        colormap : {0}
            The colormap.
        invert : {1}
            Whether the colormap should be inverted.
        """
        self.call_action("setColorMap", colormap)
        self.call_action("setInverted", invert)

    @validate(*all_optional(Constant(Scaling), Number(0.1, 1000000), Number(0.1, 2), Number(0, 100), Number(), Number(), Union(Number(-1, 1), Constant(Auto)), Union(Number(0, 2), Constant(Auto))))
    def set_scaling(self, scaling=None, alpha=None, gamma=None, rank=None, min=None, max=None, bias=None, contrast=None):
        """Set the colormap scaling.

        Parameters
        ----------
        scaling : {0}
            The scaling type.
        alpha : {1}
            The alpha value (only applicable to ``LOG`` and ``POWER`` scaling types, but set regardless of the scaling parameter provided).
        gamma : {2}
            The gamma value (only applicable to the ``GAMMA`` scaling type, but set regardless of the scaling parameter provided).
        rank : {3}
            The clip percentile rank. If this is set, *min* and *max* are ignored, and will be calculated automatically.
        min : {4}
            Custom clip minimum. Only used if both *min* and *max* are set. Ignored if *rank* is set.
        max : {5}
            Custom clip maximum. Only used if both *min* and *max* are set. Ignored if *rank* is set.
        bias : {6}
            A custom bias. Use :obj:`carta.constants.Auto.AUTO` to reset the bias to the frontend default of ``0``.
        contrast : {7}
            A custom contrast. Use :obj:`carta.constants.Auto.AUTO` to reset the contrast to the frontend default of ``1``.
        """
        if scaling is not None:
            self.call_action("setScaling", scaling)

        if alpha is not None:
            self.call_action("setAlpha", alpha)

        if gamma is not None:
            self.call_action("setGamma", gamma)

        if rank is not None:
            self.set_clip_percentile(rank)
        elif min is not None and max is not None:
            self.call_action("setCustomScale", min, max)

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

    # HISTOGRAM

    # TODO TODO TODO move contours to contours!!
    @validate(Boolean())
    def use_cube_histogram(self, contours=False):
        """Use the cube histogram.

        Parameters
        ----------
        contours : {0}
            Apply to the contours. By default this is applied to the raster component.
        """
        self.call_action(f"setUseCubeHistogram{'Contours' if contours else ''}", True)

    # TODO TODO TODO move contours to contours!!
    @validate(Boolean())
    def use_channel_histogram(self, contours=False):
        """Use the channel histogram.

        Parameters
        ----------
        contours : {0}
            Apply to the contours. By default this is applied to the raster component.
        """
        self.call_action(f"setUseCubeHistogram{'Contours' if contours else ''}", False)

    @validate(Number(0, 100))
    def set_clip_percentile(self, rank):
        """Set the clip percentile.

        Parameters
        ----------
        rank : {0}
            The percentile rank.
        """
        preset_ranks = [90, 95, 99, 99.5, 99.9, 99.95, 99.99, 100]
        self.call_action("setPercentileRank", rank)
        if rank not in preset_ranks:
            self.call_action("setPercentileRank", -1)  # select 'custom' rank button
