# Task WEB-QUOTATION-RANGE-01 — the character range leaves the quotation caption

task_id: WEB-QUOTATION-RANGE-01
status: completed in development candidate

## Outcome

The review screen's quotation caption names the page only («стр. N»). The character range («символы a–b по всему документу, а не по странице N») appears exactly once per discrepancy: inside the existing span-mismatch alert, and nowhere when the anchor agrees with the quotation. This applies owner ruling `R-43` and closes the repair half of register row `D-50`.

## Depends on

- `W22-WEB` — completed; stated the document-global convention in the caption (`D-25`).
- `W30-CERT3` — completed; measured the offset drift that opened `D-50`.

## Frozen inputs

- domain contract: unchanged; `Evidence.page_number`, `char_start`, `char_end`, `quote` are read exactly as served.
- API contract: unchanged (`1.5.0`); product `0.8.0`; migration head `0032_ar_v3_run_group`.
- analysis/comparison/event contract: unchanged.
- migration head: `0032_ar_v3_run_group`.
- base commit: `1703d5bacacb1288fe7bdd7f99793705f1453406` (`integration/ar-close-1026`).
- owner ruling: `R-43` in `docs/program/OWNER_RULINGS_2026-09-17.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the ruled repair was never applied; the caption still prints the range unconditionally

### P-01 — the caption builder and its only render site

- captured_at: 2026-10-26
- command: `git grep -n -E 'anchorLabel|am-quotation__anchor' 1703d5bacacb1288fe7bdd7f99793705f1453406 -- web/src web/tests | sed 's/^1703d5bacacb1288fe7bdd7f99793705f1453406://'`
- captured_output:
  ```text
  web/src/app/globals.css:1951:.am-quotation__anchor {
  web/src/entities/finding-observation/index.ts:18:  anchorLabel,
  web/src/entities/finding-observation/model/quotation.ts:85:export function anchorLabel(evidence: Evidence): string {
  web/src/widgets/evidence-viewer/ui/evidence-viewer.tsx:35:  anchorLabel,
  web/src/widgets/evidence-viewer/ui/evidence-viewer.tsx:85:      <p className="am-quotation__anchor">{anchorLabel(item)}</p>
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:14: *   - `anchorMatchesQuotation` and `anchorLabel` from any constant — both are rendered by
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:31:  anchorLabel,
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:164:    expect(anchorLabel(REAL_CASE)).toBe(
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:171:    expect(anchorLabel(REAL_CASE)).toContain('по всему документу');
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:177:    expect(anchorLabel(REAL_CASE)).toContain('а не по странице 2');
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:179:    expect(anchorLabel(other)).toContain('а не по странице 11');
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:180:    expect(anchorLabel(other)).not.toContain('а не по странице 2');
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:188:    const label = anchorLabel(REAL_CASE);
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:194:    const label = anchorLabel(item({ quote: 'x', page_number: 11, char_start: 0, char_end: 1 }));
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:201:    const label = anchorLabel(item({ quote: 'x', page_number: 3, char_start: 40, char_end: 95 }));
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:207:    const label = anchorLabel(item({ quote: 'x', page_number: 3, char_start: 40, char_end: 95 }));
  web/tests/unit/review/quotation-anchor-and-pages.test.ts:214:    expect(anchorLabel(item({ quote: 'x', page_number: 1, char_start: 0, char_end: 0 }))).toContain(
  web/tests/unit/review/viewer-and-panels.test.ts:75:    expect(markup).toContain('am-quotation__anchor');
  web/tests/unit/review/viewer-and-panels.test.ts:92:   * The unit test on `anchorLabel` constrains the helper; this constrains the *rendered
  web/tests/unit/review/viewer-and-panels.test.ts:157:      expect({ activePage, anchor: markup.includes('am-quotation__anchor') })
  ```
- interpretation: one builder, one render site, and two test files that pin the rendered caption. `viewer-and-panels.test.ts` is not in the lane brief's grant; it asserts the caption text («стр. 7, символы 1200», the full «по всему документу» sentence) and therefore has to change with the caption. `index.ts` is the entity's public barrel and must export the new range builder, because the widget may not deep-import into `model/`. `globals.css` only declares the class and does not change.

### P-02 — the ruling text

- captured_at: 2026-10-26
- command: `sed -n 847,851p docs/program/OWNER_RULINGS_2026-09-17.md`
- captured_output:
  ```text
  ### `R-43` — the character range leaves the screen and stays in the data

  The review screen keeps **the quotation and the page number** — what an expert checks by eye and
  what `PA-01` criterion 5 tests, so **the criterion is untouched**. The offsets remain anchors
  inside the system and keep working at the binding seam.
  ```
- interpretation: the ruling keeps the page number on screen and removes the range; the `D-50` draft wording in `DEBT_REGISTER.md` additionally proposes dropping the whole caption when anchor and quotation agree. This task follows the lane brief («page-only caption»), which also keeps `.am-quotation__anchor` declared in `globals.css` in use; dropping the caption entirely would leave that rule dead and is a separate owner decision.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/entities/finding-observation/model/quotation.ts`
- `web/src/entities/finding-observation/index.ts`
- `web/src/widgets/evidence-viewer/ui/evidence-viewer.tsx`
- `web/tests/unit/review/quotation-anchor-and-pages.test.ts`
- `web/tests/unit/review/viewer-and-panels.test.ts`
- `web/tests/unit/review/evidence-viewer.test.ts`
- `docs/program/tasks/WEB-QUOTATION-RANGE-01.md`
- `docs/program/WEB-QUOTATION-RANGE-01.md`

## Forbidden hotspots

Contracts, `src/**`, `db/**`, `infra/**`, global styles (`web/src/app/globals.css`), root dependency/lock files, `web/FRONTEND_LOCK.json`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `RELEASES.md`, `release-notes/**`, `VERSION`, `origin/main`, tags and deployment host.

## Non-goals

- No change to the discrepancy logic (`anchorMatchesQuotation`) or to the alert's first two sentences.
- No new CSS class, no removal of `.am-quotation__anchor`, no change to `globals.css`.
- No conversion of the document-global offsets to page-local ones, no second extractor, no change to the offsets served or stored.
- No edit of the register row `D-50` or of the release notes; the integrator owns both.

## Deliverables

- `anchorLabel` returns «стр. N» only; new `anchorRangeLabel` returns «символы a–b по всему документу, а не по странице N» (the existing sentence split in two, same numbers, same en dash, same disclaimer), exported from the entity barrel.
- The evidence viewer renders the range only inside the span-mismatch alert: «…и здесь он не пересчитывается: символы a–b по всему документу, а не по странице N.» The full stop before the new clause became a colon; no other copy is new.
- `quotation-anchor-and-pages.test.ts` pins the page-only caption and the range label separately; `viewer-and-panels.test.ts` adds the agreeing-anchor case (no offsets anywhere in the markup) and the mismatch case (offsets inside the alert only, caption still page-only).
- The task file and the report.

## Required tests

- `npm --prefix web test -- --run tests/unit/review tests/guards/rendered-language.guard.test.ts tests/unit/styles tests/unit/screens tests/guards/lazy-boundary.guard.test.ts` — all pass (37 files, 686 tests).
- `npm --prefix web run lint -- --quiet` and `npm --prefix web run typecheck` — exit 0.
- Governance check of this file prints `[]`.
- Mutation evidence is in the report: each new assertion goes red under a quoted change.

## Integration contract

The review screen shows «стр. N» under each quotation. When `char_end - char_start` differs from the quotation's code-point length, the alert under that quotation additionally states the range with its convention; otherwise no character offset appears in the rendered output. The offsets in the API, the database and the binding seam are untouched. Companion actions for the integrator: register row `D-50` (repair applied), and a release note.

## Failure/idempotency/security cases

- A quotation with an agreeing anchor renders no offset, in any element or attribute.
- A quotation with a disagreeing anchor renders the offsets once, inside `role="alert"`, with the document-global disclaimer naming the same page.
- The quotation string itself is byte-identical (`data-evidence-quote`, `{item.quote}`); nothing here touches it.

## Rollback / feature flag

Forward-revert this task. No flag: a pure presentation change over unchanged data.

## Handoff

- changed files: entity helper and barrel, evidence viewer, two review test files, task and report
- commands/results: see `docs/program/WEB-QUOTATION-RANGE-01.md`
- known limits: the `D-50` draft's stronger variant (no caption at all when the anchor agrees) is not applied; no browser journey was run (R-135)
- integration notes: merge with the next web candidate; add the release note from the report; mark `D-50` repaired in the register
