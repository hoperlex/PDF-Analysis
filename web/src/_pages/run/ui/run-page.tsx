'use client';

/**
 * `/projects/{project_uid}/runs/{run_id}` — run progress.
 *
 * The only screen that polls, and it polls through the one shared loop. Review is a
 * child of this route, not a sibling: a finding is only meaningful against the run that
 * produced it.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { PageShell } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { CancelRunControl } from '@/features/cancel-run';
import { DeleteRunControl } from '@/features/delete-run';
import { useMe } from '@/entities/account';

import { LazyRunProgress } from './lazy-run-progress';
import { RunEvents, mayReadJournal } from './run-events';
import styles from './run-page.module.css';
import { DocumentContext } from '@/widgets/document-context';

export interface RunPageProps {
  readonly projectUid: string;
  readonly runId: string;
}

export function RunPage({ projectUid, runId }: RunPageProps) {
  const me = useMe();
  const router = useRouter();
  // `UI-B-39`, `R-150w`: the run's events are an operator's read, so a read-only account is not offered the tab at all.
  const journal = mayReadJournal(me.data?.roles) ? <RunEvents runId={runId} /> : undefined;
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
          <Link href={routes.projects()}>Все проекты</Link>
        </>
      }
    >
      <DocumentContext projectUid={projectUid} runId={runId} current="run" />
      <div className={styles.content}>
        {/* «Отменить прогон» sits in the head beside the stages, as the original's «Отменить» on its pipeline card; «Удалить прогон»
            (`RUN-DELETE-01`) takes its place once the run has ended without a clean result, and after it the page leaves for the run's
            version, where the run is no longer listed. «Запустить с этапа»
            (`UI-A-60`) moved into «Этапы анализа раздела», which a chip of the rail opens; the events are the tab «Журнал»
            (`RUN-SCREEN-01a`). */}
        <LazyRunProgress
          projectUid={projectUid}
          runId={runId}
          actions={
            <>
              <CancelRunControl runId={runId} />
              <DeleteRunControl runId={runId} onDeleted={(run) => router.push(routes.version(run.project_uid, run.version_uid))} />
            </>
          }
          {...(journal === undefined ? {} : { journal })}
        />
      </div>
    </PageShell>
  );
}
