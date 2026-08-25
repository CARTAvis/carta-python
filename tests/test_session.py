from unittest.mock import call
import logging

import pytest

from carta.image import Image
from carta.color_blending import ColorBlending
from carta.session import Session
from carta.util import (
    CartaActionFailed,
    CartaBadResponse,
    CartaBadSession,
    CartaRequestFailed,
    CartaUnsupportedVersion,
    CartaValidationFailed,
    Macro,
    Point as Pt,
)
from carta.constants import (
    ColormapSet,
    ComplexComponent as CC,
    ImageType,
    Polarization as Pol,
    VersionMismatchAction,
)

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
    assert isinstance(session, Session)
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

def test_direct_session_construction_does_not_validate_session(mocker):
    validate_session = mocker.patch.object(Session, "_validate_session")

    session = Session(0, None)

    assert session.session_id == 0
    validate_session.assert_not_called()


def test_validate_session_fetches_frontend_version_with_timeout(session, call_action):
    call_action.return_value = "6.1.0-dev"

    assert session._validate_session(timeout=3) == "6.1.0-dev"

    call_action.assert_called_once_with(
        "fetchParameter",
        Macro("", "frontendVersion"),
        response_expected=True,
        timeout=3,
    )
    assert session.carta_version == "6.1.0-dev"


def test_validate_session_warns_for_unsupported_version_when_requested(
    session, call_action, caplog
):
    call_action.return_value = "6.0.0"

    session._validate_session(
        timeout=3, version_mismatch_action=VersionMismatchAction.WARN
    )

    assert "older than the minimum" in caplog.text
    assert "complete functionality with carta-python 2.0.x" in caplog.text
    assert "\n\nSuggested actions:\n" in caplog.text
    assert "Upgrade CARTA to at least '6.1.0'." in caplog.text
    assert "version_mismatch_action=VersionMismatchAction.WARN" not in caplog.text


def test_validate_session_raises_for_unsatisfied_minimum_in_error_mode(
    session, call_action
):
    call_action.return_value = "5.9.0"

    with pytest.raises(CartaUnsupportedVersion, match="older than the minimum"):
        session._validate_session(
            timeout=3,
            version_mismatch_action=VersionMismatchAction.ERROR,
        )


@pytest.mark.parametrize(
    "version_mismatch_action",
    [VersionMismatchAction.WARN, VersionMismatchAction.ERROR],
)
def test_validate_session_accepts_newer_frontend_major(
    session, call_action, caplog, version_mismatch_action
):
    call_action.return_value = "7.0.0"

    assert session._validate_session(
        timeout=3,
        version_mismatch_action=version_mismatch_action,
    ) == "7.0.0"

    assert not caplog.text


def test_validate_session_validates_action_before_fetching_version(session, call_action):
    with pytest.raises(CartaValidationFailed):
        session._validate_session(timeout=3, version_mismatch_action="invalid")

    call_action.assert_not_called()


def test_validate_session_reports_invalid_frontend_version_in_error_mode(
    session, call_action
):
    call_action.return_value = "bad.version"

    with pytest.raises(CartaUnsupportedVersion, match="invalid CARTA version"):
        session._validate_session(
            timeout=2, version_mismatch_action=VersionMismatchAction.ERROR
        )


def test_validate_session_wraps_frontend_version_failure(session, call_action, mocker):
    session._protocol = mocker.Mock(frontend_url="http://localhost:3000")
    call_action.side_effect = CartaActionFailed("frontendVersion unavailable")

    with pytest.raises(CartaBadSession) as e:
        session._validate_session(timeout=2)

    message = str(e.value)
    assert "Could not validate CARTA session 0" in message
    assert "http://localhost:3000" in message
    assert "2" in message
    assert "CartaActionFailed" in message
    assert "frontendVersion unavailable" in message
    assert "--enable_scripting" in message


def test_call_action_adds_compatibility_suggestion_to_frontend_failure(
    session, mocker
):
    original_error = CartaActionFailed("newAction is unavailable")
    session._cache = {"carta_version": "7.0.0"}
    session._protocol = mocker.Mock()
    session._protocol.request_scripting_action.side_effect = original_error

    with pytest.raises(CartaActionFailed) as error:
        session.call_action("newAction")

    message = str(error.value)
    assert error.value is original_error
    assert "newAction is unavailable" in message
    assert "\n\nCompatibility suggestions:\n" in message
    assert "verify that the frontend action, attribute, or response path exists" in message
    assert "upgrade carta-python to the latest available release" in message


def test_call_action_preserves_frontend_failure_without_cached_version(
    session, mocker
):
    original_error = CartaActionFailed("newAction is unavailable")
    session._protocol = mocker.Mock()
    session._protocol.request_scripting_action.side_effect = original_error

    with pytest.raises(CartaActionFailed) as error:
        session.call_action("newAction")

    assert error.value is original_error


def test_call_action_does_not_add_compatibility_suggestion_to_request_failure(
    session, mocker
):
    original_error = CartaRequestFailed("session is unavailable")
    session._cache = {"carta_version": "7.0.0"}
    session._protocol = mocker.Mock()
    session._protocol.request_scripting_action.side_effect = original_error

    with pytest.raises(CartaRequestFailed) as error:
        session.call_action("newAction")

    assert error.value is original_error


def test_interact_checks_connection_by_default(mocker):
    protocol = mocker.Mock(frontend_url="http://localhost:3000")
    mocker.patch("carta.session.Protocol", return_value=protocol)
    validate_session = mocker.patch.object(Session, "_validate_session")

    session = Session.interact("http://localhost:3000?token=x", "123")

    assert session.session_id == 123
    assert session._protocol is protocol
    validate_session.assert_called_once_with(
        timeout=10,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_interact_passes_connection_check_timeout(mocker):
    protocol = mocker.Mock(frontend_url="http://localhost:3000")
    mocker.patch("carta.session.Protocol", return_value=protocol)
    validate_session = mocker.patch.object(Session, "_validate_session")

    Session.interact(
        "http://localhost:3000?token=x",
        123,
        connection_check_timeout=4,
    )

    validate_session.assert_called_once_with(
        timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_interact_always_validates(mocker):
    protocol = mocker.Mock(frontend_url="http://localhost:3000")
    mocker.patch("carta.session.Protocol", return_value=protocol)
    validate_session = mocker.patch.object(Session, "_validate_session")

    Session.interact(
        "http://localhost:3000?token=x",
        123,
    )

    validate_session.assert_called_once_with(
        timeout=10,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_interact_passes_mismatch_action(mocker):
    protocol = mocker.Mock(frontend_url="http://localhost:3000")
    mocker.patch("carta.session.Protocol", return_value=protocol)
    validate_session = mocker.patch.object(Session, "_validate_session")

    Session.interact(
        "http://localhost:3000?token=x",
        123,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    validate_session.assert_called_once_with(
        timeout=10,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_start_and_interact_stops_backend_when_connection_check_fails(mocker):
    backend = mocker.Mock(
        frontend_url="http://localhost:3000",
        last_session_id=123,
        debug_no_auth=False,
        errors=[],
    )
    backend.start.return_value = True
    mocker.patch("carta.session.Backend", return_value=backend)
    mocker.patch.object(
        Session,
        "interact",
        side_effect=CartaBadSession("startup check failed"),
    )

    with pytest.raises(CartaBadSession):
        Session.start_and_interact()

    backend.stop.assert_called_once_with()


def test_start_and_interact_preserves_error_when_backend_stop_fails(mocker):
    backend = mocker.Mock(
        frontend_url="http://localhost:3000",
        last_session_id=123,
        debug_no_auth=False,
        errors=[],
    )
    backend.start.return_value = True
    backend.stop.side_effect = RuntimeError("stop failed")
    mocker.patch("carta.session.Backend", return_value=backend)
    startup_error = CartaBadSession("startup check failed")
    mocker.patch.object(Session, "interact", side_effect=startup_error)

    with pytest.raises(CartaBadSession, match="startup check failed"):
        Session.start_and_interact()

    backend.stop.assert_called_once_with()


def test_create_passes_connection_check_options_to_browser(mocker):
    browser = mocker.Mock()
    expected_session = mocker.Mock()
    browser.new_session_from_url.return_value = expected_session

    result = Session.create(
        browser,
        "http://localhost:3000?token=x",
        token="token",
        timeout=7,
        debug_no_auth=True,
        connection_check_timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    assert result is expected_session
    browser.new_session_from_url.assert_called_once_with(
        "http://localhost:3000?token=x",
        "token",
        backend=None,
        timeout=7,
        debug_no_auth=True,
        connection_check_timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_start_and_create_passes_connection_check_options_to_browser(mocker):
    browser = mocker.Mock()
    expected_session = mocker.Mock()
    browser.new_session_with_backend.return_value = expected_session

    result = Session.start_and_create(
        browser,
        executable_path="carta-custom",
        remote_host="remote",
        params=("--verbosity", "5"),
        timeout=7,
        token="token",
        frontend_url_timeout=8,
        connection_check_timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    assert result is expected_session
    browser.new_session_with_backend.assert_called_once_with(
        "carta-custom",
        "remote",
        ("--verbosity", "5"),
        7,
        "token",
        8,
        connection_check_timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )
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


# VIEWS / IMAGES / COLOR-BLENDING HELPERS


def test_views_heterogeneous(session, get_value):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": ImageType.COLOR_BLENDING, "id": 3},
        {"type": ImageType.FRAME, "id": 20},
    ]

    views = session.views()

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )
    assert len(views) == 3
    assert isinstance(views[0], Image) and views[0].image_id == 10
    assert isinstance(views[1], ColorBlending) and views[1].color_blending_id == 3
    assert isinstance(views[2], Image) and views[2].image_id == 20


def test_views_skips_unsupported_view_type(session, get_value, caplog, capsys):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": ImageType.PV_PREVIEW, "id": 11},
        {"type": ImageType.FRAME, "id": 20},
    ]

    with caplog.at_level(logging.WARNING, logger="carta_scripting"):
        views = session.views()

    assert [view.image_id for view in views] == [10, 20]
    assert [record.getMessage() for record in caplog.records] == [
        "Skipping unsupported PV_PREVIEW view at index 1."
    ]
    assert capsys.readouterr().out == ""


def test_image_list_is_deprecated_and_calls_images(session, mocker):
    images = mocker.patch.object(session, "images", return_value=["image"])

    with pytest.warns(DeprecationWarning) as warning:
        assert session.image_list() == ["image"]

    assert str(warning[0].message) == (
        "Session.image_list() is deprecated; use Session.images() for images, "
        "Session.views() for all views, or Session.color_blendings() for color blendings."
    )
    images.assert_called_once_with()


def test_image_by_id_is_deprecated_and_calls_view_by_id(session, mocker):
    view_by_id = mocker.patch.object(session, "view_by_id", return_value=Image(session, 12))

    with pytest.warns(
        DeprecationWarning,
        match=r"Session.image_by_id\(\) is deprecated; use Session.view_by_id\(image_id=image_id\) instead\.",
    ):
        image = session.image_by_id(12)

    assert image.image_id == 12
    view_by_id.assert_called_once_with(image_id=12)


@pytest.mark.parametrize("image_id", [-1, 1.5, "12"])
def test_image_by_id_rejects_invalid_ids(session, image_id):
    with pytest.warns(DeprecationWarning):
        with pytest.raises(CartaValidationFailed):
            session.image_by_id(image_id)


def test_views_empty(session, get_value):
    get_value.return_value = []
    assert session.views() == []
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_views_uses_one_summary_for_explicit_indices(session, get_value):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": ImageType.COLOR_BLENDING, "id": 3},
        {"type": ImageType.FRAME, "id": 20},
    ]

    views = session.views(view_indices=[2, 0, 2])

    assert [
        (type(view), view.image_id if isinstance(view, Image) else view.color_blending_id)
        for view in views
    ] == [(Image, 20), (Image, 10), (Image, 20)]
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_views_explicit_indices_list_all_out_of_range(session, get_value):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
    ]

    with pytest.raises(IndexError) as exc_info:
        session.views(view_indices=[2, 0, 1])

    assert str(exc_info.value) == "No views with indices [2, 1] are open."

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_views_explicit_indices_raise_for_unsupported_type(session, get_value):
    get_value.return_value = [
        {"type": ImageType.PV_PREVIEW, "id": -2}
    ]

    with pytest.raises(NotImplementedError):
        session.views(view_indices=[0])

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


@pytest.mark.parametrize("view_indices", [[-1], [1.5], ["1"]])
def test_views_rejects_invalid_indices(session, get_value, view_indices):
    with pytest.raises(CartaValidationFailed):
        session.views(view_indices=view_indices)

    get_value.assert_not_called()


def test_images_uses_frontend_frame_names(session, get_value):
    get_value.return_value = [
        {"value": 10, "label": "Image 10"},
        {"value": 20, "label": "Image 20"},
    ]

    images = session.images()

    assert [image.image_id for image in images] == [10, 20]
    get_value.assert_called_once_with(
        "frameNames"
    )


def test_images_uses_frame_names_for_explicit_ids(session, get_value):
    get_value.return_value = [
        {"value": 10, "label": "Image 10"},
        {"value": 20, "label": "Image 20"},
    ]

    images = session.images(image_ids=[20, 10, 20])

    assert [image.image_id for image in images] == [20, 10, 20]
    get_value.assert_called_once_with("frameNames")


def test_images_list_all_closed_explicit_ids(session, get_value):
    get_value.return_value = [{"value": 10, "label": "Image 10"}]

    with pytest.raises(RuntimeError) as exc_info:
        session.images(image_ids=[30, 10, 20])

    assert str(exc_info.value) == "No images with image_ids [30, 20] are open."

    get_value.assert_called_once_with("frameNames")


def test_color_blendings_uses_frontend_image_list_summary(
    session, get_value
):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": ImageType.COLOR_BLENDING, "id": 3},
        {"type": ImageType.COLOR_BLENDING, "id": 7},
    ]

    color_blendings = session.color_blendings()

    assert [
        color_blending.color_blending_id
        for color_blending in color_blendings
    ] == [3, 7]
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_color_blendings_uses_image_list_summary_for_explicit_ids(
    session, get_value
):
    get_value.return_value = [
        {"type": ImageType.FRAME, "id": 10},
        {"type": ImageType.COLOR_BLENDING, "id": 3},
        {"type": ImageType.COLOR_BLENDING, "id": 7},
    ]

    color_blendings = session.color_blendings([7, 3, 7])

    assert [
        color_blending.color_blending_id
        for color_blending in color_blendings
    ] == [7, 3, 7]
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_color_blendings_list_all_closed_explicit_ids(session, get_value):
    get_value.return_value = [
        {"type": ImageType.COLOR_BLENDING, "id": 3}
    ]

    with pytest.raises(RuntimeError) as exc_info:
        session.color_blendings([7, 3, 5])

    assert (
        str(exc_info.value)
        == "No color blendings with color_blending_ids [7, 5] are open."
    )

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary"
    )


def test_find_view_index_single_round_trip(session, call_action):
    call_action.side_effect = [2, 1]

    assert session._find_view_index(ImageType.FRAME, 3) == 2
    assert session._find_view_index(ImageType.COLOR_BLENDING, 7) == 1
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


def test_find_view_index_raises_when_missing(session, call_action):
    call_action.return_value = -1
    with pytest.raises(RuntimeError):
        session._find_view_index(ImageType.FRAME, 99)


# session.view_by_id


def test_view_by_id_requires_exactly_one_keyword(session, get_value):
    # Zero keywords -> ValueError with all three names listed.
    with pytest.raises(ValueError) as e:
        session.view_by_id()
    for name in ("view_index", "image_id", "color_blending_id"):
        assert name in str(e.value)
    assert "got 0 with values {}" in str(e.value)
    # Multiple keywords -> ValueError.
    with pytest.raises(ValueError) as e:
        session.view_by_id(image_id=1, color_blending_id=2)
    assert "'image_id': 1" in str(e.value)
    assert "'color_blending_id': 2" in str(e.value)


def test_view_by_id_rejects_positional(session):
    with pytest.raises(TypeError):
        session.view_by_id(0)


@pytest.mark.parametrize("keyword", [
    "view_index",
    "image_id",
    "color_blending_id",
])
@pytest.mark.parametrize("value", [-1, 1.5, "1"])
def test_view_by_id_rejects_invalid_identifier(
    session, get_value, keyword, value
):
    with pytest.raises(CartaValidationFailed):
        session.view_by_id(**{keyword: value})

    get_value.assert_not_called()


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
def test_view_by_id_by_view_index(
    session, get_value, entry, expected_type, expected_id
):
    get_value.return_value = entry

    img = session.view_by_id(view_index=0)
    assert isinstance(img, expected_type)
    assert (
        img.image_id if expected_type is Image else img.color_blending_id
    ) == expected_id
    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary[0]"
    )


def test_view_by_id_by_view_index_out_of_range(session, get_value):
    get_value.side_effect = CartaBadResponse("undefined")

    with pytest.raises(IndexError):
        session.view_by_id(view_index=99)

    get_value.assert_called_once_with(
        "imageViewConfigStore.imageListSummary[99]"
    )


def test_view_by_id_by_view_index_raises_on_unsupported_type(
    session, get_value
):
    get_value.return_value = {"type": ImageType.PV_PREVIEW, "id": -2}

    with pytest.raises(NotImplementedError):
        session.view_by_id(view_index=0)


def test_view_by_id_by_image_id(session, get_value):
    get_value.return_value = 20

    img = session.view_by_id(image_id=20)
    assert isinstance(img, Image)
    assert img.image_id == 20
    get_value.assert_called_once_with(
        "frameMap[20]",
        return_path="frameInfo.fileId",
    )


def test_view_by_id_by_image_id_no_cross_type_fallback(session, get_value):
    get_value.side_effect = CartaBadResponse("undefined")

    with pytest.raises(RuntimeError):
        session.view_by_id(image_id=7)


def test_view_by_id_by_color_blending_id(session, get_value):
    get_value.return_value = 7

    cb = session.view_by_id(color_blending_id=7)
    assert isinstance(cb, ColorBlending)
    assert cb.color_blending_id == 7
    get_value.assert_called_once_with(
        "imageViewConfigStore.colorBlendingImageMap[7]",
        return_path="id",
    )


def test_view_by_id_by_color_blending_id_no_cross_type_fallback(
    session, get_value
):
    get_value.side_effect = CartaBadResponse("undefined")

    with pytest.raises(RuntimeError):
        session.view_by_id(color_blending_id=10)


def test_view_by_id_uses_targeted_frontend_lookups(session, get_value):
    get_value.side_effect = [
        {"type": ImageType.FRAME, "id": 10},
        10,
        7,
    ]

    session.view_by_id(view_index=0)
    session.view_by_id(image_id=10)
    session.view_by_id(color_blending_id=7)

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


# session.active_view


def test_active_view_returns_image_when_image_active(session, get_value):
    get_value.side_effect = [
        ImageType.FRAME,
        12,
    ]
    active = session.active_view()
    assert isinstance(active, Image)
    assert active.image_id == 12
    assert [call.args for call in get_value.call_args_list] == [
        ("activeImage.type",),
        ("activeImage.store.id",),
    ]


def test_active_view_returns_color_blending_when_color_blending_active(
    session, get_value
):
    get_value.side_effect = [
        ImageType.COLOR_BLENDING,
        3,
    ]
    active = session.active_view()
    assert isinstance(active, ColorBlending)
    assert active.color_blending_id == 3
    assert [call.args for call in get_value.call_args_list] == [
        ("activeImage.type",),
        ("activeImage.store.id",),
    ]


def test_active_view_raises_on_unsupported_type(session, get_value):
    get_value.side_effect = [
        ImageType.PV_PREVIEW,
        -2,
    ]
    with pytest.raises(NotImplementedError):
        session.active_view()


def test_active_frame_is_deprecated_and_returns_active_image(session, mocker):
    active = Image(session, 12)
    active_view = mocker.patch.object(session, "active_view", return_value=active)

    with pytest.warns(
        DeprecationWarning,
        match=r"Session.active_frame\(\) is deprecated; use Session.active_view\(\) instead\.",
    ):
        assert session.active_frame() is active

    active_view.assert_called_once_with()


def test_active_frame_raises_for_non_image_active_view(session, mocker):
    active_view = mocker.patch.object(
        session, "active_view", return_value=ColorBlending(session, 3)
    )

    with pytest.warns(DeprecationWarning):
        with pytest.raises(TypeError, match="currently active view is not an image"):
            session.active_frame()

    active_view.assert_called_once_with()


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


@pytest.mark.parametrize("open_image_count,layer_count,expected_colormap_set", [
    (1, 1, ColormapSet.RGB),
    (3, 3, ColormapSet.RGB),
    (5, 3, ColormapSet.RGB),
    (5, 4, ColormapSet.RAINBOW),
])
def test_create_color_blending_calls_frontend_create_action(session, mocker, open_image_count, layer_count, expected_colormap_set):
    get_value = mocker.patch.object(
        session,
        "get_value",
        side_effect=[
            open_image_count,
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


def test_create_color_blending_with_images_sets_reference_and_matching(
    session, mocker
):
    images = [Image(session, 10), Image(session, 20), Image(session, 30)]
    for image in images:
        mocker.patch.object(image, "make_spatial_reference")
        mocker.patch.object(image, "set_spatial_matching")
    mocker.patch.object(session, "call_action", return_value=123)
    mocker.patch.object(
        ColorBlending,
        "depth",
        new_callable=mocker.PropertyMock,
        side_effect=[4, 3],
    )
    delete_layer = mocker.patch.object(ColorBlending, "delete_layer")
    add_layer = mocker.patch.object(ColorBlending, "add_layer")
    mock_set_colormap = mocker.patch.object(ColorBlending, "set_colormap_set")

    result = session.create_color_blending(images=images)

    images[0].make_spatial_reference.assert_called_once_with()
    images[0].set_spatial_matching.assert_not_called()
    images[1].set_spatial_matching.assert_called_once_with(True)
    images[2].set_spatial_matching.assert_called_once_with(True)
    assert delete_layer.call_args_list == [
        mocker.call(3),
        mocker.call(2),
        mocker.call(1),
    ]
    assert add_layer.call_args_list == [
        mocker.call(images[1]),
        mocker.call(images[2]),
    ]
    mock_set_colormap.assert_called_once_with(ColormapSet.RGB)
    assert isinstance(result, ColorBlending)


@pytest.mark.parametrize("images", [[], [object()]])
def test_create_color_blending_rejects_invalid_images(
    session, mocker, images
):
    call_action = mocker.patch.object(session, "call_action")

    with pytest.raises(CartaValidationFailed):
        session.create_color_blending(images=images)

    call_action.assert_not_called()


def test_create_color_blending_rejects_duplicate_images(session, mocker):
    images = [Image(session, 10), Image(session, 20), Image(session, 10)]
    call_action = mocker.patch.object(session, "call_action")

    with pytest.raises(
        CartaValidationFailed,
        match="must not contain duplicate images",
    ):
        session.create_color_blending(images=images)

    call_action.assert_not_called()


def test_create_color_blending_rejects_image_from_another_session(
    session, mocker
):
    images = [Image(session, 10), Image(Session(1, None), 20)]
    call_action = mocker.patch.object(session, "call_action")

    with pytest.raises(CartaValidationFailed, match="current session"):
        session.create_color_blending(images=images)

    call_action.assert_not_called()


def test_create_color_blending_raises_when_no_images_are_open(session, mocker):
    get_value = mocker.patch.object(session, "get_value", return_value=0)
    call_action = mocker.patch.object(session, "call_action")
    mock_set_colormap = mocker.patch.object(ColorBlending, "set_colormap_set")

    with pytest.raises(CartaActionFailed, match="No images are open"):
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
    assert hypercube.image_id == 123


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
    assert hypercube.image_id == 123


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
