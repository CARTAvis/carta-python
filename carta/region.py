"""This module contains region classes which represent single regions or annotations loaded in the session, and a region set class which represents all regions and annotations associated with an image.

Region and annotation objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.region.RegionSet` object.
"""

import posixpath
import math

from .util import Macro, BasePathMixin, Point as Pt, cached, CartaBadResponse, CartaValidationFailed
from .constants import FileType, RegionType, CoordinateType, PointShape, TextPosition, AnnotationFontStyle, AnnotationFont, SpatialAxis
from .validation import validate, Constant, IterableOf, Number, String, Point, NoneOr, Boolean, OneOf, InstanceOf, MapOf, Color, all_optional, Union, Size
from .units import AngularSize


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

    @validate(NoneOr(Boolean()))
    def list(self, ignore_cursor=True):
        """Return the list of regions associated with this image.

        Parameters
        ----------
        ignore_cursor : {0}
            Ignore the cursor region. This is set by default.

        Returns
        -------
        list of :obj:`carta.region.Region` objects.
        """
        region_list = self.get_value("regionList")
        if ignore_cursor:
            region_list = region_list[1:]
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
            The center position.
        annotation : {1}
            Whether the region should be an annotation. Defaults to ``False``.
        name : {2}
            The name. Defaults to the empty string.

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
            The center position.
        size : {1}
            The size. The two values will be interpreted as the width and height, respectively.
        annotation : {2}
            Whether this region should be an annotation. Defaults to ``False``.
        rotation : {3}
            The rotation, in degrees. Defaults to zero.
        name : {4}
            The name. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.Region` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        [size] = self._from_angular_sizes([size])
        region_type = RegionType.ANNRECTANGLE if annotation else RegionType.RECTANGLE
        return self.add_region(region_type, [center, size], rotation, name)

    @validate(Point.CoordinatePoint(), Point.SizePoint(), Boolean(), Number(), String())
    def add_ellipse(self, center, semi_axes, annotation=False, rotation=0, name=""):
        """Add a new elliptical region or elliptical annotation to this image.

        Parameters
        ----------
        center : {0}
            The center position.
        semi_axes : {1}
            The semi-axes. The two values will be interpreted as the north-south and east-west axes, respectively.
        annotation : {2}
            Whether this region should be an annotation. Defaults to ``False``.
        rotation : {3}
            The rotation, in degrees. Defaults to zero.
        name : {4}
            The name. Defaults to the empty string.

        Returns
        -------
        :obj:`carta.region.Region` object
            A new region object.
        """
        [center] = self._from_world_coordinates([center])
        [semi_axes] = self._from_angular_sizes([semi_axes])

        region_type = RegionType.ANNELLIPSE if annotation else RegionType.ELLIPSE
        return self.add_region(region_type, [center, semi_axes], rotation, name)

    @validate(Union(IterableOf(Point.NumericPoint()), IterableOf(Point.WorldCoordinatePoint())), Boolean(), String())
    def add_polygon(self, points, annotation=False, name=""):
        """Add a new polygonal region or polygonal annotation to this image.

        Parameters
        ----------
        points : {0}
            The positions of the vertices, either all in world coordinates or all in image coordinates.
        annotation : {1}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {2}
            The name. Defaults to the empty string.

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
            The start position.
        end : {1}
            The end position.
        annotation : {2}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {3}
            The name. Defaults to the empty string.

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
            The positions of the vertices, either all in world coordinates or all in image coordinates.
        annotation : {1}
            Whether this region should be an annotation. Defaults to ``False``.
        name : {2}
            The name. Defaults to the empty string.

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
            The start position.
        end : {1}
            The end position.
        name : {2}
            The name. Defaults to the empty string.

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
            The center position.
        size : {1}
            The size. The two values will be interpreted as the width and height, respectively.
        text : {2}
            The text content to display.
        rotation : {3}
            The rotation, in degrees. Defaults to zero.
        name : {4}
            The name. Defaults to the empty string.

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
            The name. Defaults to the empty string.

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
            The start position.
        end : {1}
            The end position.
        name : {2}
            The name. Defaults to the empty string.

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
        for region in self.list():
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
        elif cls.REGION_TYPES is not None:
            for t in cls.REGION_TYPES:
                Region.CUSTOM_CLASS[t] = cls

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

        Not every type maps to a specific class; some types have no specific functionality and use the default :obj:`carta.region.Region` class.

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
        return cls.CUSTOM_CLASS.get(region_type, Region)

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
            The region set containing the region.
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
            The control points, in pixels. These may be coordinates or sizes; how they are interpreted depends on the region type.
        rotation : {3}
            The rotation, in degrees. Defaults to zero.
        name : {4}
            The name. Defaults to the empty string.

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
        """The region type.

        Returns
        -------
        :obj:`carta.constants.RegionType` object
            The type.
        """
        return RegionType(self.get_value("regionType"))

    @property
    def center(self):
        """The center position, in image coordinates.

        Returns
        -------
        number
            The X coordinate of the center position.
        number
            The Y coordinate of the center position.
        """
        return Pt(**self.get_value("center")).as_tuple()

    @property
    def wcs_center(self):
        """The center position, in world coordinates.

        Returns
        -------
        string
            The X coordinate of the center position.
        string
            The Y coordinate of the center position.
        """
        [center] = self.region_set.image.to_world_coordinate_points([self.center])
        return center

    @property
    def size(self):
        """The size, in pixels.

        Returns
        -------
        number
            The width.
        number
            The height.
        """
        size = self.get_value("size")
        if not size:
            return None
        return Pt(**size).as_tuple()

    @property
    def wcs_size(self):
        """The size, in angular size units.

        Returns
        -------
        string
            The width.
        string
            The height.
        """
        size = self.get_value("wcsSize")
        if size['x'] is None or size['y'] is None:
            return None
        return (f"{size['x']}\"", f"{size['y']}\"")

    @property
    def control_points(self):
        """The control points.

        Returns
        -------
        iterable of tuples of two numbers
            The control points, in pixels.
        """
        return [Pt(**p).as_tuple() for p in self.get_value("controlPoints")]

    @property
    def name(self):
        """The name.

        Returns
        -------
        string
            The name.
        """
        return self.get_value("name")

    @property
    def color(self):
        """The color.

        Returns
        -------
        string
            The color.
        """
        return self.get_value("color")

    @property
    def line_width(self):
        """The line width.

        Returns
        -------
        number
            The line width, in pixels.
        """
        return self.get_value("lineWidth")

    @property
    def dash_length(self):
        """The dash length.

        Returns
        -------
        number
            The dash length, in pixels.
        """
        return self.get_value("dashLength")

    # SET PROPERTIES

    @validate(Point.CoordinatePoint())
    def set_center(self, center):
        """Set the center position.

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
        """Set the size.

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
        """Update the value of a single control point.

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
        """Update all the control points.

        Parameters
        ----------
        points : {0}
            The new control points, in pixels.
        """
        self.call_action("setControlPoints", [Pt(*p) for p in points])

    @validate(String())
    def set_name(self, name):
        """Set the name.

        Parameters
        ----------
        name : {0}
            The new name.
        """
        self.call_action("setName", name)

    @validate(*all_optional(Color(), Number(), Number()))
    def set_line_style(self, color=None, line_width=None, dash_length=None):
        """Set the line style.

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

# TODO also factor out size, and exclude it from the point region?


class HasRotationMixin:
    """This is a mixin class for regions which can be rotated natively."""

    # GET PROPERTIES

    @property
    def rotation(self):
        """The rotation, in degrees.

        Returns
        -------
        number
            The rotation.
        """
        return self.get_value("rotation")

    # SET PROPERTIES

    @validate(Number())
    def set_rotation(self, angle):
        """Set the rotation.

        Parameters
        ----------
        angle : {0}
            The new rotation, in degrees.
        """
        self.call_action("setRotation", angle)


class HasVerticesMixin:
    """This is a mixin class for regions which are defined by an arbitrary number of vertices. It assumes that all control points of the region should be interpreted as coordinates."""

    # GET PROPERTIES

    @property
    def vertices(self):
        """The vertices, in image coordinates.

        This is an alias of :obj:`carta.region.Region.control_points`.

        Returns
        -------
        iterable of tuples of two numbers
            The vertices.
        """
        return self.control_points

    @property
    def wcs_vertices(self):
        """The vertices, in world coordinates.

        Returns
        -------
        iterable of tuples of two strings
            The vertices.
        """
        return self.region_set.image.to_world_coordinate_points(self.control_points)

    # SET PROPERTIES

    @validate(Number(), Point.CoordinatePoint())
    def set_vertex(self, index, point):
        """Update the value of a single vertex.

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
        """Update all the vertices.

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
        """The endpoints, in image coordinates.

        This is an alias of :obj:`carta.region.Region.control_points`.

        Returns
        -------
        iterable containing two tuples of two numbers
            The endpoints.
        """
        return self.control_points

    @property
    def wcs_endpoints(self):
        """The endpoints, in world coordinates.

        Returns
        -------
        iterable containing two tuples of two strings
            The endpoints.
        """
        return self.region_set.image.to_world_coordinate_points(self.control_points)

    @property
    def length(self):
        """The Euclidean distance between the endpoints, in pixels.

        Returns
        -------
        float
            The length.
        """
        return math.hypot(*self.size)

    @property
    def wcs_length(self):
        """The Euclidean distance between the endpoints, in angular size units.

        Returns
        -------
        float
            The length.
        """
        arcsec_size = [AngularSize.from_string(s).arcsec for s in self.wcs_size]
        return str(AngularSize.from_arcsec(math.hypot(*arcsec_size)))

    # SET PROPERTIES

    @validate(Point.SizePoint())
    def set_size(self, size):
        """Set the size.

        Both pixel and angular sizes are accepted, but both values must match.

        Parameters
        ----------
        size : {0}
            The new width and height, in that order.
        """
        [size] = self.region_set._from_angular_sizes([size])
        sx, sy = size
        super().set_size((-sx, -sy))  # negated for consistency with returned size

    @validate(*all_optional(Point.CoordinatePoint(), Point.CoordinatePoint()))
    def set_endpoints(self, start=None, end=None):
        """Update the endpoints.

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

    @validate(Size())
    def set_length(self, length):
        """Update the length.

        Parameters
        ----------
        length : {0}
            The new length, in pixels or angular size units.
        """
        if isinstance(length, str):
            length = self.length * AngularSize.from_string(length).arcsec / AngularSize.from_string(self.wcs_length).arcsec

        rad = math.radians(self.rotation)

        super().set_size((length * math.sin(rad), -1 * length * math.cos(rad)))


class HasFontMixin:
    """This is a mixin class for annotations which have font properties."""

    # GET PROPERTIES

    @property
    def font_size(self):
        """The font size.

        Returns
        -------
        number
            The font size, in pixels.
        """
        return self.get_value("fontSize")

    @property
    def font_style(self):
        """The font style.

        Returns
        -------
        :obj:`carta.constants.AnnotationFontStyle`
            The font style.
        """
        return AnnotationFontStyle(self.get_value("fontStyle"))

    @property
    def font(self):
        """The font.

        Returns
        -------
        :obj:`carta.constants.AnnotationFont`
            The font.
        """
        return AnnotationFont(self.get_value("font"))

    # SET PROPERTIES

    @validate(*all_optional(Constant(AnnotationFont), Number(), Constant(AnnotationFontStyle)))
    def set_font(self, font=None, font_size=None, font_style=None):
        """Set the font properties.

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
        """The pointer width.

        Returns
        -------
        number
            The pointer width, in pixels.
        """
        return self.get_value("pointerWidth")

    @property
    def pointer_length(self):
        """The pointer length.

        Returns
        -------
        number
            The pointer length, in pixels.
        """
        return self.get_value("pointerLength")

    # SET PROPERTIES

    @validate(*all_optional(Number(), Number()))
    def set_pointer_style(self, pointer_width=None, pointer_length=None):
        """Set the pointer style.

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


class LineRegion(HasEndpointsMixin, HasRotationMixin, Region):
    """A line region or annotation."""
    REGION_TYPES = (RegionType.LINE, RegionType.ANNLINE)


class PolylineRegion(HasVerticesMixin, Region):
    """A polyline region or annotation."""
    REGION_TYPES = (RegionType.POLYLINE, RegionType.ANNPOLYLINE)


class PolygonRegion(HasVerticesMixin, Region):
    """A polygonal region or annotation."""
    REGION_TYPES = (RegionType.POLYGON, RegionType.ANNPOLYGON)


class RectangularRegion(HasRotationMixin, Region):
    """A rectangular region or annotation."""
    REGION_TYPES = (RegionType.RECTANGLE, RegionType.ANNRECTANGLE)

    # GET PROPERTIES

    @property
    def corners(self):
        """The corner positions, in image coordinates.

        Returns
        -------
        iterable containing two tuples of two numbers
            The bottom-left and top-right corner positions, in image coordinates.
        """
        center = Pt(*self.center)
        size = Pt(*self.size)
        dx, dy = size.x / 2, size.y / 2
        return ((center.x - dx, center.y - dy), (center.x + dx, center.y + dy))

    @property
    def wcs_corners(self):
        """The corner positions, in world coordinates.

        Returns
        -------
        iterable containing two tuples of two strings
            The bottom-left and top-right corner positions, in world coordinates.
        """
        return self.region_set.image.to_world_coordinate_points(self.corners)

    # SET PROPERTIES

    @validate(*all_optional(Point.CoordinatePoint(), Point.CoordinatePoint()))
    def set_corners(self, bottom_left=None, top_right=None):
        """Update the corner positions.

        Both parameters are optional. If a position is omitted, it will not be modified.

        The corner positions will be used to calculate the updated center position and size.

        Both image and world coordinates are accepted, but both values in each point must match.

        Parameters
        ----------
        bottom_left : {0}
            The new bottom-left corner position, in image or world coordinates.
        top_right : {1}
            The new top-right corner position, in image or world coordinates.
        """
        if bottom_left is None and top_right is None:
            return

        if bottom_left is None or top_right is None:
            current_bottom_left, current_top_right = self.corners

        if bottom_left is not None:
            [bottom_left] = self.region_set._from_world_coordinates([bottom_left])
        else:
            bottom_left = current_bottom_left

        if top_right is not None:
            [top_right] = self.region_set._from_world_coordinates([top_right])
        else:
            top_right = current_top_right

        bl = Pt(*bottom_left)
        tr = Pt(*top_right)

        size = Pt(tr.x - bl.x, tr.y - bl.y)
        center = (bl.x + (size.x / 2), bl.y + (size.y / 2))

        self.set_control_points([center, size.as_tuple()])


class EllipticalRegion(HasRotationMixin, Region):
    """An elliptical region or annotation."""
    REGION_TYPES = (RegionType.ELLIPSE, RegionType.ANNELLIPSE)

    # GET PROPERTIES

    @property
    def semi_axes(self):
        """The semi-axes, in pixels.

        The north-south semi-axis is equal to half of the height, and the east-west semi-axis is equal to half of the width.

        Returns
        -------
        number
            The north-south semi-axis, in pixels.
        number
            The east-west semi-axis, in pixels.
        """
        return super().size

    @property
    def wcs_semi_axes(self):
        """The semi-axes, in angular size units.

        The north-south semi-axis is equal to half of the height, and the east-west semi-axis is equal to half of the width.

        Returns
        -------
        string
            The north-south semi-axis, in angular size units.
        string
            The east-west semi-axis, in angular size units.
        """
        return super().wcs_size

    @property
    def size(self):
        """The size, in pixels.

        The width is equal to twice the east-west semi-axis, and the height is equal to twice the north-south semi-axis.

        Returns
        -------
        number
            The width.
        number
            The height.
        """
        semi_ns, semi_ew = self.semi_axes
        return (semi_ew * 2, semi_ns * 2)

    @property
    def wcs_size(self):
        """The size, in angular size units.

        The width is equal to twice the east-west semi-axis, and the height is equal to twice the north-south semi-axis.

        Returns
        -------
        string
            The width.
        string
            The height.
        """
        [size] = self.region_set.image.to_angular_size_points([self.size])
        return size

    # SET PROPERTIES

    @validate(Point.SizePoint())
    def set_semi_axes(self, semi_axes):
        """Set the semi-axes.

        Both pixel and angular sizes are accepted, but both values must match.

        Parameters
        ----------
        size : {0}
            The new north-south and east-west semi-axes, in that order.
        """
        [semi_axes] = self.region_set._from_angular_sizes([semi_axes])
        super().set_size(semi_axes)

    @validate(Point.SizePoint())
    def set_size(self, size):
        """Set the size.

        The width and height will be used to calculate the semi-axes: the north-south semi-axis is equal to half of the height, and the east-west semi-axis is equal to half of the width.

        Both pixel and angular sizes are accepted, but both values must match.

        Parameters
        ----------
        size : {0}
            The new width and height, in that order.
        """
        [size] = self.region_set._from_angular_sizes([size])
        width, height = size
        super().set_size([height / 2, width / 2])


class PointAnnotation(Region):
    """A point annotation."""
    REGION_TYPE = RegionType.ANNPOINT

    # GET PROPERTIES

    @property
    def point_shape(self):
        """The point shape.

        Returns
        -------
        :obj:`carta.constants.PointShape` object
            The point shape.
        """
        return PointShape(self.get_value("pointShape"))

    @property
    def point_width(self):
        """The point width.

        Returns
        -------
        number
            The point width, in pixels.
        """
        return self.get_value("pointWidth")

    # SET PROPERTIES

    @validate(*all_optional(Constant(PointShape), Number()))
    def set_point_style(self, point_shape=None, point_width=None):
        """Set the point style.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        point_shape : {0}
            The point shape.
        point_width : {1}
            The point width, in pixels.
        """
        if point_shape is not None:
            self.call_action("setPointShape", point_shape)
        if point_width is not None:
            self.call_action("setPointWidth", point_width)


class TextAnnotation(HasFontMixin, HasRotationMixin, Region):
    """A text annotation."""
    REGION_TYPE = RegionType.ANNTEXT

    # GET PROPERTIES

    @property
    def text(self):
        """The text content.

        Returns
        -------
        string
            The text content.
        """
        return self.get_value("text")

    @property
    def position(self):
        """The position of the text in this annotation.

        Returns
        -------
        :obj:`carta.constants.TextPosition`
            The text position.
        """
        return TextPosition(self.get_value("position"))

    # SET PROPERTIES

    @validate(String())
    def set_text(self, text):
        """Set the text content.

        Parameters
        ----------
        text : {0}
            The text content.
        """
        self.call_action("setText", text)

    @validate(Constant(TextPosition))
    def set_text_position(self, text_position):
        """Set the position of the text in this annotation.

        Parameters
        ----------
        text_position : {0}
            The position of the text.
        """
        self.call_action("setPosition", text_position)


class VectorAnnotation(HasPointerMixin, HasEndpointsMixin, HasRotationMixin, Region):
    """A vector annotation."""
    REGION_TYPE = RegionType.ANNVECTOR


class CompassAnnotation(HasFontMixin, HasPointerMixin, Region):
    """A compass annotation."""
    REGION_TYPE = RegionType.ANNCOMPASS

    # GET PROPERTIES

    @property
    def labels(self):
        """The north and east labels.

        Returns
        -------
        string
            The north label.
        string
            The east label.
        """
        return self.get_value("northLabel"), self.get_value("eastLabel")

    @property
    def point_length(self):
        """The length of the compass points, in pixels.

        Returns
        -------
        number
            The length of the compass points.
        """
        return self.get_value("length")

    @property
    def label_offsets(self):
        """The offsets of the north and east labels.

        Returns
        -------
        tuple of two numbers
            The offset of the north label, in pixels.
        tuple of two numbers
            The offset of the east label, in pixels.
        """
        return Pt(**self.get_value("northTextOffset")).as_tuple(), Pt(**self.get_value("eastTextOffset")).as_tuple()

    @property
    def arrowheads_visible(self):
        """The visibility of the north and east arrowheads.

        Returns
        -------
        boolean
            Whether the north arrowhead is visible.
        boolean
            Whether the east arrowhead is visible.
        """
        return self.get_value("northArrowhead"), self.get_value("eastArrowhead")

    # SET PROPERTIES

    @validate(Point.SizePoint())
    def set_size(self, size):
        """Set the size.

        Both pixel and angular sizes are accepted, but both values must match.

        The width and height of this annotation cannot be set independently. If two different values are provided, the smaller value will be used (after conversion to pixel units).

        This function is provided for compatibility. Also see :obj:`carta.region.CompassAnnotation.set_point_length` for a more convenient way to resize this annotation.

        Parameters
        ----------
        size : {0}
            The new size.
        """
        [size] = self.region_set._from_angular_sizes([size])
        self.call_action("setLength", min(*size))

    @validate(*all_optional(String(), String()))
    def set_label(self, north_label=None, east_label=None):
        """Set the north and east labels.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        north_label : {0}
            The north label.
        east_label : {1}
            The east label.
        """
        if north_label is not None:
            self.call_action("setLabel", north_label, True)
        if east_label is not None:
            self.call_action("setLabel", east_label, False)

    @validate(Size(), NoneOr(Constant(SpatialAxis)))
    def set_point_length(self, length, spatial_axis=None):
        """Set the length of the compass points.

        If the length is provided in angular size units, a spatial axis must also be provided in order for the angular size to be converted to pixels.

        Parameters
        ----------
        length : {0}
            The length, in pixels or angular size units.
        spatial_axis : {1}
            The spatial axis which should be used to convert angular size units. This parameter is ignored if the length is provided in pixels.

        Raises
        ------
        ValueError
            If the length is in angular size units, but no spatial axis is provided.
        """
        if isinstance(length, str):
            if spatial_axis is None:
                raise ValueError("Please specify a spatial axis to convert length from angular size units, or use pixels instead.")
            length = self.region_set.image.from_angular_size(length, spatial_axis)
        self.call_action("setLength", length)

    @validate(*all_optional(Point.NumericPoint(), Point.NumericPoint()))
    def set_label_offset(self, north_offset=None, east_offset=None):
        """Set the north and east label offsets.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        north_offset : {0}
            The north label offset, in pixels.
        east_offset : {1}
            The east label offset, in pixels.
        """
        if north_offset is not None:
            north_offset = Pt(*north_offset)
            self.call_action("setNorthTextOffset", north_offset.x, True)
            self.call_action("setNorthTextOffset", north_offset.y, False)
        if east_offset is not None:
            east_offset = Pt(*east_offset)
            self.call_action("setEastTextOffset", east_offset.x, True)
            self.call_action("setEastTextOffset", east_offset.y, False)

    @validate(*all_optional(Boolean(), Boolean()))
    def set_arrowhead_visible(self, north=None, east=None):
        """Set the north and east arrowhead visibility.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        north : {0}
            Whether the north arrowhead should be visible.
        east : {1}
            Whether the east arrowhead should be visible.
        """
        if north is not None:
            self.call_action("setNorthArrowhead", north)
        if east is not None:
            self.call_action("setEastArrowhead", east)


class RulerAnnotation(HasFontMixin, HasEndpointsMixin, Region):
    """A ruler annotation."""
    REGION_TYPE = RegionType.ANNRULER

    # GET PROPERTIES

    @property
    def auxiliary_lines_visible(self):
        """The visibility of the auxiliary lines.

        Returns
        -------
        boolean
            Whether the auxiliary lines are visible.
        """
        return self.get_value("auxiliaryLineVisible")

    @property
    def auxiliary_lines_dash_length(self):
        """The dash length of the auxiliary lines.

        Returns
        -------
        number
            The dash length of the auxiliary lines, in pixels.
        """
        return self.get_value("auxiliaryLineDashLength")

    @property
    def text_offset(self):
        """The X and Y text offsets.

        Returns
        -------
        number
            The X offset of the text, in pixels.
        number
            The Y offset of the text, in pixels.
        """
        return Pt(**self.get_value("textOffset")).as_tuple()

    @property
    def rotation(self):
        """The rotation, in degrees.

        Returns
        -------
        number
            The rotation.
        """
        ((sx, sy), (ex, ey)) = self.endpoints
        rad = math.atan2(ex - sx, sy - ey)
        rotation = math.degrees(rad)
        if ey > sy:
            rotation += 180
        rotation = (rotation + 360) % 360
        return rotation

    # SET PROPERTIES

    @validate(Point.CoordinatePoint())
    def set_center(self, center):
        """Set the center position.

        Both image and world coordinates are accepted, but both values must match.

        Parameters
        ----------
        center : {0}
            The new center position.
        """
        [center] = self.region_set._from_world_coordinates([center])
        cx, cy = center

        rad = math.radians(self.rotation)
        dx = math.hypot(*self.size) * math.sin(rad)
        dy = math.hypot(*self.size) * -1 * math.cos(rad)

        start = cx - dx / 2, cy - dy / 2
        end = cx + dx / 2, cy + dy / 2

        self.set_control_points([start, end])

    @validate(Number())
    def set_rotation(self, rotation):
        """Set the rotation.

        Parameters
        ----------
        angle : {0}
            The new rotation, in degrees.
        """
        rotation = rotation + 360 % 360

        cx, cy = self.center

        rad = math.radians(rotation)
        dx = math.hypot(*self.size) * math.sin(rad)
        dy = math.hypot(*self.size) * -1 * math.cos(rad)

        start = cx - dx / 2, cy - dy / 2
        end = cx + dx / 2, cy + dy / 2

        self.set_control_points([start, end])

    @validate(Point.SizePoint())
    def set_size(self, size):
        """Set the size.

        Both pixel and angular sizes are accepted, but both values must match.

        Parameters
        ----------
        size : {0}
            The new width and height, in that order.
        """
        [size] = self.region_set._from_angular_sizes([size])

        cx, cy = self.center
        dx, dy = size

        start = cx - dx / 2, cy - dy / 2
        end = cx + dx / 2, cy + dy / 2

        self.set_control_points([end, start])  # reversed for consistency with returned size

    @validate(*all_optional(Boolean(), Number()))
    def set_auxiliary_lines_style(self, visible=None, dash_length=None):
        """Set the auxiliary line style.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        visible : {0}
            Whether the auxiliary lines should be visible.
        dash_length : {1}
            The dash length of the auxiliary lines, in pixels.
        """
        if visible is not None:
            self.call_action("setAuxiliaryLineVisible", visible)
        if dash_length is not None:
            self.call_action("setAuxiliaryLineDashLength", dash_length)

    @validate(*all_optional(Number(), Number()))
    def set_text_offset(self, offset_x=None, offset_y=None):
        """Set the text offset.

        All parameters are optional. Omitted properties will be left unmodified.

        Parameters
        ----------
        offset_x : {0}
            The X offset of the text, in pixels.
        offset_y : {1}
            The Y offset of the text, in pixels.
        """
        if offset_x is not None:
            self.call_action("setTextOffset", offset_x, True)
        if offset_y is not None:
            self.call_action("setTextOffset", offset_y, False)
