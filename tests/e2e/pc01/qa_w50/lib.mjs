/**
 * `W50-QA-01` — what the QA browser drives share: the accounts, the sign-in, and real key
 * presses.
 *
 * The instruments of `tests/e2e/pc01/journey/` are used unchanged: `withColdBrowser` (a new
 * browser process with a throwaway profile per call, `cookies` and `viewport` set before the
 * first navigation), `Page.fill`/`click`/`evaluate`, and `width.mjs`'s `MEASUREMENT` and
 * `widthFindings`.
 *
 * ## Why a second DevTools connection, and only for keys
 *
 * `cdp.mjs`'s `Page` has no key primitive, and its protocol handle is private by design. A key
 * event dispatched from page script is *untrusted*: Enter does not click a button, Tab does not
 * move focus — so a drive built on it would measure a browser that does not exist. The real
 * thing is `Input.dispatchKeyEvent`, so this module opens a **second** DevTools client to the
 * same browser and uses it for nothing but key presses. It finds the browser by the
 * `DevToolsActivePort` file Chrome writes into its profile: `withColdBrowser` makes the profile
 * under `os.tmpdir()`, and every QA drive runs with `TMPDIR` set to a directory of its own, so
 * exactly one profile is there while a callback runs. Nothing in `cdp.mjs` changes.
 *
 * ## Accounts
 *
 * Read from the JSON file `QA_W50_ACCOUNTS` names — outside the repository, mode 0600 — as
 * `{ "<kind>": { "login": "…", "password": "…" } }`. No value is printed or written: the
 * records name the KIND of account. The sign-in drives the application's own `/login` screen;
 * the session cookie it yields is held in memory and handed to later cold browsers.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { withColdBrowser } from '../journey/cdp.mjs';

export { withColdBrowser };

export const SESSION_COOKIE = 'am_session';

/** The declared width every QA width state is measured at, and its height. */
export const FLOOR = Object.freeze({ width: 780, height: 900 });

export function parseArgs(argv, extra = {}) {
  const args = { origin: undefined, out: undefined, ...extra };
  for (let i = 0; i < argv.length; i += 1) {
    const name = argv[i];
    if (name === '--origin') args.origin = argv[++i];
    else if (name === '--out') args.out = argv[++i];
    else if (name.startsWith('--') && name.slice(2) in extra) args[name.slice(2)] = argv[++i];
    else {
      console.error(`unknown argument '${name}'`);
      process.exit(2);
    }
  }
  if (!args.origin) {
    console.error('--origin is required: a drive is a drive of something in particular.');
    process.exit(2);
  }
  args.origin = args.origin.replace(/\/+$/, '');
  return args;
}

export function accounts() {
  const file = process.env.QA_W50_ACCOUNTS;
  if (!file) throw new Error('QA_W50_ACCOUNTS must name the accounts file (outside the repository, mode 0600)');
  const mode = statSync(file).mode & 0o777;
  if (mode !== 0o600) throw new Error(`the accounts file must be mode 0600, is ${mode.toString(8)}`);
  return JSON.parse(readFileSync(file, 'utf8'));
}

/**
 * Sign in as `kind` through `/login`, and return where the application landed the browser and
 * the cookie declaration for later browsers. The value never leaves this process.
 */
export async function signIn(origin, kind) {
  const all = accounts();
  const account = all[kind];
  if (account === undefined) throw new Error(`no account of kind '${kind}' in the accounts file`);
  let cookie = null;
  let landedOn = null;
  await withColdBrowser(async (page) => {
    await page.goto(`${origin}/login`);
    await page.fill('#sign-in-login', account.login);
    await page.fill('#sign-in-password', account.password);
    await page.click('form button[type="submit"]', { text: 'Войти' });
    const waited = await page.waitFor(
      "document.location.pathname !== '/login' ? document.location.pathname : null",
      { boundMs: 30000, what: 'the browser to leave /login' },
    );
    if (!waited.ok) throw new Error(`sign-in as '${kind}': the browser stayed on /login`);
    await page.settle();
    landedOn = await page.location();
    cookie = await page.cookieFor(SESSION_COOKIE);
  });
  if (cookie === null) throw new Error(`sign-in as '${kind}': no ${SESSION_COOKIE} cookie`);
  return {
    kind,
    landedOn,
    cookies: [
      {
        name: cookie.name,
        value: cookie.value,
        url: origin,
        path: cookie.path ?? '/',
        httpOnly: cookie.httpOnly === true,
        sameSite: cookie.sameSite ?? 'Strict',
      },
    ],
  };
}

// --------------------------------------------------------------------- real key presses

const KEYS = {
  Enter: { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' },
  ' ': { key: ' ', code: 'Space', windowsVirtualKeyCode: 32, text: ' ' },
  Escape: { key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 },
  Tab: { key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 },
  ArrowDown: { key: 'ArrowDown', code: 'ArrowDown', windowsVirtualKeyCode: 40 },
  ArrowUp: { key: 'ArrowUp', code: 'ArrowUp', windowsVirtualKeyCode: 38 },
  Home: { key: 'Home', code: 'Home', windowsVirtualKeyCode: 36 },
  End: { key: 'End', code: 'End', windowsVirtualKeyCode: 35 },
};

class KeyConnection {
  #socket;
  #next = 1;
  #pending = new Map();

  constructor(socket) {
    this.#socket = socket;
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id === undefined) return;
      const entry = this.#pending.get(message.id);
      if (entry === undefined) return;
      this.#pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
  }

  send(method, params = {}, sessionId = undefined) {
    const id = this.#next++;
    return new Promise((resolve, reject) => {
      this.#pending.set(id, { resolve, reject });
      this.#socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    });
  }

  close() {
    try {
      this.#socket.close();
    } catch {
      /* going away regardless */
    }
  }
}

/**
 * A keyboard for the page `origin` is showing, in the browser `withColdBrowser` launched for the
 * current callback. Call inside the callback, after the first `goto`.
 */
export async function keyboardFor(origin) {
  const profiles = readdirSync(tmpdir())
    .filter((name) => name.startsWith('e2e-pc01-'))
    .filter((name) => {
      try {
        return statSync(join(tmpdir(), name, 'DevToolsActivePort')).isFile();
      } catch {
        return false;
      }
    })
    .sort(
      (left, right) =>
        statSync(join(tmpdir(), right, 'DevToolsActivePort')).mtimeMs -
        statSync(join(tmpdir(), left, 'DevToolsActivePort')).mtimeMs,
    );
  if (profiles.length === 0) {
    throw new Error(
      `keyboard: expected a live browser profile under ${tmpdir()}, found none. ` +
        'Run the QA drives with TMPDIR set to a directory of their own.',
    );
  }
  // `withColdBrowser` kills its Chrome before recursively removing the profile, but the kill is
  // asynchronous: the previous cold browser can leave its directory visible for a moment. The
  // browser opened for this callback has the newest DevToolsActivePort in this drive's private
  // TMPDIR, so stale profiles from earlier callbacks cannot make the second keyboard pass fail.
  const [port, path] = readFileSync(join(tmpdir(), profiles[0], 'DevToolsActivePort'), 'utf8').trim().split('\n');
  const socket = new WebSocket(`ws://127.0.0.1:${port}${path}`);
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', () => reject(new Error('keyboard: cannot reach the browser')), { once: true });
  });
  const connection = new KeyConnection(socket);
  const { targetInfos } = await connection.send('Target.getTargets');
  const pages = targetInfos.filter((t) => t.type === 'page' && t.url.startsWith(origin));
  if (pages.length !== 1) {
    connection.close();
    throw new Error(`keyboard: expected one page on ${origin}, found ${pages.length}`);
  }
  const { sessionId } = await connection.send('Target.attachToTarget', { targetId: pages[0].targetId, flatten: true });
  return {
    async press(name, { shift = false } = {}) {
      const spec = KEYS[name];
      if (spec === undefined) throw new Error(`keyboard: no key '${name}'`);
      const modifiers = shift ? 8 : 0;
      const { text, ...rest } = spec;
      await connection.send(
        'Input.dispatchKeyEvent',
        { type: text ? 'keyDown' : 'rawKeyDown', modifiers, ...rest, ...(text ? { text, unmodifiedText: text } : {}) },
        sessionId,
      );
      await connection.send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers, ...rest }, sessionId);
      // Let React commit and the islands' effects run before anything is read.
      await new Promise((resolve) => setTimeout(resolve, 150));
    },
    close() {
      connection.close();
    },
  };
}

// ----------------------------------------------------------------------------- reading

/** A short, stable description of the focused element. */
export const FOCUSED = `(() => {
  const el = document.activeElement;
  if (el === null || el === document.body) return 'body';
  const label = (el.getAttribute('aria-label') ?? el.innerText ?? '').trim().replace(/\\s+/g, ' ').slice(0, 40);
  const role = el.getAttribute('role');
  return el.tagName.toLowerCase() + (role ? '[role=' + role + ']' : '') + ':' + label;
})()`;

/** A recorder of steps: each says what was done, what was expected and what was seen. */
export function recorder(title) {
  const steps = [];
  return {
    steps,
    check(step, expected, observed) {
      const ok = JSON.stringify(expected) === JSON.stringify(observed);
      steps.push({ step, expected, observed, ok });
      console.log(`${ok ? 'PASS' : 'FAIL'}  ${title} | ${step} | expected ${JSON.stringify(expected)} | observed ${JSON.stringify(observed)}`);
      return ok;
    },
    note(step, observed) {
      steps.push({ step, observed, ok: null });
      console.log(`NOTE  ${title} | ${step} | ${JSON.stringify(observed)}`);
    },
    failed() {
      return steps.filter((s) => s.ok === false);
    },
  };
}
