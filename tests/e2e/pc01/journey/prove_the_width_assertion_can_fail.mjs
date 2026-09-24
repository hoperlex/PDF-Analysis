#!/usr/bin/env node
/**
 * The proof that `D-93`'s width assertion can go red.
 *
 *     node tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs \
 *       --origin http://127.0.0.1:31500
 *
 * **Why it exists.** A width assertion nobody has watched fail is a width assertion
 * nobody can trust -- the same reason `prove_the_guard_can_fail.py` mutates the real
 * manifest ten ways and `prove_the_screenshot_sees.mjs` decodes the PNG. Wave 43's four
 * navigation links moved the overflow threshold from **482 px to 839 px** and 1085
 * frontend tests could not see it; this is the thing that would have.
 *
 * **What it mutates.** `web/src/app/globals.css` declares `flex-wrap: wrap` on
 * `.am-app__bar`, once, as wave 43's repair. This restores what the bar had before that
 * repair, on the screen, and requires the journey's own assertion to redden.
 *
 * **Why a scratch copy and an injected rule are the same mutation here, proved rather
 * than asserted.** The deployed stand is read-only to this session: its image was built
 * from the repaired tree and cannot be rebuilt to carry the defect. So the probe does
 * both halves and joins them:
 *
 *   1. it writes a **scratch copy** of `globals.css` with that one declaration removed,
 *      and checks the copy's `.am-app__bar` block then declares no `flex-wrap` at all;
 *   2. `nowrap` is `flex-wrap`'s initial value, so a block declaring none computes to
 *      `nowrap` -- and the probe **reads the computed style back off the live bar**
 *      before and after injecting, requiring `wrap` then `nowrap`. The two halves meet at
 *      a computed value, which is what the browser lays out from.
 *
 * Nothing in the repository is modified. The copy is written under the system temp
 * directory and removed.
 *
 * **It imports the journey's own assertion.** `OPERATING_CONSTRAINTS.md` §12: a query
 * that shares an assumption with its subject is not a measurement, and a proof written to
 * agree with a second copy of the assertion proves nothing about the first.
 * `measureWidth` and `widthFindings` come from `width.mjs`, unchanged.
 *
 * Exit `0` means: every route measured was **green before** the mutation and **red
 * after** it, and the finding named the bar. Anything else is a failure with its numbers.
 */

import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';
import { openSession } from './session.mjs';
import { measureWidth, widthFindings } from './width.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..', '..');
const STYLESHEET = resolve(REPO, 'web', 'src', 'app', 'globals.css');
const SELECTOR = '.am-app__bar';
const DECLARATION = 'flex-wrap: wrap;';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 || i === process.argv.length - 1 ? fallback : process.argv[i + 1];
}

const ORIGIN = (arg('origin') ?? process.env.E2E_PC01_ORIGIN ?? '').replace(/\/+$/, '');
if (!ORIGIN) {
  console.error(
    'prove_the_width_assertion_can_fail: no origin.\n\n' +
      '  node tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs \\\n' +
      '    --origin http://127.0.0.1:PORT\n',
  );
  process.exit(2);
}

const manifest = JSON.parse(readFileSync(join(HERE, 'manifest.json'), 'utf8'));
const VIEWPORT = { width: manifest.viewport.width, height: manifest.viewport.height };

/**
 * The `.am-app__bar { ... }` block, from a stylesheet's text.
 *
 * Deliberately naive -- one selector, one brace pair -- because the thing it must not do
 * is silently match a different block and report about it. It fails loudly instead.
 */
function blockFor(css, selector) {
  const at = css.indexOf(`${selector} {`);
  if (at === -1) throw new Error(`${selector} is not declared in ${STYLESHEET}`);
  const open = css.indexOf('{', at);
  const close = css.indexOf('}', open);
  if (close === -1) throw new Error(`${selector}'s block is not closed`);
  return { start: at, open, close, text: css.slice(open, close + 1) };
}

// ---- half one: the scratch copy ------------------------------------------------------
const original = readFileSync(STYLESHEET, 'utf8');
const beforeBlock = blockFor(original, SELECTOR);
if (!beforeBlock.text.includes(DECLARATION)) {
  console.error(
    `prove_the_width_assertion_can_fail: ${SELECTOR} no longer declares ` +
      `'${DECLARATION}'. This probe reverts wave 43's repair, and there is nothing here ` +
      'to revert. If the repair moved, this probe has to move with it.',
  );
  process.exit(2);
}
const occurrences = beforeBlock.text.split(DECLARATION).length - 1;
if (occurrences !== 1) {
  console.error(
    `prove_the_width_assertion_can_fail: ${SELECTOR} declares '${DECLARATION}' ` +
      `${occurrences} times; this probe removes exactly one.`,
  );
  process.exit(2);
}

const scratchDir = mkdtempSync(join(tmpdir(), 'w44-journey-width-'));
const scratchSheet = join(scratchDir, 'globals.reverted.css');
const reverted =
  original.slice(0, beforeBlock.open) +
  beforeBlock.text.replace(DECLARATION, '') +
  original.slice(beforeBlock.close + 1);
writeFileSync(scratchSheet, reverted);
const afterBlock = blockFor(reverted, SELECTOR);
const scratchDeclaresNoWrap = !/(^|[\s;{])flex-wrap\s*:/.test(afterBlock.text);

console.log('scratch copy:', scratchSheet);
console.log(
  `  ${SELECTOR} in the repository declares '${DECLARATION}'; the copy declares ` +
    `${scratchDeclaresNoWrap ? 'no flex-wrap at all' : 'a flex-wrap STILL'}`,
);
if (!scratchDeclaresNoWrap) {
  console.error(
    'prove_the_width_assertion_can_fail: removing the declaration left another ' +
      '`flex-wrap` on the same block, so the copy does not compute to `nowrap` and the ' +
      'injected rule below would not be the same mutation.',
  );
  rmSync(scratchDir, { recursive: true, force: true });
  process.exit(2);
}
console.log(
  "  `nowrap` is flex-wrap's initial value, so that block computes to `nowrap`. The " +
    'injection below is required to read back exactly that.\n',
);

// ---- half two: the live screens ------------------------------------------------------
const session = await openSession({ origin: ORIGIN, manifest });
if (!session.ok) {
  console.error('prove_the_width_assertion_can_fail: could not sign in:\n');
  for (const f of session.failures) console.error(`  - ${f}`);
  rmSync(scratchDir, { recursive: true, force: true });
  process.exit(1);
}

/**
 * The routes this probe can open on its own.
 *
 * Every route whose path carries no `{identifier}`, because those are reached only by
 * following the walk's own links and this probe is not the walk. `AppFrame` is global, so
 * the bar is on all of them -- which is the half of `D-93` that made four links a
 * product-wide regression rather than a regression on five screens.
 */
const ROUTES = manifest.routes.filter((route) => !route.path.includes('{'));
const only = arg('route');
const chosen = only === null ? ROUTES : ROUTES.filter((r) => r.name === only);
if (chosen.length === 0) {
  console.error(`prove_the_width_assertion_can_fail: no route named '${only}'`);
  rmSync(scratchDir, { recursive: true, force: true });
  process.exit(2);
}

const INJECT = `(() => {
  const bar = document.querySelector(${JSON.stringify(SELECTOR)});
  if (bar === null) return { ok: false, why: 'no ${SELECTOR} on this screen' };
  const before = getComputedStyle(bar).flexWrap;
  const style = document.createElement('style');
  style.setAttribute('data-w44-journey-probe', 'revert-am-app-bar-flex-wrap');
  style.textContent = ${JSON.stringify(`${SELECTOR} { flex-wrap: nowrap; }`)};
  document.head.appendChild(style);
  return { ok: true, before, after: getComputedStyle(bar).flexWrap };
})()`;

const findings = [];
const table = [];

for (const route of chosen) {
  const url = ORIGIN + route.path;
  const row = await withColdBrowser(
    async (page) => {
      await page.goto(url);
      const before = await measureWidth(page);
      const applied = await page.evaluate(INJECT);
      if (!applied.ok) return { name: route.name, url, before, applied, after: null };
      const after = await measureWidth(page);
      return { name: route.name, url, before, applied, after };
    },
    { cookies: session.cookies, viewport: VIEWPORT },
  );

  const greenBefore = widthFindings(row.name, row.before, manifest.viewport);
  const redAfter =
    row.after === null ? [] : widthFindings(row.name, row.after, manifest.viewport);
  row.greenBefore = greenBefore;
  row.redAfter = redAfter;
  table.push(row);

  if (!row.applied.ok) {
    findings.push(`${route.name}: ${row.applied.why}, so nothing was reverted`);
    continue;
  }
  if (row.applied.before !== 'wrap') {
    findings.push(
      `${route.name}: the bar computed flex-wrap '${row.applied.before}' before the ` +
        "mutation and wave 43's repair is 'wrap'",
    );
  }
  if (row.applied.after !== 'nowrap') {
    findings.push(
      `${route.name}: the injection computed flex-wrap '${row.applied.after}' and the ` +
        "scratch copy computes 'nowrap', so the two are not the same mutation",
    );
  }
  if (greenBefore.length > 0) {
    findings.push(
      `${route.name}: the screen ALREADY overflows before the mutation, so this route ` +
        `proves nothing about the assertion: ${greenBefore[0]}`,
    );
  }
  if (redAfter.length === 0) {
    findings.push(
      `${route.name}: the assertion stayed GREEN with wave 43's bar restored. ` +
        `scrollWidth ${row.after?.scrollWidth} vs innerWidth ${row.after?.innerWidth}. ` +
        'A width assertion that does not redden for the defect it was written for is ' +
        'not an assertion.',
    );
  }

  console.log(
    `${redAfter.length > 0 && greenBefore.length === 0 ? 'ok  ' : 'RED '}` +
      `${route.name.padEnd(16)} ` +
      `before ${String(row.before.scrollWidth).padStart(4)}/${row.before.innerWidth} ` +
      `(${row.applied.before})  ->  ` +
      `after ${String(row.after?.scrollWidth ?? -1).padStart(4)}/${row.after?.innerWidth} ` +
      `(${row.applied.after})`,
  );
  if (redAfter.length > 0) console.log(`      ${redAfter[0]}`);
}

rmSync(scratchDir, { recursive: true, force: true });

console.log(
  `\nroutes measured: ${table.length}/${ROUTES.length} placeholder-free route(s) at ` +
    `${VIEWPORT.width}x${VIEWPORT.height}`,
);

if (findings.length > 0) {
  console.error(`\nprove_the_width_assertion_can_fail FAILED -- ${findings.length}:\n`);
  for (const f of findings) console.error(`  - ${f}`);
  process.exit(1);
}

console.log(
  `\nprove_the_width_assertion_can_fail OK -- every route was green at ` +
    `${VIEWPORT.width} px with the repair and red with it reverted. D-93's assertion ` +
    'has been seen failing.',
);
