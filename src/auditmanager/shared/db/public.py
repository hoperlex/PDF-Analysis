"""The one persistence-library name an edge may use without importing the library.

The API edge classifies a database refusal into the error envelope
(``api/routers/errors.py``), which needs to recognise the driver-error class. That is a fact
about the database boundary, so the name is re-exported from here and the router module
imports it from this package instead of reaching into ``sqlalchemy`` itself
(``AGENTS.md`` section 4: no direct SQL from a router).

It is the same class object, not a subclass or a copy: an ``isinstance`` check or an
``except`` clause against this name matches exactly what one against ``sqlalchemy.exc`` did.
"""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError

__all__ = ["DBAPIError"]
