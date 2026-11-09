import { failureMessage } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';

/**
 * A failed read of the decision memory, presented once: the shared Russian reading of the failure (`failureMessage`), the
 * correlation id, and a retry only where the envelope says the code is retryable (never inferred from the status).
 */
export function memoryFailure(error: unknown, retry: () => void, title: string): ErrorStateProps {
  const failure = failureMessage(error);
  return {
    title,
    detail: failure.detail,
    correlationId: failure.correlationId,
    ...(failure.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {}),
  };
}
