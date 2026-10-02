# W48-PROSE — tracked prose discovery and independent pin registry

## 1. Result

Task `W48-PROSE` is complete on dispatch base
`9b5219e69fe87fb710c55e8f0643ba9af74c2be0`. The focused suite is green at **59 passed**.

- D-98: the count parser no longer has a surface-noun allow-list. Canonical nouns retain exact
  dimension checks; an unknown noun is judged from an explicit API-surface/document assertion
  and values derived from actual contract/catalog history.
- D-99: files come from `git ls-files`; Dockerfiles, `.yml`, `.conf`, `.example`, `.sh` and
  extensionless tracked text have no suffix escape.
- D-100: `docs/program/P02_SEAMS.md` is a named live specification in that tracked inventory and
  has its own mutation.
- D-104: live `CURRENT_STATE.md` must point to `infra/deploy/verify-deployed.sh` and may not state
  a deployed SHA snapshot. The prose itself was already corrected by `MAIN-REF-POLICY-01`.
- D-105: `CONTRACT_PIN_REGISTRY.md` enumerates **25** independent pins: 20 surface, 3 error
  catalog, 1 application migration head and 1 history-boundary convention. Discovery finds the
  same 25 and fails on an unknown path or an extra pin in a registered path.
- D-115: every historical heading must have the real shape, waves must be unique/newest-first,
  the first must equal the highest `alpha-w*` tag, and the live prefix must retain surface,
  migration and deployed-verification facts.
- D-76 stays load-bearing: `KNOWN_OUTSTANDING_CLAIMS` remains empty.

No contract, migration, generated client, dependency, runtime behaviour, deployment command,
configuration value, workflow, ref, tag or alpha host changed.

## 2. Discovery evidence

The tracked inventory contains **1,448** paths: **1,421 UTF-8 text** and **27 binary**. The live
surface families contain **265 tracked paths**, all 265 UTF-8 text; there is no binary,
non-UTF-8 or unreadable file silently skipped in that scope.

The scanner reads the current four values from the frozen documents and derives this historical
value set by walking Git objects for the OpenAPI document and error catalog:

```text
10 12 13 14 15 16 17 18 19 20 21 22 43 46 48 50 51 53 61
```

This is why `eighteen declarations`, `fifteen copies`, `fifteen places`, an unknown noun such as
`twelve widgets`, and old counts in nonstandard suffixes are detectable without teaching the
scanner those nouns or suffixes. Arbitrary local numbers do not become surface claims merely
because a nearby comment mentions a contract. Exact local-subset exemptions and the one retained
historical P02 sentence are explicit and tested for continued existence.

Corrections made from the first widened scan:

| path | correction |
|---|---|
| `src/auditmanager/api/app.py` | documentation application says twenty declarations; a stale router-count comment no longer restates a count |
| `src/auditmanager/api/routers/declarations.py` | twenty repeated declaration sites; other comments avoid obsolete response/signature counts |
| `infra/deploy/proxy/nginx.conf` | twelve paths → seventeen; fifteen operations → twenty |
| `infra/deploy/env/alpha.env.example` | removes the obsolete count and the now-false claim that `.example` is unscanned |
| `infra/deploy/deploy.sh` | removes an obsolete numeric history restatement; names the tracked-text guard |
| `docs/program/P02_SEAMS.md` | retains the historical defect, but corrects its false present-tense claim that no scanner reads the file |

## 3. Pin inventory

`docs/program/CONTRACT_PIN_REGISTRY.md` is machine-readable JSON inside maintained prose. Each
entry has a unique id, family, path, exact live needle and the event that moves it. The guard:

1. proves every needle occurs exactly once;
2. discovers frozen count/set assignments and semantic literal assertions across tests;
3. adds the three frontend-lock surface values and history-boundary shape;
4. refuses any discovered path absent from the registry or any per-path candidate count greater
   than its registered entries.

Measured result: **25 registered / 25 discovered**, with no outside path and no overflow.
The registry does not derive expected values from the artifact being judged; the existing owning
tests remain the independent comparison.

## 4. Mutation evidence

All mutations are in-memory/synthetic and leave the worktree unchanged.

| debt/family | mutation | proof |
|---|---|---|
| D-98 | `the API surface has twelve widgets` | unknown noun is returned as a stale historical surface value |
| D-99 | real `nginx.conf`: `seventeen paths` → `sixteen paths` | `.conf` mutation appears in `_wrong_surface_claims` |
| D-100 | real P02 live claim: twenty → nineteen operations | named P02 mutation appears in `_wrong_surface_claims` |
| D-115 | correctly shaped active-wave historical heading before the real boundary | first heading disagrees with highest tag and fails |
| surface pin | remove one registered surface needle in memory | exact `pin_id` reports zero live occurrences |
| error-catalog pin | remove one registered error needle in memory | exact `pin_id` reports zero live occurrences |
| migration-head pin | remove the registered head needle in memory | exact `pin_id` reports zero live occurrences |
| history-boundary pin | remove the registered boundary-shape needle in memory | exact `pin_id` reports zero live occurrences |

The opposite directions are also covered: current surface values pass; the genuine newest-first
history sequence resolves to the tagged tip; historical wave reports remain outside the live-doc
scan; a fenced marker is not a boundary; code-unit/point numbers are not catalog counts.

## 5. Checks

```text
baseline:
  .venv/bin/python -m pytest \
    tests/contract/api_v1/test_surface_counts_in_prose.py \
    tests/contract/api_v1/test_doc_prose_facts.py -q
  47 passed in 0.81s

final:
  .venv/bin/python -m pytest \
    tests/contract/api_v1/test_surface_counts_in_prose.py \
    tests/contract/api_v1/test_doc_prose_facts.py -q
  59 passed in 1.68s

comment-only proof:
  Python AST after removing docstring nodes: unchanged for app.py and declarations.py
  nonblank/noncomment deploy/config lines: unchanged for deploy.sh, alpha.env.example,
  nginx.conf

git diff --check
  exit 0, empty output
```

The repository environment has no `.venv/bin/ruff`, so no standalone Ruff claim is made. The
focused pytest import/collection executes both changed test modules. The integrator still owes
the complete merged `make gate`; this lane does not substitute its focused result for that gate.

## 6. Contracts, limits and integration

Contracts and migration head remain frozen: API 17 paths / 20 operations / 61 schemas, error
catalog 22, migration `0013_norm_embeddings`. The scanner intentionally does not claim natural
language understanding. For an unknown noun it requires explicit surface/document context and a
value observed in real contract history. `W48-JUDGE-A` must independently invent another noun,
path and tracked suffix; a novel arbitrary number outside that evidence is not classified as a
surface size.

Integration instructions:

1. merge this lane with `W48-GUARDS` only after reading `W48-AUDIT` separately;
2. run the two focused files, then full `make gate` on the exact Stage-A merge;
3. run judge A's unlisted noun/suffix/P02/early-boundary/pin mutations from a scratch copy;
4. do not edit the debt register in this lane; close rows by integrator/GOV addendum after judge
   acceptance;
5. publish an accepted development candidate to `origin/dev`; do not update `origin/main`
   without a separate direct owner instruction for the exact SHA.

Rollback is a revert of this task commit. No data, host, credential or feature-flag rollback is
required.
