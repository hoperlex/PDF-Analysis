/**
 * The PC-01 journey's **write half**: create a project, upload the AR PDF, start a run --
 * through the browser, pressing the application's own controls, on the public origin.
 *
 * **Why this file exists.** `D-5` was `POST /api/v1/runs` -> 500, twice, through a browser,
 * on 2026-09-16. It closed *not reproducible*, permanently, because the harness that saw it
 * logged status lines only. `W21-E2E` committed the read walk and named this half in
 * `D-30`: the journey as it stood makes no `POST`, so it would not have caught the defect
 * that started the whole instrument.
 *
 * **What is asserted, per step.** That the control exists and is pressable; that the
 * browser sent the declared operation with the declared method to the declared path; that
 * it answered the declared status; that the **response body** says what the contract says
 * it says; that the screen afterwards rendered the success it claims and none of the
 * failure markers `web/src` defines; that **no** call on the BFF seam answered `>= 400`;
 * and that the browser presented no credential of its own.
 *
 * **Read the body, not the status.** `D-28`: `/projects/<anything>` answers 200 and renders
 * an error state, so a status code does not distinguish a working screen from a failing
 * one. Every step here therefore checks a rendered marker and a response field, not a
 * status alone -- and the `202` of `startRun` is checked for `state: "queued"`, because a
 * `202` that had already finished the work would be a different system.
 *
 * **Nothing here sleeps.** The run reaches its terminal asynchronously since `W20-EXEC`.
 * This waits on the attribute the run screen's own poller writes into the DOM, under a
 * bound the manifest states. Hitting the bound is a finding with every reading attached and
 * exit 1 -- never a skip, never a pass.
 *
 * ## `BETA-LIVE-JOURNEY-01`: the night window's screens, and refusals
 *
 * The four steps above are still the first four. The steps after them walk the screens the
 * 2026-10-20 night window added, and each screen has a negative case, so the vocabulary
 * grew by exactly what those needed -- and every addition is read by the same two
 * checkers (`tests/e2e/test_pc01_journey_conformance.py` and this file):
 *
 *   `as`                   which signed-in session performs the step. `admin` (the journey's
 *                          own account, holding both roles) unless the manifest's
 *                          `accounts` roster names another: an expert without `admin`, an
 *                          administrator without `expert`. A refusal by ROLE needs a session
 *                          that holds the role the screen refuses.
 *   `select`, `goto`,      three more things a user does: choose from a list, move to another
 *   `wait_for`             address, wait for a marker the screen draws.
 *   `click.times`          press the same control again before the page has answered -- a
 *                          second identical submit.
 *   `click.within`         press the control of the ROW whose words contain a text (`{selector,
 *                          text_contains}`): a list that draws one identical button per row and
 *                          gives the row no handle (`PC01-JOURNEY-GAPS-01`, «Блоки»).
 *   `expects_api[].refusal`  a declared refusal: the call is EXPECTED to answer `expect_status`
 *                          (and `expect_error_code`) and is exempt from the rule that any
 *                          `>= 400` on the seam is a finding. Nothing else is: an undeclared
 *                          `409` still reddens the step.
 *   `expects_api[].count`  how many times the browser made it. `1` after two presses is the
 *                          proof that a second identical submit sent nothing.
 *   `expects_not_called`   calls the browser must NOT make: a refusal made by the browser
 *                          before a byte is sent is exactly the absence of a request.
 *   `expects_present`      markers the screen must draw (with the words that must be in them).
 *   `captures`             several captures per step, including from a response body.
 *   `expects_download`     what a download answered: type, disposition, first bytes, the CSV's
 *                          width and its number of data rows, and that no CSV cell starts with a
 *                          character a spreadsheet would run.
 *
 * ## Which red step stops the walk
 *
 * The first four steps keep the original rule: the first red step stops the half, because
 * what they capture is what the next one addresses. A manifest that sets
 * `write.on_red: "continue_if_captured"` instead stops only the steps that NEED something
 * the red step failed to capture -- a step whose address or request path names a value no
 * earlier step produced is reported as not reached, never as passed -- so one defect does
 * not hide the screens that do not depend on it.
 */

import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

import { withColdBrowser } from './cdp.mjs';

/** The `{name}` placeholders a template mentions, in order of appearance. */
export function templateNames(template) {
  return typeof template === 'string'
    ? [...template.matchAll(/\{([a-z_]+)\}/g)].map((m) => m[1])
    : [];
}

/** `{project_uid}` -> the captured value, or a hard failure naming what is missing. */
function fill(template, captured) {
  return template.replace(/\{([a-z_]+)\}/g, (_, name) => {
    const value = captured[name];
    if (value === undefined) {
      throw new Error(
        `write step needs {${name}} but no earlier step captured it; ` +
          `captured so far: ${Object.keys(captured).join(', ') || '(nothing)'}`,
      );
    }
    return value;
  });
}

/**
 * Every captured name a step's addresses, requests and controls mention.
 *
 * A step's `bind` renames what a template variable means inside it: `{version_uid}` in a
 * step that works on the set's second version is the `second_version_uid` an earlier step
 * captured, while the address and the contract path keep the names the route and the
 * contract give them (so the gate can still compare them). A call may carry its own `bind`
 * -- the comparison page is the second version's, and the call it makes is addressed by the
 * first.
 */
export function namesNeededBy(step) {
  const names = new Set(step.needs ?? []);
  const take = (value, local = null) =>
    templateNames(value).forEach((name) => {
      const wanted = (local ?? {})[name] ?? (step.bind ?? {})[name] ?? name;
      // A constant is a member of an enumeration the step declares, not something captured.
      if (!(wanted in (step.constants ?? {}))) names.add(wanted);
    });
  take(step.at);
  for (const key of ['expects_api', 'expects_api_after_terminal', 'expects_not_called', 'expects_bff']) {
    for (const call of step[key] ?? []) take(call.path, call.bind);
  }
  for (const action of step.actions ?? []) {
    for (const key of ['selector', 'value', 'text', 'to', 'option_text', 'option_value', 'label']) {
      take(action[key]);
    }
    take(action.within?.text_contains);
  }
  for (const present of step.expects_present ?? []) {
    take(present.selector);
    take(present.text_contains);
    take(present.text_matches);
  }
  for (const selector of step.forbids_rendered ?? []) take(selector);
  for (const absent of step.expects_absent ?? []) {
    take(absent.selector);
    take(absent.text);
  }
  // What the step captures itself is not something it needs from an earlier step.
  for (const capture of [step.capture, ...(step.captures ?? [])]) {
    for (const produced of capture?.as ?? []) names.delete(produced);
  }
  return [...names];
}

/**
 * Whether the night-window steps may run against an origin, given what its provider reported.
 *
 * They start further runs, make accounts and change the origin's queue and norms snapshot. On
 * an origin that bills per run, or whose provider mode no earlier run has reported, that is not
 * done unasked (`--allow-spend`); `recorded` costs nothing and is the one mode that is.
 */
export function nightWindowMayRun({ providerMode, allowSpend }) {
  return allowSpend === true || providerMode === 'recorded';
}

/** `a.b.c` over a decoded JSON body. Absent is `undefined`, which is never a match. */
function atJsonPath(value, path) {
  let here = value;
  for (const key of path.split('.')) {
    if (here === null || typeof here !== 'object') return undefined;
    here = here[key];
  }
  return here;
}

function decodeJson(text) {
  if (typeof text !== 'string' || text.length === 0) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

/**
 * The cells of a CSV document (RFC 4180: quoted fields, doubled quotes, CRLF or LF rows).
 * A byte-order mark is skipped. Enough of a parser to ask "what does each cell start with".
 */
export function csvCells(text) {
  const source = text.startsWith('﻿') ? text.slice(1) : text;
  const cells = [];
  let cell = '';
  let quoted = false;
  let started = false;
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    if (quoted) {
      if (ch === '"' && source[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"' && !started) {
      quoted = true;
      started = true;
    } else if (ch === ',' || ch === '\n' || ch === '\r') {
      cells.push(cell);
      cell = '';
      started = false;
      if (ch === '\r' && source[i + 1] === '\n') i += 1;
    } else {
      cell += ch;
      started = true;
    }
  }
  if (started || cell !== '') cells.push(cell);
  return cells;
}

/**
 * The shape of a CSV document: the header's cell count and how many data rows follow it.
 * `rows` is `null` when the cells do not divide into whole rows of the header's width (a
 * ragged file), which is a finding in itself and never a count.
 */
export function csvShape(text) {
  const source = text.startsWith('\ufeff') ? text.slice(1) : text;
  const headerEnd = source.search(/\r?\n/);
  const header = headerEnd < 0 ? source : source.slice(0, headerEnd);
  const columns = csvCells(`${header}\n`).length;
  const cells = csvCells(source).length;
  return { columns, rows: columns > 0 && cells >= columns && cells % columns === 0 ? cells / columns - 1 : null };
}

/** A cell a spreadsheet would read as a formula: first non-space character `= + - @`, tab or CR. */
export function formulaLikeCells(cells) {
  return cells.filter((cell) => /^[ ]*[=+\-@\t\r]/.test(cell));
}

/** The concrete path of a declared call, or a hard failure naming the missing capture. */
function concretePath(expectation, captured) {
  return fill(expectation.path, captured);
}

/**
 * An exchange as the envelope may keep it: a request body that carries a password is
 * replaced. Form posts (`/bff/v1/session/password`, `/session`) and JSON bodies
 * (`temporary_password`, `new_password`) are both covered by what they are called.
 */
export function redactedExchange(exchange) {
  const body = exchange.requestBody;
  if (typeof body !== 'string' || body.length === 0) return exchange;
  let clean = body.replace(/(^|&)([a-z_]*password[a-z_]*)=[^&]*/gi, '$1$2=(redacted)');
  clean = clean.replace(/"([a-z_]*password[a-z_]*)"\s*:\s*"(?:[^"\\]|\\.)*"/gi, '"$1":"(redacted)"');
  return clean === body ? exchange : { ...exchange, requestBody: clean };
}

/**
 * Drive the write half.
 *
 * Returns the step records, the findings, and what it captured. It throws only when the
 * browser itself cannot be driven -- everything the *application* got wrong comes back as
 * a finding, so the envelope is written and the other steps still report.
 *
 * `sessions` maps a session name to the cookies that session carries; `cookies` is the
 * journey's own account and stays as the default for steps that name no `as`. `only` (a
 * list of step names) and `seed` (identifiers an earlier run captured) exist for working on
 * one step; a run that used them is partial, and the caller says so.
 */
export async function runWritePhase({
  origin,
  manifest,
  repositoryRoot,
  stamp,
  cookies = [],
  sessions = {},
  secrets = {},
  viewport = null,
  only = null,
  seed = {},
  allowSpend = false,
  provision = null,
}) {
  const spec = manifest.write;
  const ID = manifest.identifier_pattern;
  const API_PREFIX = manifest.api_prefix;
  const continueIfCaptured = spec.on_red === 'continue_if_captured';

  const failures = [];
  const records = [];
  const captured = { ...seed };
  // A password the journey typed (`secrets`) must reach neither a finding nor the envelope: a
  // message that quotes what a control read back, or a body the browser sent, is scrubbed here.
  const scrub = (text) =>
    Object.values(secrets)
      .filter((v) => typeof v === 'string' && v.length > 0)
      .reduce((t, v) => t.split(v).join('(redacted)'), String(text));
  const fail = (step, message) => failures.push(`${step}: ${scrub(message)}`);

  const fixture = resolve(repositoryRoot, spec.fixture);
  if (!existsSync(fixture)) {
    // Not a skip. A write half with no document to upload proves nothing, and saying so
    // and continuing would be the vacuous pass this instrument exists to rule out.
    fail('write', `the fixture ${spec.fixture} is not on disk at ${fixture}; nothing could be uploaded`);
    return { records, failures, captured, fixture: null, stopped: 'missing-fixture' };
  }
  const fixtureBytes = readFileSync(fixture).length;

  const sessionsByName = { admin: cookies, ...sessions };
  let stopped = null;
  let firstRed = null;
  // What the origin's provider mode was, as the run screen's own poll reported it. The night
  // window starts further runs; on an origin that bills per run that is money, so a step that
  // starts one waits for the provider mode to be known to be `recorded` or for `--allow-spend`.
  let providerMode = null;
  let nightRefused = false;
  let accountsMade = false;

  for (const step of spec.steps) {
    if (only !== null && !only.includes(step.name)) continue;

    const sessionName = step.as ?? 'admin';
    const sessionCookies = sessionsByName[sessionName];
    const record = {
      name: step.name,
      as: sessionName,
      at: step.at,
      url: null,
      actions: [],
      capturedHere: null,
      awaitTerminal: null,
      timingsMs: {},
    };
    records.push(record);

    // ---- a step whose inputs no earlier step produced is not reached, not passed ------
    const missing = namesNeededBy(step).filter((name) => captured[name] === undefined);
    if (missing.length > 0) {
      record.verdict = 'NOT REACHED';
      record.missingCaptures = missing;
      fail(
        step.name,
        `not reached: it needs ${missing.map((n) => `{${n}}`).join(', ')}, which no earlier ` +
          `step captured${firstRed === null ? '' : ` (the first red step was '${firstRed}')`}`,
      );
      console.log(`NOT ${step.name.padEnd(28)} needs ${missing.join(', ')}`);
      stopped = stopped ?? step.name;
      continue;
    }
    // ---- the night window runs only where it costs nothing ----------------------------
    // Its steps make accounts, pause dispatch, designate a norms snapshot and start further
    // runs. On an origin that bills per run, or whose provider mode is not known, that is not a
    // thing to do unasked: the first such step says so ONCE and the rest are not reached.
    if (step.screen !== undefined && step.reads_only !== true) {
      if (!nightWindowMayRun({ providerMode, allowSpend })) {
        if (!nightRefused) {
          nightRefused = true;
          fail(
            step.name,
            `not reached: the night-window steps start further runs, make accounts and change the ` +
              `origin's queue, and this origin's provider mode is ` +
              `${providerMode === null ? 'not known (no earlier run reported it)' : `'${providerMode}'`}, ` +
              `not 'recorded'. Walk such an origin with --phase core, or pass --allow-spend ` +
              `(E2E_PC01_ALLOW_SPEND=1) to say the cost and the changes are accepted. ` +
              `Every night-window step after this one is not reached for the same reason`,
          );
          console.log(`NOT night-window steps -- provider mode ${providerMode ?? 'unknown'}, not 'recorded'`);
        }
        record.verdict = 'NOT REACHED';
        stopped = stopped ?? step.name;
        continue;
      }
      if (!accountsMade && provision !== null) {
        accountsMade = true;
        const made = await provision();
        Object.assign(sessionsByName, made.sessions);
        Object.assign(captured, made.seed);
        for (const message of made.failures) failures.push(message);
      }
    }
    if (sessionCookies === undefined) {
      record.verdict = 'NOT REACHED';
      fail(
        step.name,
        `not reached: it runs as '${sessionName}', and no such session was opened ` +
          `(sessions: ${Object.keys(sessionsByName).join(', ')})`,
      );
      console.log(`NOT ${step.name.padEnd(28)} no session '${sessionName}'`);
      stopped = stopped ?? step.name;
      continue;
    }

    // What a template variable means in this step: the captured value of the same name,
    // unless the step (or the call) binds it to another captured name.
    const scope = (local = null) => {
      const view = { ...step.constants, ...captured };
      for (const bind of [step.bind, local]) {
        for (const [name, from] of Object.entries(bind ?? {})) view[name] = captured[from];
      }
      return view;
    };

    const url = origin + fill(step.at, scope());
    record.url = url;
    const t0 = Date.now();

    let ok = true;
    let downloadDir = null;
    const downloaded = new Map();
    try {
      await withColdBrowser(async (page) => {
        // `D-92`: every step of the write half POSTs, and the BFF answers 401 without a
        // session. The cookie is the one `session.mjs` obtained by driving `/login`, and
        // each step receives the SAME value rather than a jar carried on from the step
        // before -- so a step is still openable on its own, which is `D-16`'s property.
        record.startedWith = page.startedWith();
        try {
          await page.goto(url);
        } finally {
          record.navigationAttempts = page.navigationAttempts ?? null;
        }
        record.landedOn = await page.location();
        record.navigateTimingsMs = page.timingsMs;
        if ((step.expects_download ?? []).length > 0) {
          downloadDir = mkdtempSync(join(tmpdir(), 'e2e-pc01-downloads-'));
          await page.allowDownloads(downloadDir);
        }

        // ---- what the step captures, from what the application did ----------------
        // `when: "before_actions"` reads the screen as it loaded (the finding it opens on,
        // whose address the step's own call then carries); the rest read what the actions did.
        const runCapture = async (capture) => {
          let waited;
          if (capture.kind === 'attribute') {
            const expression = `(() => {
              const el = document.querySelector(${JSON.stringify(fill(capture.selector, scope()))});
              return el === null ? null : el.getAttribute(${JSON.stringify(capture.attribute)});
            })()`;
            waited = await page.waitFor(expression, {
              boundMs: capture.bound_ms,
              what: `${capture.selector}[${capture.attribute}]`,
            });
          } else if (capture.kind === 'text') {
            // A value the screen prints as words (a job's identity in the queue) and gives no
            // attribute: its text, found by selector, read when the whole text matches.
            const expression = `(() => {
              const el = document.querySelector(${JSON.stringify(fill(capture.selector, scope()))});
              return el === null ? null : (el.innerText ?? '').trim() || null;
            })()`;
            waited = await page.waitFor(expression, {
              boundMs: capture.bound_ms,
              what: `the text of ${capture.selector}`,
            });
          } else if (capture.kind === 'location') {
            const pattern = capture.pattern.replaceAll('%ID%', ID);
            const expression = `(() => {
              const m = ${JSON.stringify(pattern)};
              return new RegExp(m).test(document.location.pathname)
                ? document.location.pathname : null;
            })()`;
            waited = await page.waitFor(expression, {
              boundMs: capture.bound_ms,
              what: `the address to become ${capture.pattern}`,
            });
          } else if (capture.kind === 'response') {
            // The value is in a response body the browser already received: wait (bounded)
            // until the exchange is there and its field matches, reading the exchanges the
            // page recorded rather than anything the screen chose to draw.
            const call = (step.expects_api ?? []).find((c) => c.operationId === capture.of);
            if (call === undefined) {
              throw new Error(`step '${step.name}': capture of '${capture.of}' names no expects_api entry`);
            }
            const want = `${call.method} ${API_PREFIX}${concretePath(call, scope(call.bind))}`;
            const t = Date.now();
            let value = null;
            const readings = [];
            for (;;) {
              await page.settle({ settleMs: 300 });
              const hit = page
                .exchanges()
                .filter((e) => {
                  try {
                    return `${e.method} ${new URL(e.url).pathname}` === want;
                  } catch {
                    return false;
                  }
                })
                .map((e) => atJsonPath(decodeJson(e.responseBody) ?? {}, capture.json_path))
                .find((v) => v !== undefined && v !== null);
              if (hit !== undefined) {
                value = hit;
                break;
              }
              readings.push({ atMs: Date.now() - t, seen: 'no matching exchange with that field yet' });
              if (Date.now() - t >= capture.bound_ms) break;
              await new Promise((r) => setTimeout(r, 400));
            }
            waited = {
              ok: value !== null,
              value,
              waitedMs: Date.now() - t,
              boundMs: capture.bound_ms,
              readings,
              what: `${capture.of} response ${capture.json_path}`,
            };
          } else {
            throw new Error(`step '${step.name}': unknown capture kind '${capture.kind}'`);
          }
          record.capture = { ...(record.capture ?? {}), [capture.as.join('+')]: { ...capture, ...waited } };
          if (!waited.ok) {
            ok = false;
            fail(
              step.name,
              `after ${waited.waitedMs} ms (bound ${waited.boundMs} ms) the screen never ` +
                `offered ${waited.what}. Readings: ` +
                `${waited.readings.map((r) => `${r.atMs}ms ${r.seen}`).join(' | ') || '(none)'}`,
            );
          } else {
            const source =
              capture.kind === 'location' ? waited.value : String(waited.value);
            const pattern = new RegExp(
              (capture.matches ?? capture.pattern).replaceAll('%ID%', ID),
            );
            const hit = pattern.exec(source);
            if (hit === null) {
              ok = false;
              fail(
                step.name,
                `captured ${JSON.stringify(source)} which does not match ` +
                  `${capture.matches ?? capture.pattern}`,
              );
            } else {
              const values = hit.slice(1);
              record.capturedHere = record.capturedHere ?? {};
              capture.as.forEach((name, i) => {
                captured[name] = values[i];
                record.capturedHere[name] = values[i];
              });
              // The address changed, so the next screen is loading: let it, and keep its
              // traffic in this step's envelope rather than losing it between steps.
              if (capture.kind !== 'response') {
                record.timingsMs.settleAfterCapture = await page.settle();
              }
            }
          }
        };
        const captureSpecs = [step.capture, ...(step.captures ?? [])].filter(Boolean);
        for (const capture of captureSpecs.filter((c) => c.when === 'before_actions')) {
          await runCapture(capture);
        }

        // ---- press the application's own controls --------------------------------
        for (const action of step.actions ?? []) {
          const started = Date.now();
          const entry = { ...action, tookMs: null, result: null };
          record.actions.push(entry);
          const text = action.text === undefined ? null : fill(action.text, scope());
          const selector = action.selector === undefined ? undefined : fill(action.selector, scope());
          if (action.do === 'fill') {
            // `secret` names a password the journey holds in memory; the value typed is never
            // recorded, and neither is what the control read back.
            const typed =
              action.secret === undefined
                ? fill(action.value.replaceAll('%STAMP%', stamp), scope())
                : secrets[action.secret];
            if (typed === undefined) {
              throw new Error(`step '${step.name}': no secret named '${action.secret}'`);
            }
            entry.value = action.secret === undefined ? typed : `(secret ${action.secret})`;
            try {
              entry.result = await page.fill(selector, typed, {
                text,
                label: action.label ?? null,
                tag: action.tag ?? 'input',
                index: action.index ?? 0,
              });
            } catch (error) {
              throw new Error(scrub(error.message));
            }
            if (action.secret !== undefined) entry.result = '(secret)';
          } else if (action.do === 'click') {
            // `within` names the ROW the control sits in by the words in it (a project's name, a
            // version's identity) for lists whose rows carry no handle of their own.
            const within =
              action.within === undefined
                ? null
                : {
                    selector: action.within.selector,
                    text_contains: fill(action.within.text_contains.replaceAll('%STAMP%', stamp), scope()),
                  };
            entry.result = await page.click(selector, { text, times: action.times ?? 1, within });
          } else if (action.do === 'select') {
            const optionText =
              action.option_text === undefined
                ? null
                : fill(action.option_text.replaceAll('%STAMP%', stamp), scope());
            const optionValue =
              action.option_value === undefined ? null : fill(action.option_value, scope());
            entry.result = await page.select(selector, {
              label: action.label ?? null,
              index: action.index ?? 0,
              optionText,
              optionValue,
            });
          } else if (action.do === 'attach_file') {
            const path =
              action.fixture === true ? fixture : resolve(repositoryRoot, String(action.fixture));
            if (action.fixture === undefined || action.fixture === false) {
              throw new Error(`step '${step.name}': attach_file with no fixture`);
            }
            if (!existsSync(path)) {
              throw new Error(`step '${step.name}': the fixture ${action.fixture} is not on disk`);
            }
            const bytes = readFileSync(path).length;
            entry.path = path;
            entry.result = await page.attachFile(selector, path, { text });
            if (entry.result.size !== bytes) {
              fail(
                step.name,
                `the browser attached ${entry.result.size} bytes but ${action.fixture === true ? spec.fixture : action.fixture} is ` +
                  `${bytes} bytes on disk`,
              );
            }
          } else if (action.do === 'goto') {
            const to = origin + fill(action.to, scope());
            entry.to = to;
            await page.goto(to);
            entry.result = await page.location();
          } else if (action.do === 'wait_for') {
            const wantedText = action.text_contains === undefined ? null : fill(action.text_contains, scope());
            const expression = `(() => {
              const els = Array.from(document.querySelectorAll(${JSON.stringify(selector)}));
              const wanted = ${JSON.stringify(wantedText)};
              const hit = wanted === null ? els[0] : els.find((e) => (e.innerText ?? '').includes(wanted));
              return hit === undefined ? null : (hit.innerText ?? '').trim().slice(0, 200) || true;
            })()`;
            const waited = await page.waitFor(expression, {
              boundMs: action.bound_ms,
              what: `${selector}${wantedText === null ? '' : ` containing ${JSON.stringify(wantedText)}`}`,
            });
            entry.result = { ok: waited.ok, waitedMs: waited.waitedMs };
            if (!waited.ok) {
              ok = false;
              fail(
                step.name,
                `after ${waited.waitedMs} ms (bound ${waited.boundMs} ms) the screen never ` +
                  `offered ${waited.what}. Readings: ` +
                  `${waited.readings.map((r) => `${r.atMs}ms ${r.seen}`).join(' | ') || '(none)'}`,
              );
            }
          } else {
            throw new Error(`step '${step.name}': unknown action '${action.do}'`);
          }
          entry.tookMs = Date.now() - started;
          // A control that opens another view (a tab, a panel) needs the page to draw it
          // before the next action can find anything in it.
          if (action.settle === true) await page.settle();
        }

        record.timingsMs.settleAfterActions = await page.settle();

        for (const capture of captureSpecs.filter((c) => c.when !== 'before_actions')) {
          await runCapture(capture);
        }

        // ---- wait on the app's own state, under a stated bound --------------------
        if (ok && step.await_terminal) {
          const spec2 = step.await_terminal;
          const expression = `(() => {
            const el = document.querySelector(${JSON.stringify(spec2.outcome_selector)});
            if (el === null) return null;
            const v = el.getAttribute(${JSON.stringify(spec2.outcome_attribute)});
            // Three falsy readings that are three different facts, kept apart so the
            // envelope says which: \`null\` -- the screen has not rendered the outcome yet;
            // \`false\` -- it has, and the run is still in flight; anything else -- terminal.
            return v === null ? null : (v === ${JSON.stringify(spec2.non_terminal_value)} ? false : v);
          })()`;
          const waited = await page.waitFor(expression, {
            boundMs: spec2.bound_ms,
            pollMs: spec2.poll_ms ?? 500,
            what: `${spec2.outcome_selector} to leave '${spec2.non_terminal_value}'`,
          });
          record.timingsMs.settleAfterTerminal = await page.settle();
          record.awaitTerminal = {
            boundMs: waited.boundMs,
            waitedMs: waited.waitedMs,
            reached: waited.ok ? waited.value : null,
            readings: waited.readings,
          };
          if (!waited.ok) {
            ok = false;
            fail(
              step.name,
              `the run did not reach a terminal within the stated bound of ` +
                `${waited.boundMs} ms. It was still rendering ` +
                `'${spec2.non_terminal_value}' after ${waited.waitedMs} ms. This is a ` +
                `finding, not a skip: the readings are ` +
                `${waited.readings.map((r) => `${r.atMs}ms ${r.seen}`).join(' | ')}`,
            );
          } else if (!spec2.accept.includes(waited.value)) {
            ok = false;
            fail(
              step.name,
              `the run reached the terminal '${waited.value}', which is not one this ` +
                `journey accepts (${spec2.accept.join(', ')}). It published nothing.`,
            );
          }
          const activity = await page.evaluate(`(() => {
            const el = document.querySelector(${JSON.stringify(spec2.activity_selector)});
            return el === null ? null : el.getAttribute(${JSON.stringify(spec2.activity_attribute)});
          })()`);
          record.awaitTerminal.activity = activity;
          if (waited.ok && activity !== spec2.activity_when_final) {
            fail(
              step.name,
              `the run is terminal but the screen still reports activity ` +
                `'${activity}' rather than '${spec2.activity_when_final}'`,
            );
          }
        }

        // ---- markers the screen must draw -----------------------------------------
        record.present = [];
        for (const present of step.expects_present ?? []) {
          const selector = fill(present.selector, scope());
          const wantedText = present.text_contains === undefined ? null : fill(present.text_contains, scope());
          const min = present.min_count ?? 1;
          const matcher = present.text_matches === undefined ? null : fill(present.text_matches, scope());
          const expression = `(() => {
            const els = Array.from(document.querySelectorAll(${JSON.stringify(selector)}));
            const wanted = ${JSON.stringify(wantedText)};
            const pattern = ${JSON.stringify(matcher)} === null ? null : new RegExp(${JSON.stringify(matcher)});
            const hits = els
              .filter((e) => wanted === null || (e.innerText ?? '').includes(wanted))
              .filter((e) => pattern === null || pattern.test((e.innerText ?? '').trim()));
            return hits.length >= ${Number(min)} ? hits.length : null;
          })()`;
          const waited = await page.waitFor(expression, {
            boundMs: present.bound_ms ?? 10000,
            what: `${selector}${wantedText === null ? '' : ` containing ${JSON.stringify(wantedText)}`}${matcher === null ? '' : ` matching /${matcher}/`}`,
          });
          record.present.push({ selector, text_contains: wantedText, ok: waited.ok, count: waited.value });
          if (!waited.ok) {
            ok = false;
            const text = await page.evaluate(
              "document.body ? document.body.innerText.replace(/\\n{3,}/g, '\\n\\n').slice(0, 600) : ''",
            );
            fail(
              step.name,
              `the screen did not draw ${waited.what} (at least ${min}) within ` +
                `${waited.boundMs} ms. It rendered: ${JSON.stringify(text)}`,
            );
          }
        }

        // ---- the files a download left ----------------------------------------------
        // The browser must still be alive while it writes them, so they are collected here
        // and judged below, once the exchanges are in hand.
        if (downloadDir !== null) {
          const wanted = (step.expects_download ?? []).length;
          const began = Date.now();
          const finished = () =>
            readdirSync(downloadDir).filter((name) => !/\.(crdownload|tmp)$/.test(name) && !name.startsWith('.'));
          while (finished().length < wanted && Date.now() - began < 20000) {
            await new Promise((resolve) => setTimeout(resolve, 300));
          }
          // A finished file can still be growing for an instant after it appears.
          await new Promise((resolve) => setTimeout(resolve, 300));
          for (const name of finished()) {
            downloaded.set(name, readFileSync(join(downloadDir, name)));
          }
          record.downloadedFiles = [...downloaded].map(([name, bytes]) => ({ name, bytes: bytes.length }));
        }

        // ---- the envelope ---------------------------------------------------------
        record.timingsMs.settleBeforeEnvelope = await page.settle();
        record.bodyText = await page.evaluate(
          "document.body ? document.body.innerText.replace(/\\n{3,}/g, '\\n\\n') : ''",
        );
        record.finalLocation = await page.location();
        record.exchanges = page.exchanges().map(redactedExchange);
        record.consoleErrors = page.consoleErrors();
        record.pageErrors = page.pageErrors();

        // ---- what the screen must NOT offer ---------------------------------------
        // `expects_absent` is `forbids_rendered` for a control named by its words: the same
        // selector can match a control the role may use and one it may not.
        for (const absent of step.expects_absent ?? []) {
          const selector = fill(absent.selector, scope());
          const wantedText = absent.text === undefined ? null : fill(absent.text, scope());
          const found = await page.evaluate(`(() => {
            const wanted = ${JSON.stringify(wantedText)};
            const hit = Array.from(document.querySelectorAll(${JSON.stringify(selector)}))
              .find((e) => wanted === null || (e.innerText ?? e.value ?? '').trim() === wanted);
            return hit === undefined ? null : (hit.innerText ?? hit.outerHTML).trim().slice(0, 200);
          })()`);
          if (found !== null) {
            ok = false;
            fail(
              step.name,
              `the screen offered ${selector}${wantedText === null ? '' : ` “${wantedText}”`}, which this ` +
                `step declares must be absent: ${JSON.stringify(found)}`,
            );
          }
        }

        // ---- what the screen rendered afterwards ----------------------------------
        for (const selector of step.forbids_rendered ?? []) {
          const concrete = fill(selector, scope());
          const present = await page.evaluate(`(() => {
            const el = document.querySelector(${JSON.stringify(concrete)});
            return el === null ? null : (el.innerText ?? el.outerHTML).trim().slice(0, 300);
          })()`);
          if (present !== null) {
            ok = false;
            fail(
              step.name,
              `the screen rendered ${concrete}, which this step forbids: ${JSON.stringify(present)}`,
            );
          }
        }
      }, { cookies: sessionCookies, viewport });
    } catch (error) {
      // The browser could not be driven through this step. That is a finding about the
      // application or the origin, not a reason to report nothing.
      ok = false;
      fail(step.name, `could not be driven: ${error.message}`);
      record.drivingError = error.message;
      record.exchanges = record.exchanges ?? [];
    }

    record.timingsMs.total = Date.now() - t0;
    if (downloadDir !== null) rmSync(downloadDir, { recursive: true, force: true });

    // `D-16`, measured per step rather than claimed: this step opened in a profile holding
    // nothing but the cookies the journey explicitly handed it. A jar with anything else
    // in it means a browser was reused, which is the property `W19-SHELL` bought with one
    // process per step and the one this file must not spend.
    if (Array.isArray(record.startedWith)) {
      const startedWith = [...record.startedWith].sort();
      const handed = sessionCookies.map((c) => c.name).sort();
      if (startedWith.join(',') !== handed.join(',')) {
        ok = false;
        fail(
          step.name,
          `its browser started with cookies [${startedWith.join(', ') || '(none)'}] and ` +
            `the journey handed it [${handed.join(', ') || '(none)'}]`,
        );
      }
    }

    // ---- assertions over the recorded envelope ----------------------------------
    const exchanges = record.exchanges ?? [];
    const api = exchanges.filter((e) => {
      try {
        return new URL(e.url).pathname.startsWith(API_PREFIX);
      } catch {
        return false;
      }
    });
    record.observedApi = api.map((e) => `${e.method} ${new URL(e.url).pathname} -> ${e.status}`);

    const findAll = (method, path) => {
      const want = `${method} ${API_PREFIX}${path}`;
      return api.filter((e) => `${e.method} ${new URL(e.url).pathname}` === want);
    };
    const findExchange = (method, path) => findAll(method, path)[0] ?? null;

    /** Declared refusals: (method, concrete path, status) the step expects the seam to answer. */
    const declaredRefusals = [];
    const byOperation = new Map();
    for (const expectation of step.expects_api ?? []) {
      let concrete;
      try {
        concrete = concretePath(expectation, scope(expectation.bind));
      } catch (error) {
        fail(step.name, error.message);
        continue;
      }
      const matching = findAll(expectation.method, concrete);
      // For a refusal the exchange that carries the declared status is the one the
      // expectation is about; otherwise the first call of the operation is.
      const exchange =
        expectation.refusal === true
          ? (matching.find((e) => e.status === expectation.expect_status) ?? matching[0] ?? null)
          : (matching[0] ?? null);
      byOperation.set(expectation.operationId, exchange);
      if (expectation.refusal === true) {
        declaredRefusals.push({ method: expectation.method, path: concrete, status: expectation.expect_status });
      }
      if (exchange === null) {
        ok = false;
        fail(
          step.name,
          `declares ${expectation.method} ${API_PREFIX}${concrete} (${expectation.operationId}) ` +
            `but the browser did not make it. It made: ` +
            `${record.observedApi.join(' | ') || '(no API call at all)'}`,
        );
        continue;
      }
      if (exchange.status !== expectation.expect_status) {
        ok = false;
        fail(
          step.name,
          `${expectation.operationId} answered ${exchange.status} ${exchange.statusText ?? ''} ` +
            `and this step declares ${expectation.expect_status}. ` +
            `correlation-id: ${exchange.responseHeaders?.['x-correlation-id'] ?? '(none)'}; ` +
            `body: ${JSON.stringify((exchange.responseBody ?? '').slice(0, 400))}`,
        );
      }
      if (expectation.expect_error_code !== undefined) {
        const body = decodeJson(exchange.responseBody);
        const got = body === undefined ? undefined : body.error_code;
        if (got !== expectation.expect_error_code) {
          ok = false;
          fail(
            step.name,
            `${expectation.operationId} answered error_code ${JSON.stringify(got)} and this ` +
              `step declares ${JSON.stringify(expectation.expect_error_code)}: ` +
              `${JSON.stringify((exchange.responseBody ?? '').slice(0, 300))}`,
          );
        }
      }
      if (expectation.count !== undefined && matching.length !== expectation.count) {
        ok = false;
        fail(
          step.name,
          `${expectation.operationId} was sent ${matching.length} time(s) and this step ` +
            `declares ${expectation.count}: ${matching.map((e) => `${e.status}`).join(', ') || '(none)'}`,
        );
      }
      if (expectation.max_count !== undefined && matching.length > expectation.max_count) {
        ok = false;
        fail(
          step.name,
          `${expectation.operationId} was sent ${matching.length} time(s) and this step ` +
            `declares at most ${expectation.max_count}: ${matching.map((e) => `${e.status}`).join(', ')}`,
        );
      }
      // A second identical submit may reach the server (the page cannot always stop it);
      // what it must not do is change anything, so every answer must name the same thing.
      for (const path of expectation.same_response_at ?? []) {
        const values = matching.map((e) => atJsonPath(decodeJson(e.responseBody) ?? {}, path));
        if (new Set(values.map((v) => JSON.stringify(v))).size > 1) {
          ok = false;
          fail(
            step.name,
            `${expectation.operationId} was sent ${matching.length} time(s) and the answers ` +
              `disagree on ${path}: ${values.map((v) => JSON.stringify(v)).join(' | ')}`,
          );
        }
      }
    }

    for (const absent of step.expects_not_called ?? []) {
      let concrete;
      try {
        concrete = concretePath(absent, scope(absent.bind));
      } catch (error) {
        fail(step.name, error.message);
        continue;
      }
      const made = findAll(absent.method, concrete);
      if (made.length > 0) {
        ok = false;
        fail(
          step.name,
          `${absent.method} ${API_PREFIX}${concrete} must not be sent by this step (${absent.why ?? 'declared absent'}) ` +
            `but the browser sent it ${made.length} time(s): ${made.map((e) => e.status).join(', ')}`,
        );
      }
    }

    // The tier's own doors (`/session`, `/session/end`, `/session/password`) are no operation
    // of the contract: the browser posts a form and the tier answers a redirect. They are
    // declared apart from `expects_api`, with the status and, for a redirect, where it leads.
    for (const door of step.expects_bff ?? []) {
      const made = findAll(door.method, concretePath(door, scope(door.bind)));
      if (made.length === 0) {
        ok = false;
        fail(step.name, `declares ${door.method} ${API_PREFIX}${door.path} but the browser did not make it. It made: ${record.observedApi.join(' | ') || '(no API call at all)'}`);
        continue;
      }
      const hit = made.find((e) => e.status === door.expect_status) ?? made[0];
      if (hit.status !== door.expect_status) {
        ok = false;
        fail(step.name, `${door.method} ${API_PREFIX}${door.path} answered ${hit.status} and this step declares ${door.expect_status}`);
      }
      if (door.redirect_contains !== undefined && !String(hit.redirectedTo ?? '').includes(door.redirect_contains)) {
        ok = false;
        fail(step.name, `${door.method} ${API_PREFIX}${door.path} redirected to ${JSON.stringify(hit.redirectedTo)}, not to something containing ${JSON.stringify(door.redirect_contains)}`);
      }
      if (door.count !== undefined && made.length !== door.count) {
        ok = false;
        fail(step.name, `${door.method} ${API_PREFIX}${door.path} was sent ${made.length} time(s) and this step declares ${door.count}`);
      }
    }
    if (step.expects_location !== undefined) {
      const where = String(record.finalLocation ?? '');
      if (!where.startsWith(step.expects_location)) {
        ok = false;
        fail(step.name, `the browser ended at ${JSON.stringify(where)} and this step declares an address starting ${JSON.stringify(step.expects_location)}`);
      }
    }

    // `D-5` in one line: a call on the seam that answered an error, whatever the screen
    // then chose to render. This is what the 2026-09-16 harness saw and could not keep. A
    // refusal the step DECLARES (same method, same path, same status) is the one exception.
    for (const exchange of api) {
      if (typeof exchange.status !== 'number' || exchange.status < 400) continue;
      const path = new URL(exchange.url).pathname;
      const declared = declaredRefusals.some(
        (r) => `${r.method} ${API_PREFIX}${r.path}` === `${exchange.method} ${path}` && r.status === exchange.status,
      );
      if (declared) continue;
      ok = false;
      fail(
        step.name,
        `${exchange.method} ${path} answered ${exchange.status}. ` +
          `correlation-id: ${exchange.responseHeaders?.['x-correlation-id'] ?? '(none)'}; ` +
          `body: ${JSON.stringify((exchange.responseBody ?? '').slice(0, 400))}`,
      );
    }

    for (const check of step.expects_request ?? []) {
      const exchange = byOperation.get(check.of);
      if (!exchange) continue;
      const contentType = exchange.requestHeaders?.['content-type'] ?? '';
      if (check.content_type_starts_with && !contentType.startsWith(check.content_type_starts_with)) {
        ok = false;
        fail(
          step.name,
          `${check.of} was sent as '${contentType}' and this step declares ` +
            `'${check.content_type_starts_with}...'`,
        );
      }
      for (const needle of check.body_contains ?? []) {
        if (!(exchange.requestBody ?? '').includes(needle)) {
          ok = false;
          fail(
            step.name,
            `${check.of}'s request body does not contain ${JSON.stringify(needle)}` +
              `${exchange.requestBody === null ? ' (no request body was recorded at all)' : ''}`,
          );
        }
      }
    }

    for (const check of step.expects_response ?? []) {
      const exchange = byOperation.get(check.of);
      if (!exchange) continue;
      const decoded = decodeJson(exchange.responseBody);
      if (decoded === undefined) {
        ok = false;
        fail(
          step.name,
          `${check.of} answered a body this journey could not decode as JSON: ` +
            `${JSON.stringify((exchange.responseBody ?? '').slice(0, 200))}`,
        );
        continue;
      }
      const value = atJsonPath(decoded, check.json_path);
      if (check.equals !== undefined && value !== check.equals) {
        ok = false;
        fail(
          step.name,
          `${check.of}'s response has ${check.json_path} = ${JSON.stringify(value)} ` +
            `and this step declares ${JSON.stringify(check.equals)}`,
        );
      }
      if (check.not_equals !== undefined && value === check.not_equals) {
        ok = false;
        fail(
          step.name,
          `${check.of}'s response has ${check.json_path} = ${JSON.stringify(value)}, ` +
            `which this step declares it must not be`,
        );
      }
      if (check.at_least !== undefined && !(typeof value === 'number' && value >= check.at_least)) {
        ok = false;
        fail(
          step.name,
          `${check.of}'s response has ${check.json_path} = ${JSON.stringify(value)}, ` +
            `which is not a number of at least ${check.at_least}`,
        );
      }
      if (check.nonempty_array === true && !(Array.isArray(value) && value.length > 0)) {
        ok = false;
        fail(
          step.name,
          `${check.of}'s response has ${check.json_path} = ${JSON.stringify(value)?.slice(0, 120)}, ` +
            `which is not a non-empty array`,
        );
      }
      if (check.matches !== undefined) {
        const pattern = new RegExp(check.matches.replaceAll('%ID%', ID));
        if (typeof value !== 'string' || !pattern.test(value)) {
          ok = false;
          fail(
            step.name,
            `${check.of}'s response has ${check.json_path} = ${JSON.stringify(value)} ` +
              `which does not match ${check.matches}`,
          );
        }
      }
    }

    // ---- what a download answered ------------------------------------------------
    // The status and headers are the exchange's; the BYTES are the file the browser saved,
    // because the protocol does not give a download's body to `Network.getResponseBody`.
    record.downloads = [];
    for (const check of step.expects_download ?? []) {
      const exchange = byOperation.get(check.of) ?? null;
      const summary = { of: check.of, ok: true };
      record.downloads.push(summary);
      if (exchange === null) {
        ok = false;
        summary.ok = false;
        fail(step.name, `declares a download of ${check.of} but the browser did not make that call`);
        continue;
      }
      const type = exchange.responseHeaders?.['content-type'] ?? '';
      const disposition = exchange.responseHeaders?.['content-disposition'] ?? '';
      const named = /filename="?([^";]+)"?/.exec(disposition);
      // The file the browser saved is named by the page (`<id>-proposals.csv`), not by the
      // response's disposition (`<id>.csv`): the response names the file by its extension,
      // and the one saved file with that extension -- or, among several, the one that starts
      // with the response's name -- is the download.
      const dot = named === null ? -1 : named[1].lastIndexOf('.');
      const stem = named === null ? '' : dot < 0 ? named[1] : named[1].slice(0, dot);
      const extension = named === null || dot < 0 ? '' : named[1].slice(dot);
      const sameKind = [...downloaded.keys()].filter((name) => extension !== '' && name.endsWith(extension));
      const savedAs =
        named === null
          ? undefined
          : downloaded.has(named[1])
            ? named[1]
            : sameKind.length === 1
              ? sameKind[0]
              : sameKind.find((name) => name.startsWith(stem));
      const bytes = savedAs === undefined ? undefined : downloaded.get(savedAs);
      summary.contentType = type;
      summary.contentDisposition = disposition;
      summary.fileName = savedAs ?? null;
      summary.fileBytes = bytes === undefined ? null : bytes.length;
      const problems = [];
      if (bytes === undefined) {
        problems.push(
          `the browser saved no file named ${JSON.stringify(named === null ? '(no filename in the disposition)' : named[1])}; ` +
            `it saved ${JSON.stringify([...downloaded.keys()])}`,
        );
      }
      const body = bytes === undefined ? '' : /^text\/|json/.test(type) ? bytes.toString('utf8') : bytes.toString('latin1');
      summary.bodyChars = body.length;
      if (check.content_type_starts_with && !type.startsWith(check.content_type_starts_with)) {
        problems.push(`content-type is '${type}', declared '${check.content_type_starts_with}...'`);
      }
      if (check.content_disposition_contains && !disposition.includes(check.content_disposition_contains)) {
        problems.push(`content-disposition is '${disposition}', declared to contain '${check.content_disposition_contains}'`);
      }
      if (bytes !== undefined && check.body_starts_with !== undefined && !body.startsWith(check.body_starts_with)) {
        problems.push(`the file starts ${JSON.stringify(body.slice(0, 12))}, declared ${JSON.stringify(check.body_starts_with)}`);
      }
      for (const needle of bytes === undefined ? [] : check.body_contains ?? []) {
        if (!body.includes(needle)) problems.push(`the file does not contain ${JSON.stringify(needle)}`);
      }
      if (bytes !== undefined && check.csv_columns !== undefined) {
        const header = body.replace(/^\ufeff/, '').split(/\r?\n/, 1)[0] ?? '';
        const columns = csvCells(`${header}\n`).length;
        summary.csvColumns = columns;
        if (columns !== check.csv_columns) {
          problems.push(`the CSV header has ${columns} column(s), declared ${check.csv_columns}`);
        }
      }
      if (bytes !== undefined && check.csv_data_rows !== undefined) {
        const shape = csvShape(body);
        summary.csvDataRows = shape.rows;
        if (shape.rows !== check.csv_data_rows) {
          problems.push(
            `the CSV holds ${shape.rows === null ? 'a ragged set of cells (not whole rows)' : `${shape.rows} data row(s)`}, ` +
              `declared ${check.csv_data_rows}`,
          );
        }
      }
      if (bytes !== undefined && check.csv_no_formula_cells === true) {
        const cells = csvCells(body);
        const formulas = formulaLikeCells(cells);
        summary.csvCells = cells.length;
        summary.formulaLikeCells = formulas.slice(0, 5);
        if (formulas.length > 0) {
          problems.push(
            `${formulas.length} CSV cell(s) start with a formula character: ` +
              `${JSON.stringify(formulas.slice(0, 3))}`,
          );
        }
      }
      if (problems.length > 0) {
        ok = false;
        summary.ok = false;
        fail(step.name, `${check.of} download: ${problems.join('; ')}`);
      }
    }

    for (const expectation of step.expects_api_after_terminal ?? []) {
      let concrete;
      try {
        concrete = concretePath(expectation, scope(expectation.bind));
      } catch (error) {
        fail(step.name, error.message);
        continue;
      }
      const seen = api.filter(
        (e) => `${e.method} ${new URL(e.url).pathname}` === `${expectation.method} ${API_PREFIX}${concrete}`,
      );
      record.pollerReadings = seen
        .map((e) => atJsonPath(decodeJson(e.responseBody) ?? {}, 'state'))
        .filter((s) => s !== undefined);
      if (seen.length === 0) {
        ok = false;
        fail(
          step.name,
          `declares ${expectation.method} ${API_PREFIX}${concrete} (${expectation.operationId}) ` +
            `after the terminal, but the browser never polled it`,
        );
      }
    }

    for (const needle of step.expects_rendered ?? []) {
      if (!(record.bodyText ?? '').includes(needle)) {
        ok = false;
        fail(
          step.name,
          `the screen did not render ${JSON.stringify(needle)}. It rendered: ` +
            `${JSON.stringify((record.bodyText ?? '').slice(0, 300))}`,
        );
      }
    }

    if ((record.pageErrors ?? []).length > 0) {
      ok = false;
      fail(step.name, `threw ${record.pageErrors.length} uncaught exception(s): ${record.pageErrors[0]}`);
    }

    const credentialled = exchanges.filter((e) => e.requestCarriedAuthorization);
    record.requestsCarryingAuthorization = credentialled.map((e) => `${e.method} ${e.url}`);
    if (credentialled.length > 0) {
      ok = false;
      fail(
        step.name,
        `${credentialled.length} browser request(s) carried an Authorization header; T-6 ` +
          `puts the credential in the BFF, server-side: ${record.requestsCarryingAuthorization.join(', ')}`,
      );
    }

    for (const exchange of exchanges) {
      const mode = atJsonPath(decodeJson(exchange.responseBody) ?? {}, 'provider_mode');
      if (typeof mode === 'string' && /\/runs\/run_/.test(String(exchange.url))) providerMode = mode;
    }
    record.verdict = ok ? 'ok' : 'RED';
    console.log(
      `${ok ? 'ok  ' : 'RED '}${step.name.padEnd(28)} ` +
        `as=${sessionName} api=${record.observedApi.length} ` +
        `${record.capturedHere ? JSON.stringify(record.capturedHere) : ''} ` +
        `${record.awaitTerminal ? `terminal=${record.awaitTerminal.reached} in ${record.awaitTerminal.waitedMs}ms/${record.awaitTerminal.boundMs}ms` : ''}`,
    );

    if (!ok) {
      firstRed = firstRed ?? step.name;
      if (!continueIfCaptured) {
        // The original rule: what a red step failed to capture is what the next step
        // addresses, so nothing after it is meaningful.
        console.error(
          `\ne2e:pc01: stopping the write half at '${step.name}'. ` +
            `The steps after it were NOT checked.`,
        );
        return { records, failures, captured, fixture, stopped: step.name };
      }
    }
  }

  return { records, failures, captured, fixture, stopped };
}
