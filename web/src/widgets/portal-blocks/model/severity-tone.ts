/**
 * The badge tone of a severity, the one `SeverityBadge` draws it in (`entities/finding`), for a count
 * that stands for several findings. `null` is a page whose findings no expert has given a severity yet:
 * the neutral tone, never one borrowed from the model's proposal (AGENTS §4).
 */

import type { Severity } from '@/shared/api';
import { assertNever } from '@/shared/lib';

export type SeverityTone = 'failed' | 'degraded' | 'active' | 'inert';

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
    case 'check_adjacent':
      return 'inert';
    default:
      return assertNever(severity, 'severityTone');
  }
}
