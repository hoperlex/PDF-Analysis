# Task WEB-BORDER-TOKEN-01 — eight screens drew their borders in the text colour

task_id: WEB-BORDER-TOKEN-01
status: completed in development candidate

## Outcome

Twelve border declarations in eight widget stylesheets read a token that no stylesheet defines, `--am-border`, behind a `currentColor` fallback, so each was drawn in the text colour. They now read the border token `globals.css` defines for what the border is, with no fallback, and a structural guard fails when any `var(--am-*)` in `web/src` names a token `globals.css` does not define.

## Depends on

- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01` — completed; its widget is one of the eight.
- `DEV-WEB-REDS-01` — completed; the style suite it left is the baseline this task measures against.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.4.0`, unchanged
- analysis/comparison/event contract: not_applicable
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `f80a6c76bbcd04f3ac306206e150d33453cff7d7` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: eight widget stylesheets read `--am-border`, which no stylesheet defines, so their borders resolve to the text colour; `globals.css` defines the border levels they should read

### P-01 — twelve border declarations in eight stylesheets read `--am-border`

- captured_at: 2026-10-26
- command: `git grep -n -e "--am-border" f80a6c76 -- web/src | sed 's/^f80a6c76://'`
- captured_output:
  ```text
  web/src/widgets/analysis-profile-table/ui/analysis-profile-table.module.css:16:  border-bottom: 1px solid var(--am-border, currentColor);
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css:6:  border: 1px solid var(--am-border, currentColor);
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css:32:  border: 1px solid var(--am-border, currentColor);
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css:53:  border: 1px solid var(--am-border, currentColor);
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css:65:  border-left: 2px solid var(--am-border, currentColor);
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.module.css:6:  border: 1px solid var(--am-border, currentColor);
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.module.css:21:  border-top: 1px solid var(--am-border, currentColor);
  web/src/widgets/execution-journal/ui/execution-journal.module.css:18:  border: 1px solid var(--am-border, currentColor);
  web/src/widgets/execution-queue/ui/execution-queue.module.css:18:  border: 1px solid var(--am-border, currentColor);
  web/src/widgets/project-optimisation/ui/project-optimisation.module.css:16:  border-bottom: 1px solid var(--am-border, currentColor);
  web/src/widgets/registration-queue/ui/registration-queue.module.css:3:.item { min-width: 0; border: 1px solid var(--am-border, currentColor); border-radius: 0.5rem; padding: 1rem; overflow-wrap: anywhere; }
  web/src/widgets/worker-list/ui/worker-list.module.css:18:  border: 1px solid var(--am-border, currentColor);
  ```
- interpretation: twelve declarations across the eight named stylesheets (four of them in `ar-v3-beta-review`, two in `ar-v3-beta-status`, one in each of the other six); no other file reads the token.

### P-02 — no stylesheet defines `--am-border`

- captured_at: 2026-10-26
- command: `git grep -n -E -e "--am-border\s*:" f80a6c76 -- web/src; echo "exit=$?"`
- captured_output:
  ```text
  exit=1
  ```
- interpretation: exit 1 is `git grep` finding no match, so the token is defined nowhere in `web/src`. Without a definition each `var(--am-border, currentColor)` resolves to its fallback, the element's text colour.

### P-03 — the tokens the borders should read are defined, in both palettes

- captured_at: 2026-10-26
- command: `git grep -n -E "^\s*--am-(line|line-soft|grid-line|line-strong):" f80a6c76 -- web/src/app/globals.css | sed 's/^f80a6c76://'`
- captured_output:
  ```text
  web/src/app/globals.css:145:  --am-line-soft: #818790;
  web/src/app/globals.css:147:  --am-line: #6e737b;
  web/src/app/globals.css:149:  --am-line-strong: #60656d;
  web/src/app/globals.css:151:  --am-grid-line: #7a8089;
  web/src/app/globals.css:334:    --am-line-soft: #616f80;
  web/src/app/globals.css:335:    --am-line: #748295;
  web/src/app/globals.css:336:    --am-line-strong: #8491a1;
  web/src/app/globals.css:337:    --am-grid-line: #667587;
  web/src/app/globals.css:405:  --am-line-soft: #616f80;
  web/src/app/globals.css:406:  --am-line: #748295;
  web/src/app/globals.css:407:  --am-line-strong: #8491a1;
  web/src/app/globals.css:408:  --am-grid-line: #667587;
  ```
- interpretation: lines 145-151 are the light palette, 334-337 the system-dark media block and 405-408 the explicit dark theme. The header comment of `globals.css` (lines 129-132) says what each level is: `--am-line-soft` the quiet separator inside a card, `--am-grid-line` a table rule, `--am-line` a card edge or row boundary, `--am-line-strong` a control's own boundary.

### P-04 — the full set of undefined tokens is two, not one

- captured_at: 2026-10-26
- command: `comm -23 <(git grep -h -o -E 'var\(\s*--am-[A-Za-z0-9_-]+' f80a6c76 -- web/src | sed -E 's/.*var\(\s*//' | sort -u) <(git grep -h -E '^\s*--am-[A-Za-z0-9_-]+\s*:' f80a6c76 -- web/src/app/globals.css | sed -E 's/^\s*//;s/\s*:.*$//' | sort -u)`
- captured_output:
  ```text
  --am-border
  --am-gap-md
  ```
- interpretation: besides `--am-border`, `web/src/entities/document-version/ui/classification-history.module.css:9` reads `var(--am-gap-md)`; the spacing scale is `--am-gap-xs`, `--am-gap-sm`, `--am-gap`, `--am-gap-lg`, `--am-gap-xl`. That file is outside this task's allowed paths and the right step is a layout choice, so the guard records it in a reasoned `KNOWN_UNDEFINED` list instead of changing it.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/registration-queue/ui/registration-queue.module.css`
- `web/src/widgets/execution-queue/ui/execution-queue.module.css`
- `web/src/widgets/worker-list/ui/worker-list.module.css`
- `web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.module.css`
- `web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css`
- `web/src/widgets/analysis-profile-table/ui/analysis-profile-table.module.css`
- `web/src/widgets/project-optimisation/ui/project-optimisation.module.css`
- `web/src/widgets/execution-journal/ui/execution-journal.module.css`
- `web/tests/unit/styles/tokens-defined.test.ts`
- `web/tests/unit/styles/screens.ts`
- `docs/program/tasks/WEB-BORDER-TOKEN-01.md`
- `docs/program/WEB-BORDER-TOKEN-01.md`

## Forbidden hotspots

`web/src/app/globals.css` and every other global style, every other `web/src/**` file, `contracts/**`, `src/**`, `db/**`, `infra/**`, root dependency/lock files, `web/FRONTEND_LOCK.json`, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, `RELEASES.md`, the migration head, the composition root, `origin/main`, tags and the deployment host.

## Non-goals

- No new token, no change to a token value and no change to the 3:1 border floor.
- No repair of `--am-gap-md` in `classification-history.module.css` (outside the allowed paths; recorded and reported).
- No change to any declaration other than the colour operand of the twelve border declarations.
- No new rendered screen: `screens.ts` is listed as an allowed path only for a border pair the census could not reach, and none was missing (see Deliverables).

## Deliverables

- The twelve declarations now read, with no fallback:
  - `--am-line` for an outer card or panel edge: `registration-queue` `.item`, `execution-queue` `.row`, `worker-list` `.row`, `execution-journal` `.row`, `ar-v3-beta-status` `.panel`, `ar-v3-beta-review` `.panel`.
  - `--am-line-soft` for a separator or a box inside a card: `ar-v3-beta-status` `.group` (top rule), `ar-v3-beta-review` `.member details` and `.quote` (left rule).
  - `--am-line-strong` for a control's own boundary: `ar-v3-beta-review` `.lookup input`, the same token the global `input[type='text']` rule uses for the same element.
  - `--am-grid-line` for a table rule: `analysis-profile-table` `.cell` and `project-optimisation` `.cell`, the token the global `tbody td` rule uses. The lane brief named only the line and line-soft levels; the table cells take the level `globals.css` names "a table rule", and the control takes the one it names "a control's own boundary".
- `web/tests/unit/styles/tokens-defined.test.ts`: every `var(--am-*)` in `web/src/**/*.css`, `*.tsx` and `*.ts` must be defined in `globals.css`; each undefined read is named with file and line; the scan is asserted non-empty; a fallback does not excuse an undefined token; a reasoned `KNOWN_UNDEFINED` list (one entry, `--am-gap-md`) is a ratchet in both directions.
- `screens.ts` unchanged: the census already renders all eight stylesheets' rules (`names every colour-bearing rule that NO rendered screen reaches` stayed green).
- Report `docs/program/WEB-BORDER-TOKEN-01.md`.

## Required tests

- `npm --prefix web test -- --run tests/unit/styles tests/unit/analysis-settings tests/unit/qa_w50` — expected: 12 files, 195 tests passed.
- `npm --prefix web run lint -- --quiet` and `npm --prefix web run typecheck` — expected: exit 0.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/WEB-BORDER-TOKEN-01.md',encoding='utf-8').read())))"` — expected: `[]`.
- Mutation: put `var(--am-border, currentColor)` back in `worker-list.module.css`; `tokens-defined.test.ts` goes red naming `web/src/widgets/worker-list/ui/worker-list.module.css:18 reads var(--am-border)`. Full `make gate` is deferred by `R-135`.

## Integration contract

Presentation only. The borders of eight screens change from the text colour to the border levels above in both palettes; no markup, behaviour, contract, token or copy changes. The integrator merges this lane with the other web lanes without ordering constraint, and may re-run the three commands above.

## Failure/idempotency/security cases

A new `var(--am-x)` with no definition, with or without a fallback, in a stylesheet or in a component string, fails `tokens-defined.test.ts` with its file and line. A scan that finds nothing fails the non-emptiness assertion. A `KNOWN_UNDEFINED` entry that is repaired, or that gains a definition, fails the ratchet until it is deleted. No security surface.

## Rollback / feature flag

Forward-revert. Not behaviour-changing beyond border colour; no feature flag.

## Handoff

- changed files: eight widget stylesheets, `tokens-defined.test.ts`, this task file and the report
- commands/results: see the report
- known limits: `--am-gap-md` in `classification-history.module.css` is still undefined, so that list renders with no gap
- integration notes: a follow-up owner of `web/src/entities/document-version/**` chooses between `--am-gap-sm` and `--am-gap` and then deletes the `KNOWN_UNDEFINED` entry
