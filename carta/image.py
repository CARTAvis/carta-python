"""This module contains an image class which represents a single image open in the session.

Image objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.session.Session` object.
"""
import posixpath

from .constants import Colormap, Scaling, SmoothingMode, ContourDashMode
from .util import Macro, cached
from .validation import validate, Number, Color, Constant, Boolean, NoneOr, IterableOf, Evaluate, Attr


class Image:
    """This object corresponds to an image open in a CARTA frontend session.

    This class should not be instantiated directly. Instead, use the session object's methods for opening new images or retrieving existing images.

    Parameters
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image.
    image_id : integer
        The ID identifying this image within the session. This is a unique number which is not reused, not the index of the image within the list of currently open images.
    file_name : string
        The file name of the image. This is not a full path.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image.
    image_id : integer
        The ID identifying this image within the session.
    file_name : string
        The file name of the image.
    """

    def __init__(self, session, image_id, file_name):
        self.session = session
        self.image_id = image_id
        self.file_name = file_name

        self._base_path = f"frameMap[{image_id}]"
        self._frame = Macro("", self._base_path)

    @classmethod
    def new(cls, session, path, hdu, append):
        """Open or append a new image in the session and return an image object associated with it.

        This method should not be used directly. It is wrapped by :obj:`carta.session.Session.open_image` and :obj:`carta.session.Session.append_image`.

        Parameters
        ----------
        session : :obj:`carta.session.Session`
            The session object.
        path : string
            The path to the image file, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        hdu : string
            The HDU to open.
        append : boolean
            Whether the image should be appended. By default it is not, and all other open images are closed.

        Returns
        -------
        :obj:`carta.image.Image`
            A new image object.
        """
        path = session.resolve_file_path(path)
        directory, file_name = posixpath.split(path)
        image_id = session.call_action("appendFile" if append else "openFile", directory, file_name, hdu, return_path="frameInfo.fileId")

        return cls(session, image_id, file_name)

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
        return [cls(session, f["value"], f["label"].split(":")[1].strip()) for f in image_list]

    def __repr__(self):
        return f"{self.session.session_id}:{self.image_id}:{self.file_name}"

    def call_action(self, path, *args, **kwargs):
        """Convenience wrapper for the session object's generic action method.

        This method calls :obj:`carta.session.Session.call_action` after prepending this image's base path to the path parameter.

        Parameters
        ----------
        path : string
            The path to an action relative to this image's frame store.
        *args
            A variable-length list of parameters. These are passed unmodified to the session method.
        **kwargs
            Arbitrary keyword parameters. These are passed unmodified to the session method.

        Returns
        -------
        object or None
            The unmodified return value of the session method.
        """
        return self.session.call_action(f"{self._base_path}.{path}", *args, **kwargs)

    def get_value(self, path):
        """Convenience wrapper for the session object's generic method for retrieving attribute values.

        This method calls :obj:`carta.session.Session.get_value` after prepending this image's base path to the path parameter.

        Parameters
        ----------
        path : string
            The path to an attribute relative to this image's frame store.

        Returns
        -------
        object
            The unmodified return value of the session method.
        """
        return self.session.get_value(f"{self._base_path}.{path}")

    # METADATA

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
        """The header of the image.

        Entries with T or F string values are automatically converted to booleans.

        ``HISTORY``, ``COMMENT`` and blank keyword entries are aggregated into single entries with list values and with ``'HISTORY'``, ``'COMMENT'`` and ``''`` as keys, respectively. An entry in the history list which begins with ``'>'`` will be concatenated with the previous entry.

        Adjacent ``COMMENT`` entries are not concatenated automatically.

        Any other header entries with no values are given values of ``None``.

        Returns
        -------
        dict of string to string, integer, float, boolean, ``None`` or list of strings
            The header of the image, with field names as keys.
        """
        raw_header = self.get_value("frameInfo.fileInfoExtended.headerEntries")

        header = {}

        history = []
        comment = []
        blank = []

        def header_value(raw_entry):
            try:
                return raw_entry["numericValue"]
            except KeyError:
                try:
                    value = raw_entry["value"]
                    if value == 'T':
                        return True
                    if value == 'F':
                        return False
                    return value
                except KeyError:
                    return None

        for i, raw_entry in enumerate(raw_header):
            name = raw_entry["name"]

            if name.startswith("HISTORY "):
                line = name[8:]
                if line.startswith(">") and history:
                    history[-1] = history[-1] + line[1:]
                else:
                    history.append(line)
                continue

            if name.startswith("COMMENT "):
                comment.append(name[8:])
                continue

            if name.startswith(" " * 8):
                blank.append(name[8:])
                continue

            header[name] = header_value(raw_entry)

        if history:
            header["HISTORY"] = history

        if comment:
            header["COMMENT"] = comment

        if blank:
            header[""] = blank

        return header

    @property
    @cached
    def shape(self):
        """The shape of the image.

        Returns
        -------
        list of integers
            The shape of the image; dimensions ordered with width last.

        """
        return list(reversed([self.width, self.height, self.depth, self.stokes][:self.ndim]))

    @property
    @cached
    def width(self):
        """The width of the image.

        Returns
        -------
        integer
            The width.
        """
        return self.get_value("frameInfo.fileInfoExtended.width")

    @property
    @cached
    def height(self):
        """The height of the image.

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
    def stokes(self):
        """The number of Stokes parameters of the image.

        Returns
        -------
        integer
            The number of Stokes parameters.
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

    @validate(Evaluate(Number, 0, Attr("depth"), Number.INCLUDE_MIN), Evaluate(Number, 0, Attr("stokes"), Number.INCLUDE_MIN), Boolean())
    def set_channel_stokes(self, channel=None, stokes=None, recursive=True):
        """Set the channel and/or Stokes.

        Parameters
        ----------
        channel : {0}
            The desired channel. Defaults to the current channel.
        stokes : {1}
            The desired stokes. Defaults to the current Stokes.
        recursive : {2}
            Whether to perform the same change on all spectrally matched images. Defaults to True.
        """
        channel = channel or self.get_value("requiredChannel")
        stokes = stokes or self.get_value("requiredStokes")
        self.call_action("setChannels", channel, stokes, recursive)

    @validate(Number(), Number())
    def set_center(self, x, y):
        """Set the center position.

        TODO: what are the units?

        Parameters
        ----------
        x : {0}
            The X position.
        y : {1}
            The Y position.
        """
        self.call_action("setCenter", x, y)

    @validate(Number(), Boolean())
    def set_zoom(self, zoom, absolute=True):
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
    @validate(Constant(Scaling), NoneOr(Number()), NoneOr(Number()), NoneOr(Number()), NoneOr(Number()))
    def set_scaling(self, scaling, alpha=None, gamma=None, min=None, max=None):
        """Set the colormap scaling.

        Parameters
        ----------
        scaling : {0}
            The scaling type.
        alpha : {1}
            The alpha value (only applicable to ``LOG`` and ``POWER`` scaling types).
        gamma : {2}
            The gamma value (only applicable to the ``GAMMA`` scaling type).
        min : {3}
            The minimum of the scale. Only used if both *min* and *max* are set.
        max : {4}
            The maximum of the scale. Only used if both *min* and *max* are set.
        """
        self.call_action("renderConfig.setScaling", scaling)
        if scaling in (Scaling.LOG, Scaling.POWER) and alpha is not None:
            self.call_action("renderConfig.setAlpha", alpha)
        elif scaling == Scaling.GAMMA and gamma is not None:
            self.call_action("renderConfig.setGamma", gamma)
        if min is not None and max is not None:
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

    @validate(IterableOf(Number()), Constant(SmoothingMode), Number())
    def configure_contours(self, levels, smoothing_mode=SmoothingMode.GAUSSIAN_BLUR, smoothing_factor=4):
        """Configure contours.

        Parameters
        ----------
        levels : {0}
            The contour levels. This may be a numeric numpy array; e.g. the output of ``arange``.
        smoothing_mode : {1}
            The smoothing mode.
        smoothing_factor : {2}
            The smoothing factor.
        """
        self.call_action("contourConfig.setContourConfiguration", levels, smoothing_mode, smoothing_factor)

    @validate(NoneOr(Constant(ContourDashMode)), NoneOr(Number()))
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
            The color.
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
            The colormap.
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
    def set_percentile_rank(self, rank):
        """Set the percentile rank.

        Parameters
        ----------
        rank : {0}
            The percentile rank.
        """
        self.call_action("renderConfig.setPercentileRank", rank)

    # CLOSE

    def close(self):
        """Close this image."""
        self.session.call_action("closeFile", self._frame)
