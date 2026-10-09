/**
 * `/workers` remains the distributed-worker placeholder. W53 introduced durable Jobs,
 * Attempts and leases inside the API process, so this copy describes their presence.
 * The separate worker service and its screen remain outside this wave.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function WorkersPage() {
  return (
    <RoutePlaceholder
      screen="Исполнители"
      route="/workers"
      unavailability="Раздела нет в альфе"
      headline="Распределённых исполнителей в альфе нет."
      promise="Прогоны выполняются внутри приложения с учётом задач и попыток. Распределённые исполнители не входят в этот выпуск; отдельный экран появится после их внедрения."
    />
  );
}
