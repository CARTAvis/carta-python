import posixpath

from .validation import validate, String, Constant
from .constants import Polarization, PROTO_POLARIZATION


class StokesImage:

    @validate(Constant(PROTO_POLARIZATION), String(), String())
    def __init__(self, stokes, path, hdu=""):
        self.stokes = stokes
        self.directory, self.file_name = posixpath.split(path)
        self.hdu = hdu

    def json(self):
        return {"directory": self.directory, "file": self.file_name, "hdu": self.hdu, "polarizationType": self.stokes.proto_index}
