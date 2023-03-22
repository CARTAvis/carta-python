"""This module provides a backend object which corresponds to a CARTA backend process. It is used by the wrapper to manage a local or remote backend process directly when creating a headless browser session."""

import time
import re
import os
import subprocess
import pathlib
import signal

from .token import BackendToken
from .util import logger


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
    frontend_url_timeout : integer
        How long to keep checking the output for the frontend URL. Default: 10 seconds.
    session_creation_timeout : integer
        How long to keep checking the output for a default session ID. If this is set to zero (which is the default), no attempt is made to parse a session ID from the output. The calling function should set this to a non-zero value if parsing the session ID is required.

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
    last_session_id : integer
        The ID of the last session connected to this backend process, parsed from the process output. This is likely to be the default session automatically created in the user's browser on startup, if this functionality was not suppressed with the ``--no_browser`` flag. This value is used by the :obj:`carta.session.Session.start_and_interact` method, which connects to this default session. It is not used by the session creation methods which use a wrapper-controlled headless browser, as those parse the session ID from the browser session.
    frontend_url_timeout : integer
        How long to keep checking the output for the frontend URL.
    session_creation_timeout : integer
        How long to keep checking the output for a default session ID. If this is set to zero, no attempt is made to parse a session ID from the output.

    Returns
    -------
    :obj:`carta.backend.Backend`
        A backend object with a process which has not been started.

    """
    FRONTEND_URL = re.compile(r"CARTA is accessible at (http://.*?:\d+/\?token=(.*))")
    FRONTEND_URL_NO_AUTH = re.compile(r"CARTA is accessible at (http://(.*?):\d+.*)")
    SESSION_ID = re.compile(r"Session (\d+) \[[\d.]+\] Connected.")

    def __init__(self, params, executable_path="carta", remote_host=None, token=None, frontend_url_timeout=10, session_creation_timeout=0):
        self.proc = None
        self.frontend_url = None
        self.token = token
        self.debug_no_auth = ("--debug_no_auth" in params)
        self.output = []
        self.errors = []
        self.last_session_id = None
        self.frontend_url_timeout = frontend_url_timeout
        self.session_creation_timeout = session_creation_timeout

        ssh_cmd = ("ssh", "-tt", remote_host) if remote_host is not None else tuple()
        self.cmd = tuple(str(p) for p in (*ssh_cmd, executable_path, *params))

    def update_output(self):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.decode()

            self.output.append(line)
            if "[error]" in line or "[critical]" in line:
                self.errors.append(line)

    def start(self):
        """Start the backend process.

        This method creates the subprocess object and parses the backend host and the frontend URL from the process output.
        """
        # TODO currently we log everything to stdout, but maybe we shouldn't
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, cwd=pathlib.Path.home(), preexec_fn=os.setpgrp)
        os.set_blocking(self.proc.stdout.fileno(), False)

        frontend_url_re = self.FRONTEND_URL if not self.debug_no_auth else self.FRONTEND_URL_NO_AUTH
        token_string = None

        start = time.time()

        while self.frontend_url is None:
            if time.time() - start > self.frontend_url_timeout:
                break

            # Check for new output
            self.update_output()

            if self.proc.poll() is not None:
                return False

            for line in self.output:
                m = frontend_url_re.search(line)
                if m:
                    self.frontend_url, token_string = m.groups()
                    break

            time.sleep(1)

        if token_string is not None and self.token is None and not self.debug_no_auth:
            self.token = BackendToken(token_string)

        # Only try to parse the session ID if it has been requested
        if self.session_creation_timeout > 0:
            start = time.time()

            while self.last_session_id is None:
                if time.time() - start > self.session_creation_timeout:
                    break

                # Check for new output
                self.update_output()

                if self.proc.poll() is not None:
                    return False

                for line in self.output:
                    m = self.SESSION_ID.search(line)
                    if m:
                        self.last_session_id = m.group(1)
                        break

                time.sleep(1)

        return True

    def stop(self):
        """Stop the backend process.

        This method terminates the backend process if it exists and is running.
        """
        if self.proc is not None:
            try:
                pgrp = os.getpgid(self.proc.pid)
                os.killpg(pgrp, signal.SIGINT)
                self.proc.wait()
            except ProcessLookupError:
                logger.debug("Could not shut down backend because it was no longer running.")
