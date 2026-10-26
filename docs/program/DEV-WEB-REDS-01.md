# DEV-WEB-REDS-01 — two vitest reds on the clean integration tip

Two frontend unit tests were red on `integration/ar-close-1026` (`0555a120`; full vitest: 2 failed, 2845 passed). Both were tests that had not caught up with `AR-V3-BETA-GROUP-REVIEW-SCREEN-01`, which put the group review panel on `/analysis-settings`. Neither was a product defect, and no `web/src` file changed.

## What changed

- `web/tests/unit/qa_w50/r66-navigation.test.ts`: the `/analysis-settings` case pinned "one read: the registry". It now asserts the full list of registered reads, each with its `enabled` flag, sorted by key so the list pins which reads exist and not the order the widgets mount in: the profile registry (enabled) and the group review under the empty address, **disabled** (no `group_id`, so it asks the server nothing). Two companion cases: with a valid `group_id` the review read is enabled for exactly that group; a malformed, lower-cased or repeated `group_id` makes the route answer not-found (`NEXT_HTTP_ERROR_FALLBACK;404`) and read nothing.
- `web/tests/unit/styles/screens.ts`: one census entry, `ArV3BetaReview six scopes loaded`, renders the panel with the six-scope answer seeded. `/analysis-settings` is derived, but with no `group_id` the panel draws only its lookup form, so `.member details` and `.quote` were reached by no screen. The entry adds six scopes in four states (available with a page quotation and a norm quotation, failed, verification refused, three pending). `UNREACHED_BY_ANY_SCREEN` is untouched.
- `web/tests/unit/analysis-settings/ar-v3-beta-review-fixtures.ts` (new): the group review fixture, moved out of `ar-v3-beta-review.test.ts` so the panel's test and the census share one; the test imports it.

## Verification (lane worktree `dev-web-reds-01`, node_modules symlinked read-only)

- `npm --prefix web test -- --run tests/unit/qa_w50/r66-navigation.test.ts tests/unit/styles tests/unit/analysis-settings`: **8 files, 104 passed** (both reds green; contrast file 20/20 in ~57 s).
- `npm --prefix web run lint -- --quiet`: exit 0. `npm --prefix web run typecheck`: exit 0.
- The three guards that read `screens()` (`screen-set`, `screen-claims-about-the-system`, `lazy-boundary`): **41 passed**.
- The census measures the new screen in both palettes: a probe over `census()` listed `ArV3BetaReview six scopes loaded` sites for ink on surface, the focus outline and the selection pair, in light and in dark. The whole vitest suite was not run (`R-135`; the integrator runs it).

## Mutations (each reverted; `git status` clean afterwards)

| Mutation | Red |
| --- | --- |
| remove `<ArV3BetaReview .../>` from `analysis-settings-page.tsx` | settings case and valid-group case: `expected [ { key: [ 'analysis', …(1) ], …(1) } ] to deeply equal [ { …(2) }, …(1) ]` |
| add a third `useQuery` to the same page | same two cases: `expected [ { …(2) }, { …(2) }, …(1) ] to deeply equal [ { …(2) }, …(1) ]` |
| `enabled: validGroupId !== null` becomes `enabled: true` in the widget | settings case: `expected [ { …(2) }, …(1) ] to deeply equal [ { …(2) }, …(1) ]` (the disabled flag differs) |
| delete the `notFound()` line in the route | malformed case: `"arg_bad": expected null to be 'NEXT_HTTP_ERROR_FALLBACK;404'` |
| delete the census seed (`setQueryData`) in `screens.ts` | `names every colour-bearing rule...`: unreached `[ '._member_7c8115 details', '._quote_7c8115' ]`, identical to the unfixed base |

## Known limitation, not repaired here

The widget's borders are `var(--am-border, currentColor)`, and `--am-border` is defined in no stylesheet (`grep -rn -e "--am-border\s*:" web/src` is empty), so the border resolves to the text colour and the census produces no border pair for `.panel`, `.member details` or `.quote`. The same spelling is in eight modules (`registration-queue`, `worker-list`, `analysis-profile-table`, `execution-queue`, `ar-v3-beta-status`, `project-optimisation`, `execution-journal`, this one). The R-33 floor therefore does not measure them. It needs a stylesheet change (a defined token), which is outside this task's paths; flagged for the integrator.

## Integration note

Merge after `DEV-CONTRACT-REDS-01`; re-run the whole vitest suite once on the merged tip. Test-only, so forward-revert is the rollback.
