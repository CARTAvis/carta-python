from unittest.mock import call

import pytest

from carta.image import Image
from carta.color_blending import ColorBlending
from carta.util import CartaActionFailed, CartaBadResponse, CartaValidationFailed, Macro, Point as Pt
from carta.constants import ColormapSet, ComplexComponent as CC, ImageType, Polarization as Pol

# FIXTURES


@pytest.fixture
def get_value(session, mock_get_value):
    return mock_get_value(session)


@pytest.fixture
def call_action(session, mock_call_action):
    return mock_call_action(session)


@pytest.fixture
def method(session, mock_method):
    return mock_method(session)


# TESTS

# TODO fill in missing session tests

@pytest.mark.parametrize("name,classname", [
    ("wcs", "SessionWCSOverlay"),
])
def test_subobjects(session, name, classname):
    assert getattr(session, name).__class__.__name__ == classname


def test_carta_version_property(session, get_value):
    get_value.return_value = "6.0.0"

    assert session.carta_version == "6.0.0"
    assert session.carta_version == "6.0.0"

    get_value.assert_called_once_with("frontendVersion")


def test_session_repr_includes_carta_version(session, get_value, mocker):
    session._protocol = mocker.Mock(frontend_url="http://localhost:3000")
    get_value.return_value = "6.0.0"

    assert (
        repr(session)
        == "Session(session_id=0, uri='http://localhost:3000', carta_version='6.0.0')"
    )


def test_session_repr_uses_cached_carta_version_without_lookup(
    session, mocker
):
    session._protocol = mocker.Mock(frontend_url="http://localhost:3000")
    session._cache = {"carta_version": "6.0.0"}
    get_value = mocker.patch.object(session, "get_value")

    assert (
        repr(session)
        == "Session(session_id=0, uri='http://localhost:3000', carta_version='6.0.0')"
    )
    get_value.assert_not_called()


def test_session_repr_omits_carta_version_when_lookup_fails(session, mocker):
    session._protocol = mocker.Mock(frontend_url="http://localhost:3000")
    mocker.patch.object(
        session,
        "get_value",
        side_effect=CartaActionFailed("frontendVersion unavailable"),
    )

    assert repr(session) == "Session(session_id=0, uri='http://localhost:3000')"

# PATHS


@pytest.mark.parametrize("path, expected_path", [
    ("foo", "/current/dir/foo"),
    ("/foo", "/foo"),
    ("..", "/current"),
    (".", "/current/dir"),
    ("foo/..", "/current/dir"),
    ("foo/../bar", "/current/dir/bar"),
])
def test_resolve_file_path(session, method, path, expected_path):
    method("pwd", ["/current/dir"])
    assert session.resolve_file_path(path) == expected_path


def test_pwd(session, call_action, get_value):
    get_value.side_effect = ["current/dir/"]
    pwd = session.pwd()
    call_action.assert_called_with("fileBrowserStore.getFileList", Macro('fileBrowserStore', 'startingDirectory'))
    get_value.assert_called_with("fileBrowserStore.fileList.directory")
    assert pwd == "/current/dir"


def test_ls(session, method, call_action):
    method("pwd", ["/current/dir"])
    call_action.side_effect = [{"files": [{"name": "foo.fits"}, {"name": "bar.fits"}], "subdirectories": [{"name": "baz"}]}]
    ls = session.ls()
    call_action.assert_called_with("backendService.getFileList", "/current/dir", 2)
    assert ls == ["bar.fits", "baz/", "foo.fits"]


def test_cd(session, method, call_action):
    method("resolve_file_path", ["/resolved/file/path"])
    session.cd("original/path")
    call_action.assert_called_with("fileBrowserStore.saveStartingDirectory", "/resolved/file/path")


# IMAGE LIST / GET_IMAGE / COLOR-BLENDING HELPERS


def test_image_list_heterogeneous(session, get_value):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": ImageType.COLOR_BLENDING, "id": 3},
        {"type": ImageType.FRAME, "id": 20},
    ]

    images = session.image_list()

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )
    assert len(images) == 3
    assert isinstance(images[0], Image) and images[0].file_id == 10
    assert isinstance(images[1], ColorBlending) and images[1].color_blending_id == 3
    assert isinstance(images[2], Image) and images[2].file_id == 20


def test_image_list_skips_unsupported_image_type(session, get_value, capsys):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": 99, "id": 11},
        {"type": ImageType.FRAME, "id": 20},
    ]

    images = session.image_list()

    assert [image.file_id for image in images] == [10, 20]
    assert (
        "Skipping unsupported image-view entry at order 1"
        in capsys.readouterr().out
    )


def test_image_list_empty(session, get_value):
    get_value.return_value = []
    assert session.image_list() == []
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_find_image_view_order_single_round_trip(session, call_action):
    call_action.side_effect = [2, 1]

    assert session._find_image_view_order(ImageType.FRAME, 3) == 2
    assert session._find_image_view_order(ImageType.COLOR_BLENDING, 7) == 1
    assert call_action.call_args_list == [
        call(
            "imageViewConfigStore.getImageListIndex",
            ImageType.FRAME,
            3,
            response_expected=True,
        ),
        call(
            "imageViewConfigStore.getImageListIndex",
            ImageType.COLOR_BLENDING,
            7,
            response_expected=True,
        ),
    ]


def test_find_image_view_order_raises_when_missing(session, call_action):
    call_action.return_value = -1
    with pytest.raises(RuntimeError):
        session._find_image_view_order(ImageType.FRAME, 99)


# session.image_by_id


def test_image_by_id_requires_exactly_one_keyword(session, get_value):
    # Zero keywords -> ValueError with all three names listed.
    with pytest.raises(ValueError) as e:
        session.image_by_id()
    for name in ("image_view_order", "file_id", "color_blending_id"):
        assert name in str(e.value)
    assert "got 0 with values {}" in str(e.value)
    # Multiple keywords -> ValueError.
    with pytest.raises(ValueError) as e:
        session.image_by_id(file_id=1, color_blending_id=2)
    assert "'file_id': 1" in str(e.value)
    assert "'color_blending_id': 2" in str(e.value)


def test_image_by_id_rejects_positional(session):
    with pytest.raises(TypeError):
        session.image_by_id(0)


@pytest.mark.parametrize(
    "entry,expected_type,expected_id",
    [
        ({"type": ImageType.FRAME, "id": 10}, Image, 10),
        (
            {"type": ImageType.COLOR_BLENDING, "id": 7},
            ColorBlending,
            7,
        ),
    ],
)
def test_image_by_id_by_image_view_order(
    session, get_value, entry, expected_type, expected_id
):
    get_value.return_value = entry

    img = session.image_by_id(image_view_order=0)
    assert isinstance(img, expected_type)
    assert (
        img.file_id if expected_type is Image else img.color_blending_id
    ) == expected_id
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary[0]"
    )


def test_image_by_id_by_image_view_order_out_of_range(session, get_value):
    get_value.side_effect = CartaBadResponse("undefined")

    with pytest.raises(IndexError):
        session.image_by_id(image_view_order=99)

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary[99]"
    )


def test_image_by_id_by_image_view_order_raises_on_unsupported_type(
    session, get_value
):
    get_value.return_value = {"type": ImageType.PV_PREVIEW, "id": -2}

    with pytest.raises(NotImplementedError):
        session.image_by_id(image_view_order=0)


def test_image_by_id_by_file_id(session, get_value):
    get_value.return_value = 20

    img = session.image_by_id(file_id=20)
    assert isinstance(img, Image)
    assert img.file_id == 20
    get_value.assert_called_once_with(
        "frameMap[20]",
        return_path="frameInfo.fileId",
    )


def test_image_by_id_by_file_id_no_cross_type_fallback(session, get_value):
    get_value.side_effect = CartaBadResponse("undefined")

    with pytest.raises(RuntimeError):
        session.image_by_id(file_id=7)


def test_image_by_id_by_color_blending_id(session, get_value):
    get_value.return_value = 7

    cb = session.image_by_id(color_blending_id=7)
    assert isinstance(cb, ColorBlending)
    assert cb.color_blending_id == 7
    get_value.assert_called_once_with(
        "imageViewConfigStore.colorBlendingImageMap[7]",
        return_path="id",
    )


def test_image_by_id_by_color_blending_id_no_cross_type_fallback(
    session, get_value
):
    get_value.side_effect = CartaBadResponse("undefined")

    with pytest.raises(RuntimeError):
        session.image_by_id(color_blending_id=10)


def test_image_by_id_uses_targeted_frontend_lookups(session, get_value):
    get_value.side_effect = [
        {"type": ImageType.FRAME, "id": 10},
        10,
        7,
    ]

    session.image_by_id(image_view_order=0)
    session.image_by_id(file_id=10)
    session.image_by_id(color_blending_id=7)

    assert get_value.call_args_list == [
        call(
            "imageViewConfigStore.imageListSummary[0]"
        ),
        call("frameMap[10]", return_path="frameInfo.fileId"),
        call(
            "imageViewConfigStore.colorBlendingImageMap[7]",
            return_path="id",
        ),
    ]


# session.active_image


def test_active_image_returns_image_when_frame_active(session, get_value):
    get_value.side_effect = [
        {"type": ImageType.FRAME, "store": {"id": 12}},
    ]
    active = session.active_image()
    assert isinstance(active, Image)
    assert active.file_id == 12
    assert [call.args for call in get_value.call_args_list] == [
        ("activeImage",),
    ]


def test_active_image_returns_color_blending_when_color_blending_active(
    session, get_value
):
    get_value.side_effect = [
        {"type": ImageType.COLOR_BLENDING, "store": {"id": 3}},
    ]
    active = session.active_image()
    assert isinstance(active, ColorBlending)
    assert active.color_blending_id == 3
    assert [call.args for call in get_value.call_args_list] == [
        ("activeImage",),
    ]


def test_active_image_raises_on_unsupported_type(session, get_value):
    get_value.side_effect = [
        {"type": ImageType.PV_PREVIEW, "store": {"id": -2}},
    ]
    with pytest.raises(NotImplementedError):
        session.active_image()

# open_as_color_blending / create_color_blending


@pytest.mark.parametrize("files", [
    ["a.fits"],
    ["a.fits", "b.fits"],
    ["a.fits", "b.fits", "c.fits"],
    ["a.fits", "b.fits", "c.fits", "d.fits"],
])
def test_open_as_color_blending_opens_files_sets_matching_and_creates_blending(
    session, mocker, files
):
    images = [mocker.MagicMock(name=f"image{i}") for i in range(len(files))]
    open_images = mocker.patch.object(
        session,
        "open_images",
        return_value=images,
    )
    fake_cb = mocker.MagicMock(name="ColorBlending")
    create_color_blending = mocker.patch.object(
        session,
        "create_color_blending",
        return_value=fake_cb,
    )

    result = session.open_as_color_blending(files)
    open_images.assert_called_once_with(files, append=False)
    images[0].make_spatial_reference.assert_called_once_with()
    images[0].set_spatial_matching.assert_not_called()
    for image in images[1:]:
        image.set_spatial_matching.assert_called_once_with(True)
        image.make_spatial_reference.assert_not_called()
    create_color_blending.assert_called_once_with()
    assert result is fake_cb


def test_open_as_color_blending_rejects_empty_file_list(session, mocker):
    open_images = mocker.patch.object(session, "open_images")
    create_color_blending = mocker.patch.object(
        session, "create_color_blending"
    )

    with pytest.raises(CartaValidationFailed) as e:
        session.open_as_color_blending([])

    assert "at least 1" in str(e.value)
    open_images.assert_not_called()
    create_color_blending.assert_not_called()


@pytest.mark.parametrize("open_frame_count,layer_count,expected_colormap_set", [
    (1, 1, ColormapSet.RGB),
    (3, 3, ColormapSet.RGB),
    (5, 3, ColormapSet.RGB),
    (5, 4, ColormapSet.RAINBOW),
])
def test_create_color_blending_calls_frontend_create_action(session, mocker, open_frame_count, layer_count, expected_colormap_set):
    get_value = mocker.patch.object(
        session,
        "get_value",
        side_effect=[
            open_frame_count,
            layer_count,
        ],
    )
    call_action = mocker.patch.object(
        session,
        "call_action",
        return_value=123,
    )
    mock_set_colormap = mocker.patch.object(ColorBlending, "set_colormap_set")

    result = session.create_color_blending()
    assert get_value.call_args_list == [
        mocker.call("frames.length"),
        mocker.call(
            "imageViewConfigStore.colorBlendingImageMap[123].frames.length",
            return_path=None,
        ),
    ]
    call_action.assert_called_once_with(
        "imageViewConfigStore.createColorBlending",
        return_path="id",
    )
    mock_set_colormap.assert_called_once_with(expected_colormap_set)
    assert isinstance(result, ColorBlending)
    assert result.color_blending_id == 123


def test_create_color_blending_raises_when_no_frames_are_open(session, mocker):
    get_value = mocker.patch.object(session, "get_value", return_value=0)
    call_action = mocker.patch.object(session, "call_action")
    mock_set_colormap = mocker.patch.object(ColorBlending, "set_colormap_set")

    with pytest.raises(CartaActionFailed, match="No frames are open"):
        session.create_color_blending()

    get_value.assert_called_once_with("frames.length")
    call_action.assert_not_called()
    mock_set_colormap.assert_not_called()


def test_set_cursor(session, call_action):
    session.set_cursor(1, 2)
    call_action.assert_called_once_with(
        "activeFrame.setCursorPosition", Pt(1, 2)
    )

# OPENING IMAGES


@pytest.mark.parametrize("args,kwargs,expected_args,expected_kwargs", [
    # Open plain image
    (["subdir/image.fits"], {},
     ["subdir", "image.fits", "", False, False], {"make_active": True, "update_directory": False}),
    # Append plain image
    (["subdir/image.fits"], {"append": True},
     ["subdir", "image.fits", "", True, False], {"make_active": True, "update_directory": False}),
    # Append plain image; don't make active
    (["subdir/image.fits"], {"append": True, "make_active": False},
     ["subdir", "image.fits", "", True, False], {"make_active": False, "update_directory": False}),
    # Open plain image; select different HDU
    (["subdir/image.fits"], {"hdu": "3"},
     ["subdir", "image.fits", "3", False, False], {"make_active": True, "update_directory": False}),
    # Open plain image; update file browser directory
    (["subdir/image.fits"], {"update_directory": True},
     ["subdir", "image.fits", "", False, False], {"make_active": True, "update_directory": True}),
])
def test_open_image(mocker, session, args, kwargs, expected_args, expected_kwargs):
    mock_image_new = mocker.patch.object(Image, "new")
    session.open_image(*args, **kwargs)
    mock_image_new.assert_called_with(session, *expected_args, **expected_kwargs)


@pytest.mark.parametrize("args,kwargs,expected_args,expected_kwargs", [
    # Open complex image with default component
    (["subdir/image.fits"], {},
     ["subdir", 'AMPLITUDE("image.fits")', "", False, True], {"make_active": True, "update_directory": False}),
    # Open complex image with component selected
    (["subdir/image.fits"], {"component": CC.PHASE},
     ["subdir", 'PHASE("image.fits")', "", False, True], {"make_active": True, "update_directory": False}),
    # Append complex image
    (["subdir/image.fits"], {"component": CC.REAL, "append": True},
     ["subdir", 'REAL("image.fits")', "", True, True], {"make_active": True, "update_directory": False}),
    # Append complex image; don't make active
    (["subdir/image.fits"], {"component": CC.REAL, "append": True, "make_active": False},
     ["subdir", 'REAL("image.fits")', "", True, True], {"make_active": False, "update_directory": False}),
    # Open complex image; update file browser directory
    (["subdir/image.fits"], {"component": CC.IMAG, "update_directory": True},
     ["subdir", 'IMAG("image.fits")', "", False, True], {"make_active": True, "update_directory": True}),
])
def test_open_complex_image(mocker, session, args, kwargs, expected_args, expected_kwargs):
    mock_image_new = mocker.patch.object(Image, "new")
    session.open_complex_image(*args, **kwargs)
    mock_image_new.assert_called_with(session, *expected_args, **expected_kwargs)


@pytest.mark.parametrize("args,kwargs,expected_args,expected_kwargs", [
    # Open LEL image
    (["2*image.fits"], {},
     [".", '2*image.fits', "", False, True], {"make_active": True, "update_directory": False}),
    # Append LEL image
    (["2*image.fits+image.fits"], {"append": True},
     [".", '2*image.fits+image.fits', "", True, True], {"make_active": True, "update_directory": False}),
    # Append LEL image; don't make active
    (["2*image.fits+image.fits"], {"append": True, "make_active": False},
     [".", '2*image.fits+image.fits', "", True, True], {"make_active": False, "update_directory": False}),
    # Open LEL image; update file browser directory
    (["2*image.fits/image.fits"], {"update_directory": True},
     [".", '2*image.fits/image.fits', "", False, True], {"make_active": True, "update_directory": True}),
])
def test_open_LEL_image(mocker, session, args, kwargs, expected_args, expected_kwargs):
    mock_image_new = mocker.patch.object(Image, "new")
    session.open_LEL_image(*args, **kwargs)
    mock_image_new.assert_called_with(session, *expected_args, **expected_kwargs)


@pytest.mark.parametrize("append", [True, False])
def test_open_images(mocker, session, method, append):
    mock_open_image = method("open_image", ["1", "2", "3"])
    images = session.open_images(["foo.fits", "bar.fits", "baz.fits"], append)
    mock_open_image.assert_has_calls([
        mocker.call("foo.fits", append=append),
        mocker.call("bar.fits", append=True),
        mocker.call("baz.fits", append=True),
    ])
    assert images == ["1", "2", "3"]


@pytest.mark.parametrize("paths,expected_args", [
    (["foo.fits", "bar.fits", "baz.fits"], [
        [
            {"directory": "/resolved/path", "file": "foo.fits", "hdu": "", "polarizationType": 1},
            {"directory": "/resolved/path", "file": "bar.fits", "hdu": "", "polarizationType": 2},
            {"directory": "/resolved/path", "file": "baz.fits", "hdu": "", "polarizationType": 3},
        ], "/current/dir", ""]),
])
@pytest.mark.parametrize("append,expected_command", [
    (True, "appendConcatFile"),
    (False, "openConcatFile"),
])
def test_open_hypercube_guess_polarization(mocker, session, call_action, method, paths, expected_args, append, expected_command):
    method("pwd", ["/current/dir"])
    method("resolve_file_path", ["/resolved/path"] * 3)
    call_action.side_effect = [*expected_args[0], 123]

    hypercube = session.open_hypercube(paths, append)

    call_action.assert_has_calls([
        mocker.call("fileBrowserStore.getStokesFile", "/resolved/path", "foo.fits", ""),
        mocker.call("fileBrowserStore.getStokesFile", "/resolved/path", "bar.fits", ""),
        mocker.call("fileBrowserStore.getStokesFile", "/resolved/path", "baz.fits", ""),
        mocker.call(expected_command, *expected_args),
    ])

    assert type(hypercube) is Image
    assert hypercube.session == session
    assert hypercube.file_id == 123


@pytest.mark.parametrize("paths,expected_calls,mocked_side_effect,expected_error", [
    (["foo.fits", "bar.fits"], [
        ("fileBrowserStore.getStokesFile", "/resolved/path", "foo.fits", ""),
    ], [
        None,
    ], "Could not deduce polarization for"),
    (["foo.fits", "bar.fits"], [
        ("fileBrowserStore.getStokesFile", "/resolved/path", "foo.fits", ""),
        ("fileBrowserStore.getStokesFile", "/resolved/path", "bar.fits", ""),
    ], [
        {"directory": "/resolved/path", "file": "foo.fits", "hdu": "", "polarizationType": 1},
        {"directory": "/resolved/path", "file": "bar.fits", "hdu": "", "polarizationType": 1},
    ], "Duplicate polarizations deduced"),
])
def test_open_hypercube_guess_polarization_bad(mocker, session, call_action, method, paths, expected_calls, mocked_side_effect, expected_error):
    method("pwd", ["/current/dir"])
    method("resolve_file_path", ["/resolved/path"] * 3)
    call_action.side_effect = mocked_side_effect

    with pytest.raises(ValueError) as e:
        session.open_hypercube(paths)
    assert expected_error in str(e.value)

    call_action.assert_has_calls([mocker.call(*args) for args in expected_calls])


@pytest.mark.parametrize("paths,expected_args", [
    ({Pol.I: "foo.fits", Pol.Q: "bar.fits", Pol.U: "baz.fits"}, [
        [
            {"directory": "/resolved/path", "file": "foo.fits", "hdu": "", "polarizationType": 1},
            {"directory": "/resolved/path", "file": "bar.fits", "hdu": "", "polarizationType": 2},
            {"directory": "/resolved/path", "file": "baz.fits", "hdu": "", "polarizationType": 3},
        ], "/current/dir", ""]),
])
@pytest.mark.parametrize("append,expected_command", [
    (True, "appendConcatFile"),
    (False, "openConcatFile"),
])
def test_open_hypercube_explicit_polarization(mocker, session, call_action, method, paths, expected_args, append, expected_command):
    method("pwd", ["/current/dir"])
    method("resolve_file_path", ["/resolved/path"] * 3)
    call_action.side_effect = [123]

    hypercube = session.open_hypercube(paths, append)

    call_action.assert_has_calls([
        mocker.call(expected_command, *expected_args),
    ])

    assert type(hypercube) is Image
    assert hypercube.session == session
    assert hypercube.file_id == 123


@pytest.mark.parametrize("paths,expected_error", [
    ({Pol.I: "foo.fits"}, "at least 2"),
    (["foo.fits"], "at least 2"),
])
@pytest.mark.parametrize("append", [True, False])
def test_open_hypercube_bad(mocker, session, call_action, method, paths, expected_error, append):
    method("pwd", ["/current/dir"])
    method("resolve_file_path", ["/resolved/path"] * 3)

    with pytest.raises(Exception) as e:
        session.open_hypercube(paths, append)
    assert expected_error in str(e.value)
