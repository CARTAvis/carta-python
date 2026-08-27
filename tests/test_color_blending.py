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
    find = mocker.patch.object(session, "_find_view_index", return_value=2)
    layer_property("image_id", 42)
    layer_property("file_name", "layer1.fits")
    layer_property("colormap", "viridis")
    layer_property("inverted", False)
    layer_property("alpha", 0.5)
    r = repr(Layer(color_blending, 3))
    assert r == (
        "Layer(view_index=2, color_blending_id=0, layer_id=3, "
        "file_name='layer1.fits', colormap='viridis', inverted=False, "
        "alpha=0.5)"
    )
    find.assert_called_once_with(ImageType.FRAME, 42)


def test_layer_repr_closed_when_image_not_in_views(
    session, color_blending, layer_property, mocker
):
    layer_property("image_id", 42)
    mocker.patch.object(
        session,
        "_find_view_index",
        side_effect=RuntimeError("not in views"),
    )
    r = repr(Layer(color_blending, 3))
    assert r == (
        "[Closed] Layer(view_index=None, color_blending_id=0, "
        "layer_id=3)"
    )


def test_layer_repr_closed_when_image_is_gone(session, color_blending, mocker):
    mocker.patch(
        "carta.color_blending.Layer.image_id",
        new_callable=mocker.PropertyMock,
        side_effect=CartaActionFailed("frame is gone"),
    )
    r = repr(Layer(color_blending, 3))
    assert r == (
        "[Closed] Layer(view_index=None, color_blending_id=0, "
        "layer_id=3)"
    )


def test_layer_repr_closed_when_file_name_read_fails(
    session, color_blending, layer_property, mocker
):
    mocker.patch.object(session, "_find_view_index", return_value=2)
    layer_property("image_id", 42)
    mocker.patch(
        "carta.color_blending.Layer.file_name",
        new_callable=mocker.PropertyMock,
        side_effect=CartaActionFailed("file_name read failed"),
    )
    r = repr(Layer(color_blending, 3))
    assert r == (
        "[Closed] Layer(view_index=2, color_blending_id=0, "
        "layer_id=3)"
    )


def test_layer_file_name_property(layer, layer_get_value):
    layer.file_name
    layer_get_value.assert_called_with("frameInfo.fileInfo.name")


def test_layer_image_id_property(layer, layer_get_value):
    layer.image_id
    layer_get_value.assert_called_with("frameInfo.fileId")


def test_layer_colormap_property(layer, layer_get_value):
    layer_get_value.return_value = "viridis"

    assert layer.colormap == "viridis"
    layer_get_value.assert_called_once_with("renderConfig.colorMap")


def test_layer_inverted_property(layer, layer_get_value):
    layer_get_value.return_value = True

    assert layer.inverted is True
    layer_get_value.assert_called_once_with("renderConfig.isInverted")


def test_layer_alpha_property(layer, cb_get_value):
    cb_get_value.return_value = 0.5

    assert layer.alpha == 0.5
    cb_get_value.assert_called_once_with("alpha[1]")


def test_layer_delete(layer, mocker):
    delete_layer = mocker.patch.object(layer.color_blending, "delete_layer")

    layer.delete()

    delete_layer.assert_called_once_with(layer.layer_id)


def test_layer_set_image(layer, image, mocker):
    set_layer_image = mocker.patch.object(
        layer.color_blending, "set_layer_image"
    )

    layer.set_image(image)

    set_layer_image.assert_called_once_with(layer.layer_id, image)


def test_layer_set_image_rejects_invalid_image(layer, mocker):
    set_layer_image = mocker.patch.object(
        layer.color_blending, "set_layer_image"
    )

    with pytest.raises(CartaValidationFailed):
        layer.set_image(object())

    set_layer_image.assert_not_called()


def test_layer_view_index(session, color_blending, layer_property, mocker):
    find = mocker.patch.object(session, "_find_view_index", return_value=7)
    layer_property("image_id", 42)
    assert Layer(color_blending, 3).view_index == 7
    find.assert_called_once_with(ImageType.FRAME, 42)


def test_layer_view_index_raises_when_image_not_in_views(
    session, color_blending, layer_property, mocker
):
    layer_property("image_id", 42)
    mocker.patch.object(
        session,
        "_find_view_index",
        side_effect=RuntimeError("not in views"),
    )
    with pytest.raises(RuntimeError):
        Layer(color_blending, 3).view_index


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
        "ColorBlending(view_index=2, color_blending_id=0, "
        "file_name='Color Blending 1')"
    )


def test_color_blending_repr_closed_when_not_in_views(
    session, color_blending, mocker
):
    mocker.patch.object(
        session,
        "call_action",
        side_effect=RuntimeError("not in views"),
    )
    r = repr(color_blending)
    assert r == (
        "[Closed] ColorBlending(view_index=None, color_blending_id=0)"
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
        "[Closed] ColorBlending(view_index=2, color_blending_id=0)"
    )


def test_color_blending_file_name(color_blending, cb_get_value):
    color_blending.file_name
    cb_get_value.assert_called_with("filename")


def test_color_blending_view_index(
    session, color_blending, session_call_action
):
    session_call_action.return_value = 2
    assert color_blending.view_index == 2
    session_call_action.assert_called_once_with(
        "imageViewConfigStore.getImageListIndex",
        ImageType.COLOR_BLENDING,
        0,
        response_expected=True,
    )


def test_color_blending_view_index_raises_when_missing(
    session, color_blending, session_call_action
):
    session_call_action.return_value = -1
    with pytest.raises(RuntimeError):
        color_blending.view_index


def test_color_blending_alpha(color_blending, cb_get_value):
    color_blending.alphas
    cb_get_value.assert_called_with("alpha")


def test_color_blending_base_frame(color_blending, cb_get_value):
    cb_get_value.return_value = 42
    base_frame = color_blending._base_frame

    cb_get_value.assert_called_once_with("frames[0].id")
    assert isinstance(base_frame, Image)
    assert base_frame.session is color_blending.session
    assert base_frame.image_id == 42


def test_color_blending_make_active(session, color_blending, session_call_action):
    # make_active must be driven by color_blending_id via setActiveImageById.
    # It must not depend on view_index (which is volatile).
    color_blending.make_active()
    session_call_action.assert_called_with(
        "setActiveImageById", ImageType.COLOR_BLENDING, 0
    )


def test_color_blending_make_active_does_not_read_view_index(
    session, color_blending, session_call_action, session_get_value
):
    color_blending.make_active()
    for call in session_get_value.call_args_list:
        assert call.args != ("imageViewConfigStore.imageListSummary",)


def test_color_blending_layers_derived(session, mocker):
    cb = ColorBlending(session, 3)

    # Simulate two layers from the frontend's computed frames array length.
    gv = mocker.patch.object(cb, "get_value")
    gv.return_value = 2

    layers = cb.layers()
    assert [ly.layer_id for ly in layers] == [0, 1]
    gv.assert_called_once_with("frames.length")


def test_color_blending_layers_accepts_ids_in_order_with_duplicates(
    color_blending, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=3,
    )

    layers = color_blending.layers([2, 0, 2])

    assert [layer.layer_id for layer in layers] == [2, 0, 2]


@pytest.mark.parametrize("layer_ids", [[-1], [3], [1.5], ["1"]])
def test_color_blending_layers_rejects_invalid_ids(
    color_blending, mocker, layer_ids
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=3,
    )
    from_list = mocker.patch.object(Layer, "from_list")

    with pytest.raises(CartaValidationFailed):
        color_blending.layers(layer_ids)

    from_list.assert_not_called()


def test_color_blending_add_layer(color_blending, cb_call_action, image):
    color_blending.add_layer(image)
    cb_call_action.assert_called_with("addSelectedFrame", image._frame)


def test_color_blending_add_layer_rejects_invalid_image(
    color_blending, cb_call_action
):
    with pytest.raises(CartaValidationFailed):
        color_blending.add_layer(object())

    cb_call_action.assert_not_called()


@pytest.mark.parametrize("idx,expected_param", [(1, 0), (3, 2)])
def test_color_blending_delete_layer(
    color_blending, cb_call_action, idx, expected_param, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=4,
    )
    color_blending.delete_layer(idx)
    cb_call_action.assert_called_with("deleteSelectedFrame", expected_param)


def test_color_blending_delete_base_layer_promotes_next_layer(
    color_blending, cb_call_action, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=2,
    )
    layers = [Layer(color_blending, 0), Layer(color_blending, 1)]
    mocker.patch.object(color_blending, "layers", return_value=layers)
    mocker.patch.object(
        Layer, "image_id", new_callable=mocker.PropertyMock, return_value=42
    )
    image = mocker.patch("carta.color_blending.Image", autospec=True)

    color_blending.delete_layer(0)

    cb_call_action.assert_not_called()
    image.assert_called_once_with(color_blending.session, 42)
    image.return_value.make_spatial_reference.assert_called_once_with()


def test_color_blending_delete_only_base_layer_closes_color_blending(
    color_blending, cb_call_action, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=1,
    )
    mocker.patch.object(
        color_blending, "layers", return_value=[Layer(color_blending, 0)]
    )
    close = mocker.patch.object(color_blending, "close")

    color_blending.delete_layer(0)

    close.assert_called_once_with()
    cb_call_action.assert_not_called()


@pytest.mark.parametrize("idx", [-1, 2])
def test_color_blending_delete_layer_rejects_out_of_range(
    color_blending, cb_call_action, idx, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=2,
    )

    with pytest.raises(CartaValidationFailed):
        color_blending.delete_layer(idx)

    cb_call_action.assert_not_called()


@pytest.mark.parametrize("idx,expected_param", [(1, 0), (5, 4)])
def test_color_blending_set_layer_image_projects_layer_ids(
    color_blending, cb_call_action, cb_get_value, image, idx, expected_param, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=6,
    )
    cb_get_value.return_value = []
    color_blending.set_layer_image(idx, image)
    cb_get_value.assert_called_once_with("frames", return_path="frameInfo.fileId")
    cb_call_action.assert_called_with(
        "setSelectedFrame", expected_param, image._frame
    )


@pytest.mark.parametrize("idx", [-1, 2])
def test_color_blending_set_layer_image_rejects_out_of_range(
    color_blending, cb_call_action, image, idx, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=2,
    )

    with pytest.raises(CartaValidationFailed):
        color_blending.set_layer_image(idx, image)

    cb_call_action.assert_not_called()


@pytest.mark.parametrize("idx", [0, 2])
def test_color_blending_set_layer_image_rejects_existing_image(
    color_blending, cb_call_action, cb_get_value, image, idx, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=3,
    )
    cb_get_value.return_value = [image.image_id]
    set_spatial_matching = mocker.patch.object(image, "set_spatial_matching")
    make_spatial_reference = mocker.patch.object(image, "make_spatial_reference")

    with pytest.raises(CartaValidationFailed, match="already"):
        color_blending.set_layer_image(idx, image)

    cb_call_action.assert_not_called()
    set_spatial_matching.assert_not_called()
    make_spatial_reference.assert_not_called()


def test_color_blending_set_base_layer_image(
    color_blending, cb_call_action, cb_get_value, image, mocker
):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=1,
    )
    cb_get_value.return_value = []
    set_spatial_matching = mocker.patch.object(image, "set_spatial_matching")
    make_spatial_reference = mocker.patch.object(image, "make_spatial_reference")

    color_blending.set_layer_image(0, image)

    set_spatial_matching.assert_called_once_with(True)
    make_spatial_reference.assert_called_once_with()
    cb_call_action.assert_not_called()


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


def test_color_blending_set_alphas_valid(color_blending, mocker):
    ly1 = mocker.create_autospec(Layer(color_blending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(color_blending, 2), instance=True)
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=2,
    )
    mocker.patch.object(ColorBlending, "layers", return_value=[ly1, ly2])

    color_blending.set_alphas([0.2, 0.8])
    ly1.set_alpha.assert_called_with(0.2)
    ly2.set_alpha.assert_called_with(0.8)


@pytest.mark.parametrize("vals", [[-0.1, 0.5], [1.2], [0.1, 2.0, 0.3]])
def test_color_blending_set_alphas_invalid(color_blending, vals, mocker):
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=2,
    )

    with pytest.raises(CartaValidationFailed):
        color_blending.set_alphas(vals)


@pytest.mark.parametrize("vals", [[0.5], [0.1, 0.2, 0.3]])
def test_color_blending_set_alphas_length_mismatch(color_blending, mocker, vals):
    ly1 = mocker.create_autospec(Layer(color_blending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(color_blending, 2), instance=True)
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        return_value=2,
    )
    mocker.patch.object(ColorBlending, "layers", return_value=[ly1, ly2])

    with pytest.raises(CartaValidationFailed):
        color_blending.set_alphas(vals)


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
