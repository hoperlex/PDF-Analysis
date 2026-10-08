/**
 * `W50-QA-01`, item 7 — 780 × 900 has no horizontal overflow for every menu state.
 *
 *     TMPDIR=<own dir> QA_W50_ACCOUNTS=<0600 file> E2E_PC01_CHROME=<chrome> \
 *       node tests/e2e/pc01/qa_w50/width-states.mjs --origin http://127.0.0.1:PORT
 *
 * The verdict is `width.mjs`'s, unchanged: `scrollWidth <= innerWidth` at the declared width,
 * with the widest offenders named. Each state is a cold browser at 780 × 900 with the session
 * of the account kind it needs, opened by the real controls (clicks at their coordinates):
 *
 *   guest                        /login, nothing open
 *   expert, closed               /, the frame as it first renders
 *   expert, «Меню» open          /, «Меню» and every group inside it open
 *   expert, account menu open    /
 *   long (66-char name, 254-char e-mail): closed, account menu open, «Меню» open
 *   incomplete-profile accounts: closed and account menu open, on /account (where they land)
 *   default credential: closed and account menu open, on /account/password
 *
 * The one-row state is not displayed at 780 (the frame collapses below its breakpoint); it is
 * measured where it first shows, and the reading at 780 says which state was on screen.
 *
 * Written by QA from the plan, without the lane reports.
 */

import { MEASUREMENT, widthFindings } from '../journey/width.mjs';

import { FLOOR, accounts, parseArgs, recorder, signIn, withColdBrowser } from './lib.mjs';

const args = parseArgs(process.argv.slice(2), { row: '960' });
const ORIGIN = args.origin;
const ROW_WIDTH = Number(args.row);

const settle = () => new Promise((resolve) => setTimeout(resolve, 250));

const STATE = `(() => {
  const shown = (s) => { const el = document.querySelector(s); return el === null ? null : getComputedStyle(el).display; };
  const open = Array.from(document.querySelectorAll('button[aria-expanded="true"]')).map((b) => (b.getAttribute('aria-label') ?? b.innerText).trim().slice(0, 40));
  const name = document.querySelector('[data-account-name]');
  const login = document.querySelector('[data-account-login]');
  return {
    row: shown('[data-nav-state="row"]'),
    stacked: shown('[data-nav-state="stacked"]'),
    open,
    nameLength: name === null ? null : name.textContent.length,
    loginLength: login === null ? null : login.textContent.length,
  };
})()`;

async function openStacked(page) {
  await page.click('[data-nav-state="stacked"] button.am-disclosure__button', { text: 'Меню' });
  await settle();
  for (const label of ['Работа', 'Знания', 'Система']) {
    const found = await page.describe('[data-nav-state="stacked"] .am-disclosure--inline button.am-disclosure__button', label);
    if (found !== null) {
      await page.click('[data-nav-state="stacked"] .am-disclosure--inline button.am-disclosure__button', { text: label });
      await settle();
    }
  }
}

async function openAccount(page) {
  await page.click('[data-account-menu] button.am-menu__trigger');
  await settle();
}

const failures = [];
const readings = [];

async function measure(
  r,
  where,
  { cookies = [], path, act = null, viewport = FLOOR, expectedPath = null, expectedState = {} },
) {
  await withColdBrowser(
    async (page) => {
      await page.goto(`${ORIGIN}${path}`);
      if (act !== null) await act(page);
      await settle();
      const measurement = await page.evaluate(MEASUREMENT);
      const state = await page.evaluate(STATE);
      const landedOn = await page.location();
      const findings = widthFindings(where, measurement, viewport);
      readings.push({ where, landedOn, state, scrollWidth: measurement.scrollWidth, innerWidth: measurement.innerWidth });
      r.check(`${where} @${viewport.width}×${viewport.height} on ${landedOn} ${JSON.stringify(state)}`, [], findings);
      if (expectedPath !== null) r.check(`${where}: landed path`, expectedPath, landedOn);
      for (const [key, value] of Object.entries(expectedState)) {
        r.check(`${where}: ${key}`, value, state[key]);
      }
    },
    { cookies, viewport },
  );
}

const all = accounts();
const r = recorder('width');

await measure(r, 'guest', { path: '/login' });

const expert = await signIn(ORIGIN, 'expert');
await measure(r, 'expert, closed', { cookies: expert.cookies, path: '/' });
await measure(r, 'expert, «Меню» and every group open', { cookies: expert.cookies, path: '/', act: openStacked });
await measure(r, 'expert, account menu open', { cookies: expert.cookies, path: '/', act: openAccount });
await measure(r, 'expert, one-row state where it first shows', {
  cookies: expert.cookies,
  path: '/',
  viewport: { width: ROW_WIDTH, height: 900 },
});
await measure(r, 'expert, one-row state, account menu open', {
  cookies: expert.cookies,
  path: '/',
  viewport: { width: ROW_WIDTH, height: 900 },
  act: openAccount,
});

if (all.long !== undefined) {
  const long = await signIn(ORIGIN, 'long');
  const expectedLongState = { nameLength: 66, loginLength: 254 };
  await measure(r, '66-char name + 254-char e-mail, closed', {
    cookies: long.cookies,
    path: '/',
    expectedState: expectedLongState,
  });
  await measure(r, '66-char name + 254-char e-mail, account menu open', {
    cookies: long.cookies,
    path: '/',
    act: openAccount,
    expectedState: expectedLongState,
  });
  await measure(r, '66-char name + 254-char e-mail, «Меню» open', {
    cookies: long.cookies,
    path: '/',
    act: openStacked,
    expectedState: expectedLongState,
  });
  await measure(r, '66-char name + 254-char e-mail, one-row, account menu open', {
    cookies: long.cookies,
    path: '/',
    viewport: { width: ROW_WIDTH, height: 900 },
    act: openAccount,
    expectedState: expectedLongState,
  });
} else r.check('the long-label account is in the accounts file', true, false);

for (const kind of ['incomplete', 'incomplete-long']) {
  if (all[kind] === undefined) {
    r.check(`the '${kind}' account is in the accounts file`, true, false);
    continue;
  }
  const s = await signIn(ORIGIN, kind);
  const expectedState = kind === 'incomplete-long' ? { nameLength: 254, loginLength: 254 } : {};
  await measure(r, `${kind} profile, closed`, {
    cookies: s.cookies,
    path: s.landedOn ?? '/account',
    expectedPath: '/account',
    expectedState,
  });
  await measure(r, `${kind} profile, account menu open`, {
    cookies: s.cookies,
    path: s.landedOn ?? '/account',
    act: openAccount,
    expectedPath: '/account',
    expectedState,
  });
}

if (all.default !== undefined) {
  const d = await signIn(ORIGIN, 'default');
  await measure(r, 'default credential, closed', {
    cookies: d.cookies,
    path: d.landedOn ?? '/account/password',
    expectedPath: '/account/password',
  });
  await measure(r, 'default credential, account menu open', {
    cookies: d.cookies,
    path: d.landedOn ?? '/account/password',
    act: openAccount,
    expectedPath: '/account/password',
  });
} else r.check("the 'default' account is in the accounts file", true, false);

failures.push(...r.failed());
console.log(JSON.stringify(readings, null, 1));
console.log(`\n${failures.length === 0 ? 'WIDTH OK' : `WIDTH FAILED: ${failures.length} state(s)`}`);
process.exit(failures.length === 0 ? 0 : 1);
