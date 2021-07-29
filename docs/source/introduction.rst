Introduction
============

This is a Python-based scripting interface for `CARTA, the Cube Analysis and Rendering Tool for Astronomy <https://cartavis.org/>`_, an astronomical image visualization and analysis tool. More information about CARTA can be found on the main `CARTA documentation <https://carta.readthedocs.io>`_ page.

This scripting wrapper allows the user to execute functions in the CARTA frontend component programmatically, simulating various actions which can be taken through the graphical user interface in the browser. The CARTA backend acts as a proxy, receiving commands from the wrapper through a gRPC service, forwarding them to the frontend through a websocket connection, and relaying responses back to the wrapper.

The wrapper provides the user with a high-level API which streamlines certain common tasks and validates function input. The user also has the option of using the low-level interface more directly, to implement functionality which is not yet available in the high-level API. We recommend that users make use of the high-level API whenever possible -- custom low-level commands may break with future changes to the internals of the frontend component.

This document assumes that the user is using CARTA in "User Deployment Mode" (UDM), running the backend component directly on a local host or one accessible through SSH. "Site Deployment Mode" (SDM) support for scripting is under development.

This package is experimental, and only supports POSIX operating systems.
