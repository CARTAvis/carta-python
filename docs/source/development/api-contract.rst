Frontend API contract
=====================

The frontend API contract used by ``carta-python`` is extracted from the
wrapper source by ``scripts/extract_api.py``. Run the extractor check after
changing calls to ``call_action`` or ``get_value``:

.. code-block:: shell

   uv run python scripts/extract_api.py --check

The manifest can be regenerated explicitly with:

.. code-block:: shell

   uv run python scripts/extract_api.py --check --write-manifest

Most API paths should be statically discoverable from the source. Special
cases are marked at the call site with a ``carta-api`` comment. The comment
may be placed on the call itself or on the line immediately before it.

Legacy APIs
-----------

Use ``legacy`` when an API is retained only for compatibility with older
frontend versions. The optional ``until`` value records the last frontend
version which needs the API:

.. code-block:: python

   # carta-api:legacy until=6.1
   self.call_action("oldStore.setValue", value)

An API marked only as ``legacy`` is included in the manifest as a compatibility
entry. If another call site uses the same API without the annotation, the API
is treated as required.

Dynamic APIs
------------

Use ``dynamic`` when the path is intentionally supplied by the user and cannot
be enumerated statically. The path is relative to the wrapper object's base
path. ``*`` is the default wildcard:

.. code-block:: python

   # carta-api:dynamic path=*
   return self.get_value(name)

The shorter form is equivalent:

.. code-block:: python

   # carta-api:dynamic
   return self.get_value(name)

Dynamic annotations should only be used for genuinely open-ended paths. If a
path has a finite set of values, prefer writing those values explicitly so the
extractor can check each API individually. ``plumbing`` methods and frontend
runtime types are not declared with comments: forwarding methods are handled
by the extractor's plumbing rules, while runtime types are declared on their
Python wrapper classes with ``FRONTEND_RUNTIME_TYPE``.
