# CONTRACT-1-8-0-01 — the shared API contract moves from 1.7.0 to 1.8.0

Lane V of the window `AR-CLOSE-1026`. Base `85458f07` (`integration/ar-close-1026`), branch `agent/contract-1-8-0-01`. Task file: [`tasks/CONTRACT-1-8-0-01.md`](tasks/CONTRACT-1-8-0-01.md) (premises P-01 to P-08, and the classification of every hit). Owner ruling: `R-146ar` («1.8.0 сейчас»). Content that the move seals: `COMPARE-PERSISTED-SUMMARY-01` (`approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`; `DEBT_REGISTER.md` row `D-244`). `2.0.0` stays reserved (`D-233`) and was not touched.

## Result

`info.version` of `contracts/api/v1/openapi.json` and of its mirror `web/openapi/openapi.json` is `1.8.0`; so is every other holder of the shared literal. The generated client and `web/FRONTEND_LOCK.json` are resealed from the new bytes (contract sha256 `e82f1df0f9c3951526592e92ccfcaa69d8182fd4ec024d9a46cca7c69866cb0a`; `npm --prefix web run api:verify` OK). The surface (95 paths, 107 operations, 314 schemas), the 27 error codes and the migration head `0035_comparison_records` did not move. No migration, no operation, no schema, no behaviour was edited.

Three commits on top of the base, in the shape of the previous minor move (`b7e5fdf1`, `56b25ebe`):

| commit | what |
| --- | --- |
| `01291bac` | the task file: premises and the classification of the 191 lines that name `1.7.0` |
| `7288e82c` | the mechanical rewrite (the content commit that the lock names): 97 files with the contract documents, three served constants, the edge, the forwarder, the pins, 49 web tests, two README sections and the live state sentences |
| `dcec1d7d` | the regenerated client (4 files) and the resealed lock |

The first wording of the one new sentence of `info.description` quoted counts («three operations», «thirteen schemas») and `test_surface_counts_in_prose.py` refused it (it read them as a claim about the surface). The wording was changed and the two unpublished commits were recreated from the same tree; the table below is the final state.

## Classification

The full table (path, lines, kind, 118 rows) is in the task file. Before the edit `git grep -n '1\.7\.0'` listed 191 lines in 116 files (185 lines in 112 files outside the generated client, as `D-244` row and `COMPARE-PERSISTED-SUMMARY-01.md` counted 111 at their tip):

| kind | files | lines | rule | done |
| --- | --- | --- | --- | --- |
| A1 API document and mirror (`info.version`, `ErrorEnvelope.contract_version` const) | 2 | 4 | move | all 4 (2 per file); line 7, `info.description`, is class H |
| A2 analysis / domain / events families | 30 | 58 | move | 55 lines moved by line; the 3 `revision_note` lines rewritten by hand (revision 26) |
| A3 served literals (3 src constants, 4 edge bodies, 1 forwarder body) | 6 | 8 | move | all 8 |
| A4 facts file and seal test | 2 | 2 | move | both |
| A5 generated client | 4 | 6 | regenerate | `api:generate` |
| A6 web lock | 1 | 3 | reseal | digests, `info_version`, content commit |
| A7 contract READMEs | 2 | 3 | move | version heading, sealed revision |
| B1 web tests quoting the served version | 49 | 61 | move | all 61 |
| B2 `CURRENT_STATE.md` | 1 | 2 | move | 3 sentences, history wording kept |
| H history records | 19 | 38 | keep | untouched (17 docs; the two OpenAPI files only in one sentence) |
| C unrelated third-party versions | 2 | 6 | keep | untouched |

**Unrelated hits left alone: 6 lines in 2 files** — `web/package-lock.json` (`es-module-lexer` 1.7.0 at lines 2487-2488 and its `^1.7.0` range at 3803, `esquery` 1.7.0 at 2658-2659) and `infra/norms-worker/requirements.lock:199` (`hf-xet==1.7.0`). `git diff --stat 85458f07..HEAD -- web/package-lock.json infra/norms-worker/requirements.lock` prints nothing.

After the move `git grep -n '1\.7\.0'` (outside the two deliverables) lists 60 lines, and every one is meant to stay: 8 lines that name the version being superseded by design (`supersedes` of the three domain catalogs and the three schemas, `PREVIOUS` and the retired-prefix tuple of the seal test), 5 lines of README and `info.description` history (the old `Version 1.7.0` section and the two old wave paragraphs, the new section's reference to what it seals), 2 history lines of the lock (content commit subject and note), the 6 class C lines, 1 line for the domain README's `supersedes` sentence, and 38 lines of 18 program docs that say what was true on the day they were written (`CURRENT_STATE.md` keeps its history clauses). The mirror carries the same `info.description` line as the contract.

## Beside the literal (decisions)

* **D-1 `supersedes` and `candidate_revision`.** As in `b7e5fdf1`, the three domain catalogs and their schemas move `supersedes` `1.6.0` to `1.7.0` and `candidate_revision` 25 to 26 with a new `revision_note` («Candidate revision 26 by CONTRACT-1-8-0-01 ... family 1.8.0 seal»). The domain README says «sealed revision 26». A move that left revision 25 would have kept two seals under one number.
* **D-2 the retired-prefix tuple.** The walk of `test_contract_seal.py` collects a `const` only when it begins with a retired version; `1.7.0` is added, otherwise a stale `const: 1.7.0` in a schema would pass (mutation M12b).
* **D-3 three src constants.** `analysis/engine/result.py`, `api/routers/__init__.py`, `api/schemas/models.py` serve the version; one literal each, nothing else in `src/` changed (the domain constant is read from the catalog at import).
* **D-4 `info.description`.** Only the last sentence of the wave-B paragraph («The contract version stays 1.7.0 (a minor bump ... is the integrator's step)») was rewritten to say that the step happened; the two earlier wave sentences are true statements about their wave and stay. This is the only prose in a contract document that changed; the README sections are the other prose.
* **D-5 history.** 17 program docs and task files that quote `1.7.0` as it was (class H) and the register, the rulings and the plan are untouched (`TASK_TEMPLATE.md`: historical evidence is immutable; this lane was told not to edit `DEBT_REGISTER.md` or the rulings).

## Files

97 files changed by the rewrite and the reseal, plus the task file and this report (`git diff --name-only 85458f07..HEAD`):

| group | files | note |
| --- | --- | --- |
| `contracts/analysis/**` | 18 | 17 under `v1/` (schemas, catalogs, examples, `crop-manifest`, `legacy-*`, `portal-blocks`, `stage-registry`) and `ar_v3_beta/v1/stage.json` (`analysis_contract_version`) |
| `contracts/domain/v1/**` | 10 | 3 catalogs, 3 schemas, `error-envelope.schema.json`, 2 examples, README |
| `contracts/events/v1/**` | 3 | envelope schema and 2 examples |
| `contracts/api/v1/openapi.json`, `README.md` | 2 | |
| `web/openapi/openapi.json` | 1 | mirror (byte-identical to the contract) |
| `web/src/shared/api/generated/**` | 4 | regenerated, not edited |
| `web/src/shared/api/credentialed-forward.ts` | 1 | the forwarder's own error body |
| `web/FRONTEND_LOCK.json` | 1 | |
| `src/auditmanager/{analysis/engine/result.py, api/routers/__init__.py, api/schemas/models.py}` | 3 | one literal each |
| `infra/deploy/proxy/{nginx,tls-server}.conf` | 2 | four edge error bodies |
| `tests/contract/api_v1/test_contract_seal.py`, `tests/support/expected_facts.json` | 2 | |
| `web/tests/unit/**` | 47 | |
| `web/tests/guards/**` | 2 | `gender-agreement`, `rendered-language` |
| `docs/program/CURRENT_STATE.md` | 1 | |
| `docs/program/tasks/CONTRACT-1-8-0-01.md`, this report | 2 | |

Live prose that changed in `CURRENT_STATE.md`: the contract sentence of the stable section now reads «the shared contract is `1.8.0` after `COMPARE-PERSISTED-SUMMARY-01` under `R-146ar` (...; it was `1.7.0` after `PROD-11-AR-V1-V2-REMOVAL-01`, `1.6.0` after `EXEC-PAR-START-01`, and `1.5.0` after `AR-V3-BETA-PACK-STATUS-API-01`; `2.0.0` stays reserved, `D-233`; ...)»; in the 2026-10-27 paragraph item (3) says «the contract stayed `1.7.0` at that point, prose only» and item (7) says the three operations «were sealed under `1.7.0` (`D-244`), and the shared version then moved to `1.8.0` (`CONTRACT-1-8-0-01`, owner ruling `R-146ar`)».

## Modified tests: before and after (nothing weakened)

`tests/contract/api_v1/test_contract_seal.py` — every assertion keeps its shape; only the literals it compares to moved:

| test | asserted before | asserts now |
| --- | --- | --- |
| `test_the_facts_file_names_the_sealed_version` | `FACTS.contract_version == "1.7.0"` | `== "1.8.0"` |
| `test_every_json_artifact_of_a_family_declares_only_the_sealed_version[analysis, domain, events]` | every version-bearing key of the family is `1.7.0`, and no `const` still names a retired version (`1.0.0` to `1.6.0`) | every key is `1.8.0`, and no `const` names a retired version (`1.0.0` to `1.7.0`) |
| `test_the_api_document_and_its_web_copy_declare_the_sealed_version` | `info.version` and the `ErrorEnvelope` const `1.7.0` in both files, which are byte-identical | the same with `1.8.0` |
| `test_the_application_constants_are_the_sealed_version` | the three constants and the `ErrorEnvelope` schema say `1.7.0` | `1.8.0` |
| `test_the_edge_answers_its_own_error_bodies_with_the_sealed_version[nginx.conf, tls-server.conf]` | the set of versions in the edge bodies is `{1.7.0}` | `{1.8.0}` |
| `test_the_web_forwarder_answers_its_own_error_body_with_the_sealed_version` | the forwarder's one body says `1.7.0` | `1.8.0` |
| `test_a_domain_catalog_is_frozen_at_the_sealed_round[3 catalogs]` | version `1.7.0`, `supersedes` `1.6.0`, frozen, revision 25 | `1.8.0`, `1.7.0`, frozen, revision 26 |
| `test_a_domain_schema_refuses_a_catalog_that_is_not_frozen[3 schemas]` | pins `1.7.0`, `supersedes` `1.6.0`, frozen, `candidate_revision` const 25 | `1.8.0`, `1.7.0`, frozen, 26 |
| `test_the_envelope_schema_pins_the_sealed_version` | const `1.7.0` | `1.8.0` |

`tests/support/expected_facts.json` (the independent fact, read by the seal test and `test_doc_prose_facts.py`): `contract_version` `1.7.0` to `1.8.0`.

Web (49 files, 61 lines): 58 lines are fixtures of `ErrorEnvelope` typed by the generated client (`contract_version: '1.7.0'` to `'1.8.0'`; the assertions on what the screen shows are untouched, and `tsc` refuses a stale one, M11). Three lines assert the served version itself: `web/tests/unit/api/credentialed-forward.test.ts:160` (the exact serialized body of the forwarder's refusal, `"contract_version":"1.7.0"` to `"1.8.0"`), `:801` (`expect(body.contract_version).toBe('1.7.0')` to `'1.8.0'`) and `web/tests/unit/api/server-credential.test.ts:111` (the same assertion). Their sources moved with them (`credentialed-forward.ts`), and M5 shows them red when the source is put back.

## Mutation proofs

Each row puts one holder back to its old value in the tree, runs the guard, restores the file from git (`git checkout -- <file>`), and runs the guard again (`git status --short` was empty after every restore).

| # | mutation | guard | red | green after restore |
| --- | --- | --- | --- | --- |
| M1 | `contracts/events/v1/examples/event-envelope.example.json` back to `1.7.0` | `test_contract_seal.py::test_every_json_artifact_of_a_family...[events]` | 1 failed, 20 passed | 21 passed |
| M2 | `contracts/api/v1/openapi.json` `info.version` back to `1.7.0` (mirror unchanged) | `...test_the_api_document_and_its_web_copy_declare_the_sealed_version` | 1 failed | 21 passed |
| M3 | `src/auditmanager/api/routers/__init__.py` constant back | `...test_the_application_constants_are_the_sealed_version` | 1 failed | 21 passed |
| M4 | one literal of `infra/deploy/proxy/tls-server.conf` back | `...test_the_edge_answers_its_own_error_bodies...[tls-server.conf]` | 1 failed | 21 passed |
| M5 | `web/src/shared/api/credentialed-forward.ts` back | `...test_the_web_forwarder_answers...` and vitest `credentialed-forward`, `server-credential` | 1 failed; 2 failed, 44 passed | 21 passed; 46 passed |
| M6 | `contracts/domain/v1/identifiers.json` `supersedes` back to `1.6.0` | `...test_a_domain_catalog_is_frozen_at_the_sealed_round[identifiers.json]` | 1 failed | 21 passed |
| M7 | `error-codes.schema.json` `candidate_revision` const back to 25 | `...test_a_domain_schema_refuses_a_catalog...[error-codes.schema.json]` | 1 failed | 21 passed |
| M8 | `tests/support/expected_facts.json` back to `1.7.0` | `test_the_facts_file_names_the_sealed_version` and `test_doc_prose_facts.py::test_expected_facts_are_independent_and_current` | 2 failed, 63 passed | 65 passed |
| M9 | `types.gen.ts` `CONTRACT_VERSION` back to `1.7.0` | `npm --prefix web run api:verify` and `frontend-lock.guard.test.ts` | `drift in types.gen.ts`; 1 failed, 7 passed | `OK - 107 operations`; 8 passed |
| M10 | one digit of the contract digest in `FRONTEND_LOCK.json` | `frontend-lock.guard.test.ts` | 2 failed, 6 passed | 8 passed |
| M11 | `web/tests/unit/api/failure-message.test.ts` fixture back to `'1.7.0'` | `tsc --noEmit` | `TS2322: Type '"1.7.0"' is not assignable to type '"1.8.0"'` | exit 0 |
| M12 | `contracts/events/v1/event-envelope.schema.json` const back to `1.7.0` | seal test as committed | 1 failed | 21 passed |
| M12b | the same stale const with the retired-prefix tuple as it was before this task | seal test | **21 passed (not caught)** | shows that the tuple edit (D-2) is needed |

## Commands and counts (tip `dcec1d7d` plus this report)

* `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py` — **1175 passed, 19283 subtests passed** (165.8 s; the three files of `D-220` not run; `tests/contract/program` included on a clean, committed tree). The first run, on the first wording of the `info.description` sentence, was 1174 passed and 1 failed (`test_surface_counts_in_prose.py::test_the_api_prose_states_the_surface_this_document_declares`, see Result); fixed and rerun whole.
* `pytest ... tests/unit/api` — 31 passed.
* `npm --prefix web run api:verify` — `OK - 107 operations, contract sha256 e82f1df0...cb0a`.
* `cd web && npx vitest run` (whole suite, includes the 49 touched files and `frontend-lock.guard`) — **202 files, 3085 tests passed** (326 s; the same counts as the baseline in `CURRENT_STATE.md`).
* `cd web && npx tsc --noEmit` — exit 0; `npx eslint .` — exit 0.
* `git diff --check 85458f07..HEAD` — exit 0, no output.
* The governance one-liner on `tasks/CONTRACT-1-8-0-01.md` prints `[]`.
* Last step, after the report commit: `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, `tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` (results in the lane's final message).
* No docker, no network, no database, no private database, no push, no tag, no process killed. `.venv` and `web/node_modules` are untracked symlinks (`/root/projects/PDF-Analysis/.venv`; the `gate-night` tree's `node_modules`); pytest temp dirs were removed after each run.

## Proof that the forbidden paths are untouched

* `git diff --name-only 85458f07..HEAD` filtered by the task's allowed paths leaves nothing outside them.
* The same list filtered for `db/`, `.github/`, `uv.lock`, `pyproject.toml`, `VERSION`, `web/package.json`, `web/package-lock.json`, `docs/program/DEBT_REGISTER.md`, `docs/program/OWNER_RULINGS_*`, `infra/norms-worker/`, `tools/`, `scripts/`, `fixtures/`, `artifacts/` prints nothing.
* `git diff -U0 85458f07..HEAD -- src` is exactly three one-line changes (`CONTRACT_VERSION` twice, `Literal["1.7.0"]` once).
* The 130 lines the line-targeted rewrite changed are identical to the removed lines after `1.7.0` and `1.8.0` are read as one token (checked on the uncommitted diff; removed 130, added 130, equal as multisets). Beyond them the diff holds only the hand edits named above: `supersedes`, `candidate_revision` and `revision_note` of the domain family (9 files), the two README sections, the last sentence of `info.description`, the seal test pins, `CURRENT_STATE.md`, the lock and the regenerated client.
* The migration head, the 27 error codes and the surface did not move: `test_doc_prose_facts.py` and `test_surface_counts_in_prose.py` are part of the 1175.

## Integration notes

1. **Merge as is, do not squash.** The lock names the content commit by its short SHA (`7288e82c`); the guard checks only that it is hexadecimal (as at the previous move), so a squash or a rebase leaves a lock that names a commit that no longer exists. Re-run `api:verify` after any rebase of the contract file.
2. **Rows and docs that still say 1.7.0 and are not mine to edit:** `DEBT_REGISTER.md` `D-244` limit (1) («`info.version` is still `1.7.0` ... nothing demands it»), `D-243`, `D-236` (the line `1.7.0` vs `2.0.0` as an open choice), `D-233` item 1; `ROADMAP-GAP-2026-10-27.md` and its task file (choice 25 on the version line); `PRODUCTION-WAVE-PW4.md`; the task files and reports of `COMPARE-PERSISTED-SUMMARY-01` and `OPT-PROJECT-ALL-SECTIONS-01`. The ruling `R-146ar` settles choice 25 for `1.8.0` now; `D-244` (1) can be closed: `git grep -n '"version": "1.8.0"' contracts/api/v1/openapi.json` prints one line (`5:`).
3. `docs/program/ALPHA_ROADMAP.md` and `P02_SEAMS.md` still name `1.6.0` / `1.0.0` (`D-233` item 2, unchanged by this lane).
4. A consumer that pinned the literal `1.7.0` must move; the list of such holders is class A and B of the task file. The product `VERSION` (`0.8.2`) is a different number and was not touched.
5. `tests/contract/test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (the `D-220` files) were not run, as ordered; none of them holds `1.7.0` (they pin the draft `1.0.0-draft.*`).

## Limits

* `web/FRONTEND_LOCK.json` `info_version` is written by hand and no test compares it with the contract (`git grep -n info_version` finds only the lock itself); it is `1.8.0` now, but a future move could leave it stale. A one-line guard in `frontend-lock.guard.test.ts` (compare with `info.version`) would close it; not added, because this task moves a literal and adds no behaviour.
* Not run: `tests/integration` (needs the lane stack; the tests there that mention the version read it from the constants or the document, `git grep -n "1\.[78]\.0" -- tests/integration` is empty), the `e2e:pc01` journey, `next build`, the full `make gate`. The version is a literal that the unit, contract and web suites above judge from five independent sides (the document, the families, the constants, the edge, the client).
* `tests/characterization/w13_baseline/records/*` still carry `"contract_version": "1.0.0"` (`D-233` item 6: red before and after, unchanged).
* The `info.description` of the document now has a third wave sentence about the version; its two older wave sentences are history of their own waves, which a reader of the served document may find confusing next to `1.8.0`. Removing the older two is a contract-content edit and was not made.
