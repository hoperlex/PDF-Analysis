/**
 * The tone of a severity (`UIP-S06-03`): which `am-badge--*` modifier draws it. Computed here and nowhere else; the severity
 * badge (`ui/severity-badge.tsx`) and the round count on a block tile (`widgets/portal-blocks`) both read it.
 *
 * Five severities, five tones, in the tokens `globals.css` already has: red, amber, teal (the accent inside the application
 * frame), green and grey. «Критическое» is the failed tone, «Экономическое» the degraded one, «Эксплуатационное» the active
 * one, «Рекомендательное» the ok one and «Проверить смежный раздел» the inert one. The two that were one grey before are two
 * now, and `tests/unit/review/v2-finding-fields.test.ts` measures the distance between every two of the five in both palettes.
 *
 * A tone says WHICH severity and nothing about whose it is. Green is not «approved»: the badge is the same pill for the
 * expert's decision and for the model's proposal, and the proposal is told apart by its dashed edge, its word «предложено» and
 * its tooltip, never by a colour of its own (`R-151j`, AGENTS §4).
 *
 * `null` is a count whose findings no expert has given a severity yet: the neutral tone, never one borrowed from the model's
 * proposal. It shares the grey with «Проверить смежный раздел», which a block tile tells apart by its tooltip.
 */

import type { Severity } from '@/shared/api';
import { assertNever } from '@/shared/lib';

export type SeverityTone = 'failed' | 'degraded' | 'active' | 'ok' | 'inert';

export function severityTone(severity: Severity | null): SeverityTone {
  if (severity === null) return 'inert';
  switch (severity) {
    case 'critical':
      return 'failed';
    case 'economic':
      return 'degraded';
    case 'operational':
      return 'active';
    case 'recommendation':
      return 'ok';
    case 'check_adjacent':
      return 'inert';
    default:
      return assertNever(severity, 'severityTone');
  }
}
