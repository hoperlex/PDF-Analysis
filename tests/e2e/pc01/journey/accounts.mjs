/**
 * The accounts a refusal-by-role needs: an expert who is not an administrator and an
 * administrator who is not an expert.
 *
 * `BETA-LIVE-JOURNEY-01`. The journey's own account holds both roles (the seeded
 * administrator is also an expert), so as that account no control is ever refused for a
 * missing role -- and "a role that must be refused" is half of what the night window's
 * screens promise. The API refuses `createAssignment` to an expert and
 * `setGlobalVendorList` to one, `classifyDocumentVersion` and `startOptimisationPass` to an
 * administrator without `expert`, and the screens draw no control for the role that cannot
 * use it. Checking that needs a session that really holds only that role.
 *
 * They are made the way a person gets one, through the application's own screens: the
 * applicant fills the registration form in a cold browser, the journey's administrator
 * approves the request choosing the roles, and the applicant signs in. Nothing is created
 * by a hand-built request, so a broken registration or approval screen stops this
 * rather than being walked around.
 *
 * **No password is in this repository, in the envelope or on stdout.** Each account's
 * password is random per run (`crypto.randomBytes`), typed into the form, used for one
 * sign-in and kept only in this process's memory; every message that could carry it passes
 * through `redact`. The roster in `manifest.json` names the account and its roles, never a
 * secret. The e-mail addresses are `@example.test` (reserved, never delivered).
 *
 * What it does not do: it does not archive the accounts afterwards. The journey writes real
 * state on the origin it is pointed at, as its README says, and an administrator can archive
 * these two from the user list.
 */

import { randomBytes } from 'node:crypto';

import { withColdBrowser } from './cdp.mjs';
import { openSession } from './session.mjs';

function redact(message, secrets) {
  return secrets.reduce(
    (text, secret) => (secret ? text.replaceAll(secret, '(redacted)') : text),
    String(message),
  );
}

function bodyOf(exchange) {
  try {
    return JSON.parse(exchange?.responseBody ?? '');
  } catch {
    return null;
  }
}

function matchingExchange(page, method, path) {
  return [...page.exchanges()].reverse().find((item) => {
    try {
      return item.method === method && new URL(item.url).pathname === path;
    } catch {
      return false;
    }
  });
}

async function waitFor(page, expression, what, boundMs = 30000) {
  const result = await page.waitFor(expression, { boundMs, what });
  if (!result.ok) throw new Error(`${what}: nothing matching was rendered in ${result.boundMs} ms`);
  return result.value;
}

/** Fill the registration form in a cold browser, as the applicant would. */
async function register(origin, spec, applicant) {
  await withColdBrowser(async (page) => {
    await page.goto(origin + spec.at);
    for (const [field, value] of [
      ['last', applicant.last],
      ['first', applicant.first],
      ['middle', applicant.middle],
      ['login', applicant.login],
      ['password', applicant.password],
      ['confirm', applicant.password],
    ]) {
      await page.fill(spec.fields[field], value);
    }
    await page.click(spec.submit.selector, { text: spec.submit.text });
    await waitFor(
      page,
      `document.location.pathname === ${JSON.stringify(spec.lands_on)} ? true : null`,
      `the registration confirmation at ${spec.lands_on}`,
    );
    await page.settle();
    const sent = matchingExchange(page, 'POST', spec.exchange);
    if (!sent || sent.status !== spec.exchange_status) {
      throw new Error(
        `registration: POST ${spec.exchange} answered ${sent ? sent.status : 'nothing'}, ` +
          `expected ${spec.exchange_status}`,
      );
    }
  });
}

/** The request id of the pending request for `login`, read from the queue the screen draws. */
async function findRequestId(page, spec, login) {
  await waitFor(page, `document.querySelector(${JSON.stringify(spec.queue_marker)}) ? true : null`,
    'the registration queue');
  for (let at = 0; at < spec.page_bound; at += 1) {
    const row = await page.evaluate(`(() => {
      const item = Array.from(document.querySelectorAll(${JSON.stringify(spec.row)}))
        .find((node) => node.innerText.includes(${JSON.stringify(login)}));
      if (!item) return null;
      const id = item.querySelector(${JSON.stringify(spec.request_id_from)})?.id.slice(${spec.request_id_prefix.length});
      return id ? { request_id: id } : null;
    })()`);
    if (row) return row.request_id;
    const next = await page.describe(spec.pager_next.selector, spec.pager_next.text);
    if (!next) throw new Error(`the pending request for ${login} is not in the queue (${at + 1} page(s) read)`);
    await page.click(spec.pager_next.selector, { text: spec.pager_next.text });
    await page.settle();
  }
  throw new Error(`the pending request for ${login} is past the ${spec.page_bound}-page bound`);
}

/** Approve the request with exactly `roles`, as the journey's administrator. */
async function approve(origin, spec, adminCookies, applicant, roles) {
  return await withColdBrowser(
    async (page) => {
      await page.goto(origin + spec.at);
      const requestId = await findRequestId(page, spec, applicant.login);
      const row = spec.row_by_id.replace('%REQUEST%', requestId);
      for (const role of roles) {
        await page.click(`${row} label`, { text: spec.role_labels[role] });
      }
      await page.click(`${row} ${spec.approve.selector}`, { text: spec.approve.text });
      // The confirmation sentence is drawn by the row's own component, and the row leaves
      // the pending queue the moment the list refreshes, so the sentence can be gone before
      // anything reads it. The decision is the exchange: wait for it to be answered.
      const approvalPath = `/bff/v1/registrations/${requestId}/approve`;
      const t0 = Date.now();
      while (!matchingExchange(page, 'POST', approvalPath)?.status) {
        if (Date.now() - t0 > 30000) throw new Error('the approval was not answered within 30000 ms');
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
      await page.settle();
      const sent = matchingExchange(page, 'POST', approvalPath);
      if (!sent || sent.status !== spec.approve.expect_status) {
        throw new Error(
          `approval: POST /registrations/${requestId}/approve answered ` +
            `${sent ? sent.status : 'nothing'}, expected ${spec.approve.expect_status}`,
        );
      }
      const body = bodyOf(sent);
      const granted = Array.isArray(body?.roles) ? [...body.roles].sort().join(',') : null;
      if (granted !== null && granted !== [...roles].sort().join(',')) {
        throw new Error(`approval granted roles [${granted}], the roster declares [${roles.join(',')}]`);
      }
      return { requestId, userUid: body?.created_user_uid ?? null };
    },
    { cookies: adminCookies },
  );
}

/**
 * Register, approve and sign in every account of the manifest's roster.
 *
 * Returns `{ sessions, record, failures }`. `sessions` maps a roster name to the cookies
 * its sign-in obtained. An account that could not be made is a failure and has no session,
 * so the steps that run as it come back as not reached rather than as passed.
 */
export async function provisionAccounts({ origin, manifest, adminCookies, nonce }) {
  const spec = manifest.accounts;
  const sessions = {};
  const failures = [];
  const secrets = [];
  // Held in memory for the steps that must type an account's own password; never recorded.
  const passwords = {};
  const record = { accounts: [] };

  for (const entry of spec.roster) {
    const password = `Aq9!${randomBytes(18).toString('hex')}`;
    secrets.push(password);
    const applicant = {
      login: `journey-${entry.name.replaceAll('_', '-')}+${nonce}@example.test`,
      password,
      last: entry.last,
      first: entry.first,
      middle: entry.middle,
    };
    const row = { name: entry.name, roles: entry.roles, login: applicant.login, stages: [] };
    record.accounts.push(row);
    try {
      await register(origin, spec.register, applicant);
      row.stages.push('registered through the form');
      const decided = await approve(origin, spec.decide, adminCookies, applicant, entry.roles);
      row.requestId = decided.requestId;
      row.userUid = decided.userUid;
      row.stages.push(`approved with [${entry.roles.join(', ')}]`);
      const opened = await openSession({
        origin,
        manifest,
        credentials: { login: applicant.login, password },
      });
      if (!opened.ok) {
        throw new Error(`the approved account could not sign in: ${opened.failures.join('; ')}`);
      }
      sessions[entry.name] = opened.cookies;
      passwords[`${entry.name}_password`] = password;
      row.stages.push('signed in');
      console.log(`account: ${entry.name} [${entry.roles.join(', ')}] registered, approved, signed in`);
    } catch (error) {
      row.failure = redact(error?.message ?? error, secrets);
      failures.push(`accounts: ${entry.name}: ${row.failure}`);
      console.error(`account: ${entry.name} FAILED: ${row.failure}`);
    }
  }
  return { sessions, record, failures, passwords };
}
