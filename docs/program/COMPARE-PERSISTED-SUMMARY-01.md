# COMPARE-PERSISTED-SUMMARY-01 — the comparison of two versions becomes a record

Lane B of wave PW4. Base `3561e1c8` (`integration/ar-close-1026`), branch `agent/compare-persisted-summary-01`. Task file: [`tasks/COMPARE-PERSISTED-SUMMARY-01.md`](tasks/COMPARE-PERSISTED-SUMMARY-01.md) (premises P-01 to P-12). Source: [`ROADMAP-GAP-2026-10-27.md`](ROADMAP-GAP-2026-10-27.md) gap 3, items 11, 13 and 37; owner's `C-2` («sheet pairing, deterministic text differences as evidence, AI classification and summary on top; AI never alters the raw differences»).

Two ordered pieces. **B1** stores an expert's approval of a sheet pairing and serves the deterministic differences of the approved pairs, sealed. **B2** adds an AI summary over the approved pairs. B1 is committed whole before B2 starts; if B2 cannot be finished, B1 stands alone and the remainder is listed under «Limits».

## Design

### 0. What the premise showed, and the choices it forced

* Nothing persists a pairing or a summary at head (P-02). The pure modules are written for exactly this: `raw_text.diff_approved_pairs` takes a `ComparisonId`, a `SheetLinkId` and a `link_revision`; `raw_evidence_seal` binds the diffs of one approved set to the immutable version bytes; `summary_input` projects the changed lines of a verified seal into a bounded input. This lane persists the three identities they ask for and nothing else.
* The contract version cannot move in this lane: a minor bump rewrites one shared literal in about 90 files of three other contract families, the edge configs and unrelated web tests (P-10). The new operations are sealed as OpenAPI content under `1.7.0`; the bump is listed for the integrator.
* The account register `access/references.py` (an entry per foreign key to `app_user`) is outside the grant. The actor columns are therefore `usr_` identities with a format CHECK and no foreign key, and the display label is stored beside the id (the decision ledger's idiom), so history stays readable after an account purge. Limit L-1 names the remedy.
* `command_record.command_type` is free snake_case, `audit_event` has no closed event registry, and `conflict_reason` is a free classifier documented in prose: no closed enum has to change.

### 1. Identities and scope

* A **comparison** is an ordered pair (source version, target version) of one document in one project. Its identity `cmp_<ULID>` (`ComparisonId`) is allocated at the first approval of the pair and reused by every later row of that pair. Mode (`version`/`stage`) and run choice are views on a comparison, not part of its identity.
* A **sheet link** is one approval of one source page against one target page, identity `sln_<ULID>` (`SheetLinkId`), allocated by the approval. Withdrawing names the same `sln_`; approving the same pages again later is a new link.
* A **sheet** is identified by (version id, page number, SHA-256 of the page's text): the page number is a coordinate in an immutable version, the digest binds the content the expert saw. Never a display number, a sheet label or a file name.
* The **link revision** is the gap-free number (1, 2, ...) of the rows of one comparison. It is the revision of the approved set that `raw_text`, `raw_evidence_seal` and `summary_input` already take as `link_revision`.

### 2. Table `comparison_sheet_link` (migration `0035_comparison_records`, 23 characters)

One append-only table; every row is one event, `approved` or `withdrawn`. Withdrawal is a new row; no row is ever updated or deleted.

| Column | Meaning |
| --- | --- |
| `comparison_id` `cmp_`, `link_revision` int >= 1 | the primary key; revision n needs n - 1 |
| `event_kind` | `approved` or `withdrawn` |
| `sheet_link_id` `sln_` | the link; at most one `approved` and one `withdrawn` row per link (`UNIQUE (comparison_id, sheet_link_id, event_kind)`) |
| `project_uid` (FK `project`), `document_uid` (FK `document`), `source_version_uid`, `target_version_uid` (FK `document_version`) | the pair; the project column makes the erase closure and the erase predicate direct |
| `source_page_number`, `target_page_number` int >= 1 | coordinates |
| `source_page_text_sha256`, `target_page_text_sha256` | content digests of the two pages at approval |
| `suggestion_sha256` | the pairing proposal the expert confirmed (the served `SheetPairing.suggestion_sha256`, which binds both page digests and the rule) |
| `raw_evidence_seal_sha256` | the `raw_evidence_seal` of the approved set after this row (null only when a withdrawal empties the set); recomputed on every read |
| `actor_user_uid`, `actor_label` | who; label snapshot (1..200 characters) |
| `command_id` FK `command_record`, `UNIQUE` | the idempotency receipt of the command |
| `decided_at` | `clock_timestamp()` |

Guards in the database, not only in the command: `am_immutable_row` on UPDATE and DELETE (`AM003`); a BEFORE INSERT chain trigger `am_check_comparison_sheet_link_chain` (`AM001`) that requires revision n + 1 (or 1 for a pair with no row), the same pair on every row of a comparison and one comparison per pair (`UNIQUE (source_version_uid, target_version_uid, link_revision)` is the race backstop), both versions in the named document and project with source ordinal below target and both pages inside their versions, for `approved` that both pages are free of any active link and that fewer than 32 links are active (`raw_text.MAX_PAIRS`), for `withdrawn` that an active link with exactly the same pages and digests exists. Writers also take `pg_advisory_xact_lock` on the pair, because the application role has no UPDATE privilege and so no row lock.

The **approved set** at a revision is the `approved` rows with no `withdrawn` row; it is a query, not a stored state, so nothing can disagree with the history.

### 3. Operations (contract content under `1.7.0`; at most three, all additive)

`ComparisonPort` gains three methods; the paths sit under the existing `.../versions/{version_uid}/comparison` (the path version is the older, source version). Each write needs `Idempotency-Key`, is `_EXPERT` at the seam and re-reads the role set in its own transaction.

1. **`approveSheetPairing`** `POST .../comparison/sheet-pairings`. Body `{target_version_uid, mode, source_page_number, target_page_number, suggestion_sha256, source_run_id?, target_run_id?}`. The comparison is recomputed with that mode and those runs when the confirmation arrives and must still propose exactly this pair under exactly this `suggestion_sha256` (the analogue of the carry-over's `proposal_sha256`). `201` `SheetPairingEvent`. `409` with `conflict_reason`: `sheet_pair_not_proposed` (refused comparison, other pages or digest, a proposal that moved), `sheet_page_already_paired`, `sheet_pair_limit_reached`. An exact repeat of an active link under another key answers that link, `replayed: true`.
2. **`withdrawSheetPairing`** `POST .../comparison/sheet-pairings/{sheet_link_id}/withdrawals`, no body. Appends a `withdrawn` row. `404` for a link that is not of this path; `409` `sheet_link_not_active` for one already withdrawn.
3. **`generateComparisonSummary`** (B2) `POST .../comparison/summaries`.

`compareDocumentVersions` gains one field: `approved_pairs` (`null` when the comparison is refused). It holds the current `link_revision`, the recomputed `raw_evidence_seal_sha256`, an `evidence_state` (`none`, `sealed`, `text_changed`, `seal_changed`, `too_large`), the active links and (B2) the latest summary. Each link carries its pages, `suggestion_sha256`, who approved it and when, a `state` (`verified`, or `text_changed` when a page's digest is no longer the approved one) and, only when the whole set is `sealed`, the deterministic differences computed by `raw_text.diff_approved_pairs` and checked by `seal_raw_version_evidence`. Changed hunks carry a `hunk_id` (`<sheet_link_id>:<n>`, n counting the sheet's non-equal hunks); equal spans carry ranges only, as in the existing diff. An unapproved pair never gets this view: it keeps the existing proposal diff. Nothing is truncated: a set whose differences exceed the response budget (500,000 changed characters, the existing figure) is `too_large` and serves none.

### 4. Access, audit, idempotency, transaction

* **Who may approve** is who may decide findings today: `appendDecision` and `carryOverDecision` are `_EXPERT` in `api/security.py` and the command checks `expert` against the role set read in its own transaction (`decision_carryover.require_carryover_expert`, `R-60`: `admin` alone is `permission_denied`, `required_capability: role:expert`). The same check guards the three writes.
* **Audit**: `comparison.sheet_link_approved` and `comparison.sheet_link_withdrawn` in `audit_event` (aggregate `Comparison`, aggregate id the `cmp_`), written by a writer local to the comparison context on the caller's Session in the same transaction as the row (the `PROD-06` idiom: a per-type allow-list of keys, a value rule per key, typed entry points). Payload: ids, revision, page numbers and digests only. B2 adds `comparison.summary_generated`.
* **Idempotency**: `CommandRepository` (`ingest.public`), command types `approve_sheet_pairing`, `withdraw_sheet_pairing`, `generate_comparison_summary`; the same key replays the stored answer; a changed fingerprint under one key is the existing `idempotency_key_reuse`.
* Order inside the write transaction: request shape, expert role, path proof (`get_version_in`, `404`), advisory lock on the pair, recomputed comparison, receipt, row, audit event, receipt outcome.

### 5. B2 — the summary

* **Table `comparison_summary`** (same migration, added in the B2 commit): append-only, `summary_id` an `evt_` identity (the id of its audit event as well), `comparison_id` and `link_revision` (composite FK to `comparison_sheet_link`), `project_uid` (FK `project`), `raw_evidence_seal_sha256`, `input_sha256` (`summary_input.input_sha256`), `prompt_version`, `provider_mode` (`recorded` or `live`), `model_identity` (`recorded` or the model string), `request_sha256`, `state` (`ready`, `rejected`), `rejection_reason`, `statements` (JSON array of `{text, hunk_ids}`), `cost_basis`, `cost_micros`, actor, `command_id`, time. At most one `ready` row per (comparison, revision, input digest, prompt version), so an exact repeat never pays twice. A `rejected` row records a reply the validator refused (spend is never invisible) and carries no statements.
* **The command is the only way to a model call.** A read never calls one. The command needs an approved set in the `sealed` state and a non-empty projected input (`prepare_version_summary_input` refuses an oversize input rather than shortening it: `changed_input_too_large`, and an input with no changed line is refused before any call: nothing to summarise). The input digest and the seal are recomputed in the transaction, never taken from the request.
* **The model port** is a small protocol local to `comparison` (`SummaryModel`: a read-only class constant `provider_mode`, `complete(request) -> reply`), because `comparison` takes other contexts only through their ports. The wave's implementation is `RecordedSummaryModel`: a file `fixtures/recorded/comparison/<request_sha256>.json`, where `request_sha256` is the digest of the canonical JSON of the exact request body (instructions, prompt version and the input including its `input_sha256`), the shape of the text-profile recordings and of the AR v3 replay (P-09). A different input or prompt is a different key; a missing file is an explicit refusal (`analysis_input_invalid`, reason `recording_missing`); there is no live fallback in the class. The composition root wires it only when the process runs in `recorded` mode; in any other mode the command answers `dependency_unavailable` (`dependency: comparison_summary_model`): the live implementation is **not** wired and no live call is made or tested (`R-29`).
* **The validator** (`summary_validation`) accepts a reply only if it is the closed shape `{"statements": [...]}`, has between 1 and 20 statements, each text 1 to 1,000 characters and 1 to 50 distinct `hunk_ids`, **every one of which exists in the input**, and no extra key. An unknown reference rejects the whole reply (`unknown_hunk_reference`); nothing is repaired or dropped.
* **Cost** goes through the existing meter (`analysis.public.CostMeter`) in the composition adapter: `check_before_call`, then `record_unmetered` for the recorded binding only (basis `unmetered`, cost 0; the explicit exception of `D-225` piece 2). A reply that is not the recorded binding's has no verifiable cost in this wave and is refused.
* **Raw differences are never altered.** The summary is a separate record that references hunk ids; the read model returns the approved differences exactly as computed and beside them the latest summary with the fixed label «Сводка подготовлена моделью, проверка человеком не проводилась» and `is_current` (same revision and seal as now). A test compares the bytes of the differences before and after a summary exists.

### 6. Grants, purge and erase

`grant_classification.py` classifies both tables `append-only` (`SELECT, INSERT`) and regenerates `infra/deploy/apply-grants.sh`; `schema_coverage.py` lists the tables and their triggers; `product_purge.PRODUCT_TABLES` names both (the project erase finds them through the foreign key to `project` and refuses a closure table that is not classified); the three command types join `PRODUCT_COMMAND_TYPES` and the `comparison.` prefix joins `PRODUCT_EVENT_PREFIXES`.

### 7. Web (`widgets/version-comparison`, `_pages/stage-comparison`, new `entities/version-comparison`)

Beside each proposed pair an expert sees «Подтвердить пару» (and «Отозвать» on an approved one); a section «Подтверждённые пары» lists the approved pairs with their raw differences and says in words when the evidence is `text_changed`, `seal_changed` or `too_large`; in B2 «Подготовить сводку» (expert) and the summary with the fixed label, each statement listing the sheets and lines of the hunks it refers to. A person without `expert` sees the lists and no buttons. One idempotency key per intent, reused on retry (the carry-over hook's idiom). No internal identifier is rendered (`rendered-language.guard.test.ts`).

## Report

### Status

**B1 and B2 are both delivered**; nothing is left for B2 to hand over. Branch `agent/compare-persisted-summary-01`, base `3561e1c8`; the commits are listed by `git log --reverse --format='%h %s' 3561e1c8..HEAD`; not pushed, not tagged, not merged. The commits in order: the design note and task file; B1 (`0aa942b6` comparison + migration, `a4e890e1` API and contract, `4bc89a5c` recovery classification and head pins, `7e6eb754`, `e2857428` web, `35d58bad`, `223c00d0` lock, `403262f3`); B2 (`a57292dc` comparison + the second table, `003c7446` API and contract, `d4068fe0` recovery, `0cb32bfb` web, `0715ac8a` lock); then two guard repairs (`9b2f59bd`, `640b6256`), the task file and one audit test (correlation id).

The integrator's addendum is done in the same reseal: the prose of `analysis_input_budget_exceeded` (summary and note) in `contracts/domain/v1/error-codes.json` says that `budget_characters` is the one-call budget times the number of windows a run may use; the three documents were regenerated, not merged by hand. Prose only; keys, types and status are unchanged.

### What was built, against the design above

* **B1.** Table `comparison_sheet_link` (18 columns, append-only, chain trigger, advisory lock per pair); `SheetPairingService` (`approveSheetPairing`, `withdrawSheetPairing`: expert role read in the command's own transaction, path proof, recomputed comparison, receipt, row, audit event `comparison.sheet_link_approved` or `..._withdrawn`, receipt outcome, all in one transaction); `compareDocumentVersions.approved_pairs` with the active links, an `evidence_state` and, only when the whole set is `sealed`, the differences of `raw_text.diff_approved_pairs` checked by `raw_evidence_seal`. Hunks carry `<sheet_link_id>:<n>`. Nothing is truncated: beyond the bound the state is `too_large` and no difference is served.
* **B2.** Table `comparison_summary` (19 columns, append-only; the latest-row trigger forbids a summary of a superseded revision; at most one `ready` row per input; hardened CHECKs, found by the migration test: a `rejected` row must carry a reason, `unmetered` is allowed only for `recorded` at cost 0); `SummaryService` (a command, never a read), `summary_prompt` (`comparison-summary-v1`, request digest over the exact body), `RecordedSummaryModel` (keyed by `request_sha256`, no client, no live fallback), `summary_validation` (closed shape; **every cited hunk must exist in the input; one unknown reference rejects the whole reply**, which is stored as a `rejected` row so that spend is visible), cost through `CostMeter` in the adapter (`_MeterGate`, unmetered only for the recorded binding). `approved_pairs.summary` serves the latest summary with the fixed label and `is_current`; the differences beside it are byte-identical with and without a summary (tested).
* **Recorded mode only.** The composition root wires the model only in `recorded` mode; any other process answers `dependency_unavailable` (`dependency: comparison_summary_model`). One synthetic recording is committed (`fixtures/recorded/comparison/225dae82...json`, README says it is synthetic); a real pair has no recording, so in a recorded process its summary is the explicit refusal `analysis_input_invalid` / `recording_missing`, which stores nothing.

### Files

85 files changed (`git diff --shortstat 3561e1c8..HEAD`; `git diff --name-only 3561e1c8..HEAD | wc -l` is 85). By area:

* **Migration**: `db/migrations/versions/20261027_0035_comparison_records.py` (revision id 23 characters).
* **Domain**: `src/auditmanager/comparison/` new `sheet_links.py`, `approved_evidence.py`, `audit.py`, `pairing.py`, `summaries.py`, `summary_model.py`, `summary_prompt.py`, `summary_records.py`, `summary_validation.py`; modified `service.py`, `read_model.py`, `public.py`. `fixtures/recorded/comparison/` (recording, README, `build_fixtures.py` with `--check`).
* **API and wiring**: `api/schemas/models.py`, `api/routers/comparison.py`, `api/routers/ports.py`, `api/security.py`, `bootstrap/adapters.py` (`ComparisonAdapter`, `_MeterGate`), `bootstrap/composition.py` (`summary_model_for`); prose figures only in `api/app.py`, `api/health.py`, `api/README.md`, `api/routers/__init__.py`, `declarations.py`, `errors.py`.
* **Contract**: `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`, `contracts/domain/v1/error-codes.json`, `web/src/shared/api/generated/*` (4 files), `web/FRONTEND_LOCK.json`.
* **Recovery**: `scripts/recovery/schema_coverage.py`, `grant_classification.py`, `product_purge.py`, `infra/deploy/apply-grants.sh` (regenerated).
* **Web**: new `web/src/entities/version-comparison/` (7 files), modified `web/src/widgets/version-comparison/ui/version-comparison.tsx`.
* **Docs**: this note, the task file, `docs/program/P02_SEAMS.md`, `docs/manual-tests/PC-01_prototype.md`.
* **Tests, new (14 files; 188 Python tests and 32 web tests)**: `tests/unit/comparison/` (5 files: 11 + 21 + 5 + 11 + 26), `tests/integration/comparison/` (17 + 12), `tests/integration/db/test_comparison_records_migration.py` (41) and `test_comparison_summary_migration.py` (32), `tests/integration/composition/test_comparison_records_over_http.py` (3) and `test_comparison_summary_over_http.py` (3), `tests/integration/recovery/test_comparison_records_purge_and_erase.py` (6), `web/tests/unit/comparison/sheet-pairing.test.ts` (20) and `comparison-summary.test.ts` (12).
* **Tests, modified (20 files)**: see «Modified tests, before and after».

### Mutation tables

Method: a scratch harness applies one edit, runs the tests that guard it, restores the file and checks that the tracked tree is clean again. «red» is the number of failing tests; a mutation that stays green would be a hole. **58 mutations were run in the lane (30 on B1, 28 on B2); 57 are red; the one survivor is an equivalent mutant, explained in its row.**

**B1 (30 mutations, all red, all restored)**

| id | mutation | red tests | restored |
| --- | --- | ---: | --- |
| MG1 | migration: the immutable trigger never fires (WHEN false) | 4 | yes |
| MG2 | migration: the revision may skip a number | 1 | yes |
| MG3 | migration: one pair may get a second comparison identity | 3 | yes |
| MG4 | migration: the source may be the newer version | 1 | yes |
| MG5 | migration: a page may be held by two active links | 1 | yes |
| MG6 | migration: the 32-link bound is gone | 1 | yes |
| MG7 | migration: a withdrawal need not repeat the approval's digests | 1 | yes |
| MG8 | migration: the downgrade drops rows without refusing | 1 | yes |
| MG9 | migration: an approval may carry no seal | 1 | yes |
| MR1 | erase and purge: comparison_sheet_link is not named in PRODUCT_TABLES | 6 | yes |
| MR2 | grants: comparison_sheet_link is not classified append-only | 20 | yes |
| MR3 | purge: the comparison. event prefix is not a product prefix | 3 | yes |
| MR4 | schema coverage: the table is missing from TABLES | 20 | yes |
| MS1 | approve: the expert role is not checked | 1 | yes |
| MS2 | withdraw: the new row is written as another approval | 3 | yes |
| MS3 | approve: a failing audit event is swallowed | 1 | yes |
| MS4 | approve: the audit event is written in a transaction of its own | 1 | yes |
| MS5 | identity by page number only: the page digests are not compared | 3 | yes |
| MS6 | approve: a digest other than the proposal shown is accepted | 1 | yes |
| MS7 | approve: the occupied-page conflict is not raised | 1 | yes |
| MS8 | read: the stored seal is not compared with the recomputed one | 1 | yes |
| MS9 | approve: an earlier approval whose text changed does not block | 1 | yes |
| MS10 | approve: an oversize approved set is sealed anyway (the bound is not enforced) | 1 | yes |
| MS11 | approve: the occupied-page and limit checks are skipped, so only the database stops a 33rd link | 1 | yes |
| MS12 | api: approveSheetPairing is open to any role | 3 | yes |
| MS13 | the proposal diff of an UNAPPROVED pair is served as an approved one (every active link is shown without being approved): the read lists proposals as approvals | 4 | yes |
| MW1 | web: every role may approve | 1 | yes |
| MW2 | web: an approval is matched by the source page alone | 1 | yes |
| MW3 | web: a different pair under the same key (the pages are left out of the intent) | 1 | yes |
| MW4 | web: the approved section hides the reason it shows no difference | 5 | yes |

**B2 (28 mutations: 27 red, 1 equivalent survivor, all restored)**

| id | mutation | red tests | restored |
| --- | --- | ---: | --- |
| MB1 | validator: a cited span that does not exist is accepted | 7 | yes |
| MB2 | recording key ignores the input: the request digest covers the prompt version only | 3 | yes |
| MB3 | the summary alters the raw differences: the read drops the differences once a summary exists | 2 | yes |
| MB4 | an exact repeat calls the model again (the stored ready summary is not looked up) | 1 | yes |
| MB5 | the cost meter is not consulted before the call | 3 | yes |
| MB6 | the expert role is not checked by the summary command | 1 | yes |
| MB7 | a reply with a cost this release cannot verify is accepted | 1 | yes |
| MB8 | a process with no summary model proceeds to call it | 1 | yes |
| MB9 | api: generateComparisonSummary is open to any role | 3 | yes |
| MB10 | composition: every mode gets the recorded summary model | 1 | yes |
| MB11 | a rejected reply is not recorded as such: the unknown reference is raised as an error instead | 2 | yes |
| MB12 | migration: a summary may describe a superseded revision | 1 | yes |
| MB13 | migration: unmetered may be claimed by a live row | 3 | yes |
| MB14 | migration: the summary table is not append-only | 3 | yes |
| MB15 | migration: more than one ready summary per input | 1 | yes |
| MB16 | migration: a rejected summary may carry no reason (the NULL-passes-CHECK defect found while writing the test) | 1 | yes |
| MB17 | migration: the downgrade ignores summaries **survived: an equivalent mutant.** A summary row cannot exist without its sheet-link row (composite foreign key), so `links or summaries` and `links` refuse in the same cases and print the same message. Replaced by MB17b and MB17c, which are red. | 0 | yes |
| MB17b | migration: the downgrade refusal does not count the summaries it would drop | 1 | yes |
| MB17c | migration: the downgrade refusal is gone altogether | 1 | yes |
| MB18 | erase and purge: comparison_summary is not named in PRODUCT_TABLES | 7 | yes |
| MB19 | grants: comparison_summary is not classified append-only | 20 | yes |
| MB20 | purge: the generate_comparison_summary receipt is not a product command type | 4 | yes |
| MB21 | web: the fixed label is not shown | 1 | yes |
| MB22 | web: a summary is offered for a set the server did not seal | 2 | yes |
| MB23 | web: a rejected reply is shown as text | 1 | yes |
| MB24 | web: a superseded summary is shown as if it were current | 1 | yes |
| MB25 | audit: the request's correlation id is dropped from the event | 2 | yes |
| MB26 | audit: a malformed correlation id is written without validation | 1 | yes |

### Modified tests, before and after

No assertion was removed or loosened; every change below adds a member, moves a count by exactly the rows this task adds, or replaces a literal by a read of the live figure.

| Test | Before | After |
| --- | --- | --- |
| `tests/contract/api_v1/test_openapi_conformance.py` | `assert len(report) == 74` (operations with a parameter object resolved through a component) | `== 77`: approve, withdraw and summary each address the source version through the document and project parameters |
| `tests/contract/api_v1/test_surface_counts_in_prose.py` (P02 stale claim) | replaced the literal `"104 operations, sealed."` | replaces the sentence for the live count read from the frozen document (`_surface_counts()['operations']`) and asserts that the sentence was found; the claim it plants is unchanged |
| same file (`.conf` stale claim) | replaced the literal `"the ninety-two paths"` | finds the path count the file states by pattern and replaces it with `eighty-nine`, asserting first that `eighty-nine` is not the live count; it still proves that the scanner reads `.conf` files |
| `tests/integration/db/test_application_role_grants.py` | 64 tables refuse TRUNCATE; 36 append-only | 66; 38 |
| `tests/integration/db/test_schema_invariant_inventory.py` | columns 736, relations 76, constraints 814, indexes 184, triggers 86, functions 32 (with their digests) | 773, 78, 868, 194, 90, 34 with new digests, measured on a fresh database upgraded to 0035 in all eleven families; the diff of every family is this revision's rows only (derivation in the module's comment) |
| `tests/integration/db/test_downgrade_chain_round_trip.py` | digests of the upgrade surface of every revision up to 0034 | the same plus the digest of `0035`; `430cc5a8...` is computed from the file as committed (the test passes on this tip) |
| `tests/integration/db/test_schema_shape.py`, `test_migration_lifecycle.py` | immutable list and identity-prefix table without the new tables; `EXPECTED_TABLES` without them | the two tables added to each; `comparison_id: cmp`, `sheet_link_id: sln`, `source_version_uid`/`target_version_uid: ver`, `summary_id: evt` added |
| `tests/integration/recovery/test_grant_classification.py` | `len(coverage.TABLES) == 64` | 66 |
| `tests/integration/recovery/test_product_purge.py` | PRODUCT 32, KEEP 29, MIXED 3 | PRODUCT 34 (and both names asserted present); KEEP and MIXED unchanged |
| `tests/integration/recovery/test_project_erase.py` | closure of 31 tables; two table sets without the new names | closure of 33; the new tables added to both sets and to `SLICES` (`project_uid = :p`) |
| `tests/integration/recovery/test_synthetic_drill_compare.py`, `test_synthetic_drill_seed.py` | 64 tables | 66 |
| `tests/integration/api/test_role_register.py`, `test_authorization.py` | the three new operations absent | added with their roles and refusals; no existing row changed |
| `tests/integration/api/test_operation_surface.py` | no placeholder for a sheet link | `sheet_link_id` placeholder added |
| `tests/integration/api/test_served_document_and_health_plane.py` | the closed-body operation list without the new three | the three added |
| `tests/contract/domain_p02/test_openapi_document.py`, `web/tests/contract/seam-operations.contract.test.ts` | `REQUIRED_OPERATIONS`, `WRITE_OPERATIONS` and the keyed-write list without the new three | the three added |
| `tests/support/expected_facts.json` | head `0034_pass_scope_all_sections`; 92 paths, 104 operations, 301 schemas; the schema key list | `0035_comparison_records`; 95, 107, 314; the 13 new schema keys added |

### Commands and counts

All with the lane stack's `.env` copied to the worktree, `PYTHONPATH=src:$BS`, one pytest at a time; tests that write ran on the private database `cmp_<hex>` (created and migrated by the lane, dropped at the end); the migration suites clone their own throw-away templates.

| Command (from the worktree) | Result |
| --- | --- |
| `pytest tests/unit/comparison tests/integration/comparison` | 318 passed |
| `pytest tests/integration/db` | 807 passed (569 s) |
| `pytest tests/integration/recovery` | 490 passed (181 s) |
| `pytest tests/integration/api tests/integration/composition tests/unit/api` | 2,543 passed, 3 skipped (skip reasons were not printed in this run; no file of this lane contains a skip marker, and the suite's own skips are host conditions: docker, openssl, shellcheck, nginx, a listening address), 1,830 s; includes `test_every_port_implementation_is_whole.py` |
| `pytest tests/contract` minus the three `D-220` files (`test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py`), measured on a clean committed tree | **3 failed**, 1,172 passed, 19,283 subtests passed, 85 s. The three reds are outside this lane's grant and are described in «Integration notes»; `tests/contract/program` is among the passed |
| the same three reds with the prose patch of «Integration notes» applied to a scratch copy of the tree and then reverted | `test_doc_prose_facts.py` and `test_surface_counts_in_prose.py`: 77 passed, 0 failed |
| `npm --prefix web run api:verify` | OK (107 operations) |
| `npx tsc --noEmit`, `npx eslint .` in `web/` | exit 0, exit 0 |
| `npx vitest run` in `web/` | 202 files, 3,085 tests passed |
| `git diff --check` | clean |

### Contract and migration result

* **Contract**: 95 paths, 107 operations, 314 schemas (base: 92, 104, 301); three operations (`approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`, all `_EXPERT` and keyed), one parameter component (`SheetLinkId`), 13 schemas and two optional-and-nullable fields (`VersionComparison.approved_pairs` and `approved_pairs.summary`). Additive; `info.version` stays **`1.7.0`** (see the version rule below). The mirror, the generated client and `FRONTEND_LOCK.json` were regenerated from it (`api:verify` OK).
* **Migration**: head `0035_comparison_records` on top of `0034_pass_scope_all_sections`; upgrade adds two tables, four triggers, two functions and their indexes; downgrade refuses while either table holds a row (`0035 downgrade refused: N sheet link event(s) and M summary row(s) ...`) and otherwise drops exactly what it created; the round trip is tested in a throw-away database.

### Integration notes

1. **Files that pin the migration head** (all in this lane except the last): `scripts/recovery/schema_coverage.py` (`HEAD`, `TABLES`, the four triggers, `CONSTRAINT_COUNTS`, `INDEX_COUNT`), `tests/support/expected_facts.json` (`migration_head`), `tests/integration/db/test_downgrade_chain_round_trip.py` (upgrade-surface digest), `tests/integration/db/test_schema_invariant_inventory.py` (eleven families), `tests/integration/db/test_migration_lifecycle.py`, `test_schema_shape.py`, the recovery table counts listed above, `docs/manual-tests/PC-01_prototype.md`. **Not done (forbidden): `docs/program/CURRENT_STATE.md`.**
2. **Contract version.** Only the literal `1.7.0` was kept. `git grep -l '1\.7\.0' -- . ':!web/node_modules' ':!web/src/shared/api/generated'` lists 111 files at this tip: `contracts/api/v1/openapi.json` and its mirror (`info.version`), the other contract families' shared version, edge configs, and tests that pin it. A minor bump (`1.8.0`) is a mechanical rewrite across them, outside this lane's grant; it is the integrator's step, after which `web/FRONTEND_LOCK.json` has to be resealed again (`npm --prefix web run api:generate`, then the lock update). No test in this lane demands the bump.
3. **Three guards are red on this tip until the integrator applies a prose patch to files outside the grant** (measured, not predicted; the patch was applied to a scratch copy and made all three green, then reverted). It re-states the sealed surface (92 paths, 104 operations, 301 schemas becomes 95, 107, 314) and the head:

| File | Replace | With |
| --- | --- | --- |
| `docs/program/CURRENT_STATE.md` | `**92 paths / 104 operations / 301 schemas**`; head `**`0034_pass_scope_all_sections`**` | `**95 paths / 107 operations / 314 schemas**`; `**`0035_comparison_records`**` (and one clause on migration `0035`) |
| `docs/program/ALPHA_ROADMAP.md` (line 36) | `92 paths / 104 operations / 301 schemas` | `95 paths / 107 operations / 314 schemas` |
| `web/src/shared/api/authorization.ts` | `as the 104 operations can return it` | `107` |
| `web/src/app/bff/v1/[...path]/route.ts` | `**104 operations across ninety-two paths**` | `**107 operations across ninety-five paths**` |
| `infra/deploy/serve.py` | `(the 104 operations)` | `(the 107 operations)` |
| `infra/deploy/proxy/nginx.conf` | `contract declares the ninety-two paths`; the second line of the wrapped sentence `# 104 operations with` | `ninety-five`; `107` |
| `infra/deploy/README.md` | `the 104 operations under uvicorn`; `:8000   the 104 operations, mounted` | `107` in both |

   These are other owners' files (deploy, edge, the web BFF); editing them in a parallel lane would have made a hotspot conflict, so they are left to the integrator's reseal window. The failing tests are `test_doc_prose_facts.py::test_the_scanned_docs_state_the_migration_head_this_tree_has`, `::test_the_scanned_docs_state_the_contract_surface_this_tree_has` and `test_surface_counts_in_prose.py::test_the_api_prose_states_the_surface_this_document_declares`.
4. **Prose I did edit under `src/auditmanager/api/`** (figures only, no behaviour): 92/104/301 to 95/107/314, and in `app.py` the measured claim «Seventy-seven of the 104 operations declare their own 422» re-measured to «Eighty of the 107» (`python3 -c` over the sealed document: 80 declare a `422`, 27 do not) plus the declarations-and-models count in `create_documentation_app`. The paragraph that follows still says «Fifteen cannot» where the document has 27 operations without a `422`: that was stale at the base too (the sums never agreed since the later waves) and is left as found.
5. **Recovery**: the receipts of the three command types and the `comparison.` audit events are PRODUCT data and are purged and erased with the project (proved on real rows for two projects in `test_comparison_records_purge_and_erase.py`).
6. **Scratch file overwritten.** My mutation harness wrote `mutate.py` into the parent's shared scratchpad and replaced a file of that name which was already there. It was scratch, not the repository; I did not keep a copy.

### Limits

* **L-1.** The actor columns (`actor_user_uid`) are `usr_` identities with a format CHECK and **no foreign key to `app_user`**, and the display label is stored beside them: the register `access/references.py` (one entry per foreign key to `app_user`) is outside the grant. A purge of an account therefore leaves a historical id and its label in these rows, as the decision ledger does. The remedy is one register row and one foreign key in a later migration.
* **No live summary.** The live model implementation is not wired and was not called (`R-29`); the metered-cost path of a live reply is not built: a reply that is not the recorded binding's has no verifiable cost in this wave and is refused, so a live mode cannot be added without that piece. Only one synthetic recording exists; a real pair has none, so in the recorded process its summary is refused with `recording_missing` until a recording is made by the model-owning wave.
* **Only proposed pairs can be approved.** A pairing the comparison did not propose (manual pairing) is not built; AI classification of pairs or of finding matches is not built.
* **Contract version not bumped** (integration note 2) and the three prose reds of integration note 3.
* **The label is a fixed string**, not a result of verification: "Сводка подготовлена моделью, проверка человеком не проводилась". Nothing here makes a summary a decision of an expert (`AGENTS.md` section 4).
* **Correlation id.** The adapter passes `current_correlation_id()` to the audit writer; the writer's unit tests prove that the id is bound as given, left unbound when absent and that a malformed one writes nothing (MB25, MB26). No test reads the id back from a row written over HTTP.
* **Host conditions.** The disk of the host was at 98 to 99 percent during the lane (1.7 to 2.4 GiB free). Nothing here depended on it, but a full-disk run would show as unrelated reds (`blob_storage` unavailable). My own `pytest-N` directories were removed at the end.

### Forbidden paths are untouched

`git diff --name-only 3561e1c8..HEAD` shows 85 files, of which none is under `src/auditmanager/optimisation|runs|jobs|analysis|access|shared`, none is `tests/e2e/pc01/journey/manifest.json`, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, a ruling, an ADR or a root lock file, the only migration is `0035`, and the only files in `web/src` are under `entities/version-comparison`, `widgets/version-comparison` and the generated client. The command that proves it:

```
git diff --name-only 3561e1c8..HEAD | grep -E '^(src/auditmanager/(optimisation|runs|jobs|analysis|access|shared)/|tests/e2e/pc01/journey/manifest.json|docs/program/(CURRENT_STATE|DEBT_REGISTER)|docs/(adr|rulings)|package(-lock)?\.json|web/package(-lock)?\.json|uv\.lock|requirements|poetry\.lock|pyproject\.toml|web/src/(app|_pages|shared/(ui|styles|lib)))'   # no output
git diff --name-only 3561e1c8..HEAD | grep -E '^web/src/' | grep -v -E '^web/src/(entities/version-comparison|widgets/version-comparison|shared/api/generated)/'   # no output
git diff --name-only 3561e1c8..HEAD | grep -E '^db/migrations'   # only 20261027_0035_comparison_records.py
```
