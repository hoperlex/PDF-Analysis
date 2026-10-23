# AR v3 beta six-Run group — development integration

**Task:** [AR-V3-BETA-SIX-RUN-02](tasks/AR-V3-BETA-SIX-RUN-02.md), replacing the frozen `-01` task under its [addendum](AR-V3-BETA-SIX-RUN-01-ADDENDUM.md). **Frozen base:** `6e9f887e8d7de268ab327390e73a658c1123f9aa`. **Publication target:** `origin/dev` only; no tag, `origin/main` update or deployment claim.

## Result

`POST /ar-v3-beta/groups` and `GET /ar-v3-beta/groups/{group_id}` expose one group with a distinct `arg_` identity and six child `run_` identities in the fixed F1/F2/A1/A2/S1/S2 order. Start requires an authenticated expert, a confirmed AR version, the current qualified and sealed beta snapshot, a versioned server-side reviewed pack, and six distinct custody-verified retrieval sets. Each Run freezes its scope, map, set, project, version, snapshot, profile/bundle and input digest. One database transaction claims the idempotency key and writes the group, six Runs and memberships; an identical replay returns the same IDs. Different payloads or a failed preflight refuse without partial group or provider effect. Readback reports each child Run's current status, including a partially failed group.

Production composition installs an empty trusted-pack registry. There is no approved six-map/six-set pack, so start currently refuses before writing; the new routes do not dispatch jobs, call a provider, certify a quotation, publish a finding or issue a numerical conclusion. Existing v1 Run profile resolution and normal Run IDs remain intact.

## Changed files

- `contracts/{api,analysis,domain,events}/v1/**`, `db/migrations/versions/20261023_0032_ar_v3_run_group.py`, `src/auditmanager/shared/identity/ids.py` — family/API `1.2.0` seal, group ID, migration with immutable membership and complete six-child constraint.
- `src/auditmanager/runs/**`, `src/auditmanager/analysis/{engine/result.py,public.py,text/stage.py}`, `src/auditmanager/norms/public.py`, `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**` — trusted-pack gate, atomic command/read projection, typed public seams and wiring.
- `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, selected BFF/proxy version claims and `web/tests/**` — exact generated-client and error-envelope reseal; rendered-language guard reads the frozen beta policy's visible machine IDs.
- `tests/{contract,integration}/**`, `tests/support/expected_facts.json`, `docs/program/{CURRENT_STATE.md,P02_SEAMS.md,ALPHA_ROADMAP.md}`, `docs/manual-tests/PC-01_prototype.md` — contract, migration and prose inventory evidence.

## Focused checks

- API, domain and analysis package contracts: **512 passed**.
- Real PostgreSQL migration/group/invariant/downgrade tests: **29 passed**, including upgrade from 0031, replay, rollback, duplicate/foreign sets and stale snapshot.
- Composition whole-port checks for the new group adapter: **2 passed**.
- `npm --prefix web run api:verify`, `typecheck`, `lint` and `test:contract`: passed; contract tests **187 passed**. Web unit suite: **2356 passed**; one localhost listener hit the sandbox's `EPERM` and passed when rerun with local process permission.
- Web guards: **288 passed** across 21 files, including the frozen-policy rendered-language check and frontend lock. Final typecheck and ESLint passed. `git diff --check` passed; the exact allowed-path inventory found **127 changed files, zero outside** the task's 35 allowed rules.
- Program acceleration/current-state check: **12 passed**. The task's initial broad command named two absent test directories; its addendum now names `analysis_packages` and the API seal suite's events coverage.

## Contracts, risk and handoff

The contract family is `1.2.0`, API surface 90 paths / 102 operations / 290 schemas, migration head `0032_ar_v3_run_group`; the error catalogue remains at 27 codes. The new `arg_` identity never aliases a Run. The lock binds the exact OpenAPI bytes and generated client to the committed content SHA. The migration preserves historical Runs; after group history exists, downgrade refuses rather than erase it.

The next data owners must review the exact C01–C22 map and source pages, then promote six distinct verified sets through custody. Install the reviewed pack in the server registry only after that evidence exists. The executor owner must resolve the pinned v3 profile, recheck the current Attempt and set custody before and after provider work, and preserve recorded request/response bytes. The CITE owner must gate review-only citations and any numerical output on deterministic evidence and explicit expert decision. The stand corpus designation, controlled live provider checks and full `make gate` remain with beta acceptance under `R-135`.

Rollback before the first group is a normal revert. After a group exists, disable new starts through the trusted-pack switch and retain the immutable group/run pins for readback and replay. This task changed no root dependency/lock file, global style, original topic or normative source bytes, provider transport, CITE publication, `origin/main`, tag or deployment host; its API/contract, migration and composition edits are covered by its exclusive integration slot.
