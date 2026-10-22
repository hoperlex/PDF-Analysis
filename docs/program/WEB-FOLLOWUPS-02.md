# WEB-FOLLOWUPS-02 — one request per intent on four commands; the price list says a web-server refusal

Task: `docs/program/tasks/WEB-FOLLOWUPS-02.md` (closes `D-195`; the web half of `D-184`).
Branch `agent/lane-c-01`; this slice's base is `ff0b3ae2` (the end of `REVIEW-V2-UI-01`), the
task's frozen base is `d38f9c54`. Web only; no contract, migration, dependency or style changed.

## Result

- **Four hooks send one `POST` per intent in flight.** `start-optimisation-pass`,
  `create-assignment`, `transition-assignment` and `set-current-snapshot` now join a request
  already in flight for the same intent instead of sending a second one, and both presses get
  the one answer (or the one refusal). The gate reopens when that request settles, so a
  deliberate press afterwards is a new request. This is the guard `carry-over-decision`,
  `decide-optimisation-proposal` and `upload-price-list` already carry (`BETA-LIVE-JOURNEY-01`,
  `WEB-FOLLOWUPS-01`), written the same way: a ref holding `{ intent, promise }`, a `finally`
  that clears it.
- **What an intent is, per hook** (an exported pure function for the three that had no
  signature, so a test can pin each field):
  - start pass: the project and the document (the signature the hook already keyed its
    idempotency key by);
  - create assignment (`assignmentIntent`): project, document or none, expert, trimmed note;
  - transition (`moveIntent`): assignment, kind, trimmed reason, new assignee;
  - designate (`designationIntent`): the target and the current snapshot the screen believed.
- **The price-list upload says a web-server refusal in Russian.** A `413` from the host's body
  limit, and a `502`/`503`/`504`, now read as `classifyUploadFailure` reads them for the
  document upload («Сервер отклонил файл как слишком большой ещё до API … Лимит продукта —
  10 MiB; обратитесь к администратору стенда» and the three «Веб-сервер …» sentences), instead
  of «Запрос не дошёл до сервера … повторите попытку», which sent the user to resend a file
  that is refused again. Every other failure keeps the price-list entity's reading, which knows
  the file constraints.
- **`classifyUploadFailure` grew one optional argument** `{ limitLabel }`, the product's size
  limit named in the 413 sentence. It defaults to the document envelope's `250 MiB`, so the
  document upload is unchanged (its suite is green); the price list passes `10 MiB`. Reusing
  the shared sentence unchanged would have told a user whose price list was refused that the
  limit is 250 MiB, which is wrong in a way they can act on.
- **The price-list invalidation (item 3) was already in the tree.** `useUploadPriceList`
  invalidates the project's revisions, its priced specifications and the whole
  `optimisation / section-specification` prefix since `84f5a5f3`, and the in-flight join for
  the upload since `2750cd11`. I changed neither; I checked both with the existing tests under
  mutation (U1–U4 below). The clause «the price-list upload does not invalidate it» of
  `D-184` in `DEBT_REGISTER.md` is therefore stale.

## Changed files

Source:

- `web/src/features/start-optimisation-pass/model/use-start-optimisation-pass.ts`
- `web/src/features/create-assignment/model/use-create-assignment.ts`, `index.ts`
- `web/src/features/transition-assignment/model/use-transition-assignment.ts`, `index.ts`
- `web/src/features/set-current-snapshot/model/use-set-current-snapshot.ts`, `index.ts`
  (also exports the command type `SetCurrentSnapshotCommand`)
- `web/src/features/upload-price-list/model/upload-failure.ts` (new), `index.ts`,
  `ui/upload-price-list-form.tsx` (uses `priceListUploadFailure`)
- `web/src/entities/document-version/model/upload-failure.ts` (the `limitLabel` argument)

Tests (all under the allowed `web/tests/unit/` directories):

- `web/tests/unit/optimisation/start-pass-double-press.test.ts` (5)
- `web/tests/unit/dispatcher/assignment-double-press.test.ts` (13)
- `web/tests/unit/norms/designation-double-press.test.ts` (6)
- `web/tests/unit/upload/price-list-upload-failure.test.ts` (18)
- `web/tests/unit/norms/designation-command.test.ts`: one added `vi.mock('react', …)` giving
  `useRef` a plain holder, because the hook now keeps a ref and this suite calls it outside a
  render. No assertion changed.

## Checks (worktree `.local/worktrees/lane-c`, tip `abdc5f94`)

Redirected to files, exit status read from `$?`, one at a time under `nice -n 10`, through the
read-only `web/node_modules` symlink, every vitest run with `--no-cache`.

| command | exit |
|---|---|
| `git diff --check` | 0 |
| `npm --prefix web run typecheck` | 0 |
| `npm --prefix web run lint -- --quiet` | 0 |
| `npm --prefix web test -- --run --no-cache tests/unit/optimisation tests/unit/dispatcher tests/unit/norms tests/unit/upload` (the task's named paths) plus `tests/unit/optimisation-proposals tests/unit/projects tests/unit/screens tests/unit/api` and the guards `rendered-language`, `prepared-sections`, `presentation-language`, `gender-agreement`, `dashboard-invalidation`, `lazy-boundary` | 0 (55 files, 870 tests) |

The extra paths are the suites that already exercised these hooks or the shared classifier
(`optimisation-proposals/commands.test.ts` runs `useStartOptimisationPass`;
`projects/upload-failure.test.ts` is the document upload's classifier suite) and the guards
that read source or render screens.

The tests were written after the code. Red is shown by the mutations below; a red run on the
base tree was not made (checking out the base `web/src` is the kind of action the session's
permission classifier refused in the previous slice, so I did not attempt it).

## Mutation probes

One reversible in-place edit, the named test files run, the file restored; `git status --short`
was empty after each unless noted (the first runs of the double-press suites were taken before
their last commit). Every row is red.

Start pass (`start-pass-double-press` + the existing `optimisation-proposals/commands`):

- N1 never join (`if (false)`) → 2 red («sends ONE request…», «gives both presses the same
  refusal…»); an earlier version of the refusal case hung to a 120 s timeout under this
  mutation, so each refusal case now asserts one `POST` before it fails the request.
- N2 join any intent in flight → 1 red («does not join a request for another document set»).
- N3 never reopen the gate → 3 red, one of them the existing «reuses the key on a retry of
  the same set and mints another once the pass is stored».
- N4 drop the document from the intent → 1 red.

Create assignment (`assignment-double-press`):

- N5 never join → 3 red. N6 join any → 1 red («does not join … another expert, scope or
  note»). N7 never reopen → 1 red. N8 do not trim the note → 1 red («counts a note that
  differs only by surrounding spaces as the same intent»). N9 drop the note from the intent →
  1 red («tells every field of the intent apart»).

Transition (`assignment-double-press`):

- N10 never join → 3 red. N11 join any → 2 red. N12 never reopen → 1 red. N13 drop the kind →
  1 red. N14 do not trim the reason → 1 red. N15 drop the new assignee → 1 red.

Designate (`designation-double-press` + `designation-command`):

- N16 never join → 2 red. N17 join any → 1 red. N18 never reopen → 2 red («sends a new
  request for a press after the first settled», «reopens after a refusal»). N19 drop the
  believed current → 1 red. N20 drop the target → 2 red.

Price-list wording (`price-list-upload-failure` + the document upload's `projects/upload-failure`):

- P1 route only 502/503/504 to the classifier → 4 red (the 413 sentence, the transport note
  kept out, the end-to-end HTML 413 page, the rendered form).
- P2 route only 413 → 4 red (the three 5xx cases and «words each of the three differently»).
- P3 do not pass the limit → 3 red. P4 the label `20 MiB` → 4 red (including «says the price
  list's limit as the form states it», which compares it with `PRICE_LIST_MAX_BYTES`).
- P5 `retryable: true` → 2 red. P6 drop the correlation id → 1 red.
- P7 send everything to the classifier's reading → 5 red (the entity's constraint sentences
  stop reaching the user). P9 send everything to the entity (the pre-change behaviour) → 8 red.
- C1 the classifier ignores `limitLabel` → 4 red. C2 the classifier's default becomes `10 MiB`
  → 2 red, one of them the document upload's own «states the product limit from the envelope
  constant».
- P8 (the form calls the entity's `uploadFailureMessage` again) was first taken by deleting
  the import, which fails by a `ReferenceError`; P9 is the clean equivalent, and the form-level
  case «renders the web-server refusal under «Прайс-лист не загружен.»» is red under both.

Already in the tree, shown red by the existing `tests/unit/optimisation/commands.test.ts`:

- U1 drop the in-flight join of `useUploadPriceList` → 1 red («sends ONE request when the same
  intent is pressed twice…»). U2 drop the section-specification invalidation → 2 red. U3 and
  U4 swap the revisions and priced-specification invalidations → 1 red each.

## Decisions taken (nothing here was blocked on an owner decision)

1. **A single-slot gate per hook instance**, as in the three features that already have it:
   a press joins only the request in flight for the SAME intent, so A (in flight) then B is
   sent, and A pressed again while B is still in flight is sent as a new request. The guard
   exists for the double press of one button, not for serialising different actions.
2. **No shared helper.** `shared/**` is outside this task and the repository forbids a generic
   utility without proven semantics, so the join is written in each hook (now seven copies with
   `carry-over-decision`, `decide-optimisation-proposal` and `upload-price-list`). If the
   integrator wants one, `features/classify-version/model/single-flight.ts` is the nearest
   precedent and is not a join (it refuses the second press rather than sharing its answer).
3. **Joined presses share the promise**, so `onSuccess`/`onSettled` of both mutations run and
   `assignments.all()` or `norms.all()` is invalidated twice; harmless, and the same as the
   precedent.
4. **Only web-server answers go to the shared classifier.** Everything else about a failed
   price-list upload stays the entity's reading, because the classifier knows the document
   envelope's constraints and the entity knows the price list's. The result is mapped to the
   `FailureMessage` the form already renders (`kind: 'transport'`), so no screen changed shape.
5. `UploadFailureOptions` is a structural parameter and is not exported from
   `entities/document-version/index.ts`, which is outside the allowed paths.

## Contracts

None changed. New public symbols (feature `index.ts` files): `assignmentIntent`, `moveIntent`,
`designationIntent`, `SetCurrentSnapshotCommand`, `PRICE_LIST_LIMIT_LABEL`,
`priceListUploadFailure`.

## Risks and limits

- The guard is in the hook, so it holds for a double click delivered before the page
  re-renders. It was exercised through the hooks' configuration, not through a browser; the
  live journey that found the original double POSTs (`BETA-LIVE-JOURNEY-01`) was not run
  (`R-135`), and no live evidence is claimed.
- The 413 sentence names the product's limit and tells the user to ask the administrator; the
  limit the host really enforces is not known to the browser.
- `D-195` can be closed for these four features and the price-list wording; the `D-184`
  clause about the price-list upload not invalidating the section view is already false (see
  above). `DEBT_REGISTER.md` is outside this task, so neither row was edited.

## Instruction for the integrator

Merge `agent/lane-c-01` as a real merge; light acceptance per `AGENTS.md` §8 and the task:
`git diff --check`, the named test files, `tests/contract` with the gate's own three ignores.
The five test files above are the evidence for the two debt rows.

## Forbidden hotspots

`git diff --name-only ff0b3ae2..HEAD` before this report lists only
`web/src/features/{create-assignment,set-current-snapshot,start-optimisation-pass,transition-assignment,upload-price-list}`,
`web/src/entities/document-version/model/upload-failure.ts` and
`web/tests/unit/{dispatcher,norms,optimisation,upload}`; this report is the only file added
under `docs/program/`. No `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`,
`web/package*.json`, `web/FRONTEND_LOCK.json`, `web/src/shared/**`, global stylesheet,
`web/src/_app/providers.tsx`, `tests/**` outside `web/tests/unit/**`, `DEBT_REGISTER.md`,
`CURRENT_STATE.md`, refs, tags or stand was touched.
