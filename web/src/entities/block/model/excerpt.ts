/**
 * A short look at a recognised text, for a tile.
 *
 * A tile shows the beginning of what the portal read, not all of it: a block can hold pages of
 * text and a version holds hundreds of blocks. The full text, marked as recognised, is in the
 * block view. The cut is by code point (a letter outside the basic plane is one character) and
 * at the whitespace run before the limit when there is one, and the cut is shown with «…».
 * Nothing is rewritten: line breaks and runs of spaces become single spaces, which is how the
 * excerpt is laid out, and no other character changes.
 */

export const TILE_EXCERPT_LIMIT = 160;

export function textExcerpt(text: string, limit: number = TILE_EXCERPT_LIMIT): string {
  const flat = text.replace(/\s+/g, ' ').trim();
  const points = Array.from(flat);
  if (points.length <= limit) return flat;
  const head = points.slice(0, limit);
  const lastSpace = head.lastIndexOf(' ');
  // Cut at a word boundary when one is near the end; a single long token is cut where it stands.
  const cut = lastSpace >= limit * 0.6 ? head.slice(0, lastSpace) : head;
  return `${cut.join('').trimEnd()}…`;
}
