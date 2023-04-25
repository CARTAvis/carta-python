"""This module provides a collection of helper objects for grouping related values together."""

import posixpath

from .validation import validate, String, Constant
from .constants import Polarization


class StokesImage:
    '''An object which groups information about an image file to be used as a component in a Stokes hypercube.

    Parameters
    ----------
    stokes : :obj:`carta.constants.Polarization`
        The Stokes type to specify. Must be a member of :obj:`carta.constants.Polarization`
    path : str
        The path to the image file.
    hdu : str
        The HDU to open.

    Attributes
    ----------
    stokes : :obj:`carta.constants.Polarization`
        The Stokes type to specify. Must be a member of :obj:`carta.constants.Polarization`
    path : str
        The path to the image file.
    hdu : str
        The HDU to open.
    '''

    @validate(Constant(Polarization), String(), String())
    def __init__(self, stokes, path, hdu=""):
        self.stokes = stokes
        self.directory, self.file_name = posixpath.split(path)
        self.hdu = hdu

    def json(self):
        """The JSON serialization of this object."""
        return {"directory": self.directory, "file": self.file_name, "hdu": self.hdu, "polarizationType": self.stokes.proto_index}
