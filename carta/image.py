"""This module contains an image class which represents a single image open in the session.

Image objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.session.Session` object.
"""

from .constants import Colormap, Scaling, SmoothingMode, ContourDashMode, Polarization, SpatialAxis
from .util import Macro, cached, BasePathMixin
from .units import AngularSize, WorldCoordinate
from .validation import validate, Number, Color, Constant, Boolean, NoneOr, IterableOf, Evaluate, Attr, Attrs, OneOf, Size, Coordinate, all_optional
from .metadata import parse_header
from .vector_overlay import VectorOverlay


class Image(BasePathMixin):
    """This object corresponds to an image open in a CARTA frontend session.

    This class should not be instantiated directly. Instead, use the session object's methods for opening new images or retrieving existing images.

    Parameters
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image.
    image_id : integer
        The ID identifying this image within the session. This is a unique number which is not reused, not the index of the image within the list of currently open images.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image.
    image_id : integer
        The ID identifying this image within the session.
    """

    def __init__(self, session, image_id):
        self.session = session
        self.image_id = image_id

        self._base_path = f"frameMap[{image_id}]"
        self._frame = Macro("", self._base_path)

        # Sub-objects grouping related functions
        self.vectors = VectorOverlay(self)

    @classmethod
    def new(cls, session, directory, file_name, hdu, append, image_arithmetic, make_active=True, update_directory=False):
        """Open or append a new image in the session and return an image object associated with it.

        This method should not be used directly. It is wrapped by :obj:`carta.session.Session.open_image`, :obj:`carta.session.Session.open_complex_image` and :obj:`carta.session.Session.open_LEL_image`.

        Parameters
        ----------
        session : :obj:`carta.session.Session`
            The session object.
        directory : string
            The directory containing the image file or the base directory for the LEL arithmetic expression, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        file_name : string
            The name of the image file, or a LEL arithmetic expression.
        hdu : string
            The HDU to open.
        append : boolean
            Whether the image should be appended.
        image_arithmetic : boolean
            Whether the file name should be interpreted as a LEL expression.
        make_active : boolean
            Whether the image should be made active in the frontend. This only applies if an image is being appended. The default is ``True``.
        update_directory : boolean
            Whether the starting directory of the frontend file browser should be updated to the directory provided. The default is ``False``.

        Returns
        -------
        :obj:`carta.image.Image`
            A new image object.
        """
        command = "appendFile" if append else "openFile"
        directory = session.resolve_file_path(directory)

        params = [directory, file_name, hdu, image_arithmetic]
        if append:
            params.append(make_active)
        params.append(update_directory)

        image_id = session.call_action(command, *params, return_path="frameInfo.fileId")
        return cls(session, image_id)

    @classmethod
    def from_list(cls, session, image_list):
        """Create a list of image objects from a list of open images retrieved from the frontend.

        This method should not be used directly. It is wrapped by :obj:`carta.session.Session.image_list`.

        Parameters
        ----------
        session : :obj:`carta.session.Session`
            The session object.
        image_list : list of dicts
            The JSON object representing frame names retrieved from the frontend.

        Returns
        -------
        list of :obj:`carta.image.Image`
            A list of new image objects.
        """
        return [cls(session, f["value"]) for f in image_list]

    def __repr__(self):
        """A human-readable representation of this image object."""
        return f"{self.session.session_id}:{self.image_id}:{self.file_name}"

    # METADATA

    @property
    @cached
    def file_name(self):
        """The name of the image.

        Returns
        -------
        string
            The image name.
        """
        return self.get_value("frameInfo.fileInfo.name")

    @property
    @cached
    def directory(self):
        """The path to the directory containing the image.

        Returns
        -------
        string
            The directory path.
        """
        return self.get_value("frameInfo.directory")

    @property
    @cached
    def header(self):
        """The header of the image, parsed from the raw frontend data (see :obj:`carta.metadata.parse_header`).

        Returns
        -------
        dict of string to string, integer, float, boolean, ``None`` or list of strings
            The header of the image, with field names as keys.
        """
        raw_header = self.get_value("frameInfo.fileInfoExtended.headerEntries")
        return parse_header(raw_header)

    @property
    @cached
    def shape(self):
        """The shape of the image.

        Returns
        -------
        list of integers
            The shape of the image; dimensions ordered with width last.

        """
        return list(reversed([self.width, self.height, self.depth, self.num_polarizations][:self.ndim]))

    @property
    @cached
    def width(self):
        """The width of the image in pixels.

        Returns
        -------
        integer
            The width.
        """
        return self.get_value("frameInfo.fileInfoExtended.width")

    @property
    @cached
    def height(self):
        """The height of the image in pixels.

        Returns
        -------
        integer
            The height.
        """
        return self.get_value("frameInfo.fileInfoExtended.height")

    @property
    @cached
    def depth(self):
        """The depth of the image.

        Returns
        -------
        integer
            The depth.
        """
        return self.get_value("frameInfo.fileInfoExtended.depth")

    @property
    @cached
    def num_polarizations(self):
        """The number of polarizations of the image, excluding computed polarizations.

        Returns
        -------
        integer
            The number of polarizations.
        """
        return self.get_value("frameInfo.fileInfoExtended.stokes")

    @property
    @cached
    def ndim(self):
        """The number of dimensions of the image.

        Returns
        -------
        integer
            The number of dimensions.
        """
        return self.get_value("frameInfo.fileInfoExtended.dimensions")

    @property
    @cached
    def polarizations(self):
        """The available polarizations of the image.

        This includes Stokes parameters, correlations, and computed components.

        Returns
        -------
        list of members of :obj:`carta.constants.Polarization`
            The available polarizations.
        """
        return [Polarization(p) for p in self.get_value("polarizations")]

    # SELECTION

    def make_active(self):
        """Make this the active image."""
        self.session.call_action("setActiveFrameById", self.image_id)

    def make_spatial_reference(self):
        """Make this image the spatial reference."""
        self.session.call_action("setSpatialReference", self._frame)

    @validate(Boolean())
    def set_spatial_matching(self, state):
        """Enable or disable spatial matching.

        Parameters
        ----------
        state : boolean
            The desired spatial matching state.
        """
        self.session.call_action("setSpatialMatchingEnabled", self._frame, state)

    def make_spectral_reference(self):
        """Make this image the spectral reference."""
        self.session.call_action("setSpectralReference", self._frame)

    @validate(Boolean())
    def set_spectral_matching(self, state):
        """Enable or disable spectral matching.

        Parameters
        ----------
        state : boolean
            The desired spectral matching state.
        """
        self.session.call_action("setSpectralMatchingEnabled", self._frame, state)

    @validate(Boolean())
    def set_cube_matching(self, state):
        """Enable or disable spatial and spectral matching.

        Parameters
        ----------
        state : boolean
            The desired spatial and spectral matching state.
        """
        self.set_spatial_matching(state)
        self.set_spectral_matching(state)

    def make_raster_scaling_reference(self):
        """Make this image the raster scaling reference."""
        self.session.call_action("setRasterScalingReference", self._frame)

    @validate(Boolean())
    def set_raster_scaling_matching(self, state):
        """Enable or disable raster scaling matching.

        Parameters
        ----------
        state : boolean
            The desired raster scaling matching state.
        """
        self.session.call_action("setRasterScalingMatchingEnabled", self._frame, state)

    # NAVIGATION

    @validate(Evaluate(Number, 0, Attr("depth"), Number.INCLUDE_MIN, step=1), Boolean())
    def set_channel(self, channel, recursive=True):
        """Set the channel.

        Parameters
        ----------
        channel : {0}
            The desired channel.
        recursive : {1}
            Whether to perform the same change on all spectrally matched images. Defaults to True.
        """
        self.call_action("setChannels", channel, self.macro("", "requiredStokes"), recursive)

    @validate(Evaluate(OneOf, Attrs("polarizations")), Boolean())
    def set_polarization(self, polarization, recursive=True):
        """Set the polarization.

        Parameters
        ----------
        polarization : {0}
            The desired polarization.
        recursive : {1}
            Whether to perform the same change on all spectrally matched images. Defaults to True.
        """
        if polarization < Polarization.PTOTAL:
            polarization = self.polarizations.index(polarization)

        self.call_action("setChannels", self.macro("", "requiredChannel"), polarization, recursive)

    @property
    @cached
    def valid_wcs(self):
        """Whether the image contains valid WCS information.

        Returns
        -------
        boolean
            Whether the image has WCS information.
        """
        return self.get_value("validWcs")

    @validate(Coordinate(), Coordinate())
    def set_center(self, x, y):
        """Set the center position, in image or world coordinates.

        World coordinates are interpreted according to the session's globally set coordinate system and any custom number formats. These can be changed using :obj:`carta.session.set_coordinate_system` and :obj:`set_custom_number_format`.

        Coordinates must either both be image coordinates or match the current number formats. Numbers are interpreted as image coordinates, and numeric strings with no units are interpreted as degrees.

        Parameters
        ----------
        x : {0}
            The X position.
        y : {1}
            The Y position.

        Raises
        ------
        ValueError
            If a mix of image and world coordinates is provided, if world coordinates are provided and the image has no valid WCS information, or if world coordinates do not match the session-wide number formats.
        """
        x_is_pixel = isinstance(x, (int, float))
        y_is_pixel = isinstance(y, (int, float))

        if x_is_pixel and y_is_pixel:
            # Image coordinates
            self.call_action("setCenter", x, y)

        elif x_is_pixel or y_is_pixel:
            raise ValueError("Cannot mix image and world coordinates.")

        else:
            if not self.valid_wcs:
                raise ValueError("Cannot parse world coordinates. This image does not contain valid WCS information. Please use image coordinates (in pixels) instead.")

            number_format_x, number_format_y, _ = self.session.number_format()
            x_value = WorldCoordinate.with_format(number_format_x).from_string(x, SpatialAxis.X)
            y_value = WorldCoordinate.with_format(number_format_y).from_string(y, SpatialAxis.Y)
            self.call_action("setCenterWcs", str(x_value), str(y_value))

    @validate(Size(), Constant(SpatialAxis))
    def zoom_to_size(self, size, axis):
        """Zoom to the given size along the specified axis.

        Numbers are interpreted as pixel sizes. Numeric strings with no units are interpreted as arcseconds.

        Parameters
        ----------
        size : {0}
            The size to zoom to.
        axis : {1}
            The spatial axis to use.

        Raises
        ------
        ValueError
            If an angular size is provided and the image has no valid WCS information.
        """
        if isinstance(size, (int, float)):
            self.call_action(f"zoomToSize{axis.upper()}", size)
        else:
            if not self.valid_wcs:
                raise ValueError("Cannot parse angular size. This image does not contain valid WCS information. Please use a pixel size instead.")
            self.call_action(f"zoomToSize{axis.upper()}Wcs", str(AngularSize.from_string(size)))

    @validate(Number(), Boolean())
    def set_zoom_level(self, zoom, absolute=True):
        """Set the zoom level.

        TODO: explain this more rigorously.

        Parameters
        ----------
        zoom : {0}
            The zoom level.
        absolute : {1}
            Whether the zoom level should be treated as absolute. By default it is adjusted by a scaling factor.
        """
        self.call_action("setZoom", zoom, absolute)

    # STYLE

    @validate(Constant(Colormap), Boolean(), NoneOr(Number()), NoneOr(Number()))
    def set_colormap(self, colormap, invert=False, bias=None, contrast=None):
        """Set the colormap.

        By default the colormap is not inverted, and the bias and contrast are reset to the frontend defaults of ``0`` and ``1`` respectively.

        Parameters
        ----------
        colormap : {0}
            The colormap.
        invert : {1}
            Whether the colormap should be inverted.
        bias : {2}
            A custom bias.
        contrast : {3}
            A custom contrast.
        """
        self.call_action("renderConfig.setColorMap", colormap)
        self.call_action("renderConfig.setInverted", invert)
        if bias is not None:
            self.call_action("renderConfig.setBias", bias)
        else:
            self.call_action("renderConfig.resetBias")
        if contrast is not None:
            self.call_action("renderConfig.setContrast", contrast)
        else:
            self.call_action("renderConfig.resetContrast")

    # TODO check whether this works as expected
    @validate(Constant(Scaling), NoneOr(Number()), NoneOr(Number()), NoneOr(Number(0, 100)), NoneOr(Number()), NoneOr(Number()))
    def set_scaling(self, scaling, alpha=None, gamma=None, rank=None, min=None, max=None):
        """Set the colormap scaling.

        Parameters
        ----------
        scaling : {0}
            The scaling type.
        alpha : {1}
            The alpha value (only applicable to ``LOG`` and ``POWER`` scaling types).
        gamma : {2}
            The gamma value (only applicable to the ``GAMMA`` scaling type).
        rank : {3}
            The clip percentile rank. If this is set, *min* and *max* are ignored, and will be calculated automatically.
        min : {4}
            Custom clip minimum. Only used if both *min* and *max* are set. Ignored if *rank* is set.
        max : {5}
            Custom clip maximum. Only used if both *min* and *max* are set. Ignored if *rank* is set.
        """
        self.call_action("renderConfig.setScaling", scaling)
        if scaling in (Scaling.LOG, Scaling.POWER) and alpha is not None:
            self.call_action("renderConfig.setAlpha", alpha)
        elif scaling == Scaling.GAMMA and gamma is not None:
            self.call_action("renderConfig.setGamma", gamma)
        if rank is not None:
            self.set_clip_percentile(rank)
        elif min is not None and max is not None:
            self.call_action("renderConfig.setCustomScale", min, max)

    @validate(Boolean())
    def set_raster_visible(self, state):
        """Set the raster image visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        self.call_action("renderConfig.setVisible", state)

    def show_raster(self):
        """Show the raster image."""
        self.set_raster_visible(True)

    def hide_raster(self):
        """Hide the raster image."""
        self.set_raster_visible(False)

    # CONTOURS

    @validate(*all_optional(IterableOf(Number()), Constant(SmoothingMode), Number()))
    def configure_contours(self, levels=None, smoothing_mode=None, smoothing_factor=None):
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
            levels = self.macro("contourConfig", "levels")
        if smoothing_mode is None:
            smoothing_mode = self.macro("contourConfig", "smoothingMode")
        if smoothing_factor is None:
            smoothing_factor = self.macro("contourConfig", "smoothingFactor")
        self.call_action("contourConfig.setContourConfiguration", levels, smoothing_mode, smoothing_factor)

    @validate(*all_optional(Constant(ContourDashMode), Number()))
    def set_contour_dash(self, dash_mode=None, thickness=None):
        """Set the contour dash style.

        Parameters
        ----------
        dash_mode : {0}
            The dash mode.
        thickness : {1}
            The dash thickness.
        """
        if dash_mode is not None:
            self.call_action("contourConfig.setDashMode", dash_mode)
        if thickness is not None:
            self.call_action("contourConfig.setThickness", thickness)

    @validate(Color())
    def set_contour_color(self, color):
        """Set the contour color.

        This automatically disables use of the contour colormap.

        Parameters
        ----------
        color : {0}
            The color. The default is green.
        """
        self.call_action("contourConfig.setColor", color)
        self.call_action("contourConfig.setColormapEnabled", False)

    @validate(Constant(Colormap), NoneOr(Number()), NoneOr(Number()))
    def set_contour_colormap(self, colormap, bias=None, contrast=None):
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
        self.call_action("contourConfig.setColormap", colormap)
        self.call_action("contourConfig.setColormapEnabled", True)
        if bias is not None:
            self.call_action("contourConfig.setColormapBias", bias)
        if contrast is not None:
            self.call_action("contourConfig.setColormapContrast", contrast)

    def apply_contours(self):
        """Apply the contour configuration."""
        self.call_action("applyContours")

    @validate(*all_optional(*configure_contours.VARGS, *set_contour_dash.VARGS, *set_contour_color.VARGS, *set_contour_colormap.VARGS))
    def plot_contours(self, levels=None, smoothing_mode=None, smoothing_factor=None, dash_mode=None, thickness=None, color=None, colormap=None, bias=None, contrast=None):
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
        thickness : {4}
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
        self.configure_contours(levels, smoothing_mode, smoothing_factor)
        self.set_contour_dash(dash_mode, thickness)
        if color is not None:
            self.set_contour_color(color)
        if colormap is not None:
            self.set_contour_colormap(colormap, bias, contrast)
        self.apply_contours()

    def clear_contours(self):
        """Clear the contours."""
        self.call_action("clearContours", True)

    @validate(Boolean())
    def set_contours_visible(self, state):
        """Set the contour visibility.

        Parameters
        ----------
        state : {0}
            The desired visibility state.
        """
        self.call_action("contourConfig.setVisible", state)

    def show_contours(self):
        """Show the contours."""
        self.set_contours_visible(True)

    def hide_contours(self):
        """Hide the contours."""
        self.set_contours_visible(False)

    # HISTOGRAM

    @validate(Boolean())
    def use_cube_histogram(self, contours=False):
        """Use the cube histogram.

        Parameters
        ----------
        contours : {0}
            Apply to the contours. By default this is applied to the raster image.
        """
        self.call_action(f"renderConfig.setUseCubeHistogram{'Contours' if contours else ''}", True)

    @validate(Boolean())
    def use_channel_histogram(self, contours=False):
        """Use the channel histogram.

        Parameters
        ----------
        contours : {0}
            Apply to the contours. By default this is applied to the raster image.
        """
        self.call_action(f"renderConfig.setUseCubeHistogram{'Contours' if contours else ''}", False)

    @validate(Number(0, 100))
    def set_clip_percentile(self, rank):
        """Set the clip percentile.

        Parameters
        ----------
        rank : {0}
            The percentile rank.
        """
        preset_ranks = [90, 95, 99, 99.5, 99.9, 99.95, 99.99, 100]
        self.call_action("renderConfig.setPercentileRank", rank)
        if rank not in preset_ranks:
            self.call_action("renderConfig.setPercentileRank", -1)  # select 'custom' rank button

    # CLOSE

    def close(self):
        """Close this image."""
        self.session.call_action("closeFile", self._frame, False)
