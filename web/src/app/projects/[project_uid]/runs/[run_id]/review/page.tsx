/**
 * `/projects/{project_uid}/runs/{run_id}/review` — findings, evidence, decisions, export.
 *
 * Delegation-only. `B8` has landed `@/_pages/review`, so the body is the delegation the
 * placeholder was holding the seat for.
 *
 * Review is a child of the run, not a sibling: a finding is only meaningful against the
 * run that produced it, and the URL says so.
 */

import { ReviewPage } from '@/_pages/review';

export default async function ReviewRoute({
  params,
}: {
  params: Promise<{ project_uid: string; run_id: string }>;
}) {
  const { project_uid, run_id } = await params;
  return <ReviewPage projectUid={project_uid} runId={run_id} />;
}
