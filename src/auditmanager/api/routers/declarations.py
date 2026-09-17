"""The parts of the frozen document every operation repeats.

Declared once, because twelve copies of a response table is twelve places for one of them
to be missing a status -- which is the shape of the defect ``openapi-drift.contract.test.ts``
and `W13-CONF`'s gate both exist to catch. Each helper here produces exactly what the
contract declares, and the gate compares the result on every run.
"""

from __future__ import annotations

from typing import Annotated, Any, Final, Mapping

from fastapi import Header, Query
from pydantic import WithJsonSchema

from auditmanager.api.routers.correlation import CORRELATION_HEADER
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property

__all__ = [
    "CORRELATION_RESPONSE_HEADER",
    "CategoryFilterParam",
    "CorrelationIdParam",
    "CursorParam",
    "LimitParam",
    "VerdictFilterParam",
    "declare_correlation_id",
    "envelope_responses",
    "success",
]

#: ``#/components/headers/CorrelationId``, resolved. Every response of every operation
#: carries it -- ``P02_SEAMS.md`` section 7 -- and it is **required**, so a client may rely
#: on it being there rather than testing for it.
CORRELATION_RESPONSE_HEADER: Final[Mapping[str, Any]] = {
    CORRELATION_HEADER: {
        "required": True,
        "schema": {"$ref": "#/components/schemas/CorrelationId"},
        "description": "The correlation id for this request, assigned when the caller "
        "supplied none.",
    }
}

#: The catalog summary each declared status carries in the document. Prose, dropped by the
#: conformance gate's `N4`; written out because a served document with twelve responses
#: described as "Additional Response" is a document nobody reads twice.
_DESCRIPTIONS: Final[Mapping[int, str]] = {
    401: "No credential was presented, or the deployment does not accept it.",
    403: "The authenticated subject is not permitted this operation on this resource.",
    404: "The addressed aggregate does not exist or is not visible to this caller.",
    409: "The idempotency key was already used with a different payload fingerprint.",
    422: "The request was refused by a declared rule. `details` names which.",
    500: "A server-side fault. Nothing was created.",
    503: "A required dependency is unavailable.",
}


def envelope_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """The contract's error responses for one operation, as FastAPI declares them.

    **Every operation that can refuse must declare its own 422 here.** `W13-CONF` measured
    that there is no switch that removes FastAPI's built-in one: declaring the contract's
    own ``422`` *replaces* it, and ``HTTPValidationError`` and ``ValidationError`` then
    never enter ``components.schemas``. An operation that omits it gets FastAPI's, and the
    gate reports it in three places
    (``test_the_gate_catches_fastapis_own_validation_error``). The 43 schema names are
    pinned, so two extra ones are a failure.
    """
    return {
        status: {
            "model": models.ErrorEnvelope,
            "headers": dict(CORRELATION_RESPONSE_HEADER),
            "description": _DESCRIPTIONS[status],
        }
        for status in statuses
    }


def success(status: int, description: str, **extra: Any) -> dict[int | str, dict[str, Any]]:
    """The success response's headers, merged onto the one FastAPI generates.

    No ``model``: the schema comes from the operation's ``response_model``, so there is one
    declaration of the body shape and not two.
    """
    entry: dict[str, Any] = {
        "headers": dict(CORRELATION_RESPONSE_HEADER),
        "description": description,
    }
    for name, value in extra.items():
        if name == "headers":
            entry["headers"] = {**entry["headers"], **value}
        else:
            entry[name] = value
    return {status: entry}


#: ``#/components/parameters/CorrelationId``: optional, ``in: header``, ``$ref``.
#:
#: **Declared, and deliberately not enforced.** The annotation is a plain ``str`` with the
#: contract's schema attached, not ``models.CorrelationId``, because a constrained parameter
#: is a *refusable* one -- FastAPI would answer 422 for a malformed value. Two things say
#: that would be wrong. The contract: four of the twelve operations declare no ``422`` at
#: all, and every one of them carries this parameter. And the rule
#: :mod:`auditmanager.api.routers.correlation` has held since `B6`: an unusable correlation
#: id is **replaced, not refused**, because it addresses a diagnostic record and authorises
#: nothing, and failing a whole request over its shape would trade a working answer for a
#: cosmetic complaint. ``WithJsonSchema`` puts the contract's ``$ref`` in the document
#: without putting a refusal in the edge.
CorrelationIdParam = Annotated[
    str,
    WithJsonSchema({"$ref": "#/components/schemas/CorrelationId"}),
    Header(alias=CORRELATION_HEADER, json_schema_extra=optional_property),
]

#: ``#/components/parameters/Cursor``.
CursorParam = Annotated[models.Cursor, Query(json_schema_extra=optional_property)]

#: ``#/components/parameters/Limit``: 1..200, **default 50**. The default is the one place
#: in this contract where a parameter declares one, and the gate compares it.
LimitParam = Annotated[int, Query(ge=1, le=200)]

#: ``#/components/parameters/CategoryFilter`` and ``VerdictFilter``.
CategoryFilterParam = Annotated[
    models.FindingCategory, Query(json_schema_extra=optional_property)
]
VerdictFilterParam = Annotated[models.Verdict, Query(json_schema_extra=optional_property)]


def declare_correlation_id(correlation_id: CorrelationIdParam = None) -> None:  # type: ignore[assignment]
    """Declare the ``X-Correlation-Id`` request parameter on every operation.

    A router-level dependency and not twelve signatures, because the parameter is the same
    on all twelve and a thirteenth spelling of it is a thirteenth thing to get wrong. The
    value is *read* by :class:`~auditmanager.api.routers.correlation.CorrelationMiddleware`,
    which has to see it on requests no operation serves as well -- an undeclared path, an
    undeclared method -- so this declares the contract's parameter and does nothing else.
    """
    del correlation_id
