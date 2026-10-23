'use client';

/** @jsxRuntime automatic */

/**
 * The severity badge.
 *
 * Same discipline as `VerdictBadge`: the value set is exactly the generated `Severity`, the
 * Russian label comes from `SEVERITY_LABELS`, the contract value stays on `data-severity`
 * and is never rendered as prose, and a value outside the closed union is shown as a fault
 * instead of as a blank.
 *
 * The badge says WHICH severity and nothing about whose it is. The screens that use it put
 * the owner in words beside it: a proposal is the model's («предложение модели»), a decided
 * severity is the expert's («решённая важность»). Nothing here picks a colour that implies
 * the model's proposal was approved.
 */

import type { Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import { assertNever } from '@/shared/lib';

import { SEVERITY_LABELS } from '../model/severity-labels';

function toneFor(severity: Severity): string {
  switch (severity) {
    case 'critical':
      return 'failed';
    case 'economic':
      return 'degraded';
    case 'operational':
      return 'active';
    case 'recommendation':
      return 'inert';
    case 'check_adjacent':
      return 'inert';
    default:
      return assertNever(severity, 'SeverityBadge');
  }
}

export interface SeverityBadgeProps {
  readonly severity: Severity;
  /** What the badge is about, in Russian. Rendered as a tooltip; never the contract value. */
  readonly title?: string | undefined;
}

export function SeverityBadge({ severity, title }: SeverityBadgeProps) {
  if (!(SEVERITY_VALUES as readonly unknown[]).includes(severity)) {
    return (
      <span
        className="am-badge am-badge--failed"
        role="alert"
        data-closed-vocabulary-fault="severity"
      >
        <span className="am-badge__label">Неизвестная важность</span>
      </span>
    );
  }

  return (
    <span
      className={`am-badge am-badge--${toneFor(severity)}`}
      data-severity={severity}
      {...(title === undefined ? {} : { title })}
    >
      <span className="am-badge__label">{SEVERITY_LABELS[severity]}</span>
    </span>
  );
}
