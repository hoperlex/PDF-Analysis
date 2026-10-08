import assert from 'node:assert/strict';
import test from 'node:test';

import { navigateWithTransientRetry } from './navigation-retry.mjs';

function scriptedNavigation(results) {
  const calls = [];
  return {
    calls,
    send: async (method, params) => {
      calls.push([method, params]);
      const next = results.shift();
      if (next instanceof Error) throw next;
      return next;
    },
  };
}

test('a short network change retries GET navigation, then returns the successful page', async () => {
  const navigation = scriptedNavigation([
    { errorText: 'net::ERR_NETWORK_CHANGED' },
    { errorText: 'net::ERR_NETWORK_CHANGED' },
    { frameId: 'loaded' },
  ]);
  const delays = [];
  const retries = [];
  const reached = await navigateWithTransientRetry(navigation.send, 'http://localhost/run', {
    sleep: async (delayMs) => delays.push(delayMs),
    onRetry: (retry) => retries.push(retry),
  });

  assert.deepEqual(reached, { result: { frameId: 'loaded' }, attempts: 3 });
  assert.deepEqual(delays, [1000, 3000]);
  assert.deepEqual(retries.map((retry) => retry.attempts), [1, 2]);
  assert.deepEqual(navigation.calls, Array.from({ length: 3 }, () => [
    'Page.navigate', { url: 'http://localhost/run' },
  ]));
});

test('persistent network change returns the final failure after a fixed budget', async () => {
  const navigation = scriptedNavigation(Array.from({ length: 4 }, () => ({
    errorText: 'net::ERR_NETWORK_CHANGED',
  })));
  const delays = [];
  const reached = await navigateWithTransientRetry(navigation.send, '/run', {
    sleep: async (delayMs) => delays.push(delayMs),
  });

  assert.equal(reached.result.errorText, 'net::ERR_NETWORK_CHANGED');
  assert.equal(reached.attempts, 4);
  assert.deepEqual(delays, [1000, 3000, 6000]);
  assert.equal(navigation.calls.length, 4);
});

test('another navigation failure is returned immediately', async () => {
  const navigation = scriptedNavigation([{ errorText: 'net::ERR_CONNECTION_REFUSED' }]);
  const reached = await navigateWithTransientRetry(navigation.send, '/run', {
    sleep: () => assert.fail('must not wait for another failure'),
  });

  assert.equal(reached.result.errorText, 'net::ERR_CONNECTION_REFUSED');
  assert.equal(reached.attempts, 1);
  assert.equal(navigation.calls.length, 1);
});

test('a rejected CDP command propagates without replay', async () => {
  const navigation = scriptedNavigation([new Error('CDP disconnected')]);
  await assert.rejects(
    navigateWithTransientRetry(navigation.send, '/run', {
      sleep: () => assert.fail('must not wait after CDP disconnect'),
    }),
    /CDP disconnected/,
  );
  assert.equal(navigation.calls.length, 1);
});
