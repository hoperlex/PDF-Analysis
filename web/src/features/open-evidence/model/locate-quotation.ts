/**
 * Where a quotation sits on a rendered page: a pure function of the page's text items.
 *
 * The server's extractor and pdf.js read the same page and do not read it identically. The
 * two disagree about where one text item ends and the next begins, about how much space
 * sits between words, and about which spaces exist at all (a justified line is one run of
 * glyphs to one extractor and a dozen items to the other). A literal `indexOf` of the
 * quotation in `items.map(str).join(' ')` therefore fails on exactly the pages a reviewer
 * most wants a frame on. So the match is made on text with every whitespace and invisible
 * separator REMOVED from both sides, and each surviving character remembers the item and
 * the character offset it came from. That is what maps a match back to geometry.
 *
 * What this does not do, and says so: it does not guess. A quotation that is absent from
 * the page's text layer is reported as absent (`not-found`, or `no-text-layer` when the page
 * has no characters at all, which is what a scanned sheet looks like) and the viewer says
 * so beside the quotation. There is no fuzzy fallback, no edit distance and no "closest
 * line": the quotation is the load-bearing evidence, and a frame drawn around text the
 * server did not quote would be a claim nobody made. Nothing here reads, trims or rewrites
 * the quotation for display either; it only folds a COPY for comparison.
 *
 * A quotation that occurs more than once on the page is reported at every occurrence, in
 * reading order of the text layer. The contract carries `char_start`/`char_end` of the
 * document-global prepared text layer (`entities/finding-observation/model/pages.ts`), which
 * this layer cannot map to a page, so choosing one occurrence would be a silent guess.
 *
 * Geometry is a proportion: a partly covered item is cut at the character fraction of its
 * advance width. That is exact for monospaced runs and a few percent out for proportional
 * ones, which is inside the padding of the frame. pdf.js text items carry no per-glyph
 * advances, so this is the finest honest resolution available without re-measuring fonts.
 */

/** The part of a pdf.js `TextItem` this module reads. A structural subset, so no import. */
export interface TextRun {
  readonly str: string;
  /** Text-space to user-space matrix, `[a, b, c, d, e, f]`. */
  readonly transform: readonly number[];
  /** Advance width of the whole item, in user-space units. */
  readonly width: number;
  readonly height: number;
}

/**
 * A rectangle in the units of the viewport it was computed for, origin at the page's top-left
 * corner. The viewer asks for a viewport at scale 1, so these are PDF points; the server's
 * line geometry (`BlockGeometry.bbox`) is in the same unit and the same orientation.
 */
export interface Rect {
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

/** The characters `[start, end)` of `items[item].str` (UTF-16 offsets) that a match covers. */
export interface QuotationSpan {
  readonly item: number;
  readonly start: number;
  readonly end: number;
}

export interface QuotationMatch {
  /** One span per item the match touches, in item order. */
  readonly spans: readonly QuotationSpan[];
}

interface Origin {
  readonly item: number;
  readonly start: number;
  readonly end: number;
}

/** A page's text with whitespace removed, and where each remaining unit came from. */
export interface FoldedPage {
  readonly text: string;
  /** `origin[k]` is the source of `text[k]`; the two have the same length. */
  readonly origin: readonly Origin[];
}

/** Whitespace of every kind plus the zero-width and soft-hyphen characters extractors drop. */
const IGNORABLE = /^[\s\u00AD\u200B-\u200D\u2060\uFEFF]$/u;

/**
 * One source cluster (a character with its combining marks), folded for comparison:
 * compatibility-normalised (so `ﬁ` meets `fi`, `№` meets `No`, and a decomposed `й` meets
 * the precomposed one, as pdf.js itself normalises its text) with the ignorable characters
 * removed. May return the empty string, or more than one unit.
 */
function foldCluster(cluster: string): string {
  let folded = '';
  for (const unit of cluster.normalize('NFKC')) {
    if (!IGNORABLE.test(unit)) folded += unit;
  }
  return folded;
}

/** A base character with the combining marks that follow it, or a run of stray marks. */
const CLUSTER = /\P{M}\p{M}*|\p{M}+/gu;

/** The comparison form of a quotation. */
export function foldQuotation(quote: string): string {
  let folded = '';
  for (const cluster of quote.matchAll(CLUSTER)) folded += foldCluster(cluster[0]);
  return folded;
}

/** Fold a page's text items once; every quotation on the page is then located in the result. */
export function foldPageText(items: readonly Pick<TextRun, 'str'>[]): FoldedPage {
  let text = '';
  const origin: Origin[] = [];
  items.forEach((run, item) => {
    for (const cluster of run.str.matchAll(CLUSTER)) {
      const start = cluster.index;
      const end = start + cluster[0].length;
      const folded = foldCluster(cluster[0]);
      for (let unit = 0; unit < folded.length; unit += 1) {
        origin.push({ item, start, end });
      }
      text += folded;
    }
  });
  return { text, origin };
}

function matchAt(page: FoldedPage, at: number, length: number): QuotationMatch {
  const spans: { item: number; start: number; end: number }[] = [];
  for (let k = at; k < at + length; k += 1) {
    const source = page.origin[k] as Origin;
    const last = spans[spans.length - 1];
    if (last !== undefined && last.item === source.item) {
      last.start = Math.min(last.start, source.start);
      last.end = Math.max(last.end, source.end);
    } else {
      spans.push({ item: source.item, start: source.start, end: source.end });
    }
  }
  return { spans };
}

/**
 * Every occurrence of `quote` in the folded page, non-overlapping, in text-layer order.
 * Empty when the quotation has no characters of its own (nothing to look for is not a match).
 */
export function locateQuotation(page: FoldedPage, quote: string): readonly QuotationMatch[] {
  const needle = foldQuotation(quote);
  if (needle === '') return [];
  const found: QuotationMatch[] = [];
  let from = 0;
  for (;;) {
    const at = page.text.indexOf(needle, from);
    if (at === -1) break;
    found.push(matchAt(page, at, needle.length));
    from = at + needle.length;
  }
  return found;
}

// ------------------------------------------------------------------------ geometry

type Matrix = readonly number[];

/** `a × b` in pdf.js's row-vector convention (`Util.transform`). */
function multiply(a: Matrix, b: Matrix): readonly [number, number, number, number, number, number] {
  const [a0 = 0, a1 = 0, a2 = 0, a3 = 0, a4 = 0, a5 = 0] = a;
  const [b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0] = b;
  return [
    a0 * b0 + a2 * b1,
    a1 * b0 + a3 * b1,
    a0 * b2 + a2 * b3,
    a1 * b2 + a3 * b3,
    a0 * b4 + a2 * b5 + a4,
    a1 * b4 + a3 * b5 + a5,
  ];
}

/**
 * A proportional face does not advance by the same width for every character, so a cut made at a
 * character FRACTION of the item's advance can fall a fraction of a glyph away from the cut it
 * means (measured: the last «а» of a quotation sat just outside its box). Each side of a box that
 * is cut inside the item, not at its start or its end, is widened by this many characters, so the
 * glyph on the edge is inside the box. The box never leaves the item.
 */
export const CUT_BLEED = 0.5;

/** How far a glyph box reaches above and below the baseline, in em. Covers ascenders and descenders. */
const ASCENT_EM = 0.92;
const DESCENT_EM = 0.24;

/**
 * The box of `run.str[start, end)` in viewport pixels, or null when the item has no extent. A side
 * cut inside the item is widened by `CUT_BLEED` characters.
 *
 * Works in the viewport's own frame: the item's matrix is carried through the viewport
 * transform, so a page rotated by `/Rotate` or a rotated run comes out as the axis-aligned
 * box around the four corners of the rotated glyph box.
 */
export function spanRectangle(
  run: TextRun,
  start: number,
  end: number,
  viewportTransform: Matrix,
): Rect | null {
  const length = run.str.length;
  if (length === 0 || !(run.width > 0) || end <= start) return null;

  const scale = Math.hypot(viewportTransform[0] ?? 0, viewportTransform[1] ?? 0);
  const placed = multiply(viewportTransform, run.transform);
  const along = Math.hypot(placed[0], placed[1]);
  const up = Math.hypot(placed[2], placed[3]);
  if (!(scale > 0) || !(along > 0) || !(up > 0)) return null;

  const advance = run.width * scale;
  const unitAlong = { x: placed[0] / along, y: placed[1] / along };
  const unitUp = { x: placed[2] / up, y: placed[3] / up };

  const from = Math.max(0, start > 0 ? start - CUT_BLEED : 0) / length;
  const to = Math.min(length, end < length ? end + CUT_BLEED : length) / length;

  const xs: number[] = [];
  const ys: number[] = [];
  for (const s of [from, to]) {
    for (const t of [-DESCENT_EM, ASCENT_EM]) {
      xs.push(placed[4] + unitAlong.x * advance * s + unitUp.x * up * t);
      ys.push(placed[5] + unitAlong.y * advance * s + unitUp.y * up * t);
    }
  }
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  return { left, top, width: Math.max(...xs) - left, height: Math.max(...ys) - top };
}

/** The smallest rectangle containing all of `rects`, or null for none. */
export function unionRectangle(rects: readonly Rect[]): Rect | null {
  if (rects.length === 0) return null;
  let left = Number.POSITIVE_INFINITY;
  let top = Number.POSITIVE_INFINITY;
  let right = Number.NEGATIVE_INFINITY;
  let bottom = Number.NEGATIVE_INFINITY;
  for (const rect of rects) {
    left = Math.min(left, rect.left);
    top = Math.min(top, rect.top);
    right = Math.max(right, rect.left + rect.width);
    bottom = Math.max(bottom, rect.top + rect.height);
  }
  return { left, top, width: right - left, height: bottom - top };
}

// -------------------------------------------------------------------- the whole page

/** One occurrence of a quotation: a highlight per covered run of text. */
export interface LocatedOccurrence {
  readonly highlights: readonly Rect[];
}

export type QuotationStatus = 'found' | 'not-found' | 'no-text-layer';

export interface QuotationLocation {
  readonly ordinal: number;
  readonly status: QuotationStatus;
  readonly occurrences: readonly LocatedOccurrence[];
}

export interface QuotationQuery {
  readonly ordinal: number;
  readonly quote: string;
}

/**
 * Locate every quotation of one page.
 *
 * @param items             the page's text items, in the order pdf.js returned them
 * @param quotations        what to look for, with the caller's ordinal
 * @param viewportTransform `viewport.transform` of the viewport the rectangles are wanted in
 */
export function locateQuotations(
  items: readonly TextRun[],
  quotations: readonly QuotationQuery[],
  viewportTransform: Matrix,
): readonly QuotationLocation[] {
  const page = foldPageText(items);
  if (page.text === '') {
    return quotations.map(({ ordinal }) => ({ ordinal, status: 'no-text-layer', occurrences: [] }));
  }
  return quotations.map(({ ordinal, quote }) => {
    const occurrences: LocatedOccurrence[] = [];
    for (const match of locateQuotation(page, quote)) {
      const highlights: Rect[] = [];
      for (const span of match.spans) {
        const rect = spanRectangle(
          items[span.item] as TextRun,
          span.start,
          span.end,
          viewportTransform,
        );
        if (rect !== null) highlights.push(rect);
      }
      if (highlights.length > 0) occurrences.push({ highlights });
    }
    return { ordinal, status: occurrences.length > 0 ? 'found' : 'not-found', occurrences };
  });
}
