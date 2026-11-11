from carta.backend import Backend
from carta.token import BackendToken, ControllerToken
import inspect
import builtins
import importlib.util
import pathlib
import sys

import pytest

from carta.constants import VersionMismatchAction
from carta.util import CartaBadSession, CartaValidationFailed


class FakeElement:
    def __init__(self, text):
        self.text = text

    def get_attribute(self, name):
        assert name == "textContent"
        return self.text


class FakeDriver:
    def __init__(self, session_id="123", close_error=None):
        self.session_id = session_id
        self.close_error = close_error
        self.urls = []
        self.closed = False
        self.cookies = []

    def get(self, url):
        self.urls.append(url)

    def add_cookie(self, cookie):
        self.cookies.append(cookie)

    def find_element(self, by, value):
        return FakeElement(self.session_id)

    def quit(self):
        if self.close_error:
            raise self.close_error
        self.closed = True


@pytest.fixture
def browser_module():
    pytest.importorskip("selenium")
    import carta.browser

    return carta.browser


@pytest.fixture
def util_module():
    pytest.importorskip("selenium")
    import carta.util

    return carta.util


def make_browser(browser_class, session_id="123", close_error=None):
    browser = browser_class.__new__(browser_class)
    browser.driver = FakeDriver(session_id=session_id, close_error=close_error)
    return browser


def test_browser_imports_without_selenium(monkeypatch):
    original_import = builtins.__import__

    def import_without_selenium(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "selenium" or name.startswith("selenium."):
            raise ModuleNotFoundError("No module named 'selenium'", name="selenium")
        return original_import(name, globals, locals, fromlist, level)

    module_name = "carta._browser_without_selenium_test"
    browser_path = pathlib.Path(__file__).resolve().parents[1] / "carta" / "browser.py"
    spec = importlib.util.spec_from_file_location(module_name, browser_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    monkeypatch.setattr(builtins, "__import__", import_without_selenium)

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)

    assert module.webdriver is None
    with pytest.raises(CartaBadSession) as error:
        module._require_selenium()

    assert error.value.__cause__ is module._SELENIUM_IMPORT_ERROR


def test_new_session_from_url_runs_connection_check_after_parsing_session_id(
    mocker, browser_module
):
    browser = make_browser(browser_module.Browser)
    protocol = mocker.Mock(controller_auth=False, frontend_url="http://localhost:3000")
    mocker.patch("carta.browser.Protocol", return_value=protocol)
    session = mocker.Mock()
    session_class = mocker.patch("carta.browser.Session", return_value=session)

    result = browser.new_session_from_url(
        "http://localhost:3000?token=x",
        connection_check_timeout=5,
    )

    assert result is session
    session_class.assert_called_once_with(123, protocol)
    session._validate_session.assert_called_once_with(
        timeout=5,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )
    session._attach_resources.assert_called_once_with(browser=browser, backend=None)
    assert browser.driver.closed is False


def test_new_session_from_url_passes_mismatch_action(
    mocker, browser_module
):
    browser = make_browser(browser_module.Browser)
    protocol = mocker.Mock(controller_auth=False, frontend_url="http://localhost:3000")
    mocker.patch("carta.browser.Protocol", return_value=protocol)
    session = mocker.Mock()
    mocker.patch("carta.browser.Session", return_value=session)

    browser.new_session_from_url(
        "http://localhost:3000?token=x",
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    session._validate_session.assert_called_once_with(
        timeout=10,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_new_session_from_url_closes_browser_and_preserves_validation_error(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    protocol = mocker.Mock(controller_auth=False, frontend_url="http://localhost:3000")
    mocker.patch("carta.browser.Protocol", return_value=protocol)
    session = mocker.Mock()
    session._validate_session.side_effect = util_module.CartaUnsupportedVersion("bad version")
    mocker.patch("carta.browser.Session", return_value=session)

    with pytest.raises(util_module.CartaUnsupportedVersion):
        browser.new_session_from_url(
            "http://localhost:3000?token=x",
        )

    assert browser.driver.closed is True


def test_new_session_from_url_preserves_validation_error_when_close_fails(
    mocker, browser_module, util_module
):
    close_error = RuntimeError("close failed")
    browser = make_browser(browser_module.Browser, close_error=close_error)
    protocol = mocker.Mock(controller_auth=False, frontend_url="http://localhost:3000")
    mocker.patch("carta.browser.Protocol", return_value=protocol)
    session = mocker.Mock()
    session._validate_session.side_effect = util_module.CartaUnsupportedVersion("bad version")
    mocker.patch("carta.browser.Session", return_value=session)

    with pytest.raises(util_module.CartaUnsupportedVersion):
        browser.new_session_from_url(
            "http://localhost:3000?token=x",
        )


def test_new_session_with_backend_stops_backend_when_session_creation_fails(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(
        spec=Backend,
        frontend_url="http://localhost:3000",
        token=BackendToken("token"),
        debug_no_auth=False,
        errors=[],
    )
    backend.start.return_value = True
    mocker.patch("carta.browser.Backend", return_value=backend)
    mocker.patch.object(
        browser,
        "new_session_from_url",
        side_effect=util_module.CartaBadSession("startup failed"),
    )

    with pytest.raises(util_module.CartaBadSession):
        browser.new_session_with_backend()

    backend.stop.assert_called_once_with()
    browser.new_session_from_url.assert_called_once_with(
        "http://localhost:3000",
        backend.token,
        backend=backend,
        timeout=10,
        debug_no_auth=False,
        connection_check_timeout=10,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_new_session_with_backend_preserves_error_when_backend_stop_fails(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(
        spec=Backend,
        frontend_url="http://localhost:3000",
        token=BackendToken("token"),
        debug_no_auth=False,
        errors=[],
    )
    backend.start.return_value = True
    backend.stop.side_effect = RuntimeError("stop failed")
    mocker.patch("carta.browser.Backend", return_value=backend)
    startup_error = util_module.CartaBadSession("startup failed")
    mocker.patch.object(browser, "new_session_from_url", side_effect=startup_error)

    with pytest.raises(util_module.CartaBadSession, match="startup failed"):
        browser.new_session_with_backend()

    backend.stop.assert_called_once_with()


def test_new_session_with_backend_attaches_resources_only_after_validation(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(
        spec=Backend,
        frontend_url="http://localhost:3000",
        token=BackendToken("token"),
        debug_no_auth=True,
        errors=[],
    )
    backend.start.return_value = True
    mocker.patch("carta.browser.Backend", return_value=backend)

    class FailingSession(browser_module.Session):
        def _validate_session(self, **kwargs):
            assert self._browser is None
            assert self._backend is None
            raise util_module.CartaBadSession("startup failed")

    mocker.patch("carta.browser.Session", FailingSession)

    with pytest.raises(util_module.CartaBadSession, match="startup failed"):
        browser.new_session_with_backend()

    assert browser.driver.closed is True
    backend.stop.assert_called_once_with()


def test_new_session_with_backend_passes_version_options(
    mocker, browser_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(
        spec=Backend,
        frontend_url="http://localhost:3000",
        token=BackendToken("token"),
        debug_no_auth=False,
        errors=[],
    )
    backend.start.return_value = True
    mocker.patch("carta.browser.Backend", return_value=backend)
    session = mocker.Mock()
    new_session = mocker.patch.object(browser, "new_session_from_url", return_value=session)

    result = browser.new_session_with_backend(
        connection_check_timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    assert result is session
    new_session.assert_called_once_with(
        "http://localhost:3000",
        backend.token,
        backend=backend,
        timeout=10,
        debug_no_auth=False,
        connection_check_timeout=4,
        version_mismatch_action=VersionMismatchAction.ERROR,
    )


def test_new_session_with_backend_stops_backend_when_frontend_url_missing(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(frontend_url=None, errors=[])
    backend.start.return_value = True
    mocker.patch("carta.browser.Backend", return_value=backend)

    with pytest.raises(util_module.CartaBadSession):
        browser.new_session_with_backend()

    backend.stop.assert_called_once_with()


def test_new_session_with_backend_preserves_missing_url_error_when_backend_stop_fails(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(frontend_url=None, errors=[])
    backend.start.return_value = True
    backend.stop.side_effect = RuntimeError("stop failed")
    mocker.patch("carta.browser.Backend", return_value=backend)

    with pytest.raises(
        util_module.CartaBadSession,
        match="Could not parse CARTA frontend URL from backend output",
    ):
        browser.new_session_with_backend()

    backend.stop.assert_called_once_with()
    assert browser.driver.closed is True


@pytest.mark.parametrize("method,args", [
    ("new_session_from_url", ("http://localhost:3000?token=x",)),
    ("new_session_with_backend", ()),
])
@pytest.mark.parametrize("options", [
    {"connection_check_timeout": -1},
    {"connection_check_timeout": 0},
    {"connection_check_timeout": "invalid"},
    {"version_mismatch_action": "invalid"},
])
@pytest.mark.parametrize("positional", [False, True])
def test_browser_creation_rejects_options_before_side_effects(method, args, options, positional, mocker, browser_module):
    backend = mocker.patch("carta.browser.Backend")
    protocol = mocker.patch("carta.browser.Protocol")
    browser = make_browser(browser_module.Browser)
    browser.driver = mocker.Mock()

    create_session = getattr(browser, method)
    if positional:
        bound = inspect.signature(create_session).bind(*args, **options)
        bound.apply_defaults()
        args, options = bound.args, bound.kwargs

    with pytest.raises(CartaValidationFailed):
        create_session(*args, **options)

    backend.assert_not_called()
    protocol.assert_not_called()
    assert browser.driver.mock_calls == []


@pytest.mark.parametrize("method,options", [
    ("new_session_from_url", {"frontend_url": None}),
    ("new_session_from_url", {"token": "token"}),
    ("new_session_from_url", {"backend": object()}),
    ("new_session_from_url", {"timeout": -1}),
    ("new_session_from_url", {"debug_no_auth": "invalid"}),
    ("new_session_with_backend", {"executable_path": None}),
    ("new_session_with_backend", {"remote_host": 123}),
    ("new_session_with_backend", {"params": None}),
    ("new_session_with_backend", {"timeout": -1}),
    ("new_session_with_backend", {"token": "token"}),
    ("new_session_with_backend", {"frontend_url_timeout": -1}),
])
@pytest.mark.parametrize("positional", [False, True])
def test_browser_creation_validates_all_parameters_before_side_effects(method, options, positional, mocker, browser_module):
    backend = mocker.patch("carta.browser.Backend")
    protocol = mocker.patch("carta.browser.Protocol")
    browser = make_browser(browser_module.Browser)
    browser.driver = mocker.Mock()
    values = {"frontend_url": "http://localhost:3000?token=x"} if method == "new_session_from_url" else {}
    values.update(options)
    create_session = getattr(browser, method)
    bound = inspect.signature(create_session).bind(**values)
    bound.apply_defaults()

    with pytest.raises(CartaValidationFailed):
        if positional:
            create_session(*bound.args, **bound.kwargs)
        else:
            create_session(**values)

    backend.assert_not_called()
    protocol.assert_not_called()
    assert browser.driver.mock_calls == []


@pytest.mark.parametrize("params_kind", ["tuple", "list", "generator"])
def test_browser_startup_accepts_numeric_params_and_zero_waits(params_kind, mocker, browser_module):
    token = BackendToken("token")
    backend = mocker.Mock(spec=Backend, frontend_url="http://localhost:3000", token=token, debug_no_auth=False)
    backend.start.return_value = True
    backend_class = mocker.patch("carta.browser.Backend", return_value=backend)
    browser = make_browser(browser_module.Browser)
    expected = mocker.Mock()
    new_session = mocker.patch.object(browser, "new_session_from_url", return_value=expected)
    params = {"tuple": ("--verbosity", 5), "list": ["--verbosity", 5], "generator": iter(("--verbosity", 5))}[params_kind]

    result = browser.new_session_with_backend(params=params, token=token, timeout=0, frontend_url_timeout=0)

    assert result is expected
    backend_class.assert_called_once_with(("--no_browser", "--enable_scripting", "--verbosity", 5), "carta", None, token, frontend_url_timeout=0, session_creation_timeout=0)
    new_session.assert_called_once_with("http://localhost:3000", token, backend=backend, timeout=0, debug_no_auth=False, connection_check_timeout=10, version_mismatch_action=VersionMismatchAction.ERROR)


@pytest.mark.parametrize("token_class", [BackendToken, ControllerToken])
def test_new_session_from_url_accepts_token_types_and_backend(token_class, mocker, browser_module):
    token = token_class("token")
    backend = mocker.Mock(spec=Backend)
    protocol = mocker.Mock(controller_auth=False, frontend_url="http://localhost:3000")
    protocol_class = mocker.patch("carta.browser.Protocol", return_value=protocol)
    session = mocker.Mock()
    mocker.patch("carta.browser.Session", return_value=session)
    browser = make_browser(browser_module.Browser)

    result = browser.new_session_from_url("http://localhost:3000", token=token, backend=backend, timeout=0.1, debug_no_auth=False)

    assert result is session
    protocol_class.assert_called_once_with("http://localhost:3000", token, debug_no_auth=False)
    session._attach_resources.assert_called_once_with(browser=browser, backend=backend)
