# W59-DECISION-CARRYOVER-01 — expert-confirmed decision carryover

Status: **phase A complete** on `agent/w59-decision-carryover-01` (base `a50dafd4` =
`origin/dev` `1049367e` + the task file). Phase B (operation, reseal, web action) waits for
the integrator's contract-slot handover.

## Result (phase A)

An expert who sees an `unchanged` finding-match proposal on «Сравнение версий», whose source
finding carries a decision, can confirm «Перенести решение»: the target finding receives a new
decision event. Nothing is carried without that confirmation, nothing is written to the source
finding, its decisions or the raw comparison evidence, and no AI layer produces or edits the
decision.

- **Command** `comparison.public.DecisionCarryoverService.carry_over(session, CarryoverRequest,
  actor_uid, actor_label, actor_roles, idempotency_key)`. The request names project, document,
  source and target version, `mode` (`version` | `stage`), optional `source_run_id` /
  `target_run_id`, the source and target finding, and **the source decision the expert was
  shown** (`source_decision_id`). Order: request shape (`validation_failed`), expert role
  (`permission_denied`, `role:expert`; `admin` alone refused, `R-60`), the path (`not_found`,
  `get_version_in`), then the comparison **recomputed in the confirming transaction**
  (`VersionComparisonService.current_finding_proposals` — the same comparison without its diff
  page), which must still propose exactly this pair as `unchanged`, then the ledger rules
  under row locks.
- **Ledger** `decisions.public.carry_over_decision`. Locks both finding rows `FOR UPDATE`
  (ordered by UID; an ordinary `appendDecision` on either finding takes a key-share lock through
  the event's foreign key, so the two serialize), then: the source's current verdict must be
  `accepted`/`rejected` and its verdict-bearing event must be the named decision; an exact
  repeat (the target already carries the event this carryover renders) answers that event with
  `replayed`, by any key and any expert (first confirmer stands); any other event on the target
  refuses; a severity on the source `accept` is carried with it or refused when the target's
  observation cannot hold one (never dropped); then one `accept`/`reject` event is appended via
  `record_decision` under an idempotency key claimed as command type `carry_over_decision`.
- **Provenance without a migration.** The carried event's `comment` is a fixed rendering
  (`carryover_comment`) of the carried-from finding, the carried decision event, both versions
  and the mode, with the source ordinal as display («Решение перенесено из версии N (сравнение
  версий) после подтверждения экспертом. Исходное решение dec_… по замечанию fnd_… версии
  ver_…; целевая версия ver_….»). Identity is the UIDs; the ordinal is never read back. The
  confirming expert and time are the event's `author_user_uid`/`author_label`/`recorded_at`.
  The command record's outcome repeats the provenance as JSON. The exact-repeat check compares
  the rendering whole; nothing parses it.
- **Query** `comparison.public.carryover_candidates(session, comparison)`: the `unchanged` pairs
  of a computed `VersionComparison` whose source verdict is `accepted`/`rejected` and whose
  target has no decision event, each with the source decision (id, verdict, severity, comment,
  author label, time), in proposal order. Two batched reads (`decisions.public.current_verdicts`,
  `decision_events_by_id`), at most 200 pairs.

**Refusals** (`conflict` with `aggregate_type: ExpertDecision` and one `conflict_reason`):
`carryover_pair_not_proposed` (the recomputed comparison is refused, its findings are over the
limit, or it does not propose exactly this pair as `unchanged` — crossed, swapped, foreign,
unknown, same-finding pairs, `probably_fixed`/`new`/`undetermined`, and a pair a newer published
run no longer proposes), `carryover_source_decision_not_current` (the named decision is not the
source's current accept/reject — superseded, re-given, of another finding, or none),
`carryover_target_already_decided` (the target has any event, including a comment or an earlier
carryover of another decision), `carryover_severity_not_carryable`. One key reused for another
carryover is `idempotency_key_reuse`.

**`probably_fixed`.** The proposal has no target finding, so there is nothing to carry a verdict
to; the command refuses it (`carryover_pair_not_proposed`) and nothing marks a source resolved.
The ledger has no "resolved" verdict; recording one would be an expert's own decision, outside
carryover.

**Prepared modules reused.** `decision_carryover.require_carryover_expert` (extracted from
`confirm_decision_carryover`, behaviour unchanged) is the served role rule, and
`MAX_CARRYOVER_MATCHES` bounds the candidates. The pure offer/plan functions stay unserved: they
bind a persisted `ComparisonId` and matching revision that the served comparison deliberately
does not fabricate. The served path re-states their rules on authoritative state instead
(decided accept/reject source only, target with no events, exact one-to-one pair, recheck at
confirmation).

## Changed files (phase A)

- `src/auditmanager/comparison/carryover.py` (new) — command, query, request/outcome types;
- `src/auditmanager/comparison/service.py` — `current_finding_proposals` and the shared
  `_prepare`/`_assemble` split; `compare` answers byte-for-byte as before;
- `src/auditmanager/comparison/decision_carryover.py` — `require_carryover_expert` extracted;
- `src/auditmanager/comparison/public.py` — exports;
- `src/auditmanager/decisions/carryover.py` (new) — the ledger half and provenance rendering;
- `src/auditmanager/decisions/public.py` (new) — the context's ALR-05 surface;
- `src/auditmanager/decisions/ledger.py` — `decision_events_by_id` (batch read);
- `src/auditmanager/decisions/projection.py` — `current_verdicts` (batch read), shared row
  mapper;
- `tests/integration/comparison/test_decision_carryover_db.py` (new, 27 tests);
- `tests/integration/decisions/test_carryover_ledger.py` (new, 10 tests);
- `tests/unit/comparison/test_version_comparison_service.py` — 3 tests for the recomputation;
- `tests/integration/decisions/test_rules_are_load_bearing.py` — pre-existing red on the base
  (two tests did not know `CurrentVerdict.decided_severity`, added by W56 findings v2, which
  `comparable()` already compares): the field is added to the compared set and the probe.

No migration, contract, router, composition root, web file or dependency changed.

## Checks (phase A)

Lane `auditmanager-w59-carryover` (PostgreSQL 57560, MinIO 61160/61161, database
`auditmanager_w59_carryover`), `make up` + `make migrate` to `0024_version_classification`;
`.venv` with the w55b candidate library. Command:
`.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`.

- Base before any change: `tests/integration/comparison tests/unit/comparison
  tests/integration/decisions` — 264 passed, 2 failed (the drift above).
- After: same paths plus `tests/contract/architecture` — **309 passed**.
- Mutation probes (scratch script, each applied alone, then restored): removing the expert
  check, the pair proof, the target-has-events guard, the source-currency check, the exact-repeat
  replay, the severity guard, carrying the severity, the candidates' target-event filter,
  admitting `probably_fixed`/`new` as pairs, and the finding-version check each turns at least
  one new test red (10/10). The source-currency probe first survived (a second check caught the
  cases); a re-given verdict case was added and now kills it.
- `git diff --check` clean.
- Not run (R-135): full gate, live journey, whole contract battery, any provider call.

## Risks and limitations

- The `FOR UPDATE` serialization against a concurrent ordinary `appendDecision` is argued from
  PostgreSQL's key-share foreign-key lock, not exercised by a two-connection test (the suites
  isolate by rollback, and append-only tables cannot be cleaned up after a committed race).
- The confirmation recomputes the whole comparison (two text layers read and checked, pairing)
  inside the write transaction: seconds for two dense 500-page versions, as for the read.
- The provenance is a Russian sentence with UIDs in `comment`; it is visible wherever the latest
  comment is shown (knowledge base, CSV). A later structured-provenance column would be a
  migration; none is needed for the stated rules.
- Pre-existing elsewhere (not touched): `test_every_port_implementation_is_whole::
  test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`.

## Proposed operation (phase B, pending the contract slot)

`POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/carryovers`,
`operationId: carryOverDecision`, `role:expert`, required `Idempotency-Key`; body (closed)
`{target_version_uid, mode, source_finding_uid, target_finding_uid, source_decision_id,
source_run_id?, target_run_id?}`; `201` (appended) / `200` (exact repeat) with the carried
`DecisionEvent`, `current_verdict` and the provenance; `401, 403, 404, 409, 422, 500, 503`; four
new `conflict_reason` values in `error-codes.json`. Candidates as an added field of
`VersionComparison.findings` (`carryover_candidates`), computed in the same read by the adapter,
rather than a new GET.
