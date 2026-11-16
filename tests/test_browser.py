import sys
from unittest import mock

import pytest

# Selenium is an optional dependency (the "browser" extra) and is not installed
# for the unit tests; stub it so that carta.browser can be imported.
try:
    import selenium  # noqa: F401
except ImportError:
    for name in ("selenium", "selenium.webdriver", "selenium.common", "selenium.common.exceptions", "selenium.webdriver.chrome", "selenium.webdriver.chrome.options", "selenium.webdriver.chrome.service", "selenium.webdriver.common", "selenium.webdriver.common.by"):
        sys.modules.setdefault(name, mock.MagicMock())

from carta import browser  # noqa: E402


@pytest.fixture
def chrome_driver(mocker):
    return mocker.patch.object(browser.webdriver, "Chrome")


@pytest.fixture
def service(mocker):
    return mocker.patch.object(browser, "Service")


def test_chrome_passes_driver_path_as_service(chrome_driver, service):
    browser.Chrome(driver_path="/usr/bin/chromedriver")

    service.assert_called_once_with(executable_path="/usr/bin/chromedriver")
    kwargs = chrome_driver.call_args.kwargs
    assert kwargs["service"] is service.return_value
    assert "executable_path" not in kwargs


def test_chrome_without_driver_path_uses_default_service(chrome_driver, service):
    browser.Chrome()

    service.assert_not_called()
    assert "service" not in chrome_driver.call_args.kwargs
    assert "executable_path" not in chrome_driver.call_args.kwargs
