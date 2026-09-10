"""Typed failures of the database boundary.

Each failure names the frozen catalog code an edge must report for it
(``contracts/domain/v1/error-codes.json``). The mapping itself belongs to the API
edge; ``src/auditmanager/shared/errors/**`` is unallocated at Gate A, so the code
travels on the exception rather than being re-derived by every caller.
"""

from __future__ import annotations


class DatabaseError(Exception):
    """Base class for failures raised by the shared database boundary."""

    catalog_error_code = "internal_error"


class DatabaseConfigurationError(DatabaseError):
    """``DATABASE_URL`` is absent, unparseable or names the wrong driver.

    This is a deployment fault, not a caller fault: it is raised at construction
    time, before any connection is attempted, so a misconfigured process fails
    loudly at start rather than at first query.
    """

    catalog_error_code = "internal_error"


class DatabaseUnavailableError(DatabaseError):
    """The configured database could not be reached or refused the connection."""

    catalog_error_code = "dependency_unavailable"


class MigrationStateError(DatabaseError):
    """The database schema is not at the migration head the code expects.

    Fail-closed: an unmigrated or ahead-of-code database is refused rather than
    served. There is no automatic upgrade on connect.
    """

    catalog_error_code = "internal_error"
