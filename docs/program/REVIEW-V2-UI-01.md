# REVIEW-V2-UI-01 — the reviewer sees and uses the v2 finding fields

Task: `docs/program/tasks/REVIEW-V2-UI-01.md`. Branch `agent/lane-c-01`, base `d38f9c54`.
Web only; no contract, migration, dependency or global style changed.

## Result

On a finding that carries the v2 fields the review screen now:

- shows the **proposed severity** as the model's («Предложение модели»), next to a **severity
  select** for the accept action; the select starts empty, the proposal is never copied into
  it, and an accept with nothing chosen is **refused in the browser** with a sentence
  («Перед принятием выберите важность. Ничего не отправлено.»), not defaulted and not sent;
- sends `severity` on the accept request **only when the observation has a proposed
  severity**, and only the severity the expert chose; a reject never sends one;
- shows the **decided severity** from the server's projection beside the verdict, in the
  decision panel and in the finding list row;
- shows, under the page and quotation panes, the **required and stated values**, the **norm
  citations** (designation, title, clause, page, verified/rebound, text source, link to the
  norm at that page) and the **merged observations** (text, proposed severity as the model's,
  pages, quotations).

A finding without those fields renders and behaves as before. Verified, not argued: before
the change I rendered `FindingList` (two findings), `DecisionPanel` (pending, accepted and
pending-intent, comment-refused) and `EvidenceViewer` (no document and with document) over
legacy fixtures and saved the markup; after the change the same render is **byte-identical**
(`cmp` reported identical). That capture was a throw-away test, removed, not committed.

## Changed files

Source (all under the allowed paths):

- `web/src/features/record-verdict/model/verdict-request.ts` (new): `buildVerdictRequest`,
  `VERDICT_REFUSALS`, `verdictRefusalMessage`. Pure.
- `web/src/features/record-verdict/model/use-record-verdict.ts`, `index.ts`: `record(intent,
  observationId, severity?)`, `refusal` as state (a `useState`, filed under the finding it
  was raised for, cleared by the next sent press and by `reset`).
- `web/src/entities/expert-decision/model/intent.ts`: `intentSignature` includes the severity
  when the request has one; a request without one keeps the signature it always had.
- `web/src/entities/finding/ui/severity-badge.tsx` (new), `model/citation-labels.ts` (new),
  `index.ts`: `SeverityBadge` (five tones, Russian label, contract value on `data-severity`
  only, a fault badge for a value outside the closed set), Russian words for the citation
  states.
- `web/src/widgets/decision-panel/ui/decision-panel.tsx`, `ui/decision-panel.module.css`,
  `model/severity-draft.ts` (new): the select, the proposal line, the decided severity, the
  refusal; the pick is kept with its observation id so it cannot follow the reviewer to the
  next finding (the panel instance survives a change of selection).
- `web/src/widgets/finding-list/ui/finding-list.tsx`, `ui/finding-list.module.css`: decided
  severity badge in the row, wrapped with the verdict badge only when present.
- `web/src/widgets/evidence-viewer/ui/finding-basis.tsx`, `ui/finding-basis.module.css` (new),
  `ui/evidence-viewer.tsx`: the basis block and the `mergedObservations` prop.
- `web/src/_pages/review/ui/review-page.tsx`: passes `merged_observations`,
  `proposed_severity`, `decided_severity`, the verdict feature's refusal, and the accept
  closure `record('accept', id, { proposed, decided })`; reject passes no severity.

Tests (new, under `web/tests/unit/**` as allowed):

- `web/tests/unit/decisions/verdict-severity.test.ts` (23): the request shape with and
  without a proposed severity, for all five severities, refusals, reject, the intent
  signature and the idempotency key across a retry and a changed severity, the hook through
  its configuration.
- `web/tests/unit/review/v2-finding-fields.test.ts` (50): labels for all five severities,
  badge tones, the select present only with a proposal, not preselected, the decided severity
  in panel and list, refusal rendering for every refusal, the three states of
  `norm_citations`, values, merged observations, Cyrillic-only visible text, no raw enum
  value as a word, and the review screen over a seeded cache.
- `web/tests/unit/review/decision-panel-handlers.test.ts` (12): the panel called as a
  function with indexed state cells, the select's `onChange` and the buttons' `onClick`
  called: the pick is handed up, not the proposal; a stale pick is not handed up for another
  observation; reject hands up none.
- `web/tests/unit/review/review-page-wiring.test.ts` (5): the real screen with the panel and
  the verdict hook stood in by recorders: what `record` receives on accept and reject, and
  what the panel is given.

## Checks (worktree `.local/worktrees/lane-c`, tip of the code commits `751decc6`)

All redirected to files, exit status read from `$?`, run one at a time under `nice -n 10`
through the read-only `web/node_modules` symlink.

| command | exit |
|---|---|
| `git diff --check` | 0 |
| `npm --prefix web run typecheck` | 0 |
| `npm --prefix web run lint -- --quiet` | 0 |
| `npm --prefix web test -- --run --no-cache tests/unit/review tests/unit/decisions tests/unit/run tests/unit/widgets tests/unit/entities tests/guards/rendered-language.guard.test.ts tests/guards/prepared-sections.guard.test.ts tests/unit/styles tests/guards/presentation-language.guard.test.ts tests/guards/gender-agreement.guard.test.ts tests/guards/dashboard-invalidation.guard.test.ts tests/guards/lazy-boundary.guard.test.ts` | 0 (42 files, 598 tests) |

`tests/unit/styles` and the four extra guards are beyond the two named in the task; they were
run because this slice adds module CSS and source that those read.

## Mutation probes

Each row: one reversible in-place edit of the file, the named test files run, the file
restored from the committed copy and `git diff --stat` shown empty (apart from tests not yet
committed at that moment). Every row went red where "red" is stated. The tests were written
after the implementation, so "failing first" is shown by these mutations, not by a red run on
the base tree (a checkout of the base `web/src` for a red-on-base run was refused by the
session's permission classifier and not retried).

`verdict-request.ts`, test `verdict-severity`:

- M1 drop `|| input.proposedSeverity === undefined` → 3 red («carries no severity key at all
  on an accept», «does not send a stray choice», hook «sends the legacy request»).
- M2 drop `input.intent === 'reject' ||` → 2 red («a reject never carries a severity», hook
  «never sends a severity on a reject»).
- M3 `severity: decided` → `severity: input.proposedSeverity` → 6 red.
- M4 `decided = decidedSeverity ?? proposedSeverity` → 4 red («refuses an accept with no
  choice, and does not fall back to the proposal» and three hook cases).
- M5 drop the closed-set check → 1 red («refuses a choice outside the contract's closed set»).
- M6 message → English → 1 red («names each reason in Cyrillic with no Latin word»).

`use-record-verdict.ts`:

- M7 drop `setRefused(null)` on a sent press → red «clears the refusal when the next press
  goes out».
- M8 drop the finding check on `refusal` → red «keeps that refusal on the finding it was
  raised for».
- M9 file the refusal but still send → 3 red.
- M10 pass `proposed` as `decided` → 4 red.
- M48 drop `setRefused(null)` in `reset` → red «forgets the refusal when the reviewer
  dismisses it».

`intent.ts`:

- M11 drop the severity part → 3 red (signature differs, key minted per severity, key on the
  wire).
- M12 always append `severity:` → red «keeps the signature of a request without a severity
  exactly what it was».

`decision-panel.tsx` / `severity-draft.ts`:

- M13 show the select without a proposal → 3 red.
- M14 preselect the proposal (`value={chosen ?? proposedSeverity ?? ''}`) → 2 red.
- M15 drop the decided severity line → 6 red.
- M16 drop the refusal paragraph → 1 red.
- M17 `onAccept(observationId, proposedSeverity)` → 9 red.
- M18 drop `disabled={busy}` on the select → 1 red.
- M19 `chosenSeverity` ignores the observation id → 3 red.
- M20 `draftFromControl` accepts any value → 3 red.

`finding-list.tsx`, `severity-badge.tsx`:

- M21 always the two-badge branch → 1 red. M22 show the proposal instead of the decided
  severity → red after adding «shows the decided severity and not the proposed one when the
  two differ» (it had survived before that case existed).
- M23, M23b, M23c change the tone of critical, economic, operational → red «gives each
  severity its own tone» (survived before that case existed).
- M24 drop the closed-set fault badge → 1 red. M25 print the contract value instead of the
  label → 15 red.

`finding-basis.tsx`, `evidence-viewer.tsx`, `citation-labels.ts`:

- M26 drop the whole-block guard → 3 red. M27 `&&`→`||` in the values guard → 1 red.
- M28 treat an empty citation list as absent → 1 red. M29 never take the empty branch → 1 red.
- M31 one tone for rebound and verified → red after the tone assertion was added.
- M32 link without the page → 1 red. M33 mark every observation canonical → 2 red.
- M34 drop the empty-merged guard → red after «shows no merged block at all…» was added.
- M35 show a severity badge for an observation without a proposal → red after the
  «Предложение модели»/fault assertions were added.
- M36 quotations unordered → 1 red. M37, M37b a Latin state label → 2 red each (it had
  survived while the test compared the label with its own constant). M38 unknown state
  printed raw → 1 red.
- M39 viewer drops `mergedObservations` → 4 red. M40 viewer drops the basis → 12 red.

`review-page.tsx`:

- M41 drop `proposedSeverity` → 2 red. M42 drop `decidedSeverity` → 1 red. M43 drop
  `severityRefusal` → 1 red. M44 accept without `decided` → 1 red. M45 `proposed: undefined`
  → 2 red. M46 reject passes a severity → 1 red. M47 drop `mergedObservations` → 1 red.

One equivalent mutant, not killed and not killable: M30 prints `<span>{clause}</span>` for a
null clause, which renders an empty span, identical on screen to rendering nothing.

## Decisions taken (no owner decision was blocking; defaults named here)

1. **The select starts empty and an accept without a choice is refused.** The task's failure
   case says an accept of a finding with a proposal "is not sent without a decided severity";
   copying the model's proposal into the choice would make the model's output the expert's
   decision (`AGENTS.md` §4). The expert may of course choose the same value.
2. **Refusal over disabling.** The Accept button stays enabled and a press says why nothing
   was sent, the way the comment refusal does; a disabled button would hide the reason.
3. **Absent, empty and listed norm citations are three states.** Absent shows nothing (never
   «0»); an empty array says «Проверка нормативных ссылок выполнена: подтверждённых ссылок у
   этой находки нет.»; a listed array is itemised. This follows the contract's own text.
4. **Merged observations are shown as served, the canonical one marked «основное» rather than
   dropped**; the contract does not say whether the list includes it. No producer of
   `merged_observations` exists in `src/` yet (only the schema and the export reader), so
   this block is exercised by tests only.
5. **Rebound** is shown as «перепривязана» in the active tone, verified as «подтверждена» in
   the ok tone; the tooltip repeats the contract's meaning.
6. **Module CSS carries layout only.** The contrast census (`tests/unit/styles`) requires
   every colour-bearing rule to be reached by a screen in `tests/unit/styles/screens.ts`,
   which is outside this task's allowed paths; ink, tint and borders therefore come from
   global rules the markup already meets (`label`, `select`, `dl`, `.am-note`,
   `.am-decision__current`, `.am-decision__note`, `.am-badge*`). The census is green. A
   screen that renders a v2 finding would let a later slice give these blocks their own
   colour; that file is the integrator's to extend.
7. The select's element id is `decision-severity`, not `am-…`: `styling-layer.test.ts` reads
   every `am-` token in a `.tsx` as a class that must be declared.

## Contracts

None added or changed. `AppendDecisionRequest.severity`, `Finding.decided_severity`,
`merged_observations`, `norm_citations`, `required_value`, `stated_value` and
`FindingObservation.proposed_severity` are read from the generated client as they are.

## Risks and known limitations (found, not fixed: outside the allowed paths or the outcome)

- **Decision history and the knowledge base still show a verdict without its severity.**
  `web/src/widgets/decision-history/ui/decision-history.tsx` (around lines 125–128, the
  `am-history__verdict` span) and `web/src/widgets/knowledge-base/ui/knowledge-base.tsx` print
  `VERDICT_LABELS[event.verdict]` only, although `DecisionEvent.severity` is served. Neither
  path is allowed here; they need a slice that owns those widgets (the new `SeverityBadge`
  and `SEVERITY_LABELS` are exported from `@/entities/finding`).
- **Existing defects seen on the way, untouched:** (a) `review-page.tsx` computes
  `pendingIntent` as `'accept'` whenever the verdict mutation is pending, so a pending reject
  reads «Принимаю…»; (b) the same page prefers `verdict.result?.current_verdict` over the
  finding's own, and the hook lives at page level, so after a decision on finding A another
  finding can show A's verdict until the detail refetches; (c) `useAppendComment` keeps its
  refusal in a ref, which does not re-render, so an empty comment's refusal may not appear
  until something else renders (suspected from the code, not exercised;
  `web/src/features/append-comment` is outside this task).
- The refusal sentence stays on screen after the expert has picked a severity, until the next
  press clears it.
- Not exercised: a real browser (the select's events are exercised by calling the handlers in
  the element tree, not by a DOM), the live journey, a real v2 finding from the API, the
  contrast of the new markup with real v2 data (see decision 6). No claim of live or field
  evidence is made.
- One run, my first, was started without `--no-cache` and so updated vitest's result cache
  `web/node_modules/.vite/vitest/<hash>/results.json` in the gate worktree's `node_modules`
  through the symlink (a timing/failed-first ordering cache of spec paths, mtime 01:58:29 on
  2026-10-22; it also holds an entry for a throw-away spec that no longer exists). Every later
  run used `--no-cache`, and the file's mtime did not change again.

## Instruction for the integrator

Merge `agent/lane-c-01` as a real merge; light acceptance per `AGENTS.md` §8 and the task:
`git diff --check`, the four new test files, `tests/contract` with the gate's own three
ignores. The decision-history and knowledge-base widgets and `tests/unit/styles/screens.ts`
(a screen that renders a v2 finding) are the follow-ups named above.

## Forbidden hotspots

`git diff --name-only d38f9c54..HEAD` for the code and test commits lists only files under
`web/src/{_pages/review,entities/expert-decision,entities/finding,features/record-verdict,widgets/decision-panel,widgets/evidence-viewer,widgets/finding-list}`
and `web/tests/unit/{decisions,review}`; this report and nothing else is added under
`docs/program/`. No `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`,
`web/package*.json`, `web/FRONTEND_LOCK.json`, `web/src/shared/**`, global stylesheet,
`web/src/_app/providers.tsx`, `tests/**` outside `web/tests/unit/**`, refs, tags or stand was
touched.
