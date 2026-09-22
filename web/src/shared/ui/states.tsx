'use client';

/**
 * The five mandatory states.
 *
 * Every list, panel and viewer in PC-01 renders one of these when it has no content to
 * show. They exist as shared primitives so that "nothing here" always looks and reads the
 * same, and so that no slice invents a sixth state — a spinner that never resolves, or an
 * empty div where an error should be.
 *
 *   loading         a request is in flight
 *   empty           the request succeeded and there is genuinely nothing
 *   error           the request failed; carries a retry affordance and the correlation id
 *   unsupported     the input is outside the PC-01 envelope, and no retry will change that
 *   not-applicable  the question does not apply to this object
 *
 * `error` is the only one with an action. `unsupported` and `not-applicable` deliberately
 * have none: offering "try again" for a 31-page PDF teaches the user the wrong thing.
 */

import type { ReactNode } from 'react';

// `| undefined` is spelled out on every optional prop below. Under
// `exactOptionalPropertyTypes` an omitted prop and a prop explicitly passed as
// `undefined` are different things, and these are passed explicitly.
interface StateBlockProps {
  readonly title: string;
  readonly detail?: ReactNode | undefined;
  readonly correlationId?: string | null | undefined;
  readonly action?: ReactNode | undefined;
  readonly tone: 'neutral' | 'error' | 'warning';
  readonly role?: 'status' | 'alert' | undefined;
}

function StateBlock({ title, detail, correlationId, action, tone, role }: StateBlockProps) {
  return (
    <div className={`am-state am-state--${tone}`} role={role ?? 'status'}>
      <p className="am-state__title">{title}</p>
      {detail !== undefined ? <div className="am-state__detail">{detail}</div> : null}
      {correlationId !== undefined && correlationId !== null ? (
        <p className="am-state__correlation">
          Идентификатор корреляции <code>{correlationId}</code>
        </p>
      ) : null}
      {action !== undefined ? <div className="am-state__action">{action}</div> : null}
    </div>
  );
}

export interface LoadingStateProps {
  /** What is being loaded, e.g. "projects". Rendered as "Loading projects…". */
  readonly what?: string | undefined;
}

export function LoadingState({ what }: LoadingStateProps) {
  return <StateBlock tone="neutral" title={what === undefined ? 'Загрузка…' : `Загрузка: ${what}…`} />;
}

export interface EmptyStateProps {
  readonly title: string;
  /** What the user can do about it. Optional: sometimes empty is simply correct. */
  readonly detail?: ReactNode | undefined;
  readonly action?: ReactNode | undefined;
}

export function EmptyState({ title, detail, action }: EmptyStateProps) {
  return <StateBlock tone="neutral" title={title} detail={detail} action={action} />;
}

export interface ErrorStateProps {
  readonly title: string;
  /** The caller-safe message. Never a stack, a path, an object key or a query. */
  readonly detail?: ReactNode | undefined;
  /** From the response header, so an operator can find the diagnostic record. */
  readonly correlationId?: string | null | undefined;
  /**
   * Retry affordance. Omit it when the contract says the failure is not retryable:
   * a button that cannot help is worse than no button.
   */
  readonly onRetry?: (() => void) | undefined;
  readonly retryLabel?: string | undefined;
}

export function ErrorState({ title, detail, correlationId, onRetry, retryLabel }: ErrorStateProps) {
  return (
    <StateBlock
      tone="error"
      role="alert"
      title={title}
      detail={detail}
      correlationId={correlationId}
      action={
        onRetry === undefined ? undefined : (
          <button type="button" className="am-button" onClick={onRetry}>
            {retryLabel ?? 'Повторить'}
          </button>
        )
      }
    />
  );
}

export interface UnsupportedStateProps {
  readonly title: string;
  /** Which envelope rule was violated, in the user's words. */
  readonly detail?: ReactNode | undefined;
}

/**
 * The input is outside the PC-01 envelope — encrypted, image-only, over 25 MiB, over 30
 * pages. No retry is offered because no retry will help.
 */
export function UnsupportedState({ title, detail }: UnsupportedStateProps) {
  return <StateBlock tone="warning" title={title} detail={detail} />;
}

export interface NotApplicableStateProps {
  readonly title: string;
  readonly detail?: ReactNode | undefined;
}

/**
 * The question does not apply here — a stage that was skipped, a decision history on a
 * finding nobody has judged. Distinct from `empty`, which means the answer is genuinely
 * nothing.
 */
export function NotApplicableState({ title, detail }: NotApplicableStateProps) {
  return <StateBlock tone="neutral" title={title} detail={detail} />;
}
