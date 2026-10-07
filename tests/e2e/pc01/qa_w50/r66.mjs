/**
 * `W50-QA-01`, the `R-66` item (stand half) — the menu each complete-profile account kind sees
 * in the built frame, `/optimisation` opening for it, and the four stubs as rendered.
 *
 *     TMPDIR=<own dir> QA_W50_ACCOUNTS=<0600 file> E2E_PC01_CHROME=<chrome> \
 *       node tests/e2e/pc01/qa_w50/r66.mjs --origin http://127.0.0.1:PORT
 *
 * Kinds read: `admin` (admin + expert), `expert`, `none` (`roles: []`) — every one with a
 * changed password and a complete profile. The expectation is typed from the ruling.
 *
 * Written by QA from the ruling, without the lane reports.
 */

import { parseArgs, recorder, signIn, withColdBrowser } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const ORIGIN = args.origin;

const RULED = [
  ['/', 'Главная'],
  ['Работа', [['/projects', 'Проекты'], ['/dashboard', 'Дашборд'], ['/section-optimisation', 'Оптимизация разделов']]],
  ['Знания', [['/knowledge-base', 'База знаний'], ['/blocks', 'Блоки'], ['/norms', 'Нормы']]],
  [
    'Система',
    [['/logs', 'Журнал выполнения'], ['/workers', 'Исполнители'], ['/analysis-settings', 'Настройки анализа'], ['/queue', 'Очередь']],
  ],
];

const READ_ROW = `(() => {
  const row = document.querySelector('[data-nav-state="row"]');
  if (row === null) return null;
  const out = [];
  for (const child of row.children) {
    if (child.tagName === 'A') { out.push([child.getAttribute('href'), child.innerText.trim()]); continue; }
    const button = child.querySelector('button.am-disclosure__button');
    const links = Array.from(child.querySelectorAll('a')).map((a) => [a.getAttribute('href'), a.textContent.trim()]);
    out.push([button === null ? null : button.innerText.trim(), links]);
  }
  return out;
})()`;

const MAIN_TEXT = "(document.querySelector('main')?.innerText ?? '').trim()";

const r = recorder('R-66');

for (const kind of ['admin', 'expert', 'none']) {
  const session = await signIn(ORIGIN, kind);
  r.check(`${kind}: signs in and lands on /`, '/', session.landedOn);
  await withColdBrowser(
    async (page) => {
      await page.goto(`${ORIGIN}/`);
      r.check(`${kind}: the one-row menu at 1280, in order`, RULED, await page.evaluate(READ_ROW));
      r.check(
        `${kind}: no link to /optimisation anywhere in the frame`,
        0,
        await page.evaluate(`document.querySelectorAll('header a[href="/optimisation"]').length`),
      );
      await page.goto(`${ORIGIN}/optimisation`);
      r.check(`${kind}: /optimisation opens`, '/optimisation', await page.location());
      const text = await page.evaluate(MAIN_TEXT);
      r.check(`${kind}: /optimisation renders a screen, not the sign-in or a refusal`, true,
        text.length > 0 && !text.includes('Войти') && !text.includes('Доступ закрыт'));
      r.note(`${kind}: /optimisation first line`, text.split('\n')[0]);
      for (const stub of ['/section-optimisation', '/norms', '/analysis-settings', '/queue']) {
        const before = page.exchanges().length;
        await page.goto(`${ORIGIN}${stub}`);
        const body = await page.evaluate(MAIN_TEXT);
        const calls = page
          .exchanges()
          .slice(before)
          .filter((e) => {
            try {
              return new URL(e.url).pathname.startsWith('/bff/v1/');
            } catch {
              return false;
            }
          })
          .map((e) => `${e.method} ${new URL(e.url).pathname}`);
        r.check(`${kind}: ${stub} opens, says it is not ready, shows no digit and calls no API`,
          { at: stub, notReady: true, digits: null, calls: [] },
          {
            at: await page.location(),
            notReady: body.includes('Этот раздел ещё не готов.') && body.includes('Раздел пока недоступен'),
            digits: body.match(/\d/g),
            calls,
          });
      }
      r.note(`${kind}: page errors`, page.pageErrors());
    },
    { cookies: session.cookies, viewport: { width: 1280, height: 900 } },
  );
}

const failed = r.failed();
console.log(`\n${failed.length === 0 ? 'R-66 OK' : `R-66 FAILED: ${failed.length}`}`);
process.exit(failed.length === 0 ? 0 : 1);
