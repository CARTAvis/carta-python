carta-python
------------

This is a prototype of a scripting interface which uses a generic HTTP interface in the CARTA backend as a proxy to call actions on the CARTA frontend.

This package is not yet published on PyPi, but can be installed from the local repository directory with `pip`. Ensure that you're using a Python 3 installation and its corresponding `pip`, either using a `virtualenv` or the appropriate system executable, which may be called `pip3`. Required dependencies (the `requests` library) should be installed automatically:

    pip install .

To create a new frontend session which is controlled by the wrapper instead of connecting to an existing frontend session, you also need to install the `selenium` Python library. You also need to make sure that your desired browser is installed, together with a corresponding web driver.

Some example usage of the client as a module is shown in the [documentation](https://carta-python.readthedocs.io).

The client is under rapid development and this API should be considered experimental and subject to change depending on feedback. The current overall design principle considers session and image objects to be lightweight conduits to the frontend. They store as little state as possible and are not guaranteed to be unique or valid connections -- it is the caller's responsibility to manage the objects and store retrieved data as required.

Unit tests
----------

Running the unit tests requires the installation of additional dependencies:
```
pip install pytest
pip install pytest-mock
pip install pytest-cov
```

To run all the unit tests (from the root directory of the repository):
```
pytest tests # concise
pytest -v tests # more verbose
```

To view the code coverage:
```
pytest --cov=carta tests/
```

See the [`pytest` documentation](https://docs.pytest.org/) for more usage options.
