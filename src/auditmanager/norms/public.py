"""Cross-context surface of the normative-corpus context.

`W54-CUSTODY-01` opens it with the custody surface. Later W54 lanes add their export lines
here in plan §6's order (REPAIR, SNAPSHOT, EMBED, BUNDLE); nothing outside
``auditmanager.norms`` imports a deeper module of this context (ALR-05).
"""

from __future__ import annotations

from auditmanager.norms.citation_prep import (
    GroundedNormCitation,
    NormCitation,
    NormLabelBinding,
    NormParagraph,
    ground_norm_observation,
)
from auditmanager.norms.bundle import (  # W54-BUNDLE-01
    FINGERPRINT_ALGORITHM,
    MANIFEST_FORMAT,
    BundleRefused,
    Manifest,
    Stand,
    compute_fingerprint,
    export_bundle,
    import_bundle,
    parse_manifest,
    report_bundle,
    requeue_bundle,
    verify_bundle,
)
from auditmanager.norms.chunking import (  # W54-SNAPSHOT-01
    RELIABLE_CHUNKING_PROFILE_VERSION,
    ChunkingRefused,
)
from auditmanager.norms.custody import (
    ADMIT_COMMAND_TYPE,
    D143_MESSAGE,
    D143_REASON,
    MAX_ATTEMPTS,
    NORM_SOURCE,
    NORM_RETRIEVAL_SET,
    NORM_CATALOGUE,
    RETRY_DELAYS_SECONDS,
    ROLE_SHAPES,
    Admission,
    AdmissionRequest,
    AdmissionState,
    AdmitOutcome,
    Binding,
    BindingDigestEntry,
    BindingPublication,
    Checkpoint,
    CustodyDispatcher,
    CustodyIncident,
    CustodyManifest,
    CustodyReconciler,
    CustodyReconciliation,
    CustodyRefused,
    CustodyReport,
    CustodySlot,
    CustodySource,
    DeclaredContent,
    DispatchReport,
    DispatchResult,
    DispatchStep,
    IncidentKind,
    ManifestIndex,
    RejectedBlob,
    RoleShape,
    admit,
    binding_digest,
    blob_id_for,
    publish_bindings,
    report,
    requeue,
)
from auditmanager.norms.current_snapshot import (  # W55A-SEARCH-01
    CurrentSnapshot,
    Designation,
    Qualification,
    SnapshotEvent,
    current_snapshot,
    has_been_current,
    list_snapshot_events,
    qualification,
    set_current_snapshot,
)
from auditmanager.norms.degeneracy import DegeneracySignal, inspect as inspect_degeneracy  # W55B-RECOGNISED-01
from auditmanager.norms.embedding import (  # W54-EMBED-01
    EMBEDDING_PROFILE,
    EMBEDDING_SET_DIGEST_VERSION,
    EmbeddingSetDigest,
)
from auditmanager.norms.embedding import (
    REQUEST_FORMAT as EMBED_TEXTS_REQUEST_FORMAT,  # W54-EMBED-01
)
from auditmanager.norms.embedding import (
    RESPONSE_FORMAT as EMBED_TEXTS_RESPONSE_FORMAT,  # W54-EMBED-01
)
from auditmanager.norms.embedding_repository import (  # W54-EMBED-01
    NearestEmbedding,
    NormEmbeddingConflict,
    NormEmbeddingRepository,
    NormEmbeddingScanShort,
    StoredEmbeddingBuild,
)
from auditmanager.norms.loader import (  # W54-SNAPSHOT-01
    CorpusLoadResult,
    SnapshotImportResult,
    import_snapshot,
    load_corpus,
)
from auditmanager.norms.model import TextReliability  # W54-SNAPSHOT-01
from auditmanager.norms.repair import (  # W54-REPAIR-01
    LEDGER_VERSION,
    RepairLedger,
    RepairOutcome,
    repaired_snapshot,
)
from auditmanager.norms.repository import (  # W54-SNAPSHOT-01
    NormsProjectionConflict,
    SnapshotImportConflict,
    SnapshotRowsInvalid,
)
from auditmanager.norms.search import (  # W55A-SEARCH-01
    SEARCH_WINDOW,
    EventPosition,
    decode_event_cursor,
    encode_event_cursor,
)
from auditmanager.norms.search import get_document as get_norm_document  # W55A-SEARCH-01
from auditmanager.norms.search import (
    list_paragraphs as list_norm_paragraphs,  # W55A-SEARCH-01
)
from auditmanager.norms.search import list_snapshots as list_norm_snapshots  # W55A-SEARCH-01
from auditmanager.norms.search import pdf_binding as norm_pdf_binding  # W55A-SEARCH-01
from auditmanager.norms.search import search as search_norms  # W55A-SEARCH-01
from auditmanager.norms.snapshot import (  # W54-SNAPSHOT-01
    ROW_DIGEST_VERSION,
    DocumentRow,
    ParagraphRow,
    SnapshotRow,
    SnapshotRows,
    row_digest,
)

__all__ = [
    "ADMIT_COMMAND_TYPE",
    "D143_MESSAGE",
    "D143_REASON",
    "EMBEDDING_PROFILE",
    "EMBEDDING_SET_DIGEST_VERSION",
    "EMBED_TEXTS_REQUEST_FORMAT",
    "EMBED_TEXTS_RESPONSE_FORMAT",
    "FINGERPRINT_ALGORITHM",
    "GroundedNormCitation",
    "LEDGER_VERSION",
    "MANIFEST_FORMAT",
    "MAX_ATTEMPTS",
    "NORM_SOURCE",
    "NORM_RETRIEVAL_SET",
    "NORM_CATALOGUE",
    "RELIABLE_CHUNKING_PROFILE_VERSION",
    "RETRY_DELAYS_SECONDS",
    "ROLE_SHAPES",
    "ROW_DIGEST_VERSION",
    "SEARCH_WINDOW",
    "Admission",
    "AdmissionRequest",
    "AdmissionState",
    "AdmitOutcome",
    "Binding",
    "BindingDigestEntry",
    "BindingPublication",
    "BundleRefused",
    "Checkpoint",
    "ChunkingRefused",
    "CorpusLoadResult",
    "CurrentSnapshot",
    "CustodyDispatcher",
    "CustodyIncident",
    "CustodyManifest",
    "CustodyReconciler",
    "CustodyReconciliation",
    "CustodyRefused",
    "CustodyReport",
    "CustodySlot",
    "CustodySource",
    "DeclaredContent",
    "DegeneracySignal",
    "Designation",
    "DispatchReport",
    "DispatchResult",
    "DispatchStep",
    "DocumentRow",
    "EmbeddingSetDigest",
    "EventPosition",
    "IncidentKind",
    "Manifest",
    "ManifestIndex",
    "NearestEmbedding",
    "NormEmbeddingConflict",
    "NormEmbeddingRepository",
    "NormEmbeddingScanShort",
    "NormCitation",
    "NormLabelBinding",
    "NormParagraph",
    "NormsProjectionConflict",
    "ParagraphRow",
    "Qualification",
    "RejectedBlob",
    "RepairLedger",
    "RepairOutcome",
    "RoleShape",
    "SnapshotEvent",
    "SnapshotImportConflict",
    "SnapshotImportResult",
    "SnapshotRow",
    "SnapshotRows",
    "SnapshotRowsInvalid",
    "Stand",
    "StoredEmbeddingBuild",
    "TextReliability",
    "admit",
    "binding_digest",
    "blob_id_for",
    "compute_fingerprint",
    "current_snapshot",
    "decode_event_cursor",
    "encode_event_cursor",
    "export_bundle",
    "get_norm_document",
    "ground_norm_observation",
    "has_been_current",
    "import_bundle",
    "import_snapshot",
    "inspect_degeneracy",
    "list_norm_paragraphs",
    "list_norm_snapshots",
    "list_snapshot_events",
    "load_corpus",
    "norm_pdf_binding",
    "parse_manifest",
    "publish_bindings",
    "qualification",
    "repaired_snapshot",
    "report",
    "report_bundle",
    "requeue",
    "requeue_bundle",
    "row_digest",
    "search_norms",
    "set_current_snapshot",
    "verify_bundle",
]
