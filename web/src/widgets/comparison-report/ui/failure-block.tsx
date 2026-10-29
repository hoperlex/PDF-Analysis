/**
 * What the window says when a read or a command did not succeed: a module that is not wired yet is the module's state
 * («Модуль ещё недоступен»), not a red error; every other failure is the Russian sentence of its refusal.
 */

import type { ComparisonFailure } from '@/entities/version-series';
import { ErrorState, UnsupportedState } from '@/shared/ui';

export const MODULE_UNAVAILABLE_TITLE = 'Модуль ещё недоступен';

export function FailureBlock({ failure, title }: { readonly failure: ComparisonFailure | null; readonly title?: string | undefined }) {
  if (failure === null) return null;
  if (failure.moduleUnavailable) {
    return (
      <div data-comparison-module="unavailable">
        <UnsupportedState title={MODULE_UNAVAILABLE_TITLE} detail={failure.detail} />
      </div>
    );
  }
  if (title !== undefined) {
    return (
      <div data-comparison-failure={failure.kind}>
        <ErrorState title={title} detail={failure.detail} correlationId={failure.correlationId} />
      </div>
    );
  }
  return (
    <p className="am-decision__refusal" role="alert" data-comparison-failure={failure.kind}>
      {failure.detail}
      {failure.correlationId === null ? null : <> Код обращения: <code>{failure.correlationId}</code>.</>}
    </p>
  );
}
