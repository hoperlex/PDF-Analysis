# Task CONTRACT-1-8-0-01 — the shared API contract moves from 1.7.0 to 1.8.0 (R-146ar)

task_id: CONTRACT-1-8-0-01
status: in progress (branch `agent/contract-1-8-0-01`, worktree `.local/worktrees/contract-1-8-0-01`, not merged, not pushed)

## Outcome

`info.version` of `contracts/api/v1/openapi.json` and its mirror `web/openapi/openapi.json` is `1.8.0`, and so is every other holder of the shared literal (the analysis, domain and events families, the three served constants, the edge error bodies, the web forwarder, the facts file, the seal test, the web tests that quote the served version); the generated client and `web/FRONTEND_LOCK.json` are resealed from the new bytes (`npm --prefix web run api:verify` OK); every `1.7.0` that is not the contract version (a third-party package) is untouched, and the history records keep saying what was true when they were written. The move is the mechanical rewrite that owner ruling `R-146ar` orders for the three operations of wave B (`approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`; `docs/program/COMPARE-PERSISTED-SUMMARY-01.md`, `DEBT_REGISTER.md` row `D-244`). `2.0.0` stays reserved for the removal of `AnalysisProfileStatus.builtin` (`D-233`) and is not touched.

## Depends on

- `COMPARE-PERSISTED-SUMMARY-01` — completed and merged (the three operations; migration `0035`; surface 95 / 107 / 314).
- `PROD-11-AR-V1-V2-REMOVAL-01` — completed and merged (the previous minor move, `1.6.0` to `1.7.0`, whose two commits are the precedent).

## Frozen inputs

- domain contract: `contracts/domain/v1/*.json` `1.7.0`, `supersedes` `1.6.0`, `candidate_revision` 25 (sealed revision 25); this task moves it to `1.8.0`, `supersedes` `1.7.0`, revision 26, and adds no code, identity or machine
- API contract: `contracts/api/v1/openapi.json` `1.7.0`, 95 paths, 107 operations, 314 schemas; this task moves `info.version` and the `ErrorEnvelope.contract_version` const to `1.8.0` and leaves the surface exactly as it is
- analysis/comparison/event contract: analysis and events families `1.7.0` move with the shared literal; `contracts/comparison/v1` carries no version and is not touched
- migration head: `0035_comparison_records`, not touched
- base commit: `85458f07` (tip of `integration/ar-close-1026` at launch)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The task changes a version literal, not a route, screen, error code, migration or any other member of a maintained set; the surface (95 / 107 / 314), the 27 error codes and the migration head do not move.

## Captured premise evidence

- premise: the literal is held by 112 tracked files outside the generated client (185 lines) and by the 4 generated files; six lines in two files are third-party package versions; the three operations named by the ruling are in the contract; the previous minor move and its procedure are known; the baseline `api:verify` is OK

### P-01 — the literal `1.7.0` is held by 112 tracked files outside the generated client, plus 4 generated files; 6 of the lines are not ours
- captured_at: 2026-10-27
- command: `git grep -l '1\.7\.0' -- . ':!web/node_modules' ':!web/src/shared/api/generated' | wc -l; git grep -n '1\.7\.0' -- . ':!web/node_modules' ':!web/src/shared/api/generated' | wc -l; git grep -c '1\.7\.0' -- web/src/shared/api/generated; git grep -n '1\.7\.0' -- web/package-lock.json infra/norms-worker/requirements.lock | cut -c1-120`
- captured_output:
  ```text
  112
  185
  web/src/shared/api/generated/client.gen.ts:1
  web/src/shared/api/generated/index.ts:1
  web/src/shared/api/generated/operations.gen.ts:1
  web/src/shared/api/generated/types.gen.ts:3
  infra/norms-worker/requirements.lock:199:hf-xet==1.7.0 \
  web/package-lock.json:2487:      "version": "1.7.0",
  web/package-lock.json:2488:      "resolved": "https://registry.npmjs.org/es-module-lexer/-/es-module-lexer-1.7.0.tgz",
  web/package-lock.json:2658:      "version": "1.7.0",
  web/package-lock.json:2659:      "resolved": "https://registry.npmjs.org/esquery/-/esquery-1.7.0.tgz",
  web/package-lock.json:3803:        "es-module-lexer": "^1.7.0",
  ```
- interpretation: 112 files and 185 lines outside the generated client; the generated client holds 6 more lines in 4 files. The last block is the only place where `1.7.0` is a third-party version (`es-module-lexer`, `esquery`, `hf-xet`): two files, six lines, class C, which must not change. Every other hit is classified in the table of section «Classification».

### P-02 — every holder of the contract version says `1.7.0` and nothing else; the three catalogs supersede `1.6.0`
- captured_at: 2026-10-27
- command: `git grep -hoE '"(contract_version|name_map_contract_version|analysis_contract_version|supersedes|const)": "1\.[0-9]+\.[0-9]+"' -- contracts/analysis contracts/domain contracts/events | sort | uniq -c; git grep -n '"version": "1\.' -- contracts/api/v1/openapi.json web/openapi/openapi.json; git grep -n 'CONTRACT_VERSION: Final\|contract_version: Literal' -- src; cmp contracts/api/v1/openapi.json web/openapi/openapi.json && echo mirror-identical`
- captured_output:
  ```text
        1 "analysis_contract_version": "1.7.0"
        1 "const": "1.0.0"
        3 "const": "1.6.0"
       15 "const": "1.7.0"
        1 "contract_version": "1.0.0"
       38 "contract_version": "1.7.0"
        1 "name_map_contract_version": "1.7.0"
        3 "supersedes": "1.6.0"
  contracts/api/v1/openapi.json:5:    "version": "1.7.0",
  web/openapi/openapi.json:5:    "version": "1.7.0",
  src/auditmanager/analysis/engine/result.py:35:CONTRACT_VERSION: Final[str] = "1.7.0"
  src/auditmanager/api/routers/__init__.py:208:CONTRACT_VERSION: Final[str] = "1.7.0"
  src/auditmanager/api/schemas/models.py:753:    contract_version: Literal["1.7.0"]
  src/auditmanager/shared/errors/catalog.py:28:CONTRACT_VERSION: Final[str]
  mirror-identical
  ```
- interpretation: The shared version is one literal: 38 `contract_version`, one `analysis_contract_version`, one `name_map_contract_version` and 15 `const` pins, all `1.7.0`; the three domain catalogs and their schemas hold `supersedes` `1.6.0` (3 + 3). The `1.0.0` lines are not the contract version (`crop-manifest.schema.json` pins an `artifact_version`; the domain README quotes an old example) and stay. The API document and its mirror say `1.7.0` and are byte-identical. Three src constants serve the version (`analysis/engine/result.py`, `api/routers/__init__.py`, `api/schemas/models.py`); the domain constant is read from the catalog at import.

### P-03 — the tests that tie the versions together are `test_contract_seal.py` and the facts file; `candidate_revision` is pinned at 25
- captured_at: 2026-10-27
- command: `grep -n 'SEALED = \|PREVIOUS = \|candidate_revision\|startswith((' tests/contract/api_v1/test_contract_seal.py; grep -n 'contract_version' tests/support/expected_facts.json; git grep -n 'candidate_revision' -- tests/contract/test_domain_identifiers_schema.py | head -3`
- captured_output:
  ```text
  33:SEALED = "1.7.0"
  35:PREVIOUS = "1.6.0"
  60:                and value.startswith(("1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0"))
  135:    assert catalog["candidate_revision"] == 25
  145:    assert properties["candidate_revision"]["const"] == 25
  864:  "contract_version": "1.7.0"
  tests/contract/test_domain_identifiers_schema.py:20:It also asserts that the schema pins the catalog's ``candidate_revision``: the pin is what keeps
  tests/contract/test_domain_identifiers_schema.py:121:def test_the_schema_pins_the_catalogs_candidate_revision() -> None:
  tests/contract/test_domain_identifiers_schema.py:122:    catalog_revision = _load(CATALOG_PATH)["candidate_revision"]
  ```
- interpretation: `SEALED`, `PREVIOUS` (`1.6.0`), the two `== 25` pins and the list of retired version prefixes are the lines that move; the facts file carries the independent literal. `test_domain_identifiers_schema.py` reads the revision from the catalog and compares it with the schema, it holds no literal.

### P-04 — the three operations of wave B are in the contract and the surface is 95 / 107 / 314 under `info.version` `1.7.0`
- captured_at: 2026-10-27
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));ops=sorted(o['operationId'] for p in d['paths'].values() for o in p.values() if isinstance(o,dict) and 'operationId' in o);print(d['info']['version'],len(d['paths']),len(ops),len(d['components']['schemas']));print([x for x in ops if x in ('approveSheetPairing','withdrawSheetPairing','generateComparisonSummary')])"`
- captured_output:
  ```text
  1.7.0 95 107 314
  ['approveSheetPairing', 'generateComparisonSummary', 'withdrawSheetPairing']
  ```
- interpretation: `1.7.0`, 95 paths, 107 operations, 314 schemas, and the three operations named by `R-146ar` exist. The surface does not change in this task.

### P-05 — the owner ruling R-146ar chooses 1.8.0 now and keeps 2.0.0 reserved
- captured_at: 2026-10-27
- command: `grep -n 'R-146ar' docs/program/OWNER_RULINGS_2026-09-17.md | cut -c1-700`
- captured_output:
  ```text
  1802:| `R-146ar` | *Contract version.* Chosen: «1.8.0 сейчас» (recommended). Three operations of wave B (`approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`) are an additive minor change: `info.version` moves to `1.8.0` with the mechanical rewrite of the literal in the files that pin it and a `web/FRONTEND_LOCK.json` reseal. `2.0.0` stays reserved for the removal of `AnalysisProfileStatus.builtin` (`D-233`). |
  1813:| `R-146bc` | *Order of the next window.* Chosen: «АР: решения по цитатам + отчёт норм + активация v3» first; then the small items (`R-146ax`, `R-146ay`, `R-146az`, `R-146ar`, the switch of `R-146ba`), then the sections (`R-146ao`, `R-146aq`), then the presets (`R-146av`). The watchdog against a page limit (`R-146y`) waits for the capacity measurement. |
  ```
- interpretation: The ruling states the whole scope: `info.version` to `1.8.0`, the mechanical rewrite of the literal in the files that pin it, a `web/FRONTEND_LOCK.json` reseal; `2.0.0` stays reserved (`D-233`) and is not touched.

### P-06 — the precedent of a minor move is two commits: the literal across the families, then the regenerated client and lock
- captured_at: 2026-10-27
- command: `git show --stat --format='%h %s' b7e5fdf1 | tail -1; git show --stat --format='%h %s' 56b25ebe | tail -1; git show b7e5fdf1 --format= --name-only -- tests/contract tests/support src infra`
- captured_output:
  ```text
   89 files changed, 173 insertions(+), 155 deletions(-)
   5 files changed, 21 insertions(+), 21 deletions(-)
  infra/deploy/proxy/nginx.conf
  infra/deploy/proxy/tls-server.conf
  src/auditmanager/analysis/engine/result.py
  src/auditmanager/api/routers/__init__.py
  src/auditmanager/api/schemas/models.py
  tests/contract/api_v1/test_contract_seal.py
  tests/support/expected_facts.json
  ```
- interpretation: The previous move (`1.6.0` to `1.7.0`) touched 89 files in one commit (families, `candidate_revision` 24 to 25 with `supersedes`, src constants, the edge, two Python test files, web tests) and 5 files in a second (client and lock). Its content commit is the first one, which the lock names.

### P-07 — the repo's reseal procedure is `api:generate` then a hand-written lock update checked by `api:verify` and by the lock guard; the baseline verifies
- captured_at: 2026-10-27
- command: `grep -n '"api:' web/package.json; grep -n 'info_version\|content_commit"\|"sha256\|snapshot_sha256' web/FRONTEND_LOCK.json | cut -c1-140; npm --prefix web run api:verify 2>&1 | tail -1`
- captured_output:
  ```text
  19:    "api:generate": "node scripts/generate-api-client.mjs",
  20:    "api:verify": "node scripts/generate-api-client.mjs --check",
  19:    "sha256": "f49b6329844442ec8965a9a5dd559983a067881c489c81857d45fd60e7f5d5de",
  20:    "content_commit": "003c7446",
  25:    "info_version": "1.7.0",
  30:    "snapshot_sha256": "f49b6329844442ec8965a9a5dd559983a067881c489c81857d45fd60e7f5d5de",
  generate-api-client --check: OK - 107 operations, contract sha256 f49b6329844442ec8965a9a5dd559983a067881c489c81857d45fd60e7f5d5de
  ```
- interpretation: `api:generate` rewrites the four generated files and the mirror from `contracts/api/v1/openapi.json`; the lock's digests, `info_version` and `content_commit` are edited by hand and recomputed by `web/tests/guards/frontend-lock.guard.test.ts`. Baseline: `api:verify` is OK before any change.

### P-08 — the live prose that states the contract version is `docs/program/CURRENT_STATE.md` (three sentences), the two contract READMEs and the last sentence of `info.description`
- captured_at: 2026-10-27
- command: `grep -n -o 'contract stays .1.7.0., prose only\|info.version. is still .1.7.0.\|shared contract is .1.7.0. after\|^## Version .1.7.0.\|^# Domain contract v1 . .1.7.0.\|The contract version stays 1.7.0 (a minor bump' docs/program/CURRENT_STATE.md contracts/api/v1/README.md contracts/domain/v1/README.md contracts/api/v1/openapi.json`
- captured_output:
  ```text
  docs/program/CURRENT_STATE.md:3:contract stays `1.7.0`, prose only
  docs/program/CURRENT_STATE.md:3:info.version` is still `1.7.0`
  docs/program/CURRENT_STATE.md:14:shared contract is `1.7.0` after
  contracts/api/v1/README.md:14:## Version `1.7.0`
  contracts/domain/v1/README.md:1:# Domain contract v1 — `1.7.0`
  contracts/api/v1/openapi.json:7:The contract version stays 1.7.0 (a minor bump
  ```
- interpretation: Two sentences of the 2026-10-27 paragraph and the contract sentence of the stable section in `CURRENT_STATE.md`; the heading of each README; and the final sentence of the wave-B paragraph of `info.description`, which says the version «stays 1.7.0 ... is the integrator's step». The other two wave sentences of `info.description` («moves from 1.6.0 to 1.7.0», «stays 1.7.0 (prose only)») are true statements about their own wave and stay.


## Classification of every hit

Taken before any edit from `git grep -n '1\.7\.0' -- . ':!web/node_modules'` (191 lines in 116 unique files: the 185 lines of P-01 plus the 6 of the generated client). The per-kind counts below count a file once per kind (the two OpenAPI files hold a class A line and a class H line), so they add up to 118 files 191 hits.

| kind | files | lines | meaning and rule |
| --- | --- | --- | --- |
| A1 | 2 | 4 | the API document: `info.version` / the `ErrorEnvelope.contract_version` const (contract and its web mirror) |
| A2 | 30 | 58 | the shared version in the analysis / domain / events contract families (catalogs, schemas, examples, one `revision_note`) |
| A3 | 6 | 8 | a literal the running system serves: a src constant, the edge error bodies, the web forwarder error body |
| A4 | 2 | 2 | the independent pin of the version: the facts file and the seal test |
| A5 | 4 | 6 | the generated web client (regenerated, never edited) |
| A6 | 1 | 3 | the web lock (`FRONTEND_LOCK.json`: version, digests, commit note) |
| A7 | 2 | 3 | the live version line of a contract README |
| B1 | 49 | 61 | web test whose fixture or assertion quotes the served version (typed by the generated `ErrorEnvelope`) |
| B2 | 1 | 2 | live prose: `CURRENT_STATE.md` |
| H | 19 | 38 | historical record that quotes the version as it was (program docs, task files, the old paragraphs of `info.description`) |
| C | 2 | 6 | UNRELATED: a third-party package version |

Rules. A (the contract version itself) and B (live quotations of it) move to `1.8.0`. H keeps its words: a task file, a report or a register row says what was true on the day it was written (`AGENTS.md` and `docs/templates/TASK_TEMPLATE.md`: historical evidence is immutable), and the first two wave paragraphs of `info.description` («moves from 1.6.0 to 1.7.0», «stays 1.7.0 (prose only)») stay for the same reason; only the last sentence of the wave-B paragraph, which promised «the integrator's step», is rewritten to say that the step happened. C is not ours and does not change. Beside the literal, three things move with it exactly as in the previous move (`b7e5fdf1`): `supersedes` `1.6.0` to `1.7.0` and `candidate_revision` 25 to 26 (with its `revision_note`) in the three domain catalogs and their schemas, the two `== 25` pins and `PREVIOUS` in the seal test, and the list of retired version prefixes in the seal test's walk gains `1.7.0`.

| path | lines | kind |
| --- | --- | --- |
| `contracts/analysis/ar_v3_beta/v1/stage.json` | 4 | A2 |
| `contracts/analysis/v1/crop-manifest.schema.json` | 5 | A2 |
| `contracts/analysis/v1/examples/job-package.example.json` | 2, 11 | A2 |
| `contracts/analysis/v1/examples/result-package.example.json` | 2, 11, 15, 41, 67, 86, 105, 133, 152, 170, 185 | A2 |
| `contracts/analysis/v1/examples/result-package.missing-attempt-authority.invalid.json` | 2, 10, 14 | A2 |
| `contracts/analysis/v1/examples/stage-result.example.json` | 2 | A2 |
| `contracts/analysis/v1/examples/stage-result.failed-missing-error.invalid.json` | 2 | A2 |
| `contracts/analysis/v1/examples/stage-result.succeeded-with-error.invalid.json` | 2 | A2 |
| `contracts/analysis/v1/job-package.schema.json` | 5, 20, 114 | A2 |
| `contracts/analysis/v1/legacy-stage-map.json` | 3 | A2 |
| `contracts/analysis/v1/legacy-stage-map.schema.json` | 5, 25 | A2 |
| `contracts/analysis/v1/legacy-stage-name-map.json` | 3 | A2 |
| `contracts/analysis/v1/legacy-stage-name-map.schema.json` | 5, 28 | A2 |
| `contracts/analysis/v1/portal-blocks.schema.json` | 5 | A2 |
| `contracts/analysis/v1/result-package.schema.json` | 5, 19, 115, 123, 137 | A2 |
| `contracts/analysis/v1/stage-registry.json` | 3, 12 | A2 |
| `contracts/analysis/v1/stage-registry.schema.json` | 5, 28, 130 | A2 |
| `contracts/analysis/v1/stage-result.schema.json` | 5, 19 | A2 |
| `contracts/api/v1/README.md` | 14 | A7 |
| `contracts/api/v1/openapi.json` | 5, 7889 | A1 |
| `contracts/api/v1/openapi.json` | 7 | H |
| `contracts/domain/v1/README.md` | 1, 7 | A7 |
| `contracts/domain/v1/error-codes.json` | 3, 6 | A2 |
| `contracts/domain/v1/error-codes.schema.json` | 30 | A2 |
| `contracts/domain/v1/error-envelope.schema.json` | 17 | A2 |
| `contracts/domain/v1/examples/error-envelope.example.json` | 2 | A2 |
| `contracts/domain/v1/examples/error-envelope.unknown-code.invalid.json` | 2 | A2 |
| `contracts/domain/v1/identifiers.json` | 3, 6 | A2 |
| `contracts/domain/v1/identifiers.schema.json` | 39 | A2 |
| `contracts/domain/v1/state-machines.json` | 3, 6 | A2 |
| `contracts/domain/v1/state-machines.schema.json` | 31 | A2 |
| `contracts/events/v1/event-envelope.schema.json` | 20 | A2 |
| `contracts/events/v1/examples/event-envelope.example.json` | 2 | A2 |
| `contracts/events/v1/examples/event-envelope.legacy-schema-version.invalid.json` | 2 | A2 |
| `docs/program/COMPARE-PERSISTED-SUMMARY-01.md` | 12, 45, 221, 227 | H |
| `docs/program/CURRENT_STATE.md` | 3, 14 | B2 |
| `docs/program/DEBT_REGISTER.md` | 150, 153, 157, 158 | H |
| `docs/program/OPT-PROJECT-ALL-SECTIONS-01.md` | 19 | H |
| `docs/program/PROD-11-AR-V1-V2-REMOVAL-01.md` | 13, 28 | H |
| `docs/program/ROADMAP-GAP-2026-10-27.md` | 3, 73, 370 | H |
| `docs/program/dispatch/PRODUCTION-WAVE-PW4.md` | 63 | H |
| `docs/program/tasks/COMPARE-PERSISTED-SUMMARY-01.md` | 18, 19, 289, 291, 294 | H |
| `docs/program/tasks/HARDEN-01.md` | 18 | H |
| `docs/program/tasks/OPT-PROJECT-ALL-SECTIONS-01.md` | 21, 221, 228, 236, 368 | H |
| `docs/program/tasks/PROD-11-AR-V1-V2-REMOVAL-01.md` | 494 | H |
| `docs/program/tasks/ROADMAP-GAP-2026-10-27.md` | 17, 51, 54 | H |
| `docs/program/tasks/SEC-DB-TERSE-ERRORS-01.md` | 18 | H |
| `docs/program/tasks/SECTION-PROMPT-SENTENCE-GUARD-01.md` | 19 | H |
| `docs/program/tasks/SECTION-WIDEN-G1-01.md` | 19 | H |
| `docs/program/tasks/SECTION-WIDEN-G2-01.md` | 19 | H |
| `docs/program/tasks/SECTION-WIDEN-G3-01.md` | 20 | H |
| `docs/program/tasks/WEB-SECTION-COPY-01.md` | 20 | H |
| `infra/deploy/proxy/nginx.conf` | 493, 506 | A3 |
| `infra/deploy/proxy/tls-server.conf` | 205, 211 | A3 |
| `infra/norms-worker/requirements.lock` | 199 | C |
| `src/auditmanager/analysis/engine/result.py` | 35 | A3 |
| `src/auditmanager/api/routers/__init__.py` | 208 | A3 |
| `src/auditmanager/api/schemas/models.py` | 753 | A3 |
| `tests/contract/api_v1/test_contract_seal.py` | 33 | A4 |
| `tests/support/expected_facts.json` | 864 | A4 |
| `web/FRONTEND_LOCK.json` | 21, 23, 25 | A6 |
| `web/openapi/openapi.json` | 5, 7889 | A1 |
| `web/openapi/openapi.json` | 7 | H |
| `web/package-lock.json` | 2487, 2488, 2658, 2659, 3803 | C |
| `web/src/shared/api/credentialed-forward.ts` | 212 | A3 |
| `web/src/shared/api/generated/client.gen.ts` | 11 | A5 |
| `web/src/shared/api/generated/index.ts` | 9 | A5 |
| `web/src/shared/api/generated/operations.gen.ts` | 10 | A5 |
| `web/src/shared/api/generated/types.gen.ts` | 9, 17, 1099 | A5 |
| `web/tests/guards/gender-agreement.guard.test.ts` | 271, 312 | B1 |
| `web/tests/guards/rendered-language.guard.test.ts` | 1015, 1027, 1837, 2033, 3541, 3563 | B1 |
| `web/tests/unit/analysis-settings/analysis-settings.test.ts` | 348 | B1 |
| `web/tests/unit/analysis-settings/ar-v3-beta-pack-status.test.ts` | 259 | B1 |
| `web/tests/unit/analysis-settings/ar-v3-group-start-failure.test.ts` | 34 | B1 |
| `web/tests/unit/analysis-settings/run-list-ar-v3-live.test.ts` | 72 | B1 |
| `web/tests/unit/api/authorization-state.test.ts` | 45 | B1 |
| `web/tests/unit/api/credentialed-forward.test.ts` | 160, 801 | B1 |
| `web/tests/unit/api/failure-message.test.ts` | 36 | B1 |
| `web/tests/unit/api/failure-surface.test.ts` | 48 | B1 |
| `web/tests/unit/api/server-credential.test.ts` | 111 | B1 |
| `web/tests/unit/blocks/portal-states.test.ts` | 42 | B1 |
| `web/tests/unit/comparison/comparison-summary.test.ts` | 128 | B1 |
| `web/tests/unit/comparison/decision-carryover.test.ts` | 137 | B1 |
| `web/tests/unit/comparison/sheet-pairing.test.ts` | 138 | B1 |
| `web/tests/unit/dispatcher/dispatcher.test.ts` | 95 | B1 |
| `web/tests/unit/execution/execution-screens.test.ts` | 41 | B1 |
| `web/tests/unit/export/export-panel-xlsx.test.ts` | 26 | B1 |
| `web/tests/unit/norm-references/norm-references.test.ts` | 225 | B1 |
| `web/tests/unit/norms/catalogue.test.ts` | 29 | B1 |
| `web/tests/unit/norms/document-view.test.ts` | 117 | B1 |
| `web/tests/unit/norms/norms-screen.test.ts` | 41 | B1 |
| `web/tests/unit/norms/presentation.test.ts` | 20 | B1 |
| `web/tests/unit/optimisation/fixtures.ts` | 206 | B1 |
| `web/tests/unit/projects/create-and-list-failure.test.ts` | 17 | B1 |
| `web/tests/unit/projects/upload-failure.test.ts` | 26 | B1 |
| `web/tests/unit/qa_w49/epoch-401-closes-the-session.test.ts` | 46, 98 | B1 |
| `web/tests/unit/qa_w49/sign-in-status-and-throttle.test.ts` | 38 | B1 |
| `web/tests/unit/run/input-budget.test.ts` | 45, 135 | B1 |
| `web/tests/unit/run/polling.test.ts` | 153, 182 | B1 |
| `web/tests/unit/run/run-failure.test.ts` | 23 | B1 |
| `web/tests/unit/screens/cold-load.test.ts` | 80 | B1 |
| `web/tests/unit/screens/home.test.ts` | 166 | B1 |
| `web/tests/unit/screens/run-list-ar-start.test.ts` | 69 | B1 |
| `web/tests/unit/screens/run-list-ar-v3-start.test.ts` | 51 | B1 |
| `web/tests/unit/screens/stage-comparison.test.ts` | 155 | B1 |
| `web/tests/unit/screens/widgets.test.ts` | 135 | B1 |
| `web/tests/unit/section-specification/section-specification.test.ts` | 284 | B1 |
| `web/tests/unit/sections/fixtures.ts` | 98 | B1 |
| `web/tests/unit/session/account-fixture.ts` | 40, 57 | B1 |
| `web/tests/unit/specification-prices/specification-prices.test.ts` | 261 | B1 |
| `web/tests/unit/start-run/executor-refusal.test.ts` | 48 | B1 |
| `web/tests/unit/start-run/executor-select.test.ts` | 128, 147 | B1 |
| `web/tests/unit/styles/screens.ts` | 144 | B1 |
| `web/tests/unit/upload/price-list-upload-failure.test.ts` | 55 | B1 |
| `web/tests/unit/widgets/registration-queue.test.ts` | 38 | B1 |
| `web/tests/unit/widgets/user-management.test.ts` | 32 | B1 |
| `web/tests/unit/workers/executor-connections.test.ts` | 42 | B1 |
| `web/tests/unit/workers/workers.test.ts` | 64 | B1 |

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The H rows above are left as they are; nothing in them is corrected.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `contracts/analysis/**`
- `contracts/domain/v1/**`
- `contracts/events/v1/**`
- `contracts/api/v1/openapi.json`
- `contracts/api/v1/README.md`
- `web/openapi/openapi.json`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/credentialed-forward.ts`
- `web/tests/unit/**`
- `web/tests/guards/**`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/schemas/models.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `tests/contract/api_v1/test_contract_seal.py`
- `tests/support/expected_facts.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CONTRACT-1-8-0-01.md`
- `docs/program/CONTRACT-1-8-0-01.md`

## Forbidden hotspots

- `db/migrations/**` and every migration pin (the head stays `0035_comparison_records`)
- every contract content other than the version literal: no path, operation, schema, enum value, error code, description of an operation (the one sentence of `info.description` named in the rules above and the README version sections are the only prose)
- `src/**` other than the three version constants
- root dependency and lock files (`uv.lock`, `pyproject.toml`, `web/package.json`, `web/package-lock.json`), composition roots, global styles, `.github/**`
- `docs/program/DEBT_REGISTER.md`, `docs/program/OWNER_RULINGS_2026-09-17.md` and every other history record (class H)
- the reservation of `2.0.0` and `AnalysisProfileStatus.builtin` (`D-233`)

## Non-goals

- no new operation, schema, error code or migration; no change of the surface
- no push, no tag, no change of the product `VERSION` (`0.8.2`)
- no edit of the class H records (17 program docs and task files; the two OpenAPI files only in the one sentence named above) and no edit of the register or the rulings
- no `npm ci`; `web/node_modules` is a symlink to the gate-night tree's

## Deliverables

- the mechanical rewrite as one commit (the content commit the lock names), then the regenerated client and the resealed lock as a second commit (the shape of `b7e5fdf1` and `56b25ebe`)
- this file, with the classification above, and `docs/program/CONTRACT-1-8-0-01.md` (files, commands with counts, mutation proof, before and after of every modified test, limits, proof that the forbidden paths are untouched)

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract tests/unit/api --deselect=tests/contract/test_cp00_candidate.py --deselect=tests/contract/test_validate_bootstrap.py --deselect=tests/contract/test_cp00_final_state.py`
- expected: all green (the three D-220 files are not run); `tests/contract/program` is run after the commit because it refuses a dirty tree
- command: `npm --prefix web run api:verify; cd web && npx vitest run tests/guards tests/unit && npx tsc --noEmit && npx eslint .`
- expected: `api:verify` OK, the web suites green, `tsc` and `eslint` exit 0
- command: `git diff --check`
- expected: no output

## Integration contract

After this task every holder of the shared contract version says `1.8.0`; `GET /api/v1/...` error bodies carry `contract_version` `1.8.0` from the application, from the edge and from the web forwarder alike; `FACTS.contract_version` is `1.8.0`; the generated client exports `CONTRACT_VERSION = '1.8.0'`. A consumer that pinned `1.7.0` literally must move (the list is class A and B above). The surface, the error catalogue and the migration head are unchanged.

## Failure/idempotency/security cases

- a holder left on `1.7.0` fails `tests/contract/api_v1/test_contract_seal.py` (mutation proof in the report)
- a stale digest in `web/FRONTEND_LOCK.json` fails `web/tests/guards/frontend-lock.guard.test.ts`; a client not regenerated fails `api:verify`
- no behaviour, authorisation or data path changes

## Rollback / feature flag

Not applicable: a version literal. The two commits revert together (`git revert` of the second, then the first).

## Handoff

- changed files: filled in at the end (see the report)
- commands/results: filled in at the end
- known limits: filled in at the end
- integration notes: filled in at the end
