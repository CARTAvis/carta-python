Development
===========

Set up a development environment with ``uv``:

.. code-block:: shell

   uv sync --all-extras

Run the test suite and documentation build before submitting changes:

.. code-block:: shell

   uv run pytest
   uv run sphinx-build -W -b html docs/source docs/build/html

Development topics
------------------

.. toctree::
   :maxdepth: 1

   development/release-cycle
