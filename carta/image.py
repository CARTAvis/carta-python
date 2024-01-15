"""This module contains an image class which represents a single image open in the session.

Image objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.session.Session` object.
"""

from .constants import Polarization, SpatialAxis
from .util import Macro, cached, BasePathMixin
from .units import AngularSize, WorldCoordinate
from .validation import validate, Number, Constant, Boolean, Evaluate, Attr, Attrs, OneOf, Size, Coordinate, String
from .metadata import parse_header

from .raster import Raster
from .contours import Contours
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
    raster : :obj:`carta.raster.Raster`
        Sub-object with functions related to the raster image.
    contours : :obj:`carta.contours.Contours`
        Sub-object with functions related to the contours.
    vectors : :obj:`carta.vector_overlay.VectorOverlay`
        Sub-object with functions related to the vector overlay.
    """

    def __init__(self, session, image_id):
        self.session = session
        self.image_id = image_id

        self._base_path = f"frameMap[{image_id}]"
        self._frame = Macro("", self._base_path)

        # Sub-objects grouping related functions
        self.raster = Raster(self)
        self.contours = Contours(self)
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

    # PER-IMAGE WCS OVERLAY

    @validate(String())
    def set_custom_title(self, title_text):
        """Set a custom title for this image.

        This also automatically enables custom title text for all images. It can be disabled with :obj:`carta.wcs_overlay.Title.set_custom_text`.

        Parameters
        ----------
        title_text : {0}
            The custom title text.
        """
        self.call_action("setTitleCustomText", title_text)
        self.session.wcs.title.set_custom_text(True)

    @validate(String())
    def set_custom_colorbar_label(self, label_text):
        """Set a custom colorbar label for this image.

        This also automatically enables custom colorbar label text for all images. It can be disabled with :obj:`carta.wcs_overlay.Colorbar.set_label_custom_text`.

        Parameters
        ----------
        label_text : {0}
            The custom colorbar label text.
        """
        self.call_action("setColorbarLabelCustomText", label_text)
        self.session.wcs.colorbar.set_label_custom_text(True)

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

            number_format_x, number_format_y = self.session.wcs.numbers.format
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

    # CLOSE

    def close(self):
        """Close this image."""
        self.session.call_action("closeFile", self._frame, False)
