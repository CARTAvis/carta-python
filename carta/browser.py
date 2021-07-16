"""This module provides browser objects which can be used to create new sessions. It depends on the `selenium` library. The desired browser and its corresponding web driver also have to be installed."""

import re
import time
import os
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException

from .util import CartaScriptingException, logger
from .client import Session


class Backend:
    # TODO TODO TODO document this
    FRONTEND_URL = re.compile(r"[info] CARTA is accessible at (http://(.*?):\d+/?token=.*)\n")
    
    def __init__(self, params, executable_path="carta", remote_host=None):
        self.proc = None
        self.backend_host = None
        self.frontend_url = None
        self.output = []
        self.errors = []
        
        ssh_cmd = ("ssh", remote_host) if remote_host is not None else tuple()
        self.cmd = (*ssh_cmd, executable_path, *params)
    
    def start(self):        
        # TODO currently we log everything to stdout, but maybe we shouldn't
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
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
        
        for line in self.output:
            m = FRONTEND_URL.match(line)
            if m:
                self.frontend_url, self.backend_host = m.groups()
                break
        
        return True
    
    def stop(self):
        if self.proc is not None and self.proc.poll() is not None:
            self.proc.terminate()

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
        
    def new_session(self, **kwargs):
        """Create a new session.
        
        :obj:`carta.client.Session.new` wraps this method, which calls either :obj:`carta.browser.Browser.new_session_from_url` or :obj:`carta.browser.Browser.new_session_with_backend`, depending on which keyword arguments are provided.
        """
        
        if "frontend_url" in kwargs:
            func = self.new_session_from_url
            keys = {"frontend_url", "timeout"}
        else:
            func = self.new_session_with_backend
            keys = {"executable_path", "grpc_port", "remote_host", "params", "timeout"}
            
        func(**{k: v for k, v in kwargs.items() if k in keys})
    
    def new_session_from_url(self, frontend_url, timeout=10):
        """Create a new session by connecting to an existing backend.
        
        You can use :obj:`carta.client.Session.new`, which wraps this method.
        
        Parameters
        ----------
        frontend_url : string
            The URL of the frontend.
        timeout : number, optional
            The number of seconds to spend parsing the frontend for connection information. 10 seconds by default.
            
        Returns
        -------
        :obj:`carta.client.Session`
            A session object connected to a new frontend session running in this browser.
        """
                
        self.driver.get(frontend_url)
        
        backend_host = None
        session_id = None
        grpc_port = None
        
        start = time.time()
        last_error = ""
        
        while (backend_host is None or grpc_port is None or session_id is None):
            if time.time() - start > timeout:
                break
            
            try:
                # We can't use .text because Selenium is too clever to return the text of invisible elements.
                backend_url = self.driver.find_element_by_id("info-server-url").get_attribute("textContent")
                m = re.match(r"wss?://(.*?):\d+", backend_url)
                if m:
                    backend_host = m.group(1)
                else:
                    last_error = f"Could not parse backend host from url string '{backend_url}'."
                
                grpc_port = int(self.driver.find_element_by_id("info-grpc-port").get_attribute("textContent"))
                session_id = int(self.driver.find_element_by_id("info-session-id").get_attribute("textContent"))
            except (NoSuchElementException, ValueError) as e:
                last_error = str(e)
                time.sleep(1)
                continue # retry
        
        if None in (backend_host, grpc_port, session_id):
            self.exit("Could not parse CARTA backend host and session ID from frontend.")
        
        return Session(backend_host, grpc_port, session_id, browser=self)
    
    def new_session_with_backend(self, executable_path="carta", grpc_port=50051, remote_host=None, params=tuple(), timeout=10):
        """Create a new session after launching a new backend process.
        
        You can use :obj:`carta.client.Session.new`, which wraps this method.
        
        Parameters
        ----------
        executable_path : string, optional
            A custom path to the CARTA backend executable. The default is `"carta"`.
        grpc_port : string, optional
            The grpc_port to use. 50051 by default.
        remote_host : string, optional
            A remote host where the backend process should be launched, which must be accessible through passwordless ssh. By default the backend process is launched on the local host.
        params : iterable, optional
            Additional parameters to be passed to the backend process. By default the gRPC port is set and the automatic browser is disabled. The parameters are appended to the end of the command, so a positional parameter for a data directory can be included.
        timeout : number, optional
            The number of seconds to spend parsing the frontend for connection information. 10 seconds by default.
            
        Returns
        -------
        :obj:`carta.client.Session`
            A session object connected to a new frontend session running in this browser.
        """
        
        backend = Backend(("--no_browser", "--grpc_port", grpc_port, *params), remote_host)
        if not backend.start():
            self.exit(f"CARTA backend exited unexpectedly:\n{''.join(backend.errors)}")
        backend_host, frontend_url = backend.backend_host, backend.frontend_url
        
        if None in (backend_host, frontend_url):
            self.exit("Could not parse CARTA frontend URL from backend output.")
        
        self.driver.get(frontend_url)
        
        session_id = None
        
        start = time.time()
        last_error = ""
        
        while (session_id is None):
            if time.time() - start > timeout:
                break
            
            try:
                # We can't use .text because Selenium is too clever to return the text of invisible elements.
                session_id = int(self.driver.find_element_by_id("info-session-id").get_attribute("textContent"))
            except (NoSuchElementException, ValueError) as e:
                last_error = str(e)
                time.sleep(1)
                continue # retry
        
        if session_id is None:
            self.exit("Could not parse CARTA session ID from frontend.")
        
        return Session(backend_host, grpc_port, session_id, browser=self, backend=backend)
        
    def exit(self, msg):
        self.close()
        raise CartaScriptingException(msg)
    
    def close(self):
        """Shut down the browser driver."""
        self.driver.quit()


class ChromeHeadless(Browser):
    """Chrome or Chromium running headless, using the SwiftShader renderer for WebGL."""
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--use-gl=swiftshader")
        chrome_options.add_argument("--headless")
        super().__init__(webdriver.Chrome, options=chrome_options)


class Chrome(Browser):
    """Chrome or Chromium, no special options."""
    def __init__(self):
        super().__init__(webdriver.Chrome)


class Firefox(Browser):
    """Firefox, no special options."""
    def __init__(self):
        super().__init__(webdriver.Firefox)
