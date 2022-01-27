"""This module provides classes and functions used to send HTTP requests to a backend or a controller."""

import getpass

import requests
import simplejson
import urllib
import json

from .token import BackendToken, ControllerToken
from .util import logger, CartaBadRequest, CartaRequestFailed, CartaActionFailed, CartaBadResponse, CartaBadToken, CartaBadUrl, CartaEncoder, split_action_path

class AuthType:
    BACKEND, CONTROLLER, NONE = 0, 1, 2


class Protocol:
    ACTION_PATH = "/api/scripting/action"
    REFRESH_TOKEN_PATH = "/api/auth/refresh"
    SCRIPTING_TOKEN_PATH = "/api/auth/scripting"
    
    def __init__(self, frontend_url, token=None, debug_no_auth=False):
        self.frontend_url = frontend_url
        self.base_url, token_from_url = self.split_token_from_url(frontend_url)
        
        if debug_no_auth:
            self.auth = AuthType.NONE
        else:
            if isinstance(token, ControllerToken):
                if token.scripting:
                    raise CartaBadToken("A long-lived controller refresh token was expected, but a short-lived controller scripting token was provided.")
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
        # TODO test and add error handling
        password = getpass.getpass(f"Please enter the CARTA password for user {username}: ")
        payload = {"username": username, "password": password}
        
        response = requests.post(url=frontend_url.rstrip("/") + cls.REFRESH_TOKEN_PATH, data=payload)
        
        token = ControllerToken(response["token"]) # TODO what is this actually supposed to be???
        
        if path:
            token.save(path)
            
        return token

    @classmethod
    def split_token_from_url(cls, url):
        parsed_url = urllib.parse.urlparse(url)
        parsed_query = urllib.parse.parse_qs(parsed_url.query)
        
        base_url = parsed_url._replace(query='').geturl().rstrip("/")
        
        if "token" not in parsed_query:
            token = None
        else:
            token = BackendToken(parsed_query["token"][0])
            
        return base_url, token
    
    @property
    def domain(self):
        if not hasattr(self, "_domain"):
            parsed_url = urllib.parse.urlparse(self.frontend_url)
            self._domain = parsed_url.netloc
            if not self._domain:
                raise CartaBadUrl(f"Could not parse domain from URL string '{self.frontend_url}'")
        return self._domain
    
    @property
    def controller_auth(self):
        return self.auth == AuthType.CONTROLLER
    
    @property
    def backend_auth(self):
        return self.auth == AuthType.BACKEND
    
    @property
    def no_auth(self):
        return self.auth == AuthType.NONE
    
    def cookie(self):
        return self.refresh_token.as_cookie(self.domain)
    
    def check_refresh_token(self):
        if not self.refresh_token.valid():
            raise CartaBadToken("Long-lived controller token has expired. Please use `Protocol.request_refresh_token` to log in and save a new token.")

    def request_scripting_token(self):
        # TODO test and add error handling
        self.check_refresh_token()
        cookie = self.refresh_token.as_cookie()
        response = requests.post(url=self.base_url + self.SCRIPTING_TOKEN_PATH, cookies={cookie["name"]: cookie["value"]})
        self.scripting_token = ControllerToken(response["token"]) # TODO what is this actually supposed to be???

    def request_scripting_action(self, session_id, path, *args, **kwargs):
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
