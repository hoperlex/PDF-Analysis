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
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { withColdBrowser } from './cdp.mjs';

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
 * Drive the write half.
 *
 * Returns the step records, the findings, and what it captured. It throws only when the
 * browser itself cannot be driven -- everything the *application* got wrong comes back as
 * a finding, so the envelope is written and the other steps still report.
 */
export async function runWritePhase({ origin, manifest, repositoryRoot, stamp }) {
  const spec = manifest.write;
  const ID = manifest.identifier_pattern;
  const API_PREFIX = manifest.api_prefix;

  const failures = [];
  const records = [];
  const captured = {};
  const fail = (step, message) => failures.push(`${step}: ${message}`);

  const fixture = resolve(repositoryRoot, spec.fixture);
  if (!existsSync(fixture)) {
    // Not a skip. A write half with no document to upload proves nothing, and saying so
    // and continuing would be the vacuous pass this instrument exists to rule out.
    fail('write', `the fixture ${spec.fixture} is not on disk at ${fixture}; nothing could be uploaded`);
    return { records, failures, captured, fixture: null, stopped: 'missing-fixture' };
  }
  const fixtureBytes = readFileSync(fixture).length;

  for (const step of spec.steps) {
    const url = origin + fill(step.at, captured);
    const record = {
      name: step.name,
      at: step.at,
      url,
      actions: [],
      capturedHere: null,
      awaitTerminal: null,
      timingsMs: {},
    };
    records.push(record);
    const t0 = Date.now();

    let ok = true;
    try {
      await withColdBrowser(async (page) => {
        await page.goto(url);
        record.landedOn = await page.location();
        record.navigateTimingsMs = page.timingsMs;

        // ---- press the application's own controls --------------------------------
        for (const action of step.actions) {
          const started = Date.now();
          const entry = { ...action, tookMs: null, result: null };
          record.actions.push(entry);
          if (action.do === 'fill') {
            entry.value = action.value.replaceAll('%STAMP%', stamp);
            entry.result = await page.fill(action.selector, entry.value, {
              text: action.text ?? null,
            });
          } else if (action.do === 'click') {
            entry.result = await page.click(action.selector, { text: action.text ?? null });
          } else if (action.do === 'attach_file') {
            if (action.fixture !== true) {
              throw new Error(`step '${step.name}': attach_file with no fixture`);
            }
            entry.path = fixture;
            entry.result = await page.attachFile(action.selector, fixture, {
              text: action.text ?? null,
            });
            if (entry.result.size !== fixtureBytes) {
              fail(
                step.name,
                `the browser attached ${entry.result.size} bytes but ${spec.fixture} is ` +
                  `${fixtureBytes} bytes on disk`,
              );
            }
          } else {
            throw new Error(`step '${step.name}': unknown action '${action.do}'`);
          }
          entry.tookMs = Date.now() - started;
        }

        record.timingsMs.settleAfterActions = await page.settle();

        // ---- what the step captures, from what the application did ----------------
        if (step.capture) {
          const capture = step.capture;
          let waited;
          if (capture.kind === 'attribute') {
            const expression = `(() => {
              const el = document.querySelector(${JSON.stringify(capture.selector)});
              return el === null ? null : el.getAttribute(${JSON.stringify(capture.attribute)});
            })()`;
            waited = await page.waitFor(expression, {
              boundMs: capture.bound_ms,
              what: `${capture.selector}[${capture.attribute}]`,
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
          } else {
            throw new Error(`step '${step.name}': unknown capture kind '${capture.kind}'`);
          }
          record.capture = { ...capture, ...waited };
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
              record.capturedHere = {};
              capture.as.forEach((name, i) => {
                captured[name] = values[i];
                record.capturedHere[name] = values[i];
              });
              // The address changed, so the next screen is loading: let it, and keep its
              // traffic in this step's envelope rather than losing it between steps.
              record.timingsMs.settleAfterCapture = await page.settle();
            }
          }
        }

        // ---- wait on the app's own state, under a stated bound --------------------
        if (ok && step.await_terminal) {
          const spec2 = step.await_terminal;
          const expression = `(() => {
            const el = document.querySelector(${JSON.stringify(spec2.outcome_selector)});
            if (el === null) return null;
            const v = el.getAttribute(${JSON.stringify(spec2.outcome_attribute)});
            return v === null || v === ${JSON.stringify(spec2.non_terminal_value)} ? null : v;
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

        // ---- the envelope ---------------------------------------------------------
        record.bodyText = await page.evaluate(
          "document.body ? document.body.innerText.replace(/\\n{3,}/g, '\\n\\n') : ''",
        );
        record.finalLocation = await page.location();
        record.exchanges = page.exchanges();
        record.consoleErrors = page.consoleErrors();
        record.pageErrors = page.pageErrors();

        // ---- what the screen rendered afterwards ----------------------------------
        for (const selector of step.forbids_rendered ?? []) {
          const present = await page.evaluate(`(() => {
            const el = document.querySelector(${JSON.stringify(selector)});
            return el === null ? null : (el.innerText ?? el.outerHTML).trim().slice(0, 300);
          })()`);
          if (present !== null) {
            ok = false;
            fail(
              step.name,
              `the screen rendered ${selector}, which this step forbids: ${JSON.stringify(present)}`,
            );
          }
        }
      });
    } catch (error) {
      // The browser could not be driven through this step. That is a finding about the
      // application or the origin, not a reason to report nothing.
      ok = false;
      fail(step.name, `could not be driven: ${error.message}`);
      record.drivingError = error.message;
      record.exchanges = record.exchanges ?? [];
    }

    record.timingsMs.total = Date.now() - t0;

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

    const findExchange = (method, path) => {
      const want = `${method} ${API_PREFIX}${path}`;
      return api.find((e) => `${e.method} ${new URL(e.url).pathname}` === want) ?? null;
    };

    const byOperation = new Map();
    for (const expectation of step.expects_api ?? []) {
      let concrete;
      try {
        concrete = fill(expectation.path, captured);
      } catch (error) {
        fail(step.name, error.message);
        continue;
      }
      const exchange = findExchange(expectation.method, concrete);
      byOperation.set(expectation.operationId, exchange);
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
    }

    // `D-5` in one line: a call on the seam that answered an error, whatever the screen
    // then chose to render. This is what the 2026-09-16 harness saw and could not keep.
    for (const exchange of api) {
      if (typeof exchange.status === 'number' && exchange.status >= 400) {
        ok = false;
        fail(
          step.name,
          `${exchange.method} ${new URL(exchange.url).pathname} answered ${exchange.status}. ` +
            `correlation-id: ${exchange.responseHeaders?.['x-correlation-id'] ?? '(none)'}; ` +
            `body: ${JSON.stringify((exchange.responseBody ?? '').slice(0, 400))}`,
        );
      }
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

    for (const expectation of step.expects_api_after_terminal ?? []) {
      let concrete;
      try {
        concrete = fill(expectation.path, captured);
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

    record.verdict = ok ? 'ok' : 'RED';
    console.log(
      `${ok ? 'ok  ' : 'RED '}${step.name.padEnd(16)} ` +
        `api=${record.observedApi.length} ` +
        `${record.capturedHere ? JSON.stringify(record.capturedHere) : ''} ` +
        `${record.awaitTerminal ? `terminal=${record.awaitTerminal.reached} in ${record.awaitTerminal.waitedMs}ms/${record.awaitTerminal.boundMs}ms` : ''}`,
    );

    // A step that did not capture what the next step addresses makes every step after it
    // meaningless rather than red. Stop and say so -- the same rule as the read walk.
    if (!ok) {
      console.error(
        `\ne2e:pc01: stopping the write half at '${step.name}'. ` +
          `The steps after it were NOT checked.`,
      );
      return { records, failures, captured, fixture, stopped: step.name };
    }
  }

  return { records, failures, captured, fixture, stopped: null };
}
