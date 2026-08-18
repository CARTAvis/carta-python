import pytest

from carta.constants import VersionMismatchAction


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
    session_class.assert_called_once_with(123, protocol, browser=browser, backend=None)
    session._validate_session.assert_called_once_with(
        timeout=5,
        minimum_carta_version=None,
        version_mismatch_action=VersionMismatchAction.WARN,
    )
    assert browser.driver.closed is False


def test_new_session_from_url_passes_minimum_and_mismatch_action(
    mocker, browser_module
):
    browser = make_browser(browser_module.Browser)
    protocol = mocker.Mock(controller_auth=False, frontend_url="http://localhost:3000")
    mocker.patch("carta.browser.Protocol", return_value=protocol)
    session = mocker.Mock()
    mocker.patch("carta.browser.Session", return_value=session)

    browser.new_session_from_url(
        "http://localhost:3000?token=x",
        minimum_carta_version="6.1.0",
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    session._validate_session.assert_called_once_with(
        timeout=10,
        minimum_carta_version="6.1.0",
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
        frontend_url="http://localhost:3000",
        token="token",
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
        "token",
        backend=backend,
        timeout=10,
        debug_no_auth=False,
        connection_check_timeout=10,
        minimum_carta_version=None,
        version_mismatch_action=VersionMismatchAction.WARN,
    )


def test_new_session_with_backend_preserves_error_when_backend_stop_fails(
    mocker, browser_module, util_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(
        frontend_url="http://localhost:3000",
        token="token",
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


def test_new_session_with_backend_passes_version_options(
    mocker, browser_module
):
    browser = make_browser(browser_module.Browser)
    backend = mocker.Mock(
        frontend_url="http://localhost:3000",
        token="token",
        debug_no_auth=False,
        errors=[],
    )
    backend.start.return_value = True
    mocker.patch("carta.browser.Backend", return_value=backend)
    session = mocker.Mock()
    new_session = mocker.patch.object(browser, "new_session_from_url", return_value=session)

    result = browser.new_session_with_backend(
        connection_check_timeout=4,
        minimum_carta_version="6.1.0",
        version_mismatch_action=VersionMismatchAction.ERROR,
    )

    assert result is session
    new_session.assert_called_once_with(
        "http://localhost:3000",
        "token",
        backend=backend,
        timeout=10,
        debug_no_auth=False,
        connection_check_timeout=4,
        minimum_carta_version="6.1.0",
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
