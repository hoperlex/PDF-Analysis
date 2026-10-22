# PC01-JOURNEY-GAPS-01 — the PC-01 journey walks the menu destinations `BETA-MATRIX-02` found unwalked

**Base:** `origin/dev` `ddcef5b2` (the freeze of `docs/program/tasks/PC01-JOURNEY-GAPS-01.md`).
**Branch:** `agent/pc01-journey-gaps-01`, worktree `.local/worktrees/lane-g`.
**Status:** PHASE 1 (container-free) DONE; PHASE 2 (the live recorded stack) PENDING -- this section is rewritten when it has run.

This report is interim: it is committed so that the lane has a record while the host's complete gate holds the machine.

## What each gap closed

`docs/program/BETA-MATRIX-02.md` section B12 kept the criterion at NEEDS-CODE for five walk gaps. Each now has steps, each with a
result and a refusal. `GAP_STEPS` in `tests/e2e/test_pc01_journey_conformance.py` pins every added step by name, screen, case and the
operations it declares; `PINNED_WRITE_STEPS` and `PINNED_ROUTES` pin the 95 write steps and the 29 routes that existed before.

| gap | steps (manifest `write.steps`) | result | refusal |
|---|---|---|---|
| «Блоки» | `blocks-portal-blocks-of-a-version-with-a-run`, `blocks-text-lines-of-the-same-version` | choose the project and the version in the chooser; `listVersionPortalBlocks` answers `produced`, the blocks are drawn, one image block's crop is loaded (`streamVersionPortalBlockCrop`); the second tab reads `getVersionBlocks` | `blocks-upload-a-document-no-run-has-read`, `blocks-a-version-no-run-has-read-says-so`: a version no run has reached is told `not_produced` and the tab draws no list, no count and no picture |
| the norm document view | `norms-document-text-and-pdf` | `getNormDocument`, `listNormParagraphs` and `streamNormDocumentContent` from the catalogue's first document, at page 1 | `norms-document-page-past-the-end`: a page the document does not have is told in words and asks the store for nothing |
| a successful «Вернуть» | `assign-work-to-be-given-back`, `my-tasks-take-the-work-to-give-it-back`, `my-tasks-give-the-work-back`, `dispatcher-shows-the-work-given-back` | assigned, taken, then given back through the return form with the reason it requires: one transition `returned` carrying the reason; the row waits for an administrator with no move left for an expert; the administrator sees the reason and the moves only an administrator has | (the existing `my-tasks-return-needs-a-reason`: an empty reason sends nothing) |
| `correctVersionClassification` | `classification-correction` | the first version's stage is corrected from П to Р, section АР kept, pressing twice: one request based on revision 1, revision 2 stored, the history keeping the confirmation beside the correction with its reason | `classification-correction-is-an-experts-act` (an administrator alone is offered nothing), `classification-correction-needs-a-change`, `classification-correction-needs-a-reason` (the form holds its button; nothing is sent) |
| the identity continuation | `identity.mjs` (not a step of `--phase all`) | PENDING the live run | its own refusals (pending, zero-role approval, purge conflict, rejected/unknown/archived sign-in, self-archive) |

`approveRegistration` is reached twice in a `--phase all` run: `accounts.mjs` provisions the expert-only and the administrator-only
account through the registration and approval screens. The matrix read the manifest's steps and so counted it as walked only by the
identity continuation; `rejectRegistration`, `updateUser` and `purgeUser` are still reached only by that continuation.

## Decisions taken (the task file does not decide; the conservative choice applies)

1. **A click names its row** (`click.within = {selector, text_contains}`; `cdp.mjs` `locatorExpression`, `write.mjs`). «Блоки» draws one
   identical «Выбрать проект» button per project and one «Показать блоки» per document, and gives a row no handle (`web/src` may not be
   changed here). Pressing the first row would press somebody else's project on any stand other journeys have written to. A row that is
   not there matches nothing. These clicks carry no `text`: `rendered-language.guard.test.ts` requires every click `text` of the manifest to
   occur in a statically rendered screen, and the chooser's rows are not among them, so naming them by text would have turned the web
   tier's guard red.
2. **The «Блоки» refusal is `not_produced` on a new DOCUMENT**, uploaded before the specification set. The chooser offers the current
   version of each document, so a version without a run needs a document nobody runs. A fourth version of the baseline, or a document
   uploaded last, would have been the newest thing `listDocuments` / `listVersions` answer, and the read walk follows the newest document
   and then its newest version to find a run: it would have stopped at a version screen with no run and lost the routes after it.
   `blocks-upload-a-document-no-run-has-read` therefore sits before `upload-specification-set`; the conformance test pins the order.
3. **The return uses a second assignment.** The first one is completed by the existing steps (`my-tasks-complete-the-work`) and a completed
   assignment offers no move. The new one is assigned, taken, and given back; it stays «Возвращено» on the lane.
4. **The correction changes only the stage of the first version (П to Р), and runs before the queue steps.** Section membership (the dashboard,
   «Оптимизация разделов») reads the CURRENT version's confirmed section, and the comparisons read the later versions' stage; the first version
   is neither, and АР is kept, so nothing the steps before it counted moves.
5. **`seed_norms.py` now stores the bytes each PDF binding names in the lane's object store, before it writes the rows that claim them**
   (`S3_*` from the lane's `.env`; with no usable store it exits 2 and writes nothing). The seeded PDFs had rows and no object, which is why
   `BETA-LIVE-JOURNEY-01` could not walk the document view. The bytes are a stand-in, not a PDF; what the steps assert is the three reads and the
   viewer's address, not what the browser's viewer draws.
6. **The past-the-end page is 9999 and no missing-document case is walked.** A refusal by an unknown but well-formed identifier would need an
   identity the journey did not capture, and `constants` may only hold members of a contract enumeration; the page past the end is refused by the
   screen itself and declares that the store is not asked.
7. **`block_count` is required to be at least 1**, not 12 (the committed bundle's count): the figure is the API's, and the live run is what
   would justify pinning it.
8. **`prove_the_guard_can_fail.py` restores `manifest.json` even when a run cannot start** (it did not; the first attempt in this lane left a mutated
   manifest behind and was repaired from git) and takes the interpreter from `JOURNEY_PROOF_PYTHON`, because a lane worktree has no `.venv` of its own.

## Checks, phase 1 (container-free), on the tree below

(recorded when the lane's last code commit is in; the interim figures: `pytest tests/e2e/test_pc01_journey_conformance.py` 132 passed, `node --test` of the two journey unit files 11 passed.)

## Live run

PHASE2-PENDING

## Not walked, and why

PHASE2-PENDING

## Risks and limits

* Phase 1 proves addressing, vocabulary, dataflow and the pins; it cannot prove that a handle works. Only the live run does.
* The moved/added data changes what a later route sees: a third document in the project (unclassified, never run), a returned assignment, a
  corrected classification on the first version. The reasons it does not change the read walk are in decisions 2 and 4; the live run is the check.

## Instructions for the integrator

1. Merge `agent/pc01-journey-gaps-01` (a real merge). No contract, migration, dependency, lock file, `web/src` or `src` file is touched.
2. Light acceptance: `git diff --check`, `node --test tests/e2e/pc01/journey/write.test.mjs tests/e2e/pc01/journey/navigation-retry.test.mjs`,
   `pytest tests/e2e/test_pc01_journey_conformance.py`, `tests/contract` with the gate's three ignores; and `npm --prefix web test` for the language
   guard (it reads this manifest's click texts: none of the new clicks carries a `text` the guard does not already see).
3. The matrix's B12 row can be restated once the live run below is read; `rejectRegistration`, `updateUser` and `purgeUser` are the identity run's.

## Containment

```
git diff --name-only ddcef5b2..HEAD
```

(recorded in the final version of this report.)
