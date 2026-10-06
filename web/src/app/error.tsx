'use client';

/**
 * The error boundary for every screen (`W50-PLAN.md` §3.3).
 *
 * A screen that throws while it renders lands here instead of on the framework's own page,
 * which is English and, in development, prints the error. This one is Russian and prints
 * nothing of the error: no message, no stack, no name — a thrown value can carry a path, a
 * key or an upstream answer, and none of that is for a reviewer. Next requires an error
 * boundary to be a client component; it receives `reset`, which re-renders the segment.
 *
 * What a reviewer can act on is said: nothing was changed by the failure, and the screen can
 * be asked again. The `digest` Next attaches is the one thing an operator can trace, and it is
 * an opaque hash, so it is shown in the slot the shared error state keeps for a correlation
 * id.
 */

import { ErrorState, PageShell } from '@/shared/ui';

/*
 * The words, held apart from the markup. The boundary is rendered by nothing a screen seed
 * reaches — it appears only when a screen throws — so its own guard renders it and checks
 * them: `web/tests/guards/screen-guard.guard.test.ts`, "§3.3".
 */
const SCREEN_TITLE = 'Экран не открылся';
const FAILURE_TITLE = 'При построении экрана произошла ошибка.';
const FAILURE_DETAIL =
  'Ничего не изменено. Экран можно запросить ещё раз; если ошибка повторится, сообщите о ней, указав идентификатор ниже.';
const RETRY_LABEL = 'Открыть ещё раз';

export interface ErrorBoundaryProps {
  readonly error: Error & { readonly digest?: string };
  readonly reset: () => void;
}

export default function ErrorBoundary({ error, reset }: ErrorBoundaryProps) {
  return (
    <PageShell title={SCREEN_TITLE}>
      <ErrorState
        title={FAILURE_TITLE}
        detail={FAILURE_DETAIL}
        correlationId={error.digest ?? null}
        onRetry={reset}
        retryLabel={RETRY_LABEL}
      />
    </PageShell>
  );
}
