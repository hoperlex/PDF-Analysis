# CLASSIFICATION-CORRECTION-01 — append-only correction of a version's stage and section

**Base:** `f290f7b7` (`origin/dev` `f6a16a88` plus the frozen task files; surface 71 paths / 81
operations / 235 schemas, 25 API error codes, migration head `0027_optimisation_proposals`),
branch `agent/class-correction-01`, isolated worktree `class-correction`. **Status:** phases A and B
complete. Phase B started from the integrator's "go phase B from `c90d52f3`" (a real merge) and
merged `origin/dev` `06591a52` and `508d7ba1` (documents only) before hand-back. After this
slice: **72 paths / 82 operations / 237 schemas**, API error codes 25, migration head
**`0028_classification_corrections`**. Development candidate under `R-135`: no full gate, no
live journey, no push, merge into another branch or tag.

## Phase B — result

An expert corrects a version's confirmed stage and/or section with a reason through
`correctVersionClassification` (`POST …/versions/{version_uid}/classification/corrections`,
`201`, expert only). The correction is an append-only revision (migration `0028`); the current
classification is the latest revision, derived by the view `version_classification_current`;
every read of a classification — the three version selects, `get_classification`, the two section
views of `SECTION-READ-MODEL-01`, the dashboard breakdown, the `0027` optimisation-pass trigger —
goes through it; runs keep the profile they pinned; the version screen shows the revision, the
history and, for an expert, «Исправить». Decisions D1–D9 of section 3 were followed as written
(D10 as the integrator changed it: no separate dashboard commit).

### What changed

| area | files |
|---|---|
| domain | `sections/correction.py` (phase A), `sections/classification.py` (`correct_document_version_classification`, `ReviewFacts.revisions`, the classify message), `sections/public.py` |
| documents | `documents/repository.py` (the repointed reads, `lock_classification`, `list_classification_revisions`, `insert_correction`), `models.py` (`VersionClassificationRecord.revision`, `ClassificationRevisionRecord`, equality), `public.py`, `__init__.py` |
| dashboard | `dashboard/repository.py` (the breakdown reads the current view) |
| database | `db/migrations/versions/20261020_0028_classification_corrections.py`, `access/references.py` |
| API | `api/schemas/models.py`, `api/routers/sections.py`, `ports.py`, `api/security.py`, `bootstrap/adapters.py`, surface prose in `api/app.py`, `health.py`, `routers/{__init__,declarations,errors}.py`, `api/README.md` |
| contract | `contracts/api/v1/openapi.json` (spliced as text in its own style, `info.description` gains a reseal paragraph), `contracts/domain/v1/error-codes.json` (notes only: the two `conflict_reason`s and the new `validation_failed` constraints) |
| web | `web/openapi/openapi.json` (byte-identical), `web/src/shared/api/generated/**` and `web/FRONTEND_LOCK.json` (re-derived), `entities/document-version` (`model/classification.ts`, `ui/classification-history.tsx`), the new feature `features/correct-version-classification`, `widgets/version-classification`, `app/bff/v1/[...path]/route.ts` and `shared/api/authorization.ts` (surface prose) |
| pins and prose | `tests/support/expected_facts.json`, the registers and counts in `tests/contract/**` (including the two mutation lines of `test_surface_counts_in_prose.py`), `tests/integration/api/**`, `tests/integration/db/**` (inventory, lifecycle, shape, chain), `docs/program/{P02_SEAMS,ALPHA_ROADMAP}.md`, `docs/manual-tests/PC-01_prototype.md`, `infra/deploy/**` prose |

### Read sites, as found on the merged tree (replaces the phase A table for the SQL readers)

`grep -rn document_version_classification src db/migrations` on the tree after the merge of
`c90d52f3`: eight readers and one writer, all now on the current view except the writer.

| # | site | now |
|---|---|---|
| 1 | `documents/repository.py` `_SELECT_VERSION` | `version_classification_current`, plus `c.revision` |
| 2 | `_LIST_DOCUMENTS` | same |
| 3 | `_LIST_VERSIONS` | same |
| 4 | `_SELECT_CLASSIFICATION` (`get_classification`) | same; feeds the comparison adapter and the classify command |
| 5 | `_LIST_SECTION_MEMBERS` (`list_current_versions_in_section`, `SECTION-READ-MODEL-01`) | same |
| 6 | `_LIST_UNCLASSIFIED_CURRENT` (`list_unclassified_current_versions`) | same; the set of unclassified current versions is identical under either relation (a correction needs a confirmation), so no test can tell the two apart and none is claimed |
| 7 | `dashboard/repository.py` `_DOCUMENTS_BY_SECTION` | same |
| 8 | function `am_check_optimisation_pass_scope` (`0027`) | `CREATE OR REPLACE` in `0028`; the downgrade restores `0027`'s body (held equal by a test) |
| – | `_INSERT_CLASSIFICATION` | the writer of revision 1, unchanged table; `RETURNING … 1 AS revision` |
| – | `count_projects` | reads `project` only, not the classification; nothing to repoint |

The consumers of 5.B/5.C of phase A follow without a line of their own: run start and re-audit
(proved over HTTP: a run started before the correction keeps its pin, the replay of its key answers
it, a later start and a re-audit route from the corrected section), the comparison pair guard, the
Form-7 and priced-specification sets, and the version record's equality (a correction between two
reads of a version no longer looks like a changed version).

### Migration `0028_classification_corrections`, measured

Fresh upgrade on the lane's PostgreSQL 17 + pgvector stack; deltas against the `0027` seal, and the
whole of the difference shown to be `0028`'s by the chain test (downgrading `0028` restores the
`0027` inventory row for row). columns +20 → 606, relations +3 → 66, constraints +9 → 657, indexes
+1 → 153, triggers +2 → 72, functions +1 → 31 (and `am_check_optimisation_pass_scope` redefined),
views +2 → 4; extensions, sequences, policies and the state topology unchanged. The pins in
`test_schema_invariant_inventory.py` were rewritten from this measurement, not from the
prediction in section 7 (which it equalled).

### Checks run (lane stack: PostgreSQL 57670, MinIO 61270/61271, database `auditmanager_class_correction`)

| command (from the worktree root) | result |
|---|---|
| `pytest tests/unit tests/integration/sections tests/integration/documents/test_version_record_equality.py tests/contract` | 1888 passed; 210 not passed, all environment: `test_cp00_candidate` (48 failed, 126 errors), `test_validate_bootstrap` (21), `test_cp00_final_state` (3) — the CP-00 families need a git sandbox that a worktree is not (`D-187`) — and 2 in `test_doc_prose_facts`, whose only findings are `docs/program/CURRENT_STATE.md` naming head `0027` and `71/81/235` (the integrator's file) |
| `pytest tests/integration/db` | 534 passed, 1 failed before the reseal (the inventory pins, as expected); after rewriting them from the measurement `test_schema_invariant_inventory.py` passes (2); includes `test_classification_corrections_migration.py` (8), the chain/round-trip test of `GATE-FIX-DB-01` and `test_accounts_migration.py` |
| `pytest tests/integration/documents tests/integration/dashboard` + the inventory file | 53 passed (the current-classification reads, the command, two-session concurrency) |
| `pytest tests/integration/runs` | 413 passed (includes `test_classification_correction_over_http.py`, 11) |
| `pytest tests/integration/api` / `composition` / `comparison` / `optimisation` / `ingest` / `sections` / `decisions` / `access` | 624 / 809 (3 skipped) / 150 / 91 / 649 / 80 / 89 / 239 passed |
| `pytest tests/characterization/w13_baseline` | 67 passed (4 failed before the records moved: 02b, 13, 32, 33) |
| `npm --prefix web ci`; `npm run api:verify`; `npm run typecheck`; `npm run lint -- --quiet` | exit 0 each; `api:verify` OK, 82 operations, contract SHA-256 `b4b7b9fc…6224f` |
| `vitest run tests/guards tests/contract tests/unit/{sections,comparison,optimisation-proposals,specification-prices,optimisation,section-specification,journey,screens,api,projects,shell,styles}` | 85 files, 1350 passed (rendered-language guard, contrast census, frontend lock, dashboard-invalidation map, journey conformance among them) |
| `git diff --check` | clean |

Not run, by `R-135`: a full gate, the live journey (`e2e:pc01` — it has no correction step), a paid
provider call.

### Mutation probes (each applied to the committed file, the named tests run, the file restored)

Phase A's 34 (section 4) still hold. Phase B adds 16 Python probes (all killed) and 15 web probes
(all killed); the probe set is the table, applied one at a time by a throw-away script that asserts
each quoted text occurs exactly once.

| id | mutation | first failing test |
|---|---|---|
| B01 | `_SELECT_VERSION` reads `document_version_classification` | `test_every_version_read_projects_the_latest_revision` |
| B02 | `_LIST_DOCUMENTS` reads it | same |
| B03 | `_LIST_VERSIONS` reads it | same |
| B04 | `get_classification` reads it (`1 AS revision`) | same |
| B05 | `_LIST_SECTION_MEMBERS` reads it | `test_the_section_views_and_the_dashboard_follow_a_correction` |
| B06 | the dashboard breakdown reads it | `test_a_confirmed_code_missing_from_the_vocabulary_is_refused_not_dropped` (and the documents test) |
| B07 | the command does not lock | `TestConcurrentCorrections::test_two_experts_looking_at_the_same_revision_the_loser_conflicts` |
| B08 | the review drops `revisions` | `test_an_expert_corrects_and_the_review_shows_the_new_revision_and_the_history` |
| B09 | the correction answers `200` on the wire | same |
| B17 | the correction is declared `200` in the served document | `test_the_served_document_conforms_to_the_frozen_contract` |
| B10 | the role register lets any role correct | `test_the_registers_are_the_ruled_ones` |
| B11 | the installed scope function keeps reading the original table | `test_populated_0027_upgrades_and_every_current_classification_is_its_original` |
| B12 | the chain trigger admits a no-op | `test_the_chain_is_a_property_of_the_table` |
| B13 | the current view takes the oldest correction | `test_a_correction_is_a_new_revision_and_the_current_view_follows_it` |
| B14 | the chain trigger admits a gap | `test_the_chain_is_a_property_of_the_table` |
| B15 | the corrector is not a registered account reference | `test_the_reference_register_equals_the_schema_foreign_keys_to_app_user` |
| W01–W15 | everyone may correct; each of the five invalidations dropped (optimisation, dashboard, comparisons, projects, and the stale read-back); the reason not trimmed; `expected_revision + 1`; the letter-or-digit rule dropped; an unchanged pair accepted; history oldest first; an administrator offered the control; the history not drawn; a revision's reason hidden; stale read as unchanged | all in `classification-correction.test.ts`: W01, W12, W13 «an administrator alone is offered nothing…»; W02–W05 «on success tells every read that shows a classification»; W06, W07 «sends one POST with the reason trimmed…»; W08 «holds the button while the reason is blank…»; W09 «holds the button while the pair equals the current one…»; W10 «on a stale or unclassified refusal, reads the stored classification back»; W11, W15 «lists every revision newest first…»; W14 «maps each server answer to its kind» |

(B09 first survived: the decorator's `status_code` is documentation, the wire status is
`json_response(201, …)`; the probe was re-aimed at the wire, and the decorator's value is the
subject of B17.)

### Edits outside the task's allowed paths, by the integrator's instruction

* `tests/characterization/w13_baseline/**` (records 02b, 13, 32, 33; `journey.py`; the test file;
  the README) — the four records gain one inserted property, pinned by digest; 02b gains an
  exception block (`D-182`), 13/32/33 gain `D-182` and one sentence. The integrator's message
  after the gate window: "Characterization records 02b/13/32/33 need `revision: 1` … fix what they
  show".
* `tests/integration/dashboard/test_section_breakdown.py` — the fake session matched the SQL by
  the old table name; it follows the current view (the integrator's ruling that the dashboard
  query is repointed "with tests").

### For the integrator

* `docs/program/CURRENT_STATE.md` (not touched): surface **72/82/237**, head
  **`0028_classification_corrections`**, error codes 25.
* `docs/program/DEBT_REGISTER.md` (not touched): `D-182` is resolved by this slice; `D-180` was
  already closed by `SECTION-READ-MODEL-01`; new candidates are in section 11 (a run's pin names no
  classification revision; the live journey has no correction step).
* `NORM-REFS-RUN-01` reseals in parallel and merges after this: its numbers must be re-derived on
  top of this base (72/82/237), never copied; the generated artifacts and every surface-count
  prose line are derived from the merged contract by the commands in section 10.


## Phase A — result

The pure rules of the correction exist, with container-free tests, and the design of phase B is
written below: every read of the classification today with the exact repoint, the proposed
operation, the migration, and the decisions this report takes that the integrator may overrule.

Changed in phase A (all inside the first group of allowed paths):

| file | change |
|---|---|
| `src/auditmanager/sections/correction.py` | new: `plan_classification_correction` and its value types; no I/O |
| `src/auditmanager/sections/public.py` | exports the rules |
| `src/auditmanager/documents/models.py` | `DocumentVersionRecord.classification` leaves the record's equality (see section 5.C) |
| `tests/unit/sections/test_classification_correction.py` | 113 cases (parametrized) for the rules, a seeded 1 500-step simulation, an import-purity test |
| `tests/integration/documents/test_version_record_equality.py` | 3 cases, no database |
| `docs/program/CLASSIFICATION-CORRECTION-01.md` | this report |

## 1. The model

A version's classification is a numbered history. **Revision 1** is the original expert
confirmation (the stored `document_version_classification` row, never touched again). Corrections
are revisions **2..n**, each a full `(project_stage, section_code)` pair with the expert who made
it, a reason and the database's time. The **current classification** is the latest revision —
derived, never stored as a second copy that could disagree. A run keeps the profile pair it pinned
when it started, whatever the classification becomes; a new version inherits nothing.

## 2. The rules (`sections/correction.py`, decided in this order)

| # | rule | refusal | test (phase A) |
|---|---|---|---|
| 1 | **Who:** only an account holding `expert`; `admin` alone is refused; the role set must be a `frozenset` of known roles; the actor identity must parse. Decided first, so a caller who may not correct learns nothing about the request or the version. Any expert may correct, not only the first confirmer. | `permission_denied`, `required_capability: role:expert` | `test_an_expert_may_correct…`, `test_admin_alone_is_refused…`, `test_roles_must_be_a_frozenset…`, `test_a_role_set_holding_an_unknown_role…`, `test_an_invalid_actor_identity…`, `test_authorization_is_decided_before…` |
| 2 | **What may change:** the full target pair, both validated against the fifteen-code catalogue and `P`/`R`; the stage, the section or both may differ | `validation_failed` `enum` on `project_stage` / `section_code` | the parametrized stage/section cases, all fifteen codes |
| 3 | **Reason:** required; trimmed; at most `MAX_REASON_LENGTH = 2000` characters after trimming; holds a letter or a digit; no control or surrogate character (line breaks and tabs allowed) | `validation_failed` on `reason`: `type`, `required`, `max_length`, `printable` | the reason cases (exact bound, bound after trimming, `.`, zero-width, NUL, lone surrogate) |
| 4 | **`expected_revision`:** a plain integer of at least 1 (`bool` is not one) | `validation_failed` `type` / `minimum` | the three `expected_revision` cases |
| 5 | **The stored history is checked, not trusted:** revisions run 1..n without a gap, belong to this version, carry catalogue values and a valid actor, revision 1 has no reason, every later one has a trimmed non-empty reason, no revision repeats the values of the one before | `internal_error` (no request can repair it) | the history-integrity cases |
| 6 | **A correction presupposes the confirmation:** an empty history | `conflict`, `conflict_reason: version_not_classified` | `test_correcting_an_unclassified_version…` |
| 7 | **`expected_revision` ahead of the current revision** | `validation_failed`, `constraint: exceeds_current_revision` | `test_an_expected_revision_ahead…` |
| 8 | **Exact repeat** (`expected_revision` behind): revision `expected + 1` was written by the same actor with the same target pair and the same reason → that stored revision, `unchanged`, nothing written — even if someone corrected after it | none | `test_an_exact_repeat_answers_the_stored_revision…`, `…when_someone_else_corrected_afterwards` |
| 9 | **Conflicting concurrent correction** (`expected_revision` behind, not a repeat): another actor, other values, or the same request with another reason; the first correction stands, nothing is written | `conflict`, `conflict_reason: classification_revision_stale` | the stale/repeat-variant cases, `test_two_experts_correcting_the_same_revision…` |
| 10 | **No-op:** the target equals the **current** classification (not the original — returning to the original values is a legitimate revision) | `validation_failed`, `field: section_code`, `constraint: differs_from_current` | the no-op cases |
| 11 | otherwise **append** revision `current + 1` | — | `test_each_correction_is_the_current_revision_plus_one`, the 1 500-step simulation |

The simulation drives three experts through fresh, stale and retried requests and asserts after
every step: the history grows by at most one revision; revisions stay 1..n; no stored no-op; every
append had `expected_revision == current`; every retry of a success answers the same revision and
appends nothing; a refusal writes nothing; revision 1 is never rewritten.

## 3. Decisions taken in phase A (the integrator may overrule any; phase B follows the defaults)

| id | decision | why / alternative |
|---|---|---|
| D1 | **The reason is part of what makes a repeat exact.** A retry sends the same body; a request that differs only in its reason gets `conflict` with a message that says the first reason stands. | The spec says "same actor + same target values + same expected revision". Ignoring the reason would answer 201 for a request whose reason was silently not recorded (AGENTS §4, no silent fallback). |
| D2 | **A repeat answers the revision its request created, not the current one** (it can be older than the current). The response carries `revision`, so the client sees it. | The only truthful idempotent answer. |
| D3 | **The loser of a race conflicts even when they asked for the same values** as the winner; their reason is not recorded. | The first correction stands; recording a second actor's reason under an identical result would need a different (non-append) model. |
| D4 | **`classifyDocumentVersion` compares against the current classification.** A first-confirmation retry sent after a correction is `409 version_already_classified`; an exact repeat of the current values answers the current row. Its 409 message changes to point at the correction. | PUT stays "set if none; otherwise it must equal what is current". Answering a stale revision-1 retry with the original row would show a client a classification that no longer stands. |
| D5 | **`VersionClassification.confirmed_by_user_uid` / `confirmed_at` become the current revision's actor and time** (who stands behind the current values); the original confirmer is revision 1 in the history. New required field `revision`. | Keeps the field names and every consumer's meaning "who stands behind this"; the alternative (always the original) would make a corrected panel say the wrong person confirmed the new values. |
| D6 | **History travels in `SectionReview`** (new `revisions` list, oldest first) rather than a new read operation. | The version screen already reads the review for the panel; one cache entry; no extra path. Cost: the review reads the recognised-text markdown even when only the history is wanted. Alternative: `GET …/classification/revisions` (+1 path, +1 operation). |
| D7 | **`correctVersionClassification` is unkeyed `POST` returning `201` for a new revision and for a repeat.** No `Idempotency-Key`: `expected_revision` + actor + values + reason is the idempotency rule, as for `classifyDocumentVersion`; `createAssignment` is the precedent for an unkeyed `POST`. | A `POST` also avoids the pinned `PUT`/`PATCH`/`DELETE` set in `tests/e2e/pc01/test_acceptance.py` (no mutating method under `/versions` but the classification). |
| D8 | **No new opaque identity.** A revision is addressed only as `(version_uid, revision)`; `revision` is a per-version order used as the optimistic-concurrency token (the error catalogue already lists `expected_revision`), never a handle on its own. | AGENTS §4 forbids a display number as identity; here the number has no meaning without the version. An opaque id would be a contract-slot change to `shared/identity` and `identifiers.json`. |
| D9 | **`DocumentVersionRecord` equality ignores the classification** (done in phase A). | See 5.C: a correction that commits while a run stage re-reads the version must not fail the run. |
| D10 | **Superseded by the integrator's notice after acceptance (see the addendum at the end):** `SECTION-READ-MODEL-01` (`fee74158`, dev `802b3823`) already groups the dashboard by the confirmed classification of each document's current version and closed `D-180`; phase B has no separate dashboard commit but repoints the dashboard query and three new `documents` queries to the current view. | At the phase A base the dashboard still grouped by the legacy `document.section`; the first draft of D10 proposed repointing it in its own commit. |

## 4. Phase A checks (container-free)

PY = `.local/worktrees/w55b-main-candidate/.venv/bin/python`; every command from the worktree root.

| command | result |
|---|---|
| `$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/sections tests/integration/documents` | 116 passed |
| `$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit tests/integration/sections tests/integration/documents tests/contract/architecture tests/contract/program tests/contract/shared_kernel tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | 916 passed, 30 subtests passed (the surface-count guard first flagged `fifteen codes` in the module docstring as a claim about the 25 error codes; reworded to `fifteen sections`) |
| `git diff --check` | clean |

**Mutation proofs.** Each row applies one textual mutation to the committed file, runs the two
test directories with `-x`, restores the file and records the first failure. 34 mutants, 34
killed (M03 survived the first run — no test held an unknown role next to `expert` — and the
test `test_a_role_set_holding_an_unknown_role_is_refused_even_with_expert_in_it` was added, after
which it is killed). The list below is the whole probe set, applied one at a time by a throw-away script that asserts each quoted text occurs exactly once.

| id | mutation (module `sections/correction.py` unless noted) | first failing test |
|---|---|---|
| M01 | `or ROLE_EXPERT not in actor_roles` → `or False` | `test_admin_alone_is_refused_and_so_is_every_set_that_lacks_expert` |
| M02 | `not isinstance(actor_roles, frozenset)` → `False` | `test_roles_must_be_a_frozenset_of_known_roles` |
| M03 | `or not actor_roles.issubset(ROLES)` → `or False` | `test_a_role_set_holding_an_unknown_role_is_refused_even_with_expert_in_it` |
| M04 | actor `UserUid.parse` check removed | `test_an_invalid_actor_identity_is_refused_as_permission_denied` |
| M05 | request validated before the role check | `test_authorization_is_decided_before_the_request_and_before_the_version_state` |
| M06 | no-op refusal `if not changed:` → `if False:` | `test_a_no_op_correction_is_refused_and_writes_nothing` |
| M07 | no-op judged against `revisions[0]` (the original) | `test_a_no_op_is_judged_against_the_current_classification_not_the_original` |
| M08 | repeat ignores the actor | `test_a_repeat_by_another_actor_is_not_a_repeat` |
| M09 | repeat ignores the reason | `test_a_repeat_with_another_reason_is_refused_and_says_the_first_reason_stands` |
| M10 | repeat ignores the stage | `test_a_repeat_with_other_target_values_is_not_a_repeat` |
| M11 | repeat ignores the section | `test_a_repeat_with_other_target_values_is_not_a_repeat` |
| M12 | `if expected < current.revision:` → `if False:` (stale reads are appended) | `test_an_exact_repeat_answers_the_stored_revision_and_appends_nothing` |
| M13 | repeat looks at `revisions[expected - 1]` | `test_an_exact_repeat_answers_the_stored_revision_and_appends_nothing` |
| M14 | new revision `current + 2` | `test_a_no_op_is_judged_against_the_current_classification_not_the_original` |
| M15 | `if expected > current.revision:` → `if False:` | `test_an_expected_revision_ahead_of_the_history_is_validation_failed` |
| M16 | `type(expected) is not int` → `not isinstance(expected, int)` (accepts `True`) | `test_an_expected_revision_must_be_a_plain_integer[True]` |
| M17 | minimum 1 dropped | `test_an_expected_revision_below_one_is_validation_failed[0]` |
| M18 | `if not revisions:` → `if False:` | `test_correcting_an_unclassified_version_is_a_conflict_that_says_classify_first` |
| M19 | target stage unchecked | `test_an_unknown_stage_is_validation_failed` |
| M20 | target section unchecked | `test_an_unknown_section_is_validation_failed` |
| M21 | reason not trimmed | `test_a_repeat_ignores_surrounding_whitespace_in_the_reason` |
| M22 | bound `>` → `>=` | `test_the_reason_is_bounded_at_exactly_the_documented_length` |
| M23 | bound applied to the untrimmed text | `test_the_bound_applies_after_trimming_not_before` |
| M24 | control and surrogate characters allowed | `test_control_and_surrogate_characters_are_refused_inside_a_reason[\x00]` |
| M25 | letter-or-digit rule dropped | `test_a_reason_without_a_letter_or_digit_is_not_a_reason[.]` |
| M26 | reason type unchecked | `test_a_reason_must_be_text[None]` |
| M27 | revision gap tolerated | `test_a_history_with_a_gap_a_duplicate_or_a_late_start_is_an_integrity_fault` |
| M28 | history of another version tolerated | `test_a_history_naming_another_version_is_an_integrity_fault` |
| M29 | stored no-op in the history tolerated | `test_a_history_that_repeats_the_values_of_the_revision_before_it…` |
| M30 | reason on revision 1 tolerated | `test_reasons_follow_the_original_and_correction_split` |
| M31 | correction without a reason tolerated | `test_reasons_follow_the_original_and_correction_split` |
| M32 | history values outside the catalogue tolerated | `test_a_history_with_values_or_actors_outside_the_catalogue…` |
| M33 | `import sqlalchemy` added to the module | `test_the_module_imports_no_database_store_clock_or_network_code` |
| M34 | `documents/models.py`: `field(default=None, compare=False)` → `field(default=None)` | `test_a_corrected_classification_does_not_make_the_version_a_different_one` |

## 5. READ-SITE INVENTORY

Found by `grep -rn "document_version_classification" src db tests contracts docs web/src
scripts tools infra`, then by following every consumer of `DocumentVersionRecord.classification`
and `get_classification`. Nothing outside `documents/repository.py` and migration `0027` reads the
table itself; everything else reads it through the `documents` boundary, so repointing the
repository's reads moves the whole product at once.

### 5.A SQL that reads `document_version_classification` today — repoint to `version_classification_current`

| # | site (base `f290f7b7`) | reads | repoint |
|---|---|---|---|
| 1 | `documents/repository.py:147` `_SELECT_VERSION` | `LEFT JOIN document_version_classification c` → `c.project_stage, c.section_code, c.confirmed_by_user_uid, c.confirmed_at` for `getDocumentVersion`, `find_version`, every `get_version` | `LEFT JOIN version_classification_current c`; add `c.revision` as the 19th column; `_version_record` (:284) unpacks nineteen, `VersionClassificationRecord` gains `revision` |
| 2 | `:173` `_LIST_DOCUMENTS` | the same four columns for the document set's current version (`listDocuments`, the optimisation and Form-7 set views) | same join, same column |
| 3 | `:191` `_LIST_VERSIONS` | the same for every version (`listVersions`) | same join, same column |
| 4 | `:226` `_SELECT_CLASSIFICATION` (`get_classification` :620) | one version's classification; used by the comparison adapter `_ClassificationReader` (`bootstrap/adapters.py:2822`) and by the classify command's "re-read the winner" | `FROM version_classification_current` |
| 5 | `:233` `_INSERT_CLASSIFICATION` | writes **revision 1** into the base table — stays on the base table; `RETURNING` adds a literal `1 AS revision` | the append-only original stays exactly as 0024 made it (forbidden hotspot) |
| 6 | `db/migrations/versions/20261020_0027_optimisation_proposals.py:219` function `am_check_optimisation_pass_scope` | `JOIN document_version_classification c … AND c.section_code = 'AR'` — the version must be classified `AR` when a pass is written | `CREATE OR REPLACE FUNCTION` in `0028` with `JOIN version_classification_current c`; the trigger `trg_optimisation_pass_scope` stays; `0028`'s downgrade restores the `0027` body first |
| 7 | `dashboard/repository.py` `_DOCUMENTS_BY_SECTION` — **as of the phase A base only; superseded, see the addendum** | at the base: **not the table**, it groups published documents by the legacy `document.section` (`D-180`); after the merge of `fee74158` it groups by the confirmed classification of the current version and reads the table (join to re-measure on the merged tree) | `… JOIN document_version v ON v.version_uid = d.current_version_uid LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid GROUP BY c.section_code`; the base-tree suites (`tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py`, `test_an_absent_parent_is_not_an_empty_page.py`) and the web `widgets/dashboard` model are the places to re-check; the repoint is part of the ordinary repository commit, not a separate one |

New SQL (phase B), not a repoint: the history read (`version_classification_revision` view, ordered
by `revision`), the lock `SELECT … FOR NO KEY UPDATE` on the original row, the correction insert.

### 5.B Consumers that follow once 5.A is repointed — each needs its own evidence in phase B

| site | what it does with the classification | after a correction |
|---|---|---|
| `runs/commands.py:452-467` `start_audit_run` | reads the version in the run-creating transaction, `route_classified_version`, pins the profile pair | routes by the corrected section; a replay of an already-known key answers the original run with its pinned profile (test: start, correct, replay the key) |
| `runs/commands.py:675-677, 711-712` `reaudit_run` | routes from the version's classification now, never from the source run | the way a correction is applied to an old version: re-audit re-routes; the source run's pin is untouched |
| `runs/executor.py:893` and the five input readers | read the version for its manifest; the executor resolves the **run's pinned** profile pair, never the classification | unaffected (see 5.C for the equality hazard) |
| `sections/classification.py` `classify_document_version`, `read_section_review`, `route_classified_version` | stored row via `version.classification` | D4 for classify; the review carries `revision` and `revisions`; routing uses the current revision |
| `comparison/service.py:422-462` via `_ClassificationReader` (`bootstrap/adapters.py:2822`) and `comparison/version_section_pair.py` | each side's stage and section for the pair guard, **per request** — a comparison stores nothing (`read_model.py` docstring) | the pair guard sees the current pair at the next request; a version-mode pair whose sides now differ is refused with `project_stage_mismatch` / `confirmed_section_mismatch` (or `stage_unclassified` / `section_unconfirmed`); `carryOverDecision` recomputes the comparison, so a carryover proposed before the correction can answer `carryover_pair_not_proposed`. Nothing persisted changes. |
| `optimisation/section_specification.py:372`, `optimisation/project_match.py:185` (`list_documents`) | the section set a Form-7 view and a priced specification admit (`section_code == "AR"`, `EXCLUSION_VERSION_UNCLASSIFIED`) | the set membership follows the current classification; the trigger in 5.A row 6 is the second layer; passes already written stay immutable and pinned to their version and run |
| `bootstrap/adapters.py:467, 563` `_version_view`, `_classification_view` and `api/schemas/documents.py:96` | project the record onto `DocumentVersion.classification` / `SectionReview.classification` | add `revision` |
| `ingest/service.py:246-259, 375, 519`, `ingest/reconciliation.py:498` | return a version after an upload or replay | unchanged: a new version starts unclassified and inherits nothing; an upload replay shows the version's current classification as before |
| `specification_prices.py` router and `SpecificationPricesAdapter` (`bootstrap/adapters.py`) | requires the set's current version to be classified `AR` | follows `list_documents` |

### 5.C Guards that compare the whole version record (done in phase A)

`runs/text_window_input.py:158`, `reference_text_input.py:155`, `recognised_region_input.py:270`,
`geometry_crop_input.py:223` and `geometry_crop_item_input.py:160` read a version, read its bytes
from the store, read the version again and refuse `version_changed_during_*_read` when
`second != first`. `DocumentVersionRecord` is a dataclass whose equality covered the
`classification` field, so a correction committed inside that window would have failed a running
stage of a run that is pinned to the profile it started with — the opposite of "runs stay pinned".
Every other field of the record is immutable. Phase A removes `classification` from the record's
equality (`field(default=None, compare=False)`); `test_version_record_equality.py` proves a
corrected classification no longer changes equality or hash, that the field is still carried, and
that every other field still does (the compared-field set is pinned, so a new field must be judged
there). Mutation M34 shows the test failing.

### 5.D Web readers and caches (phase B)

The classification is rendered from `DocumentVersion.classification` and `SectionReview`: the
version screen panel (`widgets/version-classification`), badges (`entities/document-version/ui/
classification-badges.tsx`), the version list, the document list and project structure
(`widgets/project-sections`), the run control's refusal link, the dashboard tiles, the
comparison (`widgets/stage-comparison`) and the optimisation views. `useClassifyVersion` already
invalidates `versions.sectionReview`, the document's version list, `projects.all()` and
`dashboard.summary()`. The correction hook invalidates a superset:

| key | why |
|---|---|
| `queryKeys.versions.all()` | detail (infinite stale time), list, section review, comparisons (`versions.comparisons()` — a pair guard answers differently) |
| `queryKeys.projects.all()` | structure and badges |
| `queryKeys.dashboard.summary()` | the section breakdown groups by the current classification (after `fee74158`) |
| `queryKeys.optimisation.all()` | specification prices, passes, section Form-7 (`section-specification`) |
| `queryKeys.runs.all()` | the run control's «классификация» refusal state and the routing refusal |

### 5.E Tests, pins and prose that name the classification table, the head or the surface

Still correct (they read the base table, which `0028` leaves exactly as it is):
`tests/integration/db/test_version_classification_migration.py`, `test_work_assignments_migration.py`,
`test_optimisation_proposals_migration.py`, `test_downgrade_chain_round_trip.py`,
`tests/integration/ingest/test_next_version.py:199`, `tests/integration/runs/test_w59_*`,
`tests/integration/optimisation/test_section_specification.py:396`, `test_project_match.py:368`
(their table lists for truncation gain the new table). To update in phase B (a sweep, derived
from the tree, not predicted): the head literal `0027_optimisation_proposals` in
`tests/support/expected_facts.json`, `tests/integration/db/test_schema_invariant_inventory.py`,
`test_schema_shape.py`, `test_downgrade_chain_round_trip.py`, `test_migration_lifecycle.py`,
`test_optimisation_proposals_migration.py`, `docs/manual-tests/PC-01_prototype.md`,
`docs/program/P02_SEAMS.md`; the surface triple everywhere `test_surface_counts_in_prose.py`
looks (and its mutation lines) and in the files that pin the operation set
(`tests/contract/domain_p02/test_openapi_document.py`, `tests/integration/api/test_role_register.py`
twice, `test_served_document_and_health_plane.py`, `test_authorization.py`,
`tests/e2e/pc01/journey/manifest.json` and `test_acceptance.py`). The proxy needs nothing: the
new path falls under no upload location (`nginx.conf` matches only `…/documents(/…/versions)?$`).

## 6. The operation (phase B; the reseal is derived, not predicted)

`POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification/corrections`,
`operationId: correctVersionClassification`, tag `documents`, role register `_EXPERT` (admin alone
is `403 permission_denied`, `required_capability: role:expert`; the command re-reads the role set
in its own transaction, as `classifyDocumentVersion` does).

* body `CorrectVersionClassificationRequest {project_stage, section_code, reason (1..2000),
  expected_revision (integer ≥ 1)}`, `additionalProperties: false`;
* `201 VersionClassification` — the revision written, or the stored revision of an exact repeat;
  `VersionClassification` gains the required `revision` (integer ≥ 1) and its description changes
  (D5); `SectionReview` gains `revisions: VersionClassificationRevision[]` (oldest first; each
  `{revision, project_stage, section_code, actor_user_uid, at, reason|null}`; revision 1 has
  `reason: null`);
* errors, no new code: `401/403`, `404` (the chain: unknown project, a document of another
  project, a version of another document), `409 conflict` (`version_not_classified`,
  `classification_revision_stale`), `422 validation_failed` (the constraints of section 2), `500`,
  `503`. The error catalogue notes register the two `conflict_reason`s and the new
  `validation_failed` constraints (`differs_from_current`, `exceeds_current_revision`,
  `printable`, `minimum`, `required`, `max_length`);
* expected surface after the reseal if D6 stands: 72 paths / 82 operations / 237 schemas (two new
  schemas), 25 error codes, head `0028_classification_corrections` — to be derived from the
  generated contract, never copied from here.

## 7. Migration `0028_classification_corrections` (single owner of the head)

* `document_version_classification_correction (version_uid, revision, project_stage,
  section_code, corrected_by_user_uid, reason, corrected_at)`: primary key `(version_uid,
  revision)`; `version_uid` FK to `document_version_classification(version_uid)` `RESTRICT` (a
  correction presupposes the confirmation); `corrected_by_user_uid` FK to `app_user(user_uid)`
  `RESTRICT`; CHECKs for the identity formats, `revision >= 2`, the two stages, the fifteen codes
  (restated, not imported — `0024`'s habit), `char_length(reason) BETWEEN 1 AND 2000` (restated
  from `MAX_REASON_LENGTH`, held equal by a test) and `reason = btrim(reason, E' \t\r\n')`. The
  letter-or-digit and control-character rules stay in the pure module: a locale-dependent regex in
  a CHECK would be a trap. `corrected_at DEFAULT clock_timestamp()` so revisions order by commit
  under the lock rather than by transaction start.
* `trg_…_immutable` with `am_immutable_row` (UPDATE and DELETE refused, `AM003`) — the same
  guarantee as the original.
* `am_check_classification_correction_chain`, BEFORE INSERT, `AM001`: revision `n` needs revision
  `n-1` (the original for 2, the correction for the rest), and the new pair must differ from it.
  Contiguity and no-op are therefore properties of the table, not only of the command.
* views: `version_classification_revision` (`UNION ALL` of the original as revision 1 with
  `reason NULL`, and the corrections) and `version_classification_current` (the original
  `LEFT JOIN LATERAL` the latest correction by `revision DESC LIMIT 1`; columns `version_uid,
  revision, project_stage, section_code, confirmed_by_user_uid, confirmed_at` of the **current**
  revision — D5). No status or "current" column is stored anywhere.
* `CREATE OR REPLACE FUNCTION am_check_optimisation_pass_scope()` on the current view (5.A row 6).
* `access/references.py`: `("document_version_classification_correction",
  "corrected_by_user_uid", "RESTRICT", …)`, so purging a corrector is `account_referenced`;
  `test_accounts_migration.py` holds the register equal to the schema.
* **No backfill:** the upgrade creates an empty table and views; every existing version's current
  classification equals its original.
* **Downgrade** drops only its own objects, in this order: restores the `0027` body of
  `am_check_optimisation_pass_scope`, drops the two views, the trigger and function, the table.
  It logs how many corrections it drops: those versions revert to their original confirmation (runs
  already routed under a correction keep their pinned profile; optimisation passes stay).
* The schema inventory (columns, relations, constraints, indexes, triggers, functions, views) is
  re-measured from a live database in phase B and the pins are rewritten from the measurement.

## 8. The command (phase B), concurrency and idempotency

`sections.correct_document_version_classification(session, …)` in the caller's transaction:
(1) `get_version_in` — the chain, `404` before anything else; (2) `SELECT … FOR NO KEY UPDATE` on
the original row (a `SELECT … FOR UPDATE` does not fire the immutability trigger; the foreign key
check of the insert takes `FOR KEY SHARE`, which does not conflict); (3) read the whole history
under the lock; (4) `plan_classification_correction`; (5) insert on `append`, answer the stored
revision on `unchanged`. Two concurrent corrections serialise on the lock: the second reads the
first's committed revision and meets rule 8 or 9. The primary key `(version_uid, revision)` and
the chain trigger are the second and third layers (a violation is re-read and answered by the same
rule, as the seal does). A correction racing the very first confirmation sees no row and answers
`version_not_classified`. Run start takes no lock: a start and a correction that overlap are
ordered either way and the run pins what it read — a considered and rejected hardening (a share
lock on the hot path for no reachable inconsistency).

## 9. Failure, idempotency and security cases

| case | behaviour | evidence |
|---|---|---|
| admin alone / no role / unknown role | `403 permission_denied` `role:expert`, nothing read, nothing written | phase A rules 1; phase B HTTP |
| invalid body (stage, section, reason, `expected_revision`) | `422`, field and constraint named | phase A rules 2–4; phase B HTTP |
| foreign project / document / version | `404` before any state is revealed | phase B (as the seal's tests) |
| unclassified version | `409 version_not_classified` | phase A rule 6; phase B |
| exact retry | `201`, the stored revision, one row | phase A rule 8; phase B two-session test |
| concurrent corrections | one wins; the loser `409 classification_revision_stale`; one row each at most | phase A rule 9, simulation; phase B two sessions |
| no-op | `422 differs_from_current` | phase A rule 10; phase B |
| tampering with the history (UPDATE/DELETE, a gap, a no-op row, a foreign actor) | `AM003` / `AM001` from the database | phase B migration test |
| in-flight run during a correction | the run keeps its pinned profile; its stage re-read does not fail | 5.C (phase A); phase B run test |
| purge of a corrector account | `409 account_referenced` | phase B register test |
| LLM / AI | never writes a classification; no raw comparison evidence is touched | by construction: the module has no import beyond the sections catalogue |

## 10. Phase B plan, in order (executed; the result is at the top)

1. merge the commit the integrator names (real merge); `git merge-base --is-ancestor`;
2. `0028` + `access/references.py` + migration tests (upgrade on a populated `0027`, AM003/AM001,
   the round trip down/up, the `GATE-FIX-DB-01` chain test stays green);
3. repository: the repointed selects, `revision`, history, lock, insert; their tests;
4. the command and its two-session test; router, port, adapter, role table;
5. the reseal: contract (`api:generate`), the web mirror byte-identical, `npm --prefix web ci`,
   `api:verify`, `FRONTEND_LOCK.json`, `expected_facts.json`, the pins of 5.E, surface prose with
   the mutation lines of `test_surface_counts_in_prose.py` (not `CURRENT_STATE.md`);
6. repoint the dashboard repository query and the three `documents` queries `SECTION-READ-MODEL-01` added (`list_current_versions_in_section`, `list_unclassified_current_versions`, `count_projects`) to `version_classification_current`, each with a test that fails against the original-only table once a correction exists (re-measured on the merged tree; no separate commit);
7. web: the correction control and the history in the version panel (expert only), the hook and
   the invalidation of 5.D, rendered-language guard, vitest for the changed files, journey
   manifest entry (static conformance);
8. a REAL merge of the newest integration tip, regenerate every artifact, never hand-merge them.

Checks (R-135 bounded, lane containers only, staggered): migration upgrade and round trip,
the repointed suites (documents, dashboard, runs, comparison, optimisation scope),
`tests/contract` (whole directory), `api:verify`, lint, typecheck, changed vitest files,
rendered-language guard, journey conformance. No full gate, no live journey.

## 11. Risks and known limitations

* **A run's pinned profile has no recorded classification revision.** After a correction the
  version screen can show the current classification but cannot say that the latest published run
  was produced under the previous section's profile. Re-audit is the remedy; a
  `audit_run.classification_revision` column (a change to an existing table) is a later decision.
  Until then a comparison of two versions both now in section X can still read a run produced
  under another profile; the comparison rules are unchanged (non-goal).
* **Existing runs are not rewritten** and **nothing is backfilled** (non-goals).
* **A correction changes what the product admits at the next request** (comparison pairs, Form-7
  sets, optimisation passes, run start); written passes, decisions, findings and runs stay.
* **`classifyDocumentVersion` after a correction** is `409` for a retry of the original request
  (D4).
* **The Form-7 section view and the dashboard follow corrections** only once their queries read the current view (phase B step 6); until then a corrected version would still count under its original section.
* **The downgrade is lossy by nature** (it logs the count); it never touches the original rows.

## 12. Hotspot proof

### Phase A

Changed paths: `src/auditmanager/sections/correction.py`, `src/auditmanager/sections/public.py`,
`src/auditmanager/documents/models.py`, `tests/unit/sections/…`, `tests/integration/documents/…`
and this report — all in the first group of allowed paths. Not touched: `contracts/**`,
`db/migrations/**`, the composition root, `web/**`, `access/references.py`,
`pyproject.toml`, `uv.lock`, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, any ref or tag, the stand,
migrations `0001`…`0027`, the stored original confirmations.

## Addendum — after the integrator accepted phase A

The integrator approved D1-D9 as written and changed D10: `SECTION-READ-MODEL-01` is already
merged into the integration branch (`fee74158`; dev `802b3823`). Its dashboard query groups by the
confirmed classification of each document's current version (`D-180` closed there), and the
`documents` context gained the public queries `list_current_versions_in_section`,
`list_unclassified_current_versions` and `count_projects`, used by the section Form-7 view. Phase B
therefore (a) has no separate dashboard-repoint commit, and (b) after the real merge, greps the
merged tree for every `document_version_classification` join again — the list in section 5.A is
the phase A base, not the final inventory — and repoints the dashboard repository query and those
three `documents` queries to `version_classification_current`, with tests. Rows 7 and the step list
above are marked accordingly. Nothing else in this report changes.

## Hotspot proof (phase B)

Checked on the final tree with `git diff --name-only c90d52f3 HEAD` against each forbidden hotspot
of the task file, minus what came in through the two merges of `origin/dev` (documents only).

* dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`,
  `web/package-lock.json`): not touched; `web/FRONTEND_LOCK.json` is the contract's own
  re-derivation, in the task's allowed paths;
* `web/src/_app/providers.tsx` and global styles (`globals.css`): not touched; the two new style
  files are CSS modules of their own components;
* other contexts' internals: `dashboard/repository.py` is changed for one relation name on the
  owner's instruction (the dashboard query is repointed), `comparison/**`, `optimisation/**` and
  `runs/**` are not touched — they read the classification through `documents`;
* the stored original confirmations: `document_version_classification` is read by `0028` and its
  `0024` trigger still refuses UPDATE and DELETE (proved in the migration test, which also tries
  both); no statement of this slice updates or deletes one;
* `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`: not touched by this branch's
  own commits (the register moved only through the integrator's merged commits);
* refs, tags, the stand: no ref or tag was created, nothing was pushed, no stand command ran;
* migrations `0001`…`0027`: not touched (`test_downgrade_chain_round_trip.py` pins their upgrade
  text by digest and passes); this task added `0028` only.
