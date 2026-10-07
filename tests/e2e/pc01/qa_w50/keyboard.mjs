/**
 * `W50-QA-01`, items 1–4 (browser half) — the keyboard paths through the real frame, focus
 * return, Escape and the outside click, with real key events (`lib.mjs` says why a second
 * DevTools client).
 *
 *     TMPDIR=<own dir> QA_W50_ACCOUNTS=<0600 file> E2E_PC01_CHROME=<chrome> \
 *       node tests/e2e/pc01/qa_w50/keyboard.mjs --origin http://127.0.0.1:PORT [--kind expert]
 *
 * Three cold browsers, one session: the one-row bar at 1280 × 900 (the account menu and the
 * group disclosures), and the stacked «Меню» at 780 × 900. Every step prints PASS/FAIL with
 * what was expected and what was seen; the exit status is non-zero when any step failed.
 *
 * Written by QA from the plan (`W50-PLAN.md` §3.5), without the lane reports.
 */

import { FOCUSED, FLOOR, keyboardFor, parseArgs, recorder, signIn, withColdBrowser } from './lib.mjs';

const args = parseArgs(process.argv.slice(2), { kind: 'expert' });
const ORIGIN = args.origin;

const ACCOUNT = '[data-account-menu]';
const TRIGGER = `${ACCOUNT} button.am-menu__trigger`;

/** The account menu as the page shows it. */
const MENU = `(() => {
  const trigger = document.querySelector(${JSON.stringify(TRIGGER)});
  const popup = document.querySelector('${ACCOUNT} .am-menu__popup');
  return { expanded: trigger?.getAttribute('aria-expanded') ?? null, popupHidden: popup?.hidden ?? null };
})()`;

/** A disclosure's button, found by its exact text inside `scope`. */
function button(scope, label) {
  return `Array.from(document.querySelectorAll(${JSON.stringify(`${scope} button.am-disclosure__button`)}))
    .find((b) => b.innerText.trim() === ${JSON.stringify(label)})`;
}

function disclosure(scope, label) {
  return `(() => {
    const b = ${button(scope, label)};
    if (b === undefined) return null;
    const panel = document.getElementById(b.getAttribute('aria-controls'));
    return { expanded: b.getAttribute('aria-expanded'), panelHidden: panel === null ? null : panel.hidden };
  })()`;
}

const OPEN = { expanded: 'true', panelHidden: false };
const SHUT = { expanded: 'false', panelHidden: true };
const MENU_OPEN = { expanded: 'true', popupHidden: false };
const MENU_SHUT = { expanded: 'false', popupHidden: true };

async function focus(page, expression) {
  return await page.evaluate(`(() => { const el = ${expression}; if (!el) return false; el.focus(); return document.activeElement === el; })()`);
}

const failures = [];
const session = await signIn(ORIGIN, args.kind);
console.log(`signed in as the '${args.kind}' account; the application landed it on ${session.landedOn}`);

// ------------------------------------------------------------------ 1280 × 900: account menu

await withColdBrowser(
  async (page) => {
    const r = recorder(`account menu @1280 (${args.kind})`);
    await page.goto(`${ORIGIN}/`);
    const keys = await keyboardFor(ORIGIN);
    try {
      const triggerName = await page.evaluate(`document.querySelector(${JSON.stringify(TRIGGER)})?.getAttribute('aria-label') ?? ''`);
      const T = `button:${triggerName.slice(0, 40)}`;
      const P = 'a[role=menuitem]:Профиль';
      const C = 'a[role=menuitem]:Сменить пароль';
      const X = 'button[role=menuitem]:Выйти';

      r.check('focus the trigger', true, await focus(page, `document.querySelector(${JSON.stringify(TRIGGER)})`));
      await keys.press('Enter');
      r.check('Enter on the trigger opens', MENU_OPEN, await page.evaluate(MENU));
      r.check('… with focus on the first item', P, await page.evaluate(FOCUSED));
      const walk = [];
      for (const key of ['ArrowDown', 'ArrowDown', 'ArrowDown', 'ArrowUp', 'ArrowUp', 'Home', 'End']) {
        await keys.press(key);
        walk.push(await page.evaluate(FOCUSED));
      }
      r.check('ArrowDown ×3 (wraps), ArrowUp ×2 (wraps), Home, End', [C, X, P, X, C, P, X], walk);
      r.check('the menu is still open while the arrows move', MENU_OPEN, await page.evaluate(MENU));
      await keys.press('Escape');
      r.check('Escape on an item closes', MENU_SHUT, await page.evaluate(MENU));
      r.check('… and returns focus to the trigger', T, await page.evaluate(FOCUSED));

      await keys.press(' ');
      r.check('Space on the trigger opens on the first item', [MENU_OPEN, P], [await page.evaluate(MENU), await page.evaluate(FOCUSED)]);
      await keys.press('Escape');
      r.check('Escape closes it again, focus on the trigger', [MENU_SHUT, T], [await page.evaluate(MENU), await page.evaluate(FOCUSED)]);

      await keys.press('ArrowUp');
      r.check('ArrowUp on the trigger opens on the last item', [MENU_OPEN, X], [await page.evaluate(MENU), await page.evaluate(FOCUSED)]);
      await keys.press('Tab');
      const afterTab = await page.evaluate(FOCUSED);
      r.check('Tab from an item closes the menu', MENU_SHUT, await page.evaluate(MENU));
      r.check('… and focus left the menu (not an item, not pulled back to the trigger)', true,
        !afterTab.includes('[role=menuitem]') && afterTab !== T);
      r.note('focus after Tab', afterTab);

      r.check('focus the trigger again', true, await focus(page, `document.querySelector(${JSON.stringify(TRIGGER)})`));
      await keys.press('ArrowDown');
      r.check('ArrowDown on the trigger opens on the first item', [MENU_OPEN, P], [await page.evaluate(MENU), await page.evaluate(FOCUSED)]);
      await page.click('footer.am-app__footer');
      await new Promise((resolve) => setTimeout(resolve, 200));
      r.check('a click outside (the footer) closes it', MENU_SHUT, await page.evaluate(MENU));

      // Choosing an item: a link, by the keyboard. It navigates; the frame stays.
      r.check('focus the trigger again', true, await focus(page, `document.querySelector(${JSON.stringify(TRIGGER)})`));
      await keys.press('Enter');
      await keys.press('ArrowDown');
      r.check('on «Сменить пароль»', C, await page.evaluate(FOCUSED));
      await keys.press('Enter');
      const landed = await page.waitFor("document.location.pathname === '/account/password' ? 'landed' : null", {
        boundMs: 15000,
        what: 'the chosen item to navigate',
      });
      await page.settle();
      r.check('Enter on the item follows it', '/account/password', await page.location());
      r.check('… the menu is closed after choosing', MENU_SHUT, await page.evaluate(MENU));
      r.check('… and focus is back on the trigger', T, await page.evaluate(FOCUSED));
      r.note('navigation wait', { ok: landed.ok, waitedMs: landed.waitedMs });
      r.note('console errors', page.consoleErrors());
      r.note('page errors', page.pageErrors());
      failures.push(...r.failed());
    } finally {
      keys.close();
    }
  },
  { cookies: session.cookies, viewport: { width: 1280, height: 900 } },
);

// ------------------------------------------------------------- 1280 × 900: group disclosures

await withColdBrowser(
  async (page) => {
    const r = recorder(`group disclosures @1280 (${args.kind})`);
    await page.goto(`${ORIGIN}/`);
    const keys = await keyboardFor(ORIGIN);
    const ROW = '[data-nav-state="row"]';
    try {
      r.check('the one-row state is displayed at 1280', 'flex', await page.evaluate(`getComputedStyle(document.querySelector('${ROW}')).display`));
      r.check('focus «Работа»', true, await focus(page, button(ROW, 'Работа')));
      await keys.press('Enter');
      r.check('Enter opens «Работа»', OPEN, await page.evaluate(disclosure(ROW, 'Работа')));
      const walked = [];
      for (let i = 0; i < 3; i += 1) {
        await keys.press('Tab');
        walked.push(await page.evaluate(FOCUSED));
      }
      r.check('Tab walks its links in order', ['a:Проекты', 'a:Дашборд', 'a:Оптимизация разделов'], walked);
      r.check('… and it stays open while focus is inside', OPEN, await page.evaluate(disclosure(ROW, 'Работа')));
      await keys.press('ArrowDown');
      r.note('ArrowDown inside a group (the disclosure pattern leaves arrows to the browser)', {
        focus: await page.evaluate(FOCUSED),
        state: await page.evaluate(disclosure(ROW, 'Работа')),
      });
      await keys.press('Tab');
      r.check('Tab past the last link leaves the group, to «Знания»', 'button:Знания', await page.evaluate(FOCUSED));
      r.check('… and «Работа» closed when focus left it', SHUT, await page.evaluate(disclosure(ROW, 'Работа')));

      await keys.press(' ');
      r.check('Space opens «Знания»', OPEN, await page.evaluate(disclosure(ROW, 'Знания')));
      await keys.press('Escape');
      r.check('Escape on the button closes it', SHUT, await page.evaluate(disclosure(ROW, 'Знания')));
      r.check('… focus stays on «Знания»', 'button:Знания', await page.evaluate(FOCUSED));

      await keys.press('Enter');
      await keys.press('Tab');
      r.check('inside «Знания»: on «База знаний»', 'a:База знаний', await page.evaluate(FOCUSED));
      await keys.press('Escape');
      r.check('Escape from inside the panel closes it', SHUT, await page.evaluate(disclosure(ROW, 'Знания')));
      r.check('… and returns focus to its button', 'button:Знания', await page.evaluate(FOCUSED));

      await keys.press('Enter');
      r.check('Enter opens «Знания» again', OPEN, await page.evaluate(disclosure(ROW, 'Знания')));
      await page.click('footer.am-app__footer');
      await new Promise((resolve) => setTimeout(resolve, 200));
      r.check('a click outside closes it', SHUT, await page.evaluate(disclosure(ROW, 'Знания')));

      r.check('focus «Система»', true, await focus(page, button(ROW, 'Система')));
      await keys.press('Enter');
      await keys.press('Tab');
      r.check('inside «Система»: on «Журнал выполнения»', 'a:Журнал выполнения', await page.evaluate(FOCUSED));
      await keys.press('Enter');
      await page.waitFor("document.location.pathname === '/logs' ? 'landed' : null", { boundMs: 15000, what: '/logs' });
      await page.settle();
      r.check('Enter on a link follows it', '/logs', await page.location());
      r.check('… and the group closed after choosing', SHUT, await page.evaluate(disclosure(ROW, 'Система')));
      r.check('… «Система» is the current group', 'true', await page.evaluate(`${button(ROW, 'Система')}?.getAttribute('aria-current') ?? null`));
      r.note('focus after choosing a group link (the plan names no return target for a disclosure)', await page.evaluate(FOCUSED));
      r.note('page errors', page.pageErrors());
      failures.push(...r.failed());
    } finally {
      keys.close();
    }
  },
  { cookies: session.cookies, viewport: { width: 1280, height: 900 } },
);

// -------------------------------------------------------------- 780 × 900: the stacked «Меню»

await withColdBrowser(
  async (page) => {
    const r = recorder(`stacked «Меню» @780 (${args.kind})`);
    await page.goto(`${ORIGIN}/`);
    const keys = await keyboardFor(ORIGIN);
    const ST = '[data-nav-state="stacked"]';
    const MENU_BUTTON = button(ST, 'Меню');
    try {
      r.check('at 780 the one-row state is hidden and the stacked one shown',
        ['none', 'block'],
        await page.evaluate(`['[data-nav-state="row"]', '${ST}'].map((s) => getComputedStyle(document.querySelector(s)).display)`));
      r.check('focus «Меню»', true, await focus(page, MENU_BUTTON));
      await keys.press('Enter');
      r.check('Enter opens «Меню»', OPEN, await page.evaluate(disclosure(ST, 'Меню')));
      await keys.press('Tab');
      r.check('Tab: «Главная»', 'a:Главная', await page.evaluate(FOCUSED));
      await keys.press('Tab');
      r.check('Tab: the «Работа» group', 'button:Работа', await page.evaluate(FOCUSED));
      await keys.press('Enter');
      r.check('Enter opens «Работа» inside «Меню»', OPEN, await page.evaluate(disclosure(ST, 'Работа')));
      await keys.press('Tab');
      r.check('Tab: «Проекты»', 'a:Проекты', await page.evaluate(FOCUSED));
      await keys.press('Escape');
      r.check('Escape closes the inner group only', [SHUT, OPEN],
        [await page.evaluate(disclosure(ST, 'Работа')), await page.evaluate(disclosure(ST, 'Меню'))]);
      r.check('… focus on the inner group’s button', 'button:Работа', await page.evaluate(FOCUSED));
      await keys.press('Escape');
      r.check('a second Escape closes «Меню»', SHUT, await page.evaluate(disclosure(ST, 'Меню')));
      r.check('… focus on «Меню»', 'button:Меню', await page.evaluate(FOCUSED));

      await keys.press(' ');
      r.check('Space opens «Меню»', OPEN, await page.evaluate(disclosure(ST, 'Меню')));
      // Tab through to the last group button and past it: the stacked list holds Главная and three groups.
      const seen = [];
      for (let i = 0; i < 5; i += 1) {
        await keys.press('Tab');
        seen.push(await page.evaluate(FOCUSED));
      }
      r.note('Tab ×5 from «Меню» with every group closed', seen);
      r.check('Tab past the last group leaves «Меню» and closes it', SHUT, await page.evaluate(disclosure(ST, 'Меню')));

      r.check('focus «Меню» again', true, await focus(page, MENU_BUTTON));
      await keys.press('Enter');
      await page.click('footer.am-app__footer');
      await new Promise((resolve) => setTimeout(resolve, 200));
      r.check('a click outside closes «Меню»', SHUT, await page.evaluate(disclosure(ST, 'Меню')));

      r.check('focus the account trigger', true, await focus(page, `document.querySelector(${JSON.stringify(TRIGGER)})`));
      await keys.press('Enter');
      await keys.press('End');
      r.check('the account menu at 780: Enter, End', [MENU_OPEN, 'button[role=menuitem]:Выйти'],
        [await page.evaluate(MENU), await page.evaluate(FOCUSED)]);
      await keys.press('Escape');
      r.check('… Escape closes it and focus returns to the trigger', MENU_SHUT, await page.evaluate(MENU));
      r.check('… on the trigger', true, (await page.evaluate(FOCUSED)).startsWith('button:Учётная запись'));

      r.check('focus «Меню» once more', true, await focus(page, MENU_BUTTON));
      await keys.press('Enter');
      await keys.press('Tab');
      await keys.press('Tab');
      await keys.press('Enter');
      await keys.press('Tab');
      await keys.press('Tab');
      r.check('inside «Меню» › «Работа»: on «Дашборд»', 'a:Дашборд', await page.evaluate(FOCUSED));
      await keys.press('Enter');
      await page.waitFor("document.location.pathname === '/dashboard' ? 'landed' : null", { boundMs: 15000, what: '/dashboard' });
      await page.settle();
      r.check('Enter follows the link', '/dashboard', await page.location());
      r.check('… and both levels closed after choosing', [SHUT, SHUT],
        [await page.evaluate(disclosure(ST, 'Меню')), await page.evaluate(disclosure(ST, 'Работа'))]);
      r.note('focus after choosing in the stacked menu', await page.evaluate(FOCUSED));
      r.note('page errors', page.pageErrors());
      failures.push(...r.failed());
    } finally {
      keys.close();
    }
  },
  { cookies: session.cookies, viewport: { ...FLOOR } },
);

console.log(`\n${failures.length === 0 ? 'KEYBOARD OK' : `KEYBOARD FAILED: ${failures.length} step(s)`}`);
process.exit(failures.length === 0 ? 0 : 1);
