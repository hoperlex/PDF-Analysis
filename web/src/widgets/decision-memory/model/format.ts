/**
 * Plain-text forms of the geometry the memory keeps (`D-495`). The memory returns a crop as a description, not as
 * bytes (the byte path is phase M3), so what a reader gets is words and numbers.
 */

/** `[x0, y0, x1, y1]` with the digits that carry meaning: three decimals, trailing zeros dropped. */
export function formatBox(box: readonly number[]): string {
  return `[${box.map((value) => String(Number(value.toFixed(3)))).join('; ')}]`;
}

/** The unit and the origin a box is measured in, in words. The contract publishes `pt` and `top_left`; a value it adds is shown as sent. */
const BBOX_UNIT_WORDS: Readonly<Record<string, string>> = { pt: 'пт' };
const BBOX_ORIGIN_WORDS: Readonly<Record<string, string>> = { top_left: 'от левого верхнего угла' };

/** «пт, от левого верхнего угла»: how to read a box; empty when the block carried no geometry. */
export function boxFrameWords(unit: string | null, origin: string | null): string {
  return [
    unit === null ? null : (BBOX_UNIT_WORDS[unit] ?? unit),
    origin === null ? null : (BBOX_ORIGIN_WORDS[origin] ?? origin),
  ]
    .filter((part): part is string => part !== null)
    .join(', ');
}

/** A byte count as kilobytes, never below one: «12 КБ». */
export function sizeLabel(bytes: number): string {
  return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
}
