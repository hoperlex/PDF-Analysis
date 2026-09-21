/**
 * Proof that `Page.screenshot` photographs **this page**, at the size it was asked for.
 *
 * `D-55` was opened because the instrument could not screenshot at all. The repair is
 * eight lines, and eight lines that write a file are exactly the shape of change that gets
 * believed without being watched: a `screenshot()` that wrote a fixed blank PNG would pass
 * every check anyone would think to run on it -- the file exists, it is a PNG, it is not
 * empty -- while seeing nothing.
 *
 * So this asserts in both directions, the same discipline the guards in `web/tests` carry:
 *
 *   1. the capture is the size that was asked for, and the pixels are the colour the page
 *      was painted -- decoded, not merely non-zero;
 *   2. **repainting the page changes the bytes.** A photograph that does not change when
 *      its subject changes is not a photograph of its subject;
 *   3. `fullPage` captures past the viewport, so a document twice the window's height
 *      comes back at the document's height and not the window's.
 *
 * It needs a Chromium binary and nothing else -- no origin, no port, no stack, no built
 * web image -- so it runs anywhere the journey could run and costs about two seconds:
 *
 *     node tests/e2e/pc01/journey/prove_the_screenshot_sees.mjs
 *
 * It is not in `make gate` for the same reason the journey is not: the gate is stack-free
 * and a browser is an environment prerequisite. `tests/e2e/test_pc01_journey_conformance.py`
 * is what fails inside the gate when the method this proves stops existing.
 */

import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { inflateSync } from 'node:zlib';

import { withColdBrowser } from './cdp.mjs';

const W = 400;
const H = 300;

/** A page painted one flat colour, with no external resource of any kind. */
function solid(colour, heightCss = '100vh') {
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;padding:0}
    body{background:${colour};height:${heightCss}}
  </style></head><body></body></html>`;
  return 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
}

/** `width`, `height` out of the PNG's IHDR. Bytes 16..24, big-endian, by the spec. */
function pngSize(buffer) {
  if (buffer.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') {
    throw new Error('not a PNG: the signature is wrong');
  }
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

/**
 * The RGB of one pixel, decoded properly.
 *
 * Reading a raw byte out of an IDAT would be reading compressed data and calling it a
 * colour. Chromium picks its own filters per row, so the row filters have to be undone --
 * all five of them -- or the "colour" this returns is whatever the filter happened to
 * leave, which would make the check agree with a wrong answer.
 */
function pixel(buffer, px, py) {
  const { width } = pngSize(buffer);
  const depth = buffer[24];
  const colourType = buffer[25];
  if (depth !== 8 || (colourType !== 2 && colourType !== 6)) {
    throw new Error(`unsupported PNG: depth ${depth}, colour type ${colourType}`);
  }
  const bpp = colourType === 6 ? 4 : 3;
  const stride = width * bpp;

  const idat = [];
  for (let off = 8; off + 8 <= buffer.length; ) {
    const length = buffer.readUInt32BE(off);
    const type = buffer.subarray(off + 4, off + 8).toString('ascii');
    if (type === 'IDAT') idat.push(buffer.subarray(off + 8, off + 8 + length));
    off += 12 + length;
    if (type === 'IEND') break;
  }
  const raw = inflateSync(Buffer.concat(idat));

  let prior = Buffer.alloc(stride);
  let row = Buffer.alloc(stride);
  for (let y = 0; y <= py; y += 1) {
    const filter = raw[y * (stride + 1)];
    const line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    row = Buffer.alloc(stride);
    for (let i = 0; i < stride; i += 1) {
      const a = i >= bpp ? row[i - bpp] : 0;
      const b = prior[i];
      const c = i >= bpp ? prior[i - bpp] : 0;
      let value;
      if (filter === 0) value = line[i];
      else if (filter === 1) value = line[i] + a;
      else if (filter === 2) value = line[i] + b;
      else if (filter === 3) value = line[i] + ((a + b) >> 1);
      else if (filter === 4) {
        const p = a + b - c;
        const pa = Math.abs(p - a);
        const pb = Math.abs(p - b);
        const pc = Math.abs(p - c);
        value = line[i] + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c);
      } else throw new Error(`unknown PNG row filter ${filter}`);
      row[i] = value & 0xff;
    }
    prior = row;
  }
  return [row[px * bpp], row[px * bpp + 1], row[px * bpp + 2]];
}

const failures = [];
function check(claim, condition, detail) {
  console.log(`${condition ? 'ok   ' : 'FAIL '} ${claim}${detail ? `  -- ${detail}` : ''}`);
  if (!condition) failures.push(claim);
}

const dir = mkdtempSync(join(tmpdir(), 'w32see-shot-'));
try {
  const red = await withColdBrowser(async (page) => {
    await page.goto(solid('#ff0000'));
    return readFileSync(await page.screenshot(join(dir, 'red.png'), { width: W, height: H }));
  });
  const blue = await withColdBrowser(async (page) => {
    await page.goto(solid('#0000ff'));
    return readFileSync(await page.screenshot(join(dir, 'blue.png'), { width: W, height: H }));
  });
  const tall = await withColdBrowser(async (page) => {
    await page.goto(solid('#00ff00', '600px'));
    return readFileSync(
      await page.screenshot(join(dir, 'tall.png'), { fullPage: true, width: W, height: H }),
    );
  });

  const redSize = pngSize(red);
  check(
    'the capture is the viewport it was asked for',
    redSize.width === W && redSize.height === H,
    `${redSize.width}x${redSize.height}, wanted ${W}x${H}`,
  );

  const redPx = pixel(red, 10, 10);
  const bluePx = pixel(blue, 10, 10);
  check('a red page photographs red', redPx.join(',') === '255,0,0', `rgb(${redPx})`);
  check('a blue page photographs blue', bluePx.join(',') === '0,0,255', `rgb(${bluePx})`);
  check(
    'repainting the page changes the bytes',
    !red.equals(blue),
    `${red.length} vs ${blue.length} bytes`,
  );

  // The height is asserted against the CSS this file wrote -- `height:600px` -- and not
  // against anything `screenshot()` computed, so the check cannot agree with a wrong
  // answer by sharing its arithmetic (`OPERATING_CONSTRAINTS.md` §12).
  const tallSize = pngSize(tall);
  check(
    'fullPage captures the document height the CSS declared',
    tallSize.height === 600,
    `${tallSize.width}x${tallSize.height}, viewport was ${W}x${H}`,
  );
  // The claim that matters, and the one a height alone does not make: a row that is below
  // the viewport is in the photograph, painted. A capture that merely padded to 600 would
  // pass the height check and fail this one.
  const belowTheFold = pixel(tall, 10, 500);
  check(
    'a row below the viewport is in the photograph, and painted',
    belowTheFold.join(',') === '0,255,0',
    `rgb(${belowTheFold}) at y=500, viewport height ${H}`,
  );
  // Stated rather than discovered later: the content box excludes the scrollbar the taller
  // document brings, so a full-page capture is narrower than the viewport by exactly its
  // width. This is Chromium's `cssContentSize` and DevTools' own full-size capture behaves
  // the same way. Asserted so that a change in it is visible rather than silent.
  check(
    'a full-page capture is narrower than the viewport by the scrollbar, and no more',
    tallSize.width < W && W - tallSize.width <= 20,
    `${tallSize.width} vs viewport ${W}: ${W - tallSize.width}px of scrollbar`,
  );
} finally {
  rmSync(dir, { recursive: true, force: true });
}

if (failures.length > 0) {
  console.error(`\n${failures.length} claim(s) about the screenshot are false.`);
  process.exit(1);
}
console.log('\nthe screenshot sees the page.');
