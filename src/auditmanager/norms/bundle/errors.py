"""The bundle's refusals and its process exit statuses.

Every refusal names one stable reason word, so an operator reading the import log on the
stand, and a test, can tell which rule held without parsing prose. A refusal is raised
before the step it guards writes anything.
"""

from __future__ import annotations

from typing import Final

#: Exit statuses of ``python -m auditmanager.norms.bundle``. The inbound key's forced
#: command passes them on unchanged (`W54-TRANSPORT-01` §3 item 6).
EXIT_OK: Final[int] = 0
#: ``report`` (or an import's closing report) found a difference from the manifest or the
#: copy record.
EXIT_MISMATCH: Final[int] = 1
#: A rule refused the command before the step it guards wrote anything.
EXIT_REFUSED: Final[int] = 2
#: The import is not finished: an admission is still ``pending`` (due later) or
#: ``poisoned``. The bundle is kept; run ``import`` again (after ``requeue`` for poisoned).
EXIT_INCOMPLETE: Final[int] = 75


class BundleRefused(Exception):
    """A bundle command refused, with a stable ``reason`` word and a sentence for people."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason
        self.message = message


__all__ = [
    "EXIT_INCOMPLETE",
    "EXIT_MISMATCH",
    "EXIT_OK",
    "EXIT_REFUSED",
    "BundleRefused",
]
