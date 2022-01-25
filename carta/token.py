"""This module provides classes and functions for managing backend and controller tokens."""

import math
import base64
import datetime
import json

from .util import CartaBadToken

class Token:
    UNKNOWN, BACKEND, REFRESH, SCRIPTING = list(range(4))
    
    def __init__(self, string):
        self.string = string
        self.token_type = Token.UNKNOWN


class BackendToken(Token):
    def __init__(self, string):
        super().__init__(string)
        self.token_type = Token.BACKEND


class ControllerToken(Token):
    def __init__(self, string):
        super().__init__(string)
    
    def _decode_jwt(self):
        try:
            payload = self.string.split('.')[1]
        
            payload = payload.ljust(4 * math.ceil(len(payload)/4), "=")
            
            decoded_payload = base64.b64decode(payload)
            decoded_dict = json.loads(decoded_payload.decode("utf-8"))
            
            exp = int(decoded_dict["exp"])
            self._expires = datetime.datetime.fromtimestamp(exp)
            self._username = decoded_dict["username"]
            if "refreshToken" in decoded_dict:
                self._token_type = Token.REFRESH
            elif "scripting" in decoded_dict:
                self._token_type = Token.SCRIPTING
            else:
                raise ValueError("This is not a refresh token or a scripting token.")
            
        except Exception as e:
            raise CartaBadToken(f"String {self.string} cannot be converted to a controller token: {e}")
        
    @property
    def expires(self):
        if not hasattr(self, "_expires"):
            self._decode_jwt()
        return self._expires
        
    @property
    def username(self):
        if not hasattr(self, "_username"):
            self._decode_jwt()
        return self._username
        
    @property
    def token_type(self):
        if not hasattr(self, "_token_type"):
            self._decode_jwt()
        return self._token_type
    
    @property
    def refresh(self):
        return self.token_type == Token.REFRESH
    
    @property
    def scripting(self):
        return self.token_type == Token.SCRIPTING
            
    @classmethod
    def from_file(cls, path):
        with open(path) as f:
            string = f.read().strip()
                
        return cls(string)
    
    def valid(self):
        if datetime.datetime.now() > self.expires:
            return False
        return True
        
        
    def save(self, path):
        with open(path, "w") as f:
            f.write(self.string.strip())
            
    def as_cookie(self, domain):
        if not self.refresh:
            raise CartaBadToken("Cannot convert a scripting token to a cookie. Refresh token expected.")
        
        # TODO we probably don't need most of these fields at all
        return {
            "name": "Refresh-Token",
            "value": self.string,
            #"path": "/api/auth/refresh",
            "domain": domain,
            #"expires": self.expires.timestamp(),
            #"secure": True,
            #"httpOnly": True,
            #"sameSite": "Strict",
        }
