"""This module provides classes and functions for managing backend and controller tokens."""

import math
import base64
import datetime
import json

from .util import CartaBadToken


class Token:
    """The parent token class. This should not be instantiated directly."""

    def __init__(self, string):
        self.string = string


class BackendToken(Token):
    """An object representing a security token used by the backend. These tokens are strings with no additional meaning, and may be generated automatically or overridden by the user with a fixed value.

    Parameters
    ----------
    string : string
        The token string.
    """

    def __init__(self, string):
        super().__init__(string)


class ControllerToken(Token):
    """An object representing a security token used by the controller. These tokens are JWTs (JSON Web Tokens) which encode additional information such as an expiration date. The controller uses multiple types of tokens. This interface makes use of long-lived refresh tokens (used to log into the controller and to obtain scripting tokens) and short-lived scripting tokens (used to make scripting requests).

    Parameters
    ----------
    string : string
        The token string.
    """

    def __init__(self, string):
        super().__init__(string)

    def _decode_jwt(self):
        try:
            payload = self.string.split('.')[1]

            payload = payload.ljust(4 * math.ceil(len(payload) / 4), "=")

            decoded_payload = base64.b64decode(payload)
            decoded_dict = json.loads(decoded_payload.decode("utf-8"))

            exp = int(decoded_dict["exp"])
            self._expires = datetime.datetime.fromtimestamp(exp)
            self._username = decoded_dict["username"]
            if "refresh" in decoded_dict:
                self._refresh = True
            if "scripting" in decoded_dict:
                self._scripting = True

        except Exception as e:
            raise CartaBadToken(f"String {self.string} cannot be converted to a controller token: {e}")

    @property
    def expires(self):
        """The expiration date of this token.

        Returns
        -------
        :obj:`datetime.datetime` object
            The expiration date.

        Raises
        ------
        CartaBadToken
            If the token string is not a vaild JWT.
        """
        if not hasattr(self, "_expires"):
            self._decode_jwt()
        return self._expires

    @property
    def username(self):
        """The username encoded in this token.

        Returns
        -------
        string
            The username.

        Raises
        ------
        CartaBadToken
            If the token string is not a vaild JWT.
        """
        if not hasattr(self, "_username"):
            self._decode_jwt()
        return self._username

    @property
    def refresh(self):
        """Is this a refresh token?

        Returns
        -------
        boolean
            Whether this is a refresh token.

        Raises
        ------
        CartaBadToken
            If the token string is not a vaild JWT.
        """
        if not hasattr(self, "_refresh"):
            self._decode_jwt()
        return self._refresh

    @property
    def scripting(self):
        """Is this a scripting token?

        Returns
        -------
        boolean
            Whether this is a scripting token.

        Raises
        ------
        CartaBadToken
            If the token string is not a vaild JWT.
        """
        if not hasattr(self, "_scripting"):
            self._decode_jwt()
        return self._scripting

    @classmethod
    def from_file(cls, path):
        """Load a controller token from a file.

        Parameters
        ----------
        path : string
            The path to the file.

        Returns
        -------
        :obj:`carta.token.ControllerToken`
            The controller token.
        """
        with open(path) as f:
            string = f.read().strip()

        return cls(string)

    def valid(self):
        """Is this token valid?

        Returns
        -------
        boolean
            Whether this token is valid.

        Raises
        ------
        CartaBadToken
            If the token string is not a vaild JWT.
        """
        if datetime.datetime.now() > self.expires:
            return False
        return True

    def save(self, path):
        """Save this token to a file.

        Parameters
        ----------
        path : string
            The path to the file where the token should be saved.
        """
        with open(path, "w") as f:
            f.write(self.string.strip())

    def as_cookie(self, domain):
        """Create a cookie from this refresh token.

        Parameters
        ----------
        domain : string
            The domain to use in the cookie.

        Returns
        -------
        dict
            The cookie as a dictionary of string keys and values.

        Raises
        ------
        CartaBadToken
            If the token string is not a valid JWT or if this is not a refresh token.
        """

        return {
            "name": "Refresh-Token",
            "value": self.string,
            "domain": domain,
        }
