"""Shared schema conventions and the SQLSTATE codes the migration head raises.

Two things belong here and nothing else:

* one :class:`~sqlalchemy.MetaData` carrying a naming convention, so every
  constraint has a deterministic name and a later migration can drop one by name;
* the custom SQLSTATE codes the P02 trigger functions raise, so a caller maps a
  refusal to a frozen catalog code instead of matching on message text.
"""

from __future__ import annotations

from typing import Final

from sqlalchemy import MetaData

#: Deterministic constraint names. Without this, PostgreSQL invents names for
#: unnamed CHECK and UNIQUE constraints and a later migration cannot address them.
NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

#: The single MetaData every P02 table is defined against.
metadata: Final[MetaData] = MetaData(naming_convention=NAMING_CONVENTION)

# ---------------------------------------------------------------------------
# Custom SQLSTATEs raised by the trigger functions in the P02 migration head.
#
# All three map to the frozen catalog code ``state_transition_not_allowed``, whose
# summary names exactly these cases: "the fail-closed answer for every undeclared
# transition, including any attempt to reopen a terminal aggregate, overwrite a
# published version or delete a decision event." They stay distinct at the SQLSTATE
# level so an operator can tell which invariant fired without parsing a message.
# ---------------------------------------------------------------------------

#: A state column was moved along an edge the contract does not declare.
SQLSTATE_UNDECLARED_TRANSITION: Final[str] = "AM001"

#: UPDATE or DELETE was attempted on an append-only ledger table.
SQLSTATE_APPEND_ONLY_VIOLATION: Final[str] = "AM002"

#: UPDATE or DELETE was attempted on an immutable published row.
SQLSTATE_IMMUTABLE_ROW_VIOLATION: Final[str] = "AM003"

#: Every custom SQLSTATE, mapped to the catalog code an edge must report.
SQLSTATE_TO_CATALOG_CODE: Final[dict[str, str]] = {
    SQLSTATE_UNDECLARED_TRANSITION: "state_transition_not_allowed",
    SQLSTATE_APPEND_ONLY_VIOLATION: "state_transition_not_allowed",
    SQLSTATE_IMMUTABLE_ROW_VIOLATION: "state_transition_not_allowed",
}
