/**
 * The render harness for the screens `W12-WEB` measured as reached by no test.
 *
 * `W12-WEB` §10 claimed seven of its ten unreached-region mutations sat in ordinary
 * components that `renderToStaticMarkup` can reach, and that `RunProgress` additionally
 * needs a `QueryClientProvider` with a seeded `queryKeys.runs.detail(runId)` entry. That
 * claim is verified here rather than assumed: this file is the whole of the extra
 * machinery it takes, and it adds no dependency — `@tanstack/react-query` is already a
 * production dependency and `react-dom/server` is already how `tests/unit/review`
 * renders.
 *
 * What this harness can and cannot do is the boundary of this session's kill count, and
 * it is stated in the session report rather than discovered later:
 *
 *   it CAN     render one pass of any component, including one whose state comes from a
 *              `useState` initialiser or from a seeded query cache;
 *   it CANNOT  fire an event handler, run a `useEffect`, or render the same component
 *              instance twice.
 *
 * No `jsdom`, no `happy-dom`, no `@testing-library/*`. `vitest.config.ts` pins
 * `environment: 'node'` and `FRONTEND_LOCK.json` seals the dependency set.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';

import { render } from '../review/fixtures';

/**
 * A client with retries off and no background refetching, so a query that is not seeded
 * stays in its pending state instead of depending on the network during a render.
 */
export function newClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity } },
  });
}

/** Render `element` inside a provider over `client`, to static markup. */
export function renderWith(client: QueryClient, element: ReactElement): string {
  return render(createElement(QueryClientProvider, { client }, element));
}

/**
 * Put a query into its error state.
 *
 * `useQuery` never runs its `queryFn` during a server render, so the only way to reach a
 * component's failure branch from here is to build the cache entry and set its state.
 * `QueryCache.build` is the documented way to obtain the entry; nothing here reaches into
 * a private field.
 */
export function seedError(client: QueryClient, queryKey: readonly unknown[], error: unknown): void {
  const query = client.getQueryCache().build(client, { queryKey: [...queryKey] });
  query.setState({
    status: 'error',
    error: error as Error,
    fetchStatus: 'idle',
    dataUpdatedAt: 0,
    errorUpdatedAt: Date.now(),
    fetchFailureCount: 1,
  });
}
