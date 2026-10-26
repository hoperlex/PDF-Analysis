# PROD-11B-V3-STAGE-ID-MIGRATION-01 — the database admits the AR v3 CITE stage id

Task: `docs/program/tasks/PROD-11B-V3-STAGE-ID-MIGRATION-01.md`. Branch `agent/prod-11b-v3-stage-id-migration-01`, base `3f36f664` (`integration/ar-close-1026`). Debt `D-225` (found by `PROD-11a`, report `PROD-11A-V3-TEXT-LAYER-PROBE-01.md`), closes piece 1 of it and with it `D-222`. The integrator owned the migration-head slot for this lane.

## Result

Migration `0033_ar_v3_cite_stage_id` (`db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py`, `down_revision = "0032_ar_v3_run_group"`) replaces `stage_result.ck_stage_result_stage_id` with the nine registry ids plus `ar_v3_citation_review`, in one `ALTER TABLE` (drop and add in the same statement). No table, column, row or trigger moves. The downgrade refuses (`RuntimeError`, `0033 downgrade refused`) while a `stage_result` row carries the new id and otherwise restores `0002`'s constraint exactly. The head is now `0033_ar_v3_cite_stage_id`.

After it, in the probe's throw-away database, the six Runs of the unmetered recorded group end `published` with a `succeeded` CITE row and the specification readers answer `ready`. The stock recorded composition still refuses every Run on cost (piece 2 of `D-225`; not this lane).

## Premise result

The premise matched; nothing differed (task file, P-01 to P-05, real output). Three CHECKs enumerate the nine ids: `ck_stage_result_stage_id`, `ck_model_call_stage_id`, `ck_finding_observation_stage_id`, all from `STAGE_IDS` of `0002`, never redefined since. The v3 code writes the CITE id into `stage_result` (refused), into `audit_event` payloads and `analysis_artifact_publication.stage_id` (both already admit it: no vocabulary, and a lower-snake-case pattern). It writes `model_call` only through one INSERT that names `'text_analysis'`, and no v3 path writes `finding_observation`. So only the stage CHECK is widened; the other two stay at nine ids and a test holds them there.

## Files (`git diff --name-only 3f36f664..HEAD`)

```text
db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py           new
tests/integration/db/test_ar_v3_cite_stage_id_migration.py            new (8 tests)
tests/integration/runs/test_v3_saved_text_layer_probe.py              facts that flip rewritten (15 tests -> 13)
tests/integration/db/test_schema_invariant_inventory.py               constraints digest resealed
tests/integration/db/test_downgrade_chain_round_trip.py               one digest entry for 0033
tests/integration/db/test_ar_v3_run_group.py                          head literal -> FACTS.migration_head
tests/support/expected_facts.json                                     migration_head
scripts/recovery/schema_coverage.py                                   HEAD
docs/program/tasks/PROD-11B-V3-STAGE-ID-MIGRATION-01.md               this lane
docs/program/PROD-11B-V3-STAGE-ID-MIGRATION-01.md                     this report
```

Pins of the old head that were NOT changed because they are history, not claims: `scripts/recovery/product_purge.py` (comments), `tests/integration/recovery/test_synthetic_drill_seed.py`, `test_synthetic_drill_compare.py`, `test_product_purge.py`, `test_product_purge_run_group.py`, `tests/integration/p02_journey/journey.py`, `tests/integration/db/test_migration_lifecycle.py` (all list tables or narrate `0032`; this migration adds no table, and the recovery and lifecycle suites pass as they are).

## New tests (`tests/integration/db/test_ar_v3_cite_stage_id_migration.py`, real PostgreSQL, one throw-away database each)

| Test | Claim |
| --- | --- |
| `test_the_migrations_vocabulary_is_0002s_nine_ids_plus_the_profile_stage_of_the_api_and_the_contract` | no database: the migration's restated ids equal `0002`'s `STAGE_IDS`, `StageId`, and (the one) `ArV3BetaStageId` and the stage extension contract's `stage_id` |
| `test_the_check_reads_back_as_the_nine_ids_plus_the_cite_id` | `pg_get_constraintdef` lists exactly nine plus one, in that order, validated; five lookalike ids are refused |
| `test_the_cite_row_is_refused_at_0032_and_accepted_after_the_step` | the same insert fails on `ck_stage_result_stage_id` at `0032` (control: a registry id is stored) and succeeds at `0033`; one CITE row per run |
| `test_the_cite_row_is_accepted_at_the_head` | the head clone accepts it |
| `test_a_populated_0032_database_upgrades_without_a_row_changing` | 15 `stage_result` rows (succeeded and failed) are identical before and after |
| `test_the_two_other_checks_over_the_nine_ids_are_not_widened` | `ck_model_call_stage_id` and `ck_finding_observation_stage_id` still list the nine; a `model_call` row with the CITE id is refused by the first |
| `test_the_downgrade_is_refused_while_a_row_carries_the_new_id_and_only_then` | refusal message, version, constraint text and rows unchanged; deleting the row lifts it |
| `test_without_such_a_row_the_downgrade_restores_the_nine_id_check_and_the_upgrade_runs_again` | downgrade restores nine ids, validated, rows kept; the CITE row is refused again; re-upgrade restores the same definition |

## Mutation table (each applied alone, tests run, then `git checkout`; `git status --short` empty after every one)

| Mutation | Result | Red |
| --- | --- | --- |
| M1 migration omits the CITE id | 6 failed, 2 passed (new module) | vocabulary tie, read-back, refused/accepted, head acceptance, populated upgrade, downgrade-only-then |
| M2 migration adds an extra id `ar_v3_extra` | 3 failed | vocabulary tie, read-back, populated upgrade |
| M3 downgrade guard never refuses | 1 failed | refused-only-then |
| M4 downgrade restores the ten-id CHECK | 2 failed | refused-only-then, restores-nine |
| M5 downgrade guard always refuses | 2 failed | refused-only-then, restores-nine |
| M6 migration also widens `ck_model_call_stage_id` | 1 failed | the two other checks |
| M7 CITE id placed first | 4 failed (inventory + module) | `test_every_migration_invariant_family_matches_the_reviewed_fresh_database`, vocabulary tie, read-back, populated upgrade |
| M8 whitespace changed inside the 0033 upgrade text | 1 failed | `test_the_upgrade_surface_of_every_touched_migration...[20261026_0033...]` |
| M9a `schema_coverage.HEAD` left at `0032` | 25 failed, 5 passed | `test_schema_coverage.py` |
| M9b `expected_facts.json` left at `0032` | 3 failed | `test_true_migration_head_is_a_real_single_head`, `test_the_scanned_docs_state_the_migration_head_this_tree_has`, `test_upgrade_from_0031_preserves_old_runs` |
| PA (M14 reversed) migration omits the CITE id, probe run | 5 failed, 8 passed | fact 1, fact 2 (unmetered), fact 4, fact 5, fact 7b |
| P1 probe asserts nine ids | 1 failed | fact 1 |
| P2 probe asserts five requests | 2 failed | fact 2 (both groups) |
| P4 probe asserts the unmetered group fails `internal_error` | 1 failed | fact 4 |
| P5 probe asserts twelve failed | 1 failed | fact 5 |
| P7b probe asserts `analysis_missing` on the published group | 1 failed | fact 7b |
| P10 probe database-name guard disabled | 1 failed | `test_the_guards_of_the_probe_can_fail` |
| restored | new module 8 passed, probe 13 passed | |

Also shown before any mutation: with `0033` present and the old probe, exactly five tests went red (task file P-05), the five that the probe report predicted.

## Before and after of every modified test

- `test_ar_v3_run_group.py::test_upgrade_from_0031_preserves_old_runs`: before, the revision after `upgrade head` equalled the literal `"0032_ar_v3_run_group"`; after, it equals `FACTS.migration_head` (the hand-maintained fact, `0033_ar_v3_cite_stage_id`, as the sibling migration tests do). Same strength; M9b shows it goes red when the fact is stale. Nothing else in the test changed.
- `test_schema_invariant_inventory.py::test_every_migration_invariant_family_matches_the_reviewed_fresh_database`: before, ten digests plus `constraints` `(814, 25ea815f…)`; after, the same ten and `constraints` `(814, 61200aa0b25e…)`. Measured, not predicted: a fresh `0032` and a fresh `0033` database diffed row by row: constraints 814 and 814, one row removed and one added, both `stage_result.ck_stage_result_stage_id`, differing by the appended literal `ar_v3_citation_review`; columns, relations, indexes and triggers equal. The test's other families passed against the old digests, which is the check for the rest.
- `test_downgrade_chain_round_trip.py`: one more parameter of `test_the_upgrade_surface_of_every_touched_migration_is_the_one_on_origin_dev` (the 0033 digest, taken from the revision's own bytes; M8 shows it can fail). The step-by-step walk derives its chain from the revision graph, so it now includes `0033` (every downgrade step restores the previous inventory; the 0033 step passes).
- `test_v3_saved_text_layer_probe.py` (15 tests to 13):

| Before | Asserted before | After | Asserts after |
| --- | --- | --- | --- |
| `test_the_migrated_schema_does_not_admit_the_cite_stage` | nine ids, CITE not one, the what-if added exactly it | `test_the_migrated_schema_admits_the_cite_stage` | the ids are the nine plus CITE, in order |
| `test_every_provider_request_was_answered_before_the_run_failed` ×2 | six requests, stage statuses = the three deterministic stages | `test_every_provider_request_was_answered_and_the_stage_rows_are_those_the_cost_seam_allows` ×2 | six requests; statuses = three (cost-refused group) or three plus CITE `succeeded` (unmetered group) |
| `test_the_served_recorded_composition_refuses_every_run_on_cost` | `failed / analysis_input_invalid`, message names the missing cost | unchanged | unchanged |
| `test_an_unmetered_call_is_refused_at_the_cite_stage_row` | `failed / internal_error`, cause names the CHECK, no CITE row | `test_an_unmetered_call_publishes_every_run_with_a_succeeded_cite_row` | `published`, no reason, no error, CITE `succeeded`, the review artifact bound |
| `test_no_v3_run_is_published_on_the_migrated_schema` | twelve `failed` | `test_the_outcome_of_the_twelve_runs_is_decided_by_the_cost_seam_alone` | six `failed / analysis_input_invalid` then six `published` (more specific: carries the reasons) |
| `test_every_v3_run_leaves_the_saved_text_layer_whatever_its_terminal` ×3 | layer saved and returned in served, unmetered and what-if groups | same, ×2 | same assertions on the two groups that remain |
| `test_the_readers_find_no_published_run_of_an_unpublished_v3_group` ×2 | `None` / `analysis_missing` on both real-schema groups | `..._of_the_cost_refused_group` | same assertions, served group only |
| (part of fact 9) | | `test_the_readers_answer_ready_on_the_published_group` | newest published is one of the six, `ready` on it, its layer equals that Run's saved layer |
| `test_the_v1_control_is_published_and_the_same_readers_answer` | unchanged | unchanged | unchanged |
| `test_with_the_stage_check_widened_all_six_publish_and_the_readers_answer` | what-if group: six published, CITE succeeded, readers `ready` | removed | its Run assertions moved to the unmetered group (fact 4), its reader assertions to the line above |
| `test_the_probe_stayed_on_the_loopback`, `test_the_guards_of_the_probe_can_fail` | unchanged | unchanged | unchanged |

The what-if group, its third source version and its `ALTER TABLE` (`_widen_stage_check`) are removed: the real migration now does what the what-if only hypothesised, and a test that edits a constraint has no place beside the real one. The database-name guard that protected that `ALTER` now guards the probe's first write (`_drive` asserts it is connected to a `prod11a_probe_*` database); its test is unchanged and P10 shows it can fail.

## Commands and results (lane stack, one pytest at a time, no docker, no process killed)

| Command (prefix `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`) | Result |
| --- | --- |
| `tests/integration/db` (whole, includes `test_migration_lifecycle.py`, the chain round trip, the inventory, the new module) | 603 passed, 10 min 27 s |
| `tests/integration/recovery` (whole) | 320 passed, 2 min 54 s |
| `tests/integration/p02_journey/test_whole_journey_idempotency.py` | 2 passed |
| `tests/integration/runs/test_v3_saved_text_layer_probe.py` | 13 passed (15 before) |
| `tests/integration/db/test_ar_v3_cite_stage_id_migration.py` | 8 passed |
| `tests/contract/analysis_packages` | 52 passed |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (clean committed tree) | 104 passed, 1 failed: `test_the_scanned_docs_state_the_migration_head_this_tree_has` (the two documents below; an earlier run, before the task file's enumerator flag was put in the governed form, was 2 failed, 103 passed) |
| governance one-liner on the task file | `[]` |
| `git diff --check 3f36f664..HEAD` | exit 0 |

Free disk stayed between 1.8 and 1.9 GiB. After the runs `pg_database` held none of this lane's databases (`a1_probe_*`, `a1_clone_*`, `a1_tpl_*` of this tree, `prod11a_probe_*`, `prod11b_*`); the three `a1_tpl_840b23b0bf99_*` databases on the server predate this lane and were not touched.

## Documents whose head sentence now fails the prose guard (the integrator updates them; the lane may not)

Fail `tests/contract/api_v1/test_doc_prose_facts.py::test_the_scanned_docs_state_the_migration_head_this_tree_has`:

- `docs/program/CURRENT_STATE.md` (line 10: «the migration head is **`0032_ar_v3_run_group`**»)
- `docs/manual-tests/PC-01_prototype.md` (line 39: «Observe the migration head is `0032_ar_v3_run_group`»)

The same guard run is otherwise green. Not scanned by the guard but now wrong as live statements (the integrator decides): `docs/architecture/adr/ADR-0021-production-topology-and-operations.md` lines 44 and 142 («the head is `0032…`», «the head … is unchanged and none of the files that pin the head changes»: four pinning files changed here), `docs/program/PRODUCTION-READINESS-PLAN-01.md` lines 15 and 65 («No migration is added; the head stays `0032…`»), `docs/program/dispatch/PRODUCTION-WAVE-PW2B.md` line 33 (the common rule that names the head as frozen). Everything else naming `0032_ar_v3_run_group` (lane reports, `DEBT-AUDIT-2.md`, `BETA-STATIC-MATRIX-02.md`, `AR-V3-BETA-*`) is a record at its date.

## Integration notes (for the integrator)

1. Merge with `--no-ff`; then fix the two guard documents above (and, as you judge, the unguarded ones), and re-run the three docs guards: the head-sentence failure disappears and nothing else moves.
2. `D-225` check, as written in the register: `rg -n 'ar_v3_citation_review' db/migrations` now finds `0033`; the probe shows six `published` for the **unmetered** recorded group. It does **not** show six published for the stock recorded composition: that group still fails `analysis_input_invalid` on cost, which is piece 2 of `D-225` (mark the recorded binding unmetered in the composition root, or give the recordings a cost). Record piece 1 closed and piece 2 open; `D-222` closes with `D-225` once piece 2 is decided.
3. `PROD-12` activation is still not started by this lane; on this schema the stage-row refusal no longer ends a paid call in a refused CITE row.
4. `AGENTS.md` section 8 names `db/migrations/**` and `tests/support/**` (here `expected_facts.json`) as cases for a complete gate, timing under the `R-135` override. The brief forbade a full gate and a whole `tests/integration`; none was run. The database directories above are green; `tests/integration/runs` and the other contexts were not run whole.
5. The migration is a metadata change (a constraint replaced under a lock on `stage_result`, which is small); no row is rewritten. The deployed database takes it with the literal migration command. Rollback is `alembic downgrade 0032_ar_v3_run_group`, which refuses once a CITE row exists: restore a backup then.
6. `ADR-0021` line 142 said no pinned file changes; the pins that move per migration are the four code or data files in the table above and the two digests (`D-213`).

## Limits

- The two other stage CHECKs (`ck_model_call_stage_id`, `ck_finding_observation_stage_id`) stay at nine ids on the evidence that no code writes the CITE id there. If a future v3 path writes `model_call` under the CITE stage, it needs its own migration; `test_the_two_other_checks_over_the_nine_ids_are_not_widened` will then be the test to rewrite.
- The probe still uses a synthetic pack and an empty recorded reply; its limits (no live provider, text layer only) are those of `PROD-11A-V3-TEXT-LAYER-PROBE-01.md`, unchanged.
- Not run: the full gate, `tests/integration/runs`, `composition`, `analysis`, `findings` whole, the web suites.

## Forbidden paths untouched

```text
$ git diff --name-only 3f36f664..HEAD   (see Files above)
```

`contracts/**`, every composition root (`src/auditmanager/bootstrap/**`), `infra/**`, `profile.json`, `src/**`, `web/**`, root dependency and lock files, global styles, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings and the ADRs are not in that list.
