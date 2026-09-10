"""Failures raised while constructing an opaque identifier.

These are *construction* failures, not transport failures. Mapping them onto the
frozen error catalog (``contracts/domain/v1/error-codes.json``) belongs to the API
edge, which is not this session's tree: ``src/auditmanager/shared/errors/**`` is
unallocated at Gate A. Each exception therefore carries the catalog code it must be
mapped to, so the edge maps rather than guesses.
"""

from __future__ import annotations


class IdentityError(ValueError):
    """Base class for identifier construction failures."""

    #: The frozen catalog code an edge must report for this failure class.
    catalog_error_code = "validation_failed"


class IdentifierFormatError(IdentityError):
    """A string does not match the contract identifier pattern for its type.

    Contract rule enforced here: "An identifier failing the contract pattern is
    rejected at construction, not at insert."
    """


class IdentifierPrefixError(IdentifierFormatError):
    """A string is a well-formed identifier, but of a different entity type."""
