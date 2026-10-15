/** Labels for the closed AR v2 severity vocabulary. No expert choice is implied. */
import type { Severity } from '@/shared/api';

export const SEVERITY_LABELS: Readonly<Record<Severity, string>> = {
  critical: 'Критическое',
  economic: 'Экономическое',
  operational: 'Эксплуатационное',
  recommendation: 'Рекомендация',
  check_adjacent: 'Проверить смежный раздел',
};
