"""Deterministic portal-bundle fixtures for the synthetic AR corpus (W55B-FIXTURES-01).

A portal bundle is the one ZIP an upload now carries: a PDF, the portal's block list
(`_blocks.json`), the recognised text (`_results.md`) and, optionally, the portal's HTML
rendering and a stamp audit. This package builds such bundles from the synthetic PDFs in
`fixtures/synthetic/ar/`, builds the archives that break each bundle rule, and carries a
validator that says which rule a given archive breaks.

Pure standard library, like `ar_corpus/`: the repository lock carries no ZIP or PDF
tooling that could write a malformed archive on purpose, and a fixture that depends on a
library's idea of what is allowed could not test the rule.

Nothing here reads the portal's real exports. The formats were measured on one real
export and are mirrored with invented content; the real set stays outside the repository.
"""

__all__ = [
    "archive_negatives",
    "blocklist",
    "bundle",
    "generated",
    "pdffacts",
    "portal_format",
    "positives",
    "results",
    "schemacheck",
    "stampaudit",
    "validate",
    "zipscan",
    "zipwrite",
]
