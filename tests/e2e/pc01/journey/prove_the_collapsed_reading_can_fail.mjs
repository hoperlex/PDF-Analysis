#!/usr/bin/env node
/**
 * The proof that `D-565`'s collapsed-column reading can go red on a live page, where the width assertion stays green.
 *
 *     node tests/e2e/pc01/journey/prove_the_collapsed_reading_can_fail.mjs --origin http://127.0.0.1:PORT
 *
 * **What it mutates.** `D-560`: «Главная» put the tasks and the section table side by side from 1280 px, and the section table's
 * name button was 12 px wide (its name box 0 px) while the page grew taller instead of wider. `home-page.module.css` now keeps one
 * column below 1680 px; this puts the old two-track rule back on the live page (an injected `<style>` on `.overviewGrid`, whose
 * hashed class is matched by its module's prefix) and requires, over the journey's own modules (`width.mjs`):
 *
 *   1. before the injection: the reading finds nothing and the width assertion finds nothing;
 *   2. after it: the width assertion STILL finds nothing (`scrollWidth <= innerWidth`: the page is no wider), and the collapsed-column
 *      reading finds the name boxes and says so in one finding.
 *
 * The page must hold at least one project with a classified document (the sections table has rows only then): run it against a stand
 * after the write half. It imports `measureWidth`, `widthFindings`, `measureCollapsed` and `collapsedFindings` from `width.mjs`
 * unchanged (`OPERATING_CONSTRAINTS.md` section 12: a proof written against a second copy of the reading proves nothing about the first).
 *
 * Exit `0` means: green before, blind width assertion after, red collapsed reading after. Anything else is a failure with its numbers.
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';
import { openSession } from './session.mjs';
import { collapsedFindings, measureCollapsed, measureWidth, widthFindings } from './width.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const WIDTH = 1280;
const HEIGHT = 900;
const OLD_RULE =
  '[class*="home-page_overviewGrid"]{grid-template-columns:minmax(300px,0.85fr) minmax(0,1.15fr) !important}';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 || i === process.argv.length - 1 ? fallback : process.argv[i + 1];
}

const ORIGIN = (arg('origin') ?? process.env.E2E_PC01_ORIGIN ?? '').replace(/\/+$/, '');
if (!ORIGIN) {
  console.error('prove_the_collapsed_reading_can_fail: no origin.\n\n  node tests/e2e/pc01/journey/prove_the_collapsed_reading_can_fail.mjs --origin http://127.0.0.1:PORT\n');
  process.exit(2);
}

const manifest = JSON.parse(readFileSync(join(HERE, 'manifest.json'), 'utf8'));
const session = await openSession({ origin: ORIGIN, manifest });
if (!session.ok) {
  console.error('prove_the_collapsed_reading_can_fail: could not sign in:\n');
  for (const f of session.failures) console.error(`  - ${f}`);
  process.exit(1);
}

const declared = { width: WIDTH, height: HEIGHT, requested: true };
const result = await withColdBrowser(
  async (page) => {
    await page.goto(`${ORIGIN}/`);
    const rows = await page.evaluate("document.querySelectorAll('li[data-section]').length");
    const before = { width: await measureWidth(page), collapsed: await measureCollapsed(page) };
    await page.evaluate(`(() => { const s = document.createElement('style'); s.textContent = ${JSON.stringify(OLD_RULE)}; document.head.appendChild(s); return true; })()`);
    await new Promise((resolve) => setTimeout(resolve, 300));
    const after = { width: await measureWidth(page), collapsed: await measureCollapsed(page) };
    return { rows, before, after };
  },
  { cookies: session.cookies, viewport: { width: WIDTH, height: HEIGHT } },
);

const problems = [];
if (result.rows === 0) problems.push('«Главная» shows no section rows: the stand holds no classified document, so there is nothing to squeeze');
const widthBefore = widthFindings('root', result.before.width, declared);
const widthAfter = widthFindings('root', result.after.width, declared);
const collapsedBefore = collapsedFindings('root', result.before.collapsed, declared);
const collapsedAfter = collapsedFindings('root', result.after.collapsed, declared);
if (widthBefore.length > 0 || collapsedBefore.length > 0) problems.push(`not green before the injection: ${[...widthBefore, ...collapsedBefore].join(' | ').slice(0, 400)}`);
if (widthAfter.length > 0) problems.push(`the width assertion went red after the injection (scrollWidth ${result.after.width.scrollWidth} > ${result.after.width.innerWidth}): the old layout is not the blind case this proves`);
if (collapsedAfter.length !== 1) problems.push(`the collapsed-column reading gave ${collapsedAfter.length} findings after the injection and not one`);

console.log(`rows ${result.rows}; before: scrollWidth ${result.before.width.scrollWidth}/${result.before.width.innerWidth}, collapsed boxes ${result.before.collapsed.count}`);
console.log(`after the old two-track rule: scrollWidth ${result.after.width.scrollWidth}/${result.after.width.innerWidth} (width findings ${widthAfter.length}), collapsed boxes ${result.after.collapsed.count}`);
if (collapsedAfter[0]) console.log(`  ${collapsedAfter[0].slice(0, 360)}`);
if (problems.length > 0) {
  console.error('\nprove_the_collapsed_reading_can_fail: FAILED\n');
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log('\nprove_the_collapsed_reading_can_fail: the reading is green before, red after, and the width assertion is blind to the same page.');
