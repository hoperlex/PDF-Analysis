# WEB-QUOTATION-RANGE-01 — the character range leaves the quotation caption

Owner ruling `R-43` (register row `D-50`) said the document-global character range of a quotation must leave the screen and appear only where it is evidence of a discrepancy. It was never applied: `anchorLabel` still returned «стр. N, символы a–b по всему документу, а не по странице N» and the evidence viewer printed it under every quotation.

Now `anchorLabel` returns «стр. N» only, and a new `anchorRangeLabel` returns the other half of the same sentence, «символы a–b по всему документу, а не по странице N», unchanged in numbers, en dash and disclaimer. The evidence viewer prints the range only inside the existing span-mismatch alert, after its two existing sentences: «Заявленная длина фрагмента не совпадает с цитатой. Якорь показан так, как его прислал сервер, и здесь он не пересчитывается: символы 1200–1300 по всему документу, а не по странице 7.» The only text not already on screen is the punctuation joining the two parts: a colon replaces the full stop before the range, and a full stop ends it. The discrepancy logic, the `<p className="am-quotation__anchor">` element and its stylesheet rule are untouched, so no global style changed.

## Release note (Russian, one sentence)

Под каждой цитатой на экране проверки теперь указана только страница («стр. N»); диапазон символов «по всему документу» показывается лишь в предупреждении о несовпадении длины фрагмента с цитатой.

## Verification

- `npm --prefix web test -- --run tests/unit/review tests/guards/rendered-language.guard.test.ts tests/unit/styles tests/unit/screens tests/guards/lazy-boundary.guard.test.ts`: **37 files, 686 tests passed** (before the change `tests/unit/review` plus the rendered-language guard: 16 files, 274 tests passed). `tests/unit/styles` (`styling-layer`, `contrast`) and `tests/unit/screens` read the evidence viewer's classes and stay green.
- `npm --prefix web run lint -- --quiet`: exit 0. `npm --prefix web run typecheck`: exit 0.
- Governance check of `docs/program/tasks/WEB-QUOTATION-RANGE-01.md`: `[]`.
- Mutations (each applied, run on `tests/unit/review/viewer-and-panels.test.ts` and `tests/unit/review/quotation-anchor-and-pages.test.ts` (58 tests), seen red, reverted):

  | mutation | result |
  |---|---|
  | `anchorLabel` returns `` `стр. ${page}, ${anchorRangeLabel(e)}` `` (range back in the caption) | 7 failed: `is exactly the page`, `carries neither end of the character range`, `uses the server page number unchanged`, `names the page beside the quotation, and only the page`, `names a different page for a different item`, `prints no character range anywhere when the anchor agrees`, `states the declared range inside the alert, and only inside it` |
  | viewer alert drops `{anchorRangeLabel(item)}` (`…пересчитывается.`) | 3 failed (alert range tests) |
  | viewer caption renders `{anchorLabel(item)}, {anchorRangeLabel(item)}` | 4 failed (page-only caption, no-range-when-agreeing, range-only-inside-alert) |
  | `anchorRangeLabel` loses the «по всему документу, а не по странице N» clause and prints `char_end + 1` | 10 failed (pinned string, convention, denial, off-by-one, alert wording) |

## Deviations and decisions

- Two paths beyond the lane brief's grant were added to the task file with reasons: `web/tests/unit/review/viewer-and-panels.test.ts` (it asserted the old rendered caption, «стр. 7, символы 1200», in four tests) and `web/src/entities/finding-observation/index.ts` (the barrel must export `anchorRangeLabel`; the widget may not deep-import `model/`). `globals.css` was read but not touched.
- The `D-50` entry in `DEBT_REGISTER.md` quotes a draft that goes further than the lane brief: no caption at all when anchor and quotation agree, since the page repeats the heading «Цитаты на странице N». This lane keeps the page-only caption as briefed. Removing the `<p>` would leave `.am-quotation__anchor` in `globals.css` without a user and needs the global-styles owner. If the integrator wants the stronger variant, it is a follow-up task; the new tests already pin that no offset appears when the anchor agrees.
- Not run: any browser journey or live check (R-135 forbids the full battery). The rendering claim rests on `renderToStaticMarkup` assertions over the real component.

## Integration note

Merge with the next web candidate; no contract, migration, dependency or style change. After merge the integrator owns: the release note above in `release-notes/`, and marking register row `D-50` repaired (its check command is a second-extractor comparison, which this change does not alter: the offsets are still stored and served).
