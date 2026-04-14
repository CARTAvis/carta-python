import pytest

from carta.colorblending import ColorBlending, Layer
from carta.constants import Colormap as CM
from carta.constants import ColormapSet as CMS
from carta.constants import ImageType
from carta.image import Image
from carta.util import CartaActionFailed, CartaValidationFailed, Macro

# FIXTURES


@pytest.fixture
def colorblending(session):
    return ColorBlending(session, 0)


@pytest.fixture
def layer(colorblending):
    return Layer(colorblending, 1)


@pytest.fixture
def cb_get_value(colorblending, mock_get_value):
    return mock_get_value(colorblending)


@pytest.fixture
def cb_call_action(colorblending, mock_call_action):
    return mock_call_action(colorblending)


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
    return mock_property("carta.colorblending.ColorBlending")


@pytest.fixture
def layer_property(mock_property):
    return mock_property("carta.colorblending.Layer")


# TESTS — Layer


def test_layer_from_list(colorblending):
    layers = Layer.from_list(colorblending, [5, 6, 7])
    assert [ly.layer_id for ly in layers] == [5, 6, 7]
    assert all(ly.colorblending is colorblending for ly in layers)


def test_layer_repr(session, colorblending, cb_property, layer_property):
    cb_property("imageview_id", 11)
    cb_property("file_name", "blend.fits")
    layer_property("file_name", "layer1.fits")
    r = repr(Layer(colorblending, 3))
    # session id is 0 (from conftest)
    assert r == "0:11:blend.fits:3:layer1.fits"


def test_layer_file_name_property(layer, layer_get_value):
    layer.file_name
    layer_get_value.assert_called_with("frameInfo.fileInfo.name")


def test_layer_image_id_property(layer, layer_get_value):
    layer.image_id
    layer_get_value.assert_called_with("frameInfo.fileId")


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
def test_layer_set_alpha_valid(colorblending, alpha, cb_call_action):
    Layer(colorblending, 2).set_alpha(alpha)
    cb_call_action.assert_called_with("setAlpha", 2, alpha)


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_layer_set_alpha_invalid(colorblending, alpha):
    with pytest.raises(CartaValidationFailed):
        Layer(colorblending, 2).set_alpha(alpha)


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


def test_colorblending_init(session):
    colorblending = ColorBlending(session, 3)
    assert colorblending.store_id == 3
    assert (
        colorblending._base_path
        == "imageViewConfigStore.colorBlendingImages[3]"
    )
    assert colorblending._frame == Macro(
        "", "imageViewConfigStore.colorBlendingImages[3]"
    )


def test_colorblending_repr(session, colorblending, cb_property):
    cb_property("imageview_id", 3)
    cb_property("file_name", "blend.fits")
    assert repr(colorblending) == "0:3:blend.fits"


def test_colorblending_file_name(colorblending, cb_get_value):
    colorblending.file_name
    cb_get_value.assert_called_with("filename")


def test_colorblending_imageview_id(
    session, colorblending, session_get_value, cb_property
):
    cb_property("file_name", "imgC")
    session_get_value.side_effect = [["imgA", "imgB", "imgC", "imgD"]]
    assert colorblending.imageview_id == 2
    session_get_value.assert_called_with("imageViewConfigStore.imageNames")


def test_colorblending_alpha(colorblending, cb_get_value):
    colorblending.alpha
    cb_get_value.assert_called_with("alpha")


def test_colorblending_base_frame(colorblending, cb_get_value):
    cb_get_value.return_value = 42
    base_frame = colorblending._base_frame

    cb_get_value.assert_called_once_with("frames[0].id")
    assert isinstance(base_frame, Image)
    assert base_frame.session is colorblending.session
    assert base_frame.image_id == 42


def test_colorblending_make_active(
    session, colorblending, cb_property, session_call_action
):
    cb_property("imageview_id", 9)
    colorblending.make_active()
    session_call_action.assert_called_with("setActiveImageByIndex", 9)


def test_colorblending_layer_list_derived(session, mocker):
    cb = ColorBlending(session, 3)

    # Simulate two layers from the frontend's computed frames array length.
    gv = mocker.patch.object(cb, "get_value")
    gv.return_value = 2

    layers = cb.layer_list()
    assert [ly.layer_id for ly in layers] == [0, 1]
    gv.assert_called_once_with("frames.length")


def test_colorblending_add_layer(colorblending, cb_call_action, image):
    colorblending.add_layer(image)
    cb_call_action.assert_called_with("addSelectedFrame", image._frame)


@pytest.mark.parametrize("idx,expected_param", [(1, 0), (3, 2)])
def test_colorblending_delete_layer(
    colorblending, cb_call_action, idx, expected_param
):
    colorblending.delete_layer(idx)
    cb_call_action.assert_called_with("deleteSelectedFrame", expected_param)


def test_colorblending_delete_layer_rejects_base_layer(
    colorblending, cb_call_action
):
    with pytest.raises(ValueError, match="The base layer cannot be deleted."):
        colorblending.delete_layer(0)

    cb_call_action.assert_not_called()


@pytest.mark.parametrize("idx,expected_param", [(1, 0), (5, 4)])
def test_colorblending_set_layer(
    colorblending, cb_call_action, image, idx, expected_param
):
    colorblending.set_layer(image, idx)
    cb_call_action.assert_called_with(
        "setSelectedFrame", expected_param, image._frame
    )


def test_colorblending_set_layer_sequence(session, colorblending, mocker):
    # Prepare three existing layers with image_ids 10, 20, 30
    class _L:
        def __init__(self, lid, iid):
            self.layer_id = lid
            self.image_id = iid

    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )
    mocker.patch(
        "carta.colorblending.ColorBlending.alpha",
        new_callable=mocker.PropertyMock,
        return_value=[1.0, 0.2, 0.8],
    )
    del_layer = mocker.patch.object(colorblending, "delete_layer")
    add_layer = mocker.patch.object(colorblending, "add_layer")
    set_alpha = mocker.patch.object(Layer, "set_alpha", autospec=True)

    colorblending.set_layer_sequence([0, 2, 1])

    # Deletes all non-base layers (twice) then adds layers in specified order
    assert del_layer.call_count == 2
    add_args = [call.args[0] for call in add_layer.call_args_list]
    assert [img.image_id for img in add_args] == [30, 20]
    assert [call.args[1] for call in set_alpha.call_args_list] == [0.8, 0.2]


def test_colorblending_set_layer_sequence_supports_user_specified_subset_order(
    session, colorblending, mocker
):
    class _L:
        def __init__(self, lid, iid):
            self.layer_id = lid
            self.image_id = iid

    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30), _L(3, 40)],
    )
    mocker.patch(
        "carta.colorblending.ColorBlending.alpha",
        new_callable=mocker.PropertyMock,
        return_value=[1.0, 0.2, 0.8, 0.4],
    )
    del_layer = mocker.patch.object(colorblending, "delete_layer")
    add_layer = mocker.patch.object(colorblending, "add_layer")
    set_alpha = mocker.patch.object(Layer, "set_alpha", autospec=True)

    colorblending.set_layer_sequence([0, 3, 1])

    assert del_layer.call_count == 3
    assert [call.args[0].image_id for call in add_layer.call_args_list] == [40, 20]
    assert [call.args[1] for call in set_alpha.call_args_list] == [0.4, 0.2]


def test_colorblending_set_layer_sequence_rejects_missing_layer_index(
    session, colorblending, mocker
):
    class _L:
        def __init__(self, lid, iid):
            self.layer_id = lid
            self.image_id = iid

    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30), _L(3, 40)],
    )

    with pytest.raises(
        ValueError,
        match="layer_indices contains a layer index which does not exist.",
    ):
        colorblending.set_layer_sequence([0, 4, 1])


def test_colorblending_set_layer_sequence_requires_base_layer_first(
    session, colorblending, mocker
):
    class _L:
        def __init__(self, lid, iid):
            self.layer_id = lid
            self.image_id = iid

    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )

    with pytest.raises(
        ValueError,
        match="layer_indices must start with the base layer index 0.",
    ):
        colorblending.set_layer_sequence([2, 1])


def test_colorblending_set_layer_sequence_rejects_duplicate_base_layer(
    session, colorblending, mocker
):
    class _L:
        def __init__(self, lid, iid):
            self.layer_id = lid
            self.image_id = iid

    mocker.patch.object(
        ColorBlending,
        "layer_list",
        return_value=[_L(0, 10), _L(1, 20), _L(2, 30)],
    )

    with pytest.raises(
        ValueError,
        match=(
            "layer_indices must contain the base layer index 0 only once, "
            "as the first index."
        ),
    ):
        colorblending.set_layer_sequence([0, 2, 0])


def test_colorblending_set_center(colorblending, mocker):
    base_frame = mocker.create_autospec(Image, instance=True)
    mocker.patch(
        "carta.colorblending.ColorBlending._base_frame",
        new_callable=mocker.PropertyMock,
        return_value=base_frame,
    )

    colorblending.set_center(1, 2)
    base_frame.set_center.assert_called_once_with(1, 2)


@pytest.mark.parametrize("zoom,absolute", [(2, True), (3.5, False)])
def test_colorblending_set_zoom_level(colorblending, mocker, zoom, absolute):
    base_frame = mocker.create_autospec(Image, instance=True)
    mocker.patch(
        "carta.colorblending.ColorBlending._base_frame",
        new_callable=mocker.PropertyMock,
        return_value=base_frame,
    )

    colorblending.set_zoom_level(zoom, absolute)
    base_frame.set_zoom_level.assert_called_once_with(zoom, absolute)


def test_colorblending_set_colormap_set(colorblending, cb_call_action, mocker):
    # Two layers; verify setInverted(False) called on each
    ly1 = mocker.create_autospec(Layer(colorblending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(colorblending, 2), instance=True)
    mocker.patch.object(ColorBlending, "layer_list", return_value=[ly1, ly2])

    colorblending.set_colormap_set(CMS.Rainbow)
    cb_call_action.assert_called_with("applyColormapSet", CMS.Rainbow)
    ly1.call_action.assert_called_with("renderConfig.setInverted", False)
    ly2.call_action.assert_called_with("renderConfig.setInverted", False)


def test_colorblending_set_alpha_valid(colorblending, mocker):
    ly1 = mocker.create_autospec(Layer(colorblending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(colorblending, 2), instance=True)
    mocker.patch.object(ColorBlending, "layer_list", return_value=[ly1, ly2])

    colorblending.set_alpha([0.2, 0.8])
    ly1.set_alpha.assert_called_with(0.2)
    ly2.set_alpha.assert_called_with(0.8)


@pytest.mark.parametrize("vals", [[-0.1, 0.5], [1.2], [0.1, 2.0, 0.3]])
def test_colorblending_set_alpha_invalid(colorblending, vals):
    with pytest.raises(CartaValidationFailed):
        colorblending.set_alpha(vals)


@pytest.mark.parametrize("vals", [[0.5], [0.1, 0.2, 0.3]])
def test_colorblending_set_alpha_length_mismatch(colorblending, mocker, vals):
    ly1 = mocker.create_autospec(Layer(colorblending, 1), instance=True)
    ly2 = mocker.create_autospec(Layer(colorblending, 2), instance=True)
    mocker.patch.object(ColorBlending, "layer_list", return_value=[ly1, ly2])

    with pytest.raises(ValueError, match="does not match"):
        colorblending.set_alpha(vals)


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
            "set_vectoroverlay_visible",
            "toggleVectorOverlayVisible",
            False,
        ),
    ],
)
def test_colorblending_toggle_visibility_when_needed(
    colorblending, cb_get_value, cb_call_action, getter, method, action, state
):
    # Current state opposite to desired -> should toggle
    cb_get_value.side_effect = [not state]
    getattr(colorblending, method)(state)
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
            "set_vectoroverlay_visible",
            "toggleVectorOverlayVisible",
            True,
        ),
    ],
)
def test_colorblending_toggle_visibility_noop(
    colorblending, cb_get_value, cb_call_action, getter, method, action, state
):
    # Current state equals desired -> no toggle
    cb_get_value.side_effect = [state]
    getattr(colorblending, method)(state)
    cb_call_action.assert_not_called()


def test_colorblending_close(session, colorblending, session_call_action):
    colorblending.close()
    session_call_action.assert_called_with(
        "imageViewConfigStore.removeColorBlending", colorblending._frame
    )


# CREATION HELPERS


def test_colorblending_from_imageview_id(session, session_get_value, mocker):
    session_get_value.side_effect = [ImageType.COLOR_BLENDING, 17]
    init = mocker.patch.object(ColorBlending, "__init__", return_value=None)

    cb = ColorBlending.from_imageview_id(session, 5)

    assert isinstance(cb, ColorBlending)
    assert [call.args for call in session_get_value.call_args_list] == [
        ("imageViewConfigStore.imageList[5].type",),
        ("imageViewConfigStore.imageList[5].store.id",),
    ]
    init.assert_called_once_with(session, 17)


def test_colorblending_from_imageview_id_rejects_non_color_blending(
    session, session_get_value, mocker
):
    session_get_value.return_value = ImageType.FRAME
    init = mocker.patch.object(ColorBlending, "__init__", return_value=None)

    with pytest.raises(
        ValueError,
        match="imageview_id does not refer to a color blending image.",
    ):
        ColorBlending.from_imageview_id(session, 5)

    session_get_value.assert_called_once_with(
        "imageViewConfigStore.imageList[5].type"
    )
    init.assert_not_called()


def test_colorblending_from_images_success(session, mocker):
    # Prepare two images to blend
    img0 = Image(session, 100)
    img1 = Image(session, 200)

    # setSpatialReference alignment returns True for img1
    mocker.patch.object(session, "call_action")
    mocker.patch.object(img1, "call_action", return_value=True)

    # Create ID for new color blending
    session.call_action.side_effect = [None, 123]

    # Avoid __init__ side effects; just ensure returned instance
    init = mocker.patch.object(ColorBlending, "__init__", return_value=None)
    cb = ColorBlending.from_images(session, [img0, img1])
    assert isinstance(cb, ColorBlending)
    session.call_action.assert_any_call(
        "setSpatialReference", img0._frame, False
    )
    img1.call_action.assert_called_with("setSpatialReference", img0._frame)
    session.call_action.assert_called_with(
        "imageViewConfigStore.createColorBlending", return_path="id"
    )
    init.assert_called_once_with(session, 123)


def test_colorblending_from_images_alignment_failure(
    session, mocker, mock_property
):
    img0 = Image(session, 100)
    img1 = Image(session, 200)

    mocker.patch.object(session, "call_action")
    mock_property("carta.image.Image")("file_name", "bad.fits")
    mocker.patch.object(img1, "call_action", return_value=False)

    with pytest.raises(CartaActionFailed) as e:
        ColorBlending.from_images(session, [img0, img1])
    assert "Failed to set spatial reference for image bad.fits." in str(
        e.value
    )


def test_colorblending_from_images_rejects_more_than_initial_layer_limit(
    session, mocker
):
    images = [
        Image(session, image_id)
        for image_id in range(ColorBlending.MAX_INITIAL_LAYERS + 1)
    ]
    session_call_action = mocker.patch.object(session, "call_action")

    with pytest.raises(
        ValueError,
        match=(
            "Color blending initialization supports at most 10 images "
            r"\(the base layer plus 9 matched images\)."
        ),
    ):
        ColorBlending.from_images(session, images)

    session_call_action.assert_not_called()


def test_colorblending_from_files(session, mocker):
    mock_open_images = mocker.patch.object(
        session,
        "open_images",
        return_value=[Image(session, 1), Image(session, 2)],
    )
    mock_from_images = mocker.patch.object(
        ColorBlending, "from_images", return_value="CB"
    )
    out = ColorBlending.from_files(session, ["a.fits", "b.fits"], append=True)
    mock_open_images.assert_called_with(["a.fits", "b.fits"], append=True)
    mock_from_images.assert_called()
    assert out == "CB"


def test_colorblending_from_files_rejects_more_than_initial_layer_limit(
    session, mocker
):
    files = [
        f"image-{file_id}.fits"
        for file_id in range(ColorBlending.MAX_INITIAL_LAYERS + 1)
    ]
    mock_open_images = mocker.patch.object(session, "open_images")

    with pytest.raises(
        ValueError,
        match=(
            "Color blending initialization supports at most 10 images "
            r"\(the base layer plus 9 matched images\)."
        ),
    ):
        ColorBlending.from_files(session, files)

    mock_open_images.assert_not_called()
