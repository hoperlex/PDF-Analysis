#!/usr/bin/env node
/**
 * Open «Блоки» for one version in a cold browser, press «Показать ещё» until every block is
 * loaded, and measure what that costs. W55B-REHEARSAL-01.
 *
 *   E2E_PC01_CHROME=<chrome> REHEARSAL_LOGIN=... REHEARSAL_PASSWORD=... \
 *   node scripts/rehearsal/w55b/browser_blocks.mjs --origin http://127.0.0.1:31680 \
 *     --project-name NAME --version-uid V --phase NAME [--crops all|sample:N|none] [--counts-only]
 *
 * Reuses the journey's own instruments (`tests/e2e/pc01/journey/cdp.mjs`, `session.mjs`): a
 * sign-in through the real screen, then one cold browser carrying exactly that session cookie.
 * The chooser is driven by its own controls («Выбрать проект», «Показать блоки»); the portal tab
 * opens on its own. Each press of «Показать ещё» is timed until the screen's own counter
 * (`data-portal-blocks-loaded`) moves and two animation frames have passed; after each press the
 * DOM's element count, the page's JS heap and the resident memory of the browser's process tree
 * (every descendant of this Node process, read from /proc) are recorded.
 *
 * At the end the screen is checked against the version: every block once, none repeated (each
 * page section's blocks, the crops' distinct addresses), the counter equal to `block_count`.
 * `--crops` scrolls crops into view so the lazy `<img>`s load, and counts the ones that loaded,
 * failed or never finished. `--counts-only` (the owner's real export, F-7) keeps nothing but
 * numbers in the output: no title, no identifier, no text.
 *
 * Output: `.local/rehearsal-w55b/figures/<phase>.json`. Nothing is written anywhere else.
 */

import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from '../../../tests/e2e/pc01/journey/cdp.mjs';
import { openSession } from '../../../tests/e2e/pc01/journey/session.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../../..');
const OUT = join(ROOT, '.local', 'rehearsal-w55b', 'figures');
const LANE_WEB_PORT = 31680;

function argument(name, fallback = null) {
  const at = process.argv.indexOf(`--${name}`);
  if (at < 0) return fallback;
  return process.argv[at + 1];
}

const origin = argument('origin', `http://127.0.0.1:${LANE_WEB_PORT}`);
const projectName = argument('project-name');
const versionUid = argument('version-uid');
const phase = argument('phase');
const cropsMode = argument('crops', 'none');
const countsOnly = process.argv.includes('--counts-only');
const pressBoundMs = Number(argument('press-bound-ms', '180000'));

{
  const url = new URL(origin);
  if (!['127.0.0.1', 'localhost'].includes(url.hostname) || Number(url.port) !== LANE_WEB_PORT) {
    throw new Error(`refusing origin ${origin}: only this lane's loopback web port ${LANE_WEB_PORT}`);
  }
  if (!projectName || !versionUid || !phase) {
    throw new Error('--project-name, --version-uid and --phase are required');
  }
}

function context() {
  const meminfo = readFileSync('/proc/meminfo', 'utf8');
  const available = Number(/MemAvailable:\s+(\d+)/.exec(meminfo)[1]);
  const head = execFileSync('git', ['-C', ROOT, 'rev-parse', 'HEAD']).toString().trim();
  const dirty = execFileSync('git', ['-C', ROOT, 'status', '--porcelain', '-uall']).toString().trim();
  return {
    at_utc: new Date().toISOString(),
    tree: { head, clean: dirty === '' },
    loadavg: readFileSync('/proc/loadavg', 'utf8').split(' ').slice(0, 3),
    mem_available_kib: available,
  };
}

/** Resident memory of every descendant of this process: the browser and its renderers. */
function browserTreeRssKib() {
  const parents = new Map();
  const rss = new Map();
  for (const name of readdirSync('/proc')) {
    if (!/^\d+$/.test(name)) continue;
    try {
      const status = readFileSync(`/proc/${name}/status`, 'utf8');
      parents.set(Number(name), Number(/PPid:\s+(\d+)/.exec(status)[1]));
      const match = /VmRSS:\s+(\d+)/.exec(status);
      rss.set(Number(name), match ? Number(match[1]) : 0);
    } catch {
      /* gone */
    }
  }
  const mine = new Set([process.pid]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const [pid, parent] of parents) {
      if (!mine.has(pid) && mine.has(parent)) {
        mine.add(pid);
        grew = true;
      }
    }
  }
  mine.delete(process.pid);
  let total = 0;
  for (const pid of mine) total += rss.get(pid) ?? 0;
  return { processes: mine.size, rss_kib: total };
}

const COUNTER = `(() => {
  const el = document.querySelector('[data-portal-blocks-loaded]');
  return el === null ? null : Number(el.getAttribute('data-portal-blocks-loaded'));
})()`;

const FRAMES = `new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(() => done(true))))`;

const COST = `(() => ({
  dom_elements: document.getElementsByTagName('*').length,
  js_heap_used_bytes: performance.memory ? performance.memory.usedJSHeapSize : null,
  articles: document.querySelectorAll('article[data-portal-block-type]').length,
}))()`;

function pickButton(itemTest, buttonText) {
  return `(() => {
    document.querySelectorAll('[data-rehearsal-pick]').forEach((e) => e.removeAttribute('data-rehearsal-pick'));
    for (const li of document.querySelectorAll('li.am-state')) {
      if (!(${itemTest})(li)) continue;
      const button = Array.from(li.querySelectorAll('button')).find((b) => b.innerText.trim() === ${JSON.stringify(buttonText)});
      if (button) { button.setAttribute('data-rehearsal-pick', '1'); return true; }
    }
    return null;
  })()`;
}

async function main() {
  const manifest = JSON.parse(readFileSync(join(ROOT, 'tests/e2e/pc01/journey/manifest.json'), 'utf8'));
  const login = process.env.REHEARSAL_LOGIN;
  const password = process.env.REHEARSAL_PASSWORD;
  if (!login || !password) throw new Error('REHEARSAL_LOGIN and REHEARSAL_PASSWORD come from the environment');
  const session = await openSession({ origin, manifest, credentials: { login, password } });
  if (!session.ok) throw new Error(`sign-in failed: ${session.failures.join(' | ')}`);

  const result = await withColdBrowser(async (page) => {
    const out = { presses: [], findings: [] };
    const t0 = Date.now();
    await page.goto(`${origin}/blocks`);
    const projectReady = await page.waitFor(pickButton(
      `(li) => (li.querySelector('.am-state__title')?.innerText ?? '').trim() === ${JSON.stringify(projectName)}`,
      'Выбрать проект'), { boundMs: 60000, what: 'the project in the chooser' });
    if (!projectReady.ok) throw new Error('the project is not in the chooser');
    await page.click('[data-rehearsal-pick="1"]');
    const versionReady = await page.waitFor(pickButton(
      `(li) => (li.querySelector('code')?.innerText ?? '').trim() === ${JSON.stringify(versionUid)}`,
      'Показать блоки'), { boundMs: 60000, what: 'the version in the chooser' });
    if (!versionReady.ok) throw new Error('the version is not in the chooser');
    const chosenAt = Date.now();
    await page.click('[data-rehearsal-pick="1"]');
    const first = await page.waitFor(COUNTER, { boundMs: pressBoundMs, pollMs: 50, what: 'the first page of blocks' });
    if (!first.ok) throw new Error(`no portal blocks rendered within ${pressBoundMs} ms`);
    await page.evaluate(FRAMES);
    out.first_page_ms = Date.now() - chosenAt;
    out.block_count_shown = await page.evaluate(`Number(document.querySelector('[data-portal-block-count]').getAttribute('data-portal-block-count'))`);
    out.after_first = { loaded: first.value, ...(await page.evaluate(COST)), browser: browserTreeRssKib() };

    let loaded = first.value;
    for (;;) {
      const more = await page.describe('button', 'Показать ещё');
      if (more === null) break;
      const pressedAt = Date.now();
      await page.click('button', { text: 'Показать ещё' });
      const moved = await page.waitFor(`(() => { const n = ${COUNTER}; return n !== null && n > ${loaded} ? n : null; })()`,
        { boundMs: pressBoundMs, pollMs: 25, what: 'the counter to move' });
      if (!moved.ok) {
        out.findings.push(`press ${out.presses.length + 1}: the counter did not move within ${pressBoundMs} ms`);
        break;
      }
      await page.evaluate(FRAMES);
      const ms = Date.now() - pressedAt;
      loaded = moved.value;
      out.presses.push({ press: out.presses.length + 1, loaded, ms, ...(await page.evaluate(COST)), browser: browserTreeRssKib() });
      if (out.presses.length > 200) {
        out.findings.push('more than 200 presses: stopped');
        break;
      }
    }
    out.all_loaded_ms = Date.now() - chosenAt;
    out.loaded = loaded;

    // Every block once: per page section, and the crops' addresses.
    out.check = await page.evaluate(`(() => {
      const sections = Array.from(document.querySelectorAll('[data-portal-page]'));
      const pages = sections.map((s) => Number(s.getAttribute('data-portal-page')));
      const types = {};
      const perSection = [];
      for (const s of sections) {
        const kinds = Array.from(s.querySelectorAll('article[data-portal-block-type]')).map((a) => a.getAttribute('data-portal-block-type'));
        perSection.push(kinds.length);
        for (const k of kinds) types[k] = (types[k] ?? 0) + 1;
      }
      const imgs = Array.from(document.querySelectorAll('figure[data-portal-crop] img'));
      const srcs = new Set(imgs.map((i) => i.getAttribute('src')));
      return {
        sections: sections.length,
        distinct_page_numbers: new Set(pages).size,
        pages_in_order: pages.every((p, i) => i === 0 || pages[i - 1] < p),
        articles: document.querySelectorAll('article[data-portal-block-type]').length,
        by_type: types,
        blocks_per_section_min: Math.min(...perSection),
        blocks_per_section_max: Math.max(...perSection),
        crop_imgs: imgs.length,
        distinct_crop_addresses: srcs.size,
        recognised_texts: document.querySelectorAll('[data-quote-source]').length,
        descriptions: document.querySelectorAll('[data-portal-description]').length,
        mismatch_sentences: document.querySelectorAll('[data-geometry-mismatch]').length,
        still_offering_more: Array.from(document.querySelectorAll('button')).some((b) => b.innerText.trim() === 'Показать ещё'),
        horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    })()`);
    out.after_all = { ...(await page.evaluate(COST)), browser: browserTreeRssKib() };

    // Crops: scroll each chosen <img> into view and wait for it to finish.
    if (cropsMode !== 'none') {
      const total = out.check.crop_imgs;
      let chosen = [...Array(total).keys()];
      if (cropsMode.startsWith('sample:')) {
        const n = Number(cropsMode.slice(7));
        const half = Math.floor(n / 2);
        chosen = [...new Set([...chosen.slice(0, half), ...chosen.slice(Math.max(0, total - half))])];
      }
      const started = Date.now();
      const tally = { chosen: chosen.length, loaded: 0, failed: 0, unfinished: 0, slowest_ms: 0, natural_size_matches: 0 };
      for (const index of chosen) {
        const t = Date.now();
        await page.evaluate(`document.querySelectorAll('figure[data-portal-crop] img')[${index}]?.scrollIntoView({block: 'center'})`);
        const done = await page.waitFor(`(() => {
          const figure = document.querySelectorAll('figure[data-portal-crop]')[${index}];
          if (!figure) return 'gone';
          if (figure.getAttribute('data-portal-crop') === 'failed') return 'failed';
          const img = figure.querySelector('img');
          if (img && img.complete && img.naturalWidth > 0) {
            return img.naturalWidth === Number(img.getAttribute('width')) && img.naturalHeight === Number(img.getAttribute('height')) ? 'loaded:size' : 'loaded';
          }
          return null;
        })()`, { boundMs: 60000, pollMs: 50, what: `crop ${index}` });
        const ms = Date.now() - t;
        tally.slowest_ms = Math.max(tally.slowest_ms, ms);
        if (!done.ok) tally.unfinished += 1;
        else if (String(done.value).startsWith('loaded')) {
          tally.loaded += 1;
          if (done.value === 'loaded:size') tally.natural_size_matches += 1;
        } else tally.failed += 1;
      }
      tally.ms = Date.now() - started;
      out.crops = tally;
      out.after_crops = { ...(await page.evaluate(COST)), browser: browserTreeRssKib() };
    }
    out.console_errors = page.consoleErrors().length;
    out.page_errors = page.pageErrors().length;
    out.total_ms = Date.now() - t0;
    return out;
  }, { cookies: session.cookies, viewport: { width: 1280, height: 900 } });

  const expected = result.block_count_shown;
  const ok =
    result.findings.length === 0 &&
    result.loaded === expected &&
    result.check.articles === expected &&
    !result.check.still_offering_more &&
    result.check.distinct_crop_addresses === result.check.crop_imgs &&
    (result.crops === undefined || (result.crops.failed === 0 && result.crops.unfinished === 0));
  const document = {
    phase,
    context: context(),
    what: 'the «Блоки» tab of one version in a cold browser (1280 x 900), «Показать ещё» pressed to the end',
    counts_only: countsOnly,
    ok,
    ...result,
  };
  if (!countsOnly) {
    document.version_uid = versionUid;
  }
  mkdirSync(OUT, { recursive: true });
  writeFileSync(join(OUT, `${phase}.json`), JSON.stringify(document, null, 2) + '\n');
  const last = result.presses[result.presses.length - 1];
  console.log(
    `${phase}: ok=${ok}; ${result.loaded}/${expected} blocks after ${result.presses.length} presses; ` +
      `first page ${result.first_page_ms} ms; last press ${last ? last.ms : '-'} ms; all ${result.all_loaded_ms} ms; ` +
      `DOM ${result.after_all.dom_elements} elements; heap ${result.after_all.js_heap_used_bytes}; ` +
      `browser RSS ${result.after_all.browser.rss_kib} KiB; crops ${JSON.stringify(result.crops ?? null)}`,
  );
  process.exitCode = ok ? 0 : 1;
}

await main();
