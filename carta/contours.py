"""This module contains functionality for interacting with the contours of an image. The class in this module should not be instantiated directly. When an image object is created, a contours object is automatically created as a property."""

from .util import BasePathMixin
from .constants import Colormap, SmoothingMode, ContourDashMode
from .validation import validate, Number, Color, Constant, Boolean, NoneOr, IterableOf, all_optional


class Contours(BasePathMixin):
    """Utility object for collecting image functions related to contours.

    Parameters
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this contours object.

    Attributes
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this contours object.
    session : :obj:`carta.session.Session` object
        The session object associated with this contours object.
    """

    def __init__(self, image):
        self.image = image
        self.session = image.session
        self._base_path = f"{image._base_path}.contourConfig"

    @validate(*all_optional(IterableOf(Number()), Constant(SmoothingMode), Number()))
    def configure(self, levels=None, smoothing_mode=None, smoothing_factor=None):
        """Configure contours.

        Parameters
        ----------
        levels : {0}
            The contour levels. This may be a numeric numpy array; e.g. the output of ``arange``. If this is unset, the current configured levels will be used.
        smoothing_mode : {1}
            The smoothing mode. If this is unset, the frontend default will be used.
        smoothing_factor : {2}
            The smoothing kernel size in pixels. If this is unset, the frontend default will be used.
        """
        if levels is None:
            levels = self.macro("", "levels")
        if smoothing_mode is None:
            smoothing_mode = self.macro("", "smoothingMode")
        if smoothing_factor is None:
            smoothing_factor = self.macro("", "smoothingFactor")
        self.call_action("setContourConfiguration", levels, smoothing_mode, smoothing_factor)

    @validate(*all_optional(Constant(ContourDashMode), Number()))
    def set_style(self, dash_mode=None, dash_thickness=None):
        """Set the contour dash style.

        Parameters
        ----------
        dash_mode : {0}
            The dash mode.
        dash_thickness : {1}
            The dash thickness.
        """
        if dash_mode is not None:
            self.call_action("setDashMode", dash_mode)
        if dash_thickness is not None:
            self.call_action("setThickness", dash_thickness)

    @validate(Color())
    def set_color(self, color):
        """Set the contour color.

        This automatically disables use of the contour colormap.

        Parameters
        ----------
        color : {0}
            The color. The default is green.
        """
        self.call_action("setColor", color)
        self.call_action("setColormapEnabled", False)

    @validate(Constant(Colormap), NoneOr(Number()), NoneOr(Number()))
    def set_colormap(self, colormap, bias=None, contrast=None):
        """Set the contour colormap.

        This automatically enables use of the contour colormap.

        Parameters
        ----------
        colormap : {0}
            The colormap. The default is :obj:`carta.constants.Colormap.VIRIDIS`.
        bias : {1}
            The colormap bias.
        contrast : {2}
            The colormap contrast.
        """
        self.call_action("setColormap", colormap)
        self.call_action("setColormapEnabled", True)
        if bias is not None:
            self.call_action("setColormapBias", bias)
        if contrast is not None:
            self.call_action("setColormapContrast", contrast)

    def apply(self):
        """Apply the contour configuration."""
        self.image.call_action("applyContours")

    @validate(*all_optional(*configure.VARGS, *set_style.VARGS, *set_color.VARGS, *set_colormap.VARGS))
    def plot(self, levels=None, smoothing_mode=None, smoothing_factor=None, dash_mode=None, dash_thickness=None, color=None, colormap=None, bias=None, contrast=None):
        """Configure contour levels, scaling, dash, and colour or colourmap; and apply contours; in a single step.

        If both a colour and a colourmap are provided, the colourmap will be visible.

        Parameters
        ----------
        levels : {0}
            The contour levels. This may be a numeric numpy array; e.g. the output of ``arange``. If this is unset, the current configured levels will be used.
        smoothing_mode : {1}
            The smoothing mode. If this is unset, the frontend default will be used.
        smoothing_factor : {2}
            The smoothing kernel size in pixels. If this is unset, the frontend default will be used.
        dash_mode : {3}
            The dash mode.
        dash_thickness : {4}
            The dash thickness.
        color : {5}
            The color. The default is green.
        colormap : {6}
            The colormap. The default is :obj:`carta.constants.Colormap.VIRIDIS`.
        bias : {7}
            The colormap bias.
        contrast : {8}
            The colormap contrast.
        """
        self.configure(levels, smoothing_mode, smoothing_factor)
        self.set_style(dash_mode, dash_thickness)
        if color is not None:
            self.set_color(color)
        if colormap is not None:
            self.set_colormap(colormap, bias, contrast)
        self.apply()

    def clear(self):
        """Clear the contours."""
        self.image.call_action("clearContours", True)

    @validate(Boolean())
    def set_visible(self, state):
        """Set the contour visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        self.call_action("setVisible", state)

    def show(self):
        """Show the contours."""
        self.set_visible(True)

    def hide(self):
        """Hide the contours."""
        self.set_visible(False)

    # HISTOGRAM

    def use_cube_histogram(self):
        """Use the cube histogram."""
        self.image.raster.call_action("setUseCubeHistogramContours", True)

    @validate(Boolean())
    def use_channel_histogram(self):
        """Use the channel histogram."""
        self.image.raster.call_action("setUseCubeHistogramContours", False)
