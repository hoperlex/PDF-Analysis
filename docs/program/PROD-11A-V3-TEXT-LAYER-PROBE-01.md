# PROD-11A-V3-TEXT-LAYER-PROBE-01 — does a v3 Run leave the saved text layer that АР optimisation reads

Task: `docs/program/tasks/PROD-11A-V3-TEXT-LAYER-PROBE-01.md`. Branch `agent/prod-11a-v3-text-layer-probe-01`, base `0e663fd0` (`integration/ar-close-1026`). Plan item `PROD-11a` of `PRODUCTION-READINESS-PLAN-01.md`, debt `D-222`, `PROD-10-AR-V2-EXTRACT-01` finding 2. A measurement: nothing under `src/`, `db/`, `contracts/`, `infra/` or `web/` changed.

## Verdict: UNSAFE

A v3 Run **keeps** the saved text layer, but on the schema at head (`0032_ar_v3_run_group`) it **cannot reach `published`**, so the readers answer `analysis_missing`.

| Question | Answer | Evidence |
| --- | --- | --- |
| (2) Does a v3 Run leave a saved text layer that `saved_page_text` returns? | **Yes**, every Run, including the failed ones | 18 of 18 Runs: `source_preparation` succeeded, text-layer blob bound, the served reader returns 8 pages whose digest equals the stage's reference |
| (1) Does a v3 Run reach the state the readers accept (`published`)? | **No** on the schema at head | 12 of 12 Runs of the two real-schema groups end `failed`; `_newest_published` is `None`, `_read_source` answers `analysis_missing` |
| Is one piece missing, or several? | Two independent pieces; the first decides the verdict | below |

**Missing piece 1 (decides the verdict, any provider mode).** `stage_result.ck_stage_result_stage_id` admits nine stage ids and not `ar_v3_citation_review`. The v3 CITE writer builds its `StageResult` correctly and the database refuses the row: `new row for relation "stage_result" violates check constraint "ck_stage_result_stage_id"`; the carrier records `failed / internal_error`. `AR-V3-BETA-RUN-STAGE-SEAL-01` added the tenth id to the API vocabulary and said the worker "may use" it; no migration widened the CHECK (`rg -n ar_v3_citation_review db` prints nothing), and every CITE test uses fakes (`FakeRuns`), so nothing ran the writer against PostgreSQL. **Where it is fixed:** a new migration after `0032_ar_v3_run_group` (history is immutable, so not an edit of `0002`) that replaces `ck_stage_result_stage_id` with the ten ids; it needs the migration-head slot, and a change under `db/migrations/**` is one of the named cases for a complete gate in `AGENTS.md` section 8 (timing under the `R-135` override). `ck_model_call_stage_id` needs nothing: the v3 call is journalled under `text_analysis`.

**Missing piece 2 (recorded mode only, behind piece 1).** The composition root's recorded branch builds `EnvironmentProviders(RecordedAdapter(), config, call=None)`; a replayed reply carries no cost and the call is not marked unmetered, so the v3 worker refuses after the provider call (`_check_completed_cost`: `a metered AR v3 call has no verifiable cost amount`, `analysis_input_invalid`). Legacy v1 estimates a cost from the pin table; v3 refuses by design (`AR-V3-BETA-COST-REFUSAL-01`). It does not affect a live or proxied call that reports a cost, or a connection that is `not_metered`. It matters to the **recorded positive cases of `AR-V3-BETA-ACCEPT-01`**, which cannot run on the stock recorded composition until the recorded binding is marked unmetered (`bootstrap/composition.py`, recorded branch) or the recordings carry a cost.

**What this means for `D-222` and `PROD-11`.** The plan's three owner options start from "v3 does not persist the layer"; that premise is false. The layer is there. What `PROD-11` waits for is not a choice about the readers but the fix of piece 1: with only that CHECK widened, the same drive publishes all six Runs and the readers answer `ready` (fact 9, and the independent check M14). Until then, **activating the group (`PROD-12`) on the current schema would make six provider calls per version that each end in a refused CITE row**: the call is journalled before the failing write (6 of 6 requests were answered before the failure, both groups). That cost is inferred from the order of events, not measured live.

## Method

The module `tests/integration/runs/test_v3_saved_text_layer_probe.py` creates a throw-away database on the lane server, migrates it with the literal migration command, and drives:

1. a **v1 control** (`start_audit_run` then `run_to_terminal`, stock recorded replay of the committed recording) over the same PDF bytes;
2. a **reviewed pack** seeded from the pattern of `tests/integration/db/test_ar_v3_run_group.py` but with real canonical set bytes in the bucket and real custody rows (six scopes, each set carrying that scope's items), the current norms snapshot and `start_ar_v3_group`;
3. three six-Run **groups**, each on its own version of the same bytes, each Run through `run_to_terminal(..., ar_v3_pack_registry=registry)`, i.e. the worker's own entry point, `execute_run`, the three deterministic stages, `dispatch_v3_provider_call`, `run_v3_cite_stage`, `finish_v3_review_run`:
   - **served recorded composition**: providers `EnvironmentProviders(adapter, config, None).resolve`, the shape `bootstrap/composition.py` builds for `provider_mode == "recorded"`;
   - **recorded replay, call marked unmetered**: providers return `CallBinding(unmetered=True)`, the shape of a `not_metered` connection, so the cost seam is satisfied and the next seam is exposed;
   - **what-if**: the same unmetered binding after `ck_stage_result_stage_id` is widened to ten ids **in the throw-away database only** (guarded by name; `ALTER TABLE` on nothing else);
4. for every Run: state, terminal reason, stage statuses, bound artifact roles, and what the served `_SpecificationTextReader.saved_page_text` answers; for every version: `_newest_published` and `_read_source` (positions `None`: no price list).

Real: PostgreSQL, the bucket, the pinned extractor, the executor, the v3 journal and CITE writer, the served reader. Stood in: the reviewed pack (data that no code can supply, `D-204`; synthetic sets) and the model answer (an empty reply, `{"observations":[]}`, written on first sight into a temporary directory and replayed by the stock `RecordedAdapter.complete`; no client, no credential, no cost). The text layer does not depend on either: `source_preparation` runs before the provider is asked anything.

## Measured table (run `-s`, parsed from `PROD11A-MEASUREMENT`; Run ids abbreviated to their last six characters)

Every Run of every group: `source_preparation`, `page_geometry_extraction`, `document_context_build` succeeded; text-layer blob `prepared.text_layer` bound; `saved_page_text` answers 8 pages, digest equal to the stage's reference; exactly one provider request per Run was answered before the outcome.

| Group (version) | Scope: Run | Terminal | Reason | CITE stage row | `_newest_published` | `_read_source` |
| --- | --- | --- | --- | --- | --- | --- |
| served recorded composition | F1 TDPPPT, F2 EGXJW8, A1 G9MH5K, A2 7J44MN, S1 P0JHDQ, S2 JYHWWE | failed ×6 | `analysis_input_invalid` (cost) | none | `None` | `analysis_missing` |
| recorded replay, unmetered | F1 C3EEJY, F2 XJF02X, A1 XVPEDW, A2 GR4Q8E, S1 VA570Q, S2 FMZ3MB | failed ×6 | `internal_error` (`ck_stage_result_stage_id`) | none | `None` | `analysis_missing` |
| what-if, stage CHECK widened | F1 TRD199, F2 AYWQBN, A1 5C1HY2, A2 W06K6K, S1 9J7X48, S2 P0GJM0 | **published ×6** | none | succeeded ×6 | S2 (`…P0GJM0`) | `ready`, run S2, 0 rows |
| v1 control | PE42E2 | published | none | not applicable | PE42E2 | `ready`, run PE42E2, 0 rows |

`0 rows`: the baseline PDF has no specification table, for v1 as for v3, so the extraction step is not what this probe measures (limits). S2 is the newest published Run of the what-if group because it is the last-created member: the listing orders by `created_at DESC, run_id DESC`.

Schema at head and after the what-if (from the module's own output):

```text
before: CHECK ((stage_id = ANY (ARRAY['source_preparation'::text, 'page_geometry_extraction'::text, 'document_context_build'::text, 'text_analysis'::text, 'block_analysis'::text, 'finding_merge'::text, 'finding_review'::text, 'finding_correction'::text, 'norm_verification'::text])))
after : the same list plus 'ar_v3_citation_review'::text
```

## The nine facts the module asserts (test names in the module)

| Fact | Test | Statement |
| --- | --- | --- |
| 1 | `test_the_migrated_schema_does_not_admit_the_cite_stage` | nine stage ids at head, `ar_v3_citation_review` not one; the what-if added exactly that one |
| 2 | `test_every_provider_request_was_answered_before_the_run_failed` (×2) | six scopes in order, six requests, the three deterministic stages succeeded in every Run |
| 3 | `test_the_served_recorded_composition_refuses_every_run_on_cost` | `failed` / `analysis_input_invalid`, message names the missing cost amount |
| 4 | `test_an_unmetered_call_is_refused_at_the_cite_stage_row` | `failed` / `internal_error`, the cause names `ck_stage_result_stage_id`, no CITE row |
| 5 | `test_no_v3_run_is_published_on_the_migrated_schema` | twelve of twelve `failed` |
| 6 | `test_every_v3_run_leaves_the_saved_text_layer_whatever_its_terminal` (×3) | layer present and returned in all 18 Runs |
| 7 | `test_the_readers_find_no_published_run_of_an_unpublished_v3_group` (×2) | `_newest_published` `None`, `_read_source` `analysis_missing` |
| 8 | `test_the_v1_control_is_published_and_the_same_readers_answer` | the instrument reads a working path as working |
| 9 | `test_with_the_stage_check_widened_all_six_publish_and_the_readers_answer` | what-if: six `published`, CITE `succeeded`, readers `ready` |

Two more tests: `test_the_probe_stayed_on_the_loopback`, `test_the_guards_of_the_probe_can_fail`.

## Mutation table (each applied alone to the committed module, run, then `git checkout`; last line after restoring)

Command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/runs/test_v3_saved_text_layer_probe.py`; baseline `15 passed`.

| Mutation | Result | Red |
| --- | --- | --- |
| M1 assert the schema admits the CITE stage | 1 failed, 14 passed | fact 1 |
| M2 assert five provider requests, not six | 2 failed | fact 2 (both groups) |
| M3 assert the served composition publishes | 1 failed | fact 3 |
| M4 assert the unmetered call publishes on the real schema | 1 failed | fact 4 |
| M5 assert twelve real-schema Runs published | 1 failed | fact 5 |
| M6 assert `saved_page_text` does not answer | 3 failed | fact 6 (three groups) |
| M7 assert a published Run is found on the real schema | 2 failed | fact 7 |
| M7b assert `_read_source` answers `ready` on the real schema | 2 failed | fact 7 |
| M8 assert the v1 control fails | 1 failed | fact 8 |
| M9 assert the what-if group does not publish | 1 failed | fact 9 |
| M9b assert the what-if reader answers `analysis_missing` | 1 failed | fact 9 |
| M10 the loopback guard raises nothing | 1 failed | guards test |
| M11 the database-name guard disabled | 1 failed | guards test |
| M12 instrument: the what-if widening is skipped | 2 failed | facts 1 and 9 |
| M13 instrument: the unmetered group uses the served composition | 2 failed | facts 4 and 9 |
| M14 behaviour: `"ar_v3_citation_review"` added to `STAGE_IDS` of `db/migrations/versions/20260910_0002_pc01_schema.py` for one run (reverted at once) | 5 failed, 10 passed | facts 1, 2 (unmetered), 4, 5, 7 (unmetered): the real-schema unmetered group **publishes** with only that change |
| restored | `15 passed`; `git status --short` empty | |

M14 is the proof that a later fix turns this module red on purpose, and an independent confirmation of the what-if (it goes through the real migration path, not an `ALTER`). The migration file was edited for the length of one run and restored with `git checkout`; `git diff --name-only 0e663fd0..HEAD` below shows it untouched.

## Commands and results

| Command | Result |
| --- | --- |
| the module (above) | 15 passed, about 13 s |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (clean committed tree) | see the lane answer for the count |
| governance one-liner on the task file | `[]` |
| `git diff --check 0e663fd0..HEAD` | exit 0 |

One pytest process at a time; no docker; no process killed; no full gate and no whole `tests/integration` (R-135 override). Free disk stayed between 1.6 and 1.8 GiB; the module writes a few kilobytes of content-addressed objects to the lane bucket and drops its database. After the last run `pg_database` held no `prod11a_probe_*` database.

## Integration notes (for the integrator)

1. Record the verdict in `D-222`: UNSAFE, missing piece 1 as above; `PROD-11` stays held until a migration slot admits `ar_v3_citation_review` in `ck_stage_result_stage_id` and the integration tests (`tests/integration/db`, `tests/integration/runs`) are rerun on the lane stack. This module is the check for that: it will go red exactly where listed under M14, and the facts to rewrite then are 1, 2 (unmetered), 4, 5 and 7 (unmetered), after which `D-222` can be closed.
2. Piece 2 belongs with `AR-V3-BETA-ACCEPT-01` (recorded positive cases): mark the recorded binding unmetered in the composition root, or give the recordings a cost. Both are outside this lane.
3. Do not start `PROD-12` activation on the current schema (six paid calls per version, six refused CITE rows).
4. The module needs `CREATEDB` on the lane server and the lane bucket; it creates and drops one database per run (about thirteen seconds for the whole module, migration included). It runs inside `tests/integration/runs` and uses the runs harness fixtures `blob_store` and `provider_config`.
5. The module is already a fixture of the missing driver: `_drive_group` takes the six Runs to terminal through the production path. `AR-V3-BETA-ACCEPT-01` can reuse it.

## Limits

- The pack is synthetic (one paragraph per set, an empty reply); a real pack and real replies change the CITE content, not the stage row or the terminal selection.
- The PDF is the committed AR baseline (8 pages) and has no specification table, so both v1 and v3 give 0 rows; `read_specification_prices` (needs a price list) and the matching step are not exercised, only the two readers' state and text answers.
- Live mode is not measured: no credential, no network. Missing piece 1 does not depend on the provider mode (the refused write is the same row); the cost of a live activation is inferred.
- Python-level connections are recorded and checked to be loopback; the pooled bucket connection may be reused and so not appear, and the database driver does not use Python sockets, so this is not a complete egress proof. The recorded adapter holds no client and no credential.
- Only the readers and stage rows were read. The group-review read model, the run list and the web screens were not driven.
- The what-if is a hypothesis measured in a throw-away database: it shows nothing else blocks in this setting, not that the eventual migration is correct.

## Forbidden paths untouched

```text
$ git diff --name-only 0e663fd0..HEAD
docs/program/PROD-11A-V3-TEXT-LAYER-PROBE-01.md
docs/program/tasks/PROD-11A-V3-TEXT-LAYER-PROBE-01.md
tests/integration/runs/test_v3_saved_text_layer_probe.py
```

`src/**`, `db/**`, `contracts/**`, `infra/**`, `web/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings and the ADRs are untouched; no test other than the new module was added or modified (before/after of modified tests: none).
