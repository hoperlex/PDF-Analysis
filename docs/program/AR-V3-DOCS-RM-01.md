# AR-V3-DOCS-RM-01 — AR v3 leaves the ADRs, the current documents and the program records

Lane of wave AR-V3-REMOVE + V3-OPTIN. Branch `agent/ar-v3-docs-rm-01`, base `826470582`. Rulings: `R-154a`, `R-154c`, `R-154d` and
`R-154b` (`OWNER_RULINGS_2026-09-17.md` section 3.54). The word «v3» had two meanings in the tree. This lane removes the first
(AR v3, the six-scope АР beta) and leaves the second (plan v3 of the extended review) in place, now opt-in.

## What changed

- **ADRs.**
  - `ADR-0024`: the title and decision 1 are replaced. АР runs the standard analysis like every section, from the text profile sourced from the original
    application's AR files. The six-Run group keeps one historical sentence. The passages about v3 on v2 code, the v2 extraction, the pack and the group costs
    are withdrawn, with stable numbering (commitment rows 2 and 10, order step 2, alternative 1).
  - `ADR-0028`: plan v3 of the extended review is opt-in by `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v3`, the default is `v2` (`R-154b`). The status line,
    the context bullet and a note under the decision 10 table say it. The critic and correction rows run only under v3.
  - `ADR-0021`, `ADR-0022`, `ADR-0025`, `ADR-0026` and `ADR_INDEX.md` lose their AR v3 clauses. `ADR-0021` names migrations `0032` and `0033` by number.
- **Owner rulings.** `OWNER_RULINGS_2026-09-17.md` section 3.54 holds `R-154a`…`R-154d` with the owner's words. Older sections are not edited.
- **Deleted from the tree** (157 files, `git diff --name-status 826470582..HEAD | grep -c '^D'`):
  - `docs/program/AR-V3-*.md` (58 records) and `docs/program/tasks/AR-V3-*.md` (56 tasks): `R-154d`.
  - `docs/program/ar-v3-beta/` (8 files: the reviewed-pack decisions, scopes, query texts, vectors provenance and spans): the data of the pack.
  - `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md` and `docs/program/tasks/HOTFIX-AR-V3-SNAPSHOT-INT-20261030.md`: the AR v3 queue and its snapshot task.
  - Records whose subject is the AR v3 group, pack, prompt, response or six-scope map, each with its task file where one exists:
    `AR-BETA-AVAILABLE-SOURCE-GATE-01`, `AR-BETA-CITATION-REVIEW-GATE-01`, `AR-CORPUS-CITATION-BRIDGE-01`, `AR-NORM-MAP-APPROVAL-PREP-01`,
    `AR-NORM-MAP-01` (task only), `AR-SIX-RUN-SCOPE-BRIDGE-01`, `W57A-INT-V3-LOCAL-EVALUATION-PREP-01`, `W57A-INT-V3-PROMPT-MATERIAL-PREP-01`,
    `W57A-INT-V3-REQUEST-CANDIDATE-PREP-01`, `W57A-INT-V3-RESPONSE-PREP-01`, `W57A-INT-SET-PROMPT-INPUT-PREP-01`, `PROD-11A-V3-TEXT-LAYER-PROBE-01`,
    `PROD-11B-V3-STAGE-ID-MIGRATION-01`, `PROD-11C-RECORDED-COST-01`, `PROD-11D-V3-GROUP-QUEUE-01`, `CFB-INT-DEV-PUBLISH-30`, `DEV-PURGE-INVENTORY-01`.
- **Current documents.**
  - `DEBT_REGISTER.md`: `D-204`, `D-207`, `D-222`, `D-225`, `D-231`, `D-247`, `D-248`, `D-283`, `D-284`, `D-303` and `D-338` are closed as removed (`R-154a`,
    `R-154c`). Every row stays, its id is struck through, and each carries a removing-commit locator (`git log --diff-filter=D --oneline -- <record>`) and a check.
    `D-600` keeps one open reading (the cancelled-job one); its AR v3 sibling reading is moot. Other rows lose only their AR v3 clauses.
  - `ROADMAP.md`: owner goal 1 (AR v3 as an opt-in mode) is withdrawn with its design link.
  - `UI-PARITY-METRICS.md`: the `Q-MD-9` AR v3 group rule is moot.
  - `PRODUCTION-READINESS-PLAN-01.md`: a dated amendment, and `PROD-12` is marked withdrawn.
  - `P02_SEAMS.md`: the five AR v3 operation rows, their names in the keyed-writes rule and the AR v3 prose are removed. **This is the last commit of the lane
    and lands with BE step B** (see Integration).

## Judgement calls

- **Kept as history, although they mention AR v3 as one topic among several:** `PROD-10-AR-V2-EXTRACT-01` (it created `analysis/profiles/ar_shared`, which
  `src/auditmanager/analysis/recognised/region_candidate.py:22` still imports), `PROD-11-AR-V1-V2-REMOVAL-01`, `AR-SET-PROMOTION-01`, `AR-NORM-DEV-INT-01`,
  `AR-NORM-DEV-PUBLISH-01`, `AR-BETA-LOCAL-CUSTODY-01` (corpus custody), `AR-ORIGINAL-CITATIONS-PLAN-01`, `W57A-INT-CITE-*` and the other W57a norm-verification
  records, `REVIEW-INDICATION-SWITCH-01`, `BETA-STATIC-MATRIX-02`, `ROADMAP-GAP-2026-10-27`, the `PRODUCTION-WAVE-PW*` plans, and every other wave's task and record file.
- **`AR-V3-LIVENESS-01` was deleted as ordered, but its subject is generic:** the heartbeat liveness of `ssh_command` calls. `tools/executor-runner/README.md:543` still cites it.
  `D-285` and `D-289` stay open and now name the change without the record.
- **`D-280`, `D-281`, `D-282` stay open.** The wire form of an output schema is generic (`analysis/text/wire_schema.py`), so only the AR v3 framing was removed.
- **Literals kept:** `20261027_0036_cite_partition_v3` (`ADR-0025-comparison-modules.md:33`) is a migration revision id with no AR marker.
  `start_ar_v3_beta_group` (`DEBT_REGISTER.md:130`, row `D-213`) is a command type the product purge keeps classified while old `command_record` rows may carry it (`R-154c`).
  «profile v3» in `R-89` (`OWNER_RULINGS_2026-09-17.md:1481`) is an older profile of insolation, not AR v3.
- **Extended-review v3 is untouched:** `HOTFIX-STAGE-V3-1030` and `HOTFIX-STAGE-V3-UI-1030` stay, and so does the extended-plan code.

## Counts

`git grep -niE "ar[_-]?v3|AR v3|АР v3|ArV3" -- docs`, case-insensitive, on the working tree.

| Tree | Lines | Files |
| --- | --- | --- |
| Base `826470582` | 2500 | 364 |
| This lane, before this record | 820 | 208 |

The 208 files that remain: 119 task files and 71 records of other waves, 11 dispatch plans, 3 compare reviews and 2 files under `docs/program/history` (all history, not edited);
2 files under `docs/manual-tests` (outside this lane's paths); the rest are the current documents above, in which the remaining lines are the withdrawal notes, the struck
register rows and the rulings. The count of files outside `tasks/` and `history/` is 87.

## Checks

- `git diff --check`: clean on every commit.
- Guards, one locked run on tree `610e75604703433e2f185333b8e03ae13c1109fc` (before the `P02_SEAMS.md` edit):
  `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/domain_p02/test_seam_register.py`
  gave 130 passed in 79 s (`.local/evidence/lane-ar-v3-docs-rm-01/guards-run1.log`). No dangling-link guard failed, so no historical record was edited for a link.
- `P02_SEAMS.md`, after its edit, was checked by a script against `contracts/api/v1/openapi.json` minus its five AR v3 operations: the operation table matches (319 rows), and
  the keyed-writes rule matches both ways. The real tests, run against the unchanged contract, are expected to fail for exactly those two guards.

## Integration

- **Merge order.** `P02_SEAMS.md` is the last commit, prefixed «AR-V3-DOCS-RM-01 (lands with BE step B)». With the contract still carrying the five operations,
  `test_the_api_operation_table_matches_the_frozen_document` and `test_the_idempotency_rule_names_exactly_the_keyed_writes` are red. `R-154h` set the contract to `1.50.0`,
  so that commit lands with it, together with BE step B or after it.
- **Dangling references outside this lane's paths** (the lanes that own them handle them): `contracts/api/v1/README.md:379`; `scripts/ar-v3/*`,
  `infra/deploy/ar-v3-pack/README.md`, `infra/deploy/env/alpha.env.example`, `scripts/README.md` (backend lane); `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py`
  reads the deleted `docs/program/ar-v3-beta/` and `tests/integration/runs/test_v3_saved_text_layer_probe.py:27` names `PROD-11A-V3-TEXT-LAYER-PROBE-01.md` (backend lane);
  `tools/executor-runner/README.md:543`; `docs/manual-tests/HOSTS-CUTOVER.md` and `ALPHA_PUBLIC_ACCEPTANCE.md`.
- `origin/dev` moved to `637d23e06` while this lane ran. It adds `D-679` and `D-680` at the end of `DEBT_REGISTER.md`. This branch stays on `826470582`; the integrator merges.

## Risks

- The closure checks of the register rows (`git ls-files … | wc -l` prints `0`) pass on this branch. The rows `D-207` and `D-462` also depend on the backend lane's removal of the modules and tests they name.
- A record kept as history may still say «AR v3» in prose. By the plan, that history is not edited.
