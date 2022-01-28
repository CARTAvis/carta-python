"""This module provides browser objects which can be used to create new sessions. It depends on the ``selenium`` library. The desired browser and its corresponding web driver also have to be installed."""

import re
import time
import os
import subprocess
import pathlib
import signal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

from .util import CartaBadSession
from .client import Session
from .protocol import Protocol
from .token import BackendToken


class Backend:
    """Helper class for managing a CARTA backend process.
    
    You should not need to instantiate this directly; it is created on demand by a :obj:`carta.browser.Browser` object.
    
    Parameters
    ----------
    params : iterable
        Parameters to pass to the CARTA backend process.
    executable_path : string
        The path to the backend executable. Default: ``"carta"``.
    remote_host : string
        If this is set, an attempt will be made to start the backend over ``ssh`` on this host.
    token : :obj:`carta.token.BackendToken`
        If this is set, this will be used as the security token and no attempt will be made to parse the token from the backend output.
    
    Attributes
    ----------
    proc : :obj:`subprocess.Popen`
        The backend subprocess object. Set by the :obj:`carta.browser.Backend.start` method.
    frontend_url : string
        The URL of the running frontend, parsed from the output of the backend process. Set by the :obj:`carta.browser.Backend.start` method.
    token : :obj:`carta.token.BackendToken`
        The security token of the running backend, either parsed from the output of the backend process and set by the :obj:`carta.browser.Backend.start` method, or overridden with a parameter.
    debug_no_auth : boolean
        If this is set, the backend will accept HTTP connections with no authentication token. This is provided for debugging purposes only and should not be used under normal circumstances. This value is automatically detected from the provided backend parameters.
    output : list of strings
        All output of the backend process, split into lines, terminated by newline characters.
    errors : list of strings
        Error output of the backend process, split into lines, terminated by newline characters.
        
    Returns
    -------
    :obj:`carta.browser.Backend`
        A backend object with a process which has not been started. 
    
    """
    FRONTEND_URL = re.compile(r"CARTA is accessible at (http://.*?:\d+/\?token=(.*))")
    FRONTEND_URL_NO_AUTH = re.compile(r"CARTA is accessible at (http://(.*?):\d+.*)")
    
    def __init__(self, params, executable_path="carta", remote_host=None, token=None):
        self.proc = None
        self.frontend_url = None
        self.token = token
        self.debug_no_auth = ("--debug_no_auth" in params)
        self.output = []
        self.errors = []
        
        ssh_cmd = ("ssh", "-tt", remote_host) if remote_host is not None else tuple()
        self.cmd = tuple(str(p) for p in (*ssh_cmd, executable_path, *params))
            
    def start(self):
        """Start the backend process.
        
        This method creates the subprocess object and parses the backend host and the frontend URL from the process output.
        """
        # TODO currently we log everything to stdout, but maybe we shouldn't
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, cwd=pathlib.Path.home(), preexec_fn=os.setpgrp)
        os.set_blocking(self.proc.stdout.fileno(), False)
        
        time.sleep(1)
        
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.decode()
            
            self.output.append(line)
            if "[error]" in line or "[critical]" in line:
                self.errors.append(line)
        
        if self.proc.poll() is not None:
            return False
        
        frontend_url_re = self.FRONTEND_URL if not self.debug_no_auth else self.FRONTEND_URL_NO_AUTH
        
        for line in self.output:
            m = frontend_url_re.search(line)
            if m:
                self.frontend_url, token_string = m.groups()
                break
        
        if self.token is None and not self.debug_no_auth:
            self.token = BackendToken(token_string)
        
        return True
    
    def stop(self):
        """Stop the backend process.
        
        This method terminates the backend process if it exists and is running.
        """
        
        pgrp = os.getpgid(self.proc.pid)
        os.killpg(pgrp, signal.SIGINT)
        self.proc.wait()

# TODO split backend to separate file
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
        
        You can use :obj:`carta.client.Session.create`, which wraps this method.
        
        Parameters
        ----------
        frontend_url : string
            The URL of the frontend.
        token : :obj:`carta.token.Token`, optional
            The security token used by the CARTA instance. May be omitted if the URL contains a token.
        backend : :obj:`carta.browser.Backend`
            The backend object associated with this session, if any. This is set if this method is called from :obj:`carta.browser.Browser.new_session_with_backend`.
        timeout : number, optional
            The number of seconds to spend parsing the frontend for connection information. 10 seconds by default.
        debug_no_auth : boolean
            This should be set if the backend has been started with the ``--debug_no_auth`` option. This is provided for debugging purposes only and should not be used under normal circumstances. You must still pass in a *token* argument if you use this option, but you may set it to ``None``. It will be ignored.
            
        Returns
        -------
        :obj:`carta.client.Session`
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
        
        You can use :obj:`carta.client.Session.start_and_create`, which wraps this method. This method starts a backend process, parses the frontend URL from the output, and calls :obj:`carta.browser.Browser.new_session_from_url`.
        
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
        :obj:`carta.client.Session`
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
    """
    def __init__(self, headless=True, browser_path=None, driver_path=None):
        options = Options()
        if headless:
            options.add_argument("--headless")
        if browser_path:
            options.binary_location = browser_path

        kwargs = {
            "options": options,
        }

        if driver_path:
            kwargs["executable_path"] = driver_path

        super().__init__(webdriver.Chrome, **kwargs)
