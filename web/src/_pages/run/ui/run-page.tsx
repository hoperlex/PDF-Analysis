'use client';

/**
 * `/projects/{project_uid}/runs/{run_id}` — run progress.
 *
 * The only screen that polls, and it polls through the one shared loop. Review is a
 * child of this route, not a sibling: a finding is only meaningful against the run that
 * produced it.
 */

import Link from 'next/link';

import { PageShell } from '@/shared/ui';
import { RunProgress } from '@/widgets/run-progress';

export interface RunPageProps {
  readonly projectUid: string;
  readonly runId: string;
}

export function RunPage({ projectUid, runId }: RunPageProps) {
  return (
    <PageShell
      title="Run"
      subtitle={
        <>
          <code>{runId}</code>
        </>
      }
      actions={<Link href={`/projects/${projectUid}`}>Back to project</Link>}
    >
      <RunProgress projectUid={projectUid} runId={runId} />
    </PageShell>
  );
}
