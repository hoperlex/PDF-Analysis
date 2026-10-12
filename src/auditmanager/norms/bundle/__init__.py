"""The promotion bundle: export, import, report (`W54-BUNDLE-01`, `W54-PLAN.md` §3.5).

A bundle carries one repaired snapshot from the promotion database to the stand with its
ids: the canonical rows, the complete embedding build keyed by the computed chunk key, and
every source PDF and crop as content-addressed objects with the custody slots they serve.
It is named ``<content_key>+<sha256(SHA256SUMS)>`` and is imported all-or-nothing by
``python -m auditmanager.norms.bundle import`` under an accepted copy record.

Modules: ``layout`` (name, sums, tree rule), ``manifest`` (``manifest.json``),
``contents`` (rows and build files), ``copy_record`` (the record's acceptance rule and the
stand fingerprint), ``export`` (this host), ``stand`` (import, report, requeue) and
``cli``.
"""

from .copy_record import (
    FINGERPRINT_ALGORITHM,
    AcceptedRecord,
    CopyRecord,
    StandFingerprint,
    accept_for_import,
    compute_fingerprint,
    read_copy_record,
)
from .errors import EXIT_INCOMPLETE, EXIT_MISMATCH, EXIT_OK, EXIT_REFUSED, BundleRefused
from .export import (
    ExportResult,
    ExportSource,
    export_bundle,
    read_export_source,
    write_bundle,
)
from .layout import VerifiedBundle, bundle_name, verify_bundle
from .manifest import MANIFEST_FORMAT, MIN_MIGRATION_HEAD, Manifest, parse_manifest
from .stand import BundleSource, Stand, import_bundle, report_bundle, requeue_bundle

__all__ = [
    "EXIT_INCOMPLETE",
    "EXIT_MISMATCH",
    "EXIT_OK",
    "EXIT_REFUSED",
    "FINGERPRINT_ALGORITHM",
    "MANIFEST_FORMAT",
    "MIN_MIGRATION_HEAD",
    "AcceptedRecord",
    "BundleRefused",
    "BundleSource",
    "CopyRecord",
    "ExportResult",
    "ExportSource",
    "Manifest",
    "Stand",
    "StandFingerprint",
    "VerifiedBundle",
    "accept_for_import",
    "bundle_name",
    "compute_fingerprint",
    "export_bundle",
    "import_bundle",
    "parse_manifest",
    "read_copy_record",
    "read_export_source",
    "report_bundle",
    "requeue_bundle",
    "verify_bundle",
    "write_bundle",
]
