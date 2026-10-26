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

Filled in at the end of the lane: files, mutation table, before/after of every modified test, commands with counts, integration notes, limits and proof that forbidden paths are untouched.
