# CMP-STAGE-PAIR-01 — working record

Task: [`CMP-STAGE-PAIR-01`](tasks/CMP-STAGE-PAIR-01.md). This branch is based on the committed C3 seal `dc53c98b` and a local merge of the finished ZIP policy fix at `57611910`. It has no remote publication authority. The lane is **in progress**; stage upload and the screen are not implemented yet.

## Implemented in this candidate

- The seven stage-pair operations are served when `AUDITMANAGER_COMPARISON_MODULES=versions,stages`. The module-off answer remains typed `503 dependency_unavailable`.
- Pair suggestions read the newest version's effective expert classification. They emit a nonbinding П→Р hint only for a unique section and normalized designation or title on both sides. A confirmed designation on both sides scores `1.0`; a display-title fallback scores `0.75` and says so in its reason. Names never become pair identities.
- A keyed expert command confirms one П document against one Р document or a Р assembly in the same project and section. It serializes active binding decisions per project, refuses a second active pair for the П document, and replays the original command ID.
- Р assemblies have append-only member rows. Their creation and revision use distinct derived command records per member; a revision checks its `base_member_no` and leaves removed members as history. The pair references an assembly identity rather than a name or a document list.
- The keyed completeness command writes the current choice and an append-only `audit_event` with the prior choice, new choice, actor and command identity in the same transaction.
- The ZIP intake helper bounds a nonseekable raw stream before extraction: declared byte cap (2 GiB), measured size and SHA-256, one active admission, and free disk for both raw spool and maximum extracted set plus 512 MiB reserve. It passes the production set policy and comparison PDF envelope; an invalid member refuses the entire set and both temporary layers are cleaned.

## Checks so far

- Focused stage unit, PostgreSQL and HTTP tests: **19 passed** after the designation-source refinement (`/tmp/cmp-stage-pair-focused-1.log`). A separate cross-project refusal test passed (`/tmp/cmp-stage-pair-foreign-db.log`).
- C3 composition module sweep: **67 passed** (`/tmp/cmp-stage-pair-composition-stubs-2.log`): seven pair operations reach the DB or typed 404 with stages enabled; the other C3 ports remain stubs; all stage operations refuse while modules are off.
- The direct PostgreSQL tests cover keyed pair replay and same-key payload conflict, pair uniqueness, assembly creation and revision with separate member commands, stale revision refusal, completeness audit and cross-project refusal. The HTTP test covers module gating, suggestion, confirmation/replay, catalog and completeness.

## Remaining before handoff

The ten stage-upload operations still have sealed adapters. The ZIP intake helper is not their caller; no ZIP set has been admitted by the served API and D-262 remains open. The durable upload service must persist parts and candidate state, reserve admission under a database lock, measure disk on the reader's temp filesystem, run the bounded stream helper before storing each validated PDF, and reconcile interrupted multipart and blob effects. The tab-1 catalog/workbench, upload dialog and focused web checks also remain. No contract, migration or generated-client bytes have changed in this branch.
