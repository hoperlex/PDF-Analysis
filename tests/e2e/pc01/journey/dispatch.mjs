/**
 * Hold dispatch paused around a read walk, through the API, as the administrator (`D-380`, lane J2).
 *
 * The frame's end group («Выдача приостановлена», «Возобновить», the instance mark, the account) overflowed
 * only while dispatch was paused, and the ordinary read walk runs with dispatch open. The write half pauses and
 * resumes through the queue screen's buttons (`queue-pause-dispatch`, `queue-resume-dispatch`); those steps prove
 * the buttons and leave no state behind to read. This is the other half: the state itself, held for a walk.
 *
 * ## Through the API, from a browser
 *
 * `PUT /bff/v1/execution/dispatch` with `{"paused": true}` and an idempotency key, sent by `fetch` from a page
 * of the stand's own origin in a cold browser that carries the administrator's session cookie -- the same
 * request the screen's button makes, to the same seam, with no credential in the browser (`T-6`). The page is
 * the seam's own GET answer, a document without the application's script, so nothing but this call runs.
 *
 * ## What it promises
 *
 *  * it reads the state first and the state after, and says "paused" only when the API said it;
 *  * it restores what it found: a stand that was paused before the walk is left paused, one that was open is
 *    resumed (and a resume that does not take is a finding, not a shrug);
 *  * `journey.mjs` calls {@link restoreDispatch} in a `finally`, so a walk that throws does not leave an
 *    administrator's stand paused.
 */

import { randomBytes } from 'node:crypto';

import { withColdBrowser } from './cdp.mjs';

export const DISPATCH_PATH = '/execution/dispatch';

/**
 * The page-side expression: one `fetch` of the dispatch seam, `paused === null` meaning a read. The answer
 * is reduced to what a verdict needs, so the envelope keeps no more of a body than it must.
 */
export function dispatchExpression(apiPrefix, paused, idempotencyKey) {
  const url = `${apiPrefix}${DISPATCH_PATH}`;
  const init =
    paused === null
      ? { method: 'GET', credentials: 'same-origin', headers: { accept: 'application/json' } }
      : {
          method: 'PUT',
          credentials: 'same-origin',
          headers: {
            accept: 'application/json',
            'content-type': 'application/json',
            'idempotency-key': idempotencyKey,
          },
          body: JSON.stringify({ paused }),
        };
  return `(async () => {
    const response = await fetch(${JSON.stringify(url)}, ${JSON.stringify(init)});
    const text = await response.text();
    let body = null;
    try { body = JSON.parse(text); } catch { body = null; }
    return {
      status: response.status,
      correlationId: response.headers.get('x-correlation-id'),
      paused: body !== null && typeof body === 'object' ? body.paused ?? null : null,
      changedAt: body !== null && typeof body === 'object' ? body.changed_at ?? null : null,
      text: text.slice(0, 300),
    };
  })()`;
}

/** An idempotency key the contract accepts (`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`), unique per command. */
export function newDispatchKey() {
  return `ik_j2_${randomBytes(12).toString('hex')}`;
}

/** One answer, as a sentence a finding can carry. */
export function describeAnswer(answer) {
  if (answer === null || answer === undefined) return '(no answer)';
  return `${answer.status} paused=${JSON.stringify(answer.paused)} correlation-id ${answer.correlationId ?? '(none)'}` +
    (answer.status >= 400 ? ` body ${JSON.stringify(answer.text)}` : '');
}

/**
 * The verdict over the three answers of one entry into a state: the read before, the command, the read after.
 * `want` is the state asked for. Returns the findings, `[]` when the API says it is in the state asked for.
 */
export function entryFindings(want, { before, command, after }) {
  const findings = [];
  const label = want ? 'pause' : 'resume';
  if (before == null || before.status !== 200 || typeof before.paused !== 'boolean') {
    findings.push(`dispatch: the state could not be read before the ${label} (${describeAnswer(before)})`);
    return findings;
  }
  if (before.paused === want) {
    // Already in the state asked for: no command is sent, and that is recorded, not hidden.
    if (after == null || after.paused !== want) {
      findings.push(`dispatch: it was already ${want ? 'paused' : 'open'} but the read after says otherwise (${describeAnswer(after)})`);
    }
    return findings;
  }
  if (command == null || command.status !== 200) {
    findings.push(`dispatch: setExecutionPaused(${want}) was not accepted (${describeAnswer(command)})`);
  }
  if (after == null || after.status !== 200 || after.paused !== want) {
    findings.push(`dispatch: after the ${label} the API says ${describeAnswer(after)}, not paused=${want}`);
  }
  return findings;
}

/**
 * Drive dispatch to `want` (true: paused) in one cold browser. Never throws for an application answer: every
 * answer is returned, and {@link entryFindings} judges them. It throws only when the browser cannot be driven.
 */
export async function setDispatch({ origin, apiPrefix, cookies, viewport, want, key = newDispatchKey(), progress = {} }) {
  return await withColdBrowser(
    async (page) => {
      await page.goto(`${origin}${apiPrefix}${DISPATCH_PATH}`);
      // `progress` is filled as the answers come, so a browser that dies half-way still tells the caller whether a
      // command may have gone out (and so whether the state has to be put back).
      progress.want = want;
      progress.before = await page.evaluate(dispatchExpression(apiPrefix, null, key));
      progress.command = null;
      if (progress.before.status === 200 && progress.before.paused !== want) {
        progress.command = await page.evaluate(dispatchExpression(apiPrefix, want, key));
      }
      progress.after = await page.evaluate(dispatchExpression(apiPrefix, null, key));
      progress.wasPaused = progress.before.paused === true;
      return progress;
    },
    { cookies, viewport },
  );
}

/**
 * Enter the paused state for a walk. `held` is what {@link restoreDispatch} needs to put it back.
 */
export async function pauseDispatch({ origin, apiPrefix, cookies, viewport }) {
  const progress = {};
  let entry;
  let drivingError = null;
  try {
    entry = await setDispatch({ origin, apiPrefix, cookies, viewport, want: true, progress });
  } catch (error) {
    entry = progress;
    drivingError = error.message;
  }
  const findings =
    drivingError === null
      ? entryFindings(true, entry)
      : [`dispatch: the browser could not be driven while pausing: ${drivingError}`];
  // Put back whatever this walk may have changed: it found the stand open and could read that, so a command
  // that failed half-way (sent, answer lost) is still undone.
  return { entry, findings, held: { resume: entry.before?.status === 200 && entry.before?.paused === false } };
}

/**
 * Put dispatch back as it was found. A stand that was paused before the walk stays paused (`resume: false`);
 * otherwise it is resumed, and a resume the API does not confirm is a finding.
 */
export async function restoreDispatch({ origin, apiPrefix, cookies, viewport }, held) {
  if (held === null || held.resume !== true) {
    return { exit: null, findings: [], note: 'dispatch was not paused by this walk, so nothing was resumed' };
  }
  const progress = {};
  try {
    const exit = await setDispatch({ origin, apiPrefix, cookies, viewport, want: false, progress });
    return { exit, findings: entryFindings(false, exit), note: 'resumed' };
  } catch (error) {
    return {
      exit: progress,
      findings: [`dispatch: the browser could not be driven while resuming, so dispatch may still be paused: ${error.message}`],
      note: 'resume failed',
    };
  }
}
