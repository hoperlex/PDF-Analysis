/**
 * The server-state query client.
 *
 * This is the only cache in the application. There is deliberately **no** global domain
 * store: PC-01's state lives on the server, and a second copy of it in the browser is a
 * second source of truth that will disagree with the first.
 *
 * Retry policy is the contract's, not React Query's. The transport already decodes
 * `retryable` from the error envelope, which the contract pins to the catalog value for
 * the reported code, so the client retries exactly what the server said may be retried
 * and never guesses from a status code.
 */

import { QueryClient } from '@tanstack/react-query';

import { ApiFailure } from '@/shared/api';

const MAX_RETRIES = 2;

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false;
  // Anything that is not a decoded contract failure is not retried: we do not know what
  // it was, and a blind retry on an unknown error is how a duplicate command happens.
  return error instanceof ApiFailure && error.retryable;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetry,
        // Run progress has its own polling loop in `shared/api`; nothing else refetches
        // on a timer.
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
      mutations: {
        // A mutation carries an idempotency key the caller minted once. Retrying it here
        // would reuse that key, which is correct — but the decision to retry a write
        // belongs to the slice that knows what the user asked for, not to a default.
        retry: false,
      },
    },
  });
}
