# Task EMBED-01 — the encoder, the night window, the pause of vectors

## Outcome
The offline encoder container, the host timer, the window states, the check in run issue, the wait cause `vector_window`, the export and import of intents, the backfill and the loud skip work as `ADR-0029` decision 8 says.

Owner: the encoder lane.

## Depends on
- CRIT-SEAL-50

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 8 and temporary decision 2; plan section 5
- the image is built from `infra/norms-worker/Dockerfile`; the command is `python -m auditmanager.norms.embedding embed-texts --in … --out …`
- the production host has 4 GB; no memory limit is set on any service today
- plan: the «Прецеденты» plan (version 5, with the R-154 correction) is the integrator's working copy `.local/evidence/lane-common-prec/plan-v5.md` and is not in git; the decisions it carries are in `ADR-0029`
- rules: the common rules of the programme (`.local/evidence/lane-common-prec-2026-11-10.md`, git-ignored): minimal checks only, tests under the host lock, no push, merge or tag
- the plan read the code at `5342b7178`, which has the same code as the base; every `path:line` the lane relies on is checked in its own worktree before use

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `infra/deploy/compose.server.yml` (services) and `infra/deploy/verify-deployed.sh` (checks)
- enumerator_owner: EMBED-01
- totality_query: `awk '/^services:/{s=1;next} /^[a-z]/{s=0} s && /^  [a-z0-9-]+:[ ]*$/{print $1}' infra/deploy/compose.server.yml` (nine services at the base; the lane adds one)

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `infra/deploy/compose.server.yml`
- `infra/deploy/deploy.sh`
- `infra/deploy/verify-deployed.sh`
- `infra/deploy/README.md`
- `infra/norms-worker/**`
- `src/auditmanager/precedents/**`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/executors/host_commands.py`
- `src/auditmanager/api/routers/**`
- `tests/integration/jobs/**`
- `tests/unit/precedents/**`
- `tests/contract/test_compose_flag_forwarding.py`
- `scripts/recovery/product_purge.py`
- `infra/deploy/embed-window.sh`
- `infra/deploy/systemd/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- `api/routers/**` only for the implementation of the vector stubs the seal left; `jobs/repository.py` only for the window check in the same query as the analysis pause
- `scripts/recovery/product_purge.py` only for the `vector.` events and the command type of this lane

## Non-goals
- no database access and no network for the container
- no resident encoder
- no HNSW

## Deliverables
- service in the profile `embedder` that `up` does not start; `mem_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:?}`, `memswap_limit` equal to it, `oom_score_adj: 1000`, 2 CPUs, 2 threads, batch 8
- the window states `closed`, `draining`, `encoding`, `skipped` with a reason; the new-run check in the same query as the analysis pause; the wait cause `vector_window` with the text «ночное окно векторов, до HH:MM»
- export of intents (deduplicated by `input_sha256`) to a file and import of vectors with a unit-norm check; the backfill of existing cases; a text over 512 tokens becomes `poisoned` and is visible
- `deploy.sh` checks the disk before building the image; `verify-deployed.sh` checks the image and the timer
- `infra/deploy/embed-window.sh` and `infra/deploy/systemd/` (the timer unit) are new

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- in `draining` the issue takes no new run
- compose refuses to start the service without `ALPHA_MEM_LIMIT_EMBEDDER`
- a skipped window writes `skipped` and is visible
- a text over 512 tokens becomes `poisoned`
- deduplication by `input_sha256`
- the container has no network and no database

## Integration contract
`PREC-PASS` consumes the imported vectors. The first night under observation is the check of the memory limit; a lack of memory is loud.

## Failure/idempotency/security cases
- out of memory or timeout: the intents stay, the window is skipped loudly, the next night repeats

## Rollback / feature flag
Disable the timer; the intents wait.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
