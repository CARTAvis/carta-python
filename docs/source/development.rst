Development
===========

Set up a development environment with ``uv``:

.. code-block:: shell

   uv sync --all-extras

Run the test suite and documentation build before submitting changes:

.. code-block:: shell

   uv run pytest
   uv run sphinx-build -W -b html docs/source docs/build/html

Version compatibility data
--------------------------

CARTA and ``carta-python`` compatibility is defined by
``COMPATIBILITY_DATA`` in ``carta/compatibility.py``. Each entry maps an
inclusive range of CARTA ``MAJOR.MINOR`` series to the latest recommended
``carta-python`` series.

The final entry determines the requirements for the version under development:

* ``carta_min`` defines the minimum CARTA series that provides complete
  functionality.
* ``wrapper`` must match the major and minor components in ``VERSION.txt``.
* ``carta_max=None`` covers the remaining minor releases in the same CARTA
  major version.

Keep all ranges ordered from oldest to newest, non-overlapping, and within a
single CARTA major version.

Starting a new development cycle
--------------------------------

After a release, prepare ``dev`` for the next release before merging feature
work:

#. Choose the next version and add a ``-dev`` suffix in ``VERSION.txt``. For
   example, start 2.1 development with ``2.1.0-dev``.
#. If the major/minor series changes, update ``wrapper`` in the final
   compatibility entry to match. If the CARTA minimum is unchanged, update the
   existing entry rather than adding an overlapping range.
#. For a patch cycle, such as ``2.0.0`` to ``2.0.1-dev``, leave ``wrapper`` as
   ``"2.0"`` because the compatibility table tracks major/minor series.
#. Run the focused version tests.

For example, starting 2.1 development while retaining CARTA 6.1 as the minimum
uses:

.. code-block:: text

   2.1.0-dev

in ``VERSION.txt`` and:

.. code-block:: python

   COMPATIBILITY_DATA = (
       {"carta_min": "6.1", "carta_max": None, "wrapper": "2.1"},
   )

If the next release is already known to require a newer CARTA series, apply the
range update described below in the same cycle-preparation pull request.

Pull requests during a development cycle
----------------------------------------

Ordinary feature and fix pull requests target ``dev``. They should not change
``VERSION.txt`` or the compatibility table unless they alter CARTA version
requirements.

When a pull request introduces a dependency on a newer CARTA series, update the
compatibility table, its tests, and its documentation in that same pull
request. Do not defer the compatibility change to the release pull request.
Increasing the minimum requires a new ``carta-python`` major/minor series; if
the current cycle is a patch cycle, start an appropriate major/minor cycle
first.

Close the previous range and append a range for the new minimum. For example,
if the version under development is 2.1 and a pull request raises the minimum
CARTA series from 6.1 to 6.2, change the table from:

.. code-block:: python

   COMPATIBILITY_DATA = (
       {"carta_min": "6.1", "carta_max": None, "wrapper": "2.1"},
   )

to:

.. code-block:: python

   COMPATIBILITY_DATA = (
       {"carta_min": "6.1", "carta_max": "6.1", "wrapper": "2.0"},
       {"carta_min": "6.2", "carta_max": None, "wrapper": "2.1"},
   )

This preserves the recommendation for older CARTA releases while making 6.2
the minimum for the version under development. If the new minimum starts a new
CARTA major version, append the new range without closing the previous
open-ended range: an open-ended range stops automatically at the end of its
CARTA major version.

Finishing a development cycle
-----------------------------

The release pull request from ``dev`` to ``main`` finalizes ``VERSION.txt`` by
removing the ``-dev`` suffix, for example from ``2.1.0-dev`` to ``2.1.0``. It
must verify that the final compatibility entry already matches the release
major/minor version and minimum CARTA series. It should not be the first place
where a compatibility change is recorded.

Run the full test suite and documentation build before merging the release. If
the compatibility table changed during the cycle, also run its focused tests:

.. code-block:: shell

   uv run pytest
   uv run pytest tests/test_version.py
   uv run sphinx-build -W -b html docs/source docs/build/html
