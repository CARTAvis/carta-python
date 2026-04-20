carta-python
------------

This is a prototype of a scripting interface which uses a generic HTTP interface in the CARTA backend as a proxy to call actions on the CARTA frontend.

This package is not yet published on PyPi, but can be installed from the local repository directory with `pip`. Requires Python 3.10 or later. Ensure that you're using the corresponding `pip`, either using a `virtualenv` or the appropriate system executable, which may be called `pip3`. Required dependencies should be installed automatically:

    pip install .

To create a new frontend session which is controlled by the wrapper instead of connecting to an existing frontend session, you also need to install the `selenium` Python library:

    pip install selenium

If you prefer installing the optional browser dependencies via package extras, the equivalent command is:

    pip install ".[browser]"

You also need to make sure that your desired browser is installed, together with a corresponding web driver.

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
pytest tests/     # concise
pytest -v tests/  # more verbose
```

To view the code coverage:

```
pytest --cov=carta tests/
```

See the [`pytest` documentation](https://docs.pytest.org/) for more usage options.

Alternative contributor setup with uv
-------------------------------------

If you prefer a synced local development environment, `uv` is also supported:

```
uv sync
```

This creates a local virtual environment, installs the package in editable mode, and syncs the default development groups.

Equivalent development commands:

```
uv run pytest tests/                 # unit tests
uv run pytest -v tests/              # verbose unit tests
uv run pytest --cov=carta tests/     # coverage
uv run ruff check                    # lint
uv run ruff format --check           # formatting check
```

To auto-fix lint and formatting issues in the `uv` environment:

```
uv run ruff check --fix
uv run ruff format
```

Documentation
-------------

If you are using the `uv` environment, build the docs locally with Sphinx:

```
uv run sphinx-build -W -b html docs/source docs/build/html
```

Or use the Makefile shortcut inside the `docs/` directory:

```
cd docs
uv run make html
```

Then open `docs/build/html/index.html` in a browser:

```
open docs/build/html/index.html        # macOS
xdg-open docs/build/html/index.html    # Linux
```

The published docs are hosted on [Read the Docs](https://carta-python.readthedocs.io).

If you need the docs dependency export for Read the Docs after changing dependencies in `pyproject.toml`:

```
uv export --locked --only-group docs --format requirements.txt --no-hashes --output-file docs/requirements.txt
```
