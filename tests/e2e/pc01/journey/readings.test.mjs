/**
 * `D-619`: the verdicts of `readings.mjs`, without a browser (`node --test tests/e2e/pc01/journey/readings.test.mjs`; the gate runs it).
 *
 * The page-side expressions need a layout engine and are held by `readings.page.test.mjs`, which drives a real browser over
 * `fixtures/readings-page.html` and needs a Chrome (`E2E_PC01_CHROME`), so it is not in the gate's list. What is here is what
 * decides once the page has answered: the thresholds (each shown on both sides of its edge), the flags, the findings, the
 * baseline of an earlier run, and the two helpers of the CSS lab.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { Script, runInNewContext } from 'node:vm';

import {
  HEIGHT_RATIO_LIMIT,
  MENU_READING,
  PAGE_READING,
  SCROLLER_TABLE_MIN_WIDTH,
  STACKED_MENU_BELOW,
  WIDE_SCROLLER_MARGIN,
  baselineHeights,
  heightRatio,
  menuWidensThePage,
  parseVariants,
  readingFindings,
  readingFlags,
  readingNotes,
  styleInjection,
  wideScrollers,
} from './readings.mjs';

const scroller = (over, { table = false, el = 'div.frame' } = {}) => ({ el, parent: 'section', scrollWidth: 300 + over, clientWidth: 300, box: {}, table, text: 'Таблица' });
const facts = (scrollers = [], scrollH = 1500) => ({ vw: 390, scrollH, scrollers });
const readings = ({ scrollers = [], ratio = null, afterMenu = null, scrollH = 1500, baselineHeight = null } = {}) => ({ facts: facts(scrollers, scrollH), ratio, baselineHeight, afterMenu });
const phone = { width: 390, height: 844, requested: true };
const desktop = { width: 1280, height: 900, requested: true };

test('D-619: the thresholds are the ones the README states', () => {
  assert.equal(WIDE_SCROLLER_MARGIN, 16);
  assert.equal(SCROLLER_TABLE_MIN_WIDTH, 768);
  assert.equal(HEIGHT_RATIO_LIMIT, 3);
  assert.equal(STACKED_MENU_BELOW, 1024);
});

test('D-619: both page-side expressions are valid scripts, and the menu one is the only one that clicks', () => {
  // Not a substitute for the browser test: it only stops a stray backtick or an unescaped `\s` from reaching the page as a syntax error.
  assert.doesNotThrow(() => new Script(PAGE_READING));
  assert.doesNotThrow(() => new Script(MENU_READING));
  assert.ok(!/\.click\(/.test(PAGE_READING), 'the facts reading must not change the page');
  assert.ok(/\.click\(/.test(MENU_READING));
  // The doubled backslashes of the template reach the page as single ones: `\s+` in a regular expression, not `s+`.
  assert.ok(PAGE_READING.includes('/\\s+/'), 'the whitespace pattern was lost in the template string');
});

test('D-619: a ratio is height over baseline, two decimals, and none without a baseline', () => {
  assert.equal(heightRatio(4700, 1530), 3.07);
  assert.equal(heightRatio(1530, 1530), 1);
  assert.equal(heightRatio(1500, null), null);
  assert.equal(heightRatio(1500, 0), null, 'a baseline of 0 px is no baseline');
  assert.equal(heightRatio(undefined, 1500), null);
});

test('D-619: a scroller is wide when its content passes its box by MORE than the margin; under 768 px a table is by design', () => {
  assert.equal(wideScrollers(facts([scroller(WIDE_SCROLLER_MARGIN)]), 1280).length, 0, 'exactly the margin is a scrollbar, not a layout');
  assert.equal(wideScrollers(facts([scroller(WIDE_SCROLLER_MARGIN + 1)]), 1280).length, 1);
  const table = scroller(400, { table: true });
  assert.equal(wideScrollers(facts([table]), SCROLLER_TABLE_MIN_WIDTH - 1).length, 0, 'a table in its window on a phone');
  assert.equal(wideScrollers(facts([table]), SCROLLER_TABLE_MIN_WIDTH).length, 1, 'the same table at 768 px is worth a look');
  assert.equal(wideScrollers(facts([scroller(400)]), 390).length, 1, 'a scroller that is not a table is worth a look at any width');
  assert.deepEqual(wideScrollers(null, 390), []);
});

test('D-619: the flags say what to look at, and only a ratio STRICTLY over the limit is flagged', () => {
  assert.deepEqual(readingFlags(readings(), phone), []);
  assert.deepEqual(readingFlags(readings({ scrollers: [scroller(300)] }), phone), ['scroller']);
  assert.deepEqual(readingFlags(readings({ ratio: HEIGHT_RATIO_LIMIT }), phone), [], '3.0 is not over 3');
  assert.deepEqual(readingFlags(readings({ ratio: 3.01 }), phone), ['height>3x']);
  const open = { scrollWidth: 471, innerWidth: 390, offenders: [] };
  assert.deepEqual(readingFlags(readings({ afterMenu: open }), phone), ['menu-overflow']);
  assert.deepEqual(readingFlags(readings({ afterMenu: { ...open, scrollWidth: 390 } }), phone), [], 'an open menu that fits the page is fine');
  assert.deepEqual(
    readingFlags(readings({ scrollers: [scroller(300)], ratio: 4, afterMenu: open }), phone),
    ['scroller', 'height>3x', 'menu-overflow'],
  );
});

test('D-619: the menu verdict reads the page after the click, and a page that never offered a menu has none', () => {
  assert.equal(menuWidensThePage(null), false);
  assert.equal(menuWidensThePage(undefined), false);
  assert.equal(menuWidensThePage({ scrollWidth: 390, innerWidth: 390 }), false);
  assert.equal(menuWidensThePage({ scrollWidth: 391, innerWidth: 390 }), true);
});

test('D-619: an open menu that widens the page is a finding with the numbers and the widest boxes; a wide scroller alone is not', () => {
  const widened = readings({
    afterMenu: { scrollWidth: 1500, innerWidth: 390, offenders: [{ tag: 'nav', className: 'nav open', right: 1500, width: 1500 }] },
  });
  const [finding] = readingFindings('root', widened, phone);
  assert.match(finding, /^root: the stacked menu, opened at 390 px, makes the screen scroll sideways\./);
  assert.match(finding, /scrollWidth 1500 > innerWidth 390, overflowing by 1110 px/);
  assert.match(finding, /<nav\.nav\.open> right=1500 width=1500/);
  assert.equal(readingFindings('root', widened, phone).length, 1);

  assert.deepEqual(readingFindings('root', readings({ scrollers: [scroller(500)] }), phone), [], 'a scroller is a note');
  assert.deepEqual(readingFindings('root', readings(), phone), []);
  assert.match(readingFindings('root', null, phone)[0], /could not be taken from the page at all/);
});

test('D-619: a page over three times as tall as its baseline is a finding only because a baseline was given', () => {
  const tall = readings({ ratio: 3.07, scrollH: 4700, baselineHeight: 1530 });
  const [finding] = readingFindings('version', tall, phone);
  assert.match(finding, /^version: the screen is 3\.07 times as tall at 390 px as at the baseline width/);
  assert.match(finding, /4700 px against 1530 px; the limit is 3/);
  assert.deepEqual(readingFindings('version', readings({ ratio: 3, scrollH: 4590, baselineHeight: 1530 }), phone), [], 'the edge itself is not over');
  assert.deepEqual(readingFindings('version', readings({ ratio: null, scrollH: 9000 }), phone), [], 'no baseline: a tall page is not compared with anything');
  assert.deepEqual(readingFindings('version', tall, desktop).length, 1, 'the ratio does not depend on the width of the run');
});

test('D-619: a note names the scroller, its two widths and whether it holds a table', () => {
  const notes = readingNotes('knowledge-base', readings({ scrollers: [scroller(645, { table: true, el: 'div.tableFrame' }), scroller(5)] }), desktop);
  assert.equal(notes.length, 1);
  assert.match(notes[0], /^knowledge-base: <div\.tableFrame> scrolls inside its box: content 945 px in 300 px \(holds a table\) "Таблица"/);
});

test('D-619: the baseline is the page heights of an earlier run with readings, and a run without them is a stop', () => {
  const envelope = {
    records: [
      { name: 'root', readings: { facts: { scrollH: 1530 } } },
      { name: 'run', readings: { facts: { scrollH: 2100 } } },
      { name: 'no-readings' },
      { name: 'broken', readings: { facts: {} } },
    ],
  };
  const heights = baselineHeights(envelope);
  assert.deepEqual([...heights.entries()], [['root', 1530], ['run', 2100]]);
  assert.throws(() => baselineHeights({ records: [{ name: 'root' }] }), /carries no readings/);
  assert.throws(() => baselineHeights({}), /carries no readings/);
  assert.throws(() => baselineHeights(null), /carries no readings/);
});

test('D-619: the lab\'s variants are CSS strings or null, and anything else stops the run', () => {
  assert.deepEqual(parseVariants('{"committed": null, "lower": ".a{min-width:5rem}"}'), [['committed', null], ['lower', '.a{min-width:5rem}']]);
  for (const bad of ['', 'not json', '[]', 'null', '{}', '{"a": 5}', '{"a": ""}', '{"a": "  "}', '{"a": {"b": "c"}}']) {
    assert.throws(() => parseVariants(bad), Error, bad);
  }
});

test('D-619: the CSS reaches the page as data: no character of it can end the injected expression', () => {
  const nasty = '/* `${process} */ [class*="a"]::after{content:"</style><script>x()</script>\\""} \n';
  const appended = [];
  const sandbox = {
    document: {
      createElement: () => ({ setAttribute() {}, textContent: null }),
      head: { appendChild: (node) => appended.push(node) },
    },
  };
  assert.equal(runInNewContext(styleInjection(nasty), sandbox), true);
  assert.equal(appended.length, 1);
  assert.equal(appended[0].textContent, nasty, 'the stylesheet is exactly the text that was asked for');
});
