"""This module provides a collection of helper objects for storing and accessing file metadata."""

import re

from .util import cached
from .constants import Polarization

class ImageInfo:
    """This class stores metadata for an image file.
    
    Parameters
    ----------
    info : dict
        The basic metadata for this image, as received from the frontend.
    info_extended : dict
        The extended metadata for this image, as received from the frontend.
    
    Attributes
    ----------
    info : dict
        The basic metadata for this image, as received from the frontend.
    info_extended : dict
        The extended metadata for this image, as received from the frontend.
    """
    
    def __init__(self, info, info_extended):
        self.info = info
        self.info_extended = info_extended
        
    @property
    @cached
    def header(self):
        """The header of the image.

        Entries with T or F string values are automatically converted to booleans.

        ``HISTORY``, ``COMMENT`` and blank keyword entries are aggregated into single entries with list values and with ``'HISTORY'``, ``'COMMENT'`` and ``''`` as keys, respectively. An entry in the history list which begins with ``'>'`` will be concatenated with the previous entry.

        Adjacent ``COMMENT`` entries are not concatenated automatically.

        Any other header entries with no values are given values of ``None``.

        Returns
        -------
        dict of string to string, integer, float, boolean, ``None`` or list of strings
            The header of the image, with field names as keys.
        """
        raw_header = self.info_extended["headerEntries"]

        header = {}

        history = []
        comment = []
        blank = []

        def header_value(raw_entry):
            try:
                return raw_entry["numericValue"]
            except KeyError:
                try:
                    value = raw_entry["value"]
                    if value == 'T':
                        return True
                    if value == 'F':
                        return False
                    return value
                except KeyError:
                    return None

        for i, raw_entry in enumerate(raw_header):
            name = raw_entry["name"]

            if name.startswith("HISTORY "):
                line = name[8:]
                if line.startswith(">") and history:
                    history[-1] = history[-1] + line[1:]
                else:
                    history.append(line)
                continue

            if name.startswith("COMMENT "):
                comment.append(name[8:])
                continue

            if name.startswith(" " * 8):
                blank.append(name[8:])
                continue

            header[name] = header_value(raw_entry)

        if history:
            header["HISTORY"] = history

        if comment:
            header["COMMENT"] = comment

        if blank:
            header[""] = blank

        return header
    
    def deduce_polarization(self):
        """Deduce the polarization of the image from its metadata."""
        polarization = None
        
        ctype_header = [k for k, v in self.header.items() if k.startswith("CTYPE") and v.upper() == "STOKES"]
        if ctype_header:
            index = ctype_header[0][5:]
            naxis = self.header.get(f"NAXIS{index}", None)                
            crpix = self.header.get(f"CRPIX{index}", None)
            crval = self.header.get(f"CRVAL{index}", None)
            cdelt = self.header.get(f"CDELT{index}", None)
            
            if all(naxis, crpix, crval, cdelt) and naxis == 1:
                polarization_index = crval + (1 - crpix) * cdelt
                try:
                    return Polarization(polarization_index)
                except ValueError:
                    pass
        
        if polarization is None:
            name_parts = re.split([._], self.info["name"])
            matches = []
            for part in name_parts:
                if hasattr(Polarization, part.upper()):
                    matches.append(getattr(Polarization, part.upper()))
            if len(matches) == 1:
                return matches[0]
        
        raise ValueError(f"Could not deduce polarization from image file {self.info["name"]}.")
