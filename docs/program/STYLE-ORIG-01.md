# Task STYLE-ORIG-01 — the product wears the original's visual key, and the sign-in screen is variant B

Programme record, owner-approved on 2026-11-19 (`R-157a`…`R-157g`, `OWNER_RULINGS` §3.58). The analysis behind it, with four
sign-in variants, is `.local/reports/signin-contrast-2026-11-18/` (git-ignored).

## Outcome

Open any screen in both themes and see PDF-proverka's key (the original's tints, the Onest typeface, its shapes and plaque sizes)
with its quiet text darkened to AA. The sign-in screen is variant B. Layout, words and behaviour do not change.

## Depends on

- `UI-PARITY-R3` (closed 2026-11-17; the pool is on `origin/dev`).

## Frozen inputs

- base commit: `origin/dev` `e4c108bd2` (`VERSION` 0.31.1, contract 1.59.0, migration head 0071).
- no contract, migration or dependency change is in this programme.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

`origin/main` is outside this task (`R-157g`); it waits for the owner's separate word and is not touched during a live run.

## Allowed paths

The task owns the web style layer as one slot, in the order below; one lane owns `web/src/app/globals.css` at a time.

- `web/src/app/globals.css`
- `web/public/fonts/**`
- `web/src/_app/**`
- `web/src/_pages/sign-in/**`
- `web/src/shared/ui/**`
- `web/src/**/*.module.css`
- `web/tests/unit/styles/**`
- `web/tests/unit/session/sign-in-screen.test.ts`
- `web/tests/unit/shell/navigation-fit.test.ts`
- `web/tests/unit/dashboard/dense-overview.test.ts`
- `web/tests/unit/review/v2-finding-fields.test.ts`
- `release-notes/0.32.0.json`
- `release-notes/dictionary.json`
- `VERSION`
- `tests/contract/release_notes/test_release_notes_form.py`
- `tests/integration/releases/test_release_loader.py`
- `docs/program/STYLE-ORIG-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/OWNER_RULINGS_2026-09-17.md`

A change to `*.module.css` outside the slice a lane was dispatched for needs the integrator's word.

## Forbidden hotspots

- `contracts/**`, migrations, root dependency and lock files, `web/package.json`;
- the composition root (`web/src/app/layout.tsx` is read only; the theme boot script stays as it is);
- `web/src/app/**` other than `globals.css`;
- every file under `src/` (backend).

## Non-goals

- no rename, no new screen, no move of an element (`Г3`…`Г13` of 2026-11-16 stand);
- no change of the avatar palette rule (hash of `user_uid`) or of the section-colour list; their values may move only to keep
  their own existing contrast guards green;
- «Администрирование» is not fitted to the original (owner, 2026-11-16).

## Deliverables

1. `STYLE-ORIG-S1` palette: the three token blocks (light, dark media, dark attribute) in the original's tints; the dark theme is
   near-black (`R-157d`); radii and shadows of the original; the showcase tokens folded into the shared palette.
2. `STYLE-ORIG-S2` typeface: Onest (OFL) and the original's mono face self-hosted in `web/public/fonts`, `--am-font`, the original's
   size ladder, plaques at 9–10 px (`R-157e`); every re-measured vertical centring (`centre-caps-with-text-box`).
3. `STYLE-ORIG-S3` shell and blocks: a flat 214 px side panel, flat top strip, a teal line across the window, square group markers
   and teal icons in the menu (`R-157d`); buttons, fields, cards, rows and plaques as the original draws them; the literal radii
   and shadows that bypass tokens move to tokens.
4. `STYLE-ORIG-S4` sign-in screen B (`R-157c`).
5. `STYLE-ORIG-S5` guards: `contrast.test.ts` and its pending list follow `R-157b`; pinned colours, the section and avatar palettes,
   the theme guard and the size floors follow `R-157a`/`R-157e`.
6. Two previews in `.local/reports/style-orig/` (`R-157f`) and the 0.32.0 note.

## Required tests

Focused only, per `AGENTS.md` §8 and the owner's 2026-11-10 rule; no `make gate` without the owner's order.

- `npx tsc --noEmit -p web`, `eslint` on changed files, `npx next build` before publication;
- `npx vitest run tests/unit/styles` (once per block, the shared test lock is the bottleneck), plus the unit files of every screen a lane
  changed (`tests/unit/session/sign-in-screen.test.ts` for S4);
- `pytest tests/contract/release_notes`.

## Integration contract

- Consumers read tokens only; no module gains a colour literal or a custom property (`styling-layer`).
- The guest frame is the one `AppFrame` of every screen; nothing here forks it.
- `--am-font`, `--am-radius*`, `--am-shadow*` and `--am-text-*` keep their names; values change.

## Failure/idempotency/security cases

- A browser that asks for reduced motion sees the resting scene, and the sign-in slice ships no client script (`C-22`).
- The theme boot script and the stored theme choice are untouched.
- Text meets AA in both themes; a control's boundary meets 3:1 (`R-157b`).

## Rollback / feature flag

Not applicable: styles are values and rules, and a revert of the integration merge restores the previous look. No flag.

## Handoff

Kept in `.local/handoff/style-orig-2026-11-19.md` by the integrator (branch `integration/style-orig`, lanes, previews, checks).

## Result (2026-11-19, integrator pdf-analysis-aa)

Branch `integration/style-orig`, published to `origin/dev` only (`R-157g`, `R-157h`).

- S1–S4 as listed above. Three tokens were added for the sign-in drawing (`--am-card-edge`, `--am-sheet-edge`, `--am-grid-dot`), plus `--am-panel` and
  `--am-text-2xs`. The showcase tokens were NOT folded into the shared palette: their values now equal the root ones, the frame's remap keeps only the
  control boundary, and the fold is a later cleanup.
- S5: `contrast.ts` answers an edge with 3:1 only for a control (`R-157b`); 24 modules moved their controls' borders to `--am-line-strong`; 52 pending rows
  left the list (one stays); `--am-ok` is `#0c7830`; `navigation-fit` was re-measured in Onest. Three guard files outside the first path list were
  edited (`navigation-fit`, `dense-overview`, `v2-finding-fields`) because they pinned the old values; they are listed above now.
- Checks: `vitest` on `tests/unit/styles`, `tests/unit/shell`, `tests/unit/dashboard`, the sign-in screen, `executor-density-n2`, `sheet-chips` and
  `v2-finding-fields`: 38 files, 655 tests, all green; `tsc --noEmit` clean; `eslint` on the changed test files clean; `next build` exit 0;
  `pytest tests/contract/release_notes` 30/30. Static renders of 10 census screens in AppFrame at 1440, 1100 and 390 px in both themes: no horizontal overflow.
- Not run: `make gate`, the whole web unit battery, the 186-shot sweep (reduced to 60 shots above), `tests/integration/releases/test_release_loader.py` (needs a
  database; its version-set pin was moved by hand).
- Debt: the owner's OK on the previews P1 and P2 (`R-157f` lifted by `R-157h`); `.local/reports/style-orig/`. A rejected look is a revert of the integration merge.
