/**
 * What the contrast census measured on 2026-11-02 and the product does not yet satisfy.
 *
 * `contrast.test.ts` did not finish in 900 s on this tree, so for the whole of the design
 * wave (2026-10-29..30, `DESIGN-M01` .. `DESIGN-LOGIN-ORBIT-1030`) nothing measured R-33 or
 * AA: `DESIGN-M10-ACCEPTANCE` records "stopped after a long wait with no result" and no
 * design task lists the file among its checks. It runs in about 25 s now (the census index
 * in `contrast.ts`), it measures the palette that renders inside the application frame
 * (`scopedPalettes`, `framed`), it reads `:global()` rules (`scopeModuleCss`), and it is red.
 *
 * NOTHING BELOW IS A VERDICT THAT THE PAIR IS FINE. Every row is a measured failure, kept
 * visible and held by a ratchet instead of deleted from the assertion:
 *
 *   - a pair that still fails and is not listed fails `contrast.test.ts` as before;
 *   - a listed pair that now passes (or is no longer produced) fails it, until its row is
 *     deleted -- the list can lose rows by repair and gain none without editing the ceiling
 *     in that file;
 *   - a listed pair may not get WORSE than `floor`, the ratio recorded here (rounded down).
 *
 * The decision behind all but one row is the owner's, not the executor's: which palette the
 * product keeps (the `--am-showcase-*` values as the base tokens, or the base values back),
 * how the line scale spreads so that significant borders hold 3:1, and whether a translucent
 * border may remain on decoration that is `aria-hidden`. That is step 3 of
 * `ui-frontend-review-2026-11-02.md`; the arithmetic is `S7-design-01` / `S7-design-02` of
 * the 2026-11-02 code review. The one defect found by the first complete run (`<a class="am-button">` lost its label on
 * hover, 1:1) was repaired in `globals.css` the same day and has no row.
 *
 * Keyed by PAIR, as the census is: a new site of a listed pair is covered by its row. The
 * `sites` of each pair are in the failure message of `contrast.test.ts` when a row is removed.
 */

import type { Theme } from './contrast';

/** When the rows were measured. A row older than the decision that settles it is stale by definition. */
export const PENDING_SINCE = '2026-11-02';

/** The decision every palette row waits for. */
export const PENDING_DECISION =
  'Owner decision pending: one palette for the application frame and the line scale (step 3 of ' +
  'ui-frontend-review-2026-11-02.md; S7-design-01 and S7-design-02 of the 2026-11-02 code review).';

export type PendingCause =
  | 'translucent-border'
  | 'translucent-guide'
  | 'line-near-miss'
  | 'soft-ink-on-tint'
  | 'loading-shimmer';

export const PENDING_CAUSES: Readonly<Record<PendingCause, string>> = {
  'translucent-border':
    'A border drawn as color-mix(in srgb, <line or accent token> N%, transparent), N between 14 and 52, ' +
    'on the shell, the sign-in form, the update notice and several cards: the visible line is the token ' +
    'faded into its surface, 1.2 to 2.2:1, under the R-33 floor of 3:1. Repair is a solid token, which is ' +
    'the line-scale decision; alpha may stay only on aria-hidden decoration, which needs the owner to say so.',
  'translucent-guide':
    'The tree guide of the navigation (`.am-disclosure__item::before`), drawn as the line token at 38%: ' +
    '1.6 to 1.7:1 as a graphic. Same decision as the translucent borders; it is aria-hidden decoration if the owner ' +
    'rules that decoration is exempt.',
  'line-near-miss':
    '--am-showcase-line on --am-showcase-accent-soft in the dark palette is 2.995:1, five thousandths under ' +
    '3:1, on the border of every control that sits on the accent tint. A one-step move of the line value ' +
    'in the dark palette clears it; which step is the palette choice.',
  'soft-ink-on-tint':
    '--am-showcase-soft text on --am-showcase-accent-soft in the light palette is 4.34:1 against AA 4.5:1 ' +
    '(the guest preview paragraph in the sidebar, seven sites). The base tokens measured 4.68 before ' +
    'the remap; S7-design-02 suggests darkening --am-showcase-soft to about #4a666b.',
  'loading-shimmer':
    'The moving highlight of the loading skeleton (`.am-state__loading-lines > span::after`), accent tint on ' +
    'the sunken card, 1.1:1. It is decoration of a state that says "Загрузка…" in text; the owner decides ' +
    'whether decoration is exempt from the 1.4.11 graphic floor.',
};

export interface PendingPair {
  /** The census key: kind|foreground|background|state|pseudo. */
  readonly key: string;
  /** The palettes in which it fails. A failure in a palette not named here is not covered. */
  readonly themes: readonly Theme[];
  /** The ratio measured on `PENDING_SINCE`, rounded down; the pair may not fall below it. */
  readonly floor: Readonly<Partial<Record<Theme, number>>>;
  readonly cause: PendingCause;
}

export const PENDING_PAIRS: readonly PendingPair[] = [
  { key: 'edge|--am-showcase-accent@28%|--am-showcase-bg|-|border', themes: ['light', 'dark'], floor: { light: 1.52, dark: 2.00 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-accent@28%|--am-showcase-bg|focus-visible|border', themes: ['light', 'dark'], floor: { light: 1.52, dark: 2.00 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-accent@28%|--am-showcase-bg|hover|border', themes: ['light', 'dark'], floor: { light: 1.52, dark: 2.00 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-accent@28%|--am-showcase-card|-|border-color', themes: ['light', 'dark'], floor: { light: 1.54, dark: 2.05 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-accent@28%|--am-showcase-card|focus-visible|border-color', themes: ['light', 'dark'], floor: { light: 1.54, dark: 2.05 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-accent@28%|--am-showcase-card|hover|border-color', themes: ['light', 'dark'], floor: { light: 1.54, dark: 2.05 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@24%|--am-showcase-card|-|border-top', themes: ['light', 'dark'], floor: { light: 1.31, dark: 1.36 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@25%|--am-showcase-card|-|border-bottom', themes: ['light', 'dark'], floor: { light: 1.32, dark: 1.39 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-bg|-|border', themes: ['light', 'dark'], floor: { light: 1.39, dark: 1.48 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-bg|-|border-bottom', themes: ['light', 'dark'], floor: { light: 1.39, dark: 1.48 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-bg|-|border-color', themes: ['light', 'dark'], floor: { light: 1.39, dark: 1.48 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-bg|focus-visible|border', themes: ['light', 'dark'], floor: { light: 1.39, dark: 1.48 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-bg|hover|border', themes: ['light', 'dark'], floor: { light: 1.39, dark: 1.48 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-card|-|border', themes: ['light', 'dark'], floor: { light: 1.41, dark: 1.49 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-card|focus-visible|border', themes: ['light', 'dark'], floor: { light: 1.41, dark: 1.49 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@30%|--am-showcase-card|hover|border', themes: ['light', 'dark'], floor: { light: 1.41, dark: 1.49 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@32%|--am-showcase-card|-|border-left', themes: ['light', 'dark'], floor: { light: 1.45, dark: 1.54 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@34%|--am-showcase-card|-|border', themes: ['light', 'dark'], floor: { light: 1.48, dark: 1.58 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@35%|--am-showcase-bg|-|border', themes: ['light', 'dark'], floor: { light: 1.46, dark: 1.61 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@36%|--am-showcase-card|-|border-top', themes: ['light', 'dark'], floor: { light: 1.52, dark: 1.63 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line@40%|--am-showcase-card-alt|-|border', themes: ['light', 'dark'], floor: { light: 1.54, dark: 1.65 }, cause: 'translucent-border' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|-|border', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|-|border-bottom', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|-|border-color', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|active|border-color', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|disabled|border-color', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|focus-visible|border', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'edge|--am-showcase-line|--am-showcase-accent-soft|focus-visible|border-color', themes: ['dark'], floor: { dark: 2.99 }, cause: 'line-near-miss' },
  { key: 'graphic|--am-showcase-accent-soft|--am-showcase-card-alt|-|after', themes: ['light', 'dark'], floor: { light: 1.10, dark: 1.15 }, cause: 'loading-shimmer' },
  { key: 'text|--am-showcase-soft|--am-showcase-accent-soft|-|-', themes: ['light'], floor: { light: 4.33 }, cause: 'soft-ink-on-tint' },
];

/**
 * A colour-bearing rule no census screen reaches, so no pair it makes is measured except the
 * one a single rule declares in one block (`declaredPairs`).
 *
 * The first full run of `contrast.test.ts` since the design wave found 86 of them, in 23
 * stylesheets. They are NOT read and NOT judged: each is a rule whose element no seeded
 * screen renders (a missing seed), or a rule nobody needs, and from the census' side the two
 * look alike (`UNREACHED_BY_ANY_SCREEN` in the test says why a list is read rather than
 * counted). The honest state is "unmeasured", and this list keeps it visible: a rule that a
 * screen now reaches must be deleted from here (the test names it), and a new unreached rule
 * is not covered by it. `origin` is the stylesheet, `selector` the rule as authored (a
 * module's classes unhashed).
 */
export interface PendingUnreached {
  readonly origin: string;
  readonly selector: string;
}

export const PENDING_UNREACHED: readonly PendingUnreached[] = [
  { origin: 'globals.css', selector: '.am-app__nav' },
  { origin: 'web/src/_app/app-frame.module.css', selector: '.am-app[data-sidebar=\'compact\'] .guestPreviewGroup' },
  { origin: 'web/src/_app/app-frame.module.css', selector: '.contextGroup, .contextDivider' },
  { origin: 'web/src/_app/app-frame.module.css', selector: '.end .am-theme__option[aria-pressed=\'true\']' },
  { origin: 'web/src/_app/app-frame.module.css', selector: '.railTooltip' },
  { origin: 'web/src/_pages/account/ui/account-page.module.css', selector: '.profile' },
  { origin: 'web/src/_pages/queue/ui/queue-page.module.css', selector: '.intent' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-compare-page.module.css', selector: '.projectChooser' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-upload-panel.module.css', selector: '.card' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-upload-panel.module.css', selector: '.form, .batch, .card' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-workspace.module.css', selector: '.panel' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-workspace.module.css', selector: '.selection, .tabs' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-workspace.module.css', selector: '.tabs [role=\'tab\']' },
  { origin: 'web/src/_pages/stage-compare/ui/stage-workspace.module.css', selector: '.tabs [role=\'tab\'][aria-selected=\'true\']' },
  { origin: 'web/src/widgets/assignment-board/ui/assignment-board.module.css', selector: '.table tbody tr:hover' },
  { origin: 'web/src/widgets/assignment-board/ui/assignment-board.module.css', selector: '.table th' },
  { origin: 'web/src/widgets/assignment-board/ui/assignment-board.module.css', selector: '.tableWrap' },
  { origin: 'web/src/widgets/dashboard/ui/sections-panel.module.css', selector: '.selection' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.adviceDetails' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.batchList > li' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.coverageGrid > section' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.digest > div' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.observations > li' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.panel pre' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.procedures > li' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.sourceInspector' },
  { origin: 'web/src/widgets/extended-review/ui/extended-review.module.css', selector: '.summary' },
  { origin: 'web/src/widgets/stage-changes/ui/stage-changes.module.css', selector: '.card' },
  { origin: 'web/src/widgets/stage-changes/ui/stage-changes.module.css', selector: '.sides section' },
  { origin: 'web/src/widgets/stage-changes/ui/stage-changes.module.css', selector: '.viewControls input, .viewControls select' },
  { origin: 'web/src/widgets/stage-changes/ui/stage-changes.module.css', selector: '.warning, .note' },
  { origin: 'web/src/widgets/stage-changes/ui/stage-journal.module.css', selector: '.table th, .table td' },
  { origin: 'web/src/widgets/stage-pair-catalog/ui/stage-pair-catalog.module.css', selector: '.decision' },
  { origin: 'web/src/widgets/stage-pair-catalog/ui/stage-pair-catalog.module.css', selector: '.row, .decision' },
  { origin: 'web/src/widgets/stage-run-controls/ui/stage-run-controls.module.css', selector: '.batch' },
  { origin: 'web/src/widgets/stage-run-controls/ui/stage-run-controls.module.css', selector: '.estimate' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-pair-viewer.module.css', selector: '.pane' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-pair-viewer.module.css', selector: '.pane [data-evidence^="focus:"]' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-pair-viewer.module.css', selector: '.pane [data-evidence^="mask:"]' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-pair-viewer.module.css', selector: '.pane [data-evidence^="search:"]' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-sheet-map.module.css', selector: '.focusNotice' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-sheet-map.module.css', selector: '.pane, .row, .preview' },
  { origin: 'web/src/widgets/stage-sheet-map/ui/stage-sheet-map.module.css', selector: '.row[data-stage-focused-row="true"]' },
  { origin: 'web/src/widgets/stage-text-evidence/ui/stage-text-evidence.module.css', selector: '.panel' },
  { origin: 'web/src/widgets/stage-text-evidence/ui/stage-text-evidence.module.css', selector: '.stale' },
  { origin: 'web/src/widgets/stage-text-evidence/ui/stage-text-evidence.module.css', selector: '.table th, .table td' },
  { origin: 'web/src/widgets/stage-v3-experimental/ui/global-consolidation.module.css', selector: '.panel' },
  { origin: 'web/src/widgets/stage-v3-experimental/ui/global-consolidation.module.css', selector: '.panel pre' },
  { origin: 'web/src/widgets/version-comparison/ui/version-comparison.module.css', selector: '.hunks' },
];
