# Wave 48 — alpha hardening, debt closure and whole-tree audit

**Status:** planned, not dispatchable until `W48-FREEZE-01` records an exact clean base.
**Controlling ruling:** `R-49`.
**Release target:** `alpha-w48`, only after local, deployed and manual evidence all pass.

## 1. Objective

W48 makes the externally reachable alpha harder to lie about. It closes the implementable
false-green and maintenance debts named by `R-49`, removes three small runtime/UI defects already
measured by earlier judges, audits the whole tree from independent starting points, and turns the
live browser path into mandatory release evidence without making the deterministic `make gate`
depend on a public host or secret.

This is deliberately not a feature wave. Its user-visible result is narrower and valuable:

- long reviewer-entered text no longer breaks screens at 780 px;
- an unknown spend basis becomes an explicit fault instead of disappearing;
- the alpha candidate is not tagged until the real browser journey, rejection cases and manual
  acceptance have been executed against the deployed exact SHA.

## 2. Entry dependencies and current blockers

The following are entry conditions, not claims that they already hold:

| Condition | Why it blocks dispatch | Required evidence |
| --- | --- | --- |
| `MAIN-AUTODEPLOY-02` completed | a push to `main` is now a deployment action | workflow run, exact SHA and `verify-deployed.sh` result |
| `ALPHA-MANUAL-01` reviewed and integrated | W48-LIVE consumes its script/PDF pack | committed task report and fixture checksums |
| pending planning checkout reconciled with `origin/main` | planning began at local `deda533`; `origin/main` advanced through the reviewed workflow repair to `608632a` | clean linear history and fetched refs |
| `origin/dev` brought to the accepted dispatch tip | D-77 must not let a reviewer measure an obsolete branch again | exact equality with the docs-only dispatch tip containing the frozen base record |
| complete `make gate` on the freeze candidate | no lane starts from an inherited green | literal `GATE OK` tied to SHA |
| no unowned working-tree changes | the requested manual-alpha package must be independently reviewed and committed as its own task | empty `git status --porcelain` |

D-70 does not block code work, but it **does block release closure**. Before `alpha-w48` can be
tagged, A04 of the alpha runbook must show a terminal `published`/`partial` run with
`provider_mode=live`. `recorded`, `dependency_unavailable` or an unreachable provider keeps the
wave untagged.

## 3. Contract freeze

W48 has no contract task. `W48-FREEZE-01` freezes the already accepted set unchanged:

```yaml
wave_id: W48
contract_set:
  domain: 1.0.0-draft.1 revision 8, 27 opaque identities
  api: 17 paths / 20 operations / 61 schemas
  api_sha256: f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585
  error_catalog: 22
  analysis: PC-01 synthetic AR oracle, unchanged
  comparison: four-way same/changed/only_left/only_right, unchanged
migration_head: 0013_norm_embeddings
frozen_code_base: <filled by W48-FREEZE-01>
dispatch_tip: <resolved by origin/dev after the docs-only freeze commit>
frozen_by: W48-FREEZE-01
```

Any finding that requires an API/schema/error-catalog/migration change stops the affected lane.
It becomes an owner ruling and a later contract wave; it is not repaired under a convenient
W48 test path.

## 4. Gate topology decided for this wave

W48 uses two different gates because they prove different things:

1. **`make gate` remains hermetic.** It uses no public hostname, reviewer password, provider key
   or mutable deployment. It must keep the literal `GATE OK` sentinel.
2. **The alpha acceptance gate is mandatory for release but external.** It runs preflight, the
   PC-01 browser journey/refusals and the A01–A12 manual checklist against the deployed exact SHA.
   Missing credentials or provider connectivity is `BLOCKED`, never a skip or a pass.

This is the resolution W48 must encode for D-108. Putting a flaky, credentialed external system
inside `make gate` would make ordinary development nondeterministic; leaving the journey as an
unowned ad-hoc command allowed a red route to ship. The two-level release gate preserves both
properties.

## 5. Debt-to-task map

| Debt/ruling | Owner in W48 | Required closure |
| --- | --- | --- |
| D-76 third instance | `W48-PROSE` regression | keep the W47 closure load-bearing; no stale-head exception returns |
| D-98, D-99, D-100 | `W48-PROSE` | scanner derives file scope and surface claims instead of trusting noun/extension lists |
| D-104, D-105, D-115 | `W48-PROSE` | external-state prose removed/typed; every independent pin enumerated; historical boundary cannot hide live claims |
| D-87 | `W48-GUARDS` | schema invariants classified and checked against a freshly migrated database |
| D-114 | `W48-GUARDS` | pairwise-distinct seeded counts make row swaps red in backend and browser tests |
| D-116 | `W48-GUARDS` | invalidation proof reads behaviour or comment-stripped syntax, never comments as code |
| D-97 | `W48-WEB` | one shared screen-wide render contract, while focused router mounts stay focused |
| D-112 | `W48-WEB` | unbroken user strings do not overflow at 780 px on measured screens |
| D-113 | `W48-WEB` | unknown `cost_basis` renders a typed fault |
| D-74 | `W48-PORTS` | narrow semantic existence ports avoid full parent reads in both adapters and test implementations |
| D-108, D-68, D-83 boundary | `W48-LIVE` | repository-owned alpha acceptance command plus exact deployed evidence; selectors/refusals measure the intended state |
| D-89, D-96, D-117, D-77 rule | `W48-GOV` | ownership/evidence rules become templates; historical reports get an addendum, not a rewrite; branch role is explicit |
| R-49 whole-tree audit | `W48-AUDIT` | independent report with reproducible findings across the whole repository |

Owner-held D-59, D-70, D-71, D-75, D-91, D-106, D-107, D-109, D-110, D-111 and D-119 are
not silently decided here. D-70 is a release prerequisite as stated above. The others remain
registered unless the owner gives a separate ruling before freeze.

## 6. Stage 0 — freeze and dispatch

### `W48-FREEZE-01` — exact base and executable task files

**Outcome:** all entry conditions in §2 are measured; `origin/dev` and the accepted base are
reconciled; the YAML in §3 contains a real SHA; individual task files are generated from
`TASK_TEMPLATE.md` with exact `allowed_paths`, commands and lane ports.

**Allowed paths:** W48 plan/dispatch/task documents and the integration branch/ref bookkeeping
needed to fast-forward `origin/dev`. This freeze slot is the initial W48 owner of `origin/dev`;
the closeout slot owns its later final-candidate update. Neither owns `origin/main` authority.

**Required checks:** clean tree; fetched refs; `origin/dev` contains the recorded frozen code
base and equals the docs-only dispatch tip; full gate from the exact code-base SHA; focused
documentary checks after the freeze record; contract SHA/counts/catalog/migration measurements;
`git diff --check`.

The freeze uses two explicit identities because a commit cannot contain its own SHA:

- `frozen_code_base` — the exact clean commit that passed the full gate;
- `dispatch_tip` — its docs-only descendant containing the freeze report and executable Stage-A
  task files, published to `origin/dev` after focused guards pass.

Stage-A lanes branch from `dispatch_tip`; every runtime/contract byte is inherited unchanged from
`frozen_code_base`.

**Stop:** any pending task is only locally committed, any ref moved during freeze, or any
contract count differs from §3.

## 7. Stage A — instruments and independent audit

These three lanes may run in parallel from the frozen commit. Their writable paths do not
overlap.

### `W48-AUDIT` — whole-tree code audit, report only

**Outcome:** a review not led by the wave diff covers every bounded context and records
reproducible findings before repair work biases the search.

**Allowed path:** `docs/program/reviews/W48-AUDIT.md` only.

**Audit lenses:** architecture bans from `AGENTS.md`; identity and idempotency; DB/external
side-effect ordering; authentication/session exposure; secret and deploy boundaries; silent
fallbacks and closed vocabularies; migration reversibility; storage integrity; frontend state
truthfulness; tests that can pass for the wrong reason; comments/prose treated as executable
evidence; dependency and licence residue.

**Required evidence:** each finding names path/line, observable consequence, reproduction and
scope query. A count/path claim includes captured query output under D-96. No repair, no debt
register edit and no severity inflation without consequence.

### `W48-PROSE` — surface/prose truth and pin registry

**Outcome:** D-98/99/100/104/105/115 can each be re-mutated and made red by one coherent guard
family.

**Candidate writable areas:**

- `tests/contract/api_v1/test_surface_counts_in_prose.py`;
- `tests/contract/api_v1/test_doc_prose_facts.py`;
- a new `docs/program/CONTRACT_PIN_REGISTRY.md`;
- stale prose/comments discovered by the derived scanner, including `P02_SEAMS.md` and relevant
  `infra/deploy` text formats.

**Forbidden:** contracts, migrations, runtime behaviour, workflow semantics and generated
clients. Comment corrections may not change executable lines in the same patch.

**Required checks:** focused prose suites; one mutation per debt family; a full-tree inventory
showing no unregistered independent pin; `git diff --check`.

### `W48-GUARDS` — migration, dashboard-count and invalidation proofs

**Outcome:** D-87, D-114 and D-116 stop being false greens.

**Candidate writable areas:** `tests/integration/db/**`, backend dashboard tests,
`web/tests/guards/dashboard-invalidation.guard.test.ts` and focused dashboard fixtures/tests.

**Required checks:**

- every schema invariant is either exercised after a fresh migration or listed with a justified
  non-schema classification;
- swapping any pair of distinct section/verdict/run-state rows makes an exact-count test fail;
- commenting out a real invalidation call fails while adding the same text to a comment does not
  pass;
- mutations run against scratch copies/fixtures and leave the tree unchanged.

`W48-JUDGE-A` closes Stage A before any Stage B merge.

## 8. Stage B — bounded repairs

Stage B starts only after Stage A findings are triaged. These four implementation lanes are
parallel and have exclusive path families.

### `W48-PORTS` — narrow existence semantics

**Outcome:** list-decision and list-finding parent checks no longer build full run/finding
projections merely to answer existence.

**Candidate writable areas:** the two semantic ports, the two production implementations, the
two integration-test implementations, the calling routers and focused backend tests.

**Constraints:** no generic repository/base service; no direct SQL from routers; no API response
or error change; all implementations change atomically. Tests must prove the expensive full-read
methods are not called on the existence path and unknown parents retain the same typed refusal.

### `W48-WEB` — honest rendering under unknown data and hostile-width strings

**Outcome:** D-97, D-112 and D-113 close together under one frontend owner.

**Candidate writable areas:** `web/src/**`, `web/tests/**`, including the one W48 global-style
slot. No backend/API/generated-contract edit.

**Required checks:** one shared screen harness carries router/query/session states used by all
screen-wide guards; focused router tests are not forced into it; an unknown spend basis produces
`ErrorState`; 200-character project names and 400-character unbroken comments fit a 780 px
viewport; reintroducing each defect makes its own test red. Because screens change, the merged
tree must later run the live journey.

### `W48-LIVE` — release-owned alpha acceptance command

**Outcome:** D-108 is resolved by a named non-hermetic release command and an evidence schema,
not by a hidden external step inside `make gate`.

**Candidate writable areas:** `Makefile` (sole W48 owner), `scripts/manual-alpha-check.sh`,
`tests/e2e/pc01/**`, `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` and focused command-surface
tests. Workflow changes are forbidden unless `MAIN-AUTODEPLOY-02` explicitly hands ownership
over at freeze.

**Required behaviour:** the command has no default origin or credential; validates preflight;
runs sign-in, 3/3 writes, 16/16 cold routes, six refusal cases and the width assertion; stores no
secret; distinguishes `FAIL` from `BLOCKED`; records candidate/deployed SHA separately; and never
prints `PASS` when any requested phase did not execute. Manual A01–A12 remains a human signature,
not an automated fiction.

### `W48-GOV` — ownership and evidence rules made executable

**Outcome:** D-89/D-96/D-117 and the D-77 branch lesson become maintained process rather than
historical prose.

**Candidate writable areas:** `docs/templates/TASK_TEMPLATE.md`,
`docs/program/WAVE_EXECUTION_GUIDE.md`, `docs/program/dispatch/OPERATING_CONSTRAINTS.md`, a new
W46 historical addendum and focused documentary guards.

**Required behaviour:** every task adding a route/screen/error/migration names the enumerating
file and its sole owner; every exact path/count premise includes captured query output and date;
historical reports are never rewritten; `origin/dev` is the integration candidate and
`origin/main` the separately authorised auto-deploy ref. Development publication stops at
`origin/dev`; only a direct owner instruction for the exact candidate permits `main` publication.
Incorrect examples must make a guard fail.

## 9. Ownership matrix

| Hotspot/path family | Stage owner | Parallel writer |
| --- | --- | --- |
| `contracts/**`, generated clients, error catalog | frozen/no owner | none |
| `db/migrations/**`, migration head | frozen/no owner | none |
| prose/surface guards and scanned stale comments | `W48-PROSE` in Stage A | none |
| DB/dashboard/invalidation guard tests | `W48-GUARDS` in Stage A | none |
| `web/src/**`, `web/tests/**`, global styles | `W48-WEB` in Stage B | none |
| backend ports/adapters/routers for D-74 | `W48-PORTS` in Stage B | none |
| `Makefile`, PC-01 E2E and alpha runbook/script | `W48-LIVE` in Stage B | none |
| templates/execution rules/history addendum | `W48-GOV` in Stage B | none |
| `CURRENT_STATE.md`, `DEBT_REGISTER.md`, integration fixes | `W48-INT-CLOSE` | none |
| root locks/composition/deploy scripts/workflow | frozen unless a new integration grant names one | none |
| initial `origin/dev` freeze/dispatch tip | `W48-FREEZE-01` only | none |
| final `origin/dev` candidate, `alpha-w48` | `W48-INT-CLOSE` only | none |
| `origin/main` auto-deploy publication | separately assigned integration task after direct owner instruction | none |

If Stage A needs to correct a comment in a Stage B-owned source family, Stage A closes before
Stage B branches are cut. No two live lanes edit the same file.

## 10. Integration order

1. `W48-FREEZE-01` records the exact base and dispatches Stage A.
2. Integrate `W48-PROSE` and `W48-GUARDS`; keep `W48-AUDIT` report-only.
3. `W48-JUDGE-A` attacks Stage A mutations and the audit's scope.
4. Integrator triages audit findings: critical security/data-integrity/false-green findings enter
   a single `W48-FIX` slot; product/contract/owner decisions remain registered for later.
5. Cut Stage B lanes from the accepted Stage A integration SHA.
6. Integrate `W48-PORTS`, `W48-WEB`, `W48-LIVE`, `W48-GOV` in that order, resolving no semantic
   mismatch inside merge commits.
7. Run `W48-JUDGE-X` and `W48-JUDGE-Y` in parallel on the same merged SHA; exchange reports and
   cross-examine before repair.
8. One `W48-FIX` slot repairs upheld findings with explicit path grants. Re-run the affected
   mutation plus regression scope.
9. `W48-INT-CLOSE` runs the final local gates and publishes the exact candidate to `origin/dev`.
   It stops there unless the owner separately gives direct `origin/main` publication authority.

## 11. Automated gates

At minimum on the final candidate:

```text
make gate                         -> literal GATE OK
fresh database migrate/upgrade   -> head 0013_norm_embeddings
fresh/real PostgreSQL and S3 integration scopes
frontend lint + typecheck + complete tests
PC-01 conformance and all new mutation proofs
git diff --check
clean git status
```

The full gate log is tied to the exact candidate SHA. Piping through `tail`, excluding E2E from
the canonical battery or quoting a previous lane's gate is not evidence.

## 12. Manual, deployment and checkpoint sequence

`W48-INT-CLOSE` owns the final W48 `origin/dev` update and local acceptance. `origin/main`
publication remains a separate owner-authorised action:

1. Fast-forward `origin/dev` to the clean candidate and prove it names the gated SHA.
2. Re-read `origin/main`; stop if it moved. Prove candidate is its fast-forward descendant.
3. Run a disposable local/built-stack alpha acceptance before publication.
4. Report the exact candidate as development-published and stop. Do not update `origin/main`
   without a separate direct owner instruction naming publication of this exact candidate.
5. If and only if that instruction is given, the separately authorised integration action
   re-fetches refs, revalidates the gate evidence and fast-forwards the exact candidate to
   `origin/main`. This intentionally triggers auto-deploy.
6. Wait for the serialized workflow; require success and host-side `verify-deployed.sh` for the
   triggering SHA.
7. Run public preflight, PC-01 browser journey/refusals and A01–A12. Require
   `provider_mode=live`, 3/3 writes, 16/16 routes, no auth/console failures, rule-specific PDF
   refusals and no unexplained `BLOCKED`.
8. Only then create/push annotated `alpha-w48` at that exact commit. The tag itself must not move
   a branch or trigger a second deployment.

The candidate's `CURRENT_STATE.md` describes commands and the candidate boundary, not a
present-tense deployed SHA. If the separately authorised deployment or public acceptance fails,
no tag is created. Recovery is a separately gated forward repair or explicit revert commit
through `main`; never force-push, reset the host or hide the failed workflow.

## 13. Judging

Detailed briefs are in `docs/program/dispatch/W48-JUDGES.md`.

- `W48-JUDGE-A`: instrument attack after Stage A.
- `W48-JUDGE-X`: black-box/security and deployed-boundary entry point.
- `W48-JUDGE-Y`: architecture/data-integrity and maintainability entry point.
- cross-examination: every finding upheld, narrowed or falsified with a new measurement.

Judges own report files only and repair nothing.

## 14. Stop conditions

Stop integration when any of the following occurs:

- a repair requires contract/error/migration semantics;
- two tasks need the same hotspot concurrently;
- `make gate` needs a secret, public network or mutable deployment;
- an existence optimization changes the visible 404/authorization/error envelope;
- an audit finding can corrupt evidence, bypass authentication, dual-write without recovery or
  silently publish ungrounded output;
- a mutation passes for a different reason than the claim under test;
- local candidate, `origin/dev`, `origin/main`, workflow SHA and deployed SHA cannot be named
  separately;
- any final manual step is `FAIL` or unexplained `BLOCKED`.

## 15. Non-goals and following wave

W48 does not build normative search/citation APIs, upload the normative corpus, repair the 121
source pages, introduce another section profile, choose a MinIO successor, add roles/tenancy or
change dashboard pagination. Those need owner/contract decisions and belong to W49 or later.

W49 is now queued as the prerequisite data-plane vertical: maintained storage, verified
source/crop custody, the ruled 121-page repair, repaired snapshot promotion and its complete
embedding build. Retrieval with exact citations and audit-run snapshot consumption moves to W50
or later, after W49 evidence and an external-use licensing ruling exist.
