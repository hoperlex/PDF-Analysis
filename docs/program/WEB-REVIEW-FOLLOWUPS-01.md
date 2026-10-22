# WEB-REVIEW-FOLLOWUPS-01 — severity in the history, and four defects seen on the way

Task: `docs/program/tasks/WEB-REVIEW-FOLLOWUPS-01.md` (copied from `origin/dev` `d087c101`,
identical bytes). Branch `agent/web-review-followups-01`, base `64203e91` (`integration/beta-1`).
Web only; no contract, migration, dependency, global style or `shared/**` file changed.

## Result

- **The decision history and the knowledge base show the decided severity beside the verdict.**
  An event or record that carries `severity` shows «важность» and the existing `SeverityBadge`
  (Russian label, contract value on `data-severity` only); one without it renders exactly the
  markup it rendered before, byte for byte (the legacy line is written out as a literal in the
  test, and that test is green on the base tree).
- **A pending reject says «Отклоняю…».** The verdict feature now reports `pendingIntent`, read
  from the request in flight; the review page uses it instead of `'accept'` for any pending
  verdict.
- **A verdict result no longer leaks to another finding selection.** `useRecordVerdict().result`
  is returned only when the event in it was recorded against the bound finding (the server's own
  `event.finding_uid`), so the page falls back to the finding's own verdict on every other one.
- **The severity refusal sentence goes when the expert picks a severity.** The feature gained
  `clearRefusal` (forgets the browser's refusal and nothing else); the panel calls a new optional
  `onSeverityChosen` on a pick of one of the five severities (not for the «not chosen» option, not
  for an unknown value); the page hands it `verdict.clearRefusal`.
- **A comment refusal re-renders.** Confirmed by a test that fails on the base tree, then fixed:
  `useAppendComment` keeps the refusal as state, filed under the finding it was raised for.
- **The contrast census now renders a v2 finding** (item 6): four new screens, and the census
  stays green.

## Changed files

Source (all inside the allowed paths):

- `web/src/widgets/decision-history/ui/decision-history.tsx`, `web/src/widgets/knowledge-base/ui/knowledge-base.tsx`:
  the severity span with `SeverityBadge`, rendered only when `severity` is present.
- `web/src/features/record-verdict/model/verdict-request.ts`: `verdictIntentOf(request)`.
- `web/src/features/record-verdict/model/use-record-verdict.ts`, `index.ts`: `pendingIntent`,
  `clearRefusal`, `result` per finding; `verdictIntentOf` exported.
- `web/src/features/append-comment/model/use-append-comment.ts`: refusal as state per finding.
- `web/src/widgets/decision-panel/ui/decision-panel.tsx`: optional `onSeverityChosen`.
- `web/src/_pages/review/ui/review-page.tsx`: `pendingIntent` from the feature, `onSeverityChosen`.

Tests (all under the allowed `web/tests/unit/` directories):

- `web/tests/unit/review/history-and-kb-severity.test.ts` (29, new): item 1.
- `web/tests/unit/decisions/verdict-feedback.test.ts` (16, new): items 2, 3, 4 at the hook.
- `web/tests/unit/decisions/comment-refusal.test.ts` (9, new): item 5.
- `web/tests/unit/review/review-page-followups.test.ts` (9, new): items 2, 3, 4 at the page,
  with the real panel.
- `web/tests/unit/review/decision-panel-handlers.test.ts` (+11, 22 in all): item 4 at the panel.
- `web/tests/unit/styles/screens.ts`: item 6, four new screens and their fixtures; no existing
  screen or fixture was changed.
- `web/tests/unit/styles/v2-review-screens.test.ts` (8, new): each new screen holds the markup it
  was added for (a screen that renders a spinner would make the census vacuous, `D-88`).

## Checks (worktree `.local/worktrees/lane-d`)

Redirected to files in the session scratchpad, exit status read from `$?`, one process at a time
under `nice -n 10`, through the read-only `web/node_modules` symlink, every vitest run with
`--no-cache`; `free -m` available was 2.9-3.7 GiB and `df -B1M /` free 5.3 GiB before each run.
The complete gate on the host (`.local/gates/night-b315655d`) had not written `END` when the last
run finished, so nothing else was run.

| command | exit |
|---|---|
| `git diff --check` (on the final tree) | 0 |
| `npm --prefix web run typecheck` | 0 |
| `npm --prefix web run lint -- --quiet` | 0 |
| `npm --prefix web test -- --run --no-cache tests/unit/review tests/unit/decisions tests/unit/widgets tests/unit/entities tests/unit/styles tests/unit/run` | 0 (41 files, 573 tests) |
| the six guards, each in its own run: `tests/guards/rendered-language.guard.test.ts` (26) | 0 |
| `prepared-sections.guard.test.ts` (10) | 0 |
| `presentation-language.guard.test.ts` (4) | 0 |
| `gender-agreement.guard.test.ts` (10) | 0 |
| `dashboard-invalidation.guard.test.ts` (32) | 0 |
| `lazy-boundary.guard.test.ts` (24) | 0 |
| extra, because `screens.ts` is read by them: `screen-set.guard.test.ts` (11), `screen-claims-about-the-system.guard.test.ts` (6) | 0, 0 |
| extra: `tests/unit/screens` (14 files, 306 tests) | 0 |

The typecheck and lint were run on the final source; the battery was run again on the last code
commit (`453b4765`), after the last test change. This report is the only later commit.

### Failing first

The tests were written before the source and run on the base tree (the base source with the new
test files added), logs in the scratchpad:

- item 1 (`history-and-kb-severity`), first run, 29 tests: 18 red, 11 green. The 11 green are the
  legacy-markup literals, the verdict-span cases and the «no raw value as a word» cases (vacuous on
  a tree that renders no severity): they pin what the base tree renders and stay green after the
  change. Two of the green tests (a severity key present and `undefined`) were then removed because
  `exactOptionalPropertyTypes` makes them untypeable, and two «no Latin word» tests were added; those
  are green on the base tree for the same vacuous reason and red under H7 and K7 below.
- items 2, 3, 4, 5 at the hooks (`verdict-feedback`, `comment-refusal`): 17 red, 8 green. Item 5's
  «asks for a render, because nothing else will» is red on the base tree: the empty press wrote a
  ref and scheduled nothing, which confirms the suspected defect. (The test models React's
  contract, not a browser: a ref persists and schedules nothing, a state setter schedules a
  render; see the file header.)
- items 2, 4 at the page and the panel (`review-page-followups`, `decision-panel-handlers`):
  8 red, 23 green. Item 2 failed on the base tree with `expected 'accept' to be 'reject'`.
  The two item-3 cases at the page are green on the base tree by design: the page code is
  unchanged, the leak is closed in the hook, and they pin that the page uses the feature's answer
  only when it has one.

## Mutation probes

One reversible in-place edit of a committed file, the named test files run, the file restored with
`git checkout -- <file>`, and `git diff --stat` printed empty after every row (the helper is a
scratchpad script, not in the repository). Every row is red.

Item 1, `history-and-kb-severity`:

- H1 never render the severity (`… || true ? null`) → 9 red. H2 render it for events WITHOUT one
  (`!== undefined ? null`) → 11 red. H3 drop the word «важность» → 1 red. H4 shorten the badge
  title → 1 red. H5 print the raw `event.severity` instead of the badge → 10 red. H6 move the span
  after the time and author → 1 red («puts it after the verdict and before the time and the
  author»). H7 English word «severity» → 2 red (the words case and «no Latin word»).
- K1 never render (knowledge base) → 9 red. K2 render for records without one → 11 red. K3 drop
  the word → 1 red. K5 raw value instead of the badge → 10 red. K6 move the span after the event
  type → 1 red. K7 English word → 2 red. (There was no K4.)

Items 2, 3, 4 at the hook, `verdict-feedback` + `verdict-severity`:

- V1 drop the `isPending` gate on `pendingIntent` → 1 red («nothing once the mutation has settled,
  though its variables are still held»). V2 always `'accept'` → 1 red. V3 `result: mutation.data ?? null`
  (the leak) → 3 red. V4 `=== findingUid` → `!==` → 4 red. V5 `clearRefusal` also resets the
  mutation → 1 red. V6 `clearRefusal` does nothing → 1 red.
- R1 `verdictIntentOf` maps everything but a comment (`!== 'comment'`) → 1 red. R2 drop the
  `undefined` guard → 1 red.

Item 5, `comment-refusal`:

- C1 never file the refusal → 7 red. C2 do not check the finding → 2 red. C3 a sent comment does not
  clear the refusal → 1 red. C4 `reset` does not clear it → 1 red. The pre-change implementation
  (a ref) is the base-tree run above: 4 of this file's 9 cases red.

Item 4 at the panel, `decision-panel-handlers`:

- P1 call `onSeverityChosen` for every change (also the placeholder and unknown values) → 2 red.
  P2 never call it → 6 red. P3 call it only when the pick is NOT a severity → 8 red.

Items 2, 3, 4 at the page, `review-page-followups` + `review-page-wiring`:

- G1 `pendingIntent` back to «accept for any pending verdict» (the old code) → 1 red. G2 drop the
  comment branch → 1 red. G4 do not pass `onSeverityChosen` → 1 red. G5 pass a no-op → 1 red.
  G6 ignore the feature's answer → 1 red. G7 fall back to `'pending'` instead of the finding's
  verdict → 1 red. (There was no G3.)

Item 6, `v2-review-screens`:

- S1 the v2 observation loses `proposed_severity` → 1 red. S2 the detail is seeded under the wrong
  key, so the screen renders a spinner → 5 red. S3 drop `merged_observations` → 1 red. S4 drop
  `severityRefusal` → 1 red. S5 the knowledge-base screen carries no severity → 1 red. S6 the
  history screen carries no severity → 2 red.

## Decisions taken (no recorded decision blocked any of them; the conservative default is named)

1. **Wording and markup of the severity in the history and the knowledge base.** «важность» then the
   existing `SeverityBadge` with the title «Важность, решённая экспертом», the words the decision
   panel already uses, in an unclassed `<span data-decided-severity=…>` placed after the verdict
   span. No new `am-…` class: a class needs a rule in a global stylesheet, which is forbidden here,
   and `styling-layer.test.ts` rejects an undeclared one; the parent's flex gap spaces it. The
   history line reads «приём → принято важность Критическое»; if the owner wants other wording it
   is one string per widget.
2. **A severity outside the closed set** is shown as the badge's own fault («Неизвестная важность»,
   `role="alert"`), as on the finding list and the panel, and the rest of the ledger is still shown.
   The widgets' fail-closed rule for unknown event types and verdicts (the whole history hidden) was
   not extended to severity, because the badge already has its own closed-vocabulary treatment.
3. **In the knowledge base the severity is the EVENT's** (the row is an event; the verdict printed
   is the finding's current one). A later comment or reject row therefore shows none, and the badge
   is not the finding's current severity. The title says «решённая экспертом», not «текущая».
4. **Where each fix lives.** `result` is filtered in the hook, not the page, so no future consumer
   can leak it; the identity used is the server's `event.finding_uid`, not the verdict. `pendingIntent`
   is read from the request in flight and only while pending (TanStack keeps `variables` after a
   mutation settles). The refusal is cleared by a feature method plus a panel callback, because the
   refusal lives in the feature's state and the panel holds none.
5. **`onSeverityChosen` fires on a pick of a severity only.** Taking the pick back with the
   «Выберите важность» option does not clear the sentence: nothing is chosen, so it is still true.
6. **The comment refusal is filed under the finding**, as the verdict refusal is, not only turned
   into state: the hook is bound at page level and outlives a change of selection, so a ref or a
   bare state would have carried finding A's refusal onto finding B.
7. **Census (item 6): new screens, no edits to existing ones**, so existing measurements and the
   language guards' inputs are untouched. A reachability test (`v2-review-screens`) was added
   because the census cannot say whether a screen holds what it was added for.
8. `comment.result`, `verdict.error` and `isPending` were left page-level (see the first risk).

## Contracts

None added or changed. Public additions: `verdictIntentOf`, `RecordVerdictApi.pendingIntent`,
`RecordVerdictApi.clearRefusal`, `DecisionPanelProps.onSeverityChosen`.

## Risks and known limitations

- **Found, not fixed (outside the five items):** the verdict and comment hooks still report
  `error` and `isPending` page-wide. After a press on finding A and a change of selection to B, B's
  panel can show A's failure («Вердикт не записан») and A's pending state disables B's buttons until
  the request settles. The same filter by finding that `result` now has would close them; it was not
  asked for, and `comment.result` has the same shape (the page does not read it).
- **Not exercised:** a real browser (the select's `onChange` and the buttons' `onClick` are called
  through the element tree, as in `REVIEW-V2-UI-01`; the comment-refusal test uses a model of React's
  hook contract), the live journey, `npm run e2e:pc01`, a v2 finding from the API. A changed screen
  would ordinarily owe the live journey (`AGENTS.md` §8, item 2); `R-144d` forbade it while the host
  gate runs. No claim of live or field evidence is made.
- **Language guards:** `rendered-language` renders the history and the knowledge base without a
  severity (`tests/guards/**` is outside the allowed paths), so the new wording is pinned by
  `history-and-kb-severity` (no Latin word, no raw value as a word) and not by that guard.
- `web/tests/unit/styles/screens.ts` is a shared census file: another lane that adds a screen near
  `ReviewPage loaded` or `RECORDS` can conflict textually; the additions are three hunks (an import,
  a fixtures block before `FRAME_EXPERT`, a screens block after `ReviewPage loaded`).

## Instruction for the integrator

Merge `agent/web-review-followups-01` as a real merge into the integration branch (it does not touch
`origin/dev`); the task file is byte-identical to the one on `d087c101`, so it merges cleanly with
dev. Light acceptance per `AGENTS.md` §8 and the task: `git diff --check`, the named tests,
`tests/contract` with the gate's own three ignores (not run here). The six new or extended test files
above are the evidence.

## Forbidden hotspots

`git diff --name-only 64203e91..HEAD` lists only: the task file; `web/src/_pages/review/ui/review-page.tsx`;
`web/src/features/{append-comment,record-verdict}/**`; `web/src/widgets/{decision-history,decision-panel,knowledge-base}/ui/*.tsx`;
`web/tests/unit/{decisions,review,styles}/*`; and this report. No `contracts/**`, `db/migrations/**`,
`infra/**`, `Makefile`, `pyproject.toml`, `uv.lock`, `web/package*.json`, `web/FRONTEND_LOCK.json`,
`src/auditmanager/**`, `tests/support/**`, `conftest.py`, `tests/e2e/**`, `web/src/shared/**`,
`web/src/_app/providers.tsx`, global stylesheet, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, ref, tag or
stand was touched, and nothing was run in or written to `.local/worktrees/gate-night`. The vitest result cache
was not written (`--no-cache` on every run).
