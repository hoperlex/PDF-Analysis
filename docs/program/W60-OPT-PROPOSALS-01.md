# W60-OPT-PROPOSALS-01 — «Предложения»: deterministic cheaper analogs for AR with expert decisions

**Base:** `d090a84a` (`W60-OPT-MATCH-01` phase A `67fd24c0` plus this task file; head
`0026_price_lists`), branch `agent/w60-opt-proposals-01`, isolated worktree
`w60-opt-proposals`, lane PostgreSQL 57610 / MinIO 61210–61211. **Status:** phases A and B
complete, on the integration tip `1c643357` (`W60-PRICE-LIST-01` and `W60-OPT-MATCH-01` served;
surface 65/74/211, head `0026`) merged for real — `git merge-base --is-ancestor 1c643357 HEAD`
holds and the merge commit has two parents. After this slice: **70 paths / 80 operations / 229
schemas**, API error codes 25, migration head **`0027_optimisation_proposals`**. Development
candidate under `R-135`: no full gate, no live journey, no push, merge into another branch or tag.

## Phase A — result

An expert starts an optimisation pass for a document set; the pass reads the set's current
version, which must be classified `AR`, its newest published run and that run's saved text
layer, the project's current price-list revision and the effective AR vendor list (the
project's own list, else the global one). It stores immutable proposals of one deterministic
kind, `cheaper_analog`, each with the specification row's provenance, the matched and the
proposed price-list positions, both unit prices, the currency and a saving that exists only
when the row's quantity is a number. Experts append `accept` / `reject` / `revise` decisions
(a revise carries its comment); the current decision is the latest; counts by decision and a
formula-escaped CSV belong to the proposals alone. Findings are not read for writing and not
changed. No LLM, no new dependency.

### Migration `0027_optimisation_proposals` (chained on `0026_price_lists`)

| object | what it holds |
|---|---|
| `optimisation_pass` | `opp_<ULID>`; project, document, version, run (FKs); the run's `text_layer_sha256`; price-list revision and vendor-list revision (FKs) with `vendor_list_source` (`global`/`project`); `extraction_algorithm`, `match_algorithm`, `generator_version`; specification / matched / proposed row counts and `proposal_count`; `started_by_user_uid` (FK `app_user`), `started_at`. Unique on the inputs (version, run, price list, vendor list, three algorithms): the natural key of an exact repeat. `am_immutable_row` |
| `optimisation_proposal` | `opr_<ULID>`; pass (FK); per-pass `ordinal` (display order); `proposal_type` (`cheaper_analog`); provenance — `spec_row_key` (`sr-` + 32 hex), page, sheet label, line span, table, position, row text; `matched_position_id` / `proposed_position_id` (FKs `price_list_position`, never equal) with `matched_basis` (`code`/`mark`/`name`) and `analog_basis` (`code_family`/`name_similarity`) and `name_similarity` (0..1, ≤ 4 decimals); proposed vendor; unit; quantity (number and text); current and proposed unit price (exact `numeric`, proposed strictly lower); currency; `saving`; rationale. `am_immutable_row` |
| `optimisation_proposal_decision` | `opd_<ULID>`; proposal (FK); per-proposal `seq` (unique; an order, not an identity); `verdict` (`accept`/`reject`/`revise`); comment (required for `revise`, ≤ 2000); `actor_user_uid` (FK `app_user`); `command_id` (FK `command_record`, unique — one decision per key); `decided_at`. `am_immutable_row` (append-only) |
| CHECKs of the money rule | `(saving IS NULL) = (quantity IS NULL)` and `saving IS NULL OR saving = (current_unit_price − proposed_unit_price) × quantity` |
| `am_check_optimisation_pass_scope` | BEFORE INSERT: the document is in the project, the version of the document, the run of the version and project, the version classified `AR`, the price list the project's, the vendor list an `AR` `list` revision that is global or this project's and of the recorded source; else `AM001` |
| `am_check_optimisation_proposal_prices` | BEFORE INSERT: both positions belong to the pass's price list; both prices, the currency and the vendor are those positions'; else `AM001` |
| `am_require_optimisation_proposals` | deferred constraint trigger: a pass is refused at COMMIT unless exactly `proposal_count` proposals name it |

Both account columns are `RESTRICT` and registered in `access/references.py`. No backfill.
Downgrade drops the three tables and three functions only (the command records stay) and
logs how many rows it drops.

### Package `auditmanager.optimisation.proposals`

`identity.py` (`opp`/`opr`/`opd`; contracted in phase B, so the types validate through the shared registry's),
`policy.py`, `generator.py` (pure), `repository.py` (statements), `commands.py`, `queries.py`,
`export.py`, `public.py` (the surface; `optimisation/public.py` re-exports it).
Imports only sibling modules of `optimisation` (additively: `project_match`, `matching`,
`specification`, `queries`, `repository`, `policy`, `identity` — none edited) and
`access.public`, `documents.public`, `ingest.public`, `shared`.

**Generator** (`cheaper-analog-v1`). For each row whose match is `matched` (and whose unit
the generator re-checks against the matched position), a position of the same revision is a
cheaper analog when: it is another position; same unit under the matcher's `unit_key`
(`п.м` ≠ `м`); same currency; strictly lower unit price; its vendor is on the effective AR
vendor list (`vendor_key`: case, `ё`, quotes, punctuation and legal forms `ООО`/`АО`/… do not
count; no vendor never qualifies); the same kind — same head word (first word with a letter,
abbreviations folded as the matcher folds them) and either the same **code family** (leading
letters, ≥ 2, followed by a digit, of the code else the mark: `ПК 60-12-8` ~ `ПК 63-15-8`) or
**name similarity** `|A ∩ B| / |A ∪ B| ≥ 1/2` over the normalised word sets. The matcher has
no similarity threshold (its name tier is equality, similarity 1, which identifies *the*
product), so this threshold is the generator's own. Ordered by unit price ascending, then
similarity descending, source row, position id; **at most 3 per row**
(`MAX_PROPOSALS_PER_ROW`); ordinals run across rows in extraction order. Saving =
`(current − proposed) × quantity`, exact, only with a numeric quantity, else absent — never 0.
A matched row whose provenance exceeds a storage bound is counted (`rows_out_of_bounds`),
never stored cut. The rationale is words only (the positions, the vendor, the basis) — no price,
no currency code, no decimal: the figures are the proposal's own fields and a second copy of them
in prose would be a second thing to keep equal. Positions are bucketed by (unit, currency, head word), so a pass is linear
in rows × bucket size, not rows × positions.

**Commands.** `start_optimisation_pass` — `expert`; identifiers and key validated; the key is
claimed through `command_record` (same key + same payload answers the stored pass; another
payload is `idempotency_key_reuse`); `read_specification_prices` must be `ready`, else
`conflict` with `conflict_reason` = its state (`version_unclassified`, `section_not_ar`,
`price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large`); no
effective AR list → `conflict` `vendor_list_missing`; then under a per-version advisory lock a
pass with exactly these inputs is answered as stored (an exact repeat under a new key creates
nothing), else the generator runs and the pass with every proposal is inserted.
`decide_optimisation_proposal` — `expert` (an account holding only `admin` is
`permission_denied` `role:expert`); verdict enum, comment normalised (`revise` requires it);
key claimed (replay answers the stored decision); unknown proposal `not_found`
`OptimisationProposal`; next `seq` under a per-proposal advisory lock. Both own no
transaction: the composition root's unit of work commits or rolls back everything, the claim
included.

**Reads** (any one role; none is `permission_denied` `role:admin|expert`):
`list_optimisation_passes` (project, optional document, newest first, ≤ 100, each with counts
by decision), `get_optimisation_pass`, `list_optimisation_proposals` (ordinal order, offset /
limit ≤ 200, optional `decision` filter `pending|accept|reject|revise`, current decision per
proposal, pass counts always over every proposal), `list_proposal_decisions` (history).

**CSV** (`export_optimisation_proposals_csv`): computed on request, never stored; the findings
export's conventions (BOM, CRLF, RFC 4180, empty for absent) plus formula escaping of every
cell (`=`, `+`, `-`, `@`, tab, CR, LF, also after leading spaces → leading apostrophe); 42
columns: the pass identities, the proposal and its provenance, both positions, prices,
saving, rationale and the current decision.

Refusals use the existing catalog only: `validation_failed` (`pattern`, `enum`, `type`,
`required`, `max_length`, bounds), `permission_denied` (`role:expert`, `role:admin|expert`),
`not_found` (`Project`, `Document`, `OptimisationPass`, `OptimisationProposal`), `conflict`
(`aggregate_type: OptimisationPass` with the seven reasons above), the idempotency codes;
an `AM001` from the schema triggers means a port answer contradicted itself.

### Checks (phase A)

Lane containers (`make up`, `make migrate` → `0027_optimisation_proposals`), `.env` from
`.env.example` with the lane values, the `w55b-main-candidate` interpreter,
`python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`; host before
the runs: 7.7 GiB free on `/` (`df -h /`), 6 GiB memory available (`free -g`).

- `tests/unit/optimisation/proposals` — 54 passed (container-free): every analog rule
  (cheaper only, unit, currency, vendor list incl. empty and missing vendor, kind, code family
  vs dissimilar names), at most 3 per row in the fixed order, ordinals across rows,
  determinism and position-order independence, saving exact and absent-not-0, unmatched /
  ambiguous / unit-mismatched rows never proposed, a forged matched status refused by the
  generator itself, a position of another revision a caller error, an oversized row counted;
  vendor keys; the migration's restated vocabularies and bounds equal to the code; the
  algorithm versions fit the stored pattern; refusal reasons = non-ready states + vendor list;
  identities free in the registry; role matrix; verdicts, filters, comments; CSV escaping,
  exact numbers, empty saving, decision columns, header-only, determinism.
- `tests/integration/db/test_optimisation_proposals_migration.py` — 65 passed: a populated
  `0026` database upgrades with no row changed; `AM003` on all three tables; `AM001` for a pass
  without all its proposals, eleven out-of-scope passes and five proposals whose money is not
  their positions'; 40 malformed-row CHECK cases (the money rule's three among them) and the
  bounds admitted; unique inputs, ordinals, row/position pairs, seq and command; each account
  column blocking a delete; downgrade (with its count warning, command records kept) and
  re-upgrade.
- `tests/integration/optimisation/proposals` — 28 passed on the lane's PostgreSQL and MinIO
  (project, versions, Blobs, classification, the price list upload and the vendor lists
  through their boundaries; the run row inserted; runs' states and text through the port):
  the pass pins its inputs and stores four proposals (door by code family 16000 RUB, window by
  similarity 30006.0 RUB, anchor 650.00 EUR from a vendor named `=HYPERLINK(…)`, tape with no
  saving); the project override used and recorded, `inherit` falling back to global; an empty
  list a pass with no proposals; the seven refusals each leaving no row and no claim; role,
  scope and request values; key replay and reuse; an exact repeat under a new key; a new
  price-list revision a new pass with the old one unchanged; three concurrent starts → one
  pass; listings, paging, filters; decisions append, latest current, history, counts by
  decision; replay/reuse of a decision key; admin alone refused, admin+expert allowed;
  refusals write nothing; `AM003` on stored rows; the CSV escaped, complete, recomputed
  byte-identically; findings tables unchanged.
- Whole `tests/unit/optimisation` + `tests/integration/optimisation` with the affected db
  suites (`test_schema_shape`, `test_schema_invariant_inventory`, `test_migration_lifecycle`,
  `test_accounts_migration`, `test_every_immutable_table_refuses_a_write`,
  `test_price_lists_migration`): 448 passed, 5 failed — the pre-existing class the earlier
  lanes measured: `test_accounts_migration` downgrades that break at `0022_findings_v2`
  (`cannot drop columns from view`) after passing through the `0027` downgrade.
- Inventory reseal measured from two fresh databases (`0026` vs `0027`), row-diffed: the `0026`
  database equalled the previous seal in every family; every added row is this revision's
  (columns +52, relations +3, constraints +66, indexes +11, triggers +6, functions +3).
- Mutation probes, each restored afterwards (digest compared), each turned the named tests
  red: an absent saving becoming `0`; the generator's unit re-check dropped; its matched-status
  check dropped; the currency rule removed (bucket key and filter); a dearer position admitted;
  the vendor list ignored; the saving's sign swapped; the unit rule removed (bucket key and
  filter); the per-row cap removed; the saving-presence CHECK, the saving-value CHECK, the
  price trigger's current-price comparison and the scope trigger's `AR` requirement each
  dropped from the migration; an admin alone allowed to decide; no vendor list falling back
  to no restriction; a non-AR version admitted; the exact-repeat lookup skipped; a replayed key
  re-run; formula escaping disabled; leading spaces before `=` not escaped. (Dropping only the
  explicit currency or unit filter stays green by design: the bucket key enforces the same
  rule, so the probe removes both.)
- `tests/contract/architecture`, `domain_p02`, `api_v1/test_doc_prose_facts.py`,
  `tools/test_pin_sweep.py`: 200 passed, 1 failed —
  `test_the_scanned_docs_state_the_migration_head_this_tree_has`, already red at the base
  (`CURRENT_STATE.md`, integrator-owned, and `docs/manual-tests/PC-01_prototype.md`, a phase B
  path, still say `0024`).
- `git diff --check` clean. Deferred under `R-135`: the full gate, the whole contract battery,
  the frontend and the live journey.

### Known limitations

- The vendor-list entry's `material` is not matched against the position: a text layer and a
  price list carry no shared material category, so a listed vendor qualifies for every
  position it supplies.
- Analogs need the same head word; a renamed product of the same kind (`Плита` vs `Панель`)
  with no shared code family is not proposed. The similarity threshold is fixed (1/2).
- The pass reads the price list's positions a second time after the specification read
  (≤ 20 000, in pages of 5 000), because `project_match` exposes the matches but not the
  positions and is not edited here.
- Only `cheaper_analog`; `faster_install`, `simpler_design` and `lifecycle` need judgement
  and arrive with the LLM slice (`contracts/optimization/v1` reserved).
- A pass is synchronous inside the request (bounded: ≤ 10 000 rows, ≤ 30 000 proposals).

## Phase B — operations, reseal, «Предложения» on the «Оптимизация» tab

Merged `f7664f59` (dispatcher), `40cd159f` (price lists) and `1c643357` (specification and
prices) as real merges, resolving per hunk and re-deriving every generated artifact — the
contract, its byte-identical mirror, the generated client, the lock and the facts are produced
by script from the merged contract, never merged by hand.

### Surface

| | before (`1c643357`) | after |
|---|---|---|
| paths / operations / schemas | 65 / 74 / 211 | 70 / 80 / 229 |
| API error codes / migration head | 25 / `0026_price_lists` | 25 / `0027_optimisation_proposals` |

Six operations, tag `optimisation`, accepted by the integrator (the sixth on request):

| operation | method and path | role |
|---|---|---|
| `startOptimisationPass` | `POST /projects/{project_uid}/documents/{document_uid}/optimisation-passes` (`Idempotency-Key`) | `expert` |
| `listOptimisationPasses` | `GET /projects/{project_uid}/optimisation-passes?document_uid&limit` (limit ≤ 100) | any one role |
| `listOptimisationProposals` | `GET /optimisation-passes/{optimisation_pass_id}/proposals?decision&offset&limit` (limit ≤ 200) | any one role |
| `decideOptimisationProposal` | `POST /optimisation-proposals/{optimisation_proposal_id}/decisions` (`Idempotency-Key`; `verdict`, `comment`) | `expert` |
| `listProposalDecisions` | `GET /optimisation-proposals/{optimisation_proposal_id}/decisions` | any one role |
| `exportOptimisationProposalsCsv` | `GET /optimisation-passes/{optimisation_pass_id}/export.csv` | any one role |

Deviations from the proposal sent to the integrator: the path parameters are named by their
catalogue identity (`optimisation_pass_id`, `optimisation_proposal_id`), and `startOptimisationPass`
answers `201` for a new pass **and** for a replay or an exact repeat (one declared success status,
as `uploadPriceList` does), not `200` for the repeat.

Eighteen schemas: `OptimisationPassId`, `OptimisationProposalId`, `ProposalDecisionId`,
`OptimisationProposalType`, `ProposalMatchBasis`, `ProposalAnalogBasis`, `ProposalVerdict`,
`ProposalDecisionState` (the verdicts plus `pending`; also the `decision` filter),
`ProposalDecisionCounts`, `OptimisationPass`, `OptimisationPassList`, `ProposalPosition`,
`ProposalDecision`, `OptimisationProposal`, `OptimisationProposalPage`,
`DecideOptimisationProposalRequest`, `ProposalDecisionResult`, `ProposalDecisionList`. Prices,
quantities, savings and the name similarity cross the wire as exact decimal text; `saving` and
`quantity` are `null` — never `"0"` — when the specification's quantity is not a plain number.

A refused start is `409 conflict` with `details.conflict_reason` ∈ {`version_unclassified`,
`section_not_ar`, `price_list_missing`, `analysis_missing`, `text_unavailable`,
`specification_too_large`, `vendor_list_missing`} and `aggregate_type: OptimisationPass`; the
reasons and the decision constraints are registered in `error-codes.json`'s notes. No error code is
added. A malformed pass or proposal identity in a path is `404` (`aggregate_type`
`OptimisationPass` / `OptimisationProposal`), like every malformed path identity.

**Contract family placement.** As for the price lists, these operations live in `contracts/api/v1`
like every served operation; `contracts/optimization/v1` stays reserved for the model-assisted
pipeline.

Domain catalogue **revision 17** (`identifiers.json`, `error-codes.json`, `state-machines.json` and
their schemas move together): `optimisation_pass_id` (`opp`), `optimisation_proposal_id` (`opr`),
`proposal_decision_id` (`opd`) with an `optimisation_proposal_identity` distinct-identity rule that
says a proposal is neither a finding nor an `ExpertDecision`. The shared registry gains
`OptimisationPassId`, `OptimisationProposalId` and `ProposalDecisionId`;
`optimisation/proposals/identity.py` validates through them.

### Backend

- `api/schemas/models.py` (18 models), `api/routers/ports.py` (`OptimisationProposalPort`),
  `api/routers/optimisation_proposals.py` (six routes; the CSV answers `text/csv; charset=utf-8`
  and `Content-Disposition: attachment; filename="{optimisation_pass_id}.csv"`),
  `api/routers/__init__.py` (the twenty-second router module), `api/routers/handlers.py`
  (malformed `optimisation_pass_id` / `optimisation_proposal_id` → `404`), `api/security.py`
  (`startOptimisationPass`, `decideOptimisationProposal`: `expert`; the four reads: any one role).
- `bootstrap/adapters.py` — `OptimisationProposalAdapter` (reads roles in each transaction,
  resolves the people's labels through `access`, maps the records to the frozen shapes; one unit
  of work per write, so a refusal rolls back the key's claim too) and `_ProposalTextReader`, the
  `SavedTextReader` over the comparison's run reader (the run's one `source_preparation`
  artifact held to its recorded digest and size; a missing or differing blob is
  `storage_integrity_error`); `bootstrap/composition.py` wires it over the same sessions and store.
- `optimisation/public.py` re-exports the proposals surface (additively).
- The generator's `rationale` lost its figures (see phase A).

### Web

- `entities/optimisation-proposal` (queries for passes, a proposals page and a decision history;
  Russian labels for every enum — held equal to the contract's value sets by a test; exact-decimal
  presentation; a sentence for each of the seven `conflict_reason`s), `features/start-optimisation-pass`
  and `features/decide-optimisation-proposal` (one `Idempotency-Key` per intent, **dropped when the
  intent completes**: a decision is appended on purpose and a pass over changed inputs must not
  replay the old one; «На доработку» blocked without a comment; a repeat of the current verdict
  blocked), `widgets/optimisation-proposals` (set chooser of the project's АР sets, the passes with
  their counts by decision, the open pass with its inputs, the decision filter, the proposal cards —
  provenance, both exact prices, saving only where stated, the matched-by/analog-by bases, the
  current decision, the controls an expert is given, the lazily read history — paging, and the
  server's CSV). Own module CSS on the global tokens only.
- Mounted in `_pages/project-detail` under «Оптимизация», after `ProjectOptimisation` (price
  lists, «Спецификация и цены», vendor lists): a widget cannot import a widget in this layering, so
  the page composes them. New query-key factories inside the existing `optimisation` root,
  recorded in `web/docs/PC01_UI_SEAM.md`.
- **The hidden `/optimisation` stub is retired.** Its page now says that project optimisation is on
  the project's «Оптимизация» tab and redirects to the projects list (a client redirect after
  `requireScreen`, so a guest still signs in first). The registry row stays — hidden, out of the
  menu — because the route tree and the registry are held equal and the screen census renders
  every route; the prepared-sections guard no longer lists it as a section that "is coming".

### Reseal files

`contracts/api/v1/openapi.json` and byte-identical `web/openapi/openapi.json`, regenerated
`web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `tests/support/expected_facts.json`
(surface and head `0027`), `contracts/domain/v1/**`, the registers in
`tests/contract/domain_p02/test_openapi_document.py` and
`tests/contract/api_v1/{test_openapi_conformance,test_w55b_portal_bundle_seal,test_surface_counts_in_prose}.py`,
`tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane,test_operation_surface,test_query_surface}.py`,
`tests/integration/composition/{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page}.py`,
`tests/integration/db/test_schema_shape.py` (the three new prefixes and `prp` move into the
contracted set), the surface prose in `P02_SEAMS.md` (history, table, keyed-write rule),
`ALPHA_ROADMAP.md`, `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`,
`api/{README.md,app.py,health.py}`, `api/routers/{declarations,errors}.py`, the BFF `route.ts` and
`shared/api/authorization.ts`; `docs/manual-tests/PC-01_prototype.md` (head). Web registers:
`seam-operations` (fifteen keyed writes), `dashboard-invalidation` (both hooks `false`), the
rendered-language guard (`proposalShapes()`), the contrast census, the prepared-sections guard.
`CONTRACT_PIN_REGISTRY.md` needed no change (no needle moved). `docs/program/CURRENT_STATE.md` is
the integrator's and still states 65/74/211 and head `0026`.

### Checks (phase B, on the merged tree, lane containers)

| command | result |
|---|---|
| `tests/contract/api_v1/test_openapi_conformance_live.py` | passed (served document = contract) |
| `pytest tests/contract` (whole directory, container-free) | 1058 passed; 87 failed + 126 errors, all known: `test_cp00_candidate` 48 + 126 errors, `test_validate_bootstrap` 21 (`jsonschema` absent), `test_cp00_final_state` 3, `test_doc_prose_facts` 2 (`CURRENT_STATE.md` only), `test_error_kernel::test_there_are_twenty_four`, `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`, and `test_alpha_acceptance_command` (passes on a clean tree; red only while edits are uncommitted) |
| `npm --prefix web ci` / `api:generate` / `api:verify` | exit 0; 80 operations, `--check: OK` |
| `npm --prefix web run lint -- --quiet`, `typecheck` | exit 0, exit 0 |
| vitest `tests/guards tests/contract tests/unit/api tests/unit/styles tests/unit/screens tests/unit/qa_w50 tests/unit/optimisation tests/unit/optimisation-proposals tests/unit/projects tests/unit/upload tests/unit/shell` | 78 files, 1292 passed (rendered-language guard, contrast census, screen census and registry guards included) |
| `pytest tests/e2e/test_pc01_journey_conformance.py` | passed |
| lane: `tests/integration/composition/test_optimisation_proposals_over_http.py` | 5 passed: the refusals in order (`version_unclassified`, `section_not_ar`, `price_list_missing`, `analysis_missing`, `vendor_list_missing`), the pass pinned to its inputs, replay by key, a new key over the same inputs answering the stored pass, `403` for an administrator alone on both writes, `422` without a key, exact prices and an absent saving, decisions with history and counts, `422` for revise without a comment, the escaped CSV, `404`s |
| lane: `tests/unit/optimisation tests/integration/optimisation tests/integration/db/{test_optimisation_proposals_migration,test_price_lists_migration,test_schema_shape,test_schema_invariant_inventory,test_migration_lifecycle,test_every_immutable_table_refuses_a_write,test_accounts_migration}.py` | 513 passed, 5 failed — the known `test_accounts_migration` downgrade class (`cannot drop columns from view` at `0022_findings_v2`) |
| lane: `tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane,test_operation_surface,test_router_and_body_rules,test_multipart_rules,test_identity_rules,test_schema_conformance,test_schema_bounds,test_no_internal_identifiers,test_query_surface,test_listing_surface,test_absent_and_empty_are_not_the_same_answer}.py`, `tests/integration/composition/{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page,test_composition_root,test_router_answers,test_optimisation_over_http,test_specification_prices_over_http,test_optimisation_proposals_over_http}.py` | 353 passed, 1 skipped, 3 failed — all pre-existing: `test_query_surface::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it` (now only `compareDocumentVersions` and `listPriceListPositions`; the two paged operations of this slice are driven by `test_optimisation_proposals_read_the_query_parameters_they_declare`), `test_query_surface::test_the_filter_vocabularies_are_the_frozen_ones` (`FindingCategory` has 12 members), `test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it` |

The whole `tests/integration/api` + `tests/integration/composition` directories were started
twice and stopped at the 25-minute cap each time (the suites are slow on a shared host); the named
subset above is what was run to completion. Deferred under `R-135`: the full gate, the live
journey, manual acceptance.

Mutation probes of phase B, each restored afterwards (digest compared), each turned the named
tests red: an absent saving shown as «Экономия: 0»; «На доработку» allowed without a comment; a
decision keeping its `Idempotency-Key` after success; the decision form offered to a non-expert;
starting a pass invalidating the dashboard; the router dropping the `decision` filter; deciding
opened to any role (`test_role_register`); the adapter rendering an absent saving as `"0"`; the
malformed-pass-identity `404` mapping removed.

### Risks and limits

- A pass is synchronous inside the request: the specification read, the matching of up to 10 000
  rows against up to 20 000 positions and the insert of up to 30 000 proposals. The bounds are
  enforced (a larger specification is refused `specification_too_large`, nothing is cut); the time
  of a worst-case pass on the stand was not measured.
- The deterministic analog rules are conservative on purpose (same head word, then a code family or
  at least half the words in common): a renamed product with no shared code family is not proposed.
  The vendor list's `material` is not matched against the position.
- Only `cheaper_analog`. `faster_install`, `simpler_design` and `lifecycle` need judgement and wait
  for the model-assisted slice.
- `startOptimisationPass` declares a single `201` for new and repeated passes; a client cannot tell
  a replay from a new pass except by `started_at`.
- The journey manifest declares no optimisation call: the tab reads nothing until opened. The live
  journey was not run.
- `ProposalHistory` reads the history on demand; a decision made by another expert meanwhile
  appears after the next refetch (the section's «Обновить»), not live.

## Integrator instructions

1. Merge `agent/w60-opt-proposals-01` (phases A and B are one slice; the branch contains
   `1c643357` as a real ancestor). If `integration/night-1020` moved again, merge it into this
   branch first with a real `git merge`, keep both sides per hunk, and re-derive — never
   hand-merge — `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`,
   `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `tests/support/expected_facts.json`
   and every surface count word (`seventy`/`eighty`/`229` in the prose files the guard scans).
   `migration_head` stays `0027_optimisation_proposals`.
2. Move `docs/program/CURRENT_STATE.md` to 70/80/229 and head `0027_optimisation_proposals`.
3. `make migrate` on the stand applies `0027` with no backfill; the downgrade drops only its three
   tables and three functions (the command records stay).

## Hotspot proof

`git log --no-merges 1c643357..HEAD` lists this branch's own commits (phase A, phase B, one test
fix and the task file); none of them touches `docs/program/CURRENT_STATE.md`,
`web/src/_app/providers.tsx`, `web/src/app/globals.css`, `findings/**`, `decisions/**`,
`dispatch/**`, `pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json`, migrations
`0025`/`0026`, `specification.py` or `matching.py`:
`git log --no-merges 1c643357..HEAD -- <those paths>` is empty. `git diff 1c643357 HEAD --
src/auditmanager/optimisation/{policy,repository,queries,commands,uploads,project_match,identity}.py`
is empty: the earlier slices are used additively only. No dependency was added; no ref, tag or
push was made. Phase B's `contracts/domain/v1/**` and `shared/identity/**` edits are the
integrator's grant.
