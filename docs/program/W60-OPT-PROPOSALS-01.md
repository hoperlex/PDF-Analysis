# W60-OPT-PROPOSALS-01 — «Предложения»: deterministic cheaper analogs for AR with expert decisions

**Base:** `d090a84a` (`W60-OPT-MATCH-01` phase A `67fd24c0` plus this task file; head
`0026_price_lists`), branch `agent/w60-opt-proposals-01`, isolated worktree
`w60-opt-proposals`, lane PostgreSQL 57610 / MinIO 61210–61211. **Status:** phase A (migration
`0027`, the `optimisation/proposals` package, tests) complete; phase B (operations, the reseal,
the «Предложения» section on «Оптимизация», retiring the `/optimisation` stub) waits for the
contract slot. Development candidate under `R-135`: no full gate, no live journey, no push,
merge into another branch or tag.

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

`identity.py` (`opp`/`opr`/`opd`, minted on the registry's pattern, not contracted — phase B),
`policy.py`, `generator.py` (pure), `repository.py` (statements), `commands.py`, `queries.py`,
`export.py`, `public.py` (the surface; `optimisation/public.py` re-exports it in phase B).
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
never stored cut. Positions are bucketed by (unit, currency, head word), so a pass is linear
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

- `opp`, `opr`, `opd` (and `prp` in the two position columns) are minted on the registry's
  pattern but not contracted until phase B.
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
