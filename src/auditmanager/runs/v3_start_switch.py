"""The deployment's allowance to start AR v3 (`AR-V3-OPT-IN`, design 4.2; owner answers Q1 and Q2 of 2026-11-07).

AR v3 is an **opt-in** analysis. The imported (standard) analysis stays the default; a deployment may *allow* a user to
choose v3 for one start, and nothing makes v3 the default.

Two layers, both off by default:

* **capability** -- a reviewed pack is installed (``AR_V3_BETA_PACK_MANIFEST``, `AR-V3-BETA-PACK-INSTALL-01`). Needed to
  execute, read and review a group; unchanged by this module;
* **permission** -- ``AR_V3_BETA_START_ALLOWED=1``. Needed, together with the pack, to *start* a group or to ask what one
  would cost. It is read by the ``api`` service only (the worker executes what was accepted whether or not it is set), so
  switching it off stops new starts and lets runs already accepted finish.

Value rules (strict, like ``AUDITMANAGER_WORKER_SLOTS``): absent, blank or ``0`` is off, ``1`` is on, anything else
refuses the start of the process -- a value that silently read as «on» would be a permission nobody gave.

With the allowance off and a pack installed, a start or an estimate is ``409 conflict`` with ``conflict_reason``
``ar_v3_start_not_enabled`` and nothing is written. With no pack installed the answer is the one it always was
(``dependency_unavailable``, ``ar_v3_trusted_pack``): this module does not change what a deployment without a pack sees.
A retry of an **accepted** key replays the group it created whether or not the allowance is still on, exactly as it
already does after the pack is withdrawn.
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

#: The environment variable of the allowance. Absent, blank or ``0``: off. ``1``: on. Anything else: the start is refused.
START_ALLOWED_ENV: Final[str] = "AR_V3_BETA_START_ALLOWED"

#: ``conflict_reason`` of a start or an estimate while the pack is installed and the allowance is off.
CONFLICT_START_NOT_ENABLED: Final[str] = "ar_v3_start_not_enabled"
#: ``conflict_reason`` of a repeat of a run that is a member of an AR v3 group (`Q4`): a v3 run is repeated by a new
#: group start from the form, never by the standard repeat, which would silently turn it into the other analysis.
CONFLICT_MEMBER_NOT_REPEATABLE: Final[str] = "ar_v3_member_not_repeatable"


def parse_start_allowed(raw: str | None) -> bool:
    """The allowance an environment value states; ``ValueError`` (naming the variable, not the value's meaning) otherwise."""
    if raw is None:
        return False
    value = raw.strip()
    if value in ("", "0"):
        return False
    if value == "1":
        return True
    raise ValueError(
        f"{START_ALLOWED_ENV} is {value!r}; it is 1 (starts allowed), 0 or blank (not allowed), nothing else"
    )


def require_start_allowed(*, pack_installed: bool, start_allowed: bool) -> None:
    """Refuse, before anything is written, a start or an estimate the deployment has not allowed.

    ``pack_installed`` false is not this module's refusal: the caller's own «no pack» answer stands, so a deployment
    without a pack reads exactly what it read before the allowance existed.
    """
    if pack_installed and not start_allowed:
        raise DomainError(
            ErrorCode.CONFLICT, aggregate_type="ArV3RunGroup", conflict_reason=CONFLICT_START_NOT_ENABLED,
        )


def refuse_member_repeat() -> DomainError:
    """The refusal of a standard repeat of an AR v3 member (``409 conflict``, ``ar_v3_member_not_repeatable``)."""
    return DomainError(
        ErrorCode.CONFLICT, aggregate_type="AuditRun", conflict_reason=CONFLICT_MEMBER_NOT_REPEATABLE,
    )


__all__ = [
    "CONFLICT_MEMBER_NOT_REPEATABLE",
    "CONFLICT_START_NOT_ENABLED",
    "START_ALLOWED_ENV",
    "parse_start_allowed",
    "refuse_member_repeat",
    "require_start_allowed",
]
