# WEB-BORDER-TOKEN-01 — borders drawn in the text colour

Eight widget stylesheets wrote twelve border declarations as `var(--am-border, currentColor)`. No stylesheet defines `--am-border`, so each resolved to its fallback, the element's text colour: a near-black card edge on the light theme, a near-white one on the dark theme, instead of the quiet border levels `globals.css` defines. The fallback is what hid it. The contrast census did not catch it either: it reads `currentColor` as the element's ink, which clears 3:1 on any surface.

Each declaration now reads the defined token for what the border is, with no fallback (`git diff` shows twelve one-token changes and nothing else):

| Level | Used for |
| --- | --- |
| `--am-line` | outer card or panel edge: registration-queue `.item`, execution-queue `.row`, worker-list `.row`, execution-journal `.row`, ar-v3-beta-status `.panel`, ar-v3-beta-review `.panel` |
| `--am-line-soft` | separator or box inside a card: ar-v3-beta-status `.group` top rule, ar-v3-beta-review `.member details` box and `.quote` left rule |
| `--am-line-strong` | a control's own boundary: ar-v3-beta-review `.lookup input` (the level the global text-input rule uses for the same element) |
| `--am-grid-line` | a table rule: analysis-profile-table `.cell`, project-optimisation `.cell` (the level the global `tbody td` rule uses) |

The lane brief named only the line and line-soft levels. The last two rows follow the `globals.css` header comment ("a control's own boundary", "a table rule") and the global rules for the same elements; they are the one judgement in this task and are easy to flip.

## The guard

`web/tests/unit/styles/tokens-defined.test.ts` scans every `web/src/**/*.css`, `*.tsx` and `*.ts` for `var(--am-*)` and requires each token to be defined in `globals.css`. It names each undefined read with file and line, asserts the scan is not vacuous (more than 40 tokens defined and read, more than 10 collocated modules reading them), ignores comments, and treats a fallback as no excuse. Its pure functions are exercised on a deliberately broken fixture and on the real tree.

The scan found a second undefined token. `web/src/entities/document-version/ui/classification-history.module.css:9` reads `var(--am-gap-md)`; the scale is `--am-gap-xs`, `--am-gap-sm`, `--am-gap`, `--am-gap-lg`, `--am-gap-xl`. The declaration is invalid at computed-value time, so that history list renders with no gap. The file is outside this task's paths and the right step (`--am-gap-sm` or `--am-gap`) is a layout choice, so it is recorded in a commented `KNOWN_UNDEFINED` list. That list is a ratchet in both directions: repairing the file, or defining the token, fails the test until the entry is deleted.

## Verification

- `npm --prefix web test -- --run tests/unit/styles tests/unit/analysis-settings tests/unit/qa_w50`: 12 files, **195 passed** (baseline before the change, `tests/unit/styles` alone: 5 files, 65 passed; the guard adds 6).
- `npm --prefix web run lint -- --quiet`: exit 0. `npm --prefix web run typecheck`: exit 0.
- Census of the new pairs (a throwaway probe over `census()` and `declaredPairs()`, deleted before commit), both palettes, every pair at or above the 3:1 border floor: `--am-line` on paper 4.77 light / 4.34 dark, on surface 4.41 / 4.80; `--am-line-soft` on paper 3.62 / 3.31, on surface 3.35 / 3.66; `--am-grid-line` on surface 3.68 / 3.99; `--am-line-strong` on paper 5.87 / 5.29, on surface 5.43 / 5.86. The lowest new pair is `--am-line-soft` on paper in the dark palette, 3.31. No pair failed, so the floor and `globals.css` are untouched.
- `screens.ts` unchanged: the census already renders every rule of the eight stylesheets (`names every colour-bearing rule that NO rendered screen reaches` stayed green with an unchanged excused list).
- Governance of this task file: `[]`.
- Mutation 1: `var(--am-line)` replaced by `var(--am-border, currentColor)` in `worker-list.module.css`. `tokens-defined.test.ts` went red: `web/src/widgets/worker-list/ui/worker-list.module.css:18 reads var(--am-border)`; reverted, green.
- Mutation 2: the style-file filter changed from `.css` to `.cssx` so the scan finds nothing. The non-emptiness test went red (`no token reference was found at all: expected 0 to be greater than 40`) and so did the ratchet; reverted.
- Mutation 3: `KNOWN_UNDEFINED` entry renamed to `--am-gap-xx`. The unknown-token test and the ratchet both went red; reverted.

## Integration note

Presentation only: eight screens change border colour in both palettes. No markup, contract, token or copy change, and nothing to re-run on a database lane. A later owner of `web/src/entities/document-version/**` fixes `--am-gap-md` and deletes the `KNOWN_UNDEFINED` entry.
