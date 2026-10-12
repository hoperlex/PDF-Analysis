/**
 * `C-30` (W53 close): the journey records the navigation attempts a route made even when the
 * CDP command rejects, so `write.mjs`'s `finally` never writes a count that belongs to
 * another navigation.
 *
 * `cdp.mjs` is the browser driver under `tests/e2e/pc01/journey/`; its `Page` never leaves
 * the module, so this reaches the one function `Page.goto` counts through. The module is
 * imported by URL at run time: it is plain JavaScript outside the web project.
 */

import { describe, expect, it } from 'vitest';

type Send = (method: string, params: unknown) => Promise<{ errorText?: string }>;
type Reached = { readonly result: { errorText?: string }; readonly attempts: number };
type NavigateCountingAttempts = (
  send: Send,
  url: string,
  record: (count: number | null) => void,
  options?: { readonly sleep?: (delayMs: number) => Promise<void> },
) => Promise<Reached>;

const DRIVER = new URL('../../../../tests/e2e/pc01/journey/cdp.mjs', import.meta.url).href;

async function driver(): Promise<NavigateCountingAttempts> {
  const module = (await import(/* @vite-ignore */ DRIVER)) as { navigateCountingAttempts: NavigateCountingAttempts };
  return module.navigateCountingAttempts;
}

function scripted(answers: readonly ({ errorText?: string } | Error)[]): Send {
  const queue = [...answers];
  return async () => {
    const next = queue.shift();
    if (next === undefined) throw new Error('script exhausted');
    if (next instanceof Error) throw next;
    return next;
  };
}

const noWait = { sleep: async () => {} };

describe('navigation attempts in journey evidence', () => {
  it('records the attempt on a rejected first command, never the previous count', async () => {
    const navigate = await driver();
    const recorded: (number | null)[] = [];
    let current: number | null = 4; // what an earlier navigation of the same page left
    const record = (count: number | null) => { current = count; recorded.push(count); };
    await expect(navigate(scripted([new Error('CDP disconnected')]), '/run', record, noWait))
      .rejects.toThrow('CDP disconnected');
    expect(current).toBe(1);
    expect(recorded).toEqual([null, 1]);
  });

  it('counts the transient retries made before a rejection', async () => {
    const navigate = await driver();
    let current: number | null = null;
    await expect(navigate(
      scripted([{ errorText: 'net::ERR_NETWORK_CHANGED' }, new Error('CDP disconnected')]),
      '/run',
      (count) => { current = count; },
      noWait,
    )).rejects.toThrow('CDP disconnected');
    expect(current).toBe(2);
  });

  it('still records the attempts of a navigation that returns', async () => {
    const navigate = await driver();
    let current: number | null = null;
    const reached = await navigate(
      scripted([{ errorText: 'net::ERR_NETWORK_CHANGED' }, { errorText: 'net::ERR_NETWORK_CHANGED' }, {}]),
      '/run',
      (count) => { current = count; },
      noWait,
    );
    expect(reached.attempts).toBe(3);
    expect(current).toBe(3);
  });

  it('is what Page.goto counts through', async () => {
    const { readFileSync } = await import('node:fs');
    const source = readFileSync(new URL(DRIVER), 'utf8');
    const goto = source.slice(source.indexOf('async goto('), source.indexOf('const t1 = Date.now();'));
    expect(goto).toContain('navigateCountingAttempts(');
    expect(goto).not.toContain('navigateWithTransientRetry(');
  });
});
