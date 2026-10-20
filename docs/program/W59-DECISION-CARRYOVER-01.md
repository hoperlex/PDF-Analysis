# W59-DECISION-CARRYOVER-01 — expert-confirmed decision carryover

Status: **complete** on `agent/w59-decision-carryover-01`. Phase A (`f345b815`, no
migration) was accepted; phase B (operation, reseal, web action) was done after the
integrator handed over the shared contract slot, and the branch merges
`integration/night-1020` up to `a820849a` (W59-ANALYSIS-SETTINGS-01, W59-VERSION-UPLOAD-01)
with every generated artifact re-derived on the merged tree. Final surface: **54 paths /
61 operations / 158 schemas**, head `0024_version_classification` (unchanged), 25 error codes.

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

## Result (phase B)

**Operation.** `carryOverDecision` — `POST /projects/{project_uid}/documents/{document_uid}/
versions/{version_uid}/comparison/carryovers`, tag `decisions`, `role:expert` (admin alone is
`403`, `required_capability: role:expert`), required `Idempotency-Key`, closed body
`CarryOverDecisionRequest {target_version_uid, mode, source_finding_uid, target_finding_uid,
source_decision_id, source_run_id?, target_run_id?}`; `201 CarryOverDecisionResponse {event:
DecisionEvent, current_verdict, replayed, source_finding_uid, source_decision_id,
source_version_uid, source_version_ordinal, target_version_uid, mode}`; `401, 403, 404, 409
(StateConflict), 422, 500, 503`. **One deviation from the proposal:** an exact repeat answers
`201` with `replayed: true` rather than `200`, as `appendDecision` answers a replay — one success
status keeps the generated client's result type single. `DecisionEvent.severity` is omitted, not
null, when absent (`model_dump(exclude_unset=True)`, as `appendDecision` renders it).

**Read.** `FindingComparison` gains the required `carryover_candidates` (≤ 200;
`CarryoverCandidate {proposal_sha256, source_finding_uid, target_finding_uid, source_decision:
CarryoverSourceDecision {decision_id, verdict (accepted|rejected), severity, comment,
author_label, recorded_at}}`), computed by `ComparisonAdapter.compare_versions` in the same read
session as the comparison; empty when the findings are unavailable.

**Wiring.** `ComparisonPort.carry_over_decision`; `ComparisonAdapter.carry_over_decision` opens
one write transaction, reads the account's roles in it (`AccountRepository.roles_of`) and calls
`DecisionCarryoverService.carry_over`; the router passes the verified subject's `user_uid` and
`display_label` (never the body). `OPERATION_ROLES["carryOverDecision"] = expert`. Four
`conflict_reason` values are registered in `contracts/domain/v1/error-codes.json`
(`conflict.notes`); no error code added.

**Web.** On «Сравнение версий» the finding-proposal table gains «Решение эксперта». A row the
server lists as a candidate shows «В более ранней версии: принято/отклонено» and, for an expert,
«Перенести решение»; the confirmation shows the older decision (verdict, severity, author, time,
comment) and the newer finding (category, text, sheets), and only «Подтвердить перенос» sends the
command (one key per intent, reused on retry). Success shows «Решение перенесено…» (or «уже было
перенесено ранее» for a replay) and invalidates every comparison answer
(`queryKeys.versions.comparisons()`, new) and the newer finding's reads
(`decisionCacheKeys(target, target run)`: ledger, detail, the run's findings, knowledge base,
dashboard); a refusal is read in Russian per `conflict_reason` and re-reads the comparison. A
non-expert sees «Решение более ранней версии может перенести эксперт.» and no button. New:
`entities/document-version/model/carryover.ts`, `features/carry-over-decision/**`;
`entities/finding` now exports `SEVERITY_LABELS`. No new CSS module (global `am-` classes).

**Reseal artifacts** (re-derived after each merge, never hand-merged): contract (this lane's
operation, four schemas, the `FindingComparison` property and an `info.description` paragraph,
inserted by a script over the integration side's document — equal to git's textual merge),
`web/openapi/openapi.json` byte-identical (sha256 `a9ce1b50…6ee4fe`), `api:generate` +
`api:verify` (61 operations), `web/FRONTEND_LOCK.json` (contract/snapshot/generated digests,
counts, content commit `a820849`), `tests/support/expected_facts.json` (54 paths, 61
operations, 158 schemas), every surface-count prose line (re-measured from the contract, with
the 422 subsets: 43 with / 18 without), the prose mutation literals in
`test_surface_counts_in_prose.py`, the 404-reference count (38), `REQUIRED_OPERATIONS` and
`WRITE_OPERATIONS`, the role register and authorization guard lists, the subject-reader list
(`comparison.py`), the 422 set, the P02 seam table and its keyed-writes rule, the web keyed-writes
list (twelve) and the dashboard-invalidation map. Surface prose: `app.py`, `health.py`,
`routers/{__init__,declarations,errors}.py`, `api/README.md`, `P02_SEAMS.md`, `ALPHA_ROADMAP.md`,
`infra/deploy/{README.md, proxy/nginx.conf, serve.py}`, the BFF route header and
`shared/api/authorization.ts`. `CURRENT_STATE.md` is the integrator's and still states 53/60/154.

## Checks (phase B, on the final merged tree `d10c06e3` + this report)

- `tests/contract` (container-free; `test_cp00_candidate`, `test_cp00_final_state`,
  `test_validate_bootstrap` deselected as environmental in a lane worktree — `.git` is a file,
  the CP-00 tag and `jsonschema` are absent): **910 passed, 4 failed** — the two known
  pre-existing reds (`test_error_kernel::test_there_are_twenty_four`,
  `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`),
  `test_doc_prose_facts` (`CURRENT_STATE.md` 53/60/154, the integrator's file) and
  `test_alpha_acceptance_command` (refuses an uncommitted checkout; green on a clean tree).
- `npm --prefix web ci` once; `api:generate` / `api:verify` OK (61 operations); `lint --quiet`
  clean; `typecheck` clean; vitest `tests/unit/comparison tests/guards tests/contract`: **453
  passed** (31 files), including the rendered-language guard with the carryover states
  (offered on the compared screen; confirming, pending, carried, replayed, each refusal).
- `tests/e2e/test_pc01_journey_conformance.py`: **87 passed**.
- Lane database (`make up` + `make migrate`, 0024): `tests/integration/comparison
  tests/unit/comparison tests/integration/decisions` **306 passed**; focused API/composition
  suites (`test_authorization`, `test_role_register`, `test_served_document_and_health_plane`,
  `test_operation_surface`, `test_router_and_body_rules`, `test_decision_carryover_over_http`,
  `test_version_comparison_over_http`, `test_every_port_implementation_is_whole`,
  `test_an_absent_parent_is_not_an_empty_page`, `test_composition_root`,
  `test_api_token_channel`): **158 passed, 1 failed** — the pre-existing
  `test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it` (`DecisionAdapter`, red on
  the base before this lane, untouched).
- `test_decision_carryover_over_http.py` (new, recorded runs over the composed app): candidates
  appear after an accept, `201` with provenance, replay under another key, crossed/decided/stale
  `409` with their `conflict_reason`, missing key or body `422`.
- Not run (R-135): full gate, live browser journey, whole frontend suite, provider calls.

## Integrator instructions

Merge the branch head `agent/w59-decision-carryover-01` (it already contains
`integration/night-1020` at `a820849a`). If the integration branch moved again, re-run the
derivation rather than hand-merging generated files: take the integration side of
`contracts/api/v1/openapi.json`, re-insert this lane's operation/schemas/property, copy to
`web/openapi/openapi.json`, `npm --prefix web run api:generate`, re-derive `FRONTEND_LOCK.json`,
`expected_facts.json` and the surface prose. Update `CURRENT_STATE.md` to **54 paths / 61
operations / 158 schemas** (head `0024_version_classification`, 25 error codes), which clears the
one prose red. No migration, dependency, composition-root rule (the adapter gained a method on the
existing `comparisons=` port), global style or ref changed. Rollback: revert the merge; carried
decisions remain ordinary append-only decision events.

## Hotspot proof

`git diff --name-only integration/night-1020 HEAD` (61 paths) lies entirely inside this task's
`allowed_paths` (checked by script); it contains no `db/migrations/**`, dependency manifest or
lock, `web/src/_app/providers.tsx`, global style, `dispatch/**`, `CURRENT_STATE.md`, ref or tag.
Phase A touched only `src/auditmanager/{comparison,decisions}/**`,
`tests/{integration/comparison,integration/decisions,unit/comparison}/**` and this report.
Nothing was pushed or tagged.
