/**
 * A minimal Chrome DevTools Protocol client, with no dependency outside Node's standard
 * library.
 *
 * **Why this file exists rather than a `playwright-core` import.** `D-5`'s lesson is not
 * "the programme needs a browser"; it is that the *instrument* lived outside the tree and
 * died with it, so an attribution became permanently unanswerable. Three sessions have
 * since re-imported `playwright-core` from `/root/w15run-browser/node_modules` by absolute
 * path -- code in the tree would still not run in a clean clone. Adding `playwright-core`
 * to `web/package.json` would fix that and cost one repository dependency plus an install
 * in every worktree the gate touches.
 *
 * Node 22.23.1 (pinned in `web/package.json` `engines`) ships a global `WebSocket`, and the
 * four CDP domains this journey needs -- `Target`, `Page`, `Network`, `Runtime` -- are the
 * stable, documented half of the protocol. So the journey needs no dependency at all, and
 * the whole instrument is inside the repository. That is the trade this file makes: a few
 * hundred lines the programme owns, against a dependency and an instrument that is only
 * half committed.
 *
 * What it deliberately does NOT do: auto-waiting, actionability checks, downloads, video,
 * frame trees, shadow piercing. Anything that needs more than what is here is a reason to
 * reopen the dependency question, not to grow this file.
 *
 * **`W22-E2E` widened it, and that is worth stating rather than hiding in a diff.** The
 * read half navigates, records and reads text, and needed nothing else. The *write* half
 * -- create a project, upload a PDF, start a run -- has to press the application's own
 * controls, so this file grew four primitives (`click`, `fill`, `attachFile`, `waitFor`,
 * plus a public `settle`) and two protocol domains (`Input`, `DOM`). `W21-E2E` wrote that
 * the write half would be "an extension of `manifest.json` plus the walk"; measured, the
 * manifest part is true and the "plus the walk" part is not -- see
 * `docs/program/reviews/W22-E2E.md` section 2.
 *
 * Each new primitive **reads back what it did** and throws when the application did not
 * take it: a `fill` that the control did not accept, a file the browser did not attach and
 * a click on a disabled or zero-box control are failures here, not silent no-ops that
 * surface later as a missing request. A no-op that reports success is the vacuous pass
 * this programme keeps finding, one layer down.
 *
 * `waitFor` takes a **required** bound. There is no default and no unbounded wait: a
 * primitive that can hang forever reports nothing at all, which is the `D-5` failure mode.
 */

import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

/**
 * Candidate Chromium binaries, in order.
 *
 * The browser is an *environment* prerequisite, like `docker` or `npm` -- not a repository
 * dependency. `E2E_PC01_CHROME` overrides; otherwise the list below is searched and an
 * empty result is a hard failure with instructions, never a skip.
 */
const CHROME_CANDIDATES = [
  '/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',
  '/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/usr/bin/google-chrome',
];

export function findChrome() {
  const override = process.env.E2E_PC01_CHROME;
  if (override) {
    if (!existsSync(override)) {
      throw new Error(`E2E_PC01_CHROME=${override} does not exist.`);
    }
    return override;
  }
  for (const candidate of CHROME_CANDIDATES) {
    if (existsSync(candidate)) return candidate;
  }
  throw new Error(
    [
      'No Chromium binary found. The journey drives a real browser and will not skip.',
      `Looked at: ${CHROME_CANDIDATES.join(', ')}`,
      'Set E2E_PC01_CHROME=/path/to/chrome to name one.',
    ].join('\n'),
  );
}

/**
 * How long to wait for a screen to go quiet before recording it anyway.
 *
 * A screen that polls -- the run screen does -- never goes quiet, so this bound is what
 * ends the wait there. It is not a timeout in the failure sense: whatever the page had
 * done by then is recorded and checked. `E2E_PC01_SETTLE_TIMEOUT_MS` raises it for a
 * slower origin.
 */
const SETTLE_TIMEOUT_MS = Number(process.env.E2E_PC01_SETTLE_TIMEOUT_MS ?? 10000);

/** Nothing in this instrument may wait forever; a hung journey reports nothing at all. */
function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('timed out')), ms)),
  ]);
}

/** One CDP connection, multiplexed over a single WebSocket, with flat session routing. */
class Connection {
  #socket;
  #nextId = 1;
  #pending = new Map();
  #listeners = new Set();

  constructor(socket) {
    this.#socket = socket;
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id !== undefined) {
        const entry = this.#pending.get(message.id);
        if (entry === undefined) return;
        this.#pending.delete(message.id);
        if (message.error) entry.reject(new Error(`${message.method}: ${message.error.message}`));
        else entry.resolve(message.result);
        return;
      }
      for (const listener of this.#listeners) listener(message);
    });
  }

  static async open(url) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', () => reject(new Error(`cannot connect to ${url}`)), {
        once: true,
      });
    });
    return new Connection(socket);
  }

  send(method, params = {}, sessionId = undefined) {
    const id = this.#nextId++;
    const payload = { id, method, params };
    if (sessionId !== undefined) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.#pending.set(id, { resolve, reject, method });
      this.#socket.send(JSON.stringify(payload));
    });
  }

  on(listener) {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  close() {
    try {
      this.#socket.close();
    } catch {
      /* the process is going away regardless */
    }
  }
}

/**
 * Launch one browser process and attach to one fresh page in it.
 *
 * Every call is a **new operating-system process with its own throwaway profile
 * directory**: no cache, no `localStorage`, no cookies, no prior client state, nothing
 * carried from a previous route. `W19-SHELL` established that property because four
 * certifications missed `D-16` by never reloading a page, and it is preserved here by
 * construction rather than by discipline -- there is no API in this module for reusing a
 * browser across routes.
 *
 * ## `W44-JOURNEY`: two options, and why neither weakens the property above
 *
 * `D-92`. The BFF answers `401` without a session cookie -- wave 34, by design -- so a
 * walk of empty profiles reaches route 2 of 15 and stops. Two things are now settable on
 * the profile **before** the callback runs, and both are **values the caller states**,
 * never values this module carries over from a previous call:
 *
 *   `cookies`  -- an explicit list of cookie declarations. There is no jar shared between
 *                 calls and nothing is read out of one browser and into the next by this
 *                 module: the caller obtains a value once, from its own sign-in, and hands
 *                 the SAME value to every call. So route 15's browser receives exactly
 *                 what route 1's received, which is the difference between a session
 *                 *carried deliberately* and state *leaking forward*. `page.startedWith()`
 *                 reports the jar as it stood before the first navigation, so a caller can
 *                 assert per route that the profile held nothing else -- the property is
 *                 measured rather than asserted in a comment.
 *   `viewport` -- `D-93`. A layout claim needs a declared width; the default window is
 *                 whatever the host gives, which is not a measurement. Set before
 *                 navigation, because a width applied afterwards measures a reflow.
 *
 * What is deliberately still absent is any way to reuse a browser, so the cold-load
 * property cannot be lost by forgetting it. Adding a `Page` to this signature, or
 * returning one, is the change that would end `D-16`'s guarantee.
 */
export async function withColdBrowser(fn, { cookies = [], viewport = null } = {}) {
  if (!Array.isArray(cookies)) {
    throw new Error('withColdBrowser: `cookies` must be an array of cookie declarations');
  }
  for (const cookie of cookies) {
    if (typeof cookie?.name !== 'string' || typeof cookie?.value !== 'string') {
      throw new Error(
        'withColdBrowser: every cookie must declare a string `name` and a string `value`; ' +
          `got ${JSON.stringify(cookie)}`,
      );
    }
  }
  const executable = findChrome();
  const profile = mkdtempSync(join(tmpdir(), 'e2e-pc01-'));
  const child = spawn(
    executable,
    [
      '--headless=new',
      '--remote-debugging-port=0',
      `--user-data-dir=${profile}`,
      '--no-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-extensions',
      'about:blank',
    ],
    { stdio: ['ignore', 'pipe', 'pipe'] },
  );

  let connection;
  try {
    const wsUrl = await new Promise((resolve, reject) => {
      let buffer = '';
      const timer = setTimeout(
        () => reject(new Error(`browser did not announce a DevTools endpoint:\n${buffer}`)),
        30000,
      );
      child.stderr.on('data', (chunk) => {
        buffer += String(chunk);
        const match = buffer.match(/DevTools listening on (ws:\/\/\S+)/);
        if (match) {
          clearTimeout(timer);
          resolve(match[1]);
        }
      });
      child.on('exit', (code) => {
        clearTimeout(timer);
        reject(new Error(`browser exited with ${code} before listening:\n${buffer}`));
      });
    });

    connection = await Connection.open(wsUrl);
    const { targetId } = await connection.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await connection.send('Target.attachToTarget', {
      targetId,
      flatten: true,
    });
    const page = new Page(connection, sessionId);
    await page.enable();
    if (viewport !== null) await page.setViewport(viewport);
    if (cookies.length > 0) await page.setCookies(cookies);
    // Read back what this profile actually holds, BEFORE the first navigation. A fresh
    // profile plus exactly the declarations the caller passed is the whole of `D-16`'s
    // cold-load property, and this is the reading that makes it checkable from outside.
    await page.recordStartingJar();
    return await fn(page);
  } finally {
    connection?.close();
    // The process is ours and we hold its pid. Nothing here ever matches a process by
    // name: this host runs other sessions' browsers and stacks.
    try {
      child.kill('SIGKILL');
    } catch {
      /* already gone */
    }
    try {
      rmSync(profile, { recursive: true, force: true });
    } catch {
      /* best effort */
    }
  }
}

/**
 * Response headers worth keeping verbatim.
 *
 * `D-5` closed unanswerable because a harness logged *status lines only*. The correlation
 * id is how a browser-side failure is joined to a server-side log line, and the content
 * type is how "a 200 that was actually an error page" is told apart from a 200. Everything
 * else in this list is what decides whether a response was cached, redirected or streamed.
 */
const KEPT_RESPONSE_HEADERS = [
  'content-type',
  'content-length',
  'cache-control',
  'location',
  'x-correlation-id',
  'x-request-id',
  'retry-after',
];

/** Request headers worth keeping. `authorization` is recorded as PRESENCE, never value. */
const KEPT_REQUEST_HEADERS = ['content-type', 'idempotency-key', 'accept', 'referer'];

function pick(headers, names) {
  const out = {};
  for (const [key, value] of Object.entries(headers ?? {})) {
    const lower = key.toLowerCase();
    if (names.includes(lower)) out[lower] = value;
  }
  return out;
}

/** One attached page, recording every exchange it makes. */
class Page {
  #connection;
  #sessionId;
  /** requestId -> envelope under construction */
  #exchanges = new Map();
  #order = [];
  #consoleErrors = [];
  #pageErrors = [];
  #inFlight = 0;
  #lastActivity = Date.now();
  #redirectSeq = 0;
  #domEnabled = false;
  /** The jar as it stood before the first navigation. `W44-JOURNEY`, `D-16`. */
  #startedWith = null;

  constructor(connection, sessionId) {
    this.#connection = connection;
    this.#sessionId = sessionId;
  }

  #send(method, params) {
    return this.#connection.send(method, params, this.#sessionId);
  }

  async enable() {
    this.#connection.on((message) => {
      if (message.sessionId !== this.#sessionId) return;
      this.#handle(message.method, message.params);
    });
    await this.#send('Page.enable', {});
    await this.#send('Network.enable', {});
    await this.#send('Runtime.enable', {});
    // `Input` is needed only by the write half, but enabling it costs nothing and keeps
    // every page in this instrument the same shape. `DOM` is enabled lazily, in
    // `attachFile`, because it is the one domain that changes what the browser keeps.
    await this.#send('Input.setIgnoreInputEvents', { ignore: false });
  }

  #handle(method, params) {
    this.#lastActivity = Date.now();
    if (method === 'Network.requestWillBeSent') {
      const request = params.request;
      // A redirect does NOT get a new requestId: the protocol reuses the old one and
      // hands the previous hop's response in `redirectResponse`. Two consequences, both
      // of which cost a debugging round here:
      //   - the hop's own status and `location` are only ever seen in THIS event, so a
      //     handler that overwrites the envelope loses the 307 entirely -- exactly the
      //     "status lines only" impoverishment D-5 is about, one level down;
      //   - the in-flight count must NOT be incremented again, or it never drains and
      //     every navigation through a redirect waits out the full settle timeout.
      const continuing = params.redirectResponse !== undefined;
      if (continuing) {
        const previous = this.#exchanges.get(params.requestId);
        if (previous !== undefined) {
          previous.status = params.redirectResponse.status;
          previous.statusText = params.redirectResponse.statusText;
          previous.responseHeaders = pick(
            params.redirectResponse.headers,
            KEPT_RESPONSE_HEADERS,
          );
          previous.mimeType = params.redirectResponse.mimeType;
          previous.redirectedTo = request.url;
          // A redirect carries no body to fetch, and saying so is a fact, not an absence.
          previous.responseBody = null;
          const key = `${params.requestId}#hop${this.#redirectSeq++}`;
          this.#exchanges.set(key, previous);
          this.#exchanges.delete(params.requestId);
          const at = this.#order.indexOf(params.requestId);
          if (at >= 0) this.#order[at] = key;
        }
      }
      const envelope = {
        requestId: params.requestId,
        resourceType: params.type ?? null,
        method: request.method,
        url: request.url,
        requestHeaders: pick(request.headers, KEPT_REQUEST_HEADERS),
        // The value is never recorded. What matters -- and what T-6 asserts -- is that the
        // browser presents no credential of its own; the BFF holds it server-side.
        requestCarriedAuthorization: Object.keys(request.headers ?? {}).some(
          (k) => k.toLowerCase() === 'authorization',
        ),
        requestBody: request.postData ?? null,
        // The protocol hands `postData` inline only for small bodies. A multipart upload
        // is not small, and "the browser sent no body" and "we did not ask for it" are
        // different facts -- so the flag is recorded and the body is fetched separately.
        requestHasPostData: request.hasPostData === true || request.postData !== undefined,
        requestBodyTruncated: false,
        status: null,
        statusText: null,
        responseHeaders: {},
        mimeType: null,
        responseBody: null,
        responseBodyTruncated: false,
        redirectedTo: null,
        finished: false,
        failure: null,
      };
      this.#exchanges.set(params.requestId, envelope);
      this.#order.push(params.requestId);
      if (!continuing) this.#inFlight += 1;
      return;
    }
    if (method === 'Network.responseReceived') {
      const envelope = this.#exchanges.get(params.requestId);
      if (envelope === undefined) return;
      envelope.status = params.response.status;
      envelope.statusText = params.response.statusText;
      envelope.responseHeaders = pick(params.response.headers, KEPT_RESPONSE_HEADERS);
      envelope.mimeType = params.response.mimeType;
      return;
    }
    if (method === 'Network.loadingFinished' || method === 'Network.loadingFailed') {
      if (this.#inFlight > 0) this.#inFlight -= 1;
      const envelope = this.#exchanges.get(params.requestId);
      if (envelope !== undefined) {
        envelope.finished = true;
        if (method === 'Network.loadingFailed') {
          envelope.failure = params.errorText ?? 'failed';
        }
      }
      return;
    }
    if (method === 'Runtime.consoleAPICalled' && params.type === 'error') {
      this.#consoleErrors.push(
        params.args.map((a) => a.value ?? a.description ?? a.type).join(' '),
      );
      return;
    }
    if (method === 'Runtime.exceptionThrown') {
      this.#pageErrors.push(
        params.exceptionDetails?.exception?.description ??
          params.exceptionDetails?.text ??
          'exception',
      );
    }
  }

  /** Navigate, settle, then pull every body the protocol still holds. */
  async goto(url, { settleMs = 700, timeoutMs = SETTLE_TIMEOUT_MS } = {}) {
    // Kept because W15-RUN's most useful single number was a duration -- eleven seconds of
    // "Loading the run request..." with no progress -- and a journey that records only
    // outcomes cannot report that.
    const t0 = Date.now();
    const result = await this.#send('Page.navigate', { url });
    if (result.errorText) {
      // A navigation that never reached a server is a failure of the journey, not a 0.
      throw new Error(`navigation to ${url} failed: ${result.errorText}`);
    }
    const t1 = Date.now();
    await this.#settle(settleMs, timeoutMs);
    const t2 = Date.now();
    await this.#collectBodies();
    const t3 = Date.now();
    this.timingsMs = { navigate: t1 - t0, settle: t2 - t1, bodies: t3 - t2 };
    return result;
  }

  /**
   * Settle on a quiet network, not on an empty one.
   *
   * Measured, not assumed: a Next.js screen on this origin leaves at least one request
   * open after the page is fully rendered -- a streamed response that never emits
   * `Network.loadingFinished`. Waiting for `inFlight === 0` therefore burned the full
   * timeout on *every* route, and a journey that always takes its timeout is a journey
   * nobody will run. Quiet is the honest signal: nothing has happened on this connection
   * for a while, so the page is done regardless of what is still nominally open.
   */
  async #settle(settleMs, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    const quietEnough = Math.max(settleMs, 1200);
    for (;;) {
      const quietFor = Date.now() - this.#lastActivity;
      if (this.#inFlight === 0 && quietFor >= settleMs) return;
      if (quietFor >= quietEnough) return;
      if (Date.now() > deadline) return;
      await new Promise((r) => setTimeout(r, 50));
    }
  }

  /**
   * Bodies must be fetched before the browser process ends -- this is the exact step the
   * 2026-09-16 harness skipped, and skipping it is what made `D-5` unanswerable.
   */
  async #collectBodies() {
    // A SNAPSHOT, not the live array. The run screen polls: while bodies are being
    // fetched it keeps issuing requests, so iterating `this.#order` directly never
    // terminates -- the list grows at least as fast as it is consumed. Measured, from a
    // journey that hung on exactly that route.
    for (const requestId of [...this.#order]) {
      const envelope = this.#exchanges.get(requestId);
      if (envelope === null || envelope === undefined) continue;
      // The REQUEST body, for anything that carried one. `D-5` was a `POST`: what the
      // browser sent is half the envelope, and the half the 2026-09-16 harness never had.
      // Truncated hard, because the multipart body of a PDF upload is the file itself and
      // storing it would make the envelope the fixture. The truncation keeps the part that
      // is evidence -- the boundary, the field names, the filename, the declared type.
      if (envelope.requestHasPostData && envelope.requestBody === null) {
        try {
          const { postData } = await withTimeout(
            this.#send('Network.getRequestPostData', { requestId: requestId.split('#')[0] }),
            5000,
          );
          if (typeof postData === 'string' && postData.length > 4096) {
            envelope.requestBody = postData.slice(0, 4096);
            envelope.requestBodyTruncated = true;
          } else {
            envelope.requestBody = postData ?? null;
          }
        } catch {
          envelope.requestBodyTruncated = true;
        }
      }
      if (envelope.redirectedTo !== null) continue;
      if (envelope.responseBody !== null || envelope.status === null) continue;
      if (envelope.resourceType === 'Image' || envelope.resourceType === 'Font') continue;
      if (!envelope.finished) {
        // `Network.getResponseBody` for a request the browser has not finished simply
        // never answers -- it does not error. Asking is how this hung. "Still open when
        // the page settled" is itself a fact worth keeping, so it is recorded as one.
        envelope.responseBody = null;
        envelope.responseBodyTruncated = true;
        envelope.failure = envelope.failure ?? 'still in flight when the page settled';
        continue;
      }
      try {
        const { body, base64Encoded } = await withTimeout(
          this.#send('Network.getResponseBody', { requestId: requestId.split('#')[0] }),
          5000,
        );
        const text = base64Encoded ? Buffer.from(body, 'base64').toString('utf8') : body;
        if (text.length > 200000) {
          envelope.responseBody = text.slice(0, 200000);
          envelope.responseBodyTruncated = true;
        } else {
          envelope.responseBody = text;
        }
      } catch {
        // A body the browser has already evicted is recorded as such rather than as empty:
        // "we did not keep it" and "it was empty" are different facts.
        envelope.responseBody = null;
        envelope.responseBodyTruncated = true;
      }
    }
  }

  async evaluate(expression) {
    const { result, exceptionDetails } = await this.#send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (exceptionDetails) {
      throw new Error(exceptionDetails.text ?? 'evaluate failed');
    }
    return result.value;
  }

  // ------------------------------------------------------------------------------------
  // The write half's primitives. `W22-E2E`.
  //
  // Everything above this line navigates and observes. Everything below it acts, and every
  // one of these reads back what the application did with the action -- because a write
  // primitive that silently does nothing turns a journey green while exercising nothing,
  // which is exactly the class of defect this instrument exists to find.
  // ------------------------------------------------------------------------------------

  /**
   * How the journey names one control.
   *
   * A CSS selector, optionally narrowed by the control's own visible text -- which is how
   * a user names a button ("the one that says Start run") and the only way to address the
   * Start-run control, since `web/src` gives it no id, no test id and no distinguishing
   * class. Exact match on trimmed text, never a substring: "Start run" and "Start run
   * anyway" are different controls.
   */
  static locator(selector, text = null) {
    const sel = JSON.stringify(selector);
    const txt = text === null ? 'null' : JSON.stringify(text);
    return `(() => {
      const all = Array.from(document.querySelectorAll(${sel}));
      const wanted = ${txt};
      if (wanted === null) return all.length === 0 ? null : all[0];
      return all.find((e) => (e.innerText ?? e.value ?? '').trim() === wanted) ?? null;
    })()`;
  }

  /** The element behind a locator, as a remote object id, for the node-taking domains. */
  async #objectIdOf(selector, text, what) {
    const { result, exceptionDetails } = await this.#send('Runtime.evaluate', {
      expression: Page.locator(selector, text),
      returnByValue: false,
    });
    if (exceptionDetails) {
      throw new Error(`${what}: evaluating the locator threw: ${exceptionDetails.text}`);
    }
    if (result.objectId === undefined) {
      throw new Error(`${what}: no element matches ${selector}${text === null ? '' : ` with text ${JSON.stringify(text)}`}`);
    }
    return result.objectId;
  }

  /** What the page can say about a control without acting on it. */
  async describe(selector, text = null) {
    return await this.evaluate(`(() => {
      const el = ${Page.locator(selector, text)};
      if (el === null) return null;
      el.scrollIntoView({ block: 'center', inline: 'center' });
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        type: el.getAttribute('type'),
        disabled: el.disabled === true,
        text: (el.innerText ?? '').trim().slice(0, 120),
        box: { x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height },
      };
    })()`);
  }

  /**
   * Press a control the way a mouse does -- a real `Input` event at the control's own
   * coordinates, not `element.click()`.
   *
   * `element.click()` would reach React's handler too, and would also "work" on a control
   * that is invisible, zero-sized or covered. Dispatching at coordinates means a control
   * the user could not press is a control this cannot press either, and a *disabled*
   * control is a hard failure rather than a click that goes nowhere: `Upload` and `Start
   * run` are both disabled while their mutation is pending, and pressing one in that state
   * and recording a pass is how a journey certifies nothing.
   */
  async click(selector, { text = null } = {}) {
    const what = `click ${selector}${text === null ? '' : ` [text=${JSON.stringify(text)}]`}`;
    const found = await this.describe(selector, text);
    if (found === null) throw new Error(`${what}: no element matches it`);
    if (found.disabled) {
      throw new Error(`${what}: the control is disabled, so pressing it would do nothing`);
    }
    if (found.box.w === 0 || found.box.h === 0) {
      throw new Error(`${what}: the control has a zero box (${found.box.w}x${found.box.h}), so no user could press it`);
    }
    const at = { x: found.box.x, y: found.box.y };
    await this.#send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...at, button: 'none', buttons: 0 });
    await this.#send('Input.dispatchMouseEvent', { type: 'mousePressed', ...at, button: 'left', buttons: 1, clickCount: 1 });
    await this.#send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...at, button: 'left', buttons: 0, clickCount: 1 });
    this.#lastActivity = Date.now();
    return found;
  }

  /**
   * Type into a control through the browser's own editing pipeline, then read the value
   * back off the control.
   *
   * The read-back is the whole point. These are React *controlled* inputs: their `value`
   * comes from component state, so text that the application's `onChange` did not accept
   * leaves the control empty however many keystrokes were delivered. Asserting the
   * read-back turns "the form was never filled" into a failure here, instead of into a
   * confusing absence of the request three steps later.
   */
  async fill(selector, value, { text = null } = {}) {
    const what = `fill ${selector}`;
    const found = await this.evaluate(`(() => {
      const el = ${Page.locator(selector, text)};
      if (el === null) return null;
      el.focus();
      if (typeof el.select === 'function') el.select();
      return { tag: el.tagName, focused: document.activeElement === el };
    })()`);
    if (found === null) throw new Error(`${what}: no element matches it`);
    if (!found.focused) throw new Error(`${what}: the control refused focus`);
    await this.#send('Input.insertText', { text: value });
    const readBack = await this.evaluate(`(${Page.locator(selector, text)}).value`);
    if (readBack !== value) {
      throw new Error(
        `${what}: typed ${JSON.stringify(value)} but the control reads ` +
          `${JSON.stringify(readBack)} -- the application did not take the keystrokes`,
      );
    }
    this.#lastActivity = Date.now();
    return readBack;
  }

  /**
   * Attach a file from disk to a file input, the way the operating system's file chooser
   * does -- `DOM.setFileInputFiles`, so the *browser* reads the bytes.
   *
   * The alternative was to build a `File` in page script from bytes this process read and
   * assign it through a `DataTransfer`. That would be the journey uploading its own
   * construction rather than the browser uploading a file, and the multipart body on the
   * wire is the thing under test.
   */
  async attachFile(selector, absolutePath, { text = null } = {}) {
    const what = `attachFile ${selector}`;
    if (!existsSync(absolutePath)) {
      throw new Error(`${what}: ${absolutePath} does not exist, so nothing would be uploaded`);
    }
    if (!this.#domEnabled) {
      await this.#send('DOM.enable', {});
      this.#domEnabled = true;
    }
    const objectId = await this.#objectIdOf(selector, text, what);
    await this.#send('DOM.setFileInputFiles', { files: [absolutePath], objectId });
    const chosen = await this.evaluate(`(() => {
      const el = ${Page.locator(selector, text)};
      const f = el === null ? null : (el.files ?? [])[0];
      return f === undefined || f === null ? null : { name: f.name, size: f.size, type: f.type };
    })()`);
    if (chosen === null) {
      throw new Error(`${what}: the browser reports no file on the input after attaching ${absolutePath}`);
    }
    this.#lastActivity = Date.now();
    return chosen;
  }

  /**
   * Wait on something the *application* renders, within a bound this caller must state.
   *
   * `boundMs` is required. There is no default, and there is no sleep anywhere in the
   * write half: a run reaches its terminal asynchronously since `W20-EXEC`, and the only
   * honest way to know it has is to read the state the app's own poller writes into the
   * DOM. Hitting the bound is a **finding with the last reading attached**, never a skip
   * and never a pass -- a journey that gives up quietly is worth less than no journey.
   *
   * Every distinct reading is kept with the millisecond it was first seen, so the envelope
   * carries `queued -> running -> published` as the browser saw it and not just the end.
   */
  async waitFor(expression, { boundMs, pollMs = 250, what = 'a condition' } = {}) {
    if (typeof boundMs !== 'number' || !Number.isFinite(boundMs) || boundMs <= 0) {
      throw new Error(`waitFor(${what}): boundMs is required and must be a positive number`);
    }
    const t0 = Date.now();
    const readings = [];
    let value = null;
    for (;;) {
      value = await this.evaluate(expression);
      const seen = JSON.stringify(value) ?? 'undefined';
      if (readings.length === 0 || readings[readings.length - 1].seen !== seen) {
        readings.push({ atMs: Date.now() - t0, seen, value });
      }
      if (value !== null && value !== undefined && value !== false && value !== '') {
        return { ok: true, value, waitedMs: Date.now() - t0, boundMs, readings, what };
      }
      if (Date.now() - t0 >= boundMs) {
        return { ok: false, value, waitedMs: Date.now() - t0, boundMs, readings, what };
      }
      await new Promise((r) => setTimeout(r, pollMs));
    }
  }

  /**
   * Let the page go quiet after an action, then pull every body the protocol still holds.
   *
   * `goto` does this for a navigation; an action needs it too, and for the same reason:
   * the bodies of the `POST` this session exists to record are evicted when the process
   * ends. This is the public half of what `goto` already does internally.
   */
  async settle({ settleMs = 700, timeoutMs = SETTLE_TIMEOUT_MS } = {}) {
    const t0 = Date.now();
    await this.#settle(settleMs, timeoutMs);
    await this.#collectBodies();
    return Date.now() - t0;
  }

  /**
   * A PNG of what this page is showing, written to `absolutePath`. Returns the path.
   *
   * **`D-55`, and why it is eight lines rather than a dependency.** `R-18` makes
   * presentation an acceptance condition, and the gate cannot see a stylesheet. `W31-STYLE`
   * was asked for rendered evidence, found this instrument could not produce it, built a
   * harness outside the tree and reported the gap -- and that harness died with the
   * session, which is `D-5` again. `Page.captureScreenshot` is in the same stable,
   * documented half of the protocol as the four domains this file already speaks, and
   * `Page.enable()` is already called in `enable()`, so nothing new is enabled and no
   * package is added.
   *
   * **`#send` was reported as the obstacle and is not one.** It is private to `Page`, so
   * code *outside* the class cannot reach the protocol -- which is what `W31-STYLE` ran
   * into, having no licence to edit this file. A method *on* `Page` is inside the class
   * and calls `this.#send` like every other primitive here. So the private field stays
   * private: widening it would have opened the whole protocol to callers in order to reach
   * one method, and the narrow surface is the property that has kept this file from growing
   * into a browser library.
   *
   * `fullPage` captures past the viewport by asking the page for its own content size,
   * rather than by trusting the window. `width`/`height` fix the viewport so the same
   * screen photographs the same way on a host whose default window differs; they are an
   * override, and omitting them leaves whatever the browser is already showing.
   *
   * **One measured property, said here rather than found later.** `cssContentSize` is the
   * content box, which excludes the scrollbar a taller-than-the-window document brings, so
   * a `fullPage` capture comes back **narrower than the viewport by the scrollbar's width**
   * -- 385 for a 400 viewport on this host. DevTools' own full-size capture does the same.
   * `prove_the_screenshot_sees.mjs` asserts it, so a change in it is visible.
   */
  async screenshot(absolutePath, { fullPage = false, width = null, height = null } = {}) {
    if (width !== null && height !== null) {
      await this.#send('Emulation.setDeviceMetricsOverride', {
        width, height, deviceScaleFactor: 1, mobile: false,
      });
    }
    const params = { format: 'png', captureBeyondViewport: fullPage };
    if (fullPage) {
      const { cssContentSize } = await this.#send('Page.getLayoutMetrics', {});
      params.clip = { x: 0, y: 0, ...cssContentSize, scale: 1 };
    }
    const { data } = await this.#send('Page.captureScreenshot', params);
    // An empty capture is a failure that looks exactly like a blank page, so it is named
    // here rather than written to disk as a zero-byte file the reader has to diagnose.
    if (!data) throw new Error(`Page.captureScreenshot returned no data for ${absolutePath}`);
    writeFileSync(absolutePath, Buffer.from(data, 'base64'));
    return absolutePath;
  }

  /** Where the browser currently is. A `router.push` moves this without a navigation. */
  async location() {
    return await this.evaluate('document.location.pathname + document.location.search');
  }

  // ------------------------------------------------------------------------------------
  // `W44-JOURNEY`. The session and the viewport: two things a profile can be told before
  // it navigates, and nothing else.
  // ------------------------------------------------------------------------------------

  /**
   * Fix the viewport. `D-93`.
   *
   * A width assertion against whatever window the host happened to give is not a
   * measurement, and `Emulation.setDeviceMetricsOverride` is the same call `screenshot`
   * already makes for the same reason. It is applied before the first navigation, so the
   * page is laid out at the declared width rather than reflowed into it.
   */
  async setViewport({ width, height }) {
    if (!Number.isInteger(width) || width <= 0 || !Number.isInteger(height) || height <= 0) {
      throw new Error(
        `setViewport: width and height must be positive integers; got ${width}x${height}`,
      );
    }
    await this.#send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: false,
    });
    this.viewport = { width, height };
  }

  /**
   * Put explicit cookies into this profile's jar.
   *
   * Through the **protocol**, not through `document.cookie`: the session cookie is
   * `HttpOnly` by design -- `app/bff/session/store.ts` -- and page script cannot read or
   * write it. Driving it from page script would mean the journey could only work against a
   * session the application does not actually issue, which is a measurement of a different
   * system.
   */
  async setCookies(cookies) {
    await this.#send('Network.setCookies', { cookies });
  }

  /**
   * One cookie, whole, so a caller can hand the same declaration to the next cold
   * profile.
   *
   * This is the only method in this file that returns a secret-shaped value, and it is
   * named so that a reader looking for "where could a credential leave the browser"
   * finds it. Its caller -- `session.mjs` -- keeps the value in a variable and puts the
   * cookie's NAME, never its value, into the envelope.
   */
  async cookieFor(name) {
    return (await this.#jar()).find((c) => c.name === name) ?? null;
  }

  /** Every cookie this profile holds, names and attributes; values are never returned. */
  async cookieNames() {
    return (await this.#jar()).map((c) => c.name).sort();
  }

  /**
   * The whole profile's jar -- `Storage.getCookies`, not `Network.getCookies`.
   *
   * Measured, and it cost a run: `Network.getCookies` with no `urls` answers for the
   * **frames of the current page**, so on `about:blank` -- which is where a profile sits
   * before its first navigation -- it answers `[]` however many cookies the profile
   * holds. That is the reading `D-16`'s check is taken from, and an empty answer there
   * reads exactly like a cookie that was never set. `Storage.getCookies` answers for the
   * browser, which is the thing the question is about.
   */
  async #jar() {
    const { cookies } = await this.#send('Storage.getCookies', {});
    return cookies;
  }

  /** Taken once, before the first navigation. `#startedWith` is what `D-16` is about. */
  async recordStartingJar() {
    this.#startedWith = await this.cookieNames();
  }

  /**
   * The cookie names this profile held **before it navigated anywhere**.
   *
   * A caller that injects one session cookie and reads back `['am_session']` on every
   * route has measured that each route began from an empty profile plus one stated value.
   * A caller that reads back anything else is looking at a browser that is not cold.
   */
  startedWith() {
    return this.#startedWith === null ? null : [...this.#startedWith];
  }

  exchanges() {
    return this.#order.map((id) => this.#exchanges.get(id)).filter(Boolean);
  }

  consoleErrors() {
    return [...this.#consoleErrors];
  }

  pageErrors() {
    return [...this.#pageErrors];
  }
}
