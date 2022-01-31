"""This module provides a backend object which corresponds to a CARTA backend process. It is used by the wrapper to manage a local or remote backend process directly when creating a headless browser session."""

import time
import re
import os
import subprocess
import pathlib
import signal

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
        The backend subprocess object. Set by the :obj:`carta.backend.Backend.start` method.
    frontend_url : string
        The URL of the running frontend, parsed from the output of the backend process. Set by the :obj:`carta.backend.Backend.start` method.
    token : :obj:`carta.token.BackendToken`
        The security token of the running backend, either parsed from the output of the backend process and set by the :obj:`carta.backend.Backend.start` method, or overridden with a parameter.
    debug_no_auth : boolean
        If this is set, the backend will accept HTTP connections with no authentication token. This is provided for debugging purposes only and should not be used under normal circumstances. This value is automatically detected from the provided backend parameters.
    output : list of strings
        All output of the backend process, split into lines, terminated by newline characters.
    errors : list of strings
        Error output of the backend process, split into lines, terminated by newline characters.
        
    Returns
    -------
    :obj:`carta.backend.Backend`
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
