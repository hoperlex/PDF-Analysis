/**
 * `/projects/{project_uid}/runs/{run_id}` — run progress.
 *
 * Delegation-only. When `B7` lands `@/_pages/run`, the body becomes
 * `return <RunPage projectUid={project_uid} runId={run_id} />;`.
 *
 * This is the one screen that polls. It renders the literal contract run states and never
 * `succeeded`, which belongs to the per-stage rows underneath it.
 */

import { RoutePlaceholder } from '@/shared/ui';

export default async function RunRoute({
  params,
}: {
  params: Promise<{ project_uid: string; run_id: string }>;
}) {
  const { project_uid, run_id } = await params;
  return (
    <RoutePlaceholder
      screen="Run"
      route={`/projects/${project_uid}/runs/${run_id}`}
      awaitingModule="@/_pages/run"
      owner="Gate B session B7"
    />
  );
}
