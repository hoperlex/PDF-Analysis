/**
 * `W50-QA-01`, the `R-66` item (stand half) — the menu each complete-profile account kind sees
 * in the built frame, `/optimisation` opening for it, and the four screens that were stubs.
 *
 *     QA_W50_ACCOUNTS=<0600 file> E2E_PC01_CHROME=<chrome> \
 *       node tests/e2e/pc01/qa_w50/r66.mjs --origin http://127.0.0.1:PORT
 *
 * Kinds read: `admin` (admin + expert), `expert`, `none` (`roles: []`) — every one with a
 * changed password and a complete profile. The expectation is typed from the ruling.
 *
 * Written by QA from the ruling, without the lane reports.
 *
 * **`BETA-LIVE-JOURNEY-01` repaired it, 2026-10-21, because running it showed 19 of its checks
 * red against a tree whose expectations had moved on without it** (`D-186`). Three things had
 * changed and each is now typed from `web/src/shared/config/screen-registry.ts`, the ruling's
 * source: «Диспетчер» joined «Работа»; an administrator also sees «Администрирование»; and since
 * `R-80` an account with no role sees «Главная» and nothing else. `/optimisation` is a pointer
 * that replaces itself with the projects list (`W60-OPT-PROPOSALS-01`). And «Оптимизация
 * разделов», «Нормы», «Настройки анализа» and «Очередь» are no stubs any more: they open, say
 * nothing about not being ready and call their own reads (`W63`, `W55A`, `W59`, `W53`); an
 * account with no role is refused them at the guard (`/403`), without a product read.
 */

import { parseArgs, recorder, signIn, withColdBrowser } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const ORIGIN = args.origin;

// The ruling's menu, from the registry. Any account holding a role sees the first four groups;
// an administrator also sees the fifth; an account with no role sees «Главная» alone (`R-80`).
const ANY_ROLE = [
  ['/', 'Главная'],
  [
    'Работа',
    [
      ['/projects', 'Проекты'],
      ['/dashboard', 'Дашборд'],
      ['/section-optimisation', 'Оптимизация разделов'],
      ['/dispatcher', 'Диспетчер'],
    ],
  ],
  ['Знания', [['/knowledge-base', 'База знаний'], ['/blocks', 'Блоки'], ['/norms', 'Нормы']]],
  [
    'Система',
    [['/logs', 'Журнал выполнения'], ['/workers', 'Исполнители'], ['/analysis-settings', 'Настройки анализа'], ['/queue', 'Очередь']],
  ],
];
const RULED = {
  admin: [
    ...ANY_ROLE,
    ['Администрирование', [['/admin/users', 'Пользователи'], ['/admin/registrations', 'Заявки на регистрацию']]],
  ],
  expert: ANY_ROLE,
  none: [['/', 'Главная']],
};

// The four screens that were honest stubs and are screens now: what each reads on a cold open.
const GRADUATED = [
  ['/section-optimisation', '/bff/v1/sections/AR/specification'],
  ['/norms', '/bff/v1/norms/snapshots'],
  ['/analysis-settings', '/bff/v1/analysis/profiles'],
  ['/queue', '/bff/v1/execution/queue'],
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
      r.check(`${kind}: the one-row menu at 1280, in order`, RULED[kind], await page.evaluate(READ_ROW));
      r.check(
        `${kind}: no link to /optimisation anywhere in the frame`,
        0,
        await page.evaluate(`document.querySelectorAll('header a[href="/optimisation"]').length`),
      );
      await page.goto(`${ORIGIN}/optimisation`);
      // A pointer that replaces itself with the projects list; the guard refuses it to an
      // account with no role, and says where the refused account came from.
      const pointed = kind === 'none' ? '/403?from=%2Foptimisation' : '/projects';
      r.check(`${kind}: /optimisation leads to ${pointed}`, pointed, await page.location());
      const text = await page.evaluate(MAIN_TEXT);
      r.check(`${kind}: /optimisation lands on ${kind === 'none' ? 'the refusal' : 'a screen'}`, kind === 'none' ? 'refusal' : 'screen',
        text.includes('Доступ закрыт') ? 'refusal' : text.includes('Войти') ? 'sign-in' : text.length > 0 ? 'screen' : 'empty');
      r.note(`${kind}: /optimisation first line`, text.split('\n')[0]);
      for (const [screen, firstRead] of GRADUATED) {
        const before = page.exchanges().length;
        await page.goto(`${ORIGIN}${screen}`);
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
          .map((e) => new URL(e.url).pathname);
        const notAStub = !body.includes('Этот раздел ещё не готов.') && !body.includes('Раздел пока недоступен');
        if (kind === 'none') {
          r.check(`${kind}: ${screen} is refused at the guard and reads nothing of the product`,
            { refused: true, productReads: [] },
            {
              refused: (await page.location()).startsWith('/403') && body.includes('Доступ закрыт'),
              productReads: calls.filter((path) => path !== '/bff/v1/releases'),
            });
        } else {
          r.check(`${kind}: ${screen} opens, is no stub and makes its own first read`,
            { at: screen, notAStub: true, reads: true },
            { at: await page.location(), notAStub, reads: calls.includes(firstRead) });
        }
      }
      r.note(`${kind}: page errors`, page.pageErrors());
    },
    { cookies: session.cookies, viewport: { width: 1280, height: 900 } },
  );
}

const failed = r.failed();
console.log(`\n${failed.length === 0 ? 'R-66 OK' : `R-66 FAILED: ${failed.length}`}`);
process.exit(failed.length === 0 ? 0 : 1);
