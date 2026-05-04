import pytest

from carta.color_blending import ColorBlending, Layer
from carta.constants import Colormap as CM
from carta.constants import ColormapSet as CMS
from carta.constants import ImageType
from carta.constants import SpatialAxis as SA
from carta.image import Image
from carta.util import CartaActionFailed, CartaValidationFailed, Macro

# FIXTURES


@pytest.fixture
def color_blending(session):
    return ColorBlending(session, 0)


@pytest.fixture
def layer(color_blending):
    return Layer(color_blending, 1)


@pytest.fixture
def cb_get_value(color_blending, mock_get_value):
    return mock_get_value(color_blending)


@pytest.fixture
def cb_call_action(color_blending, mock_call_action):
    return mock_call_action(color_blending)


@pytest.fixture
def layer_get_value(layer, mock_get_value):
    return mock_get_value(layer)


@pytest.fixture
def layer_call_action(layer, mock_call_action):
    return mock_call_action(layer)


@pytest.fixture
def session_call_action(session, mock_call_action):
    return mock_call_action(session)


@pytest.fixture
def session_get_value(session, mock_get_value):
    return mock_get_value(session)


@pytest.fixture
def cb_property(mock_property):
    return mock_property("carta.color_blending.ColorBlending")


@pytest.fixture
def layer_property(mock_property):
    return mock_property("carta.color_blending.Layer")


# TESTS — Layer


def test_layer_from_list(color_blending):
    layers = Layer.from_list(color_blending, [5, 6, 7])
    assert [ly.layer_id for ly in layers] == [5, 6, 7]
    assert all(ly.color_blending is color_blending for ly in layers)


def test_layer_repr_healthy(session, color_blending, layer_property, mocker):
    find = mocker.patch.object(session, "_find_image_view_order", return_value=2)
    layer_property("file_id", 42)
    layer_property("file_name", "layer1.fits")
    r = repr(Layer(color_blending, 3))
    assert r == (
        "Layer(image_view_order=2, color_blending_id=0, layer_id=3, "
        "file_name='layer1.fits')"
    )
    find.assert_called_once_with(ImageType.FRAME, 42)


def test_layer_repr_closed_when_frame_not_in_image_list(
    session, color_blending, layer_property, mocker
):
    layer_property("file_id", 42)
    mocker.patch.object(
        session,
        "_find_image_view_order",
        side_effect=RuntimeError("not in image list"),
    )
    r = repr(Layer(color_blending, 3))
    assert r == (
        "[Closed] Layer(image_view_order=None, color_blending_id=0, "
        "layer_id=3)"
    )


def test_layer_repr_closed_when_frame_is_gone(session, color_blending, mocker):
    mocker.patch(
        "carta.color_blending.Layer.file_id",
        new_callable=mocker.PropertyMock,
        side_effect=CartaActionFailed("frame is gone"),
    )
    r = repr(Layer(color_blending, 3))
    assert r == (
        "[Closed] Layer(image_view_order=None, color_blending_id=0, "
        "layer_id=3)"
    )


def test_layer_repr_closed_when_file_name_read_fails(
    session, color_blending, layer_property, mocker
):
    mocker.patch.object(session, "_find_image_view_order", return_value=2)
    layer_property("file_id", 42)
    mocker.patch(
        "carta.color_blending.Layer.file_name",
        new_callable=mocker.PropertyMock,
        side_effect=CartaActionFailed("file_name read failed"),
    )
    r = repr(Layer(color_blending, 3))
    assert r == (
        "[Closed] Layer(image_view_order=2, color_blending_id=0, "
        "layer_id=3)"
    )


def test_layer_file_name_property(layer, layer_get_value):
    layer.file_name
    layer_get_value.assert_called_with("frameInfo.fileInfo.name")


def test_layer_file_id_property(layer, layer_get_value):
    layer.file_id
    layer_get_value.assert_called_with("frameInfo.fileId")


def test_layer_image_view_order(session, color_blending, layer_property, mocker):
    find = mocker.patch.object(session, "_find_image_view_order", return_value=7)
    layer_property("file_id", 42)
    assert Layer(color_blending, 3).image_view_order == 7
    find.assert_called_once_with(ImageType.FRAME, 42)


def test_layer_image_view_order_raises_when_frame_not_in_image_list(
    session, color_blending, layer_property, mocker
):
    layer_property("file_id", 42)
    mocker.patch.object(
        session,
        "_find_image_view_order",
        side_effect=RuntimeError("not in image list"),
    )
    with pytest.raises(RuntimeError):
        Layer(color_blending, 3).image_view_order


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
def test_layer_set_alpha_valid(color_blending, alpha, cb_call_action):
    Layer(color_blending, 2).set_alpha(alpha)
    cb_call_action.assert_called_with("setAlpha", 2, alpha)


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_layer_set_alpha_invalid(color_blending, alpha):
    with pytest.raises(CartaValidationFailed):
        Layer(color_blending, 2).set_alpha(alpha)


@pytest.mark.parametrize("invert", [True, False])
def test_layer_set_colormap(layer, layer_call_action, invert):
    layer.set_colormap(CM.VIRIDIS, invert)
    layer_call_action.assert_any_call("renderConfig.setColorMap", CM.VIRIDIS)
    layer_call_action.assert_any_call("renderConfig.setInverted", invert)


def test_layer_set_colormap_invalid_colormap(layer, layer_call_action):
    with pytest.raises(CartaValidationFailed):
        layer.set_colormap("not-a-colormap")

    layer_call_action.assert_not_called()


# TESTS — ColorBlending basics


def test_color_blending_init(session):
    color_blending = ColorBlending(session, 3)
    assert color_blending.color_blending_id == 3
    expected = "imageViewConfigStore.colorBlendingImageMap[3]"
    assert color_blending._base_path == expected
    assert color_blending._frame == Macro(
        "", "imageViewConfigStore.colorBlendingImageMap[3]"
    )


def test_color_blending_repr_healthy(session, color_blending, cb_property, mocker):
    mocker.patch.object(session, "call_action", return_value=2)
    cb_property("file_name", "Color Blending 1")
    r = repr(color_blending)
    assert r == (
        "ColorBlending(image_view_order=2, color_blending_id=0, "
        "file_name='Color Blending 1')"
    )


def test_color_blending_repr_closed_when_not_in_image_list(
    session, color_blending, mocker
):
    mocker.patch.object(
        session,
        "call_action",
        side_effect=RuntimeError("not in image list"),
    )
    r = repr(color_blending)
    assert r == (
        "[Closed] ColorBlending(image_view_order=None, color_blending_id=0)"
    )


def test_color_blending_repr_closed_when_backing_entry_is_gone(
    session, color_blending, mocker
):
    mocker.patch.object(session, "call_action", return_value=2)
    mocker.patch(
        "carta.color_blending.ColorBlending.file_name",
        new_callable=mocker.PropertyMock,
        side_effect=CartaActionFailed("color blending is gone"),
    )
    r = repr(color_blending)
    assert r == (
        "[Closed] ColorBlending(image_view_order=2, color_blending_id=0)"
    )


def test_color_blending_file_name(color_blending, cb_get_value):
    color_blending.file_name
    cb_get_value.assert_called_with("filename")


def test_color_blending_image_view_order(
    session, color_blending, session_call_action
):
    session_call_action.return_value = 2
    assert color_blending.image_view_order == 2
    session_call_action.assert_called_once_with(
        "imageViewConfigStore.getImageListIndex",
        ImageType.COLOR_BLENDING,
        0,
        response_expected=True,
    )


def test_color_blending_image_view_order_raises_when_missing(
    session, color_blending, session_call_action
):
    session_call_action.return_value = -1
    with pytest.raises(RuntimeError):
        color_blending.image_view_order


def test_color_blending_alpha(color_blending, cb_get_value):
    color_blending.alpha
    cb_get_value.assert_called_with("alpha")


def test_color_blending_base_frame(color_blending, cb_get_value):
    cb_get_value.return_value = 42
    base_frame = color_blending._base_frame

    cb_get_value.assert_called_once_with("frames[0].id")
    assert isinstance(base_frame, Image)
    assert base_frame.session is color_blending.session
    assert base_frame.file_id == 42


def test_color_blending_make_active(session, color_blending, session_call_action):
    # make_active must be driven by color_blending_id via setActiveImageById.
    # It must not depend on image_view_order (which is volatile).
    color_blending.make_active()
    session_call_action.assert_called_with(
        "setActiveImageById", ImageType.COLOR_BLENDING, 0
    )


def test_color_blending_make_active_does_not_read_image_view_order(
    session, color_blending, session_call_action, session_get_value
):
    color_blending.make_active()
    for call in session_get_value.call_args_list:
        assert call.args != ("imageViewConfigStore.imageListSummary",)


def test_color_blending_layer_list_derived(session, mocker):
    cb = ColorBlending(session, 3)

    # Simulate two layers from the frontend's computed frames array length.
    gv = mocker.patch.object(cb, "get_value")
    gv.return_value = 2

    layers = cb.layer_list()
    assert [ly.layer_id for ly in layers] == [0, 1]
    gv.assert_called_once_with("frames.length")


def test_color_blending_add_layer(color_blending, cb_call_action, image):
    color_blending.add_layer(image)
    cb_call_action.assert_called_with("addSelectedFrame", image._frame)


@pytest.mark.parametrize("idx,expected_param", [(1, 0), (3, 2)])
def test_color_blending_delete_layer(
    color_blending, cb_call_action, idx, expected_param
):
    color_blending.delete_layer(idx)
    cb_call_action.assert_called_with("deleteSelectedFrame", expected_param)


def test_color_blending_delete_layer_rejects_base_layer(
    color_blending, cb_call_action
):
    with pytest.raises(ValueError, match="The base layer cannot be deleted."):
        color_blending.delete_layer(0)

    cb_call_action.assert_not_called()


@pytest.mark.parametrize("idx,expected_param", [(1, 0), (5, 4)])
def test_color_blending_set_layer(
    color_blending, cb_call_action, image, idx, expected_param
):
    color_blending.set_layer(image, idx)
    cb_call_action.assert_called_with(
        "setSelectedFrame", expected_param, image._frame
    )


class _L:
    def __init__(self, lid, fid):
        self.layer_id = lid
        self.file_id = fid


def test_color_blending_set_layer_sequence(session, color_blending, mocker):
    # Prepare three existing layers with file_ids 10, 20, 30
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )
    mocker.patch(
        "carta.color_blending.ColorBlending.alpha",
        new_callable=mocker.PropertyMock,
        return_value=[1.0, 0.2, 0.8],
    )
    del_layer = mocker.patch.object(color_blending, "delete_layer")
    add_layer = mocker.patch.object(color_blending, "add_layer")
    set_alpha = mocker.patch.object(Layer, "set_alpha", autospec=True)

    color_blending.set_layer_sequence([0, 2, 1])

    # Deletes all non-base layers (twice) then adds layers in specified order
    assert del_layer.call_count == 2
    add_args = [call.args[0] for call in add_layer.call_args_list]
    assert [img.file_id for img in add_args] == [30, 20]
    assert [call.args[1] for call in set_alpha.call_args_list] == [0.8, 0.2]


def test_color_blending_set_layer_sequence_noop_when_order_is_unchanged(
    color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )
    mocker.patch(
        "carta.color_blending.ColorBlending.alpha",
        new_callable=mocker.PropertyMock,
        side_effect=AssertionError("alpha should not be read"),
    )
    del_layer = mocker.patch.object(color_blending, "delete_layer")
    add_layer = mocker.patch.object(color_blending, "add_layer")
    set_alpha = mocker.patch.object(Layer, "set_alpha", autospec=True)

    color_blending.set_layer_sequence([0, 1, 2])

    del_layer.assert_not_called()
    add_layer.assert_not_called()
    set_alpha.assert_not_called()


def test_color_blending_set_layer_sequence_supports_user_specified_subset_order(
    session, color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30), _L(3, 40)],
    )
    mocker.patch(
        "carta.color_blending.ColorBlending.alpha",
        new_callable=mocker.PropertyMock,
        return_value=[1.0, 0.2, 0.8, 0.4],
    )
    del_layer = mocker.patch.object(color_blending, "delete_layer")
    add_layer = mocker.patch.object(color_blending, "add_layer")
    set_alpha = mocker.patch.object(Layer, "set_alpha", autospec=True)

    color_blending.set_layer_sequence([0, 3, 1])

    assert del_layer.call_count == 3
    assert [call.args[0].file_id for call in add_layer.call_args_list] == [40, 20]
    assert [call.args[1] for call in set_alpha.call_args_list] == [0.4, 0.2]


def test_color_blending_set_layer_sequence_rejects_missing_layer_index(
    session, color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30), _L(3, 40)],
    )

    with pytest.raises(ValueError) as e:
        color_blending.set_layer_sequence([0, 4, 1])
    assert "layer_indices [0, 4, 1]" in str(e.value)
    assert "[4]" in str(e.value)
    assert "0..3" in str(e.value)


def test_color_blending_set_layer_sequence_requires_base_layer_first(
    session, color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )

    with pytest.raises(ValueError) as e:
        color_blending.set_layer_sequence([2, 1])
    assert "layer_indices [2, 1]" in str(e.value)
    assert "must start with the base layer index 0" in str(e.value)


def test_color_blending_set_layer_sequence_rejects_duplicate_base_layer(
    session, color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )

    with pytest.raises(ValueError) as e:
        color_blending.set_layer_sequence([0, 2, 0])
    assert "layer_indices [0, 2, 0]" in str(e.value)
    assert "must contain the base layer index 0 only once" in str(e.value)


def test_color_blending_set_layer_sequence_rejects_duplicate_non_base_layer(
    session, color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )

    with pytest.raises(ValueError) as e:
        color_blending.set_layer_sequence([0, 1, 1])
    assert "layer_indices [0, 1, 1]" in str(e.value)
    assert "must not contain duplicate layer indices" in str(e.value)
    assert "[1]" in str(e.value)


def test_color_blending_set_center(color_blending, mocker):
    base_frame = mocker.create_autospec(Image, instance=True)
    mocker.patch(
        "carta.color_blending.ColorBlending._base_frame",
        new_callable=mocker.PropertyMock,
        return_value=base_frame,
    )

    color_blending.set_center(1, 2)
    base_frame.set_center.assert_called_once_with(1, 2)


@pytest.mark.parametrize("size,axis", [(123, SA.X), ("123arcsec", SA.Y)])
def test_color_blending_zoom_to_size(color_blending, mocker, size, axis):
    base_frame = mocker.create_autospec(Image, instance=True)
    mocker.patch(
        "carta.color_blending.ColorBlending._base_frame",
        new_callable=mocker.PropertyMock,
        return_value=base_frame,
    )

    color_blending.zoom_to_size(size, axis)
    base_frame.zoom_to_size.assert_called_once_with(size, axis)


@pytest.mark.parametrize("size,axis", [("123px", SA.X), (123, "z")])
def test_color_blending_zoom_to_size_invalid(color_blending, mocker, size, axis):
    base_frame = mocker.create_autospec(Image, instance=True)
    mocker.patch(
        "carta.color_blending.ColorBlending._base_frame",
        new_callable=mocker.PropertyMock,
        return_value=base_frame,
    )

    with pytest.raises(CartaValidationFailed):
        color_blending.zoom_to_size(size, axis)

    base_frame.zoom_to_size.assert_not_called()


@pytest.mark.parametrize("zoom,absolute", [(2, True), (3.5, False)])
def test_color_blending_set_zoom_level(color_blending, mocker, zoom, absolute):
    base_frame = mocker.create_autospec(Image, instance=True)
    mocker.patch(
        "carta.color_blending.ColorBlending._base_frame",
        new_callable=mocker.PropertyMock,
        return_value=base_frame,
    )

    color_blending.set_zoom_level(zoom, absolute)
    base_frame.set_zoom_level.assert_called_once_with(zoom, absolute)


def test_color_blending_set_colormap_set(color_blending, cb_call_action):
    color_blending.set_colormap_set(CMS.RAINBOW)
    cb_call_action.assert_called_with("applyColormapSet", CMS.RAINBOW)


def test_color_blending_set_alpha_valid(color_blending, mocker):
    ly1 = mocker.create_autospec(Layer(color_blending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(color_blending, 2), instance=True)
    mocker.patch.object(ColorBlending, "layer_list", return_value=[ly1, ly2])

    color_blending.set_alpha([0.2, 0.8])
    ly1.set_alpha.assert_called_with(0.2)
    ly2.set_alpha.assert_called_with(0.8)


@pytest.mark.parametrize("vals", [[-0.1, 0.5], [1.2], [0.1, 2.0, 0.3]])
def test_color_blending_set_alpha_invalid(color_blending, vals):
    with pytest.raises(CartaValidationFailed):
        color_blending.set_alpha(vals)


@pytest.mark.parametrize("vals", [[0.5], [0.1, 0.2, 0.3]])
def test_color_blending_set_alpha_length_mismatch(color_blending, mocker, vals):
    ly1 = mocker.create_autospec(Layer(color_blending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(color_blending, 2), instance=True)
    mocker.patch.object(ColorBlending, "layer_list", return_value=[ly1, ly2])

    with pytest.raises(ValueError, match="does not match"):
        color_blending.set_alpha(vals)


@pytest.mark.parametrize(
    "getter,method,action,state",
    [
        ("rasterVisible", "set_raster_visible", "toggleRasterVisible", True),
        (
            "contourVisible",
            "set_contour_visible",
            "toggleContourVisible",
            True,
        ),
        (
            "vectorOverlayVisible",
            "set_vector_overlay_visible",
            "toggleVectorOverlayVisible",
            False,
        ),
    ],
)
def test_color_blending_toggle_visibility_when_needed(
    color_blending, cb_get_value, cb_call_action, getter, method, action, state
):
    # Current state opposite to desired -> should toggle
    cb_get_value.side_effect = [not state]
    getattr(color_blending, method)(state)
    cb_call_action.assert_called_with(action)


@pytest.mark.parametrize(
    "getter,method,action,state",
    [
        ("rasterVisible", "set_raster_visible", "toggleRasterVisible", True),
        (
            "contourVisible",
            "set_contour_visible",
            "toggleContourVisible",
            False,
        ),
        (
            "vectorOverlayVisible",
            "set_vector_overlay_visible",
            "toggleVectorOverlayVisible",
            True,
        ),
    ],
)
def test_color_blending_toggle_visibility_noop(
    color_blending, cb_get_value, cb_call_action, getter, method, action, state
):
    # Current state equals desired -> no toggle
    cb_get_value.side_effect = [state]
    getattr(color_blending, method)(state)
    cb_call_action.assert_not_called()


def test_color_blending_close(session, color_blending, session_call_action):
    color_blending.close()
    session_call_action.assert_called_with(
        "imageViewConfigStore.removeColorBlending", color_blending._frame
    )
