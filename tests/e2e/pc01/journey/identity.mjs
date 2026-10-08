#!/usr/bin/env node
/** W51 identity continuation of the PC-01 write journey. No credential enters evidence. */

import { randomBytes } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';
import { openSession } from './session.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

function argsOf(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i]?.startsWith('--') || !argv[i + 1]) throw new Error(`identity: ${argv[i]} needs a value`);
    args[argv[i].slice(2)] = argv[i + 1];
  }
  for (const key of ['origin', 'journey', 'out']) {
    if (!args[key]) throw new Error(`identity: --${key} is required`);
  }
  return args;
}

function requireThat(value, message) {
  if (!value) throw new Error(message);
}

function redact(message, secrets) {
  return secrets.reduce((text, secret) => secret ? text.replaceAll(secret, '(redacted)') : text, String(message));
}

function matchingExchange(page, method, path) {
  return [...page.exchanges()].reverse().find((item) => {
    try { return item.method === method && new URL(item.url).pathname === path; }
    catch { return false; }
  });
}

function bodyOf(exchange) {
  try { return JSON.parse(exchange?.responseBody ?? ''); }
  catch { return null; }
}

function checkedExchange(page, spec, path, record) {
  const wirePath = spec.stage === 'register' ? '/bff/v1/registration' : `/bff/v1${path}`;
  const exchange = matchingExchange(page, spec.method, wirePath);
  requireThat(exchange, `${spec.stage}: no ${spec.method} ${wirePath} reached the BFF`);
  const body = bodyOf(exchange);
  record.operations.push({ stage: spec.stage, method: spec.method, path, status: exchange.status,
    error_code: body?.error_code ?? null, conflict_reason: body?.details?.conflict_reason ?? null });
  const expectedWireStatus = spec.stage === 'register' ? 303 : spec.status;
  requireThat(exchange.status === expectedWireStatus,
    `${spec.stage}: ${spec.method} ${wirePath} answered ${exchange.status}, expected ${expectedWireStatus}`);
  if (spec.error_code) requireThat(body?.error_code === spec.error_code,
    `${spec.stage}: expected ${spec.error_code}, received ${body?.error_code ?? '(no error code)'}`);
  if (spec.conflict_reason) requireThat(body?.details?.conflict_reason === spec.conflict_reason,
    `${spec.stage}: expected ${spec.conflict_reason}, received ${body?.details?.conflict_reason ?? '(no reason)'}`);
  return body;
}

function stageSpec(manifest, name) {
  const matches = manifest.identity.operations.filter((item) => item.stage === name);
  requireThat(matches.length === 1, `identity manifest must declare one '${name}' operation`);
  return matches[0];
}

function sessionRow(path, id) {
  const register = JSON.parse(readFileSync(path, 'utf8'));
  requireThat(register.version === 2 && Array.isArray(register.sessions),
    'session register has no version-2 sessions array');
  return register.sessions.some((row) => row.id === id);
}

async function wait(page, expression, what) {
  const result = await page.waitFor(expression, { boundMs: 30000, what });
  requireThat(result.ok, `${what}: no matching rendered state in ${result.boundMs} ms`);
  return result.value;
}

async function register(origin, applicant, manifest, record) {
  await withColdBrowser(async (page) => {
    await page.goto(`${origin}/register`);
    for (const [selector, value] of [
      ['#register-last', applicant.last], ['#register-first', applicant.first],
      ['#register-middle', applicant.middle], ['#register-email', applicant.login],
      ['#register-password', applicant.password], ['#register-confirm', applicant.password],
    ]) await page.fill(selector, value);
    await page.click('form button[type="submit"]', { text: 'Отправить заявку' });
    await wait(page, `document.location.pathname === '/register/submitted' ? true : null`,
      'registration confirmation');
    await page.settle();
    checkedExchange(page, stageSpec(manifest, 'register'), '/registrations', record);
    record.checks.push('registration submitted through the form and confirmation rendered');
  });
}

async function refusedSignIn(origin, manifest, applicant, expected, record) {
  const attempted = await openSession({ origin, manifest,
    credentials: { login: applicant.login, password: applicant.password } });
  requireThat(!attempted.ok && attempted.record?.refusal?.value === expected,
    `sign-in expected ${expected}, got ${attempted.record?.refusal?.value ?? 'no refusal'}`);
  requireThat(attempted.cookies.length === 0, 'refused sign-in minted a session cookie');
  record.checks.push(`${expected} sign-in refusal rendered`);
  return attempted.record.refusal.text;
}

async function findRequest(page, login) {
  await wait(page, `document.querySelector('[data-pending-total]') ? true : null`,
    'registration queue');
  for (let pageNumber = 0; pageNumber < 25; pageNumber += 1) {
    const row = await page.evaluate(`(() => {
      const item = [...document.querySelectorAll('li[data-registration-status="pending"]')]
        .find((node) => node.innerText.includes(${JSON.stringify(login)}));
      if (!item) return null;
      const id = item.querySelector('textarea[id^="reject-"]')?.id.slice(7);
      return id ? { request_id: id } : null;
    })()`);
    if (row) return row.request_id;
    const next = await page.describe('button', 'Дальше');
    requireThat(next, `pending request for ${login} is absent after ${pageNumber + 1} queue page(s)`);
    await page.click('button', { text: 'Дальше' });
    await page.settle();
  }
  throw new Error(`pending request for ${login} exceeds the 25-page journey bound`);
}

async function decide(origin, manifest, adminCookies, applicant, kind, record) {
  return await withColdBrowser(async (page) => {
    await page.goto(`${origin}/admin/registrations`);
    const requestId = await findRequest(page, applicant.login);
    const rowSelector = `li:has(#reject-${requestId})`;
    if (kind === 'approve') {
      await page.click(`${rowSelector} button[type="submit"]`, { text: 'Одобрить заявку' });
      await wait(page, `document.querySelector('[data-registration-decision-failure="roles"]') !== null ? true : null`,
        'zero-role refusal');
      requireThat(!matchingExchange(page, 'POST', `/bff/v1/registrations/${requestId}/approve`),
        'zero-role approval sent an API request');
      record.checks.push('zero-role approval refused locally without an API call');
      await page.click(`${rowSelector} label`, { text: 'Эксперт' });
      await page.click(`${rowSelector} button[type="submit"]`, { text: 'Одобрить заявку' });
    } else {
      await page.fill(`#reject-${requestId}`, 'Синтетическая проверка отказа');
      await page.click(`${rowSelector} button[type="submit"]`, { text: 'Отклонить заявку' });
    }
    await page.settle();
    const spec = stageSpec(manifest, kind);
    const body = checkedExchange(page, spec, `/registrations/${requestId}/${kind}`, record);
    requireThat(body?.status === (kind === 'approve' ? 'approved' : 'rejected'),
      `${kind} response did not carry its decided status`);
    record.checks.push(`${kind} decision rendered for its opaque request_id`);
    return { requestId, userUid: body?.created_user_uid ?? null };
  }, { cookies: adminCookies });
}

async function assertProfile(origin, manifest, cookies, applicant, record) {
  await withColdBrowser(async (page) => {
    await page.goto(`${origin}/account`);
    await wait(page, `document.querySelector('[data-account-profile-complete]')?.getAttribute('data-account-profile-complete') === 'true' ? true : null`,
      'completed profile');
    const text = await page.evaluate('document.body.innerText');
    requireThat(text.includes(applicant.last) && text.includes(applicant.first) && text.includes('Эксперт'),
      'approved profile did not render the submitted name and expert role');
    checkedExchange(page, stageSpec(manifest, 'profile'), '/me', record);
    record.checks.push('approved profile came from request and survived a cold load');
  }, { cookies });
}

async function decision(origin, manifest, cookies, reviewPath, stage, record) {
  return await withColdBrowser(async (page) => {
    await page.goto(origin + reviewPath);
    await wait(page, `document.querySelector('[data-intent="accept"]') ? true : null`,
      'review decision control');
    const findingUid = await page.evaluate(`document.querySelector('[data-finding-uid]')?.getAttribute('data-finding-uid') ?? null`);
    requireThat(findingUid, 'review has no selected finding to decide');
    await page.click('[data-intent="accept"]');
    if (stage === 'verdict') {
      await wait(page, `(() => [...document.querySelectorAll('[data-event-type="accept"] .am-history__author')]
        .some((node) => node.innerText.trim() === ${JSON.stringify(manifest.identity.expected_author_label)}) ? true : null)()`,
      'derived verdict author label');
    } else {
      await wait(page, `document.querySelector('[role="alert"]') ? true : null`, 'permission refusal');
    }
    await page.settle();
    checkedExchange(page, stageSpec(manifest, stage), `/findings/${findingUid}/decisions`, record);
    record.checks.push(stage === 'verdict' ? 'verdict persisted with derived author label' : 'new mutation denied after sign-in');
    return findingUid;
  }, { cookies });
}

async function userAction(origin, manifest, adminCookies, userUid, stage, record) {
  await withColdBrowser(async (page) => {
    await page.goto(`${origin}/admin/users/${userUid}`);
    await wait(page, `document.querySelector('[data-user-state]') ? true : null`, 'user detail');
    if (stage === 'remove_expert') {
      await page.click('form input[name="role"][value="expert"]');
      await page.click('form button[type="submit"]', { text: 'Сохранить роли' });
      await wait(page, `document.querySelector('[role="status"]') ? true : null`, 'role change success');
    } else if (stage === 'archive') {
      await page.click('button', { text: 'Архивировать учётную запись' });
      await wait(page, `document.querySelector('[data-user-state="archived"]') ? true : null`, 'archived account');
    } else if (stage === 'purge_refused') {
      await page.click('button', { text: 'Удалить навсегда' });
      await page.click('button', { text: 'Подтвердить удаление' });
      await wait(page, `document.querySelector('[data-user-failure]') ? true : null`, 'purge conflict');
    } else throw new Error(`unknown user action ${stage}`);
    await page.settle();
    const operation = stage === 'remove_expert' ? `/users/${userUid}` :
      stage === 'purge_refused' ? `/users/${userUid}` : `/users/${userUid}/archive`;
    checkedExchange(page, stageSpec(manifest, stage), operation, record);
    record.checks.push(`${stage} answered with its declared status and rendered state`);
  }, { cookies: adminCookies });
}

async function revokedSession(origin, manifest, cookies, registerPath, record) {
  const id = cookies.find((cookie) => cookie.name === manifest.session.cookie)?.value;
  requireThat(id && sessionRow(registerPath, id), 'expert session row was absent before role revocation');
  await withColdBrowser(async (page) => {
    await page.goto(`${origin}/account`);
    await wait(page, `document.querySelector('[role="alert"]') ? true : null`, 'revoked-session state');
    await page.settle();
    checkedExchange(page, stageSpec(manifest, 'revoked_request'), '/me', record);
    requireThat(!sessionRow(registerPath, id), 'revoked session row remains in the BFF register after 401');
    const signedOutLink = await page.evaluate(`document.querySelector('a[href^="/login"]') !== null`);
    requireThat(signedOutLink, 'the 401 screen has no sign-in link in its signed-out state');
    await page.goto(`${origin}/account`);
    requireThat((await page.location()) === '/login', 'revoked browser did not reach the sign-in screen');
    const signIn = await page.evaluate(`document.querySelector('a[href="/login"]') !== null ||
      document.querySelector('#sign-in-login') !== null`);
    requireThat(signIn, 'signed-out screen offers no sign-in control or link');
    record.checks.push('next BFF call returned 401, row vanished, signed-out screen offers sign-in');
  }, { cookies });
}

async function selfArchiveRefusal(origin, manifest, adminCookies, record) {
  const adminUid = await withColdBrowser(async (page) => {
    await page.goto(`${origin}/account`);
    await wait(page, `document.querySelector('[data-account-profile-complete]') ? true : null`,
      'administrator profile');
    await page.settle();
    const me = bodyOf(matchingExchange(page, 'GET', '/bff/v1/me'));
    requireThat(me?.user_uid, 'administrator profile returned no user_uid');
    return me.user_uid;
  }, { cookies: adminCookies });
  await withColdBrowser(async (page) => {
    await page.goto(`${origin}/admin/users/${adminUid}`);
    await wait(page, `document.querySelector('[data-user-state="active"]') ? true : null`,
      'administrator card');
    await page.click('button', { text: 'Архивировать учётную запись' });
    await wait(page, `document.querySelector('[data-user-failure]') ? true : null`,
      'self-archive refusal');
    await page.settle();
    checkedExchange(page, stageSpec(manifest, 'self_archive'),
      `/users/${adminUid}/archive`, record);
    record.checks.push('administrator self-archive refused without changing account state');
  }, { cookies: adminCookies });
}

async function main() {
  const args = argsOf(process.argv.slice(2));
  const manifest = JSON.parse(readFileSync(join(HERE, 'manifest.json'), 'utf8'));
  const journey = JSON.parse(readFileSync(resolve(args.journey), 'utf8'));
  const origin = args.origin.replace(/\/+$/, '');
  const registerPath = process.env[manifest.identity.session_store_path_env];
  requireThat(registerPath, `${manifest.identity.session_store_path_env} is required to prove session-row deletion`);
  requireThat(journey.write?.ran && journey.write?.stoppedAt === null,
    'identity needs the completed PC-01 write half');
  const { project_uid: projectUid, run_id: runId } = journey.write.captured ?? {};
  requireThat(projectUid && runId, 'identity needs project_uid and run_id from the write half');
  const reviewPath = manifest.identity.review_path
    .replace('{project_uid}', projectUid).replace('{run_id}', runId);
  const nonce = randomBytes(8).toString('hex');
  const password = `Aq9!${randomBytes(18).toString('hex')}`;
  const rejectedPassword = `Bq9!${randomBytes(18).toString('hex')}`;
  const applicant = { login: `pc01+${nonce}@example.test`, password,
    last: 'Тестов', first: 'Иван', middle: 'Петрович' };
  const rejected = { login: `pc01-rejected+${nonce}@example.test`, password: rejectedPassword,
    last: 'Отказов', first: 'Иван', middle: 'Петрович' };
  const secrets = [password, rejectedPassword];
  const record = { ran: true, completed: false, operations: [], checks: [], failures: [],
    applicants: { approved: applicant.login, rejected: rejected.login }, reviewPath };
  let stoppedAt = null;
  try {
    const admin = await openSession({ origin, manifest });
    requireThat(admin.ok, `administrator sign-in failed: ${admin.failures.join('; ')}`);
    await register(origin, applicant, manifest, record);
    const pending = await refusedSignIn(origin, manifest, applicant, 'pending', record);
    requireThat(pending.includes('Заявка на регистрацию ещё не рассмотрена'),
      'pending applicant saw no pending sentence');
    const approved = await decide(origin, manifest, admin.cookies, applicant, 'approve', record);
    requireThat(approved.userUid, 'approval response contained no created_user_uid');
    const expert = await openSession({ origin, manifest,
      credentials: { login: applicant.login, password } });
    requireThat(expert.ok, `approved expert sign-in failed: ${expert.failures.join('; ')}`);
    await assertProfile(origin, manifest, expert.cookies, applicant, record);
    await decision(origin, manifest, expert.cookies, reviewPath, 'verdict', record);
    await userAction(origin, manifest, admin.cookies, approved.userUid, 'remove_expert', record);
    await revokedSession(origin, manifest, expert.cookies, registerPath, record);
    const roleless = await openSession({ origin, manifest,
      credentials: { login: applicant.login, password } });
    requireThat(roleless.ok, `roleless sign-in failed: ${roleless.failures.join('; ')}`);
    await decision(origin, manifest, roleless.cookies, reviewPath, 'denied_mutation', record);
    await userAction(origin, manifest, admin.cookies, approved.userUid, 'archive', record);
    const archivedText = await refusedSignIn(origin, manifest, applicant, 'credentials', record);
    await userAction(origin, manifest, admin.cookies, approved.userUid, 'purge_refused', record);
    await register(origin, rejected, manifest, record);
    await decide(origin, manifest, admin.cookies, rejected, 'reject', record);
    const rejectedText = await refusedSignIn(origin, manifest, rejected, 'credentials', record);
    const unknownText = await refusedSignIn(origin, manifest,
      { login: `pc01-unknown+${nonce}@example.test`, password: rejectedPassword },
      'credentials', record);
    requireThat(rejectedText === unknownText && archivedText === unknownText,
      'rejected, archived and unknown sign-in refusals differ byte-for-byte');
    record.checks.push('rejected, archived and unknown sign-in refusals are byte-identical');
    await selfArchiveRefusal(origin, manifest, admin.cookies, record);
    record.completed = true;
  } catch (error) {
    stoppedAt = record.checks.at(-1) ?? 'before first completed check';
    record.failures.push(redact(error?.message ?? error, secrets));
  }
  record.stoppedAt = stoppedAt;
  mkdirSync(resolve(args.out), { recursive: true });
  const output = join(resolve(args.out), 'identity.json');
  writeFileSync(output, JSON.stringify(record, null, 2));
  console.log(`identity: ${record.completed ? 'PASS' : 'FAIL'}; evidence: ${output}`);
  if (!record.completed) {
    for (const failure of record.failures) console.error(`  - ${failure}`);
    process.exitCode = 1;
  }
}

main().catch((error) => { console.error(`identity: ${error.message}`); process.exitCode = 2; });
