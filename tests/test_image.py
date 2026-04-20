import pytest

from carta.image import Image, ImageBase
from carta.util import CartaActionFailed, CartaValidationFailed, Point as Pt
from carta.constants import ImageType, NumberFormat as NF, SpatialAxis as SA, PaletteColor as PC, BeamType as BT, SpectralSystem as SS, SpectralType as ST, SpectralUnit as SU


# FIXTURES


@pytest.fixture
def get_value(image, mock_get_value):
    return mock_get_value(image)


@pytest.fixture
def call_action(image, mock_call_action):
    return mock_call_action(image)


@pytest.fixture
def property_(image, mock_property):
    return mock_property("carta.image.Image")


@pytest.fixture
def method(image, mock_method):
    return mock_method(image)


@pytest.fixture
def session_call_action(session, mock_call_action):
    return mock_call_action(session)


@pytest.fixture
def session_get_value(session, mock_get_value):
    return mock_get_value(session)


@pytest.fixture
def session_method(session, mock_method):
    return mock_method(session)


# TESTS

# CREATING AN IMAGE

@pytest.mark.parametrize("args,kwargs,expected_params", [
    # Open a plain image
    (["subdir", "image.fits", "", False, False], {},
     ["openFile", "/my_data/subdir", "image.fits", "", False, False]),
    # Open an expression
    (["subdir", '2*image.fits', "", False, True], {},
     ["openFile", "/my_data/subdir", '2*image.fits', "", True, False]),
    # Append a plain image
    (["subdir", "image.fits", "", True, False], {},
     ["appendFile", "/my_data/subdir", "image.fits", "", False, True, False]),
    # Append an expression
    (["subdir", "2*image.fits", "", True, True], {},
     ["appendFile", "/my_data/subdir", "2*image.fits", "", True, True, False]),
    # Open a plain image; update the file browser directory
    (["subdir", "image.fits", "", False, False], {"update_directory": True},
     ["openFile", "/my_data/subdir", "image.fits", "", False, True]),
    # Append a plain image; don't set it to active
    (["subdir", "image.fits", "", True, False], {"make_active": False},
     ["appendFile", "/my_data/subdir", "image.fits", "", False, False, False]),
])
def test_new(session, session_call_action, session_method, args, kwargs, expected_params):
    session_method("pwd", ["/my_data"])
    session_call_action.side_effect = [123]

    image_object = Image.new(session, *args, **kwargs)

    session_call_action.assert_called_with(*expected_params, return_path='frameInfo.fileId')

    assert type(image_object) is Image
    assert image_object.session == session
    assert image_object.file_id == 123


# SUBOBJECTS


@pytest.mark.parametrize("name,classname", [
    ("raster", "Raster"),
    ("contours", "Contours"),
    ("vectors", "VectorOverlay"),
    ("wcs", "ImageWCSOverlay"),
    ("regions", "RegionSet"),
])
def test_subobjects(image, name, classname):
    assert getattr(image, name).__class__.__name__ == classname


# SIMPLE PROPERTIES TODO to be completed.

@pytest.mark.parametrize("property_name,expected_path", [
    ("file_name", "frameInfo.fileInfo.name"),
    ("directory", "frameInfo.directory"),
    ("width", "frameInfo.fileInfoExtended.width"),
])
def test_simple_properties(image, property_name, expected_path, get_value):
    getattr(image, property_name)
    get_value.assert_called_with(expected_path)

# TODO tests for all existing functions to be filled in


def test_make_active(image, session_call_action):
    image.make_active()
    session_call_action.assert_called_with(
        "setActiveImageById", ImageType.FRAME, 0
    )


def test_image_base_image_view_order_not_implemented(session):
    base = ImageBase(session)
    with pytest.raises(NotImplementedError):
        base.image_view_order


def test_image_base_stable_id_not_implemented(session):
    base = ImageBase(session)
    with pytest.raises(NotImplementedError):
        base._stable_id


def test_image_base_make_active_uses_subclass_ids(session, session_call_action):
    # Verify the shared ImageBase.make_active dispatches setActiveImageById
    # with the subclass's _image_type and _stable_id exactly once.
    class Dummy(ImageBase):
        _image_type = ImageType.FRAME

        def __init__(self, session, id_):
            super().__init__(session)
            self._id = id_

        @property
        def _stable_id(self):
            return self._id

    Dummy(session, 42).make_active()
    session_call_action.assert_called_once_with(
        "setActiveImageById", ImageType.FRAME, 42
    )


def test_image_view_order_uses_summary_once(session, mocker, image):
    find = mocker.patch.object(
        session, "_find_image_view_order", return_value=3
    )
    # Frame with file_id=0 at viewer order 3.
    assert image.image_view_order == 3
    find.assert_called_once_with(ImageType.FRAME, 0)


def test_image_view_order_ignores_non_frame_entries(session, mocker):
    get_value = mocker.patch.object(
        session,
        "get_value",
        return_value=[
            {"type": ImageType.COLOR_BLENDING, "id": 0},
            {"type": ImageType.FRAME, "id": 7},
            {"type": ImageType.FRAME, "id": 3},
        ],
    )
    img = Image(session, 3)
    assert img.image_view_order == 2
    get_value.assert_called_once_with("imageViewConfigStore.imageListSummary")


def test_image_view_order_raises_when_missing(session, mocker):
    mocker.patch.object(
        session,
        "get_value",
        return_value=[{"type": ImageType.FRAME, "id": 99}],
    )
    img = Image(session, 3)
    with pytest.raises(RuntimeError):
        img.image_view_order


def test_image_repr_cached_name_resolves_only_image_view_order(session, image, mocker):
    mocker.patch.object(session, "_find_image_view_order", return_value=3)
    get_value = mocker.patch.object(image, "get_value")
    image._cache = {"file_name": "cube.fits"}
    r = repr(image)
    assert r == "Image(image_view_order=3, file_name='cube.fits', file_id=0)"
    get_value.assert_not_called()


def test_image_repr_resolves_image_view_order_and_file_name(session, image, mocker):
    mocker.patch.object(session, "_find_image_view_order", return_value=3)
    mocker.patch.object(image, "get_value", return_value="cube.fits")
    r = repr(image)
    assert r == "Image(image_view_order=3, file_name='cube.fits', file_id=0)"


def test_image_repr_closed_when_image_view_order_missing(session, image, mocker):
    mocker.patch.object(
        session,
        "_find_image_view_order",
        side_effect=RuntimeError("not in image list"),
    )
    r = repr(image)
    assert r == "[Closed] Image(image_view_order=None, file_id=0)"


def test_image_repr_closed_shows_cached_file_name(session, image, mocker):
    # When the image-view-order lookup fails but file_name was previously
    # cached, the closed repr still surfaces the cached name without
    # triggering any fresh round-trip.
    mocker.patch.object(
        session,
        "_find_image_view_order",
        side_effect=RuntimeError("not in image list"),
    )
    get_value = mocker.patch.object(image, "get_value")
    image._cache = {"file_name": "cube.fits"}
    r = repr(image)
    assert r == "[Closed] Image(image_view_order=None, file_name='cube.fits', file_id=0)"
    get_value.assert_not_called()


def test_image_repr_closed_when_frame_is_gone(session, image, mocker):
    mocker.patch.object(session, "_find_image_view_order", return_value=3)
    mocker.patch.object(
        image,
        "get_value",
        side_effect=CartaActionFailed("frameMap entry is missing"),
    )
    r = repr(image)
    assert r == "[Closed] Image(image_view_order=3, file_id=0)"


@pytest.mark.parametrize("channel", [0, 10, 19])
def test_set_channel_valid(image, channel, call_action, property_):
    property_("depth", 20)

    image.set_channel(channel)
    call_action.assert_called_with("setChannels", channel, image.macro("", "requiredStokes"), True)


@pytest.mark.parametrize("channel,error_contains", [
    (20, "must be smaller"),
    (1.5, "not an increment of 1"),
    (-3, "must be greater or equal"),
])
def test_set_channel_invalid(image, channel, error_contains, property_):
    property_("depth", 20)

    with pytest.raises(CartaValidationFailed) as e:
        image.set_channel(channel)
    assert error_contains in str(e.value)


@pytest.mark.parametrize("x", [-30, 0, 10, 12.3, 30])
@pytest.mark.parametrize("y", [-30, 0, 10, 12.3, 30])
def test_set_center_valid_pixels(image, property_, call_action, x, y):
    # Currently we have no range validation, for consistency with WCS coordinates.
    property_("width", 20)
    property_("height", 20)

    image.set_center(x, y)
    call_action.assert_called_with("setCenter", x, y)


@pytest.mark.parametrize("x,y,x_fmt,y_fmt,x_norm,y_norm", [
    ("123", "12", NF.DEGREES, NF.DEGREES, "123", "12"),
    ("123deg", "12 deg", NF.DEGREES, NF.DEGREES, "123", "12"),
    ("12:34:56.789", "12:34:56.789", NF.HMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
    ("12h34m56.789s", "12d34m56.789s", NF.HMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
    ("12h34m56.789s", "5h34m56.789s", NF.HMS, NF.HMS, "12:34:56.789", "5:34:56.789"),
    ("12d34m56.789s", "12d34m56.789s", NF.DMS, NF.DMS, "12:34:56.789", "12:34:56.789"),
])
def test_set_center_valid_wcs(image, property_, mock_property, call_action, x, y, x_fmt, y_fmt, x_norm, y_norm):
    property_("valid_wcs", True)
    mock_property("carta.wcs_overlay.Numbers")("format", (x_fmt, y_fmt))

    image.set_center(x, y)
    call_action.assert_called_with("setCenterWcs", x_norm, y_norm)


@pytest.mark.parametrize("x,y,wcs,x_fmt,y_fmt,error_contains", [
    ("abc", "def", True, NF.DEGREES, NF.DEGREES, "Invalid function parameter"),
    ("123", "123", False, NF.DEGREES, NF.DEGREES, "does not contain valid WCS information"),
    ("123", "123", True, NF.HMS, NF.DMS, "does not match expected format"),
    ("123", "123", True, NF.DEGREES, NF.DMS, "does not match expected format"),
    (123, "123", True, NF.DEGREES, NF.DEGREES, "Cannot mix image and world coordinates"),
    ("123", 123, True, NF.DEGREES, NF.DEGREES, "Cannot mix image and world coordinates"),
])
def test_set_center_invalid(image, property_, mock_property, call_action, x, y, wcs, x_fmt, y_fmt, error_contains):
    property_("width", 200)
    property_("height", 200)
    property_("valid_wcs", wcs)
    mock_property("carta.wcs_overlay.Numbers")("format", (x_fmt, y_fmt))

    with pytest.raises(Exception) as e:
        image.set_center(x, y)
    assert error_contains in str(e.value)


@pytest.mark.parametrize("axis", [SA.X, SA.Y])
@pytest.mark.parametrize("val,action,norm", [
    (123, "zoomToSize{0}", 123.0),
    ("123arcsec", "zoomToSize{0}Wcs", "123\""),
    ("123\"", "zoomToSize{0}Wcs", "123\""),
    ("123", "zoomToSize{0}Wcs", "123\""),
    ("123arcmin", "zoomToSize{0}Wcs", "123'"),
    ("123deg", "zoomToSize{0}Wcs", "123deg"),
    ("123 deg", "zoomToSize{0}Wcs", "123deg"),
])
def test_zoom_to_size(image, property_, call_action, axis, val, action, norm):
    property_("valid_wcs", True)
    image.zoom_to_size(val, axis)
    call_action.assert_called_with(action.format(axis.upper()), norm)


@pytest.mark.parametrize("axis", [SA.X, SA.Y])
@pytest.mark.parametrize("val,wcs,error_contains", [
    ("123px", True, "Invalid function parameter"),
    ("abc", True, "Invalid function parameter"),
    ("123arcsec", False, "does not contain valid WCS information"),
])
def test_zoom_to_size_invalid(image, property_, axis, val, wcs, error_contains):
    property_("valid_wcs", wcs)
    with pytest.raises(Exception) as e:
        image.zoom_to_size(val, axis)
    assert error_contains in str(e.value)


def test_from_world_coordinate_points(image, call_action):
    call_action.return_value = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}]
    points = image.from_world_coordinate_points([("1", "2"), ("3", "4"), ("5", "6")])
    call_action.assert_called_with("getImagePosFromWCS", [Pt("1", "2"), Pt("3", "4"), Pt("5", "6")])
    assert points == [(1, 2), (3, 4), (5, 6)]


def test_from_world_coordinate_points_invalid(image):
    with pytest.raises(CartaValidationFailed) as e:
        image.from_world_coordinate_points([(1, 2), (3, 4), (5, 6)])
    assert "not a pair of coordinate strings" in str(e.value)


def test_to_world_coordinate_points(image, call_action):
    call_action.return_value = [{"x": "1", "y": "2"}, {"x": "3", "y": "4"}, {"x": "5", "y": "6"}]
    points = image.to_world_coordinate_points([(1, 2), (3, 4), (5, 6)])
    call_action.assert_called_with("getWCSFromImagePos", [Pt(1, 2), Pt(3, 4), Pt(5, 6)])
    assert points == [("1", "2"), ("3", "4"), ("5", "6")]


def test_to_world_coordinate_points_invalid(image):
    with pytest.raises(CartaValidationFailed) as e:
        image.to_world_coordinate_points([("1", "2"), ("3", "4"), ("5", "6")])
    assert "not a pair of numbers" in str(e.value)


@pytest.mark.parametrize("size,axis,expected_call", [
    ("100\"", SA.X, ("getImageXValueFromArcsec", 100)),
    ("100\"", SA.Y, ("getImageYValueFromArcsec", 100)),
])
def test_from_angular_size(image, call_action, size, axis, expected_call):
    image.from_angular_size(size, axis)
    call_action.assert_called_with(*expected_call)


@pytest.mark.parametrize("size,error_contains", [
    (100, "a string was expected"),
    ("100abc", "not an angular size"),
])
def test_from_angular_size_invalid(image, size, error_contains):
    with pytest.raises(CartaValidationFailed) as e:
        image.from_angular_size(size, SA.X)
    assert error_contains in str(e.value)


def test_from_angular_size_points(mocker, image, method):
    mock_from_angular_size = method("from_angular_size", [1, 2, 3, 4])
    points = image.from_angular_size_points([("1", "2"), ("3", "4")])
    mock_from_angular_size.assert_has_calls([
        mocker.call("1", SA.X),
        mocker.call("2", SA.Y),
        mocker.call("3", SA.X),
        mocker.call("4", SA.Y),
    ])
    assert points == [(1, 2), (3, 4)]


def test_to_angular_size_points(mocker, image, call_action):
    call_action.side_effect = [{"x": "1", "y": "2"}, {"x": "3", "y": "4"}]
    points = image.to_angular_size_points([(1, 2), (3, 4)])
    call_action.assert_has_calls([
        mocker.call("getWcsSizeInArcsec", Pt(1, 2)),
        mocker.call("getWcsSizeInArcsec", Pt(3, 4)),
    ])
    assert points == [("1", "2"), ("3", "4")]


# PER-IMAGE WCS

def test_set_custom_colorbar_label(session, image, call_action, mock_method):
    label_set_custom_text = mock_method(session.wcs.colorbar.label)("set_custom_text", None)
    image.wcs.colorbar.label.set_text("Custom text here!")
    call_action.assert_called_with("setColorbarLabelCustomText", "Custom text here!")
    label_set_custom_text.assert_called_with(True)


def test_colorbar_label(image, get_value):
    get_value.side_effect = ["Custom text here!"]
    text = image.wcs.colorbar.label.text
    get_value.assert_called_with("colorbarLabelCustomText")
    assert text == "Custom text here!"


def test_set_custom_title(session, image, call_action, mock_method):
    title_set_custom_text = mock_method(session.wcs.title)("set_custom_text", None)
    image.wcs.title.set_text("Custom text here!")
    call_action.assert_called_with("setTitleCustomText", "Custom text here!")
    title_set_custom_text.assert_called_with(True)


def test_title(image, get_value):
    get_value.side_effect = ["Custom text here!"]
    text = image.wcs.title.text
    get_value.assert_called_with("titleCustomText")
    assert text == "Custom text here!"


def test_beam_set_position(mocker, image, session_call_action):
    image.wcs.beam.set_position(2, 3)
    session_call_action.assert_has_calls([
        mocker.call("frameMap[0].overlayBeamSettings.setShiftX", 2),
        mocker.call("frameMap[0].overlayBeamSettings.setShiftY", 3),
    ])


def test_beam_position(mocker, image, session_get_value):
    session_get_value.side_effect = [2, 3]
    pos_x, pos_y = image.wcs.beam.position
    session_get_value.assert_has_calls([
        mocker.call("frameMap[0].overlayBeamSettings.shiftX", return_path=None),
        mocker.call("frameMap[0].overlayBeamSettings.shiftY", return_path=None),
    ])
    assert pos_x == 2
    assert pos_y == 3


def test_beam_set_type(image, session_call_action):
    image.wcs.beam.set_type(BT.SOLID)
    session_call_action.assert_called_with("frameMap[0].overlayBeamSettings.setType", BT.SOLID)


def test_beam_type(image, session_get_value):
    session_get_value.side_effect = ["solid"]
    beam_type = image.wcs.beam.type
    session_get_value.assert_called_with("frameMap[0].overlayBeamSettings.type", return_path=None)
    assert beam_type is BT.SOLID


def test_beam_set_color(image, session_call_action):
    image.wcs.beam.set_color(PC.ROSE)
    session_call_action.assert_called_with("frameMap[0].overlayBeamSettings.setColor", PC.ROSE)


def test_beam_color(image, session_get_value):
    session_get_value.side_effect = ["auto-rose"]
    color = image.wcs.beam.color
    session_get_value.assert_called_with("frameMap[0].overlayBeamSettings.color", return_path=None)
    assert color is PC.ROSE


def test_beam_set_visible(image, session_call_action):
    image.wcs.beam.set_visible(True)
    session_call_action.assert_called_with("frameMap[0].overlayBeamSettings.setVisible", True)


def test_beam_show_hide(mocker, image, session_call_action):
    image.wcs.beam.show()
    image.wcs.beam.hide()
    session_call_action.assert_has_calls([
        mocker.call("frameMap[0].overlayBeamSettings.setVisible", True),
        mocker.call("frameMap[0].overlayBeamSettings.setVisible", False),
    ])


def test_beam_visible(image, session_get_value):
    session_get_value.side_effect = [True]
    visible = image.wcs.beam.visible
    session_get_value.assert_called_with("frameMap[0].overlayBeamSettings.visible", return_path=None)
    assert visible


def test_beam_set_width(image, session_call_action):
    image.wcs.beam.set_width(2)
    session_call_action.assert_called_with("frameMap[0].overlayBeamSettings.setWidth", 2)


def test_beam_width(image, session_get_value):
    session_get_value.side_effect = [2]
    width = image.wcs.beam.width
    session_get_value.assert_called_with("frameMap[0].overlayBeamSettings.width", return_path=None)
    assert width == 2


def test_spectral_systems_supported(image, get_value):
    get_value.side_effect = [{"LSRK", "LSRD"}]
    systems = image.spectral_systems_supported
    get_value.assert_called_with("spectralSystemsSupported")
    assert systems == {SS.LSRK, SS.LSRD}


def test_spectral_coordinate_types_supported(image, get_value):
    get_value.side_effect = [{"one": {'type': 'AWAV', 'unit': 'Angstrom'}, "two": {'type': 'AWAV', 'unit': 'm'}, "three": {'type': 'FREQ', 'unit': 'GHz'}}]
    types = image.spectral_coordinate_types_supported
    get_value.assert_called_with("spectralCoordsSupported")
    assert types == {ST.AWAV, ST.FREQ}


def test_set_spectral_system(image, property_, call_action):
    property_("is_pv", True)
    property_("spectral_systems_supported", {SS.LSRK, SS.LSRD})
    image.set_spectral_system(SS.LSRK)
    call_action.assert_called_with("setSpectralSystem", SS.LSRK)


def test_set_spectral_system_no_pv(image, property_):
    property_("is_pv", False)
    with pytest.raises(ValueError) as e:
        image.set_spectral_system(SS.LSRK)
    assert "not a position-velocity image" in str(e.value)


def test_set_spectral_system_bad_system(image, property_):
    property_("is_pv", True)
    property_("spectral_systems_supported", {SS.LSRK, SS.LSRD})
    with pytest.raises(ValueError) as e:
        image.set_spectral_system(SS.BARY)
    assert "Unsupported system: BARYCENT" in str(e.value)


def test_set_spectral_coordinate(image, property_, call_action):
    property_("is_pv", True)
    property_("spectral_coordinate_types_supported", {ST.VRAD, ST.VOPT})
    image.set_spectral_coordinate(ST.VRAD, SU.MS)
    call_action.assert_called_with("setSpectralCoordinate", "Radio velocity (m/s)")


def test_set_spectral_coordinate_default_unit(image, property_, call_action):
    property_("is_pv", True)
    property_("spectral_coordinate_types_supported", {ST.VRAD, ST.VOPT})
    image.set_spectral_coordinate(ST.VRAD)
    call_action.assert_called_with("setSpectralCoordinate", "Radio velocity (km/s)")


def test_set_spectral_coordinate_no_pv(image, property_):
    property_("is_pv", False)
    with pytest.raises(ValueError) as e:
        image.set_spectral_coordinate(ST.VRAD)
    assert "not a position-velocity image" in str(e.value)


def test_set_spectral_coordinate_bad_type(image, property_):
    property_("is_pv", True)
    property_("spectral_coordinate_types_supported", {ST.VRAD, ST.VOPT})
    with pytest.raises(ValueError) as e:
        image.set_spectral_coordinate(ST.FREQ)
    assert "Unsupported type: Frequency" in str(e.value)


def test_set_spectral_coordinate_bad_unit(image, property_):
    property_("is_pv", True)
    property_("spectral_coordinate_types_supported", {ST.VRAD, ST.VOPT})
    with pytest.raises(ValueError) as e:
        image.set_spectral_coordinate(ST.VRAD, SU.HZ)
    assert "Unsupported unit: Hz" in str(e.value)
