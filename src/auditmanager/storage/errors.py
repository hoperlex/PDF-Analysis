"""Explicit, typed BlobStore failures.

Every failure this package can produce is one of the classes below. There is no
generic "storage went wrong" escape and there is no silent degradation: an
unavailable store, a rejected credential and a checksum mismatch are three
different, separately catchable types.

Privacy, mechanically enforced
------------------------------
``FF-01`` section 2 item 4 keeps bucket and object key adapter details, and
``P1-STO-01`` requires that they never appear in a public return model *or in
error text*. That is not left to reviewer discipline here:

* the human-readable summary of an error is a class constant, never a caller
  supplied string, so no call site can interpolate a key into it;
* structured detail values are restricted to the ``safe_detail_keys`` the error
  code declares in ``contracts/domain/v1/error-codes.json``. ``bucket`` and
  ``key`` are not in that vocabulary, so passing one raises ``TypeError`` at
  construction rather than leaking at render time.

The ``code`` on each class is the frozen contract error code the API layer will
map to in P02. Nothing here builds an HTTP envelope; the code is carried so the
mapping is a lookup later rather than a reinterpretation.
"""

from __future__ import annotations

from typing import ClassVar, Final, Mapping

# The union of every `safe_detail_keys` entry the domain error-code catalog
# declares for the codes this package raises, plus the two byte-count keys the
# `storage_integrity_error` summary itself talks about ("a declared checksum,
# byte size or media type does not match"). A name that is not in this set can
# never be rendered into an error message.
SAFE_DETAIL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "aggregate_type",
        "actual_sha256",
        "actual_size",
        "blob_id",
        "constraint",
        "dependency",
        "expected_sha256",
        "expected_size",
        "field",
        "media_type",
        "required_capability",
        "role",
    }
)

# The stable dependency class name `dependency_unavailable` is allowed to carry.
# It names a class of dependency, never an endpoint, bucket or host.
BLOB_STORAGE_DEPENDENCY: Final[str] = "blob_storage"


class StorageError(Exception):
    """Base class for every BlobStore failure.

    Subclasses declare a contract error ``code``, a fixed ``summary`` and the
    subset of :data:`SAFE_DETAIL_KEYS` they may carry.
    """

    code: ClassVar[str] = "internal_error"
    summary: ClassVar[str] = "The blob store failed."
    allowed_details: ClassVar[frozenset[str]] = frozenset()

    def __init__(self, **details: object) -> None:
        unknown = set(details) - set(self.allowed_details)
        if unknown:
            raise TypeError(
                f"{type(self).__name__} may not carry the detail(s) "
                f"{sorted(unknown)!r}. Allowed: {sorted(self.allowed_details)!r}. "
                "Bucket and object key are deliberately absent from the "
                "vocabulary; see auditmanager.storage.errors."
            )
        self._details: dict[str, object] = dict(details)
        super().__init__(self._render())

    def _render(self) -> str:
        rendered = f"{self.code}: {self.summary}"
        if self._details:
            pairs = ", ".join(
                f"{name}={self._details[name]!r}" for name in sorted(self._details)
            )
            rendered = f"{rendered} [{pairs}]"
        return rendered

    @property
    def details(self) -> Mapping[str, object]:
        """Structured, key-free details safe to log or map into an envelope."""
        return dict(self._details)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._render()!r})"


# --- configuration -----------------------------------------------------------


class StorageConfigurationError(StorageError):
    """The adapter cannot be built from the configured environment.

    ``field`` carries the *name* of the frozen ``FF-01`` section 3 environment
    variable at fault. A name is not a value: the bucket's name is never
    rendered, only the fact that ``S3_BUCKET`` is the setting to look at.
    """

    code = "validation_failed"
    summary = "Object storage configuration is missing or invalid."
    allowed_details = frozenset({"field", "constraint"})


class StorageBucketMissingError(StorageConfigurationError):
    """The configured private bucket does not exist.

    Not transient, so it is a configuration fault rather than an availability
    one: no amount of retrying creates the bucket, and this adapter never
    creates it either. Bucket provisioning belongs to the local services task.
    """

    summary = "The configured object storage bucket does not exist."


# --- availability and authorization ------------------------------------------


class StorageUnavailableError(StorageError):
    """The object store could not be reached.

    This is the type that exists so that "storage is down" is never a silent
    fallback. There is no filesystem canonical adapter in this package; an
    unreachable store fails the operation and creates nothing.
    """

    code = "dependency_unavailable"
    summary = "Object storage is unavailable. Nothing was created."
    allowed_details = frozenset({"dependency"})

    def __init__(self, **details: object) -> None:
        details.setdefault("dependency", BLOB_STORAGE_DEPENDENCY)
        super().__init__(**details)


class StoragePermissionDeniedError(StorageError):
    """The configured application credentials were refused by the store.

    Raised for a rejected, missing or unsigned request against the private
    bucket. It is deliberately distinct from :class:`StorageUnavailableError`:
    a refused credential is not retryable and is not a degraded service.
    """

    code = "permission_denied"
    summary = "Object storage refused the configured application credentials."
    allowed_details = frozenset({"aggregate_type", "required_capability"})

    def __init__(self, **details: object) -> None:
        details.setdefault("aggregate_type", "Blob")
        super().__init__(**details)


# --- integrity ---------------------------------------------------------------


class BlobIntegrityError(StorageError):
    """Declared metadata does not match the bytes the store actually holds.

    The blob is never published. This is the ``verifying -> rejected`` guard of
    the frozen ``blob`` state machine.
    """

    code = "storage_integrity_error"
    summary = (
        "Declared blob metadata does not match the stored bytes. "
        "Nothing was published."
    )
    allowed_details = frozenset(
        {
            "actual_sha256",
            "actual_size",
            "expected_sha256",
            "expected_size",
            "media_type",
            "role",
        }
    )


class ChecksumMismatchError(BlobIntegrityError):
    """The SHA-256 of the stored bytes differs from the declared checksum."""

    summary = (
        "The stored bytes do not match the declared SHA-256. Nothing was published."
    )


class SizeMismatchError(BlobIntegrityError):
    """The byte count of the stored bytes differs from the declared size."""

    summary = "The stored bytes do not match the declared size. Nothing was published."


class TemporaryBlobLostError(StorageError):
    """A temporary upload disappeared between staging and verification."""

    code = "conflict"
    summary = "The temporary upload is no longer present. Nothing was published."
    allowed_details = frozenset({"aggregate_type"})

    def __init__(self, **details: object) -> None:
        details.setdefault("aggregate_type", "Blob")
        super().__init__(**details)


class BlobAttributeConflictError(StorageError):
    """Identical bytes are already published with different declared attributes.

    Blob identity is ``(sha256, size)``. Re-publishing those exact bytes under a
    different role or media type is refused rather than silently reinterpreting
    an already-available blob, whose bytes and metadata are immutable.
    """

    code = "conflict"
    summary = (
        "These bytes are already published with different declared attributes. "
        "Available blobs are immutable."
    )
    allowed_details = frozenset({"aggregate_type", "blob_id", "role", "media_type"})

    def __init__(self, **details: object) -> None:
        details.setdefault("aggregate_type", "Blob")
        super().__init__(**details)


# --- lookup ------------------------------------------------------------------


class BlobNotFoundError(StorageError):
    """No published blob is addressed by this ``blob_id``.

    The ``not_found`` code declares ``aggregate_type`` as its only safe detail,
    so the identifier is carried as an attribute for logging rather than
    rendered into the message.
    """

    code = "not_found"
    summary = "No published blob is addressed by that blob_id."
    allowed_details = frozenset({"aggregate_type"})

    def __init__(self, blob_id: str | None = None, **details: object) -> None:
        details.setdefault("aggregate_type", "Blob")
        self.blob_id = blob_id
        super().__init__(**details)


class BlobMetadataInvalidError(StorageError):
    """Declared blob metadata is not well-formed.

    Distinct from :class:`BlobIntegrityError`: nothing was compared against
    stored bytes, the declaration itself is malformed. ``field`` names which
    declaration -- ``sha256``, ``size``, ``role`` -- never a value.
    """

    code = "validation_failed"
    summary = "Declared blob metadata is not well-formed."
    allowed_details = frozenset({"field", "constraint"})


class InvalidBlobIdError(BlobMetadataInvalidError):
    """A string was offered as a ``blob_id`` but is not one."""

    summary = "The value offered is not a well-formed blob_id."


__all__ = [
    "BLOB_STORAGE_DEPENDENCY",
    "SAFE_DETAIL_KEYS",
    "BlobAttributeConflictError",
    "BlobIntegrityError",
    "BlobMetadataInvalidError",
    "BlobNotFoundError",
    "ChecksumMismatchError",
    "InvalidBlobIdError",
    "SizeMismatchError",
    "StorageBucketMissingError",
    "StorageConfigurationError",
    "StorageError",
    "StoragePermissionDeniedError",
    "StorageUnavailableError",
    "TemporaryBlobLostError",
]
