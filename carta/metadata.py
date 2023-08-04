"""This module provides a collection of helper objects for storing and accessing file metadata."""

import re

from .constants import Polarization


def parse_header(raw_header):
    """Parse raw image header entries from the frontend into a more user-friendly format.

    Entries with T or F string values are automatically converted to booleans.

    ``HISTORY``, ``COMMENT`` and blank keyword entries are aggregated into single entries with list values and with ``'HISTORY'``, ``'COMMENT'`` and ``''`` as keys, respectively. An entry in the history list which begins with ``'>'`` will be concatenated with the previous entry.

    Adjacent ``COMMENT`` entries are not concatenated automatically.

    Any other header entries with no values are given values of ``None``.

    Parameters
    ----------
    raw_header : dict
        The raw header entries received from the frontend.

    Returns
    -------
    dict of string to string, integer, float, boolean, ``None`` or list of strings
        The header of the image, with field names as keys.
    """
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


def deduce_polarization(file_name, header):
    """Deduce the polarization of an image from its metadata.

    Parameters
    ----------
    file_name : string
        The name of the image file.
    header : dict
        The parsed header of the image file (see :obj:`carta.metadata.parse_header`).

    Returns
    -------
    :obj:`carta.constants.Polarization`
        The deduced polarization.

    Raises
    ------
    ValueError
        If the polarization could not be deduced.
    """
    polarization = None

    ctype_header = [k for k, v in header.items() if k.startswith("CTYPE") and v.upper() == "STOKES"]
    if ctype_header:
        index = ctype_header[0][5:]
        naxis = header.get(f"NAXIS{index}", None)
        crpix = header.get(f"CRPIX{index}", None)
        crval = header.get(f"CRVAL{index}", None)
        cdelt = header.get(f"CDELT{index}", None)

        if all(naxis, crpix, crval, cdelt) and naxis == 1:
            polarization_index = crval + (1 - crpix) * cdelt
            try:
                return Polarization(polarization_index)
            except ValueError:
                pass

    if polarization is None:
        name_parts = re.split("[._]", file_name)
        matches = []
        for part in name_parts:
            if hasattr(Polarization, part.upper()):
                matches.append(getattr(Polarization, part.upper()))
        if len(matches) == 1:
            return matches[0]

    raise ValueError(f"Could not deduce polarization from image file {file_name}.")
