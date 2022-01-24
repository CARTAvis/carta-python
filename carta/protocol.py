"""This module provides classes and functions used to send HTTP requests to a backend or a controller."""

import getpass

import requests
import urllib
import json

from .token import BackendToken, ControllerToken
from .util import logger, CartaActionFailed, CartaBadResponse, CartaBadToken, CartaBadUrl, CartaEncoder, split_action_path

class AuthType:
    BACKEND, CONTROLLER, NONE = 0, 1, 2


class Protocol:
    ACTION_PATH = "/api/scripting/action"
    REFRESH_TOKEN_PATH = "/api/auth/refresh"
    SCRIPTING_TOKEN_PATH = "/api/auth/scripting"
    
    def __init__(self, frontend_url, token=None, debug_no_auth=False):
        if debug_no_auth:
            self.auth = AuthType.NONE
        else:
            if isinstance(token, ControllerToken):
                if token.scripting:
                    raise CartaBadToken("A long-lived controller refresh token was expected, but a short-lived controller scripting token was provided.")
                
                if not token.valid():
                    raise CartaBadToken("Long-lived controller token has expired. Please use `Protocol.request_refresh_token` to log in and save a new token.")
                
                self.auth = AuthType.CONTROLLER
                self.refresh_token = token
                self.request_scripting_token()
            elif isinstance(token, BackendToken):
                self.auth = AuthType.BACKEND
                self.backend_token = token
            elif token is None:
                try:
                    frontend_url, token = self.split_token_from_url(frontend_url)
                except CartaBadUrl:
                    raise CartaBadToken("No token was provided, and no token could be parsed from the frontend URL.")
                self.auth = AuthType.BACKEND
                self.backend_token = token
            else:
                raise CartaBadToken("Unrecognised token.")
        
        self.frontend_url = frontend_url
    
    @classmethod
    def request_refresh_token(cls, frontend_url, username, path=None):
        # TODO test and add error handling
        password = getpass.getpass(f"Please enter the CARTA password for user {username}: ")
        payload = {"username": username, "password": password}
        
        response = requests.post(url=frontend_url + cls.REFRESH_TOKEN_PATH, data=payload)
        
        token = ControllerToken(response["token"]) # TODO what is this actually supposed to be???
        
        if path:
            token.save(path)
            
        return token

    @classmethod
    def split_token_from_url(cls, url):
        parsed_url = urllib.parse.urlparse(url)
        parsed_query = urllib.parse.parse_qs(parsed_url.query)
        
        if "token" not in parsed_query:
            raise CartaBadUrl(f"Could not parse URL and token from URL string '{url}'")
        return parsed_url._replace(query='').geturl(), BackendToken(parsed_query["token"][0])
    
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

    def request_scripting_token(self):
        # TODO test and add error handling
        payload = {"token": self.refresh_token.string} # TODO what is this actually supposed to be???
        response = requests.post(url=self.frontend_url + self.SCRIPTING_TOKEN_PATH, data=payload)
        self.scripting_token = ControllerToken(response["token"]) # TODO what is this actually supposed to be???

    def request_scripting_action(self, session_id, path, *args, **kwargs):
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
        
        # TODO does this work? do we need to convert to bytes explicitly?
        request_data = json.dumps(request_kwargs, cls=CartaEncoder)
        
        carta_action_description = f"CARTA scripting action {path}.{action} called with parameters {args}"
        
        
        headers = {}
        if self.controller_auth:
            if not self.scripting_token.valid():
                self.request_scripting_token()
            headers["Authorization"] = f"Bearer: {self.scripting_token.string}"
        elif self.backend_auth:
            headers["Authorization"] = f"Bearer: {self.backend_token.string}"
        
        try:
            response = requests.post(url=self.frontend_url + self.ACTION_PATH, data=request_data, headers=headers)
        except requests.exceptions.RequestException as e:
            raise CartaActionFailed(f"{carta_action_description} failed: {e.details()}") from e
        
        try:
            response_data = response.json()
        except json.decoder.JSONDecodeError as e:
            raise CartaBadResponse(f"{carta_action_description} received a response which could not be decoded.\nError: {e}") from e
        
        logger.debug(f"Got success status: {response_data.success}; message: {response_data.message}; response: {response_data.response}")
        
        if not response_data.success:
            raise CartaActionFailed(f"{carta_action_description} failed: {response_data.message}")
        
        if response_data.response == '':
            if response_expected:
                raise CartaBadResponse(f"{carta_action_description} expected a response, but did not receive one.")
            return None

        return response_data
