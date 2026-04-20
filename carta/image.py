"""This module contains the image classes representing image-view items open in the session.

Image objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.session.Session` object.
"""


from .constants import ImageType, Polarization, SpatialAxis, SpectralSystem, SpectralType, SpectralUnit
from .util import Macro, cached, BasePathMixin, CartaScriptingException, Point as Pt
from .units import AngularSize, WorldCoordinate
from .validation import validate, Number, Constant, Boolean, Evaluate, Attr, Attrs, OneOf, Size, Coordinate, NoneOr, IterableOf, Point
from .metadata import parse_header
from .raster import Raster
from .contours import Contours
from .vector_overlay import VectorOverlay
from .wcs_overlay import ImageWCSOverlay
from .region import RegionSet


class ImageBase:
    """Base class for image-view items (file-based images and color blendings).

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


class Image(ImageBase, BasePathMixin):
    """This object corresponds to a file-based image open in a CARTA frontend session.

    This class should not be instantiated directly. Instead, use the session object's methods for opening new images or retrieving existing images.

    Parameters
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image.
    file_id : integer
        The frontend file id identifying this image. This is a unique number which is not reused, not the index of the image within the list of currently open images.

    Attributes
    ----------
    session : :obj:`carta.session.Session`
        The session object associated with this image.
    file_id : integer
        The frontend file id identifying this image.
    raster : :obj:`carta.raster.Raster`
        Sub-object with functions related to the raster image.
    contours : :obj:`carta.contours.Contours`
        Sub-object with functions related to the contours.
    vectors : :obj:`carta.vector_overlay.VectorOverlay`
        Sub-object with functions related to the vector overlay.
    wcs :  :obj:`carta.wcs_overlay.ImageWCSOverlay`
        Sub-object with functions related to the WCS overlay.
    regions : :obj:`carta.region.RegionSet` object
        Functions for manipulating regions associated with this image.
    """

    _image_type = ImageType.FRAME

    def __init__(self, session, file_id):
        self.session = session
        self.file_id = file_id

        self._base_path = f"frameMap[{file_id}]"
        self._frame = Macro("", self._base_path)

        # Sub-objects grouping related functions
        self.raster = Raster(self)
        self.contours = Contours(self)
        self.vectors = VectorOverlay(self)
        self.wcs = ImageWCSOverlay(self)
        self.regions = RegionSet(self)

    @property
    def _stable_id(self):
        return self.file_id

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

        file_id = session.call_action(command, *params, return_path="frameInfo.fileId")
        return cls(session, file_id)

    @property
    def image_view_order(self):
        """The current index of this image in image list.

        Returns
        -------
        integer
            The image view order.

        Raises
        ------
        RuntimeError
            If no matching frame entry exists in the image list.
        """
        return self.session._find_image_view_order(ImageType.FRAME, self.file_id)

    def __repr__(self):
        """A human-readable representation of this image object."""
        cls = type(self).__name__
        cached_name = getattr(self, "_cache", {}).get("file_name")
        name_part = f", file_name={cached_name!r}" if cached_name is not None else ""

        try:
            order = self.image_view_order
        except (CartaScriptingException, RuntimeError):
            return f"[Closed] {cls}(image_view_order=None{name_part}, file_id={self.file_id})"

        try:
            name = self.file_name
        except CartaScriptingException:
            return f"[Closed] {cls}(image_view_order={order}{name_part}, file_id={self.file_id})"

        return f"{cls}(image_view_order={order}, file_name={name!r}, file_id={self.file_id})"

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

        World coordinates are interpreted according to the session's globally set coordinate system and any custom number formats. These can be changed using :obj:`carta.wcs_overlay.Global.set_coordinate_system` and :obj:`carta.wcs_overlay.Numbers.set_format`.

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

    # SPECTRAL CONVERSION

    @property
    @cached
    def is_pv(self):
        """Whether this is a spatial-spectral image.

        Returns
        -------
        boolean
            Whether this is a spatial-spectral image.
        """
        return self.get_value("isPVImage")

    @property
    @cached
    def spectral_systems_supported(self):
        """The spectral systems supported by this image.

        Returns
        -------
        set of :obj:`carta.constants.SpectralSystem`
            The supported spectral systems.
        """
        return {SpectralSystem(s) for s in self.get_value("spectralSystemsSupported")}

    @property
    @cached
    def spectral_coordinate_types_supported(self):
        """The spectral coordinate types supported by this image.

        Returns
        -------
        set of :obj:`carta.constants.SpectralType`
            The supported spectral coordinate types.
        """
        types = {v['type'] for v in self.get_value("spectralCoordsSupported").values()} - {"CHANNEL"}
        return {SpectralType(t) for t in types}

    @validate(Constant(SpectralSystem))
    def set_spectral_system(self, spectral_system):
        """Set the coordinate system used for the spectral axis in the image viewer.

        This is only applicable to spatial-spectral images, such as position-velocity images or cubes with permuted axes like ``RA-FREQ-DEC``.

        Parameters
        ----------
        spectral_system : {0}
            The spectral system to use.

        Raises
        ------
        ValueError
            If this is not a spatial-spectral image, or the system is not supported.
        """
        if not self.is_pv:
            raise ValueError("Cannot set spectral system. This is not a position-velocity image.")
        spectral_system = SpectralSystem(spectral_system)
        if spectral_system not in self.spectral_systems_supported:
            raise ValueError(f"Cannot set spectral system. Unsupported system: {spectral_system}.")
        self.call_action("setSpectralSystem", spectral_system)

    @validate(Constant(SpectralType), NoneOr(Constant(SpectralUnit)))
    def set_spectral_coordinate(self, spectral_type, spectral_unit=None):
        """Set the coordinate type and unit used for the spectral axis in the image viewer.

        This is only applicable to spatial-spectral images, such as position-velocity images or cubes with permuted axes like ``RA-FREQ-DEC``.

        Parameters
        ----------
        spectral_type : {0}
            The spectral type to use.
        spectral_unit : {1}
            The spectral unit to use. If this is omitted, the default unit for the type will be used.

        Raises
        ------
        ValueError
            If this is not a spatial-spectral image, or the type is not supported, or the unit is not supported.
        """
        if not self.is_pv:
            raise ValueError("Cannot set spectral coordinate. This is not a position-velocity image.")

        spectral_type = SpectralType(spectral_type)
        description = spectral_type.description
        if spectral_type not in self.spectral_coordinate_types_supported:
            raise ValueError(f"Cannot set spectral coordinate. Unsupported type: {description}.")

        if spectral_unit is not None:
            spectral_unit = SpectralUnit(spectral_unit)
            if spectral_unit not in spectral_type.units:
                raise ValueError(f"Cannot set spectral coordinate. Unsupported unit: {spectral_unit}.")
        else:
            spectral_unit = spectral_type.default_unit

        spectral_coordinate_string = description if spectral_unit is None else f"{description} ({spectral_unit})"
        self.call_action("setSpectralCoordinate", spectral_coordinate_string)

    # COORDINATE AND SIZE CONVERSIONS

    @validate(IterableOf(Point.WorldCoordinatePoint()))
    def from_world_coordinate_points(self, points):
        """Convert world coordinate points to image coordinate points.

        The points must have string values which can be parsed as world coordinates using the current globally set coordinate system (and any custom number formats).

        Parameters
        ----------
        points : {0}
            Points with string values which are valid world coordinates.

        Returns
        -------
        iterable of numeric points
            Points with numeric values which are image coordinates.
        """
        points = [Pt(*p) for p in points]
        converted_points = self.call_action("getImagePosFromWCS", points)
        return [Pt(**p).as_tuple() for p in converted_points]

    @validate(IterableOf(Point.NumericPoint()))
    def to_world_coordinate_points(self, points):
        """Convert image coordinate points to world coordinate points.

        The points must be numeric.

        Parameters
        ----------
        points : {0}
            Points with numeric values which are valid image coordinates.

        Returns
        -------
        iterable of string coordinate points
            Points with string values which are world coordinates.
        """
        points = [Pt(*p) for p in points]
        converted_points = self.call_action("getWCSFromImagePos", points)
        return [Pt(**p).as_tuple() for p in converted_points]

    @validate(Size.AngularSize(), Constant(SpatialAxis))
    def from_angular_size(self, size, axis):
        """Convert angular size to pixel size.

        Parameters
        ----------
        size : {0}
            The angular size.
        axis : {1}
            The axis.

        Returns
        -------
        float
            The pixel size.
        """
        arcsec = AngularSize.from_string(size).arcsec
        if axis == SpatialAxis.X:
            return self.call_action("getImageXValueFromArcsec", arcsec)
        if axis == SpatialAxis.Y:
            return self.call_action("getImageYValueFromArcsec", arcsec)

    @validate(IterableOf(Point.AngularSizePoint()))
    def from_angular_size_points(self, points):
        """Convert angular size points to pixel size points.

        The points must have string values which can be parsed as angular sizes.

        Parameters
        ----------
        points : {0}
            Points with string values which are valid angular sizes.

        Returns
        -------
        iterable of numeric points
            Points with numeric values which are pixel sizes.
        """
        converted_points = []
        for x, y in points:
            converted_points.append((self.from_angular_size(x, SpatialAxis.X), self.from_angular_size(y, SpatialAxis.Y)))
        return converted_points

    @validate(IterableOf(Point.NumericPoint()))
    def to_angular_size_points(self, points):
        """Convert pixel size points to angular size points.

        The points must be numeric.

        Parameters
        ----------
        points : {0}
            Points with numeric values which are valid image coordinates.

        Returns
        -------
        iterable of angular size points
            Points with string values which are angular sizes.
        """
        converted_points = []
        for p in points:
            converted = self.call_action("getWcsSizeInArcsec", Pt(*p))
            converted_points.append(Pt(**converted).as_tuple())
        return converted_points

    # CLOSE

    def close(self):
        """Close this image."""
        self.session.call_action("closeFile", self._frame, False)
