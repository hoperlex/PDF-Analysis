# BLOCK8-INT-1030 — complete specification profile catalogue

task_id: BLOCK8-INT-1030

## Outcome

Version comparison accepts the page-count representation admitted by owner migration0044, and whole specifications traverse every metadata page instead of silently using a500-profile prefix. Incomplete/unknown source coverage cannot produce a supposedly complete specification.

## Depends on

- BLOCK7-INT-1030
- SECTION-STATS-UNCAPPED-1030

## Frozen inputs

- Base dev `2b987c842c4eb4fc57252b144578f52afc41299f`.
- API1.14.0, numeric bounds extended by owner SECTION-STATS-UNCAPPED-1030; migration0044_section_stats_uncapped.
- Existing PageProfileReader keyset after_page/more metadata seam, stored immutable profile IDs and source page_count.
- Owner continuous source-only/dev instruction; root sole active writer after delegated usage limits. Owner deploys.

## Allowed paths

- `src/auditmanager/comparison/version_reader.py`
- `src/auditmanager/comparison/profile/reader.py`
- `src/auditmanager/comparison/specification/reader.py`
- `src/auditmanager/comparison/specification/transition.py`
- `docs/program/**`

## Forbidden hotspots

Contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, prompts/call budgets/paid journal, other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No OCR or guessed page classification, no loading all archives to enumerate metadata, no finding/decision changes, no historical result rewrite, no hidden paid expansion. No claim that one complete metadata scan establishes semantic specification completeness.

## Deliverables

Page-catalogue metadata reader traverses keyset pages with strict identity/order/progress guards; source page_count detects missing/unfinished profiles without materialising huge missing-page ranges. SpecificationReader uses the full catalogue, marks unreadable confirmed SO/ambiguous scans as incomplete, and retains actual page refs. prepare_side and deterministic whole-spec comparison refuse incomplete source as existing SPEC_NOT_READ/unavailable behavior rather than removals. Existing content/source plan pins require fresh estimates when real source changes. VersionPairReader residual500-page refusal aligns to actual signed-32-bit storage representation, no new application quota.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Only existing internal read seams/VersionStream fields; frozen wire schemas and migration head unchanged. Root owns exact paths and ordinary dev publication/read-back, preserving incoming owner commits. No app DB/model execution in this coding session.

## Rollback / feature flag

Read completeness correction: revert exact files without mutating prior saved evidence/decisions. Source-key/consent guards remain; reverting cannot legitimise old incomplete prefixes as full data.

## Handoff

Exact changed files, no-check status, unchanged contracts, conservative source-readiness limits, publication receipt and D-290 acceptance debt.
