"""This module provides classes and functions used to send HTTP requests to a backend or a controller."""

import getpass

import requests
import simplejson
import urllib.parse
import json

from .token import BackendToken, ControllerToken
from .util import logger, CartaBadRequest, CartaRequestFailed, CartaActionFailed, CartaBadResponse, CartaBadToken, CartaBadUrl, CartaEncoder, split_action_path

class AuthType:
    BACKEND, CONTROLLER, NONE = 0, 1, 2


class Protocol:
    """This object manages connections to a backend or controller instance, including any required authentication.
    
    It should not be instantiated directly; it is created on demand when a :obj:`carta.session.Session` object is created using one of the convenience class methods provided.
    
    Parameters
    ----------
    frontend_url : string
        The URL of the frontend.
    token : :obj:`carta.token.Token`, optional
        The security token used by the CARTA instance. May be omitted if the URL contains a token.
    debug_no_auth : boolean
        Disable authentication. This should be set if the backend has been started with the ``--debug_no_auth`` option. This is provided for debugging purposes only and should not be used under normal circumstances.
        
    Raises
    ------
    CartaBadToken
        If an invalid token was provided.
    CartaBadUrl
        If an invalid URL was provided.
    """
    ACTION_PATH = "/api/scripting/action"
    REFRESH_TOKEN_PATH = "/api/auth/login"
    SCRIPTING_TOKEN_PATH = "/api/auth/refresh"
    
    def __init__(self, frontend_url, token=None, debug_no_auth=False):
        self.frontend_url = frontend_url
        self.base_url, token_from_url = self.split_token_from_url(frontend_url)
        
        if debug_no_auth:
            self.auth = AuthType.NONE
        else:
            if isinstance(token, ControllerToken):
                if not token.refresh:
                    raise CartaBadToken("A long-lived controller refresh token was expected, but a different controller token was provided.")
                self.auth = AuthType.CONTROLLER
                self.refresh_token = token
                self.check_refresh_token()
                self.request_scripting_token()
            elif isinstance(token, BackendToken):
                self.auth = AuthType.BACKEND
                self.backend_token = token
            elif token is None:
                if token_from_url is None:
                    raise CartaBadToken("No token was provided, and no token could be parsed from the frontend URL.")
                self.auth = AuthType.BACKEND
                self.backend_token = token_from_url
            else:
                raise CartaBadToken("Unrecognised token.")
    
    @classmethod
    def request_refresh_token(cls, frontend_url, username, path=None):
        """Request a refresh token from a controller and optionally save it to a file.
        
        This function must be run interactively. It securely prompts the user to enter a password.
        
        TODO: document exceptions
        
        Parameters
        ----------
        frontend_url : string
            The URL of the frontend.
        username : string
            The username to use to authenticate with the controller.
        path : string, optional
            A path to a file where the refresh token should be saved.
            
        Returns
        -------
        :obj:`carta.token.ControllerToken` object
            The token object created using the returned refresh token.
            
        Raises
        ------
        CartaBadRequest
            If the request was invalid.
        CartaRequestFailed
            If the request failed.
        CartaBadResponse    
            If the response could not be decoded.
        """
        password = getpass.getpass(f"Please enter the CARTA password for user {username}: ")
        payload = {"username": username, "password": password}
        
        try:
            response = requests.post(url=frontend_url.rstrip("/") + cls.REFRESH_TOKEN_PATH, data=payload)
        except requests.exceptions.RequestException as e:
            raise CartaBadRequest(f"Request for refresh token was invalid: {e}") from e
            
        try:
            response_data = response.json()
        except simplejson.errors.JSONDecodeError as e:
            raise CartaBadResponse(f"Request for refresh token received a response which could not be decoded.\nError: {e}") from e
        
        if response.status_code != 200:
            raise CartaRequestFailed(f"Request for refresh token failed with status code {response.status_code}: {response_data['message']}.")
        
        token_string = None
        
        for c in response.cookies:
            if c.name == "Refresh-Token":
                token_string = c.value
                break
            
        if not token_string:
            raise CartaBadResponse("Request for refresh token did not receive a response with the expected cookie.")

        token = ControllerToken(token_string)
        
        if path:
            token.save(path)
            
        return token

    @classmethod
    def split_token_from_url(cls, url):
        """Extract a backend token from a frontend URL.
        
        Parameters
        ----------
        url : string
            The URL of the frontend.
            
        Returns
        -------
        string
            The URL with the backend token removed.
        :obj:`carta.token.BackendToken` object or None
            The object representing the backend token.

        Raises
        ------
        CartaBadUrl
            If an invalid URL was provided.
        
        """
        parsed_url = urllib.parse.urlparse(url)
        
        if not (parsed_url.scheme and parsed_url.netloc):
            raise CartaBadUrl(f"Could not parse URL {url}.")
        
        parsed_query = urllib.parse.parse_qs(parsed_url.query)
        
        base_url = parsed_url._replace(query='').geturl().rstrip("/")
        
        if "token" not in parsed_query:
            token = None
        else:
            token = BackendToken(parsed_query["token"][0])
            
        return base_url, token
    
    @property
    def domain(self):
        """The domain extracted from the frontend URL."""
        if not hasattr(self, "_domain"):
            parsed_url = urllib.parse.urlparse(self.frontend_url)
            self._domain = parsed_url.netloc
            if not self._domain:
                raise CartaBadUrl(f"Could not parse domain from URL string '{self.frontend_url}'")
        return self._domain
    
    @property
    def controller_auth(self):
        """Is controller authentication enabled?"""
        return self.auth == AuthType.CONTROLLER
    
    @property
    def backend_auth(self):
        """Is backend authentication enabled?"""
        return self.auth == AuthType.BACKEND
    
    @property
    def no_auth(self):
        """Is authentication disabled?"""
        return self.auth == AuthType.NONE
    
    def cookie(self):
        """The refresh token in the form of a cookie."""
        return self.refresh_token.as_cookie(self.domain)
    
    def check_refresh_token(self):
        """Check whether the refresh token has expired.
        
        Raises
        ------
        CartaBadToken
            If the refresh token has expired.
        """
        if not self.refresh_token.valid():
            raise CartaBadToken("Long-lived controller token has expired. Please use `Protocol.request_refresh_token` to log in and save a new token.")

    def request_scripting_token(self):
        """Request a scripting token from the controller and cache it on this object.
        
        Raises
        ------
        CartaBadRequest
            If the request was invalid.
        CartaRequestFailed
            If the request failed.
        CartaBadResponse    
            If the response could not be decoded.
        """
        self.check_refresh_token()
        
        payload = json.dumps({"scripting": True})
        
        headers = {
            'Content-Type': 'application/json',
            'Cookie': f'Refresh-Token={self.refresh_token.string}',
        }
                
        try:
            response = requests.post(url=self.base_url + self.SCRIPTING_TOKEN_PATH, headers=headers, data=payload)
        except requests.exceptions.RequestException as e:
            raise CartaBadRequest(f"Request for scripting token was invalid: {e}") from e
                    
        try:
            response_data = response.json()
        except simplejson.errors.JSONDecodeError as e:
            raise CartaBadResponse(f"Request for scripting token received a response which could not be decoded.\nError: {e}") from e
                
        if response.status_code != 200:
            raise CartaRequestFailed(f"Request for scripting token failed with status code {response.status_code}: {response_data['message']}.")
        
        self.scripting_token = ControllerToken(response_data["access_token"])

    def request_scripting_action(self, session_id, path, *args, **kwargs):
        """Call an action on the frontend through the backend's scripting interface.
        
        Parameters
        ----------
        path : string
            The full dot-separated path to a frontend action.
        *args
            A variable-length list of parameters to pass to the action. :obj:`carta.util.Macro` objects may be used to refer to frontend objects which will be evaluated dynamically. This parameter list will be serialized into a JSON string with :obj:`carta.util.CartaEncoder`.
        **kwargs
            Arbitrary keyword arguments. At present only three are used: *async* (boolean) is passed to indicate that the request should return a response as soon as the action is called, without waiting for the action to complete. *response_expected* (boolean) indicates that the action should return a JSON object. This is set automatically if *return_path* is set. *return_path* specifies a subobject of the action's response which should be returned instead of the whole response. *timeout* (boolean) is the maximum time in seconds to wait for an action request to complete (the default is 10).
        
        Returns
        -------
        None or an object
            If the action returns a JSON object, this method will return that response deserialized into a Python object.
        
        Raises
        ------
        CartaBadRequest
            If the request was invalid.
        CartaRequestFailed
            If the backend could not send the request to the frontend.
        CartaActionFailed
            If the action failed.
        CartaBadResponse    
            If a request which was expected to have a JSON response did not have one, or if a JSON response could not be decoded.
        """
        timeout = kwargs.pop("timeout", 10)
        response_expected = kwargs.pop("response_expected", False)
        path, action = split_action_path(path)
        
        logger.debug(f"Sending action request to backend; path: {path}; action: {action}; args: {args}, kwargs: {kwargs}")
        
        request_kwargs = {
            "session_id": session_id,
            "path": path,
            "action": action,
            "parameters": args,
            "async": kwargs.get("async", False),
        }

        if "return_path" in kwargs:
            request_kwargs["return_path"] = kwargs["return_path"]
            response_expected = True
        
        request_data = json.dumps(request_kwargs, cls=CartaEncoder)
                
        carta_action_description = f"CARTA scripting action {path}.{action} called with parameters {args}"
        
        headers = {}
        if self.controller_auth:
            if not self.scripting_token.valid():
                self.check_refresh_token()
                self.request_scripting_token()
            headers["Authorization"] = f"Bearer {self.scripting_token.string}"
        elif self.backend_auth:
            headers["Authorization"] = f"Bearer {self.backend_token.string}"
        
        try:
            response = requests.post(url=self.base_url + self.ACTION_PATH, data=request_data, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise CartaBadRequest(f"{carta_action_description} failed: {e}") from e
                
        known_errors = {
            400: "The backend could not parse the request.",
            403: "Could not authenticate.",
            404: f"No session with ID {session_id} could be found.",
            500: "An internal error occurred, or the client cancelled the request.",
        }
        
        if response.status_code != 200:
            backend_message = known_errors.get(response.status_code, "Unknown error.")
            raise CartaRequestFailed(f"{carta_action_description} failed with status {response.status_code}. {backend_message}")
                
        try:
            response_data = response.json()
        except simplejson.errors.JSONDecodeError as e:
            raise CartaBadResponse(f"{carta_action_description} received a response which could not be decoded.\nError: {e}") from e
        
        logger.debug(f"Got response: {response_data}")
        
        if not response_data['success']:
            raise CartaActionFailed(f"{carta_action_description} failed: {response_data.get('message', 'No error message received.')}")
        
        if 'response' not in response_data:
            if response_expected:
                raise CartaBadResponse(f"{carta_action_description} expected a response, but did not receive one.")
            return None

        return response_data['response']
