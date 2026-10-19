# NIGHT-1020-INT-01 — integration record of the 2026-10-20 night window

**Integrator:** session `pdf-analysis-e9`, appointed by the owner for an unattended
8–10 hour window. **Ruling:** `R-139` (functional slices: sections, norms, storage
structure; bounded checks under `R-135`; no polls). One record for the whole
window, appended per publication, as `CODE-FIRST-TO-BETA.md` §2.1 item 4 allows.

## 1. Process rules on `origin/dev` (candidate `9cf21cc0`)

- Accepted `plan/cfb-vertical-slices` `38356acf` (vertical slices, one evidence per
  slice, host condition A13), recorded `R-139`, merged the W54 norms session's
  `agent/w54-norms-embed-bundle-01` `cb53ee6e` (embedding build and verified bundle
  records) and refreshed `CURRENT_STATE.md`'s corpus paragraph.
- Checks on the exact tree: `git diff --check origin/dev` clean;
  `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py` → 105 passed.
- `origin/dev` fast-forwarded `f942ca1c` → `9cf21cc0`.

## 2. Process rules on `origin/main` (candidate `ec3ebf07`, docs only)

- **Authority:** the owner's direct instruction in this session on 2026-10-20 to
  accept the slice/judging/gate liberalisation and merge it into main, stating that
  such documentation merges touch no code and need no complete gate. This record is
  the written form of that instruction; it waives the complete gate for this
  docs-only candidate only.
- **Candidate:** `ec3ebf07687e7db7ae5bf917b8da79b39e7545a7` = `origin/main`
  `37393a97` (v0.6.0 tree) plus five process documents taken unchanged from
  `9cf21cc0`: `AGENTS.md`, `docs/program/OWNER_RULINGS_2026-09-17.md`,
  `docs/program/dispatch/CODE-FIRST-TO-BETA.md`,
  `docs/program/dispatch/CODE-FIRST-SCOPE-W58-W63.md`,
  `docs/program/tasks/CODE-FIRST-BETA-01.md`. `git diff --name-only` shows no
  source, test, contract, migration, infra or dependency path.
- **Checks on the exact tree:** `git diff --check` clean; program governance and
  prose guards 93 passed; complete container-free `tests/contract` 789 passed /
  19,278 subtests, plus 109 passed on rerun of the four files that first errored
  because the fresh worktree lacked the governance interpreter (environment only).
- **Publication:** remote `main` re-read as `37393a97`, fast-forward proven, pushed
  `37393a97..ec3ebf07`.
- **Deployment:** workflow `deploy-auto` run `39316799669` for `ec3ebf07`
  completed `success` (job "Deploy exact AuditManager revision", step "Deploy and
  verify exact commit" success). Public origin probes at 2026-10-19T20:1xZ: `/` →
  `307` to `/login?next=%2F` over verified TLS (`ssl_verify_result=0`);
  unauthenticated `/api/v1/openapi.json` and `/api/v1/projects` → `401`.
- **Not verified:** `infra/deploy/verify-deployed.sh` was not run on the deployment
  host by this session (no host access); main still carries the workflow whose
  verify step can lose its stdin (the repair is on `origin/dev` only). The owner
  runs the host verifier.

## 3. Host cleanup (owner instruction 2026-10-20)

- Docker build cache pruned (`docker builder prune -a -f`, 7.05 GB) and the npm
  cache cleaned: free space on `/` 13.6 GB → 20.6 GB.
- 32 unmerged branches of 33 stale clone directories under `.local/worktrees/`
  were saved into this repository as `refs/backup/clones/<dir>/<branch>`, and one
  untracked task file into `.local/backup/clones-2026-10-20/`. Removing the clone
  directories and finished worktrees was refused by the session's permission
  layer; they remain for the owner to delete.

## 4. Round 1 dispatch (base `a1a25ebc`)

| Task | Lane | Hotspot |
| --- | --- | --- |
| `W59-SECTION-SEAL-01` | `agent/w59-section-seal-01`, stack 57480/61080 | contract, migration 0024, composition root |
| `W59-SECTION-PROFILES-01` | `agent/w59-section-profiles-01`, no services | none |
| `W54-LOCAL-IMPORT-01` | `agent/w54-local-import-01`, stack 57490/61090 | none |
