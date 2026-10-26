# AR-V3-BETA-PACK-STATUS-WEB-FIX-01 — four findings on the pack status panel and the six-check start

An independent judge read `AR-V3-BETA-PACK-STATUS-WEB-01` and reported four findings. Each was re-proved with a real run before it was fixed (task file, P-01 to P-04); all four reproduced. The task is web-only: no contract, backend, generated-client or shared-library change.

## Handoff

- Task: [AR-V3-BETA-PACK-STATUS-WEB-FIX-01](tasks/AR-V3-BETA-PACK-STATUS-WEB-FIX-01.md), frozen from `809d5c733a92e62a6979103c5771b546d1217c03` (the tip of `integration/ar-close-1026`).
- What changed, by finding:
  1. **Digest.** The installed panel no longer sets `title` on the digest. The markup carries `6d53674f688f…` and nothing more of it. The old test that pinned `title="<64 hex>"` is gone; the new test measures the longest run of the digest found anywhere in the panel's markup and in the whole settings screen, requires exactly twelve, and first proves its measure returns 64 for a digest in a `title` or a `data-` attribute (so the bound can fail).
  2. **Start in flight.** The run list now holds the idempotency key and a cache-derived "a start for this version is pending" flag (`useArV3GroupStartIntent`), draws the control while the pack is installed or a start is pending, and hands the key to the control, which sends exactly that key. A pending mutation keeps its observer, so the per-call `onSuccess` navigation still runs. The design choice against the brief's suggested lifted callback: the mutation cache already keeps a mutation until it settles, whether or not any component observes it, so the flag is read there (`useIsMutating` with the mutation's key and the version) and nothing has to report its own state upward. The control also disables its button while another mount's start for the same version is pending.
  3. **Identifiers.** `analysis_profile_id` and `prompt_bundle_id` are matched against the contract's patterns; a mismatch is the new fault reason `bad_identifier`, drawn as the contract fault. Fifteen malformed cases in the table (`"x"`, leading/trailing space, trailing newline, lower case, one character short or long, a letter Crockford omits, the other kind's prefix) and a test that the well-formed IDs are still read as given.
  4. **Retry key.** Live tests: a retry and a second press after failures send the same key as the first press; a changed version sends a different one. The control's own test now requires the key it was handed instead of `length > 8`.
- Changed files: `web/src/entities/audit-run/model/ar-v3-pack-status.ts`; `web/src/widgets/ar-v3-beta-pack/{ui/ar-v3-beta-pack.tsx, model/pack-presentation.ts}`; `web/src/features/start-ar-v3-group/{index.ts, model/use-start-ar-v3-group.ts, model/use-ar-v3-group-start-intent.ts (new), ui/start-ar-v3-group-control.tsx}`; `web/src/widgets/run-list/ui/run-list.tsx`; `web/tests/unit/analysis-settings/{ar-v3-beta-pack-status.test.ts, ar-v3-group-start-command.test.ts, run-list-ar-v3-live.test.ts (new), live-render.ts (new)}`; this note and the task file. `git diff --name-only 809d5c73..HEAD` lists nothing else.
- The new test instrument: `live-render.ts` mounts a tree with `react-dom/client` against a ~100-line hand-written node tree, so state, effects and a press run (the static harness cannot do any of the three). No dependency was added. A press calls the `onClick` the element carries; there is no layout, event path or focus. It sits under `analysis-settings` on purpose: a file under `tests/unit/screens/` that names the query provider is policed by the D-97 guard and must use `renderScreen`.
- Checks run in this tree:
  - `npm --prefix web run lint -- --quiet` → exit 0; `npm --prefix web run typecheck` → exit 0.
  - `npm --prefix web test -- --run tests/unit/analysis-settings tests/unit/screens tests/unit/styles tests/guards tests/unit/qa_w50` → 53 files, 868 tests passed (run before the commit on the same web sources; the final run on the committed tree is in the last line of this list).
  - Governance check of the task file prints `[]`.
  - `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` → 105 passed (the documentation prose guards that read the new files).
  - New tests: 8 stateful (`run-list-ar-v3-live.test.ts`), 3 added to the status test file (well-formed IDs read as given; the digest measure's self-check; the digest bound over the panel and the whole settings screen), plus 15 malformed-ID rows inside its existing fault table; one assertion in the control test changed.
- Guards shown red (the tree was restored after each; `git status` empty):

| Finding | Mutation | Red |
| --- | --- | --- |
| 1 | `<code>` → `<code title={pack.packSha256}>` | `installed: the 64-character digest is nowhere in the markup` (`expected '<section…' not to contain '6d53674f688f9eecd9c7cf3a0eaa391ca2baa…'`) |
| 1 | `PACK_DIGEST_SHOWN = 12` → `64` | 3 tests: the shortening test, the installed-panel test and the digest bound |
| 2 | `packInstalled \|\| startIntent.inFlight` → `packInstalled` (also the unfixed state, task P-02) | `keeps the control mounted and still opens the started group`, `draws nothing again once the request has settled…` (navigation list empty), `draws the control with its button disabled…` |
| 2 | `mutationKey: START_AR_V3_GROUP_MUTATION_KEY` removed from the mutation | the same three |
| 2 | `inFlight: pending > 0` → `inFlight: false` | the same three |
| 2 | `pending={mutation.isPending \|\| intent.inFlight}` → `pending={mutation.isPending}` | `draws the control with its button disabled, so the pending start is not sent twice` |
| 3 | the `bad_identifier` line removed (the unfixed state, task P-03) | `is a fault, never installed…` (`a profile id that is "x": expected 'installed' to be 'fault'`) |
| 3 | profile pattern `[0-9A-HJKMNP-TV-Z]` → `[0-9A-Z]` | same test, `a profile id with a letter Crockford omits` |
| 3 | bundle pattern loses its `$` | same test, `a bundle id with a trailing newline` |
| 4 | `useIntentKey(...)` → `newIdempotencyKey()` (fresh key per render) | `sends the SAME key when the control comes back…` and `is the same on a retry after a failure, and on a second press` |
| 4 | version dropped from the signature: `useIntentKey('start-ar-v3-group')` | `is a different one for a different version` (`expected 'ik_7711…' not to be 'ik_7711…'`) |
| 4 | the control mints `newIdempotencyKey()` per press instead of sending `intent.idempotencyKey` | three tests: both live key tests and `calls onStarted…` (`the control must send the key it was handed, not one of its own`) |
| instrument | `tick()` removed from `press` in `live-render.ts` | `is the same on a retry after a failure, and on a second press` (`expected +0 to be 1`: the retry button had not appeared) |

- Contracts: none changed. The shared contract stays at `1.5.0`; no generated file, error code, migration or dependency.
- Limits:
  - The pending flag reaches React one TanStack notification (a zero-delay timer) after the press. A pack re-read that fails inside that window can still take the control off the page; the key is held by the list, so the next press replays the same request, but that one start's navigation is lost.
  - The key lives as long as the run list. Leaving the version page and entering it again is a new intent with a new key; a request still pending is covered (the button is disabled), a request whose answer was lost and then re-entered is not.
  - A failure of a start that settles while the pack is unreadable is not shown, because the control is gone by then.
  - The stateful tests use a hand-written DOM, not a browser; no stand, pack or credentialed journey was available.
- Integration notes: merge after `AR-V3-BETA-PACK-STATUS-WEB-01`. `StartArV3GroupControl` now requires an `intent` prop; the run list is its only caller in the tree. Nothing to re-run on a database lane. On a stand with a reviewed pack, press «Запустить шесть проверок АР v3» and stop the status endpoint while the request is slow, to see the control stay and the group open.
- Forbidden hotspots (`contracts/**`, generated client, `web/FRONTEND_LOCK.json`, `web/package*.json`, global styles, composition root, `src/**`, `db/**`, `infra/**`, `Makefile`, `VERSION`, `release-notes/**`, `CURRENT_STATE.md`, `RELEASES.md`, `DEBT_REGISTER.md`, `web/src/shared/lib/**`, `web/tests/unit/styles/**`, `origin/main`, tags, deployment host) were untouched.
