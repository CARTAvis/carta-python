"""This module provides browser objects which can be used to create new sessions. It depends on the ``selenium`` library. The desired browser and its corresponding web driver also have to be installed."""

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

from .backend import Backend
from .util import CartaBadSession
from .protocol import Protocol
from .session import Session

class Browser:
    """The top-level browser class.
    
    Some common use cases are provided as subclasses, but you may instantiate this class directly to create a browser with custom configuration.
    
    Parameters
    ----------
    driver_class : a selenium web driver class
        The class to use for the browser driver.
    **kwargs
        Keyword arguments which will be passed to the driver class constructor.
        
    Attributes
    ----------
    driver : :obj:`selenium.webdriver.remote.webdriver.WebDriver`
        The browser driver.
    """
    def __init__(self, driver_class, **kwargs):
        self.driver = driver_class(**kwargs)
    
    def new_session_from_url(self, frontend_url, token=None, backend=None, timeout=10, debug_no_auth=False):
        """Create a new session by connecting to an existing backend.
        
        You can use :obj:`carta.session.Session.create`, which wraps this method.
        
        Parameters
        ----------
        frontend_url : string
            The URL of the frontend.
        token : :obj:`carta.token.Token`, optional
            The security token used by the CARTA instance. May be omitted if the URL contains a token.
        backend : :obj:`carta.backend.Backend`
            The backend object associated with this session, if any. This is set if this method is called from :obj:`carta.browser.Browser.new_session_with_backend`.
        timeout : number, optional
            The number of seconds to spend parsing the frontend for connection information. 10 seconds by default.
        debug_no_auth : boolean
            Disable authentication. This should be set if the backend has been started with the ``--debug_no_auth`` option. This is provided for debugging purposes only and should not be used under normal circumstances.
            
        Returns
        -------
        :obj:`carta.session.Session`
            A session object connected to a new frontend session running in this browser.
            
        Raises
        ------
        CartaBadToken
            If an invalid token was provided.
        CartaBadUrl
            If an invalid URL was provided.
        CartaBadSession
            If the session object could not be created.
        """
                
        protocol = Protocol(frontend_url, token, debug_no_auth=debug_no_auth)
        
        if protocol.controller_auth:
            # A limitation of Selenium is that to add cookies for a domain you have to be at that domain already.
            self.driver.get(protocol.frontend_url)
            self.driver.add_cookie(protocol.cookie())

        self.driver.get(protocol.frontend_url)
        
        session_id = None
        
        start = time.time()
        last_error = ""
        
        # Keep trying until the displayed ID is not 0
        while not session_id:
            if time.time() - start > timeout:
                break
            
            try:
                # We can't use .text because Selenium is too clever to return the text of invisible elements.
                session_id = int(self.driver.find_element_by_id("info-session-id").get_attribute("textContent"))
            except (NoSuchElementException, ValueError) as e:
                last_error = str(e)
                time.sleep(1)
                continue # retry
        
        if not session_id:
            self.exit(f"Could not parse session ID from frontend. Last error: {last_error}")
                
        return Session(session_id, protocol, browser=self, backend=backend)
    
    def new_session_with_backend(self, executable_path="carta", remote_host=None, params=tuple(), timeout=10, token=None):
        """Create a new session after launching a new backend process.
        
        You can use :obj:`carta.session.Session.start_and_create`, which wraps this method. This method starts a backend process, parses the frontend URL from the output, and calls :obj:`carta.browser.Browser.new_session_from_url`.
        
        Parameters
        ----------
        executable_path : string, optional
            A custom path to the CARTA backend executable. The default is ``"carta"``.
        remote_host : string, optional
            A remote host where the backend process should be launched, which must be accessible through passwordless ssh. By default the backend process is launched on the local host.
        params : iterable, optional
            Additional parameters to be passed to the backend process. By default scripting is enabled and the automatic browser is disabled. The parameters are appended to the end of the command, so a positional parameter for a data directory can be included.
        timeout : number, optional
            The number of seconds to spend parsing the frontend for connection information. 10 seconds by default.
        token : :obj:`carta.token.BackendToken`, optional
            The security token to use. Parsed from the backend output by default.
            
        Returns
        -------
        :obj:`carta.session.Session`
            A session object connected to a new frontend session running in this browser.
            
        Raises
        ------
        CartaBadToken
            If an invalid token was provided.
        CartaBadUrl
            If an invalid URL was provided.
        CartaBadSession
            If the session object could not be created.
        """
        
        backend = Backend(("--no_browser", "--enable_scripting", *params), executable_path, remote_host, token)
        if not backend.start():
            self.exit(f"CARTA backend exited unexpectedly:\n{''.join(backend.errors)}")
        
        if backend.frontend_url is None:
            self.exit("Could not parse CARTA frontend URL from backend output.")
            
        return self.new_session_from_url(backend.frontend_url, backend.token, backend=backend, timeout=timeout, debug_no_auth=backend.debug_no_auth)
        
    def exit(self, msg):
        self.close()
        raise CartaBadSession(msg)
    
    def close(self):
        """Shut down the browser driver."""
        self.driver.quit()


class Chrome(Browser):
    """Chrome or Chromium, optionally headless.

    Parameters
    ----------
    headless : boolean, optional
        Run the browser headless (this is the default).
    browser_path : string, optional
        A path to a custom chrome or chromium executable.
    driver_path : string, optional
        A path to a custom chromedriver executable.
    options : iterable, optional
        Additional options. A list of strings, one per option (``--option`` or ``--option=argument``).
    """
    def __init__(self, headless=True, browser_path=None, driver_path=None, options=tuple()):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        if browser_path:
            chrome_options.binary_location = browser_path
        for opt in options:
            chrome_options.add_argument(opt)

        kwargs = {
            "options": chrome_options,
        }

        if driver_path:
            kwargs["executable_path"] = driver_path

        super().__init__(webdriver.Chrome, **kwargs)
