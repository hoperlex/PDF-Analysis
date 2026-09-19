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
 * What it deliberately does NOT do: selector engines, auto-waiting, actionability checks,
 * downloads, video. This journey navigates, records and reads text. Anything that needs
 * more than that is a reason to reopen the dependency question, not to grow this file.
 */

import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync } from 'node:fs';
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
 */
export async function withColdBrowser(fn) {
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
