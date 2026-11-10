/**
 * The walk's DOM readings, as one journey tool (`D-619`, lane WALK-TOOLS; taken from the probe of lane WALK-V5).
 *
 * ## What it is for
 *
 * `width.mjs` holds two assertions, both PASS/FAIL: the page does not scroll sideways (`D-93`) and no text column is squeezed
 * to a sliver (`D-565`). The walk of 2026-11-10 (lane WALK-V5, 37 screens at 7 widths, 1680 and 1920 for the four that change
 * there) took further readings that are not assertions, because a human has to judge them, and they found the faults the two
 * assertions are blind to. This module is those readings. It is switched on with `journey.mjs --readings` and reads nothing
 * that `width.mjs` already reads.
 *
 *   - the page height, and its ratio to the same route at a baseline width (`--readings-baseline <journey.json of a 1280 run>`):
 *     a layout that folds into a tall column of syllables is a page over three times as tall as its wide twin, and no width
 *     assertion sees it (a flag over `HEIGHT_RATIO_LIMIT`, a finding only when the baseline was asked for);
 *   - the inner scrollers whose content is wider than their box (a table inside its frame is by design; the reading names it
 *     and leaves the judgement to the reader: a note, never a finding), the boxes that clip or truncate their text, the boxes
 *     that start left of the page, the elements that really widen the page (not clipped by an ancestor);
 *   - the stacked menu under `STACKED_MENU_BELOW` px: it is opened, and the page is measured again. A menu that widens the page
 *     once opened is a width fault the old assertion cannot make, because it measures before any click (a finding);
 *   - the tallest body row of each table, cell by cell: which cell makes the row tall (a narrow cell in a tall row is often a
 *     symptom of a neighbour, and the cell's own text height tells them apart).
 *
 * ## Why the verdicts are pure functions
 *
 * `OPERATING_CONSTRAINTS.md` section 12: the page-side expressions are strings the journey evaluates in the page, so `readings.test.mjs`
 * cannot exercise them without a layout engine; `readings.page.test.mjs` does, in a real browser over `fixtures/readings-page.html`
 * (the same expressions, red on the faulty page and green on the clean one). What decides, once the page has answered, is here
 * and is held by plain unit tests.
 *
 * ## The record
 *
 * `takeReadings` returns `{ facts, ratio, baselineHeight, menu, afterMenu, flags }`; `facts` keeps the shape lane WALK-V5's
 * `records.jsonl` had (`scrollH`, `scrollers`, `clipped`, `truncated`, `left`, `realOffenders`, `tables`, `h1`, `tinyText`), so a
 * walk of the matrix by the journey (one `--width` per run) and the old probe's records compare route by route.
 */

import { measureWidth } from './width.mjs';

/** An inner scroller is "wide" when its content passes its box by more than this many px (a scrollbar's width and a border are not a layout). */
export const WIDE_SCROLLER_MARGIN = 16;
/** Under this width a table that scrolls inside its frame is by design (a phone shows a wide table through a window), so it is not noted. */
export const SCROLLER_TABLE_MIN_WIDTH = 768;
/** A page more than this many times as tall as the same route at the baseline width is flagged. Strictly more: 3.0 is not. */
export const HEIGHT_RATIO_LIMIT = 3;
/** Under this width the application stacks its menu behind a «Меню» button. */
export const STACKED_MENU_BELOW = 1024;

/**
 * The page's facts, evaluated in the page. Nothing here changes the page: it reads boxes, computed styles and ranges.
 * (It is a template string: every backslash that must reach the page is doubled.)
 */
export const PAGE_READING = `(() => {
  const vw = window.innerWidth, vh = window.innerHeight, doc = document.documentElement;
  const cssName = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
  const txt = (el, n = 40) => (el.innerText ?? el.textContent ?? '').trim().replace(/\\s+/g, ' ').slice(0, n);
  const box = (r) => ({ x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) });
  const out = { vw, vh, scrollW: doc.scrollWidth, scrollH: doc.scrollHeight, scrollers: [], clipped: [], truncated: [], left: [], tinyText: 0 };
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') continue;
    const r = el.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) <= 0) continue;
    const ox = cs.overflowX;
    if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1) {
      if (ox === 'auto' || ox === 'scroll') {
        out.scrollers.push({ el: cssName(el), parent: cssName(el.parentElement), scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, box: box(r),
          table: el.querySelector('table') !== null, text: txt(el, 50) });
      } else if ((ox === 'hidden' || ox === 'clip') && txt(el) !== '') {
        const rec = { el: cssName(el), text: txt(el, 50), scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, w: Math.round(r.width), h: Math.round(r.height) };
        (cs.textOverflow === 'ellipsis' ? out.truncated : out.clipped).push(rec);
      }
    }
    if (r.left < -1 && r.right > 0) out.left.push({ el: cssName(el), left: Math.round(r.left), right: Math.round(r.right), text: txt(el, 30) });
    if (el.children.length === 0 && txt(el) !== '' && parseFloat(cs.fontSize) < 10) out.tinyText += 1;
  }
  // boxes that cross the right edge and are not clipped by an ancestor that scrolls or hides overflow (the ones that widen the page)
  out.realOffenders = [];
  if (doc.scrollWidth > vw) {
    for (const el of Array.from(document.querySelectorAll('body *'))) {
      const r = el.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0) || r.right <= vw + 0.5) continue;
      let clipped = false;
      for (let p = el.parentElement; p && p !== document.body && p !== doc; p = p.parentElement) {
        const o = getComputedStyle(p).overflowX;
        if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') { clipped = true; break; }
      }
      const pos = getComputedStyle(el).position;
      if (!clipped && pos !== 'fixed') out.realOffenders.push({ el: cssName(el), right: Math.round(r.right), w: Math.round(r.width), text: txt(el, 40) });
    }
    out.realOffenders.sort((a, b) => b.right - a.right);
    out.realOffenders = out.realOffenders.slice(0, 8);
  }
  // the tallest body row of each visible table, cell by cell: which cell makes the row tall
  out.tables = [];
  for (const table of Array.from(document.querySelectorAll('table')).slice(0, 6)) {
    const tr = table.getBoundingClientRect();
    if (!(tr.width > 0 && tr.height > 0)) continue;
    const rows = Array.from(table.querySelectorAll('tbody tr')).filter((row) => row.getBoundingClientRect().height > 0);
    if (rows.length === 0) continue;
    const tallest = rows.reduce((a, b) => (b.getBoundingClientRect().height > a.getBoundingClientRect().height ? b : a));
    const cellInfo = Array.from(tallest.children).map((c) => {
      const range = document.createRange(); range.selectNodeContents(c);
      const rr = range.getBoundingClientRect(); const cr = c.getBoundingClientRect();
      return { t: txt(c, 28), w: Math.round(cr.width), h: Math.round(cr.height), textH: Math.round(rr.height), textW: Math.round(rr.width) };
    });
    out.tables.push({ el: cssName(table), w: Math.round(tr.width), rows: rows.length, tallestRow: Math.round(tallest.getBoundingClientRect().height), cells: cellInfo });
  }
  out.scrollers = out.scrollers.slice(0, 12); out.clipped = out.clipped.slice(0, 8); out.truncated = out.truncated.slice(0, 8); out.left = out.left.slice(0, 6);
  const h1 = document.querySelector('h1');
  out.h1 = h1 ? { text: txt(h1, 60), top: Math.round(h1.getBoundingClientRect().top + scrollY), h: Math.round(h1.getBoundingClientRect().height) } : null;
  out.h1Count = document.querySelectorAll('h1').length;
  out.title = document.title;
  return out;
})()`;

/**
 * Open the stacked menu and say what it is: the «Меню» button (a visible button whose text starts with it), its panel (the
 * element it controls, or its parent), the panel's box, and how far the links reach. It CLICKS, so it is taken last and once
 * per page: a second click would close the menu it opened.
 */
export const MENU_READING = `(async () => {
  const btn = Array.from(document.querySelectorAll('button')).find((b) => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 && /^Меню/.test((b.innerText || '').trim()); });
  if (!btn) return { found: false };
  btn.click();
  await new Promise((r) => setTimeout(r, 350));
  const panelId = btn.getAttribute('aria-controls');
  const panel = (panelId ? document.getElementById(panelId) : null) || btn.parentElement;
  const r = panel.getBoundingClientRect(); const cs = getComputedStyle(panel);
  const links = Array.from(panel.querySelectorAll('a')).filter((a) => a.getBoundingClientRect().height > 0);
  const doc = document.documentElement;
  return { found: true, expanded: btn.getAttribute('aria-expanded'), panel: { w: Math.round(r.width), h: Math.round(r.height), sh: panel.scrollHeight, ch: panel.clientHeight, oy: cs.overflowY },
    links: links.length, rightMax: Math.max(0, ...links.map((a) => Math.round(a.getBoundingClientRect().right))), scrollWidth: doc.scrollWidth, innerWidth: innerWidth, innerHeight: innerHeight };
})()`;

/** The ratio of a page's height to the same route's height at the baseline width, two decimals; `null` when there is no baseline to compare with. */
export function heightRatio(height, baselineHeight) {
  if (typeof height !== 'number' || typeof baselineHeight !== 'number' || !(baselineHeight > 0)) return null;
  return Math.round((height / baselineHeight) * 100) / 100;
}

/**
 * The inner scrollers worth a look at this width: content past the box by more than `WIDE_SCROLLER_MARGIN`, and, under
 * `SCROLLER_TABLE_MIN_WIDTH`, not a table (a wide table in its own window is how a phone shows it).
 */
export function wideScrollers(facts, width) {
  return (facts?.scrollers ?? []).filter(
    (s) => s.scrollWidth - s.clientWidth > WIDE_SCROLLER_MARGIN && (width >= SCROLLER_TABLE_MIN_WIDTH || !s.table),
  );
}

/** Did the stacked menu, once opened, widen the page? The page's own numbers, as the old assertion reads them. */
export function menuWidensThePage(afterMenu) {
  return afterMenu !== null && afterMenu !== undefined && afterMenu.scrollWidth > afterMenu.innerWidth;
}

/** Short flags for a route's line: `scroller`, `height>3x`, `menu-overflow`. A flag asks for a look; only two of them are findings (below). */
export function readingFlags(readings, viewport) {
  const flags = [];
  if (wideScrollers(readings.facts, viewport.width).length > 0) flags.push('scroller');
  if (readings.ratio !== null && readings.ratio !== undefined && readings.ratio > HEIGHT_RATIO_LIMIT) flags.push(`height>${HEIGHT_RATIO_LIMIT}x`);
  if (menuWidensThePage(readings.afterMenu)) flags.push('menu-overflow');
  return flags;
}

/** What to print under a route's line: every wide scroller by name, with its numbers. Notes are for a reader; they never redden a run. */
export function readingNotes(where, readings, viewport) {
  return wideScrollers(readings.facts, viewport.width).map(
    (s) =>
      `${where}: <${s.el}> scrolls inside its box: content ${s.scrollWidth} px in ${s.clientWidth} px (${s.table ? 'holds a table' : 'not a table'})` +
      `${s.text ? ` "${s.text}"` : ''}`,
  );
}

/**
 * The verdict, as zero, one or two findings. Only what is unambiguous reddens a run:
 *
 *   - the stacked menu, opened, makes the page scroll sideways (the width assertion measures before any click);
 *   - the page is more than `HEIGHT_RATIO_LIMIT` times as tall as its baseline twin, and ONLY when a baseline was given
 *     (`--readings-baseline`): asking for it is what makes the comparison a request and not a guess.
 *
 * A wide scroller is a note (`readingNotes`), because a table in its frame is by design and nothing in the DOM says which is which.
 */
export function readingFindings(where, readings, viewport) {
  if (readings === null || readings === undefined) {
    return [`${where}: the readings could not be taken from the page at all`];
  }
  const findings = [];
  if (menuWidensThePage(readings.afterMenu)) {
    const after = readings.afterMenu;
    const named = (after.offenders ?? [])
      .slice(0, 3)
      .map((o) => `<${o.tag}${o.className ? `.${String(o.className).split(/\s+/).join('.')}` : ''}> right=${o.right} width=${o.width}`)
      .join('; ');
    findings.push(
      `${where}: the stacked menu, opened at ${viewport.width} px, makes the screen scroll sideways. ` +
        `scrollWidth ${after.scrollWidth} > innerWidth ${after.innerWidth}, overflowing by ${after.scrollWidth - after.innerWidth} px` +
        `${named ? `; widest: ${named}` : ''}. The width assertion measures before any click, so it cannot see this.`,
    );
  }
  if (readings.ratio !== null && readings.ratio !== undefined && readings.ratio > HEIGHT_RATIO_LIMIT) {
    findings.push(
      `${where}: the screen is ${readings.ratio} times as tall at ${viewport.width} px as at the baseline width ` +
        `(${readings.facts?.scrollH} px against ${readings.baselineHeight} px; the limit is ${HEIGHT_RATIO_LIMIT}). ` +
        'A squeezed layout grows the page taller instead of wider, which no width assertion sees.',
    );
  }
  return findings;
}

/**
 * Take every reading of the page, in this order: the facts, then (under `STACKED_MENU_BELOW`) the menu, opened, and the width
 * measured again. The page must have settled. The menu click is the only thing this changes, so it comes last.
 * `viewport` is the width the walk was laid out at; `baselineHeight` is this route's height at the baseline width, if one was given.
 */
export async function takeReadings(page, viewport, { baselineHeight = null } = {}) {
  const facts = await page.evaluate(PAGE_READING);
  const width = viewport?.width ?? facts.vw;
  let menu = null;
  let afterMenu = null;
  if (width < STACKED_MENU_BELOW) {
    menu = await page.evaluate(MENU_READING);
    if (menu && menu.found) {
      const measured = await measureWidth(page);
      afterMenu = { scrollWidth: measured.scrollWidth, innerWidth: measured.innerWidth, offenders: measured.offenders.slice(0, 3) };
    }
  }
  const readings = { facts, ratio: heightRatio(facts.scrollH, baselineHeight), baselineHeight, menu, afterMenu };
  readings.flags = readingFlags(readings, { width });
  return readings;
}

/**
 * The page heights of an earlier run, route by route: `{ name -> scrollH }` from the envelope (`journey.json`) of a run made
 * with `--readings` at the baseline width. A run without readings has nothing to compare with, and that is a stop, not a silence.
 */
export function baselineHeights(envelope) {
  const heights = new Map();
  for (const record of envelope?.records ?? []) {
    const height = record?.readings?.facts?.scrollH;
    if (typeof record?.name === 'string' && typeof height === 'number') heights.set(record.name, height);
  }
  if (heights.size === 0) {
    throw new Error('the baseline envelope carries no readings: run the baseline width with --readings first');
  }
  return heights;
}

/**
 * `{ "name": "css" | null }` -> `[[name, css | null], ...]`. `null` is the page as it is (the control of a lab). Anything else than a string
 * of CSS or `null` is a hard stop: a variant that quietly measured nothing would look like a variant that changed nothing.
 */
export function parseVariants(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    throw new Error(`the variants file is not JSON: ${error.message}`);
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('the variants file must be a JSON object of {name: css | null}');
  }
  const entries = Object.entries(parsed);
  if (entries.length === 0) throw new Error('the variants file names no variant');
  for (const [name, css] of entries) {
    if (css !== null && typeof css !== 'string') throw new Error(`variant '${name}' must be a string of CSS or null (got ${typeof css})`);
    if (typeof css === 'string' && css.trim() === '') throw new Error(`variant '${name}' is an empty string: use null for the page as it is`);
  }
  return entries;
}

/** An expression that appends one `<style>` holding `css` to the live page. The CSS travels as a JSON string, so no character of it can end the expression. */
export function styleInjection(css) {
  return `(() => { const s = document.createElement('style'); s.setAttribute('data-lab', ''); s.textContent = ${JSON.stringify(css)}; document.head.appendChild(s); return true; })()`;
}
