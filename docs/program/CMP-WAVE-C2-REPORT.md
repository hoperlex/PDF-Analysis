# CMP wave C2 — version comparison AI and reports: integration report

Task: `CMP-WAVE-C2-INT`. Branch: `integration/compare-modules`. Publication target: `origin/dev` only. Base remote development commit: `0277e4ef507950e2e6bafe6aa5c77928acd94013`.

## Delivered

- Frozen API `1.11.0`: 176 paths, 198 operations, 517 schemas. Migration head `0040_comparison_ai_reports` adds the C2 AI, specification, report and launch-queue tables. Product `VERSION` remains `0.9.0`.
- The shared AI-job core records consented estimates, route/model pins, spend and progress, pause/resume/cancel and recorded answers. Four methods now run through worker-routed «Исполнители»: doubtful sheet-pair checks, per-sheet descriptions, whole-specification comparison and report generation. Their answers remain provisional; deterministic comparison evidence and expert decisions are separate.
- A deterministic ГОСТ 21.110 specification reader, a Markdown summary and client/analytic PDF reports serve the C2 screens. The per-project launch queue stores order, state and counts durably. The C2 UI adds steps 4/6/7, AI hints and descriptions, consent dialogs, the report window, side panel and queue block.
- The integration repair bound live connection revisions in the worker, published checked pull crops before task exposure, preserved AI-entry series identity through consent, exposed estimates for paused work left, and corrected the font census and prose guards.

| Part | First-parent merge or commit | Record |
| --- | --- | --- |
| C2 seal | `bc59071c` | `CMP-SEAL-C2.md` |
| AI job core | `0f6a008d` | `CMP-AI-JOBS-01.md` |
| C2 UI | `0f1df032` | `CMP-VC-UI-02.md` |
| Specification | `2825f88c` | `CMP-VC-SPEC-01.md` |
| AI pair checks | `bbbcdc74` | `CMP-VC-AIPAIR-01.md` |
| AI sheet descriptions | `2e738b52` | `CMP-VC-AISHEET-01.md` |
| Reports | `4c8b3e89` | `CMP-VC-REPORT-01.md` |
| Launch queue | `8fcdda42` | `CMP-VC-QUEUE-01.md` |
| Integration repair | `efeefe1f` | `CMP-C2-FIX-01.md` |
| Task-record repair | `80dbb71f` | `CMP-C2-GOV-01.md` |
| Frontend gate repair | `06c312a3` | `CMP-C2-GATE-FE-01.md` |
| W13 characterization repair | `624e13a9` | `CMP-C2-GATE-W13-01.md` |
| Composition guard runtime repair | `acdbdedd` (merge) | `CMP-C2-GATE-BE-01.md` |

## Verification

The first complete gate on `adcac54f` passed frontend lint, typecheck and all 3,651 Vitest tests, then found a task-record format failure in the contract suite (1,309 passed, 1 failed). `CMP-C2-GOV-01` corrected the two task records; its focused governance test passed 16/16. The next gate on `ac5ee5cc` stopped in the frontend after 70 green guard assertions because one worker's `onTaskUpdate` RPC exceeded 60 seconds. `CMP-C2-GATE-FE-01` kept the same census and checks, eliminated a duplicate 70-second render and split the two palette measurements into separate tests with worker yields.

The subsequent gate on the clean code candidate `06c312a3` passed frontend lint, typecheck and **3,653 Vitest tests**, the contract suite (**1,310 passed**), foundation (**35 passed**) and the changed-context integration battery (**6,592 passed / 13 skipped / 244 subtests passed**). Its canonical remainder exposed twenty stale W13 historical response expectations (sixteen error-envelope version strings and four portal-version upload-kind fields). That already-red remainder was stopped for diagnosis; **this was not a `GATE OK`**. `CMP-C2-GATE-W13-01` kept every historical record byte and added a digest-pinned in-memory projection; its focused suite passed 73/73, including wrong-field and changed-record controls. The original composition port guard had reread every Python file for each port and held the first battery near 61% for roughly 43 observed minutes; `CMP-C2-GATE-BE-01` cached that static census per process, passed 44/44 focused cases in 17.16 s, and failed on a removed method in a disposable mutation copy.

The publication candidate containing this report is accepted only after a new full `make gate` returns literal `GATE OK` on its exact clean SHA. Its commit-specific run and remote-ref verification are recorded out of tree under `.git/gate-runs/` and `/tmp/cmp-c2-gate-publication.log`; the final publication SHA is the verified `origin/dev` tip, since a commit cannot embed its own hash in this report.

Before this documentation commit, the focused contract prose, surface-count and task-governance checks passed **93/93**, and `git diff --check` was clean.

The first report-bearing candidate `56de5bef` passed the frontend suite again (3,653/3,653) but its contract suite found one document guard: the new current-state header raised `CURRENT_STATE.md` from the maximum 120 lines to 121 (1 failed / 1,309 passed). `CMP-WAVE-C2-INT` owns that file; a wrapped W54 sentence was joined without changing its words, restoring 120 lines. The focused process-acceleration suite then passed **12/12**. This candidate was red and was not published; the next clean documentation commit needs its own complete gate.

Focused final-code evidence before the complete gate: comparison unit/contract 106 passed, pull unit 76 passed, queue integration 5 passed, AI job/pair/sheet integration 196 passed, spend/work integration 147 passed, real-DB pull context 1 passed (`CMP-C2-FIX-01.md`). The gate is the final broad-suite check.

## Limits and operation

- The comparison module flag defaults to `none`. `AUDITMANAGER_COMPARISON_MODULES=none` stops the worker from claiming C2 work; enabling it is an operator choice. No live model or runner call and no browser journey was claimed in C2.
- A launch entry paused as `needs_consent` has no API to renew that entry's consent; the UI can start the step directly. A later seal must add the entry command if desired.
- Pull crop blobs are durable before task exposure but lack a long-lived row after task expiry; the blob-reference audit may show them as unreferenced. Retention or cleanup is future work.
- The overview derives steps 4, 6 and 7 through per-row reads; specification reason/profile fields and other contract-shaped refinements wait for a later seal.
- `origin/main` is outside this task. A main publication requires the owner's separate direct instruction and the full auto-deploy policy.

## Ownership and publication

The task `CMP-WAVE-C2-INT` owns only this report, its task record, and the current-state header; the application edits have their separate lane and repair tasks above. No contract, migration, root dependency/lockfile, composition root, global style or infrastructure file changed in the integration documentation step. A fast-forward of the exact green gate commit to `origin/dev` is the only publication authorized here. The C3 ZIP-set security review runs in a separate branch and is not part of the C2 gate candidate.
