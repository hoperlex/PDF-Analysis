/**
 * What a screen of the comparison says when a read or a command did not succeed.
 *
 * A module that is not wired yet or is off answers `503 dependency_unavailable` with one of its own dependency
 * names; that is a **state of the module**, said as «Модуль ещё недоступен», not a red error and never an empty
 * list. Every other failure is the ordinary error state with the Russian sentence of the refusal. The class names
 * of the dependency stay in a `data-` attribute.
 */

import type { ComparisonFailure } from '@/entities/version-series';
import { comparisonFailure } from '@/entities/version-series';
import { ErrorState, UnsupportedState } from '@/shared/ui';

export const MODULE_UNAVAILABLE_TITLE = 'Модуль ещё недоступен';

export interface FailureStateProps {
  readonly error: unknown;
  /** What was being read, as a title says it: «Сводка по комплектам не открылась». */
  readonly title: string;
  readonly onRetry?: (() => void) | undefined;
}

export function FailureState({ error, title, onRetry }: FailureStateProps) {
  const failure: ComparisonFailure = comparisonFailure(error);
  if (failure.moduleUnavailable) {
    return (
      <div data-comparison-module="unavailable">
        <UnsupportedState title={MODULE_UNAVAILABLE_TITLE} detail={failure.detail} />
      </div>
    );
  }
  return (
    <div data-comparison-failure={failure.kind}>
      <ErrorState
        title={title}
        detail={failure.detail}
        correlationId={failure.correlationId}
        onRetry={failure.retryable ? onRetry : undefined}
      />
    </div>
  );
}

/** A refusal of a command, drawn beside the control that sent it. */
export function CommandRefusal({ failure }: { readonly failure: ComparisonFailure | null }) {
  if (failure === null) return null;
  return (
    <p className="am-decision__refusal" role="alert" data-comparison-failure={failure.kind}>
      {failure.detail}
      {failure.correlationId === null ? null : <> Код обращения: <code>{failure.correlationId}</code>.</>}
    </p>
  );
}
