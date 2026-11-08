import assert from 'node:assert/strict';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

import { describeAnswer, dispatchExpression, entryFindings, newDispatchKey } from './dispatch.mjs';

/** Run the page-side expression against a fetch stand-in; returns the reduced answer and the request it made. */
async function run(paused, reply) {
  const seen = [];
  const fetch = async (url, init) => {
    seen.push({ url, init });
    return {
      status: reply.status,
      headers: { get: (name) => (name === 'x-correlation-id' ? 'cor_1' : null) },
      text: async () => reply.text,
    };
  };
  const answer = await runInNewContext(dispatchExpression('/bff/v1', paused, 'ik_test'), { fetch, JSON });
  return { answer, request: seen[0] };
}

test('D-380: pausing is a PUT of {"paused":true} with an idempotency key, from the page\'s own origin', async () => {
  const { answer, request } = await run(true, { status: 200, text: '{"paused":true,"changed_at":"2026-11-09T10:00:00Z"}' });
  assert.equal(request.url, '/bff/v1/execution/dispatch');
  assert.equal(request.init.method, 'PUT');
  assert.equal(request.init.credentials, 'same-origin');
  assert.equal(request.init.body, '{"paused":true}');
  assert.equal(request.init.headers['idempotency-key'], 'ik_test');
  assert.equal(request.init.headers['content-type'], 'application/json');
  assert.deepEqual({ status: answer.status, paused: answer.paused, correlationId: answer.correlationId }, { status: 200, paused: true, correlationId: 'cor_1' });
});

test('D-380: a read is a GET with no body and no key, and an answer that is not JSON reads as no state', async () => {
  const read = await run(null, { status: 200, text: '{"paused":false,"changed_at":"x"}' });
  assert.equal(read.request.init.method, 'GET');
  assert.equal(read.request.init.body, undefined);
  assert.equal(read.request.init.headers['idempotency-key'], undefined);
  assert.equal(read.answer.paused, false);
  const html = await run(null, { status: 403, text: '<html>nginx 403</html>' });
  assert.equal(html.answer.paused, null);
  assert.equal(html.answer.status, 403);
});

test('D-380: the idempotency key is one the contract accepts and differs per command', () => {
  const pattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
  const a = newDispatchKey();
  assert.match(a, pattern);
  assert.notEqual(a, newDispatchKey());
});

const answer = (status, paused) => ({ status, paused, correlationId: 'cor', text: '{"detail":"x"}' });

test('D-380: pausing is proved by the API\'s own read after the command, never by the command\'s 200 alone', () => {
  assert.deepEqual(entryFindings(true, { before: answer(200, false), command: answer(200, true), after: answer(200, true) }), []);
  // The command said 200 and the state did not move: a finding.
  assert.match(entryFindings(true, { before: answer(200, false), command: answer(200, true), after: answer(200, false) })[0], /after the pause the API says/);
  // Refused (a non-administrator): the command and the unchanged state are both findings.
  const refused = entryFindings(true, { before: answer(200, false), command: answer(403, null), after: answer(200, false) });
  assert.equal(refused.length, 2);
  assert.match(refused[0], /setExecutionPaused\(true\) was not accepted \(403/);
  // The state could not be read first: nothing is sent, one finding.
  assert.match(entryFindings(true, { before: answer(401, null), command: null, after: null })[0], /could not be read before the pause/);
  assert.match(entryFindings(true, { before: null })[0], /could not be read before the pause/);
});

test('D-380: a stand found paused is left alone and said so; a resume that does not take is a finding', () => {
  assert.deepEqual(entryFindings(true, { before: answer(200, true), command: null, after: answer(200, true) }), []);
  assert.match(entryFindings(true, { before: answer(200, true), command: null, after: answer(200, false) })[0], /already paused but the read after says otherwise/);
  assert.deepEqual(entryFindings(false, { before: answer(200, true), command: answer(200, false), after: answer(200, false) }), []);
  assert.match(entryFindings(false, { before: answer(200, true), command: answer(200, false), after: answer(200, true) })[0], /after the resume the API says .*not paused=false/);
  assert.equal(describeAnswer(null), '(no answer)');
  assert.match(describeAnswer(answer(500, null)), /500 paused=null correlation-id cor body/);
});
