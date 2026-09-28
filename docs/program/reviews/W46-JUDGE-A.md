# W46-JUDGE-A — the merged tip `130200d`, sub-stage A of wave 46

**Judge:** `W46-JUDGE-A` (relaunch; the first run died on a host restart before it committed
anything) · **lane:** `gate-w46j` (PostgreSQL `127.0.0.1:56390`, S3 `59990`/`59991`) ·
**worktree:** `/root/w46j` · **branch:** `agent/w46-judge` · **tree judged:** `130200d`.

This file is committed as it is written. A section marked *in progress* is not a conclusion.

## 0. Provisioning

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK
.venv/bin/python -c "import boto3"                     -> boto3 ok
npm --prefix web ci                                    -> added 184 packages
```

## 1. Does the merged tree gate? — **No.**

```
cd /root/w46j && make gate > /root/w46j-gate.log 2>&1      # the canonical command, literally
grep -c 'GATE OK' /root/w46j-gate.log                        -> 0
```

Run on `5f21ae4` (= `130200d` plus this file only; `docs/program/reviews/` is outside every
prose guard's named scope), 06:28:01Z–06:43:44Z. The log ends:

```
7 failed, 2493 passed, 5 skipped, 4 warnings, 169 subtests passed in 863.10s (0:14:23)
GATE: the canonical battery failed with pytest exit status 1.
make: *** [Makefile:1026: gate] Error 1
```

Foundation **35 passed**. The harness reported my wrapper's `exit code 0` for this run; the
wrapper's own `$?` file says `2` and the log has no `GATE OK` line. §4.6 fired a sixth time.
Host load average was 32–95 on 8 cores during the run, so every red below was read for
contention before being believed: none of the seven builds, deploys or times anything, and
each asserts a literal count or set against `openapi.json`.

**The battery stops the gate, so the gate never ran the frontend.** I ran the two commands
`run_frontend` would have run, separately, after the battery finished:

```
npm --prefix web run typecheck    -> exit 0
npm --prefix web test             -> Test Files 1 failed | 78 passed (79)
                                     Tests      2 failed | 1118 passed (1120)
git diff --check                  -> exit 0
```

### The nine reds, by whose grant they sit in

| # | test | what it says | whose |
|---|---|---|---|
| 1 | `tests/contract/api_v1/test_doc_prose_facts.py::test_the_scanned_docs_state_the_contract_surface_this_tree_has` | `CURRENT_STATE.md` and `ALPHA_ROADMAP.md` say 16/19/53 | integrator (docs) — **predicted by `W46-SEAL` §7** |
| 2 | `tests/contract/api_v1/test_surface_counts_in_prose.py::test_the_api_prose_states_the_surface_this_document_declares` | "nineteen operations" ×6 in `infra/deploy/README.md`, `serve.py`, `bff/v1/[...path]/route.ts`, `authorization.ts`; "sixteen paths" in `route.ts` | integrator (`infra/**`, and `web/src` after merge) — **predicted by `W46-SEAL` §7** |
| 3 | `tests/contract/domain_p02/test_openapi_document.py::test_the_surface_is_exactly_the_declared_capabilities` | extra `getDashboardSummary` in the operation set | **`W46-SEAL`'s own grant (`tests/**`), not reported** |
| 4 | `tests/contract/domain_p02/test_openapi_document.py::test_every_operation_requires_the_bearer_scheme` | the same pinned set, a second copy | **`W46-SEAL`'s own grant, not reported** |
| 5 | `tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation` | `getDashboardSummary declares no client-fault response` — `{200,401,403,500,503} & {404,409,422}` is empty | **a rule, not a pin** — see finding F-2 |
| 6 | `tests/contract/domain_p02/test_seam_register.py::test_the_api_operation_table_matches_the_frozen_document` | `docs/program/P02_SEAMS.md`'s operation table lacks `('getDashboardSummary', 'GET /dashboard')` | integrator (docs), **not reported by anyone** |
| 7 | `tests/e2e/pc01/test_acceptance.py::test_c1_the_application_composes_from_the_environment_and_answers` | `assert len(client.app.router.routes) == 19` → 20 | integrator (`tests/e2e/**`), **not reported by anyone** |
| 8 | `web/tests/contract/seam-operations.contract.test.ts` › *are exactly the operations the client exposes* | `SEAM_OPERATIONS` has no `getDashboardSummary` | `web/tests` — predicted by `W46-SEAL` §7 |
| 9 | same file › *includes both authorization codes…* | `expected … to have a length of 19 but got 20` | same file; `W46-SEAL` §7 named the file but said both reds were in the first `describe` — one is in `the error catalog` |

**Five of the nine (#3–#7) were in nobody's report.** #3–#5 sit in
`W46-SEAL`'s own `allowed_paths` and in **the very file `D-105` names as a pin site**
(`test_openapi_document.py:493`, the error-code count, one assertion over from #3). They
reproduce at `W46-SEAL`'s own tip by construction —
`git diff --stat ce47316 130200d -- tests/contract/domain_p02 contracts/` is empty — so
they were red on the branch that made them, which means the branch never ran the canonical
battery: `W46-SEAL.md` §4.1 says the two extra pins were found by "running the actual
canonical battery (not a chosen scope)", and its §8 lists only named suites and defers the
`make gate` result to "the final report handed to the integrator" — the one that never
arrived. **A battery run from that tree would have printed #3–#5.**

## 2. `web/FRONTEND_LOCK.json` — recomputed or carried? — **Recomputed.**

Every 64-hex value in the file, recomputed with `hashlib.sha256` over the merged tree:

| field | file | result |
|---|---|---|
| `toolchain.lockfile_sha256` | `web/package-lock.json` | match `98691bc8…` |
| `openapi.sha256` | `contracts/api/v1/openapi.json` | match `20980cb3…` |
| `openapi.snapshot_sha256` | `web/openapi/openapi.json` | match `20980cb3…` |
| `generator.script_sha256` | `web/scripts/generate-api-client.mjs` | match `787c744d…` |
| `generated.files.client.gen.ts` | generated | match `f9bcfd18…` |
| `generated.files.index.ts` | generated | match `b2596c2e…` |
| `generated.files.operations.gen.ts` | generated | match `63e88502…` |
| `generated.files.types.gen.ts` | generated | match `a7dc6f23…` |

`openapi.paths/operations/component_schemas` = 17/20/61 = the document. The two unchanged
digests are **legitimately carried**: `git diff --stat alpha-w45 130200d -- web/package-lock.json
web/scripts/generate-api-client.mjs web/package.json` is empty. A matching digest only proves the
lock agrees with the files, so I also asked whether **the files agree with the generator**:
`npm --prefix web run api:verify` → `generate-api-client --check: OK - 20 operations, contract
sha256 20980cb3…` — the committed client is byte-identical to a fresh generation, and the
mirror to the contract. Not a hand-edited client with its hash taken afterwards.

Two things that are not digests:

- `openapi.content_commit` is `d55012a`, whose `openapi.json` hashes to `00b16114…` (the
  **pre**-reseal contract). That is a documented convention — the `commit_note` says a commit
  cannot name itself and "THE AUTHORITY IS THE DIGEST" — and it has held since `alpha-w42`
  (`667a49c`, `a49d047` behave the same way). `frontend-lock.guard.test.ts:103` checks only
  that it is hex. Not a finding; recorded so nobody mistakes it for one.
- **The `commit_note` states something false about git.** It says the two further pin files
  "moved in this reseal's own git history, **before** this commit". `git show --stat d7ac848`
  shows `test_openapi_conformance.py` and `test_served_document_and_health_plane.py` **in**
  that commit, which is what `W46-SEAL.md` §1 also says. Low severity; a lock file is read by
  the next resealer.

## 3. `getDashboardSummary`, driven — *in progress*

## 4. `/dashboard` at 780 px, both palettes; the `SEEDS` and cache-state edits — *in progress*

## 5. Can the per-section panel be made to show an invented number? — *in progress*

## 6. Off the trail — *in progress*
