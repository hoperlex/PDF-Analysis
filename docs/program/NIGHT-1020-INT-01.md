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

## 5. Slice W59 sections — published as development candidate `c4cbc026`

Merged in order: `W59-SECTION-PROFILES-01` (`e027b0d9`), `W54-LOCAL-IMPORT-01`
(`b8ed5068`), `W59-SECTION-SEAL-01` (`28c23819`), `W59-SECTION-UI-01` (`e2b0b58c`).

- **User-visible result.** An expert confirms a version's stage П/Р and one of 15
  sections on the version screen; versions, documents and the project screen show it,
  the project screen groups documents by confirmed section; run start and re-audit
  route through the text-profile registry (AR from the v1 constants plus 13 draft
  legacy-ported profiles; none for ПБ) and refuse an unclassified version or a
  section without a profile, with a Russian explanation on the run control.
- **Contract.** 48/55/131 → **50/57/137**; error catalogue unchanged at 25 (23
  stored); migration head **`0024_version_classification`**; contract SHA-256
  `3e1f070a…`, web mirror byte-identical (`cmp`).
- **Checks on the merged tree.** `tests/contract` + `tests/unit`: 942 passed, 3
  failed — two reproduce on the base (`test_error_kernel::test_there_are_twenty_four`,
  `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`), the third
  (`test_alpha_acceptance_command`) only refuses an uncommitted checkout and passes on
  the committed tree (120 passed with the journey conformance test). Web `npm ci`,
  `typecheck` and `lint --quiet` clean. Lane-level evidence (migration upgrade,
  routed execution, refusals, mutations, vitest) is in each lane's report.
- **Integrator edits.** `CURRENT_STATE.md` surface/head/W59 paragraph; two DB tests
  read the head from `tests/support/expected_facts.json` instead of the literal
  `0023_norm_citations`.
- **Deferred.** Complete gate, live journey, DB suites on the merged tree (`R-126`),
  field evidence of the profiles. Debts `D-178` … `D-182`.

## 6. Round 2 dispatch

| Task | Phase A base | Contract slot |
| --- | --- | --- |
| `W59-VERSION-COMPARE-01` | `890deb80` | holds it from `c4cbc026` |
| `W57B-NORMS-CATALOGUE-XLSX-01` | `849dddd4` | next |
| `W59-ANALYSIS-SETTINGS-01` | `121ef2ce` | after it |
