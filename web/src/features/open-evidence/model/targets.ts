/**
 * Where on a page a finding points: the authority order, and nothing else. Pure.
 *
 * A target (a quotation of a finding, or a source of the extended review) is placed by the
 * first of these that applies, and the outcome says which one it was:
 *
 *   1. LINES    the server's own line geometry (`VersionBlockIndex`): the lines of the declared
 *               page whose character range meets the quotation's. It is the only source that
 *               comes from the same extraction as the quotation, so it is the one trusted
 *               first. A partly quoted first or last line is framed whole: the index carries
 *               no per-glyph data, and a whole line is honest where a guessed fraction is not.
 *   2. REGION   a normalised rectangle the source itself carries (`bbox_norm`, portal image
 *               blocks). A native page carries the whole page, which marks nothing and is
 *               refused as a region.
 *   3. TEXT     the quotation searched in the page's text as pdf.js reads it, every exact
 *               occurrence (`locate-quotation.ts`).
 *   4. NOTHING  no frame. The status says so, and the card beside the page says «фрагмент не
 *               найден» or that the page has no text layer. There is no fuzzy match and no
 *               closest line: the quotation is the evidence, and a frame drawn around text
 *               nobody quoted is a claim nobody made.
 *
 * A rectangle that does not lie on the page is refused, not clipped into place: geometry from
 * another extraction, or for another page box, would otherwise be drawn on the wrong text with
 * every appearance of being right. The same refusal covers geometry that lies on the page but
 * not where the page's own text says the quotation is: the server measures from the media box
 * and pdf.js from the crop box, so a page whose crop box does not start at the origin would put
 * every server line a fixed distance from its text. When the page's text contains the quotation
 * and none of its occurrences meets the server's lines, the lines are not this page's, and the
 * text decides. When the text does not contain the quotation (a scan, a different reading of
 * the same glyphs) nothing contradicts the lines and they stand.
 *
 * The character range selects lines and is never shown (`R-43`, `D-50`); `block_id` is not read
 * at all.
 */

import type { Evidence, VersionBlockIndex } from '@/shared/api';

import type { QuotationStatus, Rect, TextRun } from './locate-quotation';
import { locateQuotations, unionRectangle } from './locate-quotation';
import type { Size } from './view-state';

/** `[x0, y0, x1, y1]`, each in [0, 1], origin at the page's top-left corner. */
export type Region = readonly [number, number, number, number];

export interface ViewerTarget {
  readonly id: string;
  /** What the badge on the frame says: the number the card beside the page carries. */
  readonly badge: string;
  /** Line rectangles in PDF points, page top-left origin (authority 1). */
  readonly rects?: readonly Rect[] | undefined;
  /** A normalised region (authority 2); `regionOf` is how a caller gets a valid one. */
  readonly region?: Region | undefined;
  /** The quotation to search in the page text (authority 3), and the frame's tooltip. */
  readonly quote?: string | undefined;
}

export type TargetMethod = 'lines' | 'region' | 'text';

export interface TargetResolution {
  readonly status: QuotationStatus;
  /** Which authority placed it; null when nothing did. */
  readonly method: TargetMethod | null;
  /** How many frames it has: more than one only for a text search that found the quotation again. */
  readonly occurrences: number;
}

/** One framed spot: the highlights inside it, and the box around them, in page points. */
export interface PlacedGroup {
  readonly highlights: readonly Rect[];
  readonly hull: Rect;
}

export interface Placement {
  readonly target: ViewerTarget;
  readonly resolution: TargetResolution;
  readonly groups: readonly PlacedGroup[];
}

/** A rectangle may overhang the page box by this many points before it is refused. */
export const OUT_OF_BOUNDS_TOLERANCE = 2;

/** A region this close to the whole page is the whole page: it points at nothing. */
const WHOLE_PAGE_EPSILON = 0.001;

// ------------------------------------------------------------------ authority 1: lines

/**
 * The rectangles of the lines a quotation sits on, or null when the index cannot say.
 *
 * Null for every reason there is no line to frame: no index, a version whose geometry has not
 * been produced, an anchor with no extent, no line of that page meeting the range, and a line
 * whose box is not a real box. The last is refused for the whole quotation rather than skipped
 * for the one line, because a frame around three of four lines is a statement about the text.
 */
export function lineRects(
  index: VersionBlockIndex | null | undefined,
  evidence: Pick<Evidence, 'page_number' | 'char_start' | 'char_end'>,
): readonly Rect[] | null {
  if (index === null || index === undefined || index.status !== 'produced') return null;
  if (!(evidence.char_end > evidence.char_start)) return null;

  const hits = index.blocks
    .filter(
      (block) =>
        block.page_number === evidence.page_number &&
        block.char_end > block.char_start &&
        block.char_start < evidence.char_end &&
        block.char_end > evidence.char_start,
    )
    .sort((left, right) => left.block_ordinal - right.block_ordinal);
  if (hits.length === 0) return null;

  const rects: Rect[] = [];
  for (const block of hits) {
    const { x0, y0, x1, y1 } = block.bbox;
    const real =
      block.bbox_unit === 'pt' &&
      block.bbox_origin === 'top_left' &&
      [x0, y0, x1, y1].every(Number.isFinite) &&
      x1 > x0 &&
      y1 > y0;
    if (!real) return null;
    rects.push({ left: x0, top: y0, width: x1 - x0, height: y1 - y0 });
  }
  return rects;
}

/** True when every rectangle lies on the page, give or take `OUT_OF_BOUNDS_TOLERANCE`. */
export function insidePage(rects: readonly Rect[], page: Size): boolean {
  const slack = OUT_OF_BOUNDS_TOLERANCE;
  return rects.every(
    (rect) =>
      [rect.left, rect.top, rect.width, rect.height].every(Number.isFinite) &&
      rect.width > 0 &&
      rect.height > 0 &&
      rect.left >= -slack &&
      rect.top >= -slack &&
      rect.left + rect.width <= page.width + slack &&
      rect.top + rect.height <= page.height + slack,
  );
}

// ----------------------------------------------------------------- authority 2: region

/**
 * A usable region, or null: exactly four finite numbers with `0 <= x0 < x1 <= 1` and
 * `0 <= y0 < y1 <= 1`, and not the whole page.
 *
 * The whole page is what a native page carries as its `bbox_norm`. Framing it would put a
 * frame round the edge of every such source and say nothing about where on the page the text
 * is, so it is treated as "no region" and the quotation is searched instead.
 */
export function regionOf(value: unknown): Region | null {
  if (!Array.isArray(value) || value.length !== 4) return null;
  if (!value.every((part) => typeof part === 'number' && Number.isFinite(part))) return null;
  const [x0, y0, x1, y1] = value as [number, number, number, number];
  if (!(x0 >= 0 && x0 < x1 && x1 <= 1 && y0 >= 0 && y0 < y1 && y1 <= 1)) return null;
  const whole =
    x0 <= WHOLE_PAGE_EPSILON &&
    y0 <= WHOLE_PAGE_EPSILON &&
    x1 >= 1 - WHOLE_PAGE_EPSILON &&
    y1 >= 1 - WHOLE_PAGE_EPSILON;
  return whole ? null : [x0, y0, x1, y1];
}

function regionRect(region: Region, page: Size): Rect {
  const [x0, y0, x1, y1] = region;
  return {
    left: x0 * page.width,
    top: y0 * page.height,
    width: (x1 - x0) * page.width,
    height: (y1 - y0) * page.height,
  };
}

// -------------------------------------------------------------------------- placement

function oneGroup(
  target: ViewerTarget,
  method: 'lines' | 'region',
  highlights: readonly Rect[],
): Placement | null {
  const hull = unionRectangle(highlights);
  if (hull === null) return null;
  return {
    target,
    resolution: { status: 'found', method, occurrences: 1 },
    groups: [{ highlights, hull }],
  };
}

/**
 * Authorities 1 and 2: the placement a target's own geometry gives, or null when it gives none
 * (no geometry, or geometry that does not lie on this page).
 */
export function placeByGeometry(target: ViewerTarget, page: Size): Placement | null {
  if (target.rects !== undefined && target.rects.length > 0 && insidePage(target.rects, page)) {
    const placed = oneGroup(target, 'lines', target.rects);
    if (placed !== null) return placed;
  }
  if (target.region !== undefined && regionOf(target.region) !== null) {
    return oneGroup(target, 'region', [regionRect(target.region, page)]);
  }
  return null;
}

/** What the viewer reads of a page's text: the items, and the transform to page points. */
export interface TextSnapshot {
  readonly items: readonly TextRun[];
  readonly transform: readonly number[];
}

function unplaced(target: ViewerTarget, status: QuotationStatus): Placement {
  return { target, resolution: { status, method: null, occurrences: 0 }, groups: [] };
}

/** How much of the smaller of two boxes must lie inside the other for them to be the same place. */
const SAME_PLACE = 0.5;

function overlapShare(left: Rect, right: Rect): number {
  const width = Math.min(left.left + left.width, right.left + right.width) - Math.max(left.left, right.left);
  const height = Math.min(left.top + left.height, right.top + right.height) - Math.max(left.top, right.top);
  if (!(width > 0 && height > 0)) return 0;
  return (width * height) / Math.min(left.width * left.height, right.width * right.height);
}

/**
 * Place every target of one page. The page's text is asked for when some target has a quotation
 * to look for and either no geometry of its own, or line geometry that the text can check.
 */
export async function placeTargets(
  targets: readonly ViewerTarget[],
  page: Size,
  readText: () => Promise<TextSnapshot>,
): Promise<readonly Placement[]> {
  const byGeometry = targets.map((target) => placeByGeometry(target, page));
  const searching = targets.filter(
    (target, at) =>
      (target.quote ?? '') !== '' && (byGeometry[at] === null || byGeometry[at]?.resolution.method === 'lines'),
  );
  if (searching.length === 0) {
    return targets.map((target, at) => byGeometry[at] ?? unplaced(target, 'not-found'));
  }

  const text = await readText();
  const located = locateQuotations(
    text.items,
    searching.map((target, ordinal) => ({ ordinal, quote: target.quote ?? '' })),
    text.transform,
  );
  return targets.map((target, at) => {
    const given = byGeometry[at] ?? null;
    const found = located[searching.indexOf(target)];
    const groups: PlacedGroup[] =
      found?.occurrences.flatMap((occurrence) => {
        const hull = unionRectangle(occurrence.highlights);
        return hull === null ? [] : [{ highlights: occurrence.highlights, hull }];
      }) ?? [];

    if (given !== null) {
      // Lines the page's own text contradicts are refused; lines nothing contradicts stand.
      const here = given.groups[0]?.hull;
      const contradicted =
        given.resolution.method === 'lines' &&
        here !== undefined &&
        groups.length > 0 &&
        groups.every((group) => overlapShare(here, group.hull) < SAME_PLACE);
      if (!contradicted) return given;
    }
    if (found === undefined) return unplaced(target, 'not-found');
    if (groups.length === 0) return unplaced(target, found.status === 'found' ? 'not-found' : found.status);
    return {
      target,
      resolution: { status: 'found', method: 'text', occurrences: groups.length },
      groups,
    } satisfies Placement;
  });
}

/** The outcome of each placement by target id: what the cards beside the page read. */
export function resolutionsOf(placements: readonly Placement[]): ReadonlyMap<string, TargetResolution> {
  return new Map(placements.map((placed) => [placed.target.id, placed.resolution]));
}

/**
 * The one line a card says about its frame, in the words the reviewer reads. Every outcome has a
 * sentence, and none claims more than the authority that placed it: «по разметке строк» is the
 * server's geometry, «в тексте страницы» is a search, and a quotation nothing placed says so and
 * sends the reader to the quotation.
 */
export function resolutionSentence(resolution: TargetResolution): string {
  if (resolution.status === 'no-text-layer') {
    return 'У страницы нет текстового слоя (возможно, это скан), поэтому фрагмент не отмечен — сверяйте по цитате.';
  }
  if (resolution.status === 'not-found' || resolution.method === null) {
    return 'На странице фрагмент не найден — сверяйте по цитате.';
  }
  if (resolution.method === 'text') {
    return resolution.occurrences > 1
      ? `Найдено в тексте страницы, совпадений: ${resolution.occurrences}.`
      : 'Найдено в тексте страницы.';
  }
  return resolution.method === 'region'
    ? 'Отмечено по области, которую передал источник.'
    : 'Отмечено по разметке строк.';
}
