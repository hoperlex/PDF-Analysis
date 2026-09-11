/**
 * `/projects/{project_uid}/runs/{run_id}` — run progress.
 *
 * Delegation-only. See the note in `/projects/page.tsx`.
 */

import { RunPage } from '@/_pages/run';

export default async function RunRoute({
  params,
}: {
  params: Promise<{ project_uid: string; run_id: string }>;
}) {
  const { project_uid, run_id } = await params;
  return <RunPage projectUid={project_uid} runId={run_id} />;
}
