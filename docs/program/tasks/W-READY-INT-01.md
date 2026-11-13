# Task W-READY-INT-01 — integrate and release the completed task branches

## Outcome
Publish the completed PREC-WEB, PAUSE-WEB-01, CMP-JOB-HINT-01, CMP-NOTE-265 and GATE-OPT integration as one compatible product candidate; observe successful exact-SHA deployment.

Owner: root, sole integration and release writer. Owner instruction 2026-11-13: «Готовые задачи интегрируй и пуш в мейн с минимальными проверками». This explicitly selects focused checks instead of a complete gate and authorizes origin/main publication for the completed candidate. The later cleanup agent owns only completed local resource cleanup, never product or Git publication.

## Depends on
- PREC-PASS and F8-WEB — implemented on the existing 0.27.0 base; F8 was adopted through ONE-LIST-COMPLETE-01.
- CRIT-SEAL-50 and EMBED-01 — existing vector control implementation.
- CMP-SPEND-01 and CMP-DEBT-261 — existing claim protection and comparison-version presentation.
- GATE-OPT-01 and GATE-SUITE-AUDIT-01 — locally complete source branches, accepted here only after current-tree checks.

## Frozen inputs
- base commit: 1190787d4e60203ec75b1a2ecdd6116fa6a248b9 (origin/dev); origin/main 275bde8643e1e89f5f9741be2e57b7367cde44ae.
- API/domain/analysis contract: 1.55.0; migration head: 0068_reviewable_findings; unchanged.
- source tips: PREC-WEB d2363e849, PAUSE-WEB-01 16132f05b, CMP-JOB-HINT-01 1f4e949ea, CMP-NOTE-265 b5faf2a23, GATE-OPT-INT-01 15ba0cb09.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: ready source work remained outside main; read-only revision is .local/reports/revision-2026-11-13/report.md.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: the direct owner release instruction quoted above; root is appointed release integrator.

## Allowed paths
- the existing source tasks' web/src and web/tests paths; web/tests/unit/widgets/pause-status.test.ts and tests/e2e/pc01/journey/manifest.json for their consumers
- src/auditmanager/jobs/repository.py and tests/integration/comparison/spend/{test_connection_single_user.py,conftest.py} for the current capacity-aware dispatch hint
- Makefile, tests/contract/test_gate_tiers.py, tests/integration/composition/test_stand_copy_refusals.py and the imported GATE-OPT task/report files (root owns this integration slot)
- docs/program/tasks/W-READY-INT-01.md; imported CMP task/report files; docs/program/CURRENT_STATE.md, DEBT_REGISTER.md and RELEASES.md
- VERSION, release-notes/0.28.0.json and the two release version inventories (root owns this release slot)
- local evidence/handoff and integration/main/dev Git refs

## Forbidden hotspots
- contracts/**, db/migrations/**, root dependency and lock files
- composition roots, global styles, deployment workflows and verification policy
- production settings/data, corpus, paid model calls, historical run promotion

## Non-goals
Implement unfinished PAT/QUAL/XDOC, memory comments UI, synthetic sections or historical production cleanup tools. No feature activation, dependency update or complete gate. The user requested discussion of unfinished work after this release.

## Deliverables
Compatible source integrations, one product release note, targeted current-tree evidence, exact publication and workflow verification receipt.

## Required tests
- command: focused Vitest for precedents/pause/comparison pickers and affected review consumers; package TypeScript and touched ESLint; existing static component preview tools for changed interactions
- command: isolated PostgreSQL comparison/connection capacity/group dispatch checks; Makefile tier and affected readiness-guard checks; release-note/client conformance; git diff --check
- expected: pass. No broad app battery or complete gate. Any relevant failure is repaired before publication.

## Integration contract
The prior one-list/unverified-evidence readers remain intact. Human decisions remain authoritative. Vector controls use existing authorization/keyed commands; flags remain unchanged. Dispatch selection counts each active comparison call as one capacity unit alongside existing Runs and keeps the locked claim authoritative. Gate timing preserves failures and the complete gate marker; local tiers use their own markers.

## Failure/idempotency/security cases
Viewer receives no expert controls; unread vector state cannot toggle; retries keep their idempotency key. Terminal/lost comparison calls free hint capacity and distinct simultaneous calls consume separate units. Missing precedents remain optional reference material, never expert verdicts.

## Rollback / feature flag
Revert this integration forward using the release process. No database or contract downgrade. Existing switches remain operator-owned and unchanged; no data destruction.

## Handoff
Candidate complete; publication pending. Product 0.28.0. Imported 17 ready commits, with conflict resolution preserving the current source-uncertainty reader and PDF Run admission. The dispatch hint was adapted to current capacity/group/pool semantics and has three new real-PostgreSQL mixed-unit cases.

Current-tree evidence under `.local/evidence/ready-tasks-1113/`:
- web-focused.log: 157 passed in 12 files; pause-final.log: 20 passed after correcting two old fixture contract literals to 1.55.0 (overlaps the first group).
- db-focused.log: 95 passed in an isolated fresh database at 0068; includes hint states, distinct calls plus Runs, current capacity, groups, locking and release loading.
- python-focused-final.log: 42 passed for Make tiers, selector command and release form.
- consumers-final.log: 168 passed, 166 deselected; journey declarations, current release form and the changed database-readiness refusal case. Counts overlap; do not add them as a single suite count.
- typecheck-final.log: package TypeScript exit 0; eslint.log: 39 touched TypeScript files, exit 0; client-final.log: generated client verification OK.
- prec/pause render and browser evidence: 20 static real-component views (light/dark, 1280/390), no horizontal overflow; menus/reference card opened. These are local fixture previews, not a live production journey.
- scope-check.json and manifest-equivalence.json: protected paths unchanged; journey formatting minimized without changing the tested JSON; git diff --check passed.

The first TypeScript attempt hit an intentionally bounded 1536 MiB heap; after other checks ended and host availability rose, 4096 MiB allowed the real compile to finish. It then found only two stale test literals, which were corrected and rechecked. An initial release-form run rejected an unquoted format name; the note was rewritten in user language. The release loader was initially invoked without a database and subsequently passed in the isolated database. No failed relevant check remains.

The full gate, complete batteries, paid analysis, encoder, operator setting activation and historical data changes were not run. The owner explicitly selected minimal checks. No extra full gate is needed for an unchanged API/migration/dependency/deployment surface; the affected UI, queue semantics and Make surface have focused evidence. Historical GATE-OPT reports remain dated evidence and are not current release acceptance.

Root publishes the exact clean candidate SHA after an immediate remote-main check, then observes deploy-auto and its actual same-tree/DEPLOY OK log. The SHA-bound release plan, remote readback and verification receipts are local evidence; no runtime edit may be appended without affected rechecks.
