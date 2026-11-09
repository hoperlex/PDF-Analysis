/**
 * One layout assertion, shared by the journey and by the proof that it can fail.
 *
 * ## The row
 *
 * `D-93`. Wave 43's four navigation links widened `.am-app__bar` past the viewport and
 * moved the overflow threshold from **482 px to 839 px**, so every screen in the product
 * -- `AppFrame` is global -- carried a horizontal scrollbar on a small laptop and on every
 * tablet. **This programme has 1085 frontend tests and not one of them could express a
 * width**, because the battery renders through `renderToStaticMarkup`: no layout, no box,
 * no viewport. It took a judge driving a browser to see it.
 *
 * `W43-JUDGE-B` proposed the cheap structural answer and this is it: **one assertion in
 * the journey, `scrollWidth <= innerWidth` at a declared width, on every route.** The next
 * added link then reddens by itself, on every screen, without anybody predicting which
 * screen.
 *
 * ## Why this is a module and not four lines inside `journey.mjs`
 *
 * `OPERATING_CONSTRAINTS.md` §12: a query that shares an assumption with the thing it
 * measures is not a measurement. The proof that this assertion can go red must exercise
 * **this** code, not a second copy of it written to agree -- so the expression, the
 * comparison and the wording of the finding live here, and
 * `prove_the_width_assertion_can_fail.mjs` imports the same three.
 *
 * ## Which comparison decides, stated once
 *
 * `document.documentElement.scrollWidth <= window.innerWidth`.
 *
 * `clientWidth` is the tempting one and it is the wrong one here: a vertical scrollbar
 * makes it smaller than the viewport, so a page that exactly fills the viewport would
 * redden for having a scrollbar rather than for having a layout defect. `innerWidth` is
 * the looser of the two and is the one that cannot produce a false red. A page over the
 * viewport by less than a scrollbar's width passes; a page that a reviewer has to scroll
 * sideways does not, which is the class the row is about.
 */

/**
 * What the page says about its own width, plus the elements sticking out of it.
 *
 * The offenders are the actionable half. `W43-JUDGE-B` found the bar by looking; a finding
 * that says only "839 > 780" sends the next reader looking again, so the widest few boxes
 * that cross the viewport's right edge are named with enough of their identity to grep.
 */
export const MEASUREMENT = `(() => {
  const doc = document.documentElement;
  const innerWidth = window.innerWidth;
  const offenders = [];
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const right = r.right + window.scrollX;
    if (right <= innerWidth + 0.5) continue;
    offenders.push({
      tag: el.tagName.toLowerCase(),
      className: typeof el.className === 'string' ? el.className.slice(0, 120) : null,
      id: el.id || null,
      left: Math.round(r.left + window.scrollX),
      right: Math.round(right),
      width: Math.round(r.width),
      text: (el.innerText ?? '').trim().replace(/\\s+/g, ' ').slice(0, 60),
    });
  }
  offenders.sort((a, b) => b.right - a.right);
  return {
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    innerWidth,
    bodyScrollWidth: document.body ? document.body.scrollWidth : null,
    offenders: offenders.slice(0, 5),
    offenderCount: offenders.length,
  };
})()`;

/** Take the reading. The page must already have settled; this reflows nothing. */
export async function measureWidth(page) {
  return await page.evaluate(MEASUREMENT);
}

/**
 * The verdict, as zero or one finding.
 *
 * `declared` is the manifest's `viewport`. It is passed in rather than imported so that
 * the assertion cannot quietly measure against a width the manifest does not state --
 * §12's "never build an expectation out of the thing under test", applied to a number.
 */
export function widthFindings(where, measurement, declared) {
  if (measurement === null || measurement === undefined) {
    return [`${where}: the width could not be read from the page at all`];
  }
  const { scrollWidth, innerWidth, clientWidth, offenders, offenderCount } = measurement;
  // `D-380`: a run may ask for another width than the manifest's (`--width`); `declared.requested` says so, and the
  // findings then name the width as requested, because "declared" would send a reader to a manifest that says 780.
  const kind = declared.requested === true ? 'requested' : 'declared';
  if (innerWidth !== declared.width) {
    // The viewport was not the one declared, so whatever the comparison says is a
    // statement about some other width. That is a finding, not a caveat.
    return [
      `${where}: the page was laid out at ${innerWidth} px and this ${declared.requested === true ? 'run requests' : 'manifest declares'} ` +
        `${declared.width} px, so the width assertion measured a viewport nobody stated`,
    ];
  }
  if (scrollWidth <= innerWidth) return [];
  const named =
    offenders.length === 0
      ? '(no element crosses the edge, so the overflow is in a margin, a shadow or a ' +
        'scroll container rather than in a box)'
      : offenders
          .map(
            (o) =>
              `<${o.tag}${o.id ? `#${o.id}` : ''}${o.className ? `.${o.className.split(/\s+/).join('.')}` : ''}> ` +
              `right=${o.right} width=${o.width}${o.text ? ` "${o.text}"` : ''}`,
          )
          .join('; ');
  return [
    `${where}: the screen scrolls sideways at the ${kind} width. ` +
      `scrollWidth ${scrollWidth} > innerWidth ${innerWidth} (clientWidth ${clientWidth}), ` +
      `overflowing by ${scrollWidth - innerWidth} px. ` +
      `${offenderCount} element(s) cross the right edge; widest: ${named}. ` +
      'D-93: AppFrame is global, so this is every screen in the product and not this one.',
  ];
}

/**
 * `D-565`: a collapsed column is a width fault that `scrollWidth <= innerWidth` cannot see.
 *
 * ## The row
 *
 * `D-560` (a section table whose name column was 12 px wide at 1280) and `D-561` (37 px at 390) passed the assertion
 * above in every walk since the section table got its five numbers. A grid track that is squeezed does not push the
 * page sideways: the text wraps one word to a line inside the narrow box and the page grows TALLER, so the document's
 * width is untouched while a reader sees a column of syllables. Lane WALK-V4 found both by reading the boxes, not
 * the page.
 *
 * ## The reading, stated once
 *
 * A visible leaf box (its children, if any, are inline) that holds at least `COLLAPSED_MIN_TEXT` characters of text,
 * is narrower than `COLLAPSED_MAX_WIDTH` px and taller than `COLLAPSED_MIN_HEIGHT` px. Ten characters in a box under
 * 90 px wide wrap in two lines at most unless the box is squeezed (a 16 px line is about 8 px per character, so ten
 * characters need 80 px on one line), and a box over 70 px tall holds four lines or more at the dense line height.
 * A word that is simply long (`Администратор` in a narrow chip) is one line and therefore short, so it does not read.
 * Vertical writing is skipped: a rotated label is narrow and tall by design.
 *
 * The page of WALK-V4 gave 16 hits on «Главная» at 390 px and 15 at 1440 px before the fix and none after; one true
 * hit was left (`D-563`, the author cell of the runs' table).
 */
export const COLLAPSED_MIN_TEXT = 10;
export const COLLAPSED_MAX_WIDTH = 90;
export const COLLAPSED_MIN_HEIGHT = 70;

export const COLLAPSED_READING = `(() => {
  const MIN_TEXT = ${COLLAPSED_MIN_TEXT}, MAX_WIDTH = ${COLLAPSED_MAX_WIDTH}, MIN_HEIGHT = ${COLLAPSED_MIN_HEIGHT};
  const hits = [];
  let count = 0;
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    const tag = el.tagName.toLowerCase();
    if (el.closest('svg') && tag !== 'svg') continue;
    const r = el.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) continue;
    if (!(r.width < MAX_WIDTH && r.height > MIN_HEIGHT)) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) <= 0) continue;
    if (typeof cs.writingMode === 'string' && cs.writingMode.startsWith('vertical')) continue;
    const text = (el.innerText ?? el.textContent ?? '').trim().replace(/\\s+/g, ' ');
    if (text.length < MIN_TEXT) continue;
    const leaf = Array.from(el.children).every((c) => { const d = getComputedStyle(c).display; return d === 'inline' || d === 'none'; });
    if (!leaf) continue;
    count += 1;
    if (hits.length >= 8) continue;
    const lineHeight = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.3;
    hits.push({
      tag,
      className: typeof el.className === 'string' ? el.className.trim().slice(0, 120) : null,
      id: el.id || null,
      width: Math.round(r.width),
      height: Math.round(r.height),
      lines: Math.round(r.height / lineHeight),
      text: text.slice(0, 50),
    });
  }
  return { count, hits };
})()`;

/** Take the collapsed-column reading. Like `measureWidth`, it reflows nothing. */
export async function measureCollapsed(page) {
  return await page.evaluate(COLLAPSED_READING);
}

/**
 * The verdict, as zero or one finding. `reading` is what `measureCollapsed` returned; `declared` is the viewport the run
 * was held to, so the finding names the width the squeeze was measured at.
 */
export function collapsedFindings(where, reading, declared) {
  if (reading === null || reading === undefined) {
    return [`${where}: the collapsed-column reading could not be taken from the page at all`];
  }
  if (!(reading.count > 0)) return [];
  const kind = declared.requested === true ? 'requested' : 'declared';
  const named = reading.hits
    .map(
      (h) =>
        `<${h.tag}${h.id ? `#${h.id}` : ''}${h.className ? `.${h.className.split(/\s+/).join('.')}` : ''}> ` +
        `${h.width} x ${h.height} px (${h.lines} lines) "${h.text}"`,
    )
    .join('; ');
  return [
    `${where}: a column collapsed at the ${kind} width ${declared.width} px. ` +
      `${reading.count} visible text box(es) of ${COLLAPSED_MIN_TEXT} or more characters are under ${COLLAPSED_MAX_WIDTH} px wide ` +
      `and over ${COLLAPSED_MIN_HEIGHT} px tall; first: ${named}. ` +
      'D-565: a squeezed grid track makes the page taller instead of wider, so scrollWidth cannot see it.',
  ];
}
