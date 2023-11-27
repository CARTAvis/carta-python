import pytest

from carta.image import Image
from carta.util import Macro
from carta.constants import ComplexComponent as CC, Polarization as Pol

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
    ("overlay", "WCSOverlay"),
])
def test_subobjects(session, name, classname):
    assert getattr(session, name).__class__.__name__ == classname

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


def test_ls(session, method, call_action, get_value):
    method("pwd", ["/current/dir"])
    get_value.side_effect = [{"files": [{"name": "foo.fits"}, {"name": "bar.fits"}], "subdirectories": [{"name": "baz"}]}]
    ls = session.ls()
    call_action.assert_called_with("fileBrowserStore.getFileList", "/current/dir")
    get_value.assert_called_with("fileBrowserStore.fileList")
    assert ls == ["bar.fits", "baz/", "foo.fits"]


def test_cd(session, method, call_action):
    method("resolve_file_path", ["/resolved/file/path"])
    session.cd("original/path")
    call_action.assert_called_with("fileBrowserStore.saveStartingDirectory", "/resolved/file/path")

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
