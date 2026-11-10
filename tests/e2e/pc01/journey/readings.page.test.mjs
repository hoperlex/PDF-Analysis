/**
 * `D-619`: the walk's readings in a real browser, over a fixture page, shown red on the faulty page and green on the clean one.
 *
 *     E2E_PC01_CHROME=/path/to/chrome node --test tests/e2e/pc01/journey/readings.page.test.mjs
 *
 * `readings.test.mjs` holds the verdicts without a browser. The page-side expressions (`PAGE_READING`, `MENU_READING`) read boxes, computed
 * styles and ranges, which a fake document cannot make honest, so they are exercised here over `fixtures/readings-page.html`, served on a
 * loopback port by this test. The same file is loaded twice: with its `#fault` style (four faults: a scroller wider than its box, an
 * opened menu wider than the page, a table column squeezed to 24 px, a box that clips its text) and without it (`?clean=1`). The expressions
 * and verdicts are the journey's own (`readings.mjs`), not copies; only the page differs.
 *
 * It needs a Chrome and, like `cdp.mjs`, will not skip without one, so it is NOT in the list `test_pc01_journey_conformance.py` runs with
 * the gate (the gate host names no browser). It needs no stand and no sign-in.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, join } from 'node:path';
import test, { after, before } from 'node:test';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';
import { readingFindings, readingFlags, readingNotes, styleInjection, takeReadings, wideScrollers } from './readings.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE = readFileSync(join(HERE, 'fixtures', 'readings-page.html'), 'utf8');
const FAULT = /<style id="fault">[\s\S]*?<\/style>/;
assert.ok(FAULT.test(FIXTURE), 'the fixture lost its #fault style: the test would compare a page with itself');

let server;
let origin;
before(async () => {
  server = createServer((request, response) => {
    const clean = new URL(request.url, 'http://127.0.0.1').searchParams.get('clean') === '1';
    response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    response.end(clean ? FIXTURE.replace(FAULT, '') : FIXTURE);
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
});
after(() => new Promise((resolve) => server.close(resolve)));

/** One cold browser at `width`, the page loaded as asked, every reading taken the way the journey takes them. */
async function read({ width, clean, baselineHeight = null }) {
  const viewport = { width, height: width <= 480 ? 844 : 900 };
  const readings = await withColdBrowser(
    async (page) => {
      await page.goto(`${origin}/${clean ? '?clean=1' : ''}`);
      return await takeReadings(page, viewport, { baselineHeight });
    },
    { viewport },
  );
  return { readings, viewport };
}

test('D-619: at 390 px the faulty page is read as a wide scroller, a widening menu, a squeezed row and a clipped box', async () => {
  const { readings, viewport } = await read({ width: 390, clean: false });
  const { facts } = readings;

  // the inner scroller, with its two widths
  const wide = wideScrollers(facts, viewport.width);
  assert.equal(wide.length, 1, JSON.stringify(facts.scrollers));
  assert.equal(wide[0].scrollWidth, 900);
  assert.ok(wide[0].clientWidth < 400, `clientWidth ${wide[0].clientWidth}`);
  assert.equal(wide[0].table, false);

  // the box that clips its text
  assert.equal(facts.clipped.length, 1, JSON.stringify(facts.clipped));
  assert.equal(facts.clipped[0].w, 100);
  assert.ok(facts.clipped[0].scrollWidth > 100);

  // the tallest row of the table, cell by cell: the first cell is the one that makes it tall
  assert.equal(facts.tables.length, 1);
  const [table] = facts.tables;
  assert.ok(table.tallestRow > 150, `tallest row ${table.tallestRow}`);
  assert.ok(table.cells[0].textH >= 4 * table.cells[1].textH, JSON.stringify(table.cells));
  assert.ok(table.cells[0].w < 40, `the squeezed cell is ${table.cells[0].w} px wide`);

  // the stacked menu: opened by the reading, and the page measured again
  assert.equal(readings.menu.found, true);
  assert.equal(readings.menu.expanded, 'true');
  assert.equal(readings.menu.links, 2);
  assert.ok(readings.afterMenu.scrollWidth >= 1500, `scrollWidth after the click ${readings.afterMenu.scrollWidth}`);
  assert.equal(readings.afterMenu.innerWidth, 390);
  assert.ok(facts.scrollW <= facts.vw, 'before the click the page does not scroll sideways: the old width assertion is blind to the menu');

  // what the journey would do with it
  assert.deepEqual(readingFlags(readings, viewport), ['scroller', 'menu-overflow']);
  const findings = readingFindings('fixture', readings, viewport);
  assert.equal(findings.length, 1);
  assert.match(findings[0], /^fixture: the stacked menu, opened at 390 px, makes the screen scroll sideways\./);
  assert.equal(readingNotes('fixture', readings, viewport).length, 1);
});

test('D-619: the same page without its fault is read clean: no scroller, no clip, no tall row, a menu that fits', async () => {
  const { readings, viewport } = await read({ width: 390, clean: true });
  const { facts } = readings;
  assert.deepEqual(wideScrollers(facts, viewport.width), []);
  assert.deepEqual(facts.clipped, []);
  assert.equal(facts.tables.length, 1);
  assert.ok(facts.tables[0].tallestRow <= 70, `tallest row ${facts.tables[0].tallestRow}`);
  assert.ok(facts.tables[0].cells[0].w > 100);
  assert.equal(readings.menu.found, true);
  assert.equal(readings.menu.expanded, 'true');
  assert.ok(readings.afterMenu.scrollWidth <= readings.afterMenu.innerWidth, JSON.stringify(readings.afterMenu));
  assert.deepEqual(readingFlags(readings, viewport), []);
  assert.deepEqual(readingFindings('fixture', readings, viewport), []);
  assert.deepEqual(readingNotes('fixture', readings, viewport), []);
});

test('D-619: at 1280 px the menu is not opened, and the faulty page keeps its scroller and its tall row', async () => {
  const { readings, viewport } = await read({ width: 1280, clean: false });
  assert.equal(readings.menu, null, 'the menu is stacked only under 1024 px');
  assert.equal(readings.afterMenu, null);
  assert.equal(wideScrollers(readings.facts, viewport.width).length, 1);
  assert.deepEqual(readingFlags(readings, viewport), ['scroller']);
  assert.deepEqual(readingFindings('fixture', readings, viewport), []);
  const clean = await read({ width: 1280, clean: true });
  assert.deepEqual(readingFlags(clean.readings, clean.viewport), []);
});

test('D-619: the page height against a baseline: a page over three times its twin is a finding, the same page against itself is not', async () => {
  const wideTwin = await read({ width: 1280, clean: true });
  const own = wideTwin.readings.facts.scrollH;
  assert.ok(own > 0);
  // The same page read against a baseline a third of its height is over the limit; against its own height it is at 1.0.
  const against = await read({ width: 1280, clean: true, baselineHeight: Math.floor(own / 4) });
  assert.ok(against.readings.ratio > 3, `ratio ${against.readings.ratio}`);
  assert.deepEqual(readingFlags(against.readings, against.viewport), ['height>3x']);
  assert.equal(readingFindings('fixture', against.readings, against.viewport).length, 1);
  const itself = await read({ width: 1280, clean: true, baselineHeight: own });
  assert.equal(itself.readings.ratio, 1);
  assert.deepEqual(readingFindings('fixture', itself.readings, itself.viewport), []);
});

test('D-619: the lab\'s injection reaches the live page: a candidate rule changes the reading, and a page without it does not', async () => {
  const viewport = { width: 390, height: 844 };
  const rule = '.c-name { width: 24px !important; }';
  const heights = await withColdBrowser(
    async (page) => {
      await page.goto(`${origin}/?clean=1`);
      const before = (await takeReadings(page, { width: 1280 })).facts.tables[0].tallestRow;
      await page.evaluate(styleInjection(rule));
      await new Promise((resolve) => setTimeout(resolve, 200));
      const after = (await takeReadings(page, { width: 1280 })).facts.tables[0].tallestRow;
      return { before, after };
    },
    { viewport },
  );
  assert.ok(heights.before <= 70, `before ${heights.before}`);
  assert.ok(heights.after > 150, `after the injected rule ${heights.after}`);
});
