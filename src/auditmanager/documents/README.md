# `documents` boundary

Objects, disciplines, projects, documents and display metadata. Owns explicit current-version pointer transitions with ingest collaboration.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.

## How a version reached the product (`CMP-INGEST-01`)

`document_version.upload_kind` is `portal_bundle` (every version before migration `0038`) or `comparison_pdf` (a plain PDF
admitted for comparison, ADR-0025 decision 11). A comparison version is bound under the manifest role
`comparison.source_pdf`, never `source.document`, holds none of the portal bundle's counts and starts no section analysis
(`runs.commands.refuse_comparison_only_version`). `DocumentRepository.publish_version` makes it the document's current
version **only while the document holds no portal version**; every reader of `current_version_uid` is therefore safe
without knowing the kind (`tests/integration/ingest/comparison_pdf/test_confirmation_rules.py` judges each reader).
`DocumentVersionRecord.source` is the bytes accessor (either role); `entry(MANIFEST_ROLE_SOURCE_DOCUMENT)` stays strict.
