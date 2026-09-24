/**
 * `/blocks` — page-level block markup, prepared and not built.
 *
 * `R-23`'s addendum (`OWNER_RULINGS_2026-09-17.md` §3.11) rules blocks wanted and the
 * front-end preparation allowed now, under the rule it made general: **the front end
 * carries the structure before the back end does, with honest stubs.**
 *
 * The promise below is bounded by what `docs/program/W43-PREP.md` note 1 measured, and
 * every clause of it is checkable:
 *
 *   - the application DOES compute block rectangles — `page_geometry_extraction` writes
 *     `bbox {x0, y0, x1, y1}` in points, one per text line — so the screen does not say
 *     the geometry is missing, because that would be false;
 *   - **no operation returns them.** The only block-shaped field on the 18-operation
 *     surface is `Evidence.block_id`, which the contract itself calls *"Secondary anchor
 *     into this version's block index. Not a contract identifier."* So the promise says
 *     what is actually in the way: a reseal, not a missing measurement;
 *   - the vector graph legacy drew has no source at all. `polygon_points` is `null` on
 *     every one of the corpus's blocks, so the promise does not mention it.
 *
 * No count, no total and no sample row: `R-23`'s fourth rule is that an empty screen is
 * more honest than a plausible one.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function BlocksPage() {
  return (
    <RoutePlaceholder
      screen="Блоки"
      route="/blocks"
      promise="Здесь будет разметка блоков страницы: какие фрагменты документа анализ считает блоками и где каждый из них находится. Границы блоков приложение уже вычисляет во время прогона, но наружу их не отдаёт ни одна операция договора, поэтому показывать пока нечего."
    />
  );
}
