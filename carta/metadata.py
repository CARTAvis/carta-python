"""This module provides a collection of helper objects for storing and accessing file metadata."""


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
