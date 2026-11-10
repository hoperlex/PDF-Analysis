#!/usr/bin/env node
/**
 * The CSS lab (`D-619`; the generic form of lane WALK-V5's knowledge-base lab): candidate CSS injected into the LIVE page of one
 * route, at several widths, and the page measured with the journey's own readings. It changes nothing in the tree and nothing on
 * the stand: the stylesheet lives in the page until the browser (a cold one per width and variant) is torn down.
 *
 *     node tests/e2e/pc01/journey/lab.mjs --origin http://127.0.0.1:PORT --journey <journey.json of a read walk> --route knowledge-base \
 *          --variants variants.json [--widths 360,768,1280] [--selector 'tbody tr'] [--out result.json]
 *
 * `variants.json` is `{ "committed": null, "lower": "[class*=\"x_col\"]{min-width:5rem !important}" }`: `null` is the page as it is (always
 * include it: a number with no control beside it measures nothing). `--journey` supplies the route's concrete address (the envelope's
 * `records[].url`, captured identities included), so the lab reads the same screen the walk read. The sign-in is the journey's own
 * (`E2E_PC01_LOGIN` / `E2E_PC01_PASSWORD`, `session.mjs`).
 *
 * Per width and variant it prints and records: the page height, the width reading (`scrollWidth` against `innerWidth`), the collapsed-column
 * count (`width.mjs`), and, with `--selector`, the box (width, height) of up to 20 matches, so a candidate floor can be read off the row
 * heights it produces. A candidate is for the owner of the stylesheet to take; the lab proposes nothing.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';
import { parseVariants, styleInjection } from './readings.mjs';
import { openSession } from './session.mjs';
import { measureCollapsed, measureWidth } from './width.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(name);
  return i < 0 || i === process.argv.length - 1 ? fallback : process.argv[i + 1];
};
const usage = (why) => {
  console.error(`lab: ${why}\n\n  node tests/e2e/pc01/journey/lab.mjs --origin O --journey <journey.json> --route <name> --variants <file.json> [--widths 360,768,1280] [--selector CSS] [--out file]`);
  process.exit(2);
};

const origin = (arg('--origin') ?? process.env.E2E_PC01_ORIGIN ?? '').replace(/\/+$/, '');
if (!origin) usage('no origin');
if (arg('--journey') === null || arg('--route') === null || arg('--variants') === null) usage('--journey, --route and --variants are required');
const widths = arg('--widths', '360,768,1024,1280').split(',').map(Number);
if (widths.some((w) => !Number.isInteger(w) || w < 240 || w > 3840)) usage('--widths must be whole numbers of pixels between 240 and 3840');

let variants;
try {
  variants = parseVariants(readFileSync(arg('--variants'), 'utf8'));
} catch (error) {
  usage(error.message);
}
const envelope = JSON.parse(readFileSync(arg('--journey'), 'utf8'));
const record = (envelope.records ?? []).find((r) => r.name === arg('--route'));
if (!record?.url) usage(`the envelope holds no route '${arg('--route')}' with an address`);
const path = record.url.replace(/^https?:\/\/[^/]+/, '');
const selector = arg('--selector');
const manifest = JSON.parse(readFileSync(join(HERE, 'manifest.json'), 'utf8'));

const session = await openSession({ origin, manifest });
if (!session.ok) {
  console.error('lab: sign-in failed', session.failures);
  process.exit(1);
}

const MEASURE = `(() => {
  const doc = document.documentElement;
  const selector = ${JSON.stringify(selector)};
  const boxes = selector === null ? [] : Array.from(document.querySelectorAll(selector)).slice(0, 20).map((el) => {
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  });
  return { docHeight: doc.scrollHeight, boxes };
})()`;

const out = [];
for (const width of widths) {
  for (const [name, css] of variants) {
    const reading = await withColdBrowser(
      async (page) => {
        await page.goto(origin + path);
        if (css !== null) {
          await page.evaluate(styleInjection(css));
          await new Promise((resolve) => setTimeout(resolve, 300));
        }
        return { page: await page.evaluate(MEASURE), width: await measureWidth(page), collapsed: await measureCollapsed(page) };
      },
      { cookies: session.cookies, viewport: { width, height: width <= 480 ? 844 : 900 } },
    );
    const row = {
      width,
      variant: name,
      docHeight: reading.page.docHeight,
      scrollWidth: reading.width.scrollWidth,
      innerWidth: reading.width.innerWidth,
      collapsed: reading.collapsed.count,
      boxes: reading.page.boxes,
    };
    out.push(row);
    console.log(
      `${String(width).padStart(5)} ${name.padEnd(12)} height ${row.docHeight} width ${row.scrollWidth}/${row.innerWidth} collapsed ${row.collapsed}` +
        `${selector ? ` boxes ${row.boxes.map((b) => `${b.w}x${b.h}`).join(' ')}` : ''}`,
    );
  }
}
if (arg('--out') !== null) writeFileSync(arg('--out'), JSON.stringify({ origin, route: arg('--route'), path, selector, results: out }, null, 1));
