import pytest
import math

from carta.region import Region
from carta.constants import RegionType as RT, FileType as FT, CoordinateType as CT, AnnotationFontStyle as AFS, AnnotationFont as AF, PointShape as PS, TextPosition as TP, SpatialAxis as SA
from carta.util import Point as Pt, Macro

# FIXTURES

# Session and image mocks


@pytest.fixture
def session_call_action(session, mock_call_action):
    return mock_call_action(session)


@pytest.fixture
def session_method(session, mock_method):
    return mock_method(session)


@pytest.fixture
def image_method(image, mock_method):
    return mock_method(image)


@pytest.fixture
def mock_to_world(image_method):
    return image_method("to_world_coordinate_points", lambda l: [(str(x), str(y)) for (x, y) in l])


@pytest.fixture
def mock_to_angular(image_method):
    return image_method("to_angular_size_points", lambda l: [(str(x), str(y)) for (x, y) in l])


# Regionset mocks


@pytest.fixture
def regionset_get_value(image, mock_get_value):
    return mock_get_value(image.regions)


@pytest.fixture
def regionset_call_action(image, mock_call_action):
    return mock_call_action(image.regions)


@pytest.fixture
def regionset_method(image, mock_method):
    return mock_method(image.regions)


@pytest.fixture
def mock_from_world(regionset_method):
    return regionset_method("_from_world_coordinates", lambda l: [(int(x), int(y)) for (x, y) in l])


@pytest.fixture
def mock_from_angular(regionset_method):
    return regionset_method("_from_angular_sizes", lambda l: [(int(x), int(y)) for (x, y) in l])


# The region-specific mocks are all factories, so that they can be used to mock different region subclasses (specified by region type)


@pytest.fixture
def region(image, mock_property):
    def func(region_type=None, region_id=0):
        clazz = Region if region_type is None else Region.region_class(region_type)
        mock_property(f"carta.region.{clazz.__name__}")("region_type", region_type)
        reg = clazz(image.regions, region_id)
        return reg
    return func


@pytest.fixture
def get_value(mocker):
    def func(reg, mock_value=None):
        return mocker.patch.object(reg, "get_value", return_value=mock_value)
    return func


@pytest.fixture
def call_action(mock_call_action):
    def func(reg):
        return mock_call_action(reg)
    return func


@pytest.fixture
def property_(mock_property):
    def func(reg):
        return mock_property(f"carta.region.{reg.__class__.__name__}")
    return func


@pytest.fixture
def method(mock_method):
    def func(reg):
        return mock_method(reg)
    return func


# TESTS

# REGION SET


@pytest.mark.parametrize("ignore_cursor,expected_items", [
    (True, [2, 3]),
    (False, [1, 2, 3]),
])
def test_regionset_list(mocker, image, regionset_get_value, ignore_cursor, expected_items):
    regionset_get_value.side_effect = [[1, 2, 3]]
    mock_from_list = mocker.patch.object(Region, "from_list")
    image.regions.list(ignore_cursor)
    regionset_get_value.assert_called_with("regionList")
    mock_from_list.assert_called_with(image.regions, expected_items)


def test_regionset_get(mocker, image, regionset_get_value):
    regionset_get_value.side_effect = [RT.RECTANGLE]
    mock_existing = mocker.patch.object(Region, "existing")
    image.regions.get(1)
    regionset_get_value.assert_called_with("regionMap[1]", return_path="regionType")
    mock_existing.assert_called_with(RT.RECTANGLE, image.regions, 1)


def test_regionset_import_from(mocker, image, session_method, session_call_action):
    session_method("resolve_file_path", ["/path/to/directory/"])
    session_call_action.side_effect = [FT.CRTF, None]
    image.regions.import_from("input_region_file")
    session_call_action.assert_has_calls([
        mocker.call("backendService.getRegionFileInfo", "/path/to/directory/", "input_region_file", return_path="fileInfo.type"),
        mocker.call("importRegion", "/path/to/directory/", "input_region_file", FT.CRTF, image._frame),
    ])


@pytest.mark.parametrize("coordinate_type", [CT.PIXEL, CT.WORLD])
@pytest.mark.parametrize("file_type", [FT.CRTF, FT.DS9_REG])
@pytest.mark.parametrize("region_ids,expected_region_ids", [(None, [2, 3, 4]), ([2, 3], [2, 3]), ([4], [4])])
def test_regionset_export_to(mocker, image, session_method, session_call_action, regionset_get_value, coordinate_type, file_type, region_ids, expected_region_ids):
    session_method("resolve_file_path", ["/path/to/directory/"])
    regionset_get_value.side_effect = [[{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]]
    image.regions.export_to("output_region_file", coordinate_type, file_type, region_ids)
    session_call_action.assert_called_with("exportRegions", "/path/to/directory/", "output_region_file", coordinate_type, file_type, expected_region_ids, image._frame)


def test_regionset_add_region(mocker, image):
    mock_new = mocker.patch.object(Region, "new")
    image.regions.add_region(RT.RECTANGLE, [(10, 10), (100, 100)], 90, "name")
    mock_new.assert_called_with(image.regions, RT.RECTANGLE, [(10, 10), (100, 100)], 90, "name")


@pytest.mark.parametrize("func,args,kwargs,expected_args,expected_kwargs", [
    ("add_point", [(10, 10)], {}, [RT.POINT, [(10, 10)]], {"name": ""}),
    ("add_point", [("10", "10")], {}, [RT.POINT, [(10, 10)]], {"name": ""}),
    ("add_point", [(10, 10)], {"annotation": True}, [RT.ANNPOINT, [(10, 10)]], {"name": ""}),
    ("add_point", [(10, 10)], {"name": "my region"}, [RT.POINT, [(10, 10)]], {"name": "my region"}),

    ("add_rectangle", [(10, 10), (20, 20)], {}, [RT.RECTANGLE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_rectangle", [("10", "10"), ("20", "20")], {}, [RT.RECTANGLE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_rectangle", [("10", "10"), (20, 20)], {}, [RT.RECTANGLE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_rectangle", [(10, 10), ("20", "20")], {}, [RT.RECTANGLE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_rectangle", [(10, 10), (20, 20)], {"annotation": True}, [RT.ANNRECTANGLE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_rectangle", [(10, 10), (20, 20)], {"name": "my region"}, [RT.RECTANGLE, [(10, 10), (20, 20)], 0, "my region"], {}),
    ("add_rectangle", [(10, 10), (20, 20)], {"rotation": 45}, [RT.RECTANGLE, [(10, 10), (20, 20)], 45, ""], {}),

    ("add_ellipse", [(10, 10), (20, 20)], {}, [RT.ELLIPSE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_ellipse", [("10", "10"), ("20", "20")], {}, [RT.ELLIPSE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_ellipse", [("10", "10"), (20, 20)], {}, [RT.ELLIPSE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_ellipse", [(10, 10), ("20", "20")], {}, [RT.ELLIPSE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_ellipse", [(10, 10), (20, 20)], {"annotation": True}, [RT.ANNELLIPSE, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_ellipse", [(10, 10), (20, 20)], {"name": "my region"}, [RT.ELLIPSE, [(10, 10), (20, 20)], 0, "my region"], {}),
    ("add_ellipse", [(10, 10), (20, 20)], {"rotation": 45}, [RT.ELLIPSE, [(10, 10), (20, 20)], 45, ""], {}),

    ("add_polygon", [[(10, 10), (20, 20), (30, 30)]], {}, [RT.POLYGON, [(10, 10), (20, 20), (30, 30)]], {"name": ""}),
    ("add_polygon", [[("10", "10"), ("20", "20"), ("30", "30")]], {}, [RT.POLYGON, [(10, 10), (20, 20), (30, 30)]], {"name": ""}),
    ("add_polygon", [[(10, 10), (20, 20), (30, 30)]], {"annotation": True}, [RT.ANNPOLYGON, [(10, 10), (20, 20), (30, 30)]], {"name": ""}),
    ("add_polygon", [[(10, 10), (20, 20), (30, 30)]], {"name": "my region"}, [RT.POLYGON, [(10, 10), (20, 20), (30, 30)]], {"name": "my region"}),

    ("add_line", [(10, 10), (20, 20)], {}, [RT.LINE, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_line", [("10", "10"), ("20", "20")], {}, [RT.LINE, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_line", [(10, 10), (20, 20)], {"annotation": True}, [RT.ANNLINE, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_line", [(10, 10), (20, 20)], {"name": "my region"}, [RT.LINE, [(10, 10), (20, 20)]], {"name": "my region"}),

    ("add_polyline", [[(10, 10), (20, 20), (30, 30)]], {}, [RT.POLYLINE, [(10, 10), (20, 20), (30, 30)]], {"name": ""}),
    ("add_polyline", [[("10", "10"), ("20", "20"), ("30", "30")]], {}, [RT.POLYLINE, [(10, 10), (20, 20), (30, 30)]], {"name": ""}),
    ("add_polyline", [[(10, 10), (20, 20), (30, 30)]], {"annotation": True}, [RT.ANNPOLYLINE, [(10, 10), (20, 20), (30, 30)]], {"name": ""}),
    ("add_polyline", [[(10, 10), (20, 20), (30, 30)]], {"name": "my region"}, [RT.POLYLINE, [(10, 10), (20, 20), (30, 30)]], {"name": "my region"}),

    ("add_vector", [(10, 10), (20, 20)], {}, [RT.ANNVECTOR, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_vector", [("10", "10"), ("20", "20")], {}, [RT.ANNVECTOR, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_vector", [(10, 10), (20, 20)], {"name": "my region"}, [RT.ANNVECTOR, [(10, 10), (20, 20)]], {"name": "my region"}),

    ("add_text", [(10, 10), (20, 20), "text goes here"], {}, [RT.ANNTEXT, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_text", [("10", "10"), ("20", "20"), "text goes here"], {}, [RT.ANNTEXT, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_text", [("10", "10"), (20, 20), "text goes here"], {}, [RT.ANNTEXT, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_text", [(10, 10), ("20", "20"), "text goes here"], {}, [RT.ANNTEXT, [(10, 10), (20, 20)], 0, ""], {}),
    ("add_text", [(10, 10), (20, 20), "text goes here"], {"name": "my region"}, [RT.ANNTEXT, [(10, 10), (20, 20)], 0, "my region"], {}),
    ("add_text", [(10, 10), (20, 20), "text goes here"], {"rotation": 45}, [RT.ANNTEXT, [(10, 10), (20, 20)], 45, ""], {}),

    ("add_compass", [(10, 10), 100], {}, [RT.ANNCOMPASS, [(10, 10), (100, 100)]], {"name": ""}),
    ("add_compass", [("10", "10"), 100], {}, [RT.ANNCOMPASS, [(10, 10), (100, 100)]], {"name": ""}),
    ("add_compass", [(10, 10), 100], {"name": "my region"}, [RT.ANNCOMPASS, [(10, 10), (100, 100)]], {"name": "my region"}),

    ("add_ruler", [(10, 10), (20, 20)], {}, [RT.ANNRULER, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_ruler", [("10", "10"), ("20", "20")], {}, [RT.ANNRULER, [(10, 10), (20, 20)]], {"name": ""}),
    ("add_ruler", [(10, 10), (20, 20)], {"name": "my region"}, [RT.ANNRULER, [(10, 10), (20, 20)]], {"name": "my region"}),
])
def test_regionset_add_region_with_type(mocker, image, regionset_method, mock_from_world, mock_from_angular, region, func, args, kwargs, expected_args, expected_kwargs):
    mock_add_region = regionset_method("add_region", None)

    if func == "add_text":
        text_annotation = region(region_type=RT.ANNTEXT)
        mock_add_region.return_value = text_annotation
        mock_set_text = mocker.patch.object(text_annotation, "set_text")

    getattr(image.regions, func)(*args, **kwargs)

    mock_add_region.assert_called_with(*expected_args, **expected_kwargs)

    if func == "add_text":
        mock_set_text.assert_called_with(args[2])


def test_regionset_clear(mocker, image, regionset_method, method, region):
    regionlist = [region(), region(), region()]
    mock_deletes = [method(r)("delete", None) for r in regionlist]
    regionset_method("list", [regionlist])

    image.regions.clear()

    for m in mock_deletes:
        m.assert_called_with()


def test_region_type(image, get_value):
    reg = Region(image.regions, 0)  # Bypass the default to test the real region_type
    reg_get_value = get_value(reg, 3)

    region_type = reg.region_type

    reg_get_value.assert_called_with("regionType")
    assert region_type == RT.RECTANGLE


@pytest.mark.parametrize("region_type", [t for t in RT])
def test_center(region, get_value, region_type):
    reg = region(region_type)
    reg_get_value = get_value(reg, {"x": 20, "y": 30})

    center = reg.center

    reg_get_value.assert_called_with("center")
    assert center == (20, 30)


@pytest.mark.parametrize("region_type", [t for t in RT])
def test_wcs_center(region, property_, mock_to_world, region_type):
    reg = region(region_type)
    property_(reg)("center", (20, 30))

    wcs_center = reg.wcs_center

    mock_to_world.assert_called_with([(20, 30)])
    assert wcs_center == ("20", "30")


@pytest.mark.parametrize("region_type", [t for t in RT])
def test_size(region, get_value, region_type):
    reg = region(region_type)

    if region_type in {RT.POINT, RT.ANNPOINT}:
        reg_get_value = get_value(reg, None)
    elif region_type in {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER}:
        # Check that we get the absolute values of these
        reg_get_value = get_value(reg, {"x": -20, "y": -30})
    else:
        reg_get_value = get_value(reg, {"x": 20, "y": 30})

    size = reg.size

    reg_get_value.assert_called_with("size")
    if region_type in {RT.ELLIPSE, RT.ANNELLIPSE}:
        assert size == (60, 40)  # The frontend size returned for an ellipse is the semi-axes, which we double and swap
    elif region_type in {RT.POINT, RT.ANNPOINT}:
        assert size is None  # Test that returned null/undefined size for a point is converted to None as expected
    else:
        assert size == (20, 30)


@pytest.mark.parametrize("region_type", [t for t in RT])
def test_wcs_size(region, get_value, property_, mock_to_angular, region_type):
    reg = region(region_type)

    if region_type in {RT.ELLIPSE, RT.ANNELLIPSE, RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER}:
        # Bypasses wcsSize to call own (overridden) size and converts to angular units
        property_(reg)("size", (20, 30))
    elif region_type in {RT.POINT, RT.ANNPOINT}:
        # Simulate undefined size
        reg_get_value = get_value(reg, {"x": None, "y": None})
    else:
        reg_get_value = get_value(reg, {"x": "20", "y": "30"})

    size = reg.wcs_size

    if region_type in {RT.ELLIPSE, RT.ANNELLIPSE, RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER}:
        mock_to_angular.assert_called_with([(20, 30)])
        assert size == ("20", "30")
    elif region_type in {RT.POINT, RT.ANNPOINT}:
        reg_get_value.assert_called_with("wcsSize")
        assert size is None
    else:
        reg_get_value.assert_called_with("wcsSize")
        assert size == ("20\"", "30\"")


def test_control_points(region, get_value):
    reg = region()
    get_value(reg, [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}])
    points = reg.control_points
    assert points == [(1, 2), (3, 4), (5, 6)]


@pytest.mark.parametrize("method_name,value_name", [
    ("name", "name"),
    ("color", "color"),
    ("line_width", "lineWidth"),
    ("dash_length", "dashLength"),
])
def test_simple_properties(region, get_value, method_name, value_name):
    reg = region()
    mock_value_getter = get_value(reg, "dummy")
    value = getattr(reg, method_name)
    mock_value_getter.assert_called_with(value_name)
    assert value == "dummy"


@pytest.mark.parametrize("region_type", [t for t in RT])
@pytest.mark.parametrize("value,expected_value", [
    ((20, 30), Pt(20, 30)),
    (("20", "30"), Pt(20, 30)),
])
def test_set_center(region, mock_from_world, call_action, method, property_, region_type, value, expected_value):
    reg = region(region_type)

    if region_type == RT.ANNRULER:
        property_(reg)("size", (-10, -10))
        property_(reg)("rotation", 135)
        mock_set_points = method(reg)("set_control_points", None)
    else:
        mock_call = call_action(reg)

    reg.set_center(value)

    if region_type == RT.ANNRULER:
        mock_set_points.assert_called_with([(15, 25), (25, 35)])
    else:
        mock_call.assert_called_with("setCenter", expected_value)


@pytest.mark.parametrize("region_type", [t for t in RT])
@pytest.mark.parametrize("value,expected_value", [
    ((20, 30), Pt(20, 30)),
    ((-20, -30), Pt(-20, -30)),
    (("20", "30"), Pt(20, 30)),
])
def test_set_size(region, mock_from_angular, call_action, method, property_, region_type, value, expected_value):
    reg = region(region_type)

    if region_type in {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER}:
        mock_set_points = method(reg)("set_control_points", None)
        property_(reg)("center", (10, 10))
        property_(reg)("rotation", 135)
    else:
        mock_call = call_action(reg)

    reg.set_size(value)

    if region_type in {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER}:
        mock_set_points.assert_called_with([(0.0, -5.0), (20.0, 25.0)])
    elif region_type == RT.ANNCOMPASS:
        mock_call.assert_called_with("setLength", min(expected_value.x, expected_value.y))
    elif region_type in {RT.ELLIPSE, RT.ANNELLIPSE}:
        mock_call.assert_called_with("setSize", Pt(expected_value.y / 2, expected_value.x / 2))
    else:
        mock_call.assert_called_with("setSize", expected_value)


def test_set_control_point(region, call_action):
    reg = region()
    mock_call = call_action(reg)
    reg.set_control_point(3, (20, 30))
    mock_call.assert_called_with("setControlPoint", 3, Pt(20, 30))


def test_set_control_points(region, call_action):
    reg = region()
    mock_call = call_action(reg)
    reg.set_control_points([(20, 30), (40, 50)])
    mock_call.assert_called_with("setControlPoints", [Pt(20, 30), Pt(40, 50)])


def test_set_name(region, call_action):
    reg = region()
    mock_call = call_action(reg)
    reg.set_name("My region name")
    mock_call.assert_called_with("setName", "My region name")


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    (["blue", 2, 3], {}, [("setColor", "blue"), ("setLineWidth", 2), ("setDashLength", 3)]),
    (["blue"], {"dash_length": 3}, [("setColor", "blue"), ("setDashLength", 3)]),
    ([], {"line_width": 2}, [("setLineWidth", 2)]),
])
def test_set_line_style(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region()
    mock_call = call_action(reg)
    reg.set_line_style(*args, **kwargs)
    mock_call.assert_has_calls([mocker.call(*c) for c in expected_calls])


def test_lock(region, call_action):
    reg = region()
    mock_call = call_action(reg)
    reg.lock()
    mock_call.assert_called_with("setLocked", True)


def test_unlock(region, call_action):
    reg = region()
    mock_call = call_action(reg)
    reg.unlock()
    mock_call.assert_called_with("setLocked", False)


def test_focus(region, call_action):
    reg = region()
    mock_call = call_action(reg)
    reg.focus()
    mock_call.assert_called_with("focusCenter")


@pytest.mark.parametrize("args,kwargs,expected_params", [
    (["/path/to/file"], {}, ["/path/to/file", CT.WORLD, FT.CRTF]),
    (["/path/to/file", CT.PIXEL, FT.DS9_REG], {}, ["/path/to/file", CT.PIXEL, FT.DS9_REG]),
    (["/path/to/file"], {"coordinate_type": CT.PIXEL}, ["/path/to/file", CT.PIXEL, FT.CRTF]),
    (["/path/to/file"], {"file_type": FT.DS9_REG}, ["/path/to/file", CT.WORLD, FT.DS9_REG]),
])
def test_export_to(region, regionset_method, args, kwargs, expected_params):
    reg = region()
    mock_export = regionset_method("export_to", None)

    reg.export_to(*args, **kwargs)

    mock_export.assert_called_with(*expected_params, [reg.region_id])


def test_delete(region, regionset_call_action):
    reg = region()
    reg.delete()
    regionset_call_action.assert_called_with("deleteRegion", Macro("", f"{reg.region_set._base_path}.regionMap[{reg.region_id}]"))


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.RECTANGLE, RT.ANNRECTANGLE, RT.ELLIPSE, RT.ANNELLIPSE, RT.ANNTEXT, RT.ANNVECTOR, RT.ANNRULER})
def test_rotation(region, get_value, property_, region_type):
    reg = region(region_type)

    if region_type == RT.ANNRULER:
        property_(reg)("endpoints", [(90, 110), (110, 90)])
    else:
        mock_rotation = get_value(reg, "dummy")

    value = reg.rotation

    if region_type == RT.ANNRULER:
        assert value == 45
    else:
        mock_rotation.assert_called_with("rotation")
        assert value == "dummy"


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.RECTANGLE, RT.ANNRECTANGLE, RT.ELLIPSE, RT.ANNELLIPSE, RT.ANNTEXT, RT.ANNVECTOR, RT.ANNRULER})
def test_set_rotation(region, call_action, method, property_, region_type):
    reg = region(region_type)

    if region_type == RT.ANNRULER:
        property_(reg)("center", (100, 100))
        property_(reg)("size", (20, 20))
        mock_set_points = method(reg)("set_control_points", None)
    else:
        mock_call = call_action(reg)

    reg.set_rotation(45)

    if region_type == RT.ANNRULER:
        mock_set_points.assert_called_with([(90, 110), (110, 90)])
    else:
        mock_call.assert_called_with("setRotation", 45)


@pytest.mark.parametrize("region_type", {RT.POLYLINE, RT.POLYGON, RT.ANNPOLYLINE, RT.ANNPOLYGON})
def test_vertices(region, property_, region_type):
    reg = region(region_type)
    property_(reg)("control_points", [(10, 10), (20, 30), (30, 20)])
    vertices = reg.vertices
    assert vertices == [(10, 10), (20, 30), (30, 20)]


@pytest.mark.parametrize("region_type", {RT.POLYLINE, RT.POLYGON, RT.ANNPOLYLINE, RT.ANNPOLYGON})
def test_wcs_vertices(region, property_, mock_to_world, region_type):
    reg = region(region_type)
    property_(reg)("control_points", [(10, 10), (20, 30), (30, 20)])
    vertices = reg.wcs_vertices
    assert vertices == [("10", "10"), ("20", "30"), ("30", "20")]


@pytest.mark.parametrize("region_type", {RT.POLYLINE, RT.POLYGON, RT.ANNPOLYLINE, RT.ANNPOLYGON})
@pytest.mark.parametrize("vertex", [(30, 40), ("30", "40")])
def test_set_vertex(region, method, mock_from_world, region_type, vertex):
    reg = region(region_type)
    mock_set_control_point = method(reg)("set_control_point", None)
    reg.set_vertex(1, vertex)
    mock_set_control_point.assert_called_with(1, (30, 40))


@pytest.mark.parametrize("region_type", {RT.POLYLINE, RT.POLYGON, RT.ANNPOLYLINE, RT.ANNPOLYGON})
@pytest.mark.parametrize("vertices", [
    [(10, 10), (20, 30), (30, 20)],
    [("10", "10"), ("20", "30"), ("30", "20")],
])
def test_set_vertices(region, method, mock_from_world, region_type, vertices):
    reg = region(region_type)
    mock_set_control_points = method(reg)("set_control_points", None)
    reg.set_vertices(vertices)
    mock_set_control_points.assert_called_with([(10, 10), (20, 30), (30, 20)])


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER})
def test_endpoints(region, property_, region_type):
    reg = region(region_type)
    property_(reg)("control_points", [(10, 10), (20, 30)])
    endpoints = reg.endpoints
    assert endpoints == [(10, 10), (20, 30)]


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER})
def test_wcs_endpoints(region, property_, mock_to_world, region_type):
    reg = region(region_type)
    property_(reg)("control_points", [(10, 10), (20, 30)])
    endpoints = reg.wcs_endpoints
    assert endpoints == [("10", "10"), ("20", "30")]


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER})
def test_length(region, property_, region_type):
    reg = region(region_type)
    property_(reg)("size", (30, 40))
    length = reg.length
    assert length == 50


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER})
def test_wcs_length(region, property_, region_type):
    reg = region(region_type)
    property_(reg)("wcs_size", ("30", "40"))
    length = reg.wcs_length
    assert length == "50\""


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER})
@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([(10, 10), (20, 30)], {}, [(0, (10, 10)), (1, (20, 30))]),
    ([("10", "10"), ("20", "30")], {}, [(0, (10, 10)), (1, (20, 30))]),
    ([(10, 10), ("20", "30")], {}, [(0, (10, 10)), (1, (20, 30))]),
    ([], {"start": (10, 10)}, [(0, (10, 10))]),
    ([], {"end": (20, 30)}, [(1, (20, 30))]),
])
def test_set_endpoints(mocker, region, method, mock_from_world, region_type, args, kwargs, expected_calls):
    reg = region(region_type)
    mock_set_control_point = method(reg)("set_control_point", None)
    reg.set_endpoints(*args, **kwargs)
    mock_set_control_point.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("region_type", {RT.LINE, RT.ANNLINE, RT.ANNVECTOR, RT.ANNRULER})
@pytest.mark.parametrize("length", [math.sqrt(800), str(math.sqrt(800))])
def test_set_length(mocker, region, property_, region_type, length):
    reg = region(region_type)

    property_(reg)("length", 100)
    property_(reg)("wcs_length", "100")
    property_(reg)("rotation", 45)
    mock_region_set_size = mocker.patch.object(Region, "set_size")

    reg.set_length(length)

    mock_region_set_size.assert_called()
    (s1, s2), = mock_region_set_size.call_args.args
    assert math.isclose(s1, 20)
    assert math.isclose(s2, -20)


@pytest.mark.parametrize("region_type", {RT.ANNTEXT, RT.ANNCOMPASS, RT.ANNRULER})
@pytest.mark.parametrize("method_name,value_name,mocked_value,expected_value", [
    ("font_size", "fontSize", 20, 20),
    ("font_style", "fontStyle", "Bold", AFS.BOLD),
    ("font", "font", "Courier", AF.COURIER),
])
def test_font_properties(region, get_value, region_type, method_name, value_name, mocked_value, expected_value):
    reg = region(region_type)
    mock_value_getter = get_value(reg, mocked_value)
    value = getattr(reg, method_name)
    mock_value_getter.assert_called_with(value_name)
    assert value == expected_value


@pytest.mark.parametrize("region_type", {RT.ANNTEXT, RT.ANNCOMPASS, RT.ANNRULER})
@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([AF.COURIER, 20, AFS.BOLD], {}, [("setFont", AF.COURIER), ("setFontSize", 20), ("setFontStyle", AFS.BOLD)]),
    ([], {"font": AF.COURIER, "font_size": 20, "font_style": AFS.BOLD}, [("setFont", AF.COURIER), ("setFontSize", 20), ("setFontStyle", AFS.BOLD)]),
    ([AF.COURIER], {"font_style": AFS.BOLD}, [("setFont", AF.COURIER), ("setFontStyle", AFS.BOLD)]),
    ([], {"font_size": 20}, [("setFontSize", 20)]),
])
def test_set_font(mocker, region, call_action, region_type, args, kwargs, expected_calls):
    reg = region(region_type)
    mock_action_caller = call_action(reg)
    reg.set_font(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("region_type", {RT.ANNVECTOR, RT.ANNCOMPASS})
@pytest.mark.parametrize("method_name,value_name", [
    ("pointer_width", "pointerWidth"),
    ("pointer_length", "pointerLength"),
])
def test_pointer_properties(region, get_value, region_type, method_name, value_name):
    reg = region(region_type)
    mock_value_getter = get_value(reg, "dummy")
    value = getattr(reg, method_name)
    mock_value_getter.assert_called_with(value_name)
    assert value == "dummy"


@pytest.mark.parametrize("region_type", {RT.ANNVECTOR, RT.ANNCOMPASS})
@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([2, 20], {}, [("setPointerWidth", 2), ("setPointerLength", 20)]),
    ([], {"pointer_length": 20}, [("setPointerLength", 20)]),
])
def test_set_pointer_style(mocker, region, call_action, region_type, args, kwargs, expected_calls):
    reg = region(region_type)
    mock_action_caller = call_action(reg)
    reg.set_pointer_style(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("region_type", {RT.RECTANGLE, RT.ANNRECTANGLE})
def test_corners(region, property_, region_type):
    reg = region(region_type)
    property_(reg)("center", (100, 200))
    property_(reg)("size", (30, 40))

    bottom_left, top_right = reg.corners

    assert bottom_left == (85, 180)
    assert top_right == (115, 220)


@pytest.mark.parametrize("region_type", {RT.RECTANGLE, RT.ANNRECTANGLE})
def test_wcs_corners(region, property_, mock_to_world, region_type):
    reg = region(region_type)
    property_(reg)("corners", [(85, 180), (115, 220)])

    bottom_left, top_right = reg.wcs_corners

    assert bottom_left == ("85", "180")
    assert top_right == ("115", "220")


@pytest.mark.parametrize("region_type", {RT.RECTANGLE, RT.ANNRECTANGLE})
@pytest.mark.parametrize("args,kwargs,expected_args", [
    ([], {}, None),
    ([(75, 170), (135, 240)], {}, [(105.0, 205.0), (60, 70)]),
    ([(75, 170)], {}, [(95.0, 195.0), (40, 50)]),
    ([], {"top_right": (135, 240)}, [(110.0, 210.0), (50, 60)]),
])
def test_set_corners(region, method, property_, mock_from_world, region_type, args, kwargs, expected_args):
    reg = region(region_type)
    property_(reg)("corners", [(85, 180), (115, 220)])
    mock_set_control_points = method(reg)("set_control_points", None)

    reg.set_corners(*args, **kwargs)

    if expected_args is None:
        mock_set_control_points.assert_not_called()
    else:
        mock_set_control_points.assert_called_with(expected_args)


@pytest.mark.parametrize("region_type", {RT.ELLIPSE, RT.ANNELLIPSE})
def test_semi_axes(mocker, region, region_type):
    reg = region(region_type)
    mocker.patch("carta.region.Region.size", new_callable=mocker.PropertyMock, return_value=(20, 30))

    semi_axes = reg.semi_axes

    assert semi_axes == (20, 30)


@pytest.mark.parametrize("region_type", {RT.ELLIPSE, RT.ANNELLIPSE})
def test_wcs_semi_axes(mocker, region, region_type):
    reg = region(region_type)
    mocker.patch("carta.region.Region.wcs_size", new_callable=mocker.PropertyMock, return_value=("20", "30"))

    semi_axes = reg.wcs_semi_axes

    assert semi_axes == ("20", "30")


@pytest.mark.parametrize("region_type", {RT.ELLIPSE, RT.ANNELLIPSE})
@pytest.mark.parametrize("semi_axes", [(20, 30), ("20", "30")])
def test_set_semi_axes(mocker, region, mock_from_angular, region_type, semi_axes):
    reg = region(region_type)
    mock_region_set_size = mocker.patch.object(Region, "set_size")

    reg.set_semi_axes(semi_axes)

    mock_region_set_size.assert_called_with((20, 30))


@pytest.mark.parametrize("method_name,value_name,mocked_value,expected_value", [
    ("point_shape", "pointShape", 2, PS.CIRCLE),
    ("point_width", "pointWidth", 5, 5),
])
def test_point_properties(region, get_value, method_name, value_name, mocked_value, expected_value):
    reg = region(RT.ANNPOINT)
    mock_value_getter = get_value(reg, mocked_value)
    value = getattr(reg, method_name)
    mock_value_getter.assert_called_with(value_name)
    assert value == expected_value


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([PS.CIRCLE, 5], {}, [("setPointShape", PS.CIRCLE), ("setPointWidth", 5)]),
    ([], {"point_shape": PS.CIRCLE}, [("setPointShape", PS.CIRCLE)]),
    ([], {"point_width": 5}, [("setPointWidth", 5)]),
])
def test_set_point_style(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region(RT.ANNPOINT)
    mock_action_caller = call_action(reg)
    reg.set_point_style(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("method_name,value_name,mocked_value,expected_value", [
    ("text", "text", "my text", "my text"),
    ("position", "position", 3, TP.LOWER_LEFT),
])
def test_text_properties(region, get_value, method_name, value_name, mocked_value, expected_value):
    reg = region(RT.ANNTEXT)
    mock_value_getter = get_value(reg, mocked_value)
    value = getattr(reg, method_name)
    mock_value_getter.assert_called_with(value_name)
    assert value == expected_value


def test_set_text(region, call_action):
    reg = region(RT.ANNTEXT)
    mock_action_caller = call_action(reg)
    reg.set_text("my text")
    mock_action_caller.assert_called_with("setText", "my text")


def test_set_text_position(region, call_action):
    reg = region(RT.ANNTEXT)
    mock_action_caller = call_action(reg)
    reg.set_text_position(TP.LOWER_LEFT)
    mock_action_caller.assert_called_with("setPosition", TP.LOWER_LEFT)


@pytest.mark.parametrize("method_name,value_names,mocked_values,expected_value", [
    ("labels", ["northLabel", "eastLabel"], ["N", "E"], ("N", "E")),
    ("point_length", ["length"], [100], 100),
    ("label_offsets", ["northTextOffset", "eastTextOffset"], [{"x": 1, "y": 2}, {"x": 3, "y": 4}], ((1, 2), (3, 4))),
    ("arrowheads_visible", ["northArrowhead", "eastArrowhead"], [True, False], (True, False)),
])
def test_compass_properties(region, mocker, method_name, value_names, mocked_values, expected_value):
    reg = region(RT.ANNCOMPASS)
    mock_value_getter = mocker.patch.object(reg, "get_value", side_effect=mocked_values)
    value = getattr(reg, method_name)
    mock_value_getter.assert_has_calls([mocker.call(name) for name in value_names])
    assert value == expected_value


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    (["N", "E"], {}, [("setLabel", "N", True), ("setLabel", "E", False),]),
    (["N"], {}, [("setLabel", "N", True)]),
    ([], {"east_label": "E"}, [("setLabel", "E", False)]),
])
def test_set_label(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region(RT.ANNCOMPASS)
    mock_action_caller = call_action(reg)
    reg.set_label(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("args,kwargs,expected_calls,error_contains", [
    ([100], {}, [("setLength", 100)], None),
    (["100", SA.X], {}, [("setLength", 100)], None),
    (["100"], {"spatial_axis": SA.X}, [("setLength", 100)], None),
    (["100"], {}, [], "Please specify a spatial axis"),
])
def test_set_point_length(mocker, region, call_action, image_method, args, kwargs, expected_calls, error_contains):
    reg = region(RT.ANNCOMPASS)
    mock_action_caller = call_action(reg)
    image_method("from_angular_size", [100])

    if error_contains is None:
        reg.set_point_length(*args, **kwargs)
        mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])
    else:
        with pytest.raises(ValueError) as e:
            reg.set_point_length(*args, **kwargs)
        assert error_contains in str(e.value)


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([(1, 2), (3, 4)], {}, [("setNorthTextOffset", 1, True), ("setNorthTextOffset", 2, False), ("setEastTextOffset", 3, True), ("setEastTextOffset", 4, False)]),
    ([(1, 2)], {}, [("setNorthTextOffset", 1, True), ("setNorthTextOffset", 2, False)]),
    ([], {"east_offset": (3, 4)}, [("setEastTextOffset", 3, True), ("setEastTextOffset", 4, False)]),
])
def test_set_label_offset(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region(RT.ANNCOMPASS)
    mock_action_caller = call_action(reg)
    reg.set_label_offset(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([True, False], {}, [("setNorthArrowhead", True), ("setEastArrowhead", False)]),
    ([True], {}, [("setNorthArrowhead", True)]),
    ([], {"east": False}, [("setEastArrowhead", False)]),
])
def test_set_arrowhead_visible(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region(RT.ANNCOMPASS)
    mock_action_caller = call_action(reg)
    reg.set_arrowhead_visible(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("method_name,value_name,mocked_value,expected_value", [
    ("auxiliary_lines_visible", "auxiliaryLineVisible", True, True),
    ("auxiliary_lines_dash_length", "auxiliaryLineDashLength", 5, 5),
    ("text_offset", "textOffset", {"x": 1, "y": 2}, (1, 2)),
])
def test_ruler_properties(region, get_value, method_name, value_name, mocked_value, expected_value):
    reg = region(RT.ANNRULER)
    mock_value_getter = get_value(reg, mocked_value)
    value = getattr(reg, method_name)
    mock_value_getter.assert_called_with(value_name)
    assert value == expected_value


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([True, 5], {}, [("setAuxiliaryLineVisible", True), ("setAuxiliaryLineDashLength", 5)]),
    ([True], {}, [("setAuxiliaryLineVisible", True)]),
    ([], {"dash_length": 5}, [("setAuxiliaryLineDashLength", 5)]),
])
def test_set_auxiliary_lines_style(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region(RT.ANNRULER)
    mock_action_caller = call_action(reg)
    reg.set_auxiliary_lines_style(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])


@pytest.mark.parametrize("args,kwargs,expected_calls", [
    ([], {}, []),
    ([1, 2], {}, [("setTextOffset", 1, True), ("setTextOffset", 2, False)]),
    ([1], {}, [("setTextOffset", 1, True)]),
    ([], {"offset_y": 2}, [("setTextOffset", 2, False)]),
])
def test_set_text_offset(mocker, region, call_action, args, kwargs, expected_calls):
    reg = region(RT.ANNRULER)
    mock_action_caller = call_action(reg)
    reg.set_text_offset(*args, **kwargs)
    mock_action_caller.assert_has_calls([mocker.call(*c) for c in expected_calls])
