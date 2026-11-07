/**
 * `useAddressState`: one hook for the screens that keep a piece of their state in the address (the two comparison screens had a copy
 * each; «Очередь» is the third user).
 *
 * The hook is driven as a plain function: `useSearchParams` is replaced by a stub that answers what the test sets, and `window` by a
 * recording history. Each half of the contract has a case that shows it can fail:
 *
 *   - the value is `read` over the router's params, and `initial` only where there is no router;
 *   - a write goes over the address AS IT IS NOW and carries the parameters it does not own;
 *   - `push` adds a history entry, `replace` rewrites the current one, and the default is `push`;
 *   - a write that changes nothing touches the history not at all.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const router = vi.hoisted(() => ({ params: null as URLSearchParams | null }));

vi.mock('next/navigation', () => ({ useSearchParams: () => router.params }));

import { useAddressState } from '@/shared/lib/use-address-state';

interface Shape { readonly tab: string }
const read = (params: Pick<URLSearchParams, 'get'>): Shape => ({ tab: params.get('tab') ?? 'first' });
const write = (params: Pick<URLSearchParams, 'toString'>, next: Shape): URLSearchParams => {
  const written = new URLSearchParams(params.toString());
  if (next.tab === 'first') written.delete('tab');
  else written.set('tab', next.tab);
  return written;
};

let calls: string[] = [];

beforeEach(() => {
  calls = [];
  router.params = new URLSearchParams('');
  vi.stubGlobal('window', {
    location: { search: '', pathname: '/screen' },
    history: {
      state: { marker: 1 },
      pushState: (_state: unknown, _title: string, href: string) => calls.push(`push ${href}`),
      replaceState: (_state: unknown, _title: string, href: string) => calls.push(`replace ${href}`),
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('reading', () => {
  it('reads the router’s params', () => {
    router.params = new URLSearchParams('tab=second');
    expect(useAddressState(read, write)[0]).toEqual({ tab: 'second' });
    router.params = new URLSearchParams('');
    expect(useAddressState(read, write)[0]).toEqual({ tab: 'first' });
  });

  it('starts from `initial` only outside the router', () => {
    router.params = null;
    expect(useAddressState(read, write, { tab: 'seeded' })[0]).toEqual({ tab: 'seeded' });
    expect(useAddressState(read, write)[0]).toEqual({ tab: 'first' });
    // Inside the router the address wins, even over a seed: a link that changes the address changes the screen.
    router.params = new URLSearchParams('');
    expect(useAddressState(read, write, { tab: 'seeded' })[0]).toEqual({ tab: 'first' });
  });
});

describe('writing', () => {
  it('pushes by default and replaces on request, keeping the history state', () => {
    const [, go] = useAddressState(read, write);
    go({ tab: 'second' });
    go({ tab: 'second' }, 'push');
    go({ tab: 'third' }, 'replace');
    expect(calls).toEqual(['push /screen?tab=second', 'push /screen?tab=second', 'replace /screen?tab=third']);
  });

  it('writes over the address as it is when the handler runs, and carries what it does not own', () => {
    const [, go] = useAddressState(read, write);
    // The handler was made when the address was empty; by the time it runs a poll has written `run`.
    (window.location as { search: string }).search = '?run=run_1&tab=second';
    go({ tab: 'third' });
    expect(calls).toEqual(['push /screen?run=run_1&tab=third']);
  });

  it('drops a write that changes nothing, and writes the bare path when nothing is left', () => {
    const [, go] = useAddressState(read, write);
    (window.location as { search: string }).search = '?tab=second';
    go({ tab: 'second' });
    go({ tab: 'second' }, 'replace');
    expect(calls).toEqual([]);
    go({ tab: 'first' });
    expect(calls).toEqual(['push /screen']);
  });

  it('does nothing without a window', () => {
    vi.stubGlobal('window', undefined);
    const [, go] = useAddressState(read, write);
    go({ tab: 'second' });
    expect(calls).toEqual([]);
  });
});
