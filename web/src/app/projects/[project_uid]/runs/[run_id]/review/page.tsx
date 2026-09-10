/**
 * `/projects/{project_uid}/runs/{run_id}/review` — findings, evidence, decisions, export.
 *
 * Delegation-only. When `B8` lands `@/_pages/review`, the body becomes
 * `return <ReviewPage projectUid={project_uid} runId={run_id} />;`.
 *
 * Review is a child of the run, not a sibling: a finding is only meaningful against the
 * run that produced it, and the URL says so.
 */

import { RoutePlaceholder } from '@/shared/ui';

export default async function ReviewRoute({
  params,
}: {
  params: Promise<{ project_uid: string; run_id: string }>;
}) {
  const { project_uid, run_id } = await params;
  return (
    <RoutePlaceholder
      screen="Review"
      route={`/projects/${project_uid}/runs/${run_id}/review`}
      awaitingModule="@/_pages/review"
      owner="Gate B session B8"
    />
  );
}
