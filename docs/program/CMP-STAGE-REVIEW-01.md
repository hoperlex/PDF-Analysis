# CMP-STAGE-REVIEW-01 — stage review backend

Completed 2026-10-30 in `agent/cmp-stage-review-01`. Root remains the only integrator and remote-ref writer. The owner deferred full gates and heavy windows until tomorrow; this report records focused functional evidence only.

## Result

`StageReviewService` materializes step-7 cards from the run's effective map revision (original revision otherwise). Publication checks the current work lease, project, `stages` module, closed `stage_chain` kind, payload run identity, full/running run and current map/version pins. Map edits and publication serialize on the existing pair advisory lock. Cards, per-side evidence anchors, exact carried verdicts and the publication receipt commit together. Replays compare a content digest, including the empty result.

Validated stage-AI classification rows provide class/category/title/system labels. Every uncovered deterministic text difference becomes conservative `REVIEW / uncertain / unknown`; a SAME/MOVED judgment cannot remove raw differences. Unchecked/unreliable graphics remain status records. A reliable nonempty graphical result may become a REVIEW card; no graphical interpretation or model call is introduced. Absence remains unproved in these raw-derived cards. Text is the stored normalised evidence, not invented original typography.

Expert bulk verdicts use the existing `apply_stage_card_verdicts` command receipt, stable card lock ordering and expected revisions. Duplicate cards, foreign cards, stale or incomplete runs, rejected decisions without a reason and SERVICE_STRUCTURE votes refuse the whole transaction. Replaying a successful key returns the original verdict IDs, even after newer expert acts exist. History is append-only.

Card identity is the class plus sorted atomic source IDs. The evidence digest independently binds source kind, per-side page profile, fragment content key and box anchors; it excludes model class and revision-local difference identity. Equal evidence with unanimous previous decisions carries as a new verdict row, retaining actor/command and `carried_from_verdict_id`. Disagreement refuses automatic carryover. Partial source overlap and changed evidence at the same deterministic document/page/side/box location produce partial/stale labels only; a location match never authorizes acceptance.

The accepted journal contains PROJECT_CHANGE/REVIEW cards whose latest verdict is accepted. Its groups are exactly `{key,label,rows:StageChangeCard[]}`, by designation, section or closed system. Designations prefer confirmed intake designations, then the document title; section comes from the version classification. Counts expose total, review, exact `project_changes` class count, conflicting previous exact decisions and `high_importance=0` because importance has no evidence. Synthesis remains the separate sealed stage-AI read view.

Synchronous local writers return XLSX/PDF/HTML bytes, without a generic exports writer, resource or DB/external dual write. XLSX uses literal inline strings, deterministic ZIP metadata and XML control-character encoding; HTML escapes source data; PDF embeds the repository's DejaVu font and preserves extractable Cyrillic. All formats include accepted/SAME-MOVED/service counts, source staleness and the limitations of absence claims. No formula or script executes from source text.

## Integration interface

Import `StageReviewService` from `auditmanager.comparison.stage_review` and construct with `sessions` only (no constructor I/O).

- `advance(item, run_id) -> dict[str,int]`
- `page(run_id, after=None, limit=100) -> (tuple[dict], next_card_key, counts)`
- `get(card_id) -> dict`
- `apply_verdicts(run_id, updates, *, user_uid, actor_roles, idempotency_key) -> tuple[dict]`
- `verdicts(card_id, after_revision=None, limit=100) -> (tuple[dict], next_revision)`
- `journal(run_id, grouping='designation') -> dict`
- `export(run_id, format, grouping='designation') -> bytes`, format `xlsx|pdf|html`

Plain dictionaries match the frozen API DTOs. Root owns transport mapping, ACL/module gates, composition and worker integration. No API, migration, generated client or shared wiring change belongs to this task. Root merged its serial 0042 progress/read provider into this worktree before this lane's commit; these inherited changes are not authored here.

## Focused checks

- `.venv/bin/python -m pytest -q --tb=short tests/unit/comparison/stage_review --basetemp=/tmp/cmp-stage-review-unit3`: **9 passed**.
- `.venv/bin/python -m pytest -q --tb=short tests/integration/comparison/stage_review --basetemp=/tmp/cmp-stage-review-db3`: **7 passed**, real local migration 0042 on the root-assigned isolated PostgreSQL `58040`.
- Export tests parse XLSX XML/ZIP and a real PDF reader, check formula/script quoting, Cyrillic extraction and deterministic bytes.
- DB tests exercise current/lost/foreign leases, full-run raw fallback, source scope, SAME retention, unvoted service cards, keyed replay, optimistic revision refusal, atomic bulk rollback, accepted groups, three output formats, empty replay, exact carryover lineage and changed-source stale refusal.
- `git diff --check`: clean.

## Limits

Synchronous budgets refuse explicitly above 20,000 raw differences, 10,000 prior verdict-bearing cards or 10,000 accepted journal cards. Export refuses above 5,000 rows or 8,000,000 source characters. A combined card above either frozen 20,000-character side budget refuses rather than silently truncating evidence. Recognised text remains provisional upstream; these cards never claim proven absence. There is no importance assessment. High-level synthesis is consumed through the separate sealed endpoint. No full gate, build, whole battery, browser journey, live model call, deployment or remote ref update was performed.

## Files and ownership

Only the task/report, `comparison/stage_review/{__init__,cards,service,writers}.py`, `tests/unit/comparison/stage_review/test_cards_and_writers.py` and `tests/integration/comparison/stage_review/test_service.py` are authored in this lane. Ignored `.env` and `.venv` select the assigned local foundation and existing environment. Forbidden hotspots are untouched by this commit. Root integrates the local provider and performs tomorrow's broader checks.
