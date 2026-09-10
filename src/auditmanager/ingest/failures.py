"""Turning an adapter failure into the one typed failure the rest of the system speaks.

``auditmanager.storage`` raises its own explicitly typed errors and carries the frozen
catalog code each one maps to. This module performs that mapping once, so no call site
re-derives it and no call site invents a code the catalog does not declare.

Two filters are applied, and both matter:

* **the code** comes from the adapter's own ``code`` attribute, which is a catalog
  string. An adapter that ever carried an unknown code becomes ``internal_error``
  through :func:`~auditmanager.shared.errors.from_internal`, never an invented member;
* **the details** are narrowed to the ``safe_detail_keys`` the *reported code* declares.
  The storage package's own vocabulary is wider than any single code's -- it includes
  ``actual_size`` and ``expected_size``, which ``storage_integrity_error`` does not
  declare -- so passing them straight through would raise ``UnsafeDetailKey`` at
  envelope time. Narrowing here means a storage failure is reportable, always.

Neither filter can leak a location: the storage package's error vocabulary has no
bucket, key, URL or path in it at all, and its summaries are class constants rather
than interpolated strings.
"""

from __future__ import annotations

from typing import Any

from auditmanager.shared.errors import DomainError, from_internal
from auditmanager.storage import StorageError

__all__ = ["domain_error_from_storage"]


def domain_error_from_storage(exc: StorageError, **extra: Any) -> DomainError:
    """The :class:`DomainError` one storage failure maps to.

    ``extra`` lets a caller add what it knows -- typically ``role`` -- and is narrowed
    by exactly the same rule as the adapter's own details.
    """
    code = from_internal(getattr(exc, "code", "") or "")
    allowed = code.safe_detail_keys
    details: dict[str, Any] = {}
    for source in (dict(exc.details), extra):
        for key, value in source.items():
            if key in allowed and isinstance(value, (str, int, float, bool)):
                details[key] = value
    return DomainError(code, **details)
