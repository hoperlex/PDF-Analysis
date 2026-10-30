# CMP-MANUAL-DATA-1030

## Outcome
One downloadable, synthetic comparison-input pack with a short operator guide; no application behavior change.

## Depends on
- HOTFIX-PRESENTATION-DEMO-1030 (complete)

## Frozen inputs
- domain/comparison contract: ADR-0025, unchanged
- API contract: 1.14.0, unchanged
- migration head: `0043_stage_ai_generations`, unchanged
- base commit: `85ab8c1edc7313bec379949ba9e6ffbeba5325fa`
- source: the four synthetic comparison ZIPs from the completed `HOTFIX-PRESENTATION-DEMO-1030` fixture set

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the completed fixture task provides four PDF-only comparison ZIPs with recorded SHA256 and CRC checks; source hashes were checked again before packaging.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev (owner chose dev only)
- origin_main_authority: none

## Allowed paths
- `fixtures/manual-comparison-1030/**`
- `docs/program/tasks/CMP-MANUAL-DATA-1030.md`

## Forbidden hotspots
- Runtime, UI, `contracts/**`, migrations, dependencies/lockfiles, composition root, global styles, `origin/main`.

## Non-goals
- Live model/browser run, result-quality claim, deployment, customer documents.

## Deliverables
- `comparison-manual-pack.zip` containing the four already validated PDF-only comparison ZIPs and the concise `README.md`.
- The same `README.md` outside the archive for quick preview.

## Required tests
- `sha256sum -c SHA256SUMS` from `fixtures/presentation-hotfix`: all six OK.
- Python archive inspection: four inner ZIPs, PDF-only contents, outer/inner CRC, README byte identity, path safety.
- `git diff --check`.

## Integration contract
- Extract the outer pack; upload its inner ZIPs unchanged to the corresponding comparison screens. No new API or config dependency.

## Rollback / feature flag
- Delete the pack and guide; no feature flag or persisted behavior change.

## Failure/idempotency/security cases
- The outer ZIP is only a carrier; users extract it and upload the unchanged inner ZIPs. All documents are synthetic. Build uses fixed ZIP metadata.

## Handoff
- changed files: this task file and `fixtures/manual-comparison-1030/{README.md,comparison-manual-pack.zip}`.
- commands/results: source hashes and pack inventory/CRC pass; no full gate needed for data-only task.
- known limits: no browser import or model execution claimed.
- integration notes: publish to dev only; main is excluded.
