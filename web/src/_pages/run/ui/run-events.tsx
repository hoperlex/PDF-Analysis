'use client';

/**
 * `UI-B-39`: the run page shows the run's own events, as the original's «Лог» tab of a project does —
 * the execution journal filtered to this run, its first page, with the way to the whole journal. The
 * journal is an operator's read (`R-150w`): a viewer is not offered it; while the account is not known yet
 * the block is drawn and the server answers for itself.
 */

import Link from 'next/link';

import type { RunId } from '@/shared/api';
import { routes } from '@/shared/lib';
import { ErrorState, LoadingState } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { executionFailure, useExecutionJournal } from '@/entities/execution';
import { ExecutionJournal } from '@/widgets/execution-journal';

/** The roles that read the execution journal (`R-150w`); an unknown account is left to the server. */
export function mayReadJournal(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}

export function RunEvents({ runId }: { readonly runId: string }) {
  const me = useMe();
  const allowed = mayReadJournal(me.data?.roles);
  const journal = useExecutionJournal(runId as RunId, undefined, allowed);
  if (!allowed) return null;
  return (
    <section aria-labelledby="run-events-title" data-run-events={runId}>
      <h2 id="run-events-title">События прогона</h2>
      {journal.isPending ? <LoadingState what="события прогона" /> : null}
      {journal.error !== null ? (
        <ErrorState
          title="События прогона не открылись"
          detail={executionFailure(journal.error, false).detail}
          correlationId={executionFailure(journal.error, false).correlationId}
          onRetry={() => void journal.refetch()}
        />
      ) : null}
      {journal.data !== undefined ? <ExecutionJournal entries={journal.data.items} onNext={null} onPrevious={null} /> : null}
      <p>
        <Link href={routes.logs(runId)}>Весь журнал прогона</Link>
      </p>
    </section>
  );
}
