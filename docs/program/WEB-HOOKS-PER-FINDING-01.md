# WEB-HOOKS-PER-FINDING-01 — a verdict or comment failure belongs to the finding it was raised for

Task: `docs/program/tasks/WEB-HOOKS-PER-FINDING-01.md` (unchanged). Branch
`agent/web-hooks-per-finding-01`, base `42f45ebb` (the freeze commit on `integration/beta-main`).
Web only; no contract, migration, dependency, global style or `shared/**` file changed. Debt `D-201`.

## Result

- **`useRecordVerdict` and `useAppendComment` report `error`, `isPending` and `pendingIntent` for
  the finding the last press was raised for, and for no other.** After a press on finding A and a
  change to finding B, B's panel no longer shows A's «Вердикт не записан» / «Комментарий не
  добавлен», no longer says «Принимаю…» / «Отклоняю…» / «Добавляю…» for a press made elsewhere, and
  its three buttons are enabled. Back on A the failure (or the busy state) is still there.
- **The comment hook's `result` is filed the same way** (only to the finding whose event it carries,
  the server's own `event.finding_uid`), as the verdict hook's already was.
- **`reset` dismisses only the held press of its own finding.** A reset bound to B no longer wipes
  A's failure.
- **The idempotency rule is unchanged** (one key per intent, reused on every retry, fresh after the
  intent succeeded), but its holder is now per finding, because B's buttons can be pressed while A's
  request is out (see Decision 3).
- **`rendered-language` renders the decision history and the knowledge base with a severity.**
  `Severity` joined the translated schemas (before, a raw `critical` beside a verdict was read as
  contract vocabulary and permitted), with a `data-severity` coverage marker and one hand-written
  accept per member in the matrix.

The review page (`web/src/_pages/review/**`) and the decision panel needed no change: they read
`error`, `pendingIntent` and `result` from the hooks, and the hooks now answer per finding.

## Changed files (`git diff --name-only 42f45ebb..HEAD`)

Source:

- `web/src/features/record-verdict/model/use-record-verdict.ts`
- `web/src/features/append-comment/model/use-append-comment.ts`

Tests (all under `web/tests/unit/{decisions,review}/` and `web/tests/guards/`):

- `web/tests/unit/decisions/mutation-model.ts` (new): React Query's real `MutationObserver` over a real
  `QueryClient`, with `useMutation`'s two behaviours around it (one observer per call site kept across
  renders; `setOptions` on every render, which also rewrites the callbacks of a still-pending mutation).
- `web/tests/unit/decisions/per-finding-feedback.test.ts` (new, 23): both hooks, press on A / switch to B.
- `web/tests/unit/review/review-page-per-finding.test.ts` (new, 6): the real page, real hooks, real panel.
- `web/tests/unit/decisions/{verdict-feedback,verdict-severity,comment-refusal}.test.ts`: the mutation's
  variables are now `{findingUid, request}`; the mocks and the `sent` / `mutationFn` calls follow. No
  assertion was weakened.
- `web/tests/guards/rendered-language.guard.test.ts`: `SEVERITY_DECISIONS`, `'Severity'` in
  `TRANSLATED_SCHEMAS`, a `data-severity` entry in `SCHEMA_MARKERS`, five more members in the
  «no longer permitted as visible text» list.

## Checks

Worktree `.local/worktrees/lane-h`, through the read-only `web/node_modules` symlink; every vitest run
with `--no-cache`; one process at a time under `nice -n 10`; output redirected to files in the session
scratchpad and `$?` read directly (never through a pipe). Before each run `free -m` available was
1.4-4.4 GiB (>= 1500 MiB at launch) and `df -B1M /` free 4.4-4.6 GiB (>= 3000 MiB). The host gate
(`.local/gates/night-b315655d`) read 91 % the whole time and had not written `END`; nothing was run in or
written to `.local/worktrees/gate-night`. No docker, no `make`, no e2e, no whole vitest suite.

| command (final code tree `cbf1c888`) | exit |
|---|---|
| `git diff --check 42f45ebb..HEAD` | 0 |
| `npm --prefix web run typecheck` | 0 |
| `npm --prefix web run lint -- --quiet` | 0 (after one fix: `import()` type annotations in the new tests) |
| `npm --prefix web test -- --run --no-cache tests/unit/review tests/unit/decisions tests/unit/widgets tests/unit/entities tests/unit/styles tests/unit/run` | 0 (43 files, 602 tests) |
| guard `rendered-language` (26 tests) | 0 |
| guard `prepared-sections` (10) | 0 |
| guard `presentation-language` (4) | 0 |
| guard `gender-agreement` (10) | 0 |
| guard `dashboard-invalidation` (32) | 0 |
| guard `lazy-boundary` (24) | 0 |

### Failing first

The reproduction was written and run on the base tree before any fix (logs in the scratchpad):

- `per-finding-feedback.test.ts`, first version (18 cases): 13 red, 5 green.
- `review-page-per-finding.test.ts` (6 cases): 5 red, 1 green (the verdict-shown pin, already filed per
  finding by `WEB-REVIEW-FOLLOWUPS-01`, kept as a pin).
- Both files in their FINAL form against the base hook sources (`git checkout 42f45ebb -- web/src/features/
  record-verdict web/src/features/append-comment`, run, restored; `git status` and `git diff --stat HEAD`
  empty afterwards): **24 red of 29**. The five green are: a verdict answer goes to its own finding; no
  press shows nothing; a retry with nothing in between keeps its key; the next press after a success
  mints a new key; the page's verdict-shown pin. The red ones fail for the reason a reviewer sees:
  `expected Error: Сервер недоступен to be null` (A's failure on B), `expected true to be false` (A's
  pending on B), the page markup containing `Вердикт не записан` / `Принимаю…` / `Отклоняю…` /
  `Добавляю…` on B, idempotency keys that differ where a retry must keep its key, the request sent to
  the finding the hook was re-bound to (`expected ...Z to be ...B`), and a different set of cache keys
  refreshed than A's (those of the finding the hook was bound to when the answer arrived).

### Mutation probes

Each row: one reversible in-place edit of a committed file, the named tests run, the file restored with
`git checkout -- <file>`, and `git diff --stat` printed empty after the restore (the helper is a
scratchpad script, not in the repository). All rows replayed on the final tree `cbf1c888`. Hook rows run
`tests/unit/decisions` + `review-page-per-finding.test.ts`; guard rows run `rendered-language`.

Verdict hook (`use-record-verdict.ts`):

- V1 `isPending` page-wide (`mutation.isPending`) -> 1 red. V2 `pendingIntent` page-wide -> 3 red.
  V3 `error` page-wide (`mutation.error`) -> 3 red. V4 `reset` unconditional -> 1 red.
- V5 the previous intent is read from the LAST slot of any finding (`[...values()].at(-1)`) -> 1 red.
  V6 `onSuccess` forgets the key without checking it is the completed intent's -> 1 red.
  V7 `onSuccess` refreshes the caches of the closure's finding instead of the press's -> 1 red.
  V8 `mutationFn` sends to the closure's finding instead of the press's -> 1 red.

Comment hook (`use-append-comment.ts`):

- C1 `isPending` page-wide -> 2 red. C2 `error` page-wide -> 2 red. C3 `reset` unconditional -> 1 red.
  C4 `result` unfiltered (`mutation.data ?? null`) -> 1 red.
- C5 last-slot previous intent -> 1 red. C6 unconditional key forget -> 1 red. C7 closure's caches
  -> 1 red. C8 closure's finding on the wire -> 1 red.

(V5 and C5 were first GREEN: with a per-finding map a succeeded press deletes its own slot, so
"A fails, B succeeds, A retries" leaves A's slot as the last one. Two cases were added in which B FAILS
in between, and V5/C5 went red; that is the only reason those two tests exist.)

`rendered-language` (the widgets' severity text, `decision-history.tsx` and `knowledge-base.tsx`):

- GL1 history: «важность» -> the Latin word `weight` -> 2 red. GL3 knowledge base: same -> 2 red.
- GL2 history: the badge replaced by the raw `{event.severity}` -> 2 red. GL4 knowledge base: same -> 2 red.
- GL6 the guard's own seed loses its `check_adjacent` event -> 1 red (the coverage case, naming the
  member).
- Necessity of the extension: the guard as it was before this slice (`git checkout fd026769~1 -- <guard>`)
  with GL2 or GL4 applied stays GREEN (exit 0, 0 red) -- it was blind to a raw severity value -- and
  both files were restored (`git status` and `git diff --stat HEAD` empty).
- The Latin word `severity` is NOT a usable probe: it is a CSV column name, and the guard permits the
  contract's CSV columns as visible text. A regression to the English word «severity» in this particular
  wording therefore passes the guard (see risks); `weight` is not in the contract and is caught.

## Decisions taken (the task file does not decide; the conservative option is named)

1. **The press is the mutation's variable.** `useMutation<AppendDecisionResponse, Error, VerdictPress>`
   with `VerdictPress = {findingUid, request}` (same for comments). One source of truth, set atomically
   by `mutate`, rather than a second state or a ref that could drift from the mutation (the older hook
   tests replace `useRef`/`useState` by single holders, which a second cell would have broken). The
   existing hook tests were updated to the new variables shape; their assertions are unchanged.
2. **The hook reports the LAST press only.** A press on B replaces the report about A (A's request still
   completes and still refreshes A's caches). "A failure of A is still shown on A when the expert returns
   to it" holds across any change of selection that is not followed by a press on another finding.
   Keeping a failure per finding across later presses would need a map of states beside the observer, a
   larger change than the task asks for.
3. **The idempotency holder is per finding, and a success forgets only the intent it completed.** This
   is not a change of the rule; it is what keeps the rule true once B's buttons are enabled while A is in
   flight. With one slot for the hook, B's press overwrites A's key (A's retry would mint a new one) and
   A's success empties B's (B's retry would mint a new one): a retry with a fresh key appends a second
   event to a ledger that has no delete. `resolveIntentKey`, `intentSignature` and the `shared/lib` rule
   are untouched.
4. **`mutationFn` and `onSuccess` use the press's finding, not the render's.** React Query rewrites the
   callbacks of a pending mutation with the latest render's on every render, so with the closure's
   `findingUid` a success arriving after the selection moved refreshed the caches of the wrong finding
   (the base tree did this; V7/C7/V8/C8 pin it).
5. **`reset` dismisses the mutation only when it holds this finding's press.** It still clears the
   browser refusal as before.
6. **No new wording and no page change.** The Russian copy is the existing copy; the page already reads
   the hooks.
7. **Guard: `Severity` is a translated schema, the seeds are hand-written.** One accept per member
   (`SEVERITY_DECISIONS`), so a sixth severity reddens the coverage case instead of seeding itself, as the
   file's own rule says. The journal rows of the knowledge base are built from `DECISIONS` and inherit them;
   the first events carry none, so the legacy line of both screens is still rendered.

## Contracts

None added or changed. No public export added or removed from either feature; `RecordVerdictApi` and
`AppendCommentApi` keep their fields, with documentation of the per-finding meaning.

## Risks and known limitations

- **Pressing B while A is still out is now possible** (it is the point of the slice). The hook reports the
  last press only, so after that press A shows enabled buttons although its first request may still be in
  flight. A second press of the SAME intent on A reuses A's key (the server answers the same event); a
  press of a DIFFERENT intent on A (accept, then reject) is two commands, as it was whenever the first had
  already settled. The window is narrow (a slow request, a switch, a press elsewhere, a switch back, a
  press), and the append-only ledger has no delete, so it is named here. Closing it would need
  per-finding pending state beside the observer, not asked for.
- **A changed screen would ordinarily owe the live journey** (`AGENTS.md` §8, item 2): B's buttons are no
  longer disabled by A's request. Not run (`R-144d` forbids it while the host gate runs; the task's non-goals
  say so). No claim of live, browser or field evidence is made. The page-level tests render the real page
  once per state with `renderToStaticMarkup` and call the panel's own handlers taken from the rendered
  props; React Query's observer is real, React's event system and re-rendering are not.
- **The guard permits the word `severity`** (CSV column vocabulary), so only a Latin word outside the
  contract or a raw severity VALUE is caught in this wording.
- Not run (not named by the task): `tests/unit/screens`, `tests/contract`, `screen-set` and
  `screen-claims-about-the-system` guards (`screens.ts` was not touched), the whole vitest suite, the
  complete gate.

## Instruction for the integrator

Merge `agent/web-hooks-per-finding-01` as a real merge into `integration/beta-main`. The task file is
unchanged and the freeze commit is the base, so it merges without a conflict with the base; the two
feature hooks and `rendered-language.guard.test.ts` are the only shared files another lane could touch.
Light acceptance (`AGENTS.md` §8): `git diff --check`, `typecheck`, `lint --quiet`, the named battery and
the six named guards above. The live journey is owed for the changed behaviour of the review screen and
was not run here.

## Forbidden hotspots

`git diff --name-only 42f45ebb..HEAD` lists only the two feature hooks, the seven test files above and this
report; every path is inside the allowed list (`web/src/features/{record-verdict,append-comment}/**`,
`web/tests/unit/{decisions,review}/**`, `web/tests/guards/**`, `docs/program/WEB-HOOKS-PER-FINDING-01.md`).
No `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency or lock file,
`web/src/shared/**`, `web/src/_app/providers.tsx`, global style, `tests/**` outside `web/tests/**`,
`CURRENT_STATE.md`, `DEBT_REGISTER.md`, ref, tag or stand was touched. The widget files
`decision-history.tsx` and `knowledge-base.tsx` (outside the allowed list) were edited only for the
mutation probes GL1-GL4 and restored with `git checkout --` each time; they are absent from the diff. The
vitest result cache was not written (`--no-cache` on every run), and nothing was run in or written to
`.local/worktrees/gate-night`.
