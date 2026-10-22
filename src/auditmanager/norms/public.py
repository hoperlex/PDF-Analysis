"""Cross-context surface of the normative-corpus context.

`W54-CUSTODY-01` opens it with the custody surface. Later W54 lanes add their export lines
here in plan §6's order (REPAIR, SNAPSHOT, EMBED, BUNDLE); nothing outside
``auditmanager.norms`` imports a deeper module of this context (ALR-05).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auditmanager.analysis.public import TextLayer
    from auditmanager.norms.references.observation_plan import ReferencePage

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
from auditmanager.norms.catalogue import (  # W57B-NORMS-CATALOGUE-XLSX-01
    CatalogueEntry,
    CataloguePage,
    DisplayName,
    KindCount,
    display_name,
)
from auditmanager.norms.catalogue import list_documents as list_norm_catalogue  # W57B-NORMS-CATALOGUE-XLSX-01
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
from auditmanager.norms.references.catalogue_input import (
    CatalogueInputRefused,
    VerifiedCatalogueInput,
    load_verified_catalogue,
)
from auditmanager.norms.references.pipeline import (
    ReferencePipelineResult,
    run_reference_pipeline,
)
from auditmanager.norms.references.read_model import (  # NORM-REFS-RUN-01
    CitationAnchor,
    CitedNorm,
    ReferenceReadModel,
    TooManyCitations,
    UnrecognisedSlug,
    build_reference_read_model,
)
from auditmanager.norms.references.resolution import ReferenceRefused  # NORM-REFS-RUN-01
from auditmanager.norms.references.snapshot_catalogue import (  # NORM-REFS-RUN-01
    read_snapshot_catalogue,
)
from auditmanager.norms.repair import (  # W54-REPAIR-01
    LEDGER_VERSION,
    RepairLedger,
    RepairOutcome,
    repaired_snapshot,
)
from auditmanager.norms.retrieval.promotion import (
    PreparedPromotion,
    PromotionOutcome,
    PromotionRefused,
    PromotionRequest,
    admit_matched,
    finalize_matched,
    prepare_promotion,
    record_rejection,
    select_verified_retrieval_set,
)
from auditmanager.norms.retrieval.promotion_repository import VerifiedSetReference
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


def reference_pages_from_text_layer(
    *, text_layer: TextLayer, version_uid: str, page_count: int
) -> tuple[ReferencePage, ...]:
    """Expose the pure bridge without a public-facade import cycle."""
    from auditmanager.norms.references.text_pages import (
        reference_pages_from_text_layer as bridge,
    )

    return bridge(
        text_layer=text_layer, version_uid=version_uid, page_count=page_count,
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
    "CitationAnchor",
    "CitedNorm",
    "CorpusLoadResult",
    "CatalogueEntry",
    "CatalogueInputRefused",
    "CataloguePage",
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
    "DisplayName",
    "DocumentRow",
    "EmbeddingSetDigest",
    "EventPosition",
    "IncidentKind",
    "KindCount",
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
    "PreparedPromotion",
    "PromotionOutcome",
    "PromotionRefused",
    "PromotionRequest",
    "Qualification",
    "RejectedBlob",
    "RepairLedger",
    "RepairOutcome",
    "ReferencePipelineResult",
    "ReferenceReadModel",
    "ReferenceRefused",
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
    "TooManyCitations",
    "UnrecognisedSlug",
    "VerifiedCatalogueInput",
    "VerifiedSetReference",
    "admit",
    "admit_matched",
    "binding_digest",
    "blob_id_for",
    "build_reference_read_model",
    "compute_fingerprint",
    "current_snapshot",
    "decode_event_cursor",
    "display_name",
    "encode_event_cursor",
    "export_bundle",
    "finalize_matched",
    "get_norm_document",
    "ground_norm_observation",
    "has_been_current",
    "import_bundle",
    "import_snapshot",
    "inspect_degeneracy",
    "list_norm_catalogue",
    "list_norm_paragraphs",
    "list_norm_snapshots",
    "list_snapshot_events",
    "load_verified_catalogue",
    "load_corpus",
    "norm_pdf_binding",
    "parse_manifest",
    "prepare_promotion",
    "publish_bindings",
    "qualification",
    "read_snapshot_catalogue",
    "reference_pages_from_text_layer",
    "repaired_snapshot",
    "report",
    "report_bundle",
    "record_rejection",
    "requeue",
    "requeue_bundle",
    "row_digest",
    "run_reference_pipeline",
    "search_norms",
    "select_verified_retrieval_set",
    "set_current_snapshot",
    "verify_bundle",
]
