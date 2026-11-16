import importlib
import sys
from unittest import mock

import pytest

import carta

SELENIUM_MODULES = ("selenium", "selenium.webdriver", "selenium.common", "selenium.common.exceptions", "selenium.webdriver.chrome", "selenium.webdriver.chrome.options", "selenium.webdriver.chrome.service", "selenium.webdriver.common", "selenium.webdriver.common.by")


@pytest.fixture
def browser():
    """Import carta.browser, with selenium stubbed if it is not installed.

    Selenium is an optional dependency (the "browser" extra) and is not
    installed for the unit tests. The stubs and the imported module are removed
    afterwards, so that other tests are not affected.
    """
    try:
        import selenium  # noqa: F401
        stubs = {}
    except ImportError:
        stubs = {name: mock.MagicMock() for name in SELENIUM_MODULES}

    with mock.patch.dict(sys.modules, stubs):
        sys.modules.pop("carta.browser", None)
        yield importlib.import_module("carta.browser")
        sys.modules.pop("carta.browser", None)
    if hasattr(carta, "browser"):
        del carta.browser


@pytest.fixture
def chrome_driver(mocker, browser):
    return mocker.patch.object(browser.webdriver, "Chrome")


@pytest.fixture
def service(mocker, browser):
    return mocker.patch.object(browser, "Service")


def test_chrome_passes_driver_path_as_service(browser, chrome_driver, service):
    browser.Chrome(driver_path="/usr/bin/chromedriver")

    service.assert_called_once_with(executable_path="/usr/bin/chromedriver")
    kwargs = chrome_driver.call_args.kwargs
    assert kwargs["service"] is service.return_value
    assert "executable_path" not in kwargs


def test_chrome_without_driver_path_uses_default_service(browser, chrome_driver, service):
    browser.Chrome()

    service.assert_not_called()
    assert "service" not in chrome_driver.call_args.kwargs
    assert "executable_path" not in chrome_driver.call_args.kwargs

