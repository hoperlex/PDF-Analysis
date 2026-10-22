# BETA-CONTRACT-SEAL-01 report — the contract sealed at `1.0.0` (B9)

Task: [`tasks/BETA-CONTRACT-SEAL-01.md`](tasks/BETA-CONTRACT-SEAL-01.md). Lane branch
`agent/beta-contract-seal-01`. Phase A tip `d9afc6f3` (on `2161d505`), real merge of `origin/dev`
`3c62533b` as `c7d5f483`, phase B tip `c957e7d9`, merged into `origin/dev` by the integrator as
`49e43980`; this report was written on `origin/dev` `2affede8`. `contract_version` is `1.0.0`
everywhere it is declared and served, the domain error catalogue is `frozen` with 27 codes, and the
two run-start routing refusals of `D-179` have codes of their own. Nothing else about behaviour
moved.

## 1. Numbers after the seal

| Fact | Before | After |
|---|---|---|
| `contract_version` (API `info.version`, `ErrorEnvelope` const, domain, analysis, events, `getProductVersion`) | `1.0.0-draft.1` | **`1.0.0`** |
| Domain catalogs `status` / `frozen` / `supersedes` / `candidate_revision` | `draft_candidate` / `false` / `1.0.0-draft.0` / 17 | **`frozen` / `true` / `1.0.0-draft.1` / 19** (18 was phase A) |
| API surface (paths / operations / component schemas) | 73 / 83 / 242 | 73 / 83 / 242 (unchanged) |
| Error catalogue / enum | 25 codes | **27 codes** (`version_classification_required`, `section_profile_unavailable`) |
| Stored vocabulary (`expected_facts.error_catalog.stored_vocabulary`) | 23 | **25** |
| Migration head | `0028_classification_corrections` | **`0029_routing_refusal_codes`** |
| `expected_facts` | `api_codes` 25, `stored_vocabulary` 23, head 0028, `1.0.0-draft.1` | 27, 25, `0029_routing_refusal_codes`, `1.0.0` |
| `pin_sweep contract-version` | 67 consumer paths | 69 paths (the two added are the seal's own tests); none declares the old literal as its own version |

`python3 tools/plan/pin_sweep.py contract-version`: exit 0 before and after. After the seal the
literal `1.0.0-draft.1` remains only where it is a statement about history: `supersedes` pins in the
domain schemas and catalogs, the READMEs' version-line prose, the new seal test and the
characterization move test (which name the draft on purpose), the `FRONTEND_LOCK.json` note, and
the quarantined `tests/contract/test_cp00_candidate.py` (below).

## 2. Phase A — dedicated codes for the two refusals (`D-179`)

| Code | HTTP | `retryable` | Category | Detail keys | Replaces |
|---|---|---|---|---|---|
| `version_classification_required` | 422 | false | `policy` | none | `required_norm_unavailable` + `reference_kind: version_classification` |
| `section_profile_unavailable` | 422 | false | `dependency` | none | `required_norm_unavailable` + `reference_kind: analysis_profile` (no `analysis_profile_id`) |

Both keep the status and the retry rule of the code they replace. They are answered by `startRun` and
`reauditRun` before the idempotency key is claimed, so nothing is written. An old client that read
`required_norm_unavailable` for these two cases reads the new codes: a changed behaviour of a draft
contract, documented in the catalogue notes, the OpenAPI `startRun`/`reauditRun` text, the domain
README (revision 18) and `P02_SEAMS.md`.

**One decision for the integrator to confirm.** The executor's refusal of a run's *pinned* profile pair
that the deployment does not register (`runs/executor.py::_pinned_text_profile`) is also
`reference_kind: analysis_profile`, but it carries `analysis_profile_id` and `prompt_bundle_id`, is raised
by the worker on a run that already exists, and is exactly what `required_norm_unavailable` says
("an AnalysisProfile cannot be resolved to an immutable versioned record"). It stays
`required_norm_unavailable`; the catalogue note says so. Moving it would change a stored run's
`terminal_reason` and is outside "the two run-start refusals".

Migration `0029_routing_refusal_codes` replaces the four stored-error `CHECK`s
(`command_record.error_code`, `audit_run.terminal_reason`, `model_call.error_code`,
`provider_call_effect.error_code`) with the 25 stored codes. Both refusals write nothing today; the
vocabulary admits them so no later path needs a second widening. The downgrade refuses while any of the
four columns holds a new code and otherwise restores `0022`'s constraints exactly. The inventory test
`test_schema_invariant_inventory` was resealed only after measuring: two fresh databases at `0028` and
`0029` differ in one family (constraints: 657 rows both, four rows redefined, each by exactly the two
quoted codes); every other family is identical.

Web: `catalog-message`, `terminal-reason` (Russian sentences), `routing-refusal` keyed on the code (the
`reference_kind` reading is gone and a test keeps it gone), `PC01_ERROR_CODES` (derived: the two codes are
named in the 422 `RunInputInvalid` description), two `CACHE_STATES` in the rendered-language guard that
render the new terminal-reason sentences.

## 3. Phase B — the seal

- `1.0.0` in: `contracts/api/v1/openapi.json` (`info.version`, `ErrorEnvelope` const) and the
  byte-identical `web/openapi/openapi.json`; `contracts/domain/v1/{error-codes,identifiers,state-machines}.json`
  and their schemas, `error-envelope.schema.json`, both examples; all of `contracts/analysis/v1` (12 files +
  examples) and `contracts/events/v1`; `src/auditmanager/api/routers/__init__.py`, `api/schemas/models.py`
  (`ErrorEnvelope.contract_version`), `analysis/engine/result.py`; the edge's `429` and `401` bodies in
  `infra/deploy/proxy/nginx.conf` and `tls-server.conf`; `web/src/shared/api/credentialed-forward.ts`; the
  generated client (`api:generate`) and `FRONTEND_LOCK.json` (re-derived by recomputing every digest, not
  edited by hand); `tests/support/expected_facts.json`; 47 test files that carried the literal.
- The domain schemas pin `status` to `const "frozen"`, `frozen` to `const true`, `supersedes` to
  `1.0.0-draft.1`, `candidate_revision` to 19, so a catalog that fell back to a draft fails its own schema.
- `OPEN-RETENTION` (`U-04`) stays `not_decided`; the catalogue states that the freeze declares no retention
  window. A test fails if a number of days or hours appears in it.
- `rate_limited` note and `issueToken`'s description name the credential exchange the edge throttles since
  `HARDEN-AUTH-EDGE-01` (integrator instruction); the registration operations' own text was already correct.
- Prose: `D-151` (OpenAPI: "Reading product data needs an active account with a complete profile **and at
  least one role** (`R-80`)"; `P02_SEAMS.md` likewise) and `D-161` (rule 1 now carves out the portal's
  external `blk_` identity) are closed. The two "reserved `contracts/optimization/v1` family" sentences of the
  W60 paragraphs now say no such family exists. A "Sealed" paragraph ends `info.description`.
- Characterization: the sixteen error records of `tests/characterization/w13_baseline` moved by exactly the
  `contract_version` value and a body `length` eight shorter; `capture.py` was not run. See the README
  amendment and `test_the_sixteen_error_records_moved_by_the_contract_version_and_nothing_else`, which puts
  the draft version back and requires each body to equal the capture at `c7d5f483` digest for digest.

### Not re-captured on purpose (asserted, then left)

| Record | What it pins | Decision |
|---|---|---|
| `artifacts/validation/PC-02/baseline/runs/PC02-N01..N04.json` | what the application answered in the measured live `P4-RUN-01` session | A measurement of a past session, not a pin of the current contract; rewriting it would misreport what the application said. Left. |
| `fixtures/golden/GJ-02/manifest.json`, `selection.json`, `SELECTION.md` | the CP-00 authority reading of `stage-registry.json` at `1.0.0-draft.1` (`skip_allowed false` for `finding_merge`) | The pinned value did not change; the manifest's SHA-256 is pinned by `selection.json` and by CP-00 evidence. Left. |
| `tests/contract/test_cp00_candidate.py`, `test_validate_bootstrap.py` | the CP-00 candidate at `92e13fa4` (22 codes) and bootstrap fixtures | Ignored by the official `tests/contract` invocation, red for months by design; a statement about that tree. Left. |

## 4. The register rows

| Debt | Decision | Reason |
|---|---|---|
| `D-179` | **done** | phase A |
| `D-151` | **done** | OpenAPI and `P02_SEAMS.md` prose, pinned by `test_the_two_prose_rules_the_seal_corrected_are_corrected` |
| `D-161` | **done** | OpenAPI rule 1, same test |
| `D-172` | **carried** | (a) a `304` for crops needs a digest-only read on the port, built in `bootstrap/adapters.py` (composition root, outside the grants); (b) the integer rule in the block-list schema's `x-envelope-rules` changes `IMPLEMENTED_ENVELOPE_RULES` in `tools/fixtures/portal_bundle/validate.py` (outside the grants) and `test_portal_bundles.py` pins the count |
| `D-163` | **carried** | a member-digest field on a version is a new field with an ingest, `documents` and migration change; the task forbids a new schema and feature. An optional addition after the seal is a minor version |
| `D-145` | **carried** | a run-state field on `ExecutionQueueItem` is built in `bootstrap/adapters.py` (composition root, forbidden hotspot) and changes the queue control; the register said "due at the W58 contract 1.0.0", so the debt row should read: carried to the first minor version, optional field |

## 5. Checks (commands run on the lane's own containers unless stated)

| Check | Result |
|---|---|
| `python3 tools/plan/pin_sweep.py contract-version` before / after | exit 0 / exit 0 (67 / 69 paths) |
| `pytest tests/contract --ignore=…test_cp00_candidate.py --ignore=…test_cp00_final_state.py --ignore=…test_validate_bootstrap.py` on `origin/dev` `2affede8` | **983 passed**, exit 0 |
| `npm --prefix web run api:verify` (also `node scripts/generate-api-client.mjs --check`) | OK, 83 operations, contract sha256 `741f29f9…`, exit 0 |
| `npm --prefix web run lint -- --quiet`, `run typecheck` | exit 0, exit 0 (phase B tree; no web change since) |
| vitest, changed files + `tests/contract` + `frontend-lock.guard` | 42 files, 686 tests passed (phase B); phase A: 35 files, 607 tests |
| migration `0029`: `tests/integration/db/test_routing_refusal_codes_migration.py` | 10 passed (per-table: the CHECK refuses before and admits after; a row survives the upgrade and stops the downgrade; the clean downgrade restores 0022's vocabulary) |
| `tests/integration/db` (phase A tree) | 546 passed |
| `tests/integration/api tests/integration/runs tests/integration/sections` (phase A tree) | 1167 passed |
| `tests/characterization` (phase B tree) | 69 passed |
| `tests/integration/db/{test_schema_invariant_inventory,test_migration_lifecycle,test_routing_refusal_codes_migration}.py`, `tests/integration/sections`, `tests/characterization` on `2affede8` | 171 passed |
| Phase B broad run (`tests/e2e/pc01/test_acceptance.py` + integration `analysis auth qa_w52 composition api runs sections db`, 3615 tests) | **voided at about 75 %**: the shared `/` filled (about 0.3 GB free) and object storage answered `StorageUnavailableError`. The first 75 % (e2e acceptance, analysis, auth, qa_w52, composition, api) passed except three tests in `analysis/geometry/test_geometry_stage.py`; those and the 12 modules that failed after the disk filled were run again focused (13 files, 136 tests) on `2affede8` once space returned: **136 passed**. `runs`/`sections`/`db` for the phase B tree were not run in full; no file in them carries the moved literal and the migration is the one phase A measured. The integrator's gate on the merged tree covers them. |
| `getProductVersion` read through the composed application | `{"product_version": "0.7.0", …, "contract_version": "1.0.0"}`; pinned by the new `test_the_composed_product_version_reports_the_sealed_contract_version` |
| `git diff --check` | exit 0 |
| Full `make gate` | not run (task non-goal; the integrator runs it on the exact merged tree) |

## 6. Mutations — every new or moved guard shown failing

Each was applied to the committed tree, the named test run, and the file restored (`cmp`-checked).

| # | Mutation | Reddened |
|---|---|---|
| M1 | `http` of `section_profile_unavailable` 422 → 409 in `error-codes.json` | `test_routing_refusal_codes::test_the_catalogue_entry[section_profile_unavailable]` |
| M2 | `retryable` of `version_classification_required` false → true | `…::test_the_catalogue_entry[version_classification_required]` |
| M3 | its `category` `policy` → `validation` | same test |
| M4 | `safe_detail_keys` `[]` → `["reference_kind"]` | same test ("a routing refusal carries no details") |
| M5 | envelope `if/then` pin of `section_profile_unavailable` flipped to `true` | `…::test_the_envelope_schema_admits_the_code_and_pins_its_retry_flag` |
| M6 | `RunInputInvalid` stops naming `section_profile_unavailable` | `…::test_the_served_document_enumerates_and_declares_the_code` |
| M7 | migration `_ADDED_ERROR_CODES` forgets one code | `test_contract_vocabulary::test_error_code_domain_equals_the_frozen_catalog` |
| M8 / M8b | downgrade guard stops reading `provider_call_effect` / `audit_run` | `test_routing_refusal_codes_migration::…stops_the_downgrade[…]` (the refusal message is asserted, so a failing `ALTER` is not accepted) |
| M8c | upgrade leaves `ck_model_call_error_code` on the old vocabulary | `…test_the_widening_is_what_admits_the_codes[model_call]` |
| M9 / M9b | profile reasons reported as the classification code / unclassified reuses `required_norm_unavailable` | `test_w59_classification_command::TestRouting` |
| M9c | refusal reintroduces a `reference_kind` detail | `test_w59_section_routing_over_http` (500: the envelope screen refuses the key) |
| W1 | `routingRefusal` swaps the two sentences | `run-refusal.test.ts` (2 tests) |
| W2 | run failure reads `reference_kind: analysis_profile` as a routing refusal again | `run-refusal.test.ts` |
| W3 | English catalog message for `section_profile_unavailable` | `catalog-message.contract.test.ts` (no Cyrillic; too short) |
| W4 | terminal-reason sentence of one code replaced by the other's | `run-terminal-reason.test.ts`, `terminal-reason-sentences.contract.test.ts` |
| W5 | `PC01_ERROR_CODES` forgets a new code | `pc01-error-codes.contract.test.ts` |
| W6 | English word inside a new terminal-reason sentence | `rendered-language.guard.test.ts` (2 tests) |
| F1–F4 | `api_codes` 27 → 26, `stored_vocabulary` 25 → 24, `migration_head` back to 0028 | `test_openapi_document` / `test_envelope_screen_rules`, `test_contract_vocabulary`, `test_doc_prose_facts`, `failure-surface` + `seam-operations` |
| S1–S2 | `CONTRACT_VERSION` of `routers/__init__.py` / `result.py` back to the draft | `test_contract_seal::test_the_application_constants_are_the_sealed_version` |
| S3 | `tls-server.conf` `429` body left on the draft | `…::test_the_edge_answers_its_own_error_bodies_with_the_sealed_version` |
| S4 | web forwarder left on the draft | `…::test_the_web_forwarder_answers_its_own_error_body_with_the_sealed_version` |
| S5 / S6 | one analysis schema `const` / the events example left on the draft | `…::test_every_json_artifact_of_a_family_declares_only_the_sealed_version[analysis / events]` |
| S7 | `identifiers.json` un-frozen | `…::test_a_domain_catalog_is_frozen_at_the_sealed_round` |
| S8 | `state-machines.schema.json` allows `frozen: false` | `…::test_a_domain_schema_refuses_a_catalog_that_is_not_frozen` |
| S9 | a "30 days" retention window written into the freeze note | `…::test_the_retention_question_stays_undecided_and_declares_no_window` |
| S10 | `rate_limited` note forgets the token exchange | `…::test_the_rate_limited_note_names_the_credential_exchange` |
| S11 / S11b / S11c | OpenAPI copy not mirrored / D-151 sentence reverted / D-161 exception removed | `…::test_the_api_document_and_its_web_copy…`, `…::test_the_two_prose_rules_…` |
| S12 / S13 | `info.version` back to the draft / facts file back to the draft | `test_contract_seal` (two tests) |
| S14 | a characterization record changes its error code as well | `test_the_sixteen_error_records_moved_by_the_contract_version_and_nothing_else` |
| S15 | the domain catalog the adapter reads left on the draft | `test_router_answers::test_the_composed_product_version_reports_the_sealed_contract_version` (live body shows `1.0.0-draft.1`) |

Harness note for the next lane: `mut.py` and the other helper scripts were first kept in the session
scratchpad, which turned out to be shared with another session that overwrote one of them; a mutation run
printed that session's output instead of a verdict until the helper was moved to a private directory.
Check that a mutation run prints its own `[label] exit=` line.

## 7. Files changed (two lane commits, 142 files; nothing outside `allowed_paths`)

- **Contracts:** `contracts/api/v1/{openapi.json,README.md}`; `contracts/domain/v1/` (3 catalogs, 3 schemas,
  `error-envelope.schema.json`, 2 examples, README); `contracts/analysis/v1/` (12 files, 6 examples, README);
  `contracts/events/v1/` (schema, 2 examples, README).
- **Migration:** `db/migrations/versions/20261021_0029_routing_refusal_codes.py` (new).
- **Source:** `shared/errors/codes.py`, `api/schemas/models.py`, `api/routers/__init__.py`,
  `analysis/engine/result.py`, `sections/{classification,public}.py`, `runs/commands.py` (docstring).
- **Edge and web:** `infra/deploy/proxy/{nginx,tls-server}.conf`; `web/openapi/openapi.json`,
  `web/FRONTEND_LOCK.json`, `web/src/shared/api/{generated/* (4), catalog-message, errors, credentialed-forward}.ts`,
  `web/src/entities/{audit-run/model/{routing-refusal,run-failure,terminal-reason}, execution/model/failure}.ts`.
- **Tests:** new `tests/contract/api_v1/test_routing_refusal_codes.py`, `test_contract_seal.py`,
  `tests/integration/db/test_routing_refusal_codes_migration.py`; changed `tests/support/expected_facts.json`, the
  vocabulary, error-kernel, portal-bundle-seal, conformance, alpha-acceptance, status-policy, release, auth and
  access-matrix tests, the downgrade-chain digest table, the schema-invariant inventory, the four routing
  integration modules, `test_router_answers.py`, `tests/characterization/w13_baseline/{README.md,
  test_response_baseline.py,records/ (16)}`, `tests/e2e/pc01/…` (manifest comment, README, acceptance), and
  36 `web/tests` files (the literal), `rendered-language.guard`, `run-refusal`, `run-terminal-reason`.
- **Docs:** `docs/program/{CONTRACT_PIN_REGISTRY,P02_SEAMS}.md`, `docs/manual-tests/PC-01_prototype.md`, this report.

## 8. Risks, limits, instructions

- **Wire change.** Every error body now says `contract_version: "1.0.0"` (the edge's too). A client or script
  that compared the draft string breaks; the repository's own are moved. The `startRun`/`reauditRun` routing
  refusals change code (documented as a changed behaviour of a draft).
- **Stored data.** Nothing stored carries `contract_version` (no column); no row carries a new code today.
  `findings/recorded_saved_plan.py` compares a rebuilt `StageResult.contract_version` with the constant, both
  built from the same code, so no stored artifact is affected.
- **Not touched, still on the old claims** (the integrator's or evidence): `docs/program/RELEASES.md` `v0.7.0`
  `contract_version` cell (`1.0.0-draft.1` is true of the tree that release names; no test pins it),
  `CURRENT_STATE.md`, `DEBT_REGISTER.md` rows `D-145/151/161/163/172`, `docs/architecture/*`,
  `artifacts/checkpoints/CP-00/*`, `fixtures/golden/*`, `artifacts/validation/PC-02/baseline/*`.
- **Instruction.** The integrator merges the lane tip (already done for `c957e7d9`; this report is one more
  commit), derives nothing by hand (all generated artifacts were re-derived with `api:generate` and the lock
  recomputed), updates the register rows above, and runs the full gate on the merged tree. After the seal any
  contract change follows `VERSIONING_AND_FREEZE_POLICY.md`.

## 9. Hotspots

The two lane commits' changed paths (`git diff --name-only 2161d505 d9afc6f3` and `c7d5f483 c957e7d9`, 142
files) were each matched against the task's `allowed_paths` and against the forbidden list: zero outside the
grants and none of `VERSION`, `release-notes/**`, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, dependency or lock
files, `web/src/_app/providers.tsx`, global styles, refs or tags. No push, no tag.
