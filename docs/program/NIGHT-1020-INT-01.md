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

## 7. Slice W59 comparison (+ W62 П→Р) — published as development candidate `1af17a48`

Merged `W59-VERSION-COMPARE-01` (`367ea390`).

- **User-visible result.** «Сравнение версий» on the version screen: pick another
  version of the same set; with the same stage and section the deterministic
  comparison shows sheet pairing, paged line diffs with page anchors and finding-match
  proposals (labelled as proposals); `mode=stage` compares an earlier П version with a
  later Р version of the same section — the code half of W62 STAGE-COMPARE. Any other
  pair is refused with one closed reason; no AI layer, nothing persisted.
- **Contract.** 50/57/137 → **51/58/147** (`compareDocumentVersions`, 10 schemas); head
  and error catalogue unchanged; mirror byte-identical.
- **Checks on the merged tree.** `tests/contract` + `tests/unit` + journey conformance:
  1094 passed, 2 failed (both reproduce on the base: `test_error_kernel`,
  `test_ar_v2_seeded`); web `typecheck` clean. Lane: 187 comparison tests (two 500-page
  versions), 9 HTTP composition cases, 835 vitest, lint clean.
- **Found gap.** A further version cannot be uploaded into an existing set through the
  product (`uploadDocument` always creates a new document) — dispatched as
  `W59-VERSION-UPLOAD-01`.

## 8. Round 3 dispatch and slot queue

| Task | Phase A base | Slot |
| --- | --- | --- |
| `W57B-NORMS-CATALOGUE-XLSX-01` | `849dddd4` | holds it from `1af17a48` |
| `W59-ANALYSIS-SETTINGS-01` | `121ef2ce` | queued |
| `W59-VERSION-UPLOAD-01` | `641f2b9e` | queued |
| `W61-DISPATCHER-01` (migration 0025 in phase A) | `979632af` | queued |
| `W59-SEAL-FOLLOWUP-01` (suites only) | `77aa55bd` | none needed |

## 9. Integrator decision: a shared contract slot (from 04:30)

With four lanes queued behind one contract owner and the window closing, the
integrator opened the slot to parallel reseals under `R-139`: each lane reseals from
the published integration tip, and before its hand-back merges the newest tip, keeps
both sides' paths and schemas in `contracts/api/v1/openapi.json`, and **re-derives**
every derived artifact (web mirror copy, `api:generate`, `api:verify`,
`FRONTEND_LOCK.json`, `tests/support/expected_facts.json`, every surface-count prose
line) instead of hand-merging it, then reruns `tests/contract`. The migration head
stays single-owner (`0025` dispatcher, `0026` price lists chained on it). AGENTS §3's
single-owner rule is suspended for the API surface only, for this window only.

## 10. Slices published from the shared slot

- **`W59-ANALYSIS-SETTINGS-01`** (`b344f004`) — candidate `0f0903f2`. «Настройки
  анализа» lists the 15 sections with their profile (`listAnalysisProfiles`, status
  builtin/draft/reviewed, prompt-bundle hash, legacy source); АИ, ПЗ, ПОС and ТХ runs
  reach `published` in recorded mode with synthetic recordings keyed to each profile's
  own request; ПБ and unclassified versions are refused; one profile's recording never
  answers another's. 51/58/147 → **52/59/153**.
- **`W59-VERSION-UPLOAD-01`** (`bddaa058`) — candidate `a820849a`. «Загрузить новую
  версию» adds the next immutable version to an existing set (`uploadDocumentVersion`,
  same envelope, custody and outbox as `uploadDocument`); the new version is current and
  unclassified, older versions untouched; a concurrent-upload ordinal race in
  `publish_version` (reachable before) is fixed by a row lock. This closes the gap the
  comparison slice found. **53/60/154**; nginx upload locations widened in both proxy
  files.
- **Checks on the merged tree** after each merge: `tests/contract` + `tests/unit` +
  journey conformance (+ upload headroom): 1113 passed, the two base reds only; web
  `typecheck` clean; mirror byte-identical.
- **Debts to add at window close:** synthetic recordings cover only the AR baseline
  document and four sections; `Dockerfile.api` comment names only `text_analysis/**`;
  D-174 (BFF memory under a real 250 MiB bundle) now also covers the version upload.
- **`W59-DECISION-CARRYOVER-01`** (`2d8dbee8`) — candidate `c22f2049`. On «Сравнение
  версий» an expert carries a decision from an older finding onto the `unchanged`
  matched finding of the newer version («Перенести решение»), only while the
  recomputed comparison still proposes the pair; the target gets one new event with a
  fixed provenance sentence, nothing else is written; no migration. A pre-existing red
  (`test_rules_are_load_bearing`, `decided_severity`) is repaired. **54/61/158**.
- **`W57B-NORMS-CATALOGUE-XLSX-01`** (`4639f3be`) — candidate `beafeab5`. «Нормы» gains a
  catalogue of the current snapshot (`listNormDocuments`: 674 documents, 23 kinds;
  257 display designations repaired by a deterministic derivation, snapshot rows
  untouched, measured read-only on the local real-corpus stand at ~20 ms); a run's
  findings download as Excel in the legacy layout (`exportRunXlsx`, expert) through the
  certified chain, two chain defects fixed (500-page label bound, v1 findings). A
  pre-existing red (`test_v2_csv_severity` UPDATE on an immutable row) repaired.
  **56/63/161**.
- **Checks on the merged tree** after each: `tests/contract` + `tests/unit` + journey
  conformance 1184 passed, the two base reds only; web `typecheck` clean; mirror
  byte-identical.
- **`W61-DISPATCHER-01`** (`6f014201`) — candidate `f7664f59`. «Диспетчер» (`/dispatcher`,
  group «Работа»): an administrator assigns a project or a document set to an active
  expert, reassigns or cancels; the expert takes it, completes it or returns it with a
  reason from «Мои задачи» on the home screen; one open assignment per scope; every
  change is an append-only event and the state is derived by a view (migration
  `0025_work_assignments`, `asg_` identities, state machine `work_assignment`, domain
  candidate revision 15). Q-2's W61/W62 placement is moot for the code under `R-139`.
  **59/67/171**, head **`0025_work_assignments`**. Merged-tree checks: 1249 passed, the
  two base reds only; `typecheck` clean.
