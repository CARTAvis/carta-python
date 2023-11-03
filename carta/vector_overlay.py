"""This module contains functionality for interacting with the vector overlay of an image. The class in this module should not be instantiated directly. When an image object is created, a vector overlay object is automatically created as a property."""

from .util import logger, Macro, BasePathMixin
from .constants import Colormap, VectorOverlaySource, Auto
from .validation import validate, Number, Color, Constant, Boolean, all_optional, Union, vargs


class VectorOverlay(BasePathMixin):
    """Utility object for collecting image functions related to the vector overlay.

    Parameters
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this vector overlay.

    Attributes
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this vector overlay.
    session : :obj:`carta.session.Session` object
        The session object associated with this vector overlay.
    """

    def __init__(self, image):
        self.image = image
        self.session = image.session
        self._base_path = f"{image._base_path}.vectorOverlayConfig"

    @validate(*all_optional(Constant(VectorOverlaySource), Constant(VectorOverlaySource), Boolean(), Number(), Number(), Boolean(), Number(), Boolean(), Number(), Number()))
    def configure(self, angular_source=None, intensity_source=None, pixel_averaging_enabled=None, pixel_averaging=None, fractional_intensity=None, threshold_enabled=None, threshold=None, debiasing=None, q_error=None, u_error=None):
        """Configure vector overlay.

        All parameters are optional. For each option that is not provided, the value currently set in the frontend will be preserved. Initial frontend settings are noted below.

        We deduce some boolean options. For example, providing an explicit pixel averaging width with the **pixel_averaging** parameter will automatically enable pixel averaging unless **pixel_averaging_enabled** is also explicitly set to ``False``. To disable pixel averaging, explicitly set **pixel_averaging_enabled** to ``False``.

        Parameters
        ----------
        angular_source : {0}
            The angular source. This is initially set to computed PA if the image contains Stokes information, otherwise to the current image.
        intensity_source : {1}
            The intensity source. This is initially set to computed PI if the image contains Stokes information, otherwise to the current image.
        pixel_averaging_enabled : {2}
            Enable pixel averaging. This is initially enabled if the pixel averaging width is positive.
        pixel_averaging : {3}
            The pixel averaging width in pixels. The initial value can be configured in the frontend preferences (the default is ``4``).
        fractional_intensity : {4}
            Enable fractional polarization intensity. The initial value can be configured in the frontend preferences. By default this is disabled and the absolute polarization intensity is used.
        threshold_enabled : {5}
            Enable threshold. Initially the threshold is disabled.
        threshold : {6}
            The threshold in Jy/pixels. The initial value is zero.
        debiasing : {7}
            Enable debiasing. This is initially disabled.
        q_error : {8}
            The Stokes Q error in Jy/beam. Set both this and ``u_error`` to enable debiasing. Initially set to zero.
        u_error : {9}
            The Stokes U error in Jy/beam. Set both this and ``q_error`` to enable debiasing. Initially set to zero.
        """

        # Avoid doing a lot of needless work for a no-op
        args = (angular_source, intensity_source, pixel_averaging_enabled, pixel_averaging, fractional_intensity, threshold_enabled, threshold, debiasing, q_error, u_error)
        if any(a is not None for a in args):
            if pixel_averaging is not None and pixel_averaging_enabled is None:
                pixel_averaging_enabled = True
            if threshold is not None and threshold_enabled is None:
                threshold_enabled = True
            if q_error is not None and u_error is not None and debiasing is None:
                debiasing = True

            if (q_error is not None and u_error is None) or (q_error is None and u_error is not None):
                debiasing = False
                logger.warning("The Stokes Q error and Stokes U error must both be set to enable debiasing.")

            args = []

            for value, attr_name in (
                (angular_source, "angularSource"),
                (intensity_source, "intensitySource"),
                (pixel_averaging_enabled, "pixelAveragingEnabled"),
                (pixel_averaging, "pixelAveraging"),
                (fractional_intensity, "fractionalIntensity"),
                (threshold_enabled, "thresholdEnabled"),
                (threshold, "threshold"),
                (debiasing, "debiasing"),
                (q_error, "qError"),
                (u_error, "uError"),
            ):
                if value is None:
                    args.append(self.macro("", attr_name))
                else:
                    args.append(value)

            self.call_action("setVectorOverlayConfiguration", *args)

    @validate(Number())
    def set_thickness(self, thickness):
        """Set the vector overlay line thickness.

        Parameters
        ----------
        thickness : {0}
            The line thickness in pixels. The initial value is ``1``.
        """
        self.call_action("setThickness", thickness)

    @validate(*all_optional(Union(Number(), Constant(Auto)), Union(Number(), Constant(Auto))))
    def set_intensity_range(self, intensity_min=None, intensity_max=None):
        """Set the vector overlay intensity range.

        Parameters
        ----------
        intensity_min : {0}
            The minimum value of intensity in Jy/pixel. Use :obj:`carta.constants.Auto.AUTO` to clear the custom value and calculate it automatically.
        intensity_max : {1}
            The maximum value of intensity in Jy/pixel. Use :obj:`carta.constants.Auto.AUTO` to clear the custom value and calculate it automatically.
        """
        if intensity_min is not None or intensity_max is not None:
            if intensity_min is None:
                intensity_min = self.macro("", "intensityMin")
            elif intensity_min is Auto.AUTO:
                intensity_min = Macro.UNDEFINED

            if intensity_max is None:
                intensity_max = self.macro("", "intensityMax")
            elif intensity_max is Auto.AUTO:
                intensity_max = Macro.UNDEFINED

            self.call_action("setIntensityRange", intensity_min, intensity_max)

    @validate(Number(), Number())
    def set_length_range(self, length_min, length_max):
        """Set the vector overlay length range.

        Parameters
        ----------
        length_min : {0}
            The minimum value of line length in pixels. The initial value is ``0``.
        length_max : {1}
            The maximum value of line length in pixels. The initial value is ``20``.
        """
        self.call_action("setLengthRange", length_min, length_max)

    @validate(Number())
    def set_rotation_offset(self, rotation_offset):
        """Set the vector overlay rotation offset.

        Parameters
        ----------
        rotation_offset : {0}
            The rotation offset in degrees. The initial value is ``0``.
        """
        self.call_action("setRotationOffset", rotation_offset)

    @validate(Color())
    def set_color(self, color):
        """Set the vector overlay color.

        This automatically disables the colormap.

        Parameters
        ----------
        color : {0}
            The color. The initial value is ``#238551`` (a shade of green).
        """
        self.call_action("setColor", color)
        self.call_action("setColormapEnabled", False)

    @validate(Constant(Colormap))
    def set_colormap(self, colormap):
        """Set the vector overlay colormap.

        This also automatically enables the colormap.

        Parameters
        ----------
        colormap : {0}
            The colormap. The initial value is :obj:`carta.constants.Colormap.VIRIDIS`.
        """
        self.call_action("setColormap", colormap)
        self.call_action("setColormapEnabled", True)

    @validate(*all_optional(Number(-1, 1), Number(0, 2)))
    def set_bias_and_contrast(self, bias=None, contrast=None):
        """Set the vector overlay bias and contrast.

        Parameters
        ----------
        bias : {0}
            The colormap bias. The initial value is ``0``.
        contrast : {1}
            The colormap contrast. The initial value is ``1``.
        """
        if bias is not None:
            self.call_action("setColormapBias", bias)
        if contrast is not None:
            self.call_action("setColormapContrast", contrast)

    def apply(self):
        """Apply the vector overlay configuration."""
        self.image.call_action("applyVectorOverlay")

    @validate(*all_optional(*vargs(configure, set_thickness, set_intensity_range, set_length_range, set_rotation_offset, set_color, set_colormap, set_bias_and_contrast)))
    def plot(self, angular_source=None, intensity_source=None, pixel_averaging_enabled=None, pixel_averaging=None, fractional_intensity=None, threshold_enabled=None, threshold=None, debiasing=None, q_error=None, u_error=None, thickness=None, intensity_min=None, intensity_max=None, length_min=None, length_max=None, rotation_offset=None, color=None, colormap=None, bias=None, contrast=None):
        """Configure, style, and apply the vector overlay in a single step.

        If both a color and a colormap are provided, the colormap will be enabled.

        Parameters
        ----------
        angular_source : {0}
            The angular source. This is initially set to computed PA if the image contains Stokes information, otherwise to the current image.
        intensity_source : {1}
            The intensity source. This is initially set to computed PI if the image contains Stokes information, otherwise to the current image.
        pixel_averaging_enabled : {2}
            Enable pixel averaging. This is initially enabled if the pixel averaging width is positive.
        pixel_averaging : {3}
            The pixel averaging width in pixels. The initial value can be configured in the frontend preferences (the default is ``4``).
        fractional_intensity : {4}
            Enable fractional polarization intensity. The initial value can be configured in the frontend preferences. By default this is disabled and the absolute polarization intensity is used.
        threshold_enabled : {5}
            Enable threshold. Initially the threshold is disabled.
        threshold : {6}
            The threshold in Jy/pixels. The initial value is zero.
        debiasing : {7}
            Enable debiasing. This is initially disabled.
        q_error : {8}
            The Stokes Q error in Jy/beam. Set both this and ``u_error`` to enable debiasing. Initially set to zero.
        u_error : {9}
            The Stokes U error in Jy/beam. Set both this and ``q_error`` to enable debiasing. Initially set to zero.
        thickness : {10}
            The line thickness in pixels. The initial value is ``1``.
        intensity_min : {11}
            The minimum value of intensity in Jy/pixel. Use :obj:`carta.constants.Auto.AUTO` to clear the custom value and calculate it automatically.
        intensity_max : {12}
            The maximum value of intensity in Jy/pixel. Use :obj:`carta.constants.Auto.AUTO` to clear the custom value and calculate it automatically.
        length_min : {13}
            The minimum value of line length in pixels. The initial value is ``0``.
        length_max : {14}
            The maximum value of line length in pixels. The initial value is ``20``.
        rotation_offset : {15}
            The rotation offset in degrees. The initial value is ``0``.
        color : {16}
            The color. The initial value value is ``#238551`` (a shade of green).
        colormap : {17}
            The colormap. The initial value is :obj:`carta.constants.Colormap.VIRIDIS`.
        bias : {18}
            The colormap bias. The initial value is ``0``.
        contrast : {19}
            The colormap contrast. The initial value is ``1``.
        """
        changes_made = False

        for method, args in [
            (self.configure, (angular_source, intensity_source, pixel_averaging_enabled, pixel_averaging, fractional_intensity, threshold_enabled, threshold, debiasing, q_error, u_error)),
            (self.set_thickness, (thickness,)),
            (self.set_intensity_range, (intensity_min, intensity_max)),
            (self.set_length_range, (length_min, length_max)),
            (self.set_rotation_offset, (rotation_offset,)),
            (self.set_color, (color,)),
            (self.set_colormap, (colormap,)),
            (self.set_bias_and_contrast, (bias, contrast)),
        ]:
            if any(a is not None for a in args):
                method(*args)
                changes_made = True

        if changes_made:
            self.apply()

    def clear(self):
        """Clear the vector overlay configuration."""
        self.image.call_action("clearVectorOverlay", True)

    @validate(Boolean())
    def set_visible(self, state):
        """Set the vector overlay visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        self.call_action("setVisible", state)

    def show(self):
        """Show the vector overlay."""
        self.set_visible(True)

    def hide(self):
        """Hide the vector overlay."""
        self.set_visible(False)
