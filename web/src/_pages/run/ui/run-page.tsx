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
import { routes } from '@/shared/lib';
import { CancelRunControl } from '@/features/cancel-run';
import { StartRunFromStageControl } from '@/features/start-run-from-stage';

import { LazyRunProgress } from './lazy-run-progress';
import { RunEvents } from './run-events';
import styles from './run-page.module.css';
import { DocumentContext } from '@/widgets/document-context';

export interface RunPageProps {
  readonly projectUid: string;
  readonly runId: string;
}

export function RunPage({ projectUid, runId }: RunPageProps) {
  return (
    <PageShell
      title="Прогон"
      surface="canvas"
      subtitle={
        <>
          <code>{runId}</code>
        </>
      }
      actions={
        <>
          <Link href={routes.project(projectUid)}>К проекту</Link>{' '}
          <Link href={routes.logs(runId)}>Журнал прогона</Link>{' '}
          <Link href={routes.projects()}>Все проекты</Link>
        </>
      }
    >
      <DocumentContext projectUid={projectUid} runId={runId} current="run" />
      <div className={styles.content}>
        {/* «Отменить прогон» sits in the head beside the stages, as the original's «Отменить» on its pipeline card. */}
        {/* «Запустить с этапа» (`UI-A-60`) is the ended run's counterpart: it is drawn only once the run has stopped. */}
        <LazyRunProgress projectUid={projectUid} runId={runId} actions={<><CancelRunControl runId={runId} /><StartRunFromStageControl runId={runId} /></>} />
        <RunEvents runId={runId} />
      </div>
    </PageShell>
  );
}
