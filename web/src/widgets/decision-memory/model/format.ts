/**
 * Plain-text forms of the geometry and the digests the memory keeps (`D-495`). The memory returns a crop as a description, not as
 * bytes (the byte path is phase M3), so what a reader gets is words and numbers.
 */

/** `[x0, y0, x1, y1]` with the digits that carry meaning: three decimals, trailing zeros dropped. */
export function formatBox(box: readonly number[]): string {
  return `[${box.map((value) => String(Number(value.toFixed(3)))).join('; ')}]`;
}

/** The head of a digest: enough to tell two apart, with the whole digest in the tooltip. */
export function shortDigest(digest: string, length = 12): string {
  return digest.length <= length ? digest : `${digest.slice(0, length)}…`;
}

/** A byte count as kilobytes, never below one: «12 КБ». */
export function sizeLabel(bytes: number): string {
  return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
}
