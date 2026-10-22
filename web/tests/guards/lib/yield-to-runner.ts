/**
 * Let the runner's worker talk to the main process between the tests of a heavy file.
 *
 * WHY THIS EXISTS. `pool: 'forks'` with `singleFork` runs a file's tests in one process, and
 * the tests of the two census files (`rendered-language.guard`, `styles/contrast`) are
 * synchronous CPU work: nothing in them awaits I/O, so between the first and the last test
 * the worker's event loop never reaches its poll phase. The runner reports each finished
 * test to the main process over an RPC call (`onTaskUpdate`) whose reply arrives as I/O and
 * whose 60 s timeout is a timer. A file that computes for longer than 60 s without one yield
 * hands the loop the timer first, and the run aborts with `Timeout calling "onTaskUpdate"`
 * while every assertion is still green. `contrast.test.ts` measured 54 s alone and ~62 s in
 * the whole suite once the executor screens joined the census (EXEC candidate 1).
 *
 * WHAT IT DOES. One `setTimeout(0)` after each test: a macrotask boundary, so the reply to
 * the call that is in flight is read before the next test starts. It runs no assertion,
 * changes no fixture and no timeout, and costs about a millisecond per test. It is NOT a
 * retry: a test that fails still fails once.
 *
 * Call it at the top level of a file, once. A file whose longest single test approaches 60 s
 * still needs splitting - this bounds the stretch between tests, not inside one.
 */

import { afterEach } from 'vitest';

export function yieldToRunnerAfterEachTest(): void {
  afterEach(async () => {
    await new Promise<void>((resolve) => {
      setTimeout(resolve, 0);
    });
  });
}
