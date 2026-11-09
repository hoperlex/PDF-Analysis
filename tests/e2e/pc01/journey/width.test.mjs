/**
 * `D-565`: the collapsed-column reading of `width.mjs`, run against a fake page, and shown able to fail.
 *
 * `node --test tests/e2e/pc01/journey/width.test.mjs` (the gate runs it with the other journey unit tests).
 *
 * The reading is a string that the journey evaluates in the page. Here the same string is evaluated by `node:vm` over a tiny
 * document: boxes with a rectangle, a computed style, children and text. It is the real expression, not a copy of it, so a
 * change of the thresholds or of the leaf rule shows up as a red test.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

import {
  COLLAPSED_MAX_WIDTH,
  COLLAPSED_MIN_HEIGHT,
  COLLAPSED_MIN_TEXT,
  COLLAPSED_READING,
  collapsedFindings,
  widthFindings,
} from './width.mjs';

/** A box of the fake page. `display` is the computed display; `inline` children keep the parent a leaf. */
function box(text, w, h, { tag = 'div', className = '', display = 'block', visibility = 'visible', opacity = '1', writingMode = 'horizontal-tb', children = [], inSvg = false, lineHeight = '20px', textHeight = h } = {}) {
  const el = {
    textHeight,
    tagName: tag.toUpperCase(),
    className,
    id: '',
    innerText: text,
    children,
    getBoundingClientRect: () => ({ width: w, height: h, left: 0, right: w, top: 0, bottom: h }),
    closest: (selector) => (selector === 'svg' && inSvg ? {} : null),
    style: { display, visibility, opacity, writingMode, lineHeight, fontSize: '16px' },
  };
  return el;
}

function read(...elements) {
  const sandbox = {
    document: {
      querySelectorAll: () => elements,
      // The text's own box: the fake box says how tall its text is (a cell in a tall row holds one line).
      createRange: () => {
        let target = null;
        return { selectNodeContents: (el) => { target = el; }, getBoundingClientRect: () => ({ height: target.textHeight }) };
      },
    },
    getComputedStyle: (el) => el.style,
  };
  return runInNewContext(COLLAPSED_READING, sandbox);
}

const NAME = 'Выписка из реестра';

test('D-565: the thresholds are the ones the row states', () => {
  assert.equal(COLLAPSED_MIN_TEXT, 10);
  assert.equal(COLLAPSED_MAX_WIDTH, 90);
  assert.equal(COLLAPSED_MIN_HEIGHT, 70);
});

test('D-565: a name squeezed to 12 px and 787 px tall is read as a collapsed column (the page above it is not wider)', () => {
  const squeezed = box(NAME, 12, 787, { tag: 'button', className: 'rowButton' });
  const reading = read(squeezed);
  assert.equal(reading.count, 1);
  assert.equal(reading.hits[0].tag, 'button');
  assert.equal(reading.hits[0].width, 12);
  assert.equal(reading.hits[0].height, 787);
  assert.equal(reading.hits[0].lines, 39);
});

test('D-565: the same name in a box that is wide enough, or short enough, or too short in text, is not read', () => {
  assert.equal(read(box(NAME, 245, 41)).count, 0, 'a normal row button');
  assert.equal(read(box(NAME, 89, 69)).count, 0, 'under 90 px but only three lines tall');
  assert.equal(read(box(NAME, 90, 400)).count, 0, '90 px is the edge: not under 90');
  assert.equal(read(box('Админ', 40, 200)).count, 0, 'five characters is a label, not a sentence');
  assert.equal(read(box('Администратор', 85, 22)).count, 0, 'one long word in a narrow chip is a single line');
});

test('D-565: a box nobody sees, a vertical label and a drawing\'s inner text are not read', () => {
  assert.equal(read(box(NAME, 12, 400, { display: 'none' })).count, 0);
  assert.equal(read(box(NAME, 12, 400, { visibility: 'hidden' })).count, 0);
  assert.equal(read(box(NAME, 12, 400, { opacity: '0' })).count, 0);
  assert.equal(read(box(NAME, 20, 400, { writingMode: 'vertical-rl' })).count, 0, 'a rotated label is narrow and tall by design');
  assert.equal(read(box(NAME, 12, 400, { tag: 'text', inSvg: true })).count, 0);
  assert.equal(read(box('', 12, 400)).count, 0, 'a box with no text');
});

test('D-565: a container of blocks is not a leaf; a button over inline spans is', () => {
  const inner = box('Выписка из реестра', 12, 400, { tag: 'span', display: 'inline' });
  assert.equal(read(box('Выписка из реестра', 60, 400, { children: [inner] })).count, 1, 'inline children keep it a leaf');
  const block = box('Выписка из реестра', 60, 400, { tag: 'p', display: 'block' });
  const container = box('Выписка из реестра и ещё', 60, 400, { children: [block] });
  assert.equal(read(container, block).count, 1, 'the block child is the leaf, the container is not');
  assert.equal(read(container).count, 0, 'on its own the container holds a block, so it is not a leaf');
});

test('D-565: the reading keeps at most eight named hits but counts all of them', () => {
  const many = Array.from({ length: 12 }, () => box(NAME, 40, 300));
  const reading = read(...many);
  assert.equal(reading.count, 12);
  assert.equal(reading.hits.length, 8);
});

test('D-565: the finding names the width, the box and the reason; a clean reading gives none', () => {
  const phone = { width: 390, height: 844, requested: true };
  const reading = read(box(NAME, 63, 414, { tag: 'button', className: 'rowButton name' }));
  const [finding] = collapsedFindings('root', reading, phone);
  assert.match(finding, /^root: a column collapsed at the requested width 390 px\./);
  assert.match(finding, /1 visible text box\(es\) of 10 or more characters are under 90 px wide and over 70 px tall/);
  assert.match(finding, /<button\.rowButton\.name> 63 x 414 px \(21 lines\) "Выписка из реестра"/);
  assert.match(finding, /D-565/);
  assert.deepEqual(collapsedFindings('root', read(box(NAME, 245, 41)), phone), []);
  assert.match(collapsedFindings('root', reading, { width: 780, height: 900 })[0], /at the declared width 780 px/);
  assert.match(collapsedFindings('root', null, phone)[0], /could not be taken from the page at all/);
});

test('D-565: a page that does not scroll sideways passes the width assertion while the reading still names the squeeze', () => {
  // The two readings are independent: this is the page of D-560, 1280 px wide, laid out inside its viewport.
  const page = { scrollWidth: 1280, clientWidth: 1265, innerWidth: 1280, offenders: [], offenderCount: 0 };
  const declared = { width: 1280, height: 900, requested: true };
  assert.deepEqual(widthFindings('root', page, declared), [], 'scrollWidth <= innerWidth cannot see a collapsed column');
  assert.equal(collapsedFindings('root', read(box(NAME, 12, 787, { tag: 'button' })), declared).length, 1);
});

test('D-565: a box of width 0 with its text is the extreme case and is read (the name of D-560 was 0 px wide in a 12 px button)', () => {
  const reading = read(box(NAME, 0, 787, { tag: 'span', className: 'name' }));
  assert.equal(reading.count, 1);
  assert.equal(reading.hits[0].width, 0);
  assert.equal(read(box(NAME, 0, 787, { display: 'none' })).count, 0, 'a box that is not drawn is not read, whatever its rectangle says');
  assert.equal(read(box(NAME, 0, 787, { display: 'contents' })).count, 0, '`display: contents` has no box of its own');
  assert.equal(read(box(NAME, 0, 20)).count, 0, 'an empty-looking zero-width box one line tall is not a column');
});

test('D-565: a narrow cell of one line in a tall row is not squeezed, its text is the measure (the box is as tall as the row)', () => {
  const cell = box('версия 1.2.0', 87, 83, { tag: 'td', textHeight: 19 });
  assert.equal(read(cell).count, 0, 'twelve characters on one line in 87 px, in a row of 83 px because of a neighbour');
  const squeezed = box('версия 1.2.0 и ещё слова', 58, 107, { tag: 'td', textHeight: 107 });
  assert.equal(read(squeezed).count, 1, 'the same cell with its text broken into six lines');
});
