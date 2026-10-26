"""Operator command that promotes ONE reviewed retrieval set into durable custody.

::

    python -m auditmanager.norms.retrieval.promote_cli new-id
    python -m auditmanager.norms.retrieval.promote_cli plan    <bundle dir>
    python -m auditmanager.norms.retrieval.promote_cli promote <bundle dir>

The library (:mod:`auditmanager.norms.retrieval.promotion`) already encodes a two-person
check: the *candidate* bytes are computed from the database, the *expected* digests come
from an independent reviewer, and only equal digests are admitted. This command keeps the
two halves apart in time:

``plan``
    Read only. Builds the candidate inside one ``REPEATABLE READ READ ONLY`` transaction and
    prints its ``set_sha256`` and ``catalogue_sha256`` for the reviewer to compare with their
    own computation. It writes nothing to the database and never opens the object store.
``promote``
    Runs only when the bundle carries ``expected_set_sha256`` and ``expected_catalogue_sha256``
    that equal the freshly prepared candidate. It admits both artifacts (the R-76 outbox, one
    transaction), runs the custody dispatcher, then finalizes: both saved Blobs are read back and
    the immutable set row and both bindings are inserted in one transaction. Re-running the
    same command with the same ``set_id`` is an exact replay, never a duplicate.

The bundle directory holds exactly ``map.json`` (the reviewed canonical map bytes, hashed as
they are, never re-serialised) and ``request.json`` (:data:`REQUEST_FORMAT`). Unknown keys,
duplicate keys, floats, oversize files, symlinks and extra directory entries are refused.
``set_id`` is supplied by the operator so a retry names the same set; ``new-id`` prints a
fresh one. ``DATABASE_URL`` and the ``S3_*`` names come from the process environment.

The request is bound to the reviewed map before anything else happens: ``map.json`` is parsed
and every item's target spans in ``request.json`` must equal the spans the map lists for that
item, exactly (``request_targets_differ_from_map``); the label the request gives each mapped
document must equal the one designation the map's targets carry for it
(``request_designations_differ_from_map``), because that label is printed in every prompt row and
is a sort key; the request's snapshot must be the map's (``request_snapshot_differs_from_map``);
a map flagged ``synthetic`` is refused (``map_synthetic``). The library alone compares only the
*set* of document ids with the map, so without this the same map bytes and ``map_sha256`` could
carry prompt rows the map never listed, or rows attributed to another norm.

The ``synthetic`` flag is a guard against accidents, not a control against forgery: the map is
the reviewer's file, anyone who can write it can write ``false``, and this module does not load
the beta policy snapshot that ``map_pack validate`` compares with (the norms context does not
import the analysis profile). What holds a forged map is the library, which compares the map's
identity with the request's snapshot and reads that snapshot from the database, and the
reviewer's independently computed digests.

Exit status: 0 verified or replayed (``plan``: a candidate was computed and, if the bundle
carried expectations, they match); 2 refused with ``promote: REFUSED [reason]`` on stderr and
no database or object-store effect; 3 uncertain, some admission or dispatch state may exist,
and stderr names the ``set_id`` and the exact command to run next. Any other status is not
classified by this command: a bug before the admission step wrote nothing, but the process
being stopped by SIGTERM, SIGKILL or the out-of-memory killer during dispatch (Python cannot
catch the last two, and SIGTERM is not turned into an interrupt) can leave admissions behind
with no exit 3 and no ``next:`` line. After any such stop, re-running the same command is
idempotent: the same admissions are replayed, never duplicated.

The candidate bytes are the custody source: after an interruption a re-run recomputes them from
the same snapshot and bundle, and the dispatcher re-verifies their SHA-256 against what the
admission declared, so no staged copy outside the database is trusted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import sys
from array import array
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.norms.custody import (
    NORM_CATALOGUE,
    NORM_RETRIEVAL_SET,
    Admission,
    AdmissionState,
    Checkpoint,
    CustodyDispatcher,
    CustodyRefused,
    CustodySlot,
    DeclaredContent,
    blob_id_for,
)
from auditmanager.norms.custody.repository import CustodyRepository
from auditmanager.norms.embedding import vectors
from auditmanager.norms.retrieval import promotion
from auditmanager.norms.retrieval.artifact import ArtifactRefused, SetIdentity, canonical_json_bytes
from auditmanager.norms.retrieval.candidate import CandidateRefused
from auditmanager.norms.retrieval.evidence_bridge import (
    EvidenceBridgeRefused,
    ReviewedDesignation,
)
from auditmanager.norms.retrieval.promotion import (
    MAX_ARTIFACT_BYTES,
    PreparedPromotion,
    PromotionOutcome,
    PromotionRefused,
    PromotionRequest,
)
from auditmanager.norms.retrieval.qualification_decision import QualificationDecisionRefused
from auditmanager.norms.retrieval.qualification_reader import QualificationReadRefused
from auditmanager.norms.retrieval.ranking import RankingRefused, RetrievalItem, TargetSpan
from auditmanager.norms.retrieval.source_reader import SnapshotEvidenceRefused
from auditmanager.norms.retrieval.window_reader import WindowReadRefused
from auditmanager.shared.db import DatabaseError, get_session_factory, session_scope
from auditmanager.shared.identity import NormRetrievalSetId
from auditmanager.storage.public import BlobStore, S3BlobStore, S3StorageSettings, StorageError

REQUEST_FORMAT = "ar-set-promotion-request-v1"
MAP_NAME = "map.json"
REQUEST_NAME = "request.json"
MAX_REQUEST_BYTES = 4_000_000

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_UNCERTAIN = 3

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MEDIA_TYPE = "application/json"
#: The expected digests ``plan`` hands the library when the bundle carries none. They are
#: never reported as a verdict: ``plan`` prints ``not_compared`` in that case.
_NO_EXPECTATION = "0" * 64
_ROLES = (NORM_RETRIEVAL_SET, NORM_CATALOGUE)

_TOP_REQUIRED = frozenset({
    "format", "set_id", "snapshot_id", "reviewed_content_key", "embedding_build",
    "chunking_profile", "independently_checked_source_digest",
    "independently_checked_embedding_digest", "designations", "items",
})
_TOP_OPTIONAL = frozenset({"expected_set_sha256", "expected_catalogue_sha256"})

#: Refusals the library raises before it writes or reaches the object store.
_REFUSALS: tuple[type[BaseException], ...] = (
    PromotionRefused, CandidateRefused, QualificationDecisionRefused, QualificationReadRefused,
    SnapshotEvidenceRefused, WindowReadRefused, EvidenceBridgeRefused, ArtifactRefused,
    RankingRefused, CustodyRefused,
)


class CliRefused(ValueError):
    """The bundle or the stand cannot be promoted; ``reason`` is the stable classifier."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


# --- the bundle ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedBundle:
    request: PromotionRequest
    #: True when the bundle carried expected digests, so a verdict is meaningful.
    compared: bool
    #: Per item id, the reviewer-recorded SHA-256 of the query text its vector came from.
    query_text_digests: Mapping[str, str]


def _read_file(path: Path, limit: int, label: str) -> bytes:
    """Read one regular, non-symlink file of at most ``limit`` bytes."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        raise CliRefused(
            "bundle_unreadable", f"{label} is missing, a symlink or unreadable"
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise CliRefused("bundle_unreadable", f"{label} is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(limit + 1)
    finally:
        os.close(descriptor)
    if len(data) > limit:
        raise CliRefused("bundle_oversize", f"{label} exceeds {limit} bytes")
    return data


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate key")
    return dict(pairs)


def _strict_json(data: bytes) -> Any:
    # Floats and NaN parse, then fail the integer/text checks of every field that follows.
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_object_pairs)
    except (UnicodeError, ValueError) as exc:
        raise CliRefused(
            "request_invalid", f"{REQUEST_NAME} is not strict JSON ({exc})"
        ) from exc
    except RecursionError as exc:
        raise CliRefused("request_invalid", f"{REQUEST_NAME} is nested too deeply") from exc


def _object(
    value: Any, label: str, required: frozenset[str], optional: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CliRefused("request_invalid", f"{label} must be an object")
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    if missing or unknown:
        raise CliRefused(
            "request_invalid",
            f"{label}: missing {missing or 'nothing'}, unknown {unknown or 'nothing'}",
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CliRefused("request_invalid", f"{label} must be nonempty text")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise CliRefused("request_invalid", f"{label} must be a lowercase SHA-256")
    return value


def _ordinal(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise CliRefused("request_invalid", f"{label} must be an integer >= 0")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise CliRefused("request_invalid", f"{label} must be a nonempty list")
    return value


def _target(raw: Any, label: str) -> TargetSpan:
    target = _object(raw, label, frozenset({"document_id", "ordinal_first", "ordinal_last"}))
    return TargetSpan(
        document_id=_text(target["document_id"], f"{label}.document_id"),
        ordinal_first=_ordinal(target["ordinal_first"], f"{label}.ordinal_first"),
        ordinal_last=_ordinal(target["ordinal_last"], f"{label}.ordinal_last"),
    )


def _designation(raw: Any, label: str) -> ReviewedDesignation:
    row = _object(raw, label, frozenset({"document_id", "slug", "designation"}))
    return ReviewedDesignation(
        document_id=_text(row["document_id"], f"{label}.document_id"),
        slug=_text(row["slug"], f"{label}.slug"),
        designation=_text(row["designation"], f"{label}.designation"),
    )


def _item(raw: Any, label: str) -> tuple[RetrievalItem, str]:
    item = _object(
        raw, label, frozenset({"item_id", "query_vector_base64", "provenance", "targets"}),
    )
    provenance = _object(
        item["provenance"], f"{label}.provenance",
        frozenset({"query_text_sha256", "query_vector_sha256"}),
    )
    text_digest = _digest(provenance["query_text_sha256"], f"{label}.provenance.query_text_sha256")
    declared = _digest(provenance["query_vector_sha256"], f"{label}.provenance.query_vector_sha256")
    try:
        encoded = _text(item["query_vector_base64"], f"{label}.query_vector_base64")
        packed = vectors.from_base64(encoded)
        vectors.require_unit(packed)
    except vectors.VectorRefused as exc:
        raise CliRefused("request_invalid", f"{label}.query_vector_base64: {exc}") from exc
    if vectors.sha256(packed) != declared:
        raise CliRefused(
            "query_vector_digest_mismatch",
            f"{label}: the vector bytes do not hash to provenance.query_vector_sha256",
        )
    return RetrievalItem(
        item_id=_text(item["item_id"], f"{label}.item_id"),
        query_vector=array("f", vectors.unpack(packed)),
        targets=tuple(
            _target(target, f"{label}.targets[{index}]")
            for index, target in enumerate(_list(item["targets"], f"{label}.targets"))
        ),
    ), text_digest


@dataclass(frozen=True, slots=True)
class _ReviewedMap:
    """What the reviewed ``map.json`` itself says, in the terms the request is compared in."""

    snapshot_id: str
    #: Per item id, the sorted ``(document, first, last)`` spans.
    spans: Mapping[str, list[tuple[str, int, int]]]
    #: Per mapped document, the one designation every target of that document carries.
    designations: Mapping[str, str]


def _reviewed_targets(map_bytes: bytes) -> _ReviewedMap:
    """The snapshot, per-item spans and per-document designations the reviewed map lists.

    Reads the map the way the library validates it (``json.loads`` of the UTF-8 bytes, which must
    equal their own canonical encoding) and refuses a map it cannot read, because a request that
    cannot be compared with its map cannot be trusted to follow it. A map that gives one document
    two designations contradicts itself and is refused as well.
    """
    try:
        mapping = json.loads(map_bytes.decode("utf-8"))
        canonical = canonical_json_bytes(mapping)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        # `ArtifactRefused` (a float, non-NFC text) is a ValueError as well.
        raise CliRefused("map_invalid", f"{MAP_NAME} is not canonical JSON") from exc
    if not isinstance(mapping, dict) or canonical != map_bytes:
        raise CliRefused("map_invalid", f"{MAP_NAME} is not a canonical JSON object")
    synthetic = mapping.get("synthetic")
    if synthetic is True:
        raise CliRefused(
            "map_synthetic", f"{MAP_NAME} is flagged synthetic; a real promotion refuses it"
        )
    if synthetic is not False:
        raise CliRefused("map_invalid", f"{MAP_NAME} carries no boolean synthetic flag")
    snapshot_id = mapping.get("norms_snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise CliRefused("map_invalid", f"{MAP_NAME} carries no norms snapshot id")
    items = mapping.get("items")
    if not isinstance(items, list) or not items:
        raise CliRefused("map_invalid", f"{MAP_NAME} lists no items")
    reviewed: dict[str, list[tuple[str, int, int]]] = {}
    designations: dict[str, str] = {}
    for index, item in enumerate(items):
        label = f"{MAP_NAME} items[{index}]"
        item_id = item.get("id") if isinstance(item, dict) else None
        targets = item.get("targets") if isinstance(item, dict) else None
        if not isinstance(item_id, str) or not item_id or item_id in reviewed:
            raise CliRefused("map_invalid", f"{label} has no unique id")
        if not isinstance(targets, list) or not targets:
            raise CliRefused("map_invalid", f"{label} lists no targets")
        spans: list[tuple[str, int, int]] = []
        for target in targets:
            document = target.get("norm_document_id") if isinstance(target, dict) else None
            first = target.get("ordinal_first") if isinstance(target, dict) else None
            last = target.get("ordinal_last") if isinstance(target, dict) else None
            designation = target.get("designation") if isinstance(target, dict) else None
            if (
                not isinstance(document, str) or not document or type(first) is not int
                or type(last) is not int or first < 0 or last < first
            ):
                raise CliRefused("map_invalid", f"{label} has a target that is not a document span")
            if not isinstance(designation, str) or not designation:
                raise CliRefused("map_invalid", f"{label} has a target without a designation")
            if designations.setdefault(document, designation) != designation:
                raise CliRefused(
                    "map_invalid", f"{label} gives one document two different designations"
                )
            spans.append((document, first, last))
        reviewed[item_id] = sorted(spans)
    # Every mapped document must have a designation in the map to be compared with (`map_pack`
    # writes exactly the documents of the targets, sorted).
    if mapping.get("mapped_document_ids") != sorted(designations):
        raise CliRefused(
            "map_invalid", f"{MAP_NAME} mapped_document_ids are not the documents of its targets"
        )
    return _ReviewedMap(snapshot_id, reviewed, designations)


def _bind_request_to_map(
    map_bytes: bytes,
    items: tuple[RetrievalItem, ...],
    designations: tuple[ReviewedDesignation, ...],
    snapshot_id: str,
) -> None:
    """The request's snapshot, items, spans and document labels must be the reviewed map's.

    The library compares only the set of document ids and the ordered item ids with the map; the
    spans, and with them the prompt rows, would otherwise be whatever the request said, and so
    would the label printed in each row. The order of one item's spans is not a difference, their
    number and values are. A refusal names item ids or counts, never a span, a label or a document.
    """
    reviewed = _reviewed_targets(map_bytes)
    if snapshot_id != reviewed.snapshot_id:
        raise CliRefused(
            "request_snapshot_differs_from_map",
            f"the request's snapshot_id is not the reviewed {MAP_NAME}'s norms_snapshot_id",
        )
    requested = [item.item_id for item in items]
    if len(set(requested)) != len(requested) or set(requested) != set(reviewed.spans):
        differing = sorted(set(requested) ^ set(reviewed.spans)) or sorted(requested)
        raise CliRefused(
            "request_items_differ_from_map",
            "the request's items are not the reviewed map's items: " + ", ".join(differing),
        )
    def spans(item: RetrievalItem) -> list[tuple[str, int, int]]:
        return sorted((s.document_id, s.ordinal_first, s.ordinal_last) for s in item.targets)

    differing = [item.item_id for item in items if spans(item) != reviewed.spans[item.item_id]]
    if differing:
        raise CliRefused(
            "request_targets_differ_from_map",
            "the request's target spans differ from the reviewed map for: " + ", ".join(differing),
        )
    labelled = [entry.document_id for entry in designations]
    differing_documents = (set(labelled) ^ set(reviewed.designations)) | {
        entry.document_id for entry in designations
        if reviewed.designations.get(entry.document_id) != entry.designation
    }
    if len(set(labelled)) != len(labelled) or differing_documents:
        raise CliRefused(
            "request_designations_differ_from_map",
            "the request's designations are not the reviewed map's for "
            f"{max(len(differing_documents), 1)} of {len(reviewed.designations)} mapped "
            "documents; compare each document's designation in request.json with the "
            f"designation of its targets in {MAP_NAME}",
        )


def load_bundle(directory: Path, *, require_expected: bool) -> LoadedBundle:
    """Parse and strictly validate one bundle directory; touches nothing else."""
    try:
        info = os.lstat(directory)
    except (OSError, ValueError) as exc:  # ValueError: an embedded NUL byte in the path
        raise CliRefused("bundle_unreadable", "the bundle directory is missing") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CliRefused("bundle_unreadable", "the bundle path is not a real directory (symlink?)")
    try:
        names = sorted(os.listdir(directory))
    except OSError as exc:
        raise CliRefused("bundle_unreadable", "the bundle directory cannot be listed") from exc
    if names != sorted((MAP_NAME, REQUEST_NAME)):
        raise CliRefused(
            "bundle_layout",
            f"the bundle must hold exactly {MAP_NAME} and {REQUEST_NAME}, found {names}",
        )
    map_bytes = _read_file(directory / MAP_NAME, MAX_ARTIFACT_BYTES, MAP_NAME)
    raw = _object(
        _strict_json(_read_file(directory / REQUEST_NAME, MAX_REQUEST_BYTES, REQUEST_NAME)),
        REQUEST_NAME, _TOP_REQUIRED, _TOP_OPTIONAL,
    )
    if raw["format"] != REQUEST_FORMAT:
        raise CliRefused("request_invalid", f"format must be {REQUEST_FORMAT!r}")
    present = _TOP_OPTIONAL & raw.keys()
    if present and present != _TOP_OPTIONAL:
        raise CliRefused(
            "request_invalid", "expected_set_sha256 and expected_catalogue_sha256 come together"
        )
    if require_expected and not present:
        raise CliRefused(
            "expected_digests_required",
            "promote needs expected_set_sha256 and expected_catalogue_sha256 from the "
            "independent reviewer; run plan first",
        )
    set_id = _text(raw["set_id"], "set_id")
    try:
        # The explicit line-break test keeps this check independent of the shared parser's
        # anchoring: an identity is the whole string.
        if "\n" in set_id:
            raise ValueError("line break")
        NormRetrievalSetId.parse(set_id)
    except (TypeError, ValueError) as exc:
        raise CliRefused("request_invalid", "set_id is not an nrs_ identity") from exc
    designations = tuple(
        _designation(entry, f"designations[{index}]")
        for index, entry in enumerate(_list(raw["designations"], "designations"))
    )
    parsed = [
        _item(entry, f"items[{index}]") for index, entry in enumerate(_list(raw["items"], "items"))
    ]
    items = tuple(item for item, _ in parsed)
    snapshot_id = _text(raw["snapshot_id"], "snapshot_id")
    _bind_request_to_map(map_bytes, items, designations, snapshot_id)
    request = PromotionRequest(
        set_id=set_id,
        identity=SetIdentity(
            map_sha256=hashlib.sha256(map_bytes).hexdigest(),
            snapshot_id=snapshot_id,
            reviewed_content_key=_text(raw["reviewed_content_key"], "reviewed_content_key"),
            embedding_build=_text(raw["embedding_build"], "embedding_build"),
        ),
        map_bytes=map_bytes,
        reviewed_designations=designations,
        items=items,
        chunking_profile=_text(raw["chunking_profile"], "chunking_profile"),
        independently_checked_source_digest=_digest(
            raw["independently_checked_source_digest"], "independently_checked_source_digest"
        ),
        independently_checked_embedding_digest=_digest(
            raw["independently_checked_embedding_digest"], "independently_checked_embedding_digest"
        ),
        expected_set_sha256=(
            _digest(raw["expected_set_sha256"], "expected_set_sha256")
            if present else _NO_EXPECTATION
        ),
        expected_catalogue_sha256=(
            _digest(raw["expected_catalogue_sha256"], "expected_catalogue_sha256")
            if present else _NO_EXPECTATION
        ),
    )
    return LoadedBundle(
        request=request, compared=bool(present),
        query_text_digests={item.item_id: digest for item, digest in parsed},
    )


# --- the world the command acts on ----------------------------------------------------------


class PromotionRunner(Protocol):
    """Everything ``plan`` and ``promote`` do to the database and the object store."""

    def prepare(self, request: PromotionRequest) -> PreparedPromotion:
        """Candidate bytes and comparison from one read-only transaction."""

    def admit(self, prepared: PreparedPromotion) -> tuple[str, str]:
        """Admit both artifacts in one transaction, or refuse with nothing written."""

    def settle(self, prepared: PreparedPromotion) -> Mapping[str, str]:
        """Dispatch until idle; the state of each role's live admission afterwards."""

    def finalize(self, prepared: PreparedPromotion) -> PromotionOutcome:
        """Verify both saved Blobs, then insert the set row and both bindings."""


RunnerFactory = Callable[[bool], PromotionRunner]


@dataclass(frozen=True, slots=True)
class _Manifest:
    """The custody manifest of one promotion: the reviewer's digests, this set's two slots."""

    set_id: str
    entries: Mapping[str, DeclaredContent]

    def declared(self, slot: CustodySlot) -> DeclaredContent | None:
        if (
            slot.target_kind != "norm_retrieval_set" or slot.target_id != self.set_id
            or slot.anchor_kind != "artifact"
        ):
            return None
        return self.entries.get(slot.role)


@dataclass(frozen=True, slots=True)
class _Source:
    """Serves the freshly recomputed candidate bytes to the dispatcher, by role and set."""

    set_id: str
    data: Mapping[str, bytes]

    def open(self, admission: Admission) -> bytes | BinaryIO:
        if admission.target_id != self.set_id or admission.role not in self.data:
            # Never serve a foreign admission: the dispatcher would count a transient try
            # against it. ``admit`` refuses first while any other admission is pending.
            raise FileNotFoundError("admission is not part of this promotion")
        return self.data[admission.role]


def _artifact_bytes(prepared: PreparedPromotion) -> dict[str, bytes]:
    return {
        NORM_RETRIEVAL_SET: prepared.candidate.retrieval_set.data,
        NORM_CATALOGUE: prepared.candidate.catalogue.data,
    }


class DatabaseRunner:
    """The production runner: the library functions over a real session factory and store."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: BlobStore | None = None,
        *,
        checkpoint: Checkpoint | None = None,
    ) -> None:
        self._factory = session_factory
        self._store = store
        self._checkpoint = checkpoint

    def _require_store(self) -> BlobStore:
        if self._store is None:
            raise CliRefused("blob_store_unavailable", "this step needs the object store")
        return self._store

    def prepare(self, request: PromotionRequest) -> PreparedPromotion:
        session = self._factory()
        try:
            session.connection(execution_options={
                "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
            })
            return promotion.prepare_promotion(session, request)
        finally:
            session.rollback()
            session.close()

    def admit(self, prepared: PreparedPromotion) -> tuple[str, str]:
        request = prepared.request
        expected = {
            NORM_RETRIEVAL_SET: request.expected_set_sha256,
            NORM_CATALOGUE: request.expected_catalogue_sha256,
        }
        manifest = _Manifest(request.set_id, {
            role: DeclaredContent(expected[role], len(data), _MEDIA_TYPE)
            for role, data in _artifact_bytes(prepared).items()
        })
        repository = CustodyRepository()
        with session_scope(self._factory) as session:
            everywhere = repository.state_counts(session, role=None, target_ids=None)
            mine = sum(
                repository.state_counts(session, role=role, target_ids=[request.set_id]).get(
                    AdmissionState.PENDING, 0
                )
                for role in _ROLES
            )
            if everywhere.get(AdmissionState.PENDING, 0) > mine:
                raise CliRefused(
                    "foreign_pending_admissions",
                    "another custody admission is pending; the dispatcher takes any due "
                    "admission, so let its owner finish or requeue it first",
                )
            return promotion.admit_matched(session, prepared, manifest=manifest)

    def settle(self, prepared: PreparedPromotion) -> Mapping[str, str]:
        dispatcher = CustodyDispatcher(
            self._require_store(),
            source=_Source(prepared.request.set_id, _artifact_bytes(prepared)),
            session_factory=self._factory,
            checkpoint=self._checkpoint,
        )
        dispatcher.dispatch()
        repository = CustodyRepository()
        states: dict[str, str] = {}
        with session_scope(self._factory) as session:
            for role in _ROLES:
                counts = repository.state_counts(
                    session, role=role, target_ids=[prepared.request.set_id],
                )
                # One live admission per slot at most; earlier rejected ones are history.
                live = [
                    state for state in (
                        AdmissionState.CONFIRMED, AdmissionState.PENDING, AdmissionState.POISONED,
                    ) if counts.get(state, 0)
                ]
                states[role] = live[0].value if live else "none"
        return states

    def finalize(self, prepared: PreparedPromotion) -> PromotionOutcome:
        with session_scope(self._factory) as session:
            return promotion.finalize_matched(session, prepared, blob_store=self._require_store())


def runner_from_environment(with_store: bool) -> PromotionRunner:
    """The application's own session factory and S3 store, from the frozen environment names."""
    store: BlobStore | None = None
    if with_store:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    return DatabaseRunner(get_session_factory(), store)


# --- the commands ---------------------------------------------------------------------------


def _reason_of(exc: BaseException) -> tuple[str, str]:
    """A stable classifier and a safe one-line message for a typed refusal."""
    if isinstance(exc, CliRefused):
        return exc.reason, exc.message
    if isinstance(exc, CustodyRefused):
        return exc.reason, str(exc)
    if isinstance(exc, StorageError):
        return "blob_store_unavailable", str(exc)
    if isinstance(exc, (DatabaseError, SQLAlchemyError)):
        return "database_unavailable", type(exc).__name__
    reason = re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()
    return reason, str(exc)


def _oneline(value: str, limit: int = 300) -> str:
    collapsed = " ".join(value.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"


def _refused(command: str, exc: BaseException) -> int:
    reason, message = _reason_of(exc)
    print(f"{command}: REFUSED [{reason}]: {_oneline(message)}", file=sys.stderr)
    return EXIT_REFUSED


def _uncertain(request: PromotionRequest, bundle: Path, reason: str, message: str) -> int:
    print(f"promote: UNCERTAIN [{reason}]: {_oneline(message)}", file=sys.stderr)
    print(f"set_id: {request.set_id}", file=sys.stderr)
    print(
        "state: an admission or dispatch step may exist; no verified set row is claimed. "
        "Re-running is idempotent for this set_id.",
        file=sys.stderr,
    )
    print(
        "next: python -m auditmanager.norms.retrieval.promote_cli promote "
        + shlex.quote(str(bundle)),
        file=sys.stderr,
    )
    return EXIT_UNCERTAIN


def _print_candidate(
    prepared: PreparedPromotion, *, compared: bool,
    query_text_digests: Mapping[str, str] | None = None,
) -> None:
    request, candidate = prepared.request, prepared.candidate
    identity = request.identity
    for name, value in (
        ("set_id", request.set_id),
        ("snapshot_id", identity.snapshot_id),
        ("reviewed_content_key", identity.reviewed_content_key),
        ("embedding_build", identity.embedding_build),
        ("chunking_profile", request.chunking_profile),
        ("map_sha256", identity.map_sha256),
        ("source_proof_digest", request.independently_checked_source_digest),
        ("embedding_proof_digest", request.independently_checked_embedding_digest),
        ("set_sha256", candidate.retrieval_set.sha256),
        ("set_size_bytes", len(candidate.retrieval_set.data)),
        ("catalogue_sha256", candidate.catalogue.sha256),
        ("catalogue_size_bytes", len(candidate.catalogue.data)),
        ("prompt_part_characters", len(candidate.selection.prompt_part)),
        ("verdict", prepared.comparison.status if compared else "not_compared"),
    ):
        print(f"{name}: {value}")
    # The reviewer compares these against the map's own query and target decisions.
    for item in request.items if query_text_digests is not None else ():
        spans = ",".join(
            f"{span.document_id}:{span.ordinal_first}-{span.ordinal_last}" for span in item.targets
        )
        print(
            f"item: {item.item_id} query_text_sha256={query_text_digests[item.item_id]} "
            f"query_vector_sha256={vectors.sha256(vectors.pack(item.query_vector))} targets={spans}"
        )
    if query_text_digests is not None:
        # The label that reaches every prompt row of a document; `load_bundle` has already proved
        # it equal to the designation of that document's targets in the reviewed map.
        for reviewed in sorted(request.reviewed_designations, key=lambda row: row.document_id):
            label = json.dumps(reviewed.designation, ensure_ascii=False)
            print(f"designation: {reviewed.document_id} {label}")


def _mismatch(prepared: PreparedPromotion) -> CliRefused:
    return CliRefused(
        "expected_digest_mismatch",
        "the expected digests differ from the candidate for: "
        + ", ".join(prepared.comparison.different_artifacts),
    )


def _plan(bundle: Path, factory: RunnerFactory) -> int:
    try:
        loaded = load_bundle(bundle, require_expected=False)
        prepared = factory(False).prepare(loaded.request)
        _print_candidate(
            prepared, compared=loaded.compared, query_text_digests=loaded.query_text_digests,
        )
        if loaded.compared and prepared.comparison.status != "matched":
            raise _mismatch(prepared)
    except (*_REFUSALS, CliRefused, StorageError, DatabaseError, SQLAlchemyError) as exc:
        return _refused("plan", exc)
    return EXIT_OK


def _promote(bundle: Path, factory: RunnerFactory) -> int:
    # Everything up to the end of ``admit`` either refuses with nothing written or raises
    # inside one rolled-back transaction.
    try:
        loaded = load_bundle(bundle, require_expected=True)
        runner = factory(True)
        prepared = runner.prepare(loaded.request)
        if prepared.comparison.status != "matched":
            _print_candidate(prepared, compared=True)
            raise _mismatch(prepared)
    except (*_REFUSALS, CliRefused, StorageError, DatabaseError, SQLAlchemyError) as exc:
        return _refused("promote", exc)
    request = loaded.request
    try:
        runner.admit(prepared)
    except (*_REFUSALS, CliRefused) as exc:
        return _refused("promote", exc)
    except (Exception, KeyboardInterrupt) as exc:
        return _uncertain(request, bundle, "admission_uncertain", type(exc).__name__)
    # From here an admission is committed; any stop leaves a state a re-run converges from.
    try:
        states = runner.settle(prepared)
        unsettled = {role: state for role, state in states.items() if state != "confirmed"}
        if unsettled:
            detail = ", ".join(f"{role}={state}" for role, state in sorted(unsettled.items()))
            hint = (
                " A poisoned admission needs custody requeue first; a pending one is retried "
                "after its delay (30 s, 5 min, 30 min, 2 h)."
            )
            return _uncertain(request, bundle, "dispatch_unsettled", detail + "." + hint)
        outcome = runner.finalize(prepared)
    except PromotionRefused as exc:
        return _uncertain(request, bundle, "finalize_refused", str(exc))
    except (Exception, KeyboardInterrupt) as exc:
        return _uncertain(
            request, bundle, "interrupted", f"{type(exc).__name__}: {_oneline(str(exc), 200)}",
        )
    comparison = prepared.comparison
    set_size = len(prepared.candidate.retrieval_set.data)
    catalogue_size = len(prepared.candidate.catalogue.data)
    print("promote: verified")
    print(f"set_id: {outcome.set_id}")
    print(f"replayed: {'true' if outcome.replayed else 'false'}")
    print(f"set_sha256: {comparison.observed_set_sha256}")
    print(f"set_blob_id: {blob_id_for(comparison.observed_set_sha256, set_size)}")
    print(f"catalogue_sha256: {comparison.observed_catalogue_sha256}")
    print(f"catalogue_blob_id: {blob_id_for(comparison.observed_catalogue_sha256, catalogue_size)}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None, *, runner_factory: RunnerFactory | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m auditmanager.norms.retrieval.promote_cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-id", help="print a fresh nrs_ identity for a bundle's set_id")
    for name, text in (
        ("plan", "read-only: print the candidate set and catalogue digests"),
        ("promote", "admit, dispatch and finalize when the expected digests match"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    if args.command == "new-id":
        print(NormRetrievalSetId.new())
        return EXIT_OK
    factory = runner_factory or runner_from_environment
    if args.command == "plan":
        return _plan(args.bundle, factory)
    return _promote(args.bundle, factory)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "REQUEST_FORMAT", "CliRefused", "DatabaseRunner", "LoadedBundle", "PromotionRunner",
    "load_bundle", "main", "runner_from_environment",
]
