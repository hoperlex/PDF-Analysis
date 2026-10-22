# PC01-JOURNEY-GAPS-01 — the PC-01 journey walks the menu destinations `BETA-MATRIX-02` found unwalked

**Base:** `origin/dev` `ddcef5b2` (the freeze of `docs/program/tasks/PC01-JOURNEY-GAPS-01.md`), then — by the integrator, at the integrator's
order — `integration/beta-main` `dd562bcf` merged in (merge commit `7a238a52`; lanes B, C, D, E and H: the review screen v2, the double-press
guards, the per-finding hooks, the PB profile). No file under `tests/e2e` changed by that merge.
**Branch:** `agent/pc01-journey-gaps-01`, worktree `.local/worktrees/lane-g`.
**Tested tree (the live run):** `7a238a52` plus the working-tree edits that became commit `7e9e88ea` (the journey's `manifest.json`,
`seed_norms.py` and `identity.mjs`; `web/src` and `src` are exactly the merge's). Commits after it are the conformance test's pins of those repairs,
the README and this report; none touches what the browser meets.
**Status:** the journey now declares **109 write steps and 29 read routes** (before: 95 and 29) and ran **green on the full beta tree**: exit `0`,
`write steps checked: 109/109`, `routes checked: 29/29`, `e2e:pc01 OK`; the identity continuation ran for the first time on a built stack and
**passed** (12 operations, 18 checks). Recorded provider only; no spend.

## The live run

Stack (this lane, `auditmanager-lane-g`, ports below the ephemeral range): PostgreSQL 57670 and MinIO 61470/61471 from `make up` (migrations to
`0029`); the API from `infra/deploy/serve.py` on 28572 with `EXECUTION_ROLE=api` and `AUDITMANAGER_PROVIDER_MODE=recorded`, a worker
(`python -m auditmanager.workers serve`), and `next start` on 28574 built from the merged tree with `NEXT_PUBLIC_API_BASE_URL=/bff/v1`
(`next build` peak 976 MiB resident under a V8 heap bound of 1200 MiB). The deployment secret and the administrator's new password were generated
inside the launching process and written nowhere. The host was loaded by other lanes' test runs (load average 25 for part of it).

| run | command (credentials from the environment) | result |
|---|---|---|
| 1 | `npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:28574 --phase all --out …/evidence/run-1` | exit **1**, **109/109** write steps and **29/29** routes checked, 374 s, **2 findings** (below) |
| 2 | the same, `--out …/evidence/run-2` | exit **0**, **109/109**, **29/29**, `e2e:pc01 OK`, 345 s |
| identity | `node tests/e2e/pc01/journey/identity.mjs --origin … --journey …/run-2/journey.json --out …/run-2/identity2` | exit **0**, `identity: PASS`, 12 operations, 18 checks (5 earlier attempts in this lane failed at stale stages, below) |

Envelopes (untracked `.local` of the lane's worktree; no credential, token or cookie in them):
`/root/projects/PDF-Analysis/.local/worktrees/lane-g/.local/evidence/run-2/journey.json` and `…/run-2/identity2/identity.json`
(`run-1/` is the red first run). The two findings of run 1, both repaired in `7e9e88ea` before run 2:

1. `analysis-settings-lists-the-profiles` (a step of the base journey) required a section with no profile (`tr[data-profile="none"]`). On the beta tree the
   PB profile exists, so all fifteen sections have one (AR builtin, fourteen drafts that say they need an expert's check). The step now requires the AR
   builtin row and the drafts' sentence.
2. `norms-document-text-and-pdf` (a new step): `getNormDocument` answered `paragraph_count = 0` for seeded documents that had paragraphs. The seed wrote the
   column as `0`; it now states the count.

All 14 other new steps were green in run 1 and in run 2. What they measured on the stack:

| step(s) | measured |
|---|---|
| `blocks-portal-blocks-of-a-version-with-a-run` | `listVersionPortalBlocks` `200` `produced`, `block_count` 12 (8 text, 2 stamp, 2 image), 2 crops, both `streamVersionPortalBlockCrop` `200` `image/png` |
| `blocks-text-lines-of-the-same-version` | `getVersionBlocks` `200` `produced`, 78 text lines |
| `blocks-upload-a-document-no-run-has-read`, `blocks-a-version-no-run-has-read-says-so` | `uploadDocument` `201`; `listVersionPortalBlocks` `200` `not_produced`, `block_count` 0, no items, the tab draws no list, count or picture |
| `norms-document-text-and-pdf` | `getNormDocument` `200` (`content_available` true, 12 pages, 1 paragraph), `listNormParagraphs` `200`, `streamNormDocumentContent` `200` `application/pdf` (the 63 stand-in bytes the seed stored) |
| `norms-document-page-past-the-end` | the document and the paragraphs are read; **no** `/content` request; the screen says the page does not exist |
| `assign-…-given-back`, `my-tasks-take-…`, `my-tasks-give-the-work-back`, `dispatcher-shows-…` | one `transitionAssignment` `200` with body `{"kind":"returned","reason":"…"}` and answer `status: returned`; the administrator sees the reason and the moves only an administrator has |
| `classification-correction*` (4 steps) | `correctVersionClassification` `201`, one request for two presses, body based on `expected_revision: 1`, answer `revision: 2` (`project_stage` `R`, section `AR`); the history lists revision 1 (confirmation) and 2 (correction) |

## What each gap closed

`GAP_STEPS` in `tests/e2e/test_pc01_journey_conformance.py` pins every added step by name, screen, case and the operations it declares;
`PINNED_WRITE_STEPS` and `PINNED_ROUTES` pin the 95 write steps and 29 routes the journey had before, by name and order.

| gap | steps | result | refusal |
|---|---|---|---|
| «Блоки» | `blocks-portal-blocks-of-a-version-with-a-run`, `blocks-text-lines-of-the-same-version` | choose the project and the version, read the portal blocks, one crop and the text lines | `blocks-upload-a-document-no-run-has-read` + `blocks-a-version-no-run-has-read-says-so`: a version no run has reached is told `not_produced` |
| the norm document view | `norms-document-text-and-pdf` | `getNormDocument`, `listNormParagraphs`, `streamNormDocumentContent` | `norms-document-page-past-the-end` |
| a successful «Вернуть» | `assign-work-to-be-given-back`, `my-tasks-take-the-work-to-give-it-back`, `my-tasks-give-the-work-back`, `dispatcher-shows-the-work-given-back` | assigned, taken, given back with its reason | (the existing `my-tasks-return-needs-a-reason`) |
| `correctVersionClassification` | `classification-correction` | stage П to Р, revision 2 | `classification-correction-is-an-experts-act`, `-needs-a-change`, `-needs-a-reason` |
| the identity continuation | `identity.mjs`, outside `--phase all` | `approveRegistration`, `rejectRegistration`, `updateUser` (role removal) and the other eight operations of `identity.operations`, run once on a stack | pending sign-in, zero-role approval, purge of a referenced account (`409 account_referenced`), rejected/archived/unknown sign-ins byte-identical, self-archive `403`, a revoked session, a role-less decision `403` |

`approveRegistration` is reached twice in a `--phase all` run: `accounts.mjs` provisions the expert-only and the administrator-only account through the
registration and approval screens. The matrix read the manifest's steps and counted it as walked only by the identity continuation.

## The identity continuation: five stages had gone stale

`D-137` recorded that it had never run on a built stand. Run on this stack it failed five times in a row, each at a stage that no longer matched the screen it
meets, and each repair is in `identity.mjs`:

* `assertProfile`: the profile prints the display label (`Тестов И. П.`) and keeps the names in form fields, which `innerText` does not hold.
* `revokedSession`: the role removal revokes the credential the web tier holds; the screen's own guard reads the account on the server, the API answers `401`,
  the tier closes the session's row and sends the browser to sign in — inside one navigation, so the browser never sees the `401`. The stage now requires the
  redirect, that the register row is gone, and that the seam answers `401 authentication_required` when asked once more.
* `deniedMutation` (was `decision` with the control pressed): since `R-80` a role-less account is turned away at `/403`; the review control is never drawn. The
  stage requires the `/403` and then asks the API for the decision directly with the same cookie: `403 permission_denied`.
* archiving an account and rejecting a registration ask for a confirmation first.
* a failed wait says where the browser was, what it showed and what the seam answered.

## Decisions taken (the task file does not decide; the conservative choice applies)

1. **A click names its row** (`click.within = {selector, text_contains}`; `cdp.mjs` `locatorExpression`, `write.mjs`). «Блоки» draws one identical «Выбрать проект» button per
   project and one «Показать блоки» per document, and gives a row no handle (`web/src` may not be changed here). Pressing the first row would press somebody else's
   project on any stand other journeys have written to. A row that is not there matches nothing. These clicks carry no `text`: `rendered-language.guard.test.ts` requires
   every click `text` of the manifest to occur in a statically rendered screen, and the chooser's rows are not among them. A `wait_for` for the row precedes each press.
2. **The «Блоки» refusal is `not_produced` on a new DOCUMENT, uploaded before the specification set.** `listDocuments` answers each document's current version, newest first
   (`ORDER BY published_at DESC`), and the read walk follows the first document and then its newest version to find a run. A fourth version of the baseline, or a document uploaded
   last, would have been newest and run-less, and the walk would have stopped at a version screen. The conformance test pins the order. The live run confirmed the walk is intact.
3. **The return uses a second assignment** — the first is completed by the existing steps, and a completed assignment offers no move.
4. **The correction changes only the stage of the first version (П to Р), after the steps that count confirmed sets.** Section membership reads the CURRENT version; the first version
   is neither current nor compared later.
5. **`seed_norms.py` stores the bytes each PDF binding names in the lane's object store, before it writes the rows that claim them** (`S3_*` from the lane's `.env`; with no usable store it
   exits `2` and writes nothing), and now states each document's paragraph count. The bytes are a stand-in, not a PDF; the steps assert the three reads, not what the browser's viewer draws.
6. **The past-the-end page is `9999`; no missing-document case is walked** — it would need an identity the journey did not capture, and `constants` may only hold members of a contract enumeration.
7. **`block_count` is required to be at least 1**; the live run measured 12 and 78, which the report records instead of pinning.
8. **`prove_the_guard_can_fail.py` restores `manifest.json` even when a run cannot start** (the first attempt in this lane left a mutated manifest behind and was repaired from git) and takes
   the interpreter from `JOURNEY_PROOF_PYTHON`.
9. **A hole the new work exposed was closed:** the words of a `wait_for` (`text_contains`) were read by neither `namesNeededBy` in `write.mjs` nor the conformance test's dataflow check; a template
   no step captured in a wait stayed GREEN under a quoted mutation. Both read it now.
10. **The matrix's identity gap names `purgeUser`; only its refusal is walked** (below).

## Checks (light acceptance, `AGENTS.md` §8; the complete gate was not run, `R-135`)

CHECKS-TABLE

## Not walked, and why

* **A successful `purgeUser` (`204`).** The continuation walks the refusal (`409 account_referenced`, an archived account that authored a decision). A purge that succeeds needs an
  account nothing references; the continuation makes none. Not walked.
* **What the browser's PDF viewer draws** on the norm document page: the seeded bytes are a stand-in, so the step asserts the three reads and the viewer's address.
* **A norm document that does not exist** (`404`), for the reason in decision 6.
* **The stand.** Everything above is a recorded local stack of this lane, not the published stand; no live provider, no real norms corpus, no deployed build, no edge (nginx) run.
* **`getAssignment`, `listPriceListPositions`, `listOptimisationPasses`, `listProposalDecisions`, `getRunNormVerification`, `getProductVersion`** from the matrix's list of unnamed operations are not in this
  task's five gaps and are not walked here.
* **"The full АР function matrix"** (B12's last clause) has no definition in the tree; not touched.

## Risks and limits

* The journey writes more state on an origin: a third document in the project (never run), a returned assignment, a corrected classification, accounts. It is for a lane or a test-data stand,
  and `--phase all` still refuses a non-recorded origin without `--allow-spend`.
* The lane's administrator is the seeded account taken off the shipped password; a password lost with its process can only be recovered by returning the lane's row to the shipped state
  (README, «Taking the seeded administrator off the shipped password»). Found on the way: the seeded login `admin` is not an e-mail, so its profile needs one, and the login then becomes it.
* The host was shared and loaded during the runs (other lanes' vitest); durations are not a benchmark.

## Instructions for the integrator

1. Merge `agent/pc01-journey-gaps-01` (a real merge; its tip contains your `7a238a52` merge of `integration/beta-main`). No contract, migration, dependency, lock file, `web/src` or `src` file is touched.
2. The matrix's B12 row can be restated from the live run above: «Блоки», the norm document view, a successful «Вернуть», `correctVersionClassification` and the identity continuation now have a recorded run on the full beta tree,
   except the unwalked items listed above (`purgeUser` success).
3. `scripts/manual-alpha-check.sh` / `make alpha-acceptance` call `--phase all` as before; the stand's `core` phase is unchanged (4 write steps, 29 routes).
4. If the web tier's screens change a handle the new steps read, `test_every_control_the_write_half_presses_still_exists_in_the_application` and `test_every_control_the_identity_continuation_presses_still_exists_in_the_application` name it.

## Containment

`git diff --name-only ddcef5b2..HEAD` (the merge brings the beta tree's own files, which are the integrator's; the lane's own changes are the first block):

CONTAINMENT
