carta-python
------------

This is a prototype of a scripting interface which uses a generic gRPC service in the CARTA backend as a proxy to call actions on the CARTA frontend.

The protocol buffer definitions and associated files are in a submodule which has to be loaded. Either clone the repository with `--recursive`, or load the submodule afterwards:

    git submodule update --init

This package is not yet published on PyPi, but can be installed from the local repository directory with `pip`. Ensure that you're using a Python 3 installation and its corresponding `pip`, either using a `virtualenv` or the appropriate system executable, which may be called `pip3`. Python dependencies (such as `grpcio` and `grpcio-tools`) should be installed automatically:

    pip install .

To create a new frontend session which is controlled by the wrapper instead of connecting to an existing frontend session, you also need to install the `selenium` Python library. You also need to make sure that your desired browser is installed, together with a corresponding web driver.

Some example usage of the client as a module is shown in the [documentation](https://carta-python.readthedocs.io).

The client is under rapid development and this API should be considered experimental and subject to change depending on feedback. The current overall design principle considers session and image objects to be lightweight conduits to the frontend. They store as little state as possible and are not guaranteed to be unique or valid connections -- it is the caller's responsibility to manage the objects and store retrieved data as required.
