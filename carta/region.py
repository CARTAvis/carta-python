"""This module contains region classes which represent single regions or annotations loaded in the session, and a region set class which represents all regions and annotations associated with an image.

Region and annotation objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.region.RegionSet` object.
"""

import posixpath

from .util import Macro, BasePathMixin, Point as Pt, cached, CartaBadResponse, CartaValidationFailed
from .constants import FileType, RegionType, CoordinateType, PointShape, TextPosition, AnnotationFontStyle, AnnotationFont
from .validation import validate, Constant, IterableOf, Number, String, Point, NoneOr, Boolean, OneOf, InstanceOf, MapOf, Color, all_optional, Union


class RegionSet(BasePathMixin):
    """Utility object for collecting region-related image functions.

    Parameters
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this region set.

    Attributes
    ----------
    image : :obj:`carta.image.Image` object
        The image associated with this region set.
    session : :obj:`carta.session.Session` object
        The session object associated with this region set.
    """

    def __init__(self, image):
        self.image = image
        self.session = image.session
        self._base_path = f"{image._base_path}.regionSet"

    def list(self):
        """Return the list of regions associated with this image.

        Returns
        -------
        list of :obj:`carta.region.Region` objects.
        """
        region_list = self.get_value("regionList")
        return Region.from_list(self, region_list)

    @validate(Number())
    def get(self, region_id):
        """Return the region with the given region ID.

        Parameters
        ----------
        region_id : {0}
            The region ID.

        Returns
        -------
        :obj:`carta.region.Region` object
            The region with the given ID.

        Raises
        ------
        ValueError
            If there is no region with the given ID.
        """
        try:
            region_type = self.get_value(f"regionMap[{region_id}]", return_path="regionType")
        except CartaBadResponse:
            raise ValueError(f"Could not find region with ID {region_id}.")
        return Region.existing(region_type, self, region_id)

    @validate(String())
    def import_from(self, path):
        """Import regions into this image from a file.

        Parameters
        ----------
        path : {0}
            The path to the region file, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.

        Raises
        ------
        CartaActionFailed
            If the file does not exist or is not a region file.
        """
        directory, file_name = posixpath.split(path)
        directory = self.session.resolve_file_path(directory)

        file_type = FileType(self.session.call_action("backendService.getRegionFileInfo", directory, file_name, return_path="fileInfo.type"))

        self.session.call_action("importRegion", directory, file_name, file_type, self.image._frame)

    @validate(String(), Constant(CoordinateType), OneOf(FileType.CRTF, FileType.DS9_REG), NoneOr(IterableOf(Number())))
    def export_to(self, path, coordinate_type=CoordinateType.WORLD, file_type=FileType.CRTF, region_ids=None):
        """Export regions from this image into a file.

        Parameters
        ----------
        path : {0}
            The path where the file should be saved, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        coordinate_type : {1}
            The coordinate type to use (world coordinates by default).
        file_type : {2}
            The region file type to use (CRTF by default).
        region_ids : {3}
            The region IDs to include. By default all regions will be included (except the cursor).
        """
        directory, file_name = posixpath.split(path)
        directory = self.session.resolve_file_path(directory)

        if region_ids is None:
            region_ids = [r["id"] for r in self.get_value("regionList")[1:]]

        self.session.call_action("exportRegions", directory, file_name, coordinate_type, file_type, region_ids, self.image._frame)

    @validate(Constant(RegionType), IterableOf(Point.NumericPoint()), Number(), String())
    def add_region(self, region_type, points, rotation=0, name=""):
        """Add a new region or annotation to this image.

        This is a generic low-level function. Also see the higher-level functions for adding regions of specific types, such as :obj:`carta.region.RegionSet.add_point`.

        Parameters
        ----------
        region_type : {0}
            The type of the region.
        points : {1}
            The control points defining the region, in image coordinates. How these values are interpreted depends on the region type.
        rotation : {2}
            The rotation of the region, in degrees. Defaults to zero.
        name : {3}
            The name of the region. Defaults to the empty string.
        """
        return Region.new(self, region_type, points, rotation, name)

    def _from_world_coordinates(self, points):
        """Internal utility function for coercing world or image coordinates to image coordinates. This is used in various region functions to simplify accepting both world and image coordinates.

        The points provided must either all be world coordinates or all be image coordinates. This can be enforced with the appropriate validation on the calling method.

        If the points provided are world coordinates, the method on the image object is called successfully and returns the points transformed into image coordinates, which this method returns.

        If the points provided are image coordinates, the type validation on the image method fails. This exception is caught silently by this method, and the unmodified points are returned.

        See also :obj:`carta.region.RegionSet._from_angular_sizes`.

        Parameters
        ----------
        points : iterable of points which are all either world or image coordinates
            The input points.

        Returns
        -------
        iterable of points which are image coordinates
            The output points.
        """
        try:
            points = self.image.from_world_coordinate_points(points)
        except CartaValidationFailed:
            pass
        return points

    def _from_angular_sizes(self, points):
        """Internal utility function for coercing angular or pixel sizes to pixel sizes. This is used in various region functions to simplify accepting both angular and pixel sizes.

        The points provided must either all be angular sizes or all be pixel sizes. This can be enforced with the appropriate validation on the calling method.

        If the points provided are angular sizes, the method on the image object is called successfully and returns the points transformed into pixel sizes.

        If the points provided are in pixel sizes, the type validation on the image method fails. This exception is caught silently by this method, and the unmodified points are returned.

        See also :obj:`carta.region.RegionSet._from_world_coordinates`.

        Parameters
        ----------
        points : iterable of points which are all either angular or pixel sizes
            The input points.

        Returns
        -------
        iterable of points which are pixel sizes
            The output points.
        """
        try:
            points = self.image.from_angular_size_points(points)
        except CartaValidationFailed:
            pass
        return points

    @validate(Point.CoordinatePoint(), Boolean(), String())
    def add_point(self, center, annotation=False, name=""):
        """Add a new point region or point annotation to this image.

        Parameters
        ----------
        center : {0}
            The center position of the region.
        annotation : {1}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {2}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.Region` or :obj:`carta.region.PointAnnotation` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        region_type = RegionType.ANNPOINT if annotation else RegionType.POINT
        return self.add_region(region_type, [center], name=name)

    @validate(Point.CoordinatePoint(), Point.SizePoint(), Boolean(), Number(), String())
    def add_rectangle(self, center, size, annotation=False, rotation=0, name=""):
        """Add a new rectangular region or rectangular annotation to this image.

        Parameters
        ----------
        center : {0}
            The center position of the region.
        size : {1}
            The size of the region. The ``x`` and ``y`` values will be interpreted as the width and height, respectively.
        annotation : {2}
            Whether this region should be an annotation. Defaults to ``False``.
        rotation : {3}
            The rotation of the region, in degrees. Defaults to zero.
        name : {4}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.Region` or :obj:`carta.region.Annotation` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        [size] = self._from_angular_sizes([size])
        region_type = RegionType.ANNRECTANGLE if annotation else RegionType.RECTANGLE
        return self.add_region(region_type, [center, size], rotation, name)

    @validate(Point.CoordinatePoint(), Point.SizePoint(), Boolean(), Number(), String())
    def add_ellipse(self, center, size, annotation=False, rotation=0, name=""):
        """Add a new elliptical region or elliptical annotation to this image.

        Parameters
        ----------
        center : {0}
            The center position of the region.
        size : {1}
            The size of the region. The ``x`` and ``y`` values will be interpreted as the semi-major and semi-minor axes, respectively.
        annotation : {2}
            Whether this region should be an annotation. Defaults to ``False``.
        rotation : {3}
            The rotation of the region, in degrees. Defaults to zero.
        name : {4}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.Region` or :obj:`carta.region.Annotation` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        [size] = self._from_angular_sizes([size])
        region_type = RegionType.ANNELLIPSE if annotation else RegionType.ELLIPSE
        return self.add_region(region_type, [center, size], rotation, name)

    @validate(Union(IterableOf(Point.NumericPoint()), IterableOf(Point.WorldCoordinatePoint())), Boolean(), String())
    def add_polygon(self, points, annotation=False, name=""):
        """Add a new polygonal region or polygonal annotation to this image.

        Parameters
        ----------
        points : {0}
            The positions of the vertices of the region, either all in world coordinates or all in image coordinates.
        annotation : {1}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {2}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.PolygonRegion` or :obj:`carta.region.PolygonAnnotation` object
            A new region object.
        """
        points = self._from_world_coordinates(points)
        region_type = RegionType.ANNPOLYGON if annotation else RegionType.POLYGON
        return self.add_region(region_type, points, name=name)

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint(), Boolean(), String())
    def add_line(self, start, end, annotation=False, name=""):
        """Add a new line region or line annotation to this image.

        Parameters
        ----------
        start : {0}
            The start position of the region.
        end : {1}
            The end position of the region.
        annotation : {2}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {3}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.LineRegion` or :obj:`carta.region.LineAnnotation` object
            A new region object.
        """
        [start, end] = self._from_world_coordinates([start, end])
        region_type = RegionType.ANNLINE if annotation else RegionType.LINE
        return self.add_region(region_type, [start, end], name=name)

    @validate(Union(IterableOf(Point.NumericPoint()), IterableOf(Point.WorldCoordinatePoint())), Boolean(), String())
    def add_polyline(self, points, annotation=False, name=""):
        """Add a new polyline region or polyline annotation to this image.

        Parameters
        ----------
        points : {0}
            The positions of the vertices of the region, either all in world coordinates or all in image coordinates.
        annotation : {1}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {2}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.PolylineRegion` or :obj:`carta.region.PolylineAnnotation` object
            A new region object.
        """
        points = self._from_world_coordinates(points)
        region_type = RegionType.ANNPOLYLINE if annotation else RegionType.POLYLINE
        return self.add_region(region_type, points, name=name)

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint(), String())
    def add_vector(self, start, end, name=""):
        """Add a new vector annotation to this image.

        Parameters
        ----------
        start : {0}
            The start position of the region.
        end : {1}
            The end position of the region.
        name : {2}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.VectorAnnotation` object
            A new region object.
        """
        [start] = self._from_world_coordinates([start])  # Parsed separately in case they are mismatched
        [end] = self._from_world_coordinates([end])  # Parsed separately in case they are mismatched
        return self.add_region(RegionType.ANNVECTOR, [start, end], name=name)

    @validate(Point.CoordinatePoint(), Point.SizePoint(), String(), Number(), String())
    def add_text(self, center, size, text, rotation=0, name=""):
        """Add a new text annotation to this image.

        Parameters
        ----------
        center : {0}
            The center position of the region.
        size : {1}
            The size of the region. The ``x`` and ``y`` values will be interpreted as the width and height, respectively.
        text : {2}
            The text content to display.
        rotation : {3}
            The rotation of the region, in degrees. Defaults to zero.
        name : {4}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.TextAnnotation` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        [size] = self._from_angular_sizes([size])
        region = self.add_region(RegionType.ANNTEXT, [center, size], rotation, name)
        region.set_text(text)
        return region

    @validate(Point.CoordinatePoint(), Number(), String())
    def add_compass(self, center, length, name=""):
        """Add a new compass annotation to this image.

        Parameters
        ----------
        center : {0}
            The origin position of the compass.
        length : {1}
            The length of the compass points, in pixels.
        name : {2}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.CompassAnnotation` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        return self.add_region(RegionType.ANNCOMPASS, [center, (length, length)], name=name)

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint(), String())
    def add_ruler(self, start, end, name=""):
        """Add a new ruler annotation to this image.

        Parameters
        ----------
        start : {0}
            The start position of the region.
        end : {1}
            The end position of the region.
        name : {2}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.RulerAnnotation` object
            A new region object.
        """
        [start] = self._from_world_coordinates([start])  # Parsed separately in case they are mismatched
        [end] = self._from_world_coordinates([end])  # Parsed separately in case they are mismatched
        return self.add_region(RegionType.ANNRULER, [start, end], name=name)

    def clear(self):
        """Delete all regions except for the cursor region."""
        for region in self.list()[1:]:
            region.delete()


class Region(BasePathMixin):
    """Utility object which provides access to one region associated with an image.

    # TODO find out what happens to region IDs when you match/unmatch or delete.

    Parameters
    ----------
    region_set : :obj:`carta.region.RegionSet` object
        The region set containing this region.
    region_id : integer
        The ID of this region.

    Attributes
    ----------
    region_set : :obj:`carta.region.RegionSet` object
        The region set containing this region.
    region_id : integer
        The ID of this region.
    session : :obj:`carta.session.Session` object
        The session object associated with this region.
    """

    REGION_TYPE = None
    CUSTOM_CLASS = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.REGION_TYPE is not None:
            Region.CUSTOM_CLASS[cls.REGION_TYPE] = cls

    def __init__(self, region_set, region_id):
        self.region_set = region_set
        self.session = region_set.session
        self.region_id = region_id

        self._base_path = f"{region_set._base_path}.regionMap[{region_id}]"
        self._region = Macro("", self._base_path)

    def __repr__(self):
        return f"{self.region_id}:{self.region_type.label}"

    # CREATE OR CONNECT

    @classmethod
    @validate(Constant(RegionType))
    def region_class(cls, region_type):
        """The region class associated for this type.

        Not every type maps to a specific class; some types have no specific functionality and use the default :obj:`carta.region.Region` or :obj:`carta.region.Annotation` classes.

        Parameters
        ----------
        region_type : {0}
            The region type.

        Returns
        -------
        class object
            The region class.
        """
        region_type = RegionType(region_type)
        return cls.CUSTOM_CLASS.get(region_type, Annotation if region_type.is_annotation else Region)

    @classmethod
    @validate(Constant(RegionType), InstanceOf(RegionSet), Number())
    def existing(cls, region_type, region_set, region_id):
        """Create a region object corresponding to an existing region.

        This is an internal helper method which should not be used directly.

        Parameters
        ----------
        region_type : {0}
            The region type.
        region_set : {1}
            The region set containing this region.
        region_id : {2}
            The ID of the region.

        Returns
        -------
        :obj:`carta.region.Region` object
            The region object.
        """
        return cls.region_class(region_type)(region_set, region_id)

    @classmethod
    @validate(InstanceOf(RegionSet), Constant(RegionType), IterableOf(Point.NumericPoint()), Number(), String())
    def new(cls, region_set, region_type, points, rotation=0, name=""):
        """Create a new region.

        This is an internal helper method which should not be used directly.

        Parameters
        ----------
        region_set : {0}
            The region set in which to create this region.
        region_type : {1}
            The region type.
        points : {2}
            The control points of the region, in pixels. These may be coordinates or sizes; how they are interpreted depends on the region type.
        rotation : {3}
            The rotation of the region, in degrees. Defaults to zero.
        name : {4}
            The name of the region. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.Region` object
            The region object.
        """
        points = [Pt(*point) for point in points]
        region_id = region_set.call_action("addRegionAsync", region_type, points, rotation, name, return_path="regionId")
        return cls.existing(region_type, region_set, region_id)

    @classmethod
    @validate(InstanceOf(RegionSet), IterableOf(MapOf(String(), Number(), required_keys={"type", "id"})))
    def from_list(cls, region_set, region_list):
        """Create region objects corresponding to a list of existing regions in a single region set.

        This is an internal helper method which should not be used directly.

        Parameters
        ----------
        region_set : {0}
            The region set which contains these regions.
        region_list : {1}
            A list of dictionaries containing region types and IDs.

        Returns
        -------
        iterable of :obj:`carta.region.Region` objects
            The region objects.
        """
        return [cls.existing(r["type"], region_set, r["id"]) for r in region_list]

    # GET PROPERTIES

    @property
    @cached
    def region_type(self):
        """The type of the region.

        Returns
        -------
        :obj:`carta.constants.RegionType` object
            The type.
        """
        return RegionType(self.get_value("regionType"))

    @property
    def center(self):
        """The center position of the region, in image coordinates.

        Returns
        -------
        tuple of two numbers
            The center position.
        """
        return Pt(**self.get_value("center")).as_tuple()

    @property
    def wcs_center(self):
        """The center position of the region, in world coordinates.

        Returns
        -------
        tuple of two strings
            The center position.
        """
        [center] = self.region_set.image.to_world_coordinate_points([self.center])
        return center

    @property
    def size(self):
        """The size of the region, in pixels.

        Returns
        -------
        tuple of two numbers
            The size. The first value is the width, and the second value is the height.
        """
        return Pt(**self.get_value("size")).as_tuple()

    @property
    def wcs_size(self):
        """The size of the region, in angular size units.

        Returns
        -------
        tuple of two strings
            The size. The first value is the width, and the second value is the height.
        """
        size = self.get_value("wcsSize")
        return (f"{size['x']}\"", f"{size['y']}\"")

    @property
    def rotation(self):
        """The rotation of the region, in degrees.

        Returns
        -------
        number
            The rotation.
        """
        return self.get_value("rotation")

    @property
    def control_points(self):
        """The control points of the region, in pixels.

        Returns
        -------
        iterable of tuples of two numbers
            The control points.
        """
        return [Pt(**p).as_tuple() for p in self.get_value("controlPoints")]

    @property
    def name(self):
        """The name of the region.

        Returns
        -------
        string
            The name.
        """
        return self.get_value("name")

    @property
    def color(self):
        """The color of the region.

        Returns
        -------
        string
            The color.
        """
        return self.get_value("color")

    @property
    def line_width(self):
        """The line width of the region, in pixels.

        Returns
        -------
        number
            The line width.
        """
        return self.get_value("lineWidth")

    @property
    def dash_length(self):
        """The dash length of the region, in pixels.

        Returns
        -------
        number
            The dash length.
        """
        return self.get_value("dashLength")

    # SET PROPERTIES

    @validate(Point.CoordinatePoint())
    def set_center(self, center):
        """Set the center position of this region.

        Both image and world coordinates are accepted, but both values must match.

        Parameters
        ----------
        center : {0}
            The new center position.
        """
        [center] = self.region_set._from_world_coordinates([center])
        self.call_action("setCenter", Pt(*center))

    @validate(Point.SizePoint())
    def set_size(self, size):
        """Set the size of this region.

        TODO list region types for which this does not work.

        Both pixel and angular sizes are accepted, but both values must match.

        Parameters
        ----------
        size : {0}
            The new size.
        """
        [size] = self.region_set._from_angular_sizes([size])
        self.call_action("setSize", Pt(*size))

    @validate(Number(), Point.NumericPoint())
    def set_control_point(self, index, point):
        """Update the value of a single control point of this region.

        Parameters
        ----------
        index : {0}
            The index of the control point to update.
        point : {1}
            The new value for the control point, in pixels.
        """
        self.call_action("setControlPoint", index, Pt(*point))

    @validate(IterableOf(Point.NumericPoint()))
    def set_control_points(self, points):
        """Update all the control points of this region.

        Parameters
        ----------
        points : {0}
            The new control points, in pixels.
        """
        self.call_action("setControlPoints", [Pt(*p) for p in points])

    @validate(Number())
    def set_rotation(self, angle):
        """Set the rotation of this region.

        Parameters
        ----------
        angle : {0}
            The new rotation angle, in degrees.
        """
        self.call_action("setRotation", angle)

    @validate(String())
    def set_name(self, name):
        """Set the name of this region.

        Parameters
        ----------
        name : {0}
            The new name.
        """
        self.call_action("setName", name)

    @validate(*all_optional(Color(), Number(), Number()))
    def set_line_style(self, color=None, line_width=None, dash_length=None):
        """Set the line style of this region.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        color : {0}
            The new color.
        line_width : {1}
            The new line width, in pixels.
        dash_length : {2}
            The new dash length, in pixels.
        """
        if color is not None:
            self.call_action("setColor", color)
        if line_width is not None:
            self.call_action("setLineWidth", line_width)
        if dash_length is not None:
            self.call_action("setDashLength", dash_length)

    def lock(self):
        """Lock this region."""
        self.call_action("setLocked", True)

    def unlock(self):
        """Unlock this region."""
        self.call_action("setLocked", False)

    def focus(self):
        """Center the image view on this region."""
        self.call_action("focusCenter")

    # IMPORT AND EXPORT

    @validate(String(), Constant(CoordinateType), OneOf(FileType.CRTF, FileType.DS9_REG))
    def export_to(self, path, coordinate_type=CoordinateType.WORLD, file_type=FileType.CRTF):
        """Export this region into a file.

        Parameters
        ----------
        path : {0}
            The path where the file should be saved, either relative to the session's current directory or an absolute path relative to the CARTA backend's root directory.
        coordinate_type : {1}
            The coordinate type to use (world coordinates by default).
        file_type : {2}
            The region file type to use (CRTF by default).
        """
        self.region_set.export_to(path, coordinate_type, file_type, [self.region_id])

    def delete(self):
        """Delete this region."""
        self.region_set.call_action("deleteRegion", self._region)


class HasVerticesMixin:
    """This is a mixin class for regions which are defined by an arbitrary number of vertices. It assumes that all control points of the region should be interpreted as coordinates."""

    # GET PROPERTIES

    @property
    def vertices(self):
        """The vertices of the region, in image coordinates.

        This is an alias of :obj:`carta.region.Region.control_points`.

        Returns
        -------
        iterable of tuples of two numbers
            The vertices.
        """
        return self.control_points

    @property
    def wcs_vertices(self):
        """The vertices of the region, in world coordinates.

        Returns
        -------
        iterable of tuples of two strings
            The vertices.
        """
        return self.region_set.image.to_world_coordinate_points[self.control_points]

    # SET PROPERTIES

    @validate(Number(), Point.CoordinatePoint())
    def set_vertex(self, index, point):
        """Update the value of a single vertex of this region.

        Parameters
        ----------
        index : {0}
            The index of the vertex to update.
        point : {1}
            The new value for the vertex, in image or world coordinates.
        """
        [point] = self.region_set._from_world_coordinates([point])
        self.set_control_point(index, point)

    @validate(Union(IterableOf(Point.NumericPoint()), IterableOf(Point.WorldCoordinatePoint())))
    def set_vertices(self, points):
        """Update all the vertices of this region.

        Both image and world coordinates are accepted, but all values must match.

        Parameters
        ----------
        points : {0}
            The new vertices, in image or world coordinates.
        """
        points = self.region_set._from_world_coordinates(points)
        self.set_control_points(points)


class HasEndpointsMixin:
    """This is a mixin class for regions which are defined by two endpoints. It assumes that the region has two control points and both should be interpreted as coordinates."""

    # GET PROPERTIES

    @property
    def endpoints(self):
        """The endpoints of the region, in image coordinates.

        This is an alias of :obj:`carta.region.Region.control_points`.

        Returns
        -------
        iterable of tuples of two numbers
            The endpoints.
        """
        return self.control_points

    @property
    def wcs_endpoints(self):
        """The endpoints of the region, in world coordinates.

        Returns
        -------
        iterable of tuples of two strings
            The endpoints.
        """
        return self.region_set.image.to_world_coordinate_points[self.control_points]

    # SET PROPERTIES

    @validate(*all_optional(Point.CoordinatePoint(), Point.CoordinatePoint()))
    def set_endpoints(self, start=None, end=None):
        """Update the endpoints of this region.

        Both parameters are optional. If an endpoint is omitted, it will not be modified.

        Both image and world coordinates are accepted, but both values in each point must match.

        Parameters
        ----------
        start : {0}
            The new start position, in image or world coordinates.
        end : {1}
            The new end position, in image or world coordinates.
        """
        if start is not None:
            [start] = self.region_set._from_world_coordinates([start])
            self.set_control_point(0, start)
        if end is not None:
            [end] = self.region_set._from_world_coordinates([end])
            self.set_control_point(1, end)


class HasFontMixin:
    """This is a mixin class for annotations which have font properties."""

    # GET PROPERTIES

    @property
    def font_size(self):
        """The font size of this annotation, in pixels.

        Returns
        -------
        number
            The font size.
        """
        return self.get_value("fontSize")

    @property
    def font_style(self):
        """The font style of this annotation.

        Returns
        -------
        :obj:`carta.constants.AnnotationFontStyle`
            The font style.
        """
        return AnnotationFontStyle(self.get_value("fontStyle"))

    @property
    def font(self):
        """The font of this annotation.

        Returns
        -------
        :obj:`carta.constants.AnnotationFont`
            The font.
        """
        return AnnotationFont(self.get_value("font"))

    # SET PROPERTIES

    @validate(*all_optional(Constant(AnnotationFont), Number(), Constant(AnnotationFontStyle)))
    def set_font(self, font=None, font_size=None, font_style=None):
        """Set the font properties of this annotation.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        font : {0}
            The font face.
        font_size : {1}
            The font size, in pixels.
        font_style : {2}
            The font style.
        """
        if font:
            self.call_action("setFont", font)
        if font_size is not None:
            self.call_action("setFontSize", font_size)
        if font_style:
            self.call_action("setFontStyle", font_style)


class HasPointerMixin:
    """This is a mixin class for annotations which have a pointer style."""

    # GET PROPERTIES

    @property
    def pointer_width(self):
        """The pointer width of this annotation, in pixels.

        Returns
        -------
        number
            The pointer width.
        """
        return self.get_value("pointerWidth")

    @property
    def pointer_length(self):
        """The pointer length of this annotation, in pixels.

        Returns
        -------
        number
            The pointer length.
        """
        return self.get_value("pointerLength")

    # SET PROPERTIES

    @validate(*all_optional(Number(), Number()))
    def set_pointer_style(self, pointer_width=None, pointer_length=None):
        """Set the pointer style of this annotation.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        pointer_width : {0}
            The pointer width, in pixels.
        pointer_length : {1}
            The pointer length, in pixels.
        """

        if pointer_width is not None:
            self.call_action("setPointerWidth", pointer_width)
        if pointer_length is not None:
            self.call_action("setPointerLength", pointer_length)


class Annotation(Region):
    """Base class for annotations."""
    pass


class LineRegion(Region, HasEndpointsMixin):
    """A line region."""
    REGION_TYPE = RegionType.LINE


class PolylineRegion(Region, HasVerticesMixin):
    """A polyline region."""
    REGION_TYPE = RegionType.POLYLINE


class PolygonRegion(Region, HasVerticesMixin):
    """A polygonal region."""
    REGION_TYPE = RegionType.POLYGON


class LineAnnotation(Annotation, HasEndpointsMixin):
    """A line annotation."""
    REGION_TYPE = RegionType.ANNLINE


class PolylineAnnotation(Annotation, HasVerticesMixin):
    """A polyline annotation."""
    REGION_TYPE = RegionType.ANNPOLYLINE


class PolygonAnnotation(Annotation, HasVerticesMixin):
    """A polygonal annotation."""
    REGION_TYPE = RegionType.ANNPOLYGON


class PointAnnotation(Annotation):
    """A point annotation."""
    REGION_TYPE = RegionType.ANNPOINT

    # GET PROPERTIES

    @property
    def point_shape(self):
        return PointShape(self.get_value("pointShape"))

    @property
    def point_width(self):
        return self.get_value("pointWidth")

    # SET PROPERTIES

    @validate(Constant(PointShape))
    def set_point_shape(self, shape):
        self.call_action("setPointShape", shape)

    @validate(Number())
    def set_point_width(self, width):
        self.call_action("setPointWidth", width)


class TextAnnotation(Annotation, HasFontMixin):
    """A text annotation."""
    REGION_TYPE = RegionType.ANNTEXT

    # GET PROPERTIES

    @property
    def text(self):
        return self.get_value("text")

    @property
    def position(self):
        return TextPosition(self.get_value("position"))

    # SET PROPERTIES

    @validate(String())
    def set_text(self, text):
        self.call_action("setText", text)

    @validate(Constant(TextPosition))
    def set_position(self, position):
        self.call_action("setPosition", position)


class VectorAnnotation(Annotation, HasPointerMixin, HasEndpointsMixin):
    """A vector annotation."""
    REGION_TYPE = RegionType.ANNVECTOR


class CompassAnnotation(Annotation, HasFontMixin, HasPointerMixin):
    """A compass annotation."""
    REGION_TYPE = RegionType.ANNCOMPASS

    # GET PROPERTIES

    @property
    def labels(self):
        return self.get_value("northLabel"), self.get_value("eastLabel")

    @property
    def length(self):
        return self.get_value("length")

    @property
    def text_offsets(self):
        return Pt(**self.get_value("northTextOffset")), Pt(**self.get_value("eastTextOffset"))

    @property
    def arrowheads_visible(self):
        return self.get_value("northArrowhead"), self.get_value("eastArrowhead")

    # SET PROPERTIES

    @validate(*all_optional(String(), String()))
    def set_label(self, north_label=None, east_label=None):
        if north_label is not None:
            self.call_action("setLabel", north_label, True)
        if east_label is not None:
            self.call_action("setLabel", east_label, False)

    @validate(Number())
    def set_length(self, length):
        self.call_action("setLength", length)

    @validate(*all_optional(Point.NumericPoint(), Point.NumericPoint()))
    def set_text_offset(self, north_offset=None, east_offset=None):
        if north_offset is not None:
            self.call_action("setNorthTextOffset", north_offset.x, True)
            self.call_action("setNorthTextOffset", north_offset.y, False)
        if east_offset is not None:
            self.call_action("setEastTextOffset", east_offset.x, True)
            self.call_action("setEastTextOffset", east_offset.y, False)

    @validate(*all_optional(Boolean(), Boolean()))
    def set_arrowhead_visible(self, north=None, east=None):
        if north is not None:
            self.call_action("setNorthArrowhead", north)
        if east is not None:
            self.call_action("setEastArrowhead", east)


class RulerAnnotation(Annotation, HasFontMixin, HasEndpointsMixin):
    """A ruler annotation."""
    REGION_TYPE = RegionType.ANNRULER

    # GET PROPERTIES

    @property
    def auxiliary_lines_visible(self):
        return self.get_value("auxiliaryLineVisible")

    @property
    def auxiliary_lines_dash_length(self):
        return self.get_value("auxiliaryLineDashLength")

    @property
    def text_offset(self):
        return Pt(*self.get_value("textOffset"))

    # SET PROPERTIES

    @validate(Boolean())
    def set_auxiliary_lines_visible(self, visible):
        self.call_action("setAuxiliaryLineVisible", visible)

    @validate(Number())
    def set_auxiliary_lines_dash_length(self, length):
        self.call_action("setAuxiliaryLineDashLength", length)

    @validate(Number(), Number())
    def set_text_offset(self, x, y):  # TODO pixel only!
        self.call_action("setTextOffset", x, True)
        self.call_action("setTextOffset", y, False)
