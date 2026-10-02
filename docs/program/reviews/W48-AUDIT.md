# W48-AUDIT — independent audit of the frozen alpha tree

## 1. Subject, boundary and verdict

- **Audit subject / dispatch base:** `9b5219e69fe87fb710c55e8f0643ba9af74c2be0`
  (`origin/dev` at the start of the audit).
- **Frozen runtime code base:** `6118e66033380661bb747244e0f7a222fb9a87b4`.
- **Remote deployment ref at the start:** `origin/main =
  608632a52940cbff70a1e8361f241901f48182aa`.
- **Frozen contracts:** domain revision 8; API 17 paths / 20 operations / 61 schemas;
  22 error codes; migration head `0013_norm_embeddings`.
- **Date:** 2026-10-02.

**Verdict: audit complete; the frozen tree is not acceptable as an alpha-promotion subject.**
Stage-A repairs may continue, but promotion needs explicit disposition of two release-blocking
data-integrity findings (`A-01`, `A-02`). The report also records a systematic backend boundary
violation (`A-03`), four fail-open frontend vocabulary paths (`A-04`) and stale governance state
(`A-05`). This task repairs none of them and authorises neither a tag nor a ref update.

The verdict is deliberately narrower than “the application cannot be exercised”. The frozen
runtime gate is green and the deployment workflow is pinned. The failure is that a process loss
at two observable side-effect boundaries can leave canonical evidence or cost provenance
irreconcilable, contrary to the programme's accepted architecture.

## 2. Environment and scope inventory

The audit ran on Linux `6.8.0-142-generic` x86-64, Python `3.12.3`, Node `v22.23.1` and npm
`10.9.8`. No customer data, live provider, alpha credential or mutable deployment endpoint was
used. Runtime probes used only a disposable detached worktree and were removed after capture.

Tracked family inventory was taken before selecting findings:

| family | measured scope |
|---|---|
| backend contexts | access 10, analysis 32, api 32, bootstrap 3, dashboard 3, decisions 4, documents 4, exports 5, findings 6, ingest 6, norms 14, runs 8, shared 21, storage 9 Python files; comparison/export/jobs/operations/workers contain package or non-Python surfaces only |
| frontend layers | `_app` 6, `_pages` 33, app 21, entities 39, features 27, shared 35, widgets 39 TypeScript/TSX files |
| backend tests | characterization 3, checkpoint 2, contract 27, e2e 12, integration 181, replay 3, support 1 Python files |
| frontend tests | contract 7, guards 29, unit 63 TypeScript/TSX files |
| operational/governance | `.github` 1, db 17, infra 27, contracts 34, scripts 3, tools 16, docs 392 tracked files |

Reproduction:

```sh
for d in src/auditmanager/*; do
  test -d "$d" && printf '%s %s\n' "${d##*/}" "$(find "$d" -type f -name '*.py' | wc -l)"
done
for d in web/src/*; do
  test -d "$d" && printf '%s %s\n' "${d##*/}" \
    "$(find "$d" -type f \( -name '*.ts' -o -name '*.tsx' \) | wc -l)"
done
for d in .github db infra contracts scripts tools docs; do
  printf '%s %s\n' "$d" "$(git ls-files "$d" | wc -l)"
done
```

The counts are an inventory, not a clean claim: generated caches were excluded and every lens
below records its own query and limits.

## 3. Findings

### A-01 — a completed provider attempt can be lost with all cost provenance

**Class:** release-blocking data integrity; identity/idempotency; side-effect ordering.

`src/auditmanager/analysis/text/stage.py:225-240` performs the potentially paid external call at
line 226, then allocates `ModelCallId` only after the response returns. The caller records the
returned calls later at `src/auditmanager/runs/executor.py:423-443`. The carrier commits `running`
before execution, but commits all stage/model/terminal rows only after the whole run at
`src/auditmanager/runs/carrier.py:253-270`.

The gap is not protected by another durable authority. `src/auditmanager/runs/retry.py:13-19`
states that attempts are process-local and that PC-01 has no Job, Attempt, lease, execution token
or outbox. `src/auditmanager/runs/scope.py:88-96` pins those aggregates as not instantiated.

**Observable consequence.** If the provider accepts or answers a request and the process dies
before `_record_model_calls` and the final commit, restart reconciliation can terminate the
already-`running` run, but it cannot recover the missing attempt, tokens, charge, request checksum
or response provenance. A retry also has no durable provider-attempt identity with which to prove
that it is not buying the same answer twice.

**Reproduction / scope query:**

```sh
nl -ba src/auditmanager/analysis/text/stage.py | sed -n '205,255p'
nl -ba src/auditmanager/runs/executor.py | sed -n '410,475p'
nl -ba src/auditmanager/runs/carrier.py | sed -n '235,275p'
rg -n 'adapter\.complete|_record_model_calls|Job|Attempt|execution token|outbox' \
  src/auditmanager/analysis src/auditmanager/runs tests/integration/runs
```

The query covers every provider invocation and the declared durable-execution scope. No real
provider kill was executed: doing so would spend money and use forbidden credentials. The static
order is sufficient to prove the unrecorded interval; a repair still needs a kill-after-acceptance
test against owned disposable infrastructure.

### A-02 — canonical analysis artifacts can become unreachable S3 objects

**Class:** release-blocking data integrity; storage/migration; side-effect ordering.

`src/auditmanager/analysis/ports/artifacts.py:60-86` writes canonical bytes with
`blob_store.put_blob`. The deterministic stages publish before returning their `StageProduction`
at:

- `src/auditmanager/analysis/stages/source_preparation.py:74-77`;
- `src/auditmanager/analysis/stages/page_geometry_extraction.py:110-111`;
- `src/auditmanager/analysis/stages/document_context_build.py:110`.

Only after `run_stage` returns does `src/auditmanager/runs/executor.py:657-665` persist the stage
result, and the carrier does not commit it until `carrier.py:270`. Text observations have the same
ordering at `executor.py:462-475`. The only `BlobMetadataRepository` consumers are ingest service
and ingest reconciliation; analysis publication creates no metadata breadcrumb, outbox row or
named orphan reconciler.

**Observable consequence.** A crash or DB rollback after `put_blob` but before the stage-result
commit leaves a real object consuming storage with no canonical database reference and no
enumeration/reconciliation path that can classify or delete it. Content addressing prevents a
wrong-byte overwrite, but it does not make the orphan discoverable.

**Reproduction / scope query:**

```sh
rg -n 'put_blob\(|publish_artifact\(' src/auditmanager/analysis src/auditmanager/runs
rg -n 'BlobMetadataRepository' src/auditmanager
nl -ba src/auditmanager/runs/executor.py | sed -n '640,675p'
nl -ba src/auditmanager/runs/carrier.py | sed -n '253,273p'
```

This is the review-only failure described by ALR-17: there is an external effect paired with a
DB mutation, but no named outbox/recovery procedure. No destructive MinIO crash probe was run.
A repair needs a disposable-bucket fault test at every publication boundary, not a test against
the alpha bucket.

### A-03 — at least sixteen backend imports bypass another context's public module

**Class:** architecture boundary; systematic, not a single import typo.

ALR-05 in `docs/architecture/ARCHITECTURE_LINT_RULES.md:155-165` permits a cross-context backend
import only through `auditmanager.<context>.public`; `shared` and an importing module under
`bootstrap` are the stated exceptions. An AST walk over `src/auditmanager/**/*.py`, excluding
same-context, `shared` and bootstrap importers, found this minimum set:

```text
analysis/engine/runner.py:55                 -> storage.models
analysis/ports/artifacts.py:29               -> storage.models
analysis/ports/stage.py:26                   -> storage.models
analysis/stages/page_geometry_extraction.py:125 -> storage.models
api/composition.py:11                        -> bootstrap.composition
api/composition.py:12                        -> bootstrap.settings
dashboard/repository.py:23                   -> documents.repository
decisions/ledger.py:61                       -> findings.queries
ingest/reconciliation.py:83                  -> storage.blob_repository
ingest/service.py:75                         -> storage.blob_repository
norms/__main__.py:122                        -> analysis.text
norms/__main__.py:130                        -> analysis.text
runs/executor.py:84                          -> analysis.ports.artifacts
runs/executor.py:85                          -> analysis.text
runs/executor.py:96                          -> analysis.text.stage
runs/executor.py:123                         -> storage.models
```

**Observable consequence.** Internal module moves or invariants can break consumers outside the
owner context without a public-surface change. The current architecture specification labels
this an `error`, but no enforced repository check catches the existing set, so future enforcement
would immediately fail the frozen tree.

**Reproduction / scope query:** parse every `Import`/`ImportFrom` below `src/auditmanager`, derive
the importer context from the first path segment and target context from the second dotted-name
segment, then report different-context targets except `shared`, bootstrap importers and the exact
module `auditmanager.<target>.public`. Confirm individual sites with:

```sh
rg -n '^from auditmanager\.' src/auditmanager --glob '*.py'
sed -n '155,165p' docs/architecture/ARCHITECTURE_LINT_RULES.md
```

This count deliberately does not classify imports through a package `__init__` as violations;
it is therefore a lower bound. `api/composition.py` describes itself as a composition-root seam,
but the frozen ALR grants no exception to an API importer and no waiver was found. Whether to
amend that rule or move the seam is an owner/integration decision, not an audit repair.

### A-04 — four closed-vocabulary values render fail-open in two screens

**Class:** frontend truth; silent fallback.

The already-open D-113 is reproducible at
`web/src/widgets/dashboard/ui/run-activity-panel.tsx:101-113`: `cost_basis='guessed'` renders a
blank basis and caption instead of a boundary fault. The same defect class is wider in
`web/src/widgets/knowledge-base/ui/knowledge-base.tsx`:

- `current_verdict='guessed'` is echoed raw by the fallback at lines 57-59 and 95-96;
- `category='guessed'` becomes an empty label at line 94;
- `event_type='guessed'` becomes an empty label at line 98.

**Observable consequence.** A broken server vocabulary can produce plausible but false or blank
review history instead of the explicit failure state used by the repaired screens. The raw
machine values remain in data attributes, which makes the omission inspectable but does not make
it visible to the reviewer.

**Reproduction.** In a disposable copy, an SSR probe called `renderToStaticMarkup` with each
value cast through `unknown` to the transport type. Results were respectively raw `guessed`, an
empty category span, an empty event span and an empty cost-basis/caption. The probe was removed.
The focused suite below remained green (`6` files, `73` tests), proving it does not exercise those
invalid wire values:

```sh
npm --prefix web test -- \
  tests/guards/transport-boundary.guard.test.ts \
  tests/guards/server-credential.guard.test.ts \
  tests/guards/session-durability.guard.test.ts \
  tests/guards/dashboard-invalidation.guard.test.ts \
  tests/unit/widgets/dashboard.test.ts \
  tests/unit/screens/knowledge-base.test.ts
```

Scope query: inspect every `Record<closed transport union, string>` lookup and every `?? rawValue`
fallback in screen-wide consumers. This probe covered the dashboard and knowledge-base consumers;
it does not claim every focused widget has been mutation-tested.

### A-05 — D-52 is operationally repaired but still registered as open

**Class:** governance/dependency licence truth.

`docs/program/DEBT_REGISTER.md:3683-3715` still says the Feather MIT notice is absent and the open
table still lists D-52. In the frozen tree, `web/NOTICE` carries the notice and provenance map,
`web/src/shared/ui/icon.tsx:1-18` binds copied geometry to that notice, and commit
`4a602baffee21567f7623de4dd0bcc672c788351` introduced both. The two icon tests pass (`43/43`).

**Observable consequence.** A release reviewer following the canonical register is told a legal
obligation is unmet even though the distributable contains it. Conversely, future regressions
cannot be distinguished from an intentionally open row. The register's append-only correction
policy requires a close addendum rather than rewriting the historical evidence.

**Reproduction / scope query:**

```sh
rg -n 'D-52' docs/program/DEBT_REGISTER.md docs/program
find web -maxdepth 2 -type f \( -name 'NOTICE' -o -name 'LICENSE*' \) -print
git show --stat 4a602baffee21567f7623de4dd0bcc672c788351
npm --prefix web test -- tests/unit/icon-convention.test.ts tests/unit/icon-provenance.test.ts
```

The search found no later D-52 close/addendum. This audit task cannot edit the register; GOV or
the integrator must reconcile it.

## 4. Lens disposition and measured-clean conclusions

| required lens | disposition |
|---|---|
| architecture boundary | `A-03`; a repository-wide cross-context import query found a minimum 16 violations |
| identity / idempotency | API/domain identity tests are green; `A-01` finds no durable identity for provider attempts |
| side-effect ordering | `A-01` and `A-02` are release blockers under AGENTS §4 and ALR-17 |
| auth / session / secrets | focused server-credential and session-durability guards pass; `rg` found no browser credential storage outside the server-side BFF boundary; live revocation was not exercised |
| closed vocabulary / fallback | `A-04`; existing transport guard is green but misses four invalid values |
| migration / storage | migration head remains `0013_norm_embeddings`; full gate is green; no migration mutation was performed because W48-GUARDS owns it; `A-02` is the storage gap |
| frontend truth | `A-04`; D-113 reproduced and the same mechanism found in knowledge base |
| false-green | D-87, D-114 and D-116 remain scheduled Stage-A inputs; the focused invalidation guard is green, not evidence that its comments-as-code weakness is fixed |
| dependency / licence | `npm ls --all` exits 0; icon provenance tests pass; `A-05` is stale governance; no online CVE/licence-database audit was performed |
| deployment ref | workflow contract test passes; workflow triggers on `main`, serialises deployment and carries exact SHA; `origin/main` was not changed and `dev` does not deploy |

Additional negative queries produced no finding within their instrument:

- no direct SQL execution, S3 SDK call or filesystem operation was found in API routers; the
  `DBAPIError` import in `api/routers/errors.py` only maps SQLSTATE;
- raw frontend `fetch` is confined to the shared transport; Node filesystem use is in the
  server-side BFF session store, not a React component;
- S3 SDK imports are confined to the storage context;
- decisions/comparison contain no analysis or norms import;
- searches for path, filename or display-number identity construction found only comments and
  presentation, not canonical identifiers.

These are measured-clean conclusions only for the named static queries. Dynamic monkey-patching,
third-party runtime behaviour and untracked deployment configuration remain outside them.

## 5. Commands and results

| command / instrument | exit and result |
|---|---|
| `make gate` in an isolated worktree at runtime base `6118e66` with the ignored real corpus mounted read-only | exit 0, literal `GATE OK`; backend 2641 passed / 5 skipped, foundation 35 passed, frontend 1162 passed in 82 files; API 17/20/61, 22 errors, domain rev 8, migration `0013_norm_embeddings` |
| same gate before the ignored corpus was made visible to the worktree | non-zero only at the corpus precondition; no product test failure; rerun above is the recorded gate |
| contract/settings/provider identity focused pytest group without lane environment | exit 1: 160 passed, 8 settings-default failures, 27 subtests; all failures required the task's explicit environment |
| same group with disposable non-secret `DATABASE_URL`, S3 fields and API token | exit 0: 168 passed, 27 subtests |
| focused frontend transport/session/dashboard/knowledge-base command in `A-04` | exit 0: 6 files, 73 tests |
| icon convention/provenance command in `A-05` | exit 0: 2 files, 43 tests |
| `npm --prefix web ls --all` | exit 0; optional unmet and platform-specific extraneous packages only; this is not a vulnerability audit |
| SSR invalid-vocabulary probe in disposable worktree | exit 0; four fail-open renderings reproduced; probe and temporary module link removed |
| AST cross-context import walk | exit 0; minimum 16 ALR-05 sites |

The environment-less pytest failure is retained because omitting it would make the rerun look
stronger than it was. It is not classified as a product defect: `test_settings_defaults.py`
deliberately verifies supplied settings and the complete rerun used explicit disposable values.

## 6. Known scheduled exposures, not rediscovered findings

- **D-70:** repository state cannot establish what the ignored deployment `provider.env` contains.
  The user reports that deployment is active, but W48 release/tag work still needs live evidence
  from the named host and provider mode. No inference from the old recorded stub was made.
- **D-87 / D-114 / D-116:** migration mutation, unequal swapped counts and comments-as-code are
  already Stage-A guard inputs. A green current suite does not close them.
- **D-113:** the dashboard instance is part of `A-04`, but its existence is already registered.
- **D-119:** the exact source-pinned MinIO build is reproducible, not a resolution of the archived
  upstream/security-lifecycle decision.
- responsive overflow and screen-polish rows assigned to Stage B were not promoted into new audit
  findings merely because the audit could find their known source lines.

## 7. Untested questions

1. Real login, session revocation, direct-API denial and the complete manual alpha journey on the
   externally reachable deployment; this task owns no credentials or mutable host action.
2. Kill-after-provider-acceptance and kill-after-object-publication behaviour against owned
   disposable provider/S3/DB services.
3. Browser layout at 780 × 900 with 200-character names and unbroken 400-character comments.
4. Fresh-database migration mutations and independent false-green mutations owned by W48-GUARDS
   and W48-JUDGE-A.
5. Online dependency vulnerability, transitive-licence and container image scan. `npm ls` proves
   installation shape only.
6. Current external MinIO volume inventory, backup/restore rehearsal and the D-119 owner choice.

## 8. Integration and rollback

This report is evidence, not a repair. The integrator should:

1. read `A-01` and `A-02` before accepting Stage A and open at most one explicit `W48-FIX` grant
   with a named Job/Attempt/outbox/reconciliation owner;
2. decide whether `api/composition.py` is granted a documented ALR-05 waiver or moved behind the
   declared composition root before mechanically repairing `A-03`;
3. route `A-04` through the Stage-B/client boundary owner and D-52 through GOV/addendum ownership;
4. preserve the frozen contract/migration/dependency set unless a separately owned slot says
   otherwise.

Rollback is deletion/revert of this report only. It changes no runtime behaviour, contract,
migration, lock, composition root, global style, deployment state, tag or remote ref.
