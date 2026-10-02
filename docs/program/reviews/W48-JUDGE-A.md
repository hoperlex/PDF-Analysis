# W48-JUDGE-A — Stage-A false-green judge

## 1. Subject, boundary and verdict

- **Subject:** `39e06c2cae7531481da80b0ace70668d26b1416e`
  (`test(W48): close guard false greens`), the accepted local merge of `W48-PROSE` and
  `W48-GUARDS` over the frozen `origin/dev` base.
- **Audit read separately:** `W48-AUDIT` at
  `c11f1b6dfe0c34a9274bc5793b53fc9e5578c8d7`; it is evidence, not part of this subject.
- **Frozen contracts:** domain revision 8; API 17 paths / 20 operations / 61 schemas;
  22 error codes; migration head `0013_norm_embeddings`.
- **Date:** 2026-10-02.

**Verdict: REJECT Stage A.** The migration-inventory, unequal-row and invalidation repairs do
what their reports claim under fresh independent mutations. The prose and independent-pin
instruments do not yet close their stated universe: a stale surface count behind a new subject
synonym passes (`JA-01`), an exact stale claim in a tracked path outside three hand-listed
prefixes passes (`JA-02`), and an independent TypeScript contract pin outside the Python-only
inventory passes (`JA-03`). The separately read audit also omitted a transitive/dynamic import
scope from one clean conclusion; the expanded query found no defect (`JA-04`).

This task repairs nothing and authorises no tag, deployment, `origin/dev` update or
`origin/main` update. In particular, the full Stage-A gate being green does not override these
deliberately demonstrated false greens.

## 2. Environment and method

The judge ran on Linux `6.8.0-142-generic` x86-64, CPython `3.12.3`, Node `v22.23.1` and
npm `10.9.8`. The subject worktree stayed report-only. Mutations ran in two disposable clones
at the exact subject SHA; the PostgreSQL/MinIO clone was below `/root` because the installed
Docker is snap-confined and cannot mount `/tmp`. Its isolated lane used instance
`auditmanager-w48-judge-a`, PostgreSQL port `55550`, S3 API port `59500` and S3 console port
`59501`. All credentials were disposable local values and are deliberately absent from this
report.

The pre-dispatch baseline was the integrator's full `make gate` at this exact subject: exit `0`,
literal final `GATE OK`; backend `2655 passed, 5 skipped, 4 warnings, 169 subtests`; foundation
`35 passed`; frontend `1165 passed` in `82` files. The judge did not treat that baseline as
mutation evidence.

Every mutation below was restored. `git diff --check` in the final disposable clone exited `0`,
and `git diff --name-only` printed nothing. Only ignored/untracked links to the existing locked
runtime environment and frontend modules remained before the clone was removed.

## 3. Findings

### JA-01 — a stale count behind a new surface-subject synonym is green

**Class:** Stage-A false green; prose truth; subject discovery.

`tests/contract/api_v1/test_surface_counts_in_prose.py:103-110` still decides whether a prose
sentence is about the frozen contract through `_SURFACE_SUBJECT`, an explicit regular-expression
list. The noun after the number is now generic, which correctly catches a new noun such as
`facets`, but the subject before that number is not generic.

In a tracked TOML file inside the already-scanned `infra/deploy/` prefix, the stale statement:

```text
The complete HTTP interface exposes twelve endpoints.
```

left all `26` surface-prose tests green. Replacing only that sentence with the already-listed
subject `The API surface has twelve facets.` made the same suite fail exactly once and reported
`twelve facets` against `{17, 20, 22, 61}`.

**Consequence.** A deployment note can make a whole-interface size claim using ordinary wording
which the guard never classifies as a surface claim. The change from a noun allow-list to a
subject allow-list moved rather than removed the synonym false green.

**Reproduction:** add and stage `infra/deploy/judge-surface.toml` with each sentence above, then
run:

```sh
.venv/bin/python -m pytest tests/contract/api_v1/test_surface_counts_in_prose.py -q
```

Result: listed subject + new noun exit `1` (`1 failed, 25 passed`); new subject synonym exit `0`
(`26 passed`).

### JA-02 — surface prose is still discovered only in hand-listed paths

**Class:** Stage-A false green; tracked-file scope.

`tests/contract/api_v1/test_surface_counts_in_prose.py:49-50,301-307` filters the tracked text
inventory through exactly three prefixes (`src/auditmanager/api/`, `infra/deploy/`, `web/src/`)
plus one document. The inventory is extension-independent, but not path-independent.

The exact sentence already proved red inside `infra/deploy/`:

```text
The API surface has twelve facets.
```

was added and staged as `scripts/judge-surface.toml`. The complete suite exited `0` with
`26 passed`.

**Consequence.** A new tracked release/generator/operator surface outside the three enumerated
prefixes is invisible until an author remembers to extend the test's private topology. The
guard cannot prove there is no sibling stale count in a new location, although its source-file
discovery now correctly handles a newly seen `.toml` file inside an enumerated path.

**Reproduction:** stage the one-line file under `scripts/` and run the same focused pytest
command as `JA-01`; exit `0`, `26 passed`.

### JA-03 — independent TypeScript pins are outside the registry inventory

**Class:** Stage-A false green; contract-pin completeness.

`tests/contract/api_v1/test_doc_prose_facts.py:99-126` discovers symbolic and assertion pins only
in `tests/**/*.py`, then special-cases `web/FRONTEND_LOCK.json` and the Python historical-heading
shape. The completeness assertion at lines `479-508` can therefore compare only paths that this
Python-only discovery has already admitted.

A staged `web/tests/contract/judge-independent-pin.contract.test.ts` containing a standalone
`const FROZEN_OPERATION_COUNT = 12` assertion, with no `CONTRACT_PIN_REGISTRY.md` entry, left the
registry completeness test green.

**Consequence.** A frontend contract test can acquire a second independently maintained API,
catalog or migration literal without registration. A later reseal can update the canonical
contract and leave that test's value stale while the completeness control continues to claim the
pin universe is enumerated.

**Reproduction:** stage the TypeScript test and run:

```sh
.venv/bin/python -m pytest \
  tests/contract/api_v1/test_doc_prose_facts.py::test_contract_pin_registry_is_complete_and_points_to_live_needles -q
```

Result: exit `0`, `1 passed`.

### JA-04 — the audit's clean import conclusion omitted transitive and dynamic scope

**Class:** audit scope gap; no product defect reproduced.

The separate audit states at `docs/program/reviews/W48-AUDIT.md:267` that
`decisions/comparison` contain no `analysis` or `norms` import. Its recorded repository-wide AST
instrument classifies direct `Import`/`ImportFrom` edges; it does not record a transitive closure
or a search for `__import__` / `importlib.import_module` calls before making this measured-clean
statement.

The judge parsed every `src/auditmanager/**/*.py`, resolved relative imports, started from all
four `decisions`/`comparison` modules, traversed the complete local import graph, and inspected
constant and non-constant dynamic import calls across the reachable set. It reached `42` modules
in contexts `decisions, documents, findings, ingest, shared, storage`; it reached neither
`analysis` nor `norms` and found no dynamic-import call.

**Consequence.** There is no new boundary defect, but the audit's original negative evidence was
narrower than the natural reading of its conclusion. The expanded result upholds the clean claim
for this subject; future reports should state `direct` or include the closure explicitly.

**Reproduction:** the disposable AST probe exited `0` with:

```text
start_modules=4 reachable_modules=42
reachable_contexts=decisions,documents,findings,ingest,shared,storage
reachable_analysis_or_norms=NONE
dynamic_import_calls=NONE
```

## 4. Mutations that correctly went red

### Historical boundary and pin families

- Inserting an earlier, syntactically valid duplicate
  `## Previous release state — wave 47 (historical record)` before the live migration claim made
  `test_the_historical_section_is_excluded_from_the_live_scan` exit `1`. The failure reported
  `historical headings must be unique and newest-first; D-115 mutation: [47, 47, 46, 45, 44, 43]`.
- The committed parametrised mutation for `surface`, `error_catalog`, `migration_head` and
  `history_boundary` ran independently: exit `0`, `4 passed`. Each case changes one live needle
  without changing its registry and asserts a family-specific registry error.

Commands:

```sh
.venv/bin/python -m pytest \
  tests/contract/api_v1/test_doc_prose_facts.py::test_the_historical_section_is_excluded_from_the_live_scan -q
.venv/bin/python -m pytest \
  tests/contract/api_v1/test_doc_prose_facts.py::test_one_changed_pin_per_registry_family_is_red -q
```

### Fresh-migration invariant

The pristine fresh-database inventory exited `0` (`2 passed`). Replacing
`ck_norm_embedding_unit_norm` in `20261001_0013_norm_embeddings.py` with `CHECK (true)` and
rerunning against newly created databases exited `1` (`2 failed`): the constraint digest changed
and the explicit tautology query named `norm_embedding.ck_norm_embedding_unit_norm`.

Command (the disposable lane URL and credentials are omitted as required by the brief):

```sh
DATABASE_URL=<disposable-lane-url> .venv/bin/python -m pytest \
  tests/integration/db/test_schema_invariant_inventory.py -q
```

This proves the test observes current migration bytes on an empty database, not the lane's
already migrated database.

### Pairwise-distinct dashboard rows

For the backend, `_filled` was mutated three times to swap only `AR`/`KM`,
`pending`/`rejected`, and `queued`/`running`. Each complete fresh-deployment command exited `1`
with `1 failed, 3 passed`, and the failure showed respectively `AR 3 / KM 1`,
`pending 3 / rejected 1`, and `queued 3 / running 2` against the distinct expected counts.

```sh
DATABASE_URL=<disposable-lane-url> S3_ENDPOINT_URL=<disposable-lane-endpoint> \
  S3_REGION=us-east-1 S3_ACCESS_KEY_ID=<disposable> S3_SECRET_ACCESS_KEY=<disposable> \
  S3_BUCKET=auditmanager-w48-judge-a .venv/bin/python -m pytest \
  tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py -q
```

For the browser, the displayed value lookup was mutated independently in each panel for the
same three swaps. Each run exited `1`: section `2 failed, 15 passed`, verdict
`1 failed, 16 passed`, and run state `1 failed, 16 passed`. The row-keyed assertions named the
first wrong member rather than merely observing that both numbers existed somewhere on screen.

```sh
npm --prefix web test -- tests/unit/widgets/dashboard.test.ts
```

### Invalidation AST

Commenting out the real create-project invalidation made the focused guard exit `1`
(`1 failed, 8 passed`) and named the create-project hook. After restoring the call, adding the
same `queryKeys.dashboard.summary()` text only as a comment to the mapped non-invalidating
export hook left the intended result green (`9 passed`); the decoy did not turn that hook into an
invalidator.

```sh
npm --prefix web test -- tests/guards/dashboard-invalidation.guard.test.ts
```

## 5. Command/result ledger

| command / instrument | exit and result |
|---|---|
| Stage-A integration `make gate` at the exact subject | `0`; literal `GATE OK`; backend 2655 passed / 5 skipped / 4 warnings / 169 subtests; foundation 35; frontend 1165 in 82 files |
| surface known subject + new noun in tracked TOML under `infra/deploy/` | `1`; 1 failed, 25 passed |
| surface new subject synonym in the same tracked TOML | `0`; 26 passed — `JA-01` |
| exact stale surface claim in staged `scripts/*.toml` | `0`; 26 passed — `JA-02` |
| early valid duplicate historical boundary | `1`; 1 failed |
| one changed registry needle in each of four families | `0`; 4 mutation assertions passed |
| unregistered independent TypeScript operation-count pin | `0`; 1 passed — `JA-03` |
| pristine fresh migration inventory | `0`; 2 passed |
| migration `CHECK (true)` against a newly migrated database | `1`; 2 failed |
| backend section / verdict / run-state swaps | each `1`; each 1 failed, 3 passed |
| frontend section swap | `1`; 2 failed, 15 passed |
| frontend verdict swap | `1`; 1 failed, 16 passed |
| frontend run-state swap | `1`; 1 failed, 16 passed |
| real invalidation commented out | `1`; 1 failed, 8 passed |
| real invalidation restored plus decoy comment | `0`; 9 passed |
| transitive/dynamic decisions+comparison import probe | `0`; 42 reachable modules, no analysis/norms, no dynamic import calls |
| final disposable clone `git diff --check` / `git diff --name-only` | `0` / empty |

An initial dashboard mutation command omitted the S3 application settings and errored in setup
for all four cases. It is not mutation evidence; the complete reruns above supplied the isolated
lane settings and reached the intended assertions. An initial `make up` below `/tmp` also failed
because snap-confined Docker rewrote the inaccessible compose path; the `/root` disposable clone
was the complete rerun.

## 6. Untested questions

1. A structural, semantics-aware replacement for prose subject discovery was not designed or
   evaluated; this judge only proves two concrete false greens.
2. The pin mutation proves TypeScript is absent from discovery, not that every numeric frontend
   assertion is a contract pin. A repair needs a bounded semantic rule to avoid registering HTTP
   status codes, fixture sizes and local enum counts.
3. Migration families not listed in the committed inventory were not exhaustively compared to
   every PostgreSQL catalog; the required weakened constraint and all currently listed families
   were exercised.
4. No live provider, alpha credential, external host, deployment ref, customer data or alpha
   object-store volume was touched.
5. The release-blocking `W48-AUDIT` findings `A-01` and `A-02` remain uncorrected and were not
   fault-injected here; this judge is not an acceptance of them.

## 7. Integration, rollback and final diff

The integrator should reject Stage A and open a bounded repair slot for `JA-01` through `JA-03`
before any Stage-B dispatch. `JA-04` needs an audit wording/scope correction, not runtime code.
The repair must preserve the frozen contracts, migration head, dependency locks, composition root
and global styles; it also needs independent red/green mutations for the newly defined discovery
boundaries. The release cannot be promoted while `W48-AUDIT` `A-01` and `A-02` are unresolved.

Rollback is deletion/revert of this report only. The task changes no product code, test, contract,
migration, lock, composition root, global style, tag, deployment or remote ref.

At report commit time, the required command:

```sh
git diff --name-only 39e06c2cae7531481da80b0ace70668d26b1416e..HEAD
```

must print exactly:

```text
docs/program/reviews/W48-JUDGE-A.md
```
