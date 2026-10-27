# ANALYSIS-PRESETS-01 — named executor selections for a run («Настройки анализа», `R-146av`)

Written 2026-10-27 by the integrator from the final report of the Sonnet lane `ANALYSIS-PRESETS-01` (branch `agent/analysis-presets-01`, tip `5804ee45`, base `05f4584d`; merged as `51ad571c`). **The lane could not create new `.md` files (the harness refused every Write of one), so this report and the task file were written by the integrator from the lane's hand-back; the design is also in the docstring of migration `0037` and in `src/auditmanager/executors/presets.py`, `preset_commands.py` and `preset_audit.py`.** Nothing of it has run on a live host. Owner decision: `R-146av` («Строить пресеты», against the integrator's recommendation, `A-8`).

## What a preset holds, and why only that

A preset is a **name plus an executor connection**. Premise printed by the lane from the code:

- the only per-run fields of `startRun` are `executor_connection_id` and `provider_mode`; `provider_mode` is refused unless it equals the deployment's own;
- `reauditRun` takes no body and the six-check group start takes only a version;
- the analysis profile is routed from the version's classification, it is not chosen;
- the cost ceiling is the process-wide `AUDITMANAGER_RUN_COST_CEILING_USD`;
- no threshold is an input of a start (the hits in the tree are sweep and liveness intervals).

The integrator's description of the preset in the poll («executor route, the per-run cost limit, the threshold») was therefore wider than the code allows; per the instruction the lane built **neither a per-run limit nor a threshold**. A test (`test_analysis_preset_surface.py`) pins «a preset holds only start fields»: a new start field must be added to the preset deliberately.

## Design

| Piece | Content |
| --- | --- |
| Table | `analysis_preset_revision`, append-only: archive is a new row; the database refuses `UPDATE` and `DELETE` |
| Chain trigger | gap-free revision numbers; nothing after an archive; an active name is unique (case-insensitive); the connection must be live; at most 100 presets; one advisory lock |
| Run record | `audit_run.preset_revision_id`, frozen by the guard trigger, with an `INSERT` check that the run froze that preset's connection |
| Ids | no new id prefix (that needs `contracts/domain/identifiers.json`, `src/shared/identity` and the pin of 48, all outside the grant): preset and revision ids are `evt_` ids, like `summary_id` in `0035`; a dedicated prefix is a mechanical change in those three places |
| Access | create, revise, archive: `_ADMIN`; the list: `_ANY_ROLE`; `startRun` with a preset: `_EXPERT` |
| Audit | `executor.preset_*` events; the event id equals the revision id; written in the same transaction |
| Start | the server applies the preset's CURRENT revision (no expected revision on start); the run page shows the revision used; the idempotency fingerprint carries `preset_id`, not the resolved connection, so a retry after a revision replays, while a hand-chosen executor or another preset under the same key is `idempotency_key_reuse` |
| Refusals before the key claim | unknown preset `422 unknown_preset`; archived `409 preset_archived`; a preset together with an executor `422` |
| Re-audit | records no preset; it keeps the executor through the existing `executor_chosen` event |
| Purge/erase | presets are executor configuration: KEPT in the product purge; append-only grants |
| Equivalence | a run started with a preset equals the hand-started run in every column except ids, clock and the preset (`test_a_preset_start_is_byte_identical_to_the_hand_chosen_start`) |
| Web | the section in «Настройки анализа» (list, create, revise as new revision, archive with confirmation; admin-only controls), «Пресет» beside «Исполнитель» at run start (a preset and an executor are mutually exclusive in the body), the preset on the run page and row |

## Contract and migration

Contract `1.8.0` stays (additive). Surface **95/107/314 → 98/111/321** (four operations, seven schemas including `RunPreset`, two optional fields); no new error code. Head **`0037_analysis_presets`** (21 characters); the down/up round trip and the downgrade refusal (refuses while rows exist) are tested. Files that pin head `0037`: `scripts/recovery/schema_coverage.py` (`HEAD`, tables, triggers, counts), `tests/support/expected_facts.json`, `test_downgrade_chain_round_trip.py` (digest), `test_schema_invariant_inventory.py` (reseal), `docs/manual-tests/PC-01_prototype.md`, the application-role grants/lifecycle/shape pins and four recovery count pins. Files that pin the counts: the contract and its mirror, `api/**` prose, `P02_SEAMS.md`, `expected_facts.json`, seam/role/authorization tests; the integrator patched `CURRENT_STATE.md`, `ALPHA_ROADMAP.md`, `infra/deploy/README.md`, `infra/deploy/proxy/nginx.conf`, `infra/deploy/serve.py`, `web/src/app/bff/v1/[...path]/route.ts` and `web/src/shared/api/authorization.ts` (the three prose guards were red until then; 77 passed after).

## Mutation table (lane's own, 36 rows, all restored, all red at the end)

Migration (12): M1 immutable trigger, M2 gap, M3 after archive, M4 case-insensitive name, M5 advisory lock (two real connections), M6 archive repeats name/connection, M7 archived connection, M8 limit of 100, M9 id equals first revision, M10 downgrade refusal, M11 frozen guard, M12 run claims another connection's preset. Commands (7): C1/C2 role of create/archive, C3 audit failure takes the row with it, C4 name in use, C5 archived preset chosen, C6 limit, C7 no-change revision. Start (7): S1 connection applied, S2 preset+executor, S3 fingerprint, S4 run records the revision, S5 replay of a known key, S6 resolved connection in the fingerprint, S7 status preset. API (2): A1 create role, A2 list role. Web (8): W1 admin-only controls, W2 body carries both, W3 intent signature, W4 archived offered, W5 preset on the run page, W6 executor lock, W7 blocker, W8 archive confirmation. Surviving at first pass: W2, W5 (no test) and A1/A2 (selector selected nothing): fixed and rerun red.

## Tests (lane, private databases; the stack's own database untouched)

`tests/unit` 2960 passed; `tests/contract` minus the three `D-220` files 1182 passed, 3 red until the integrator's prose patch (then green); `tests/integration/db` 862 passed (two pins moved after a column rename and were resealed); `recovery` 117 (four count pins moved) and the new classification file 4; `api` + `executors` 907; `runs` + `composition` 2788 (three stand-in/sweep pins fixed); new and related Python tests 155; web `vitest` 204 files / 3136 passed, `tsc`, `eslint`, `api:verify` green. Modified existing web tests (counts of selects/reads/source text, the dashboard hook map, the language-guard matrix with three excused mutation-state labels, live-render `change`); nothing weakened.

## Limits and notes

- The server applies the CURRENT preset revision at start; there is no expected revision on the start request.
- Archiving a connection does not archive the presets that name it; they show as unusable.
- The live-render harness has no form submit; the save button is a click handler.
- The constraint/conflict words `unknown_preset`, `preset_archived`, `preset_name_in_use`, `preset_limit_reached`, `differs_from_current`, `conflicts_with_executor_connection_id` are not in the `contracts/domain/v1/error-codes.json` prose (that family was outside the grant), like `unknown_connection`.
- The preset is a convenience over what the start already takes; it does not make a per-run cost limit or threshold possible. If the owner wants those, they are a separate decision about moving process-wide settings to per-run inputs.
- `/tmp/pytest-of-root/pytest-N` directories of the lane were left in place.
