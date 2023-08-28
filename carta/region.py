"""This module contains region classes which represent single regions or annotations loaded in the session, and a region set class which represents all regions and annotations associated with an image.

Region and annotation objects should not be instantiated directly, and should only be created through methods on the :obj:`carta.region.RegionSet` object.
"""

import posixpath

from .util import Macro, BasePathMixin, Point as Pt, cached, CartaBadResponse, CartaValidationFailed
from .constants import FileType, RegionType, CoordinateType, PointShape, TextPosition, AnnotationFontStyle, AnnotationFont
from .validation import validate, Constant, IterableOf, Number, String, Point, NoneOr, Boolean, OneOf, InstanceOf, MapOf, Color, all_optional, Size, Union


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
        """Add a new region to this image.

        This is a generic low-level function. Also see the higher-level functions for adding regions of specific types, like :obj:`carta.image.add_region_rectangular`.

        Parameters
        ----------
        region_type : {0}
            The type of the region.
        points : {1}
            The control points defining the region, in image coordinates. How these values are interpreted depends on the region type.
        rotation : {2}
            The rotation of the region, in degrees.
        name : {3}
            The name of the region. Defaults to the empty string.
        """
        return Region.new(self, region_type, points, rotation, name)

    def _from_world_coordinates(self, points):
        try:
            points = self.image.from_world_coordinate_points(points)
        except CartaValidationFailed:
            pass
        return points

    def _from_angular_sizes(self, points):
        try:
            points = self.image.from_angular_size_points(points)
        except CartaValidationFailed:
            pass
        return points

    @validate(Point.CoordinatePoint(), Boolean(), String())
    def add_point(self, center, annotation=False, name=""):
        [center] = self._from_world_coordinates([center])
        region_type = RegionType.ANNPOINT if annotation else RegionType.POINT
        return self.add_region(region_type, [center], name=name)

    @validate(Point.CoordinatePoint(), Size(), Size(), Boolean(), Number(), String())
    def add_rectangle(self, center, width, height, annotation=False, rotation=0, name=""):
        [center] = self._from_world_coordinates([center])
        [(width, height)] = self._from_angular_sizes([(width, height)])
        region_type = RegionType.ANNRECTANGLE if annotation else RegionType.RECTANGLE
        return self.add_region(region_type, [center, (width, height)], rotation, name)

    @validate(Point.CoordinatePoint(), Size(), Size(), Boolean(), Number(), String())
    def add_ellipse(self, center, semi_major, semi_minor, annotation=False, rotation=0, name=""):
        [center] = self._from_world_coordinates([center])
        [(semi_major, semi_minor)] = self._from_angular_sizes([(semi_major, semi_minor)])
        region_type = RegionType.ANNELLIPSE if annotation else RegionType.ELLIPSE
        return self.add_region(region_type, [center, (semi_major, semi_minor)], rotation, name)

    @validate(Union(IterableOf(Point.NumericPoint()), IterableOf(Point.WorldCoordinatePoint())), Boolean(), String())
    def add_polygon(self, points, annotation=False, name=""):
        points = self._from_world_coordinates(points)
        region_type = RegionType.ANNPOLYGON if annotation else RegionType.POLYGON
        return self.add_region(region_type, points, name=name)

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint(), Boolean(), String())
    def add_line(self, start, end, annotation=False, name=""):
        [start, end] = self._from_world_coordinates([start, end])
        region_type = RegionType.ANNLINE if annotation else RegionType.LINE
        return self.add_region(region_type, [start, end], name=name)

    @validate(Union(IterableOf(Point.NumericPoint()), IterableOf(Point.WorldCoordinatePoint())), Boolean(), String())
    def add_polyline(self, points, annotation=False, name=""):
        points = self._from_world_coordinates(points)
        region_type = RegionType.ANNPOLYLINE if annotation else RegionType.POLYLINE
        return self.add_region(region_type, points, name=name)

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint(), String())
    def add_vector(self, start, end, name=""):
        [start, end] = self._from_world_coordinates([start, end])
        return self.add_region(RegionType.ANNVECTOR, [start, end], name=name)

    @validate(Point.CoordinatePoint(), Size(), Size(), String(), Number(), String())
    def add_text(self, center, width, height, text, rotation=0, name=""):
        [center] = self._from_world_coordinates([center])
        [(width, height)] = self._from_angular_sizes([(width, height)])
        region = self.add_region(RegionType.ANNTEXT, [center, (width, height)], rotation, name)
        region.set_text(text)
        return region

    @validate(Point.CoordinatePoint(), Number(), String())
    def add_compass(self, center, length, name=""):
        [center] = self._from_world_coordinates([center])
        return self.add_region(RegionType.ANNCOMPASS, [center, (length, length)], name=name)

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint(), String())
    def add_ruler(self, start, end, name=""):
        [start, end] = self._from_world_coordinates([start, end])
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
        region_type = RegionType(region_type)
        return cls.CUSTOM_CLASS.get(region_type, Annotation if region_type.is_annotation else Region)

    @classmethod
    @validate(Constant(RegionType), InstanceOf(RegionSet), Number())
    def existing(cls, region_type, region_set, region_id):
        return cls.region_class(region_type)(region_set, region_id)

    @classmethod
    @validate(InstanceOf(RegionSet), Constant(RegionType), IterableOf(Point()), Number(), String())
    def new(cls, region_set, region_type, points, rotation=0, name=""):
        points = [Pt(*point) for point in points]  # TODO at this point we should already have pixel points here
        region_id = region_set.call_action("addRegionAsync", region_type, points, rotation, name, return_path="regionId")
        return cls.existing(region_type, region_set, region_id)

    @classmethod
    @validate(InstanceOf(RegionSet), IterableOf(MapOf(String(), Number(), required_keys={"type", "id"})))
    def from_list(cls, region_set, region_list):
        return [cls.existing(r["type"], region_set, r["id"]) for r in region_list]

    # GET PROPERTIES

    @property
    @cached
    def region_type(self):
        return RegionType(self.get_value("regionType"))

    @property
    def center(self):
        return Pt(**self.get_value("center")).as_tuple()

    @property
    def wcs_center(self):
        [center] = self.region_set.image.to_world_coordinate_points([self.center])
        return center

    @property
    def size(self):
        return Pt(**self.get_value("size")).as_tuple()

    @property
    def wcs_size(self):
        size = self.get_value("wcsSize")
        return (f"{size['x']}\"", f"{size['y']}\"")

    @property
    def rotation(self):
        return self.get_value("rotation")

    @property
    def control_points(self):
        return [Pt(**p).as_tuple() for p in self.get_value("controlPoints")]

    @property
    def name(self):
        return self.get_value("name")

    @property
    def color(self):
        return self.get_value("color")

    @property
    def line_width(self):
        return self.get_value("lineWidth")

    @property
    def dash_length(self):
        return self.get_value("dashLength")

    # SET PROPERTIES

    @validate(Point.CoordinatePoint())
    def set_center(self, center):
        [center] = self.region_set._from_world_coordinates([center])
        self.call_action("setCenter", Pt(*center))

    @validate(Size(), Size())
    def set_size(self, x, y):
        [(x, y)] = self.region_set._from_angular_sizes([(x, y)])
        self.call_action("setSize", Pt(x, y))

    @validate(Number(), Point.NumericPoint())
    def set_control_point(self, index, point):
        self.call_action("setControlPoint", index, Pt(*point))

    @validate(IterableOf(Point.NumericPoint()))
    def set_control_points(self, points):
        self.call_action("setControlPoints", [Pt(*p) for p in points])

    @validate(Number())
    def set_rotation(self, angle):
        """Set the rotation of this region to the given angle.

        Parameters
        ----------
        angle : {0}
            The new rotation angle.
        """
        self.call_action("setRotation", angle)

    @validate(String())
    def set_name(self, name):
        self.call_action("setName", name)

    @validate(Color())
    def set_color(self, color):
        self.call_action("setColor", color)

    @validate(Number())
    def set_line_width(self, width):
        self.call_action("setLineWidth", width)

    @validate(Number())
    def set_dash_length(self, length):
        self.call_action("setDashLength", length)

    def lock(self):
        self.call_action("setLocked", True)

    def unlock(self):
        self.call_action("setLocked", False)

    def focus(self):
        self.call_action("focusCenter")

    # IMPORT AND EXPORT

    @validate(String(), Constant(CoordinateType), OneOf(FileType.CRTF, FileType.DS9_REG))
    def export_to(self, path, coordinate_type=CoordinateType.WORLD, file_type=FileType.CRTF):
        self.region_set.export_to(path, coordinate_type, file_type, [self.region_id])

    def delete(self):
        """Delete this region."""
        self.region_set.call_action("deleteRegion", self._region)


class HasPositionsMixin:
    @property
    def positions(self):
        return self.control_points

    @property
    def wcs_positions(self):
        return self.region_set.image.to_world_coordinate_points[self.control_points]

    @validate(IterableOf(Point.CoordinatePoint()))
    def set_positions(self, points):
        points = self.region_set._from_world_coordinates(points)
        self.set_control_points(points)

    @validate(Point.CoordinatePoint())
    def set_position(self, index, point):
        [point] = self.region_set._from_world_coordinates([point])
        self.set_control_point(index, point)


class HasEndpointsMixin:
    @property
    def endpoints(self):
        return self.control_points

    @property
    def wcs_endpoints(self):
        return self.region_set.image.to_world_coordinate_points[self.control_points]

    @validate(Point.CoordinatePoint(), Point.CoordinatePoint())
    def set_endpoints(self, start, end):
        [start] = self.region_set._from_world_coordinates([start])
        [end] = self.region_set._from_world_coordinates([end])
        self.set_control_points([start, end])


# TODO maybe consolidate these into single functions
class HasFontMixin:

    # GET PROPERTIES

    @property
    def font_size(self):
        return self.get_value("fontSize")

    @property
    def font_style(self):
        return AnnotationFontStyle(self.get_value("fontStyle"))

    @property
    def font(self):
        return AnnotationFont(self.get_value("font"))

    # SET PROPERTIES

    @validate(Number())
    def set_font_size(self, size):
        self.call_action("setFontSize", size)

    @validate(Constant(AnnotationFontStyle))
    def set_font_style(self, style):
        self.call_action("setFontStyle", style)

    @validate(Constant(AnnotationFont))
    def set_font(self, font):
        self.call_action("setFont", font)


# TODO maybe consolidate these into single functions
class HasPointerMixin:

    # GET PROPERTIES

    @property
    def pointer_width(self):
        return self.get_value("pointerWidth")

    @property
    def pointer_length(self):
        return self.get_value("pointerLength")

    # SET PROPERTIES

    @validate(Number())
    def set_pointer_width(self, width):
        self.call_action("setPointerWidth", width)

    @validate(Number())
    def set_pointer_length(self, length):
        self.call_action("setPointerLength", length)


class Annotation(Region):
    """Base class for annotations."""
    pass


class LineRegion(Region, HasEndpointsMixin):
    REGION_TYPE = RegionType.LINE


class PolylineRegion(Region, HasPositionsMixin):
    REGION_TYPE = RegionType.POLYLINE


class PolygonRegion(Region, HasPositionsMixin):
    REGION_TYPE = RegionType.POLYGON


class LineAnnotation(Annotation, HasEndpointsMixin):
    REGION_TYPE = RegionType.ANNLINE


class PolylineAnnotation(Annotation, HasPositionsMixin):
    REGION_TYPE = RegionType.ANNPOLYLINE


class PolygonAnnotation(Annotation, HasPositionsMixin):
    REGION_TYPE = RegionType.ANNPOLYGON


class PointAnnotation(Annotation):
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
    REGION_TYPE = RegionType.ANNVECTOR


class CompassAnnotation(Annotation, HasFontMixin, HasPointerMixin):
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

    @validate(*all_optional(Point.NumericPoint(), Point.NumericPoint()))  # TODO pixel only!
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
