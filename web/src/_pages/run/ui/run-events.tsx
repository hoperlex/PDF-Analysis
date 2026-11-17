'use client';

/**
 * `UI-B-39`: the run page shows the run's own events, as the original's «Лог» tab of a project does —
 * the execution journal filtered to this run, its first page, with the way to the whole journal. The
 * journal is an operator's read (`R-150w`): a viewer is not offered it; while the account is not known yet
 * the block is drawn and the server answers for itself.
 *
 * `UIP-S08-03`: the log opens with a line that says what the run is doing now («Сейчас: Анализ текста · стр. 3 из 10») or how it
 * ended («Прогон завершён: опубликован»), from the journal's own events; under it «Скопировать», «Автообновление» and the count
 * of the page; under those the events in groups by stage, without the «Прогон» column the whole page is about.
 */

import Link from 'next/link';
import { useState } from 'react';

import type { RunId } from '@/shared/api';
import { routes } from '@/shared/lib';
import { ErrorState, LoadingState } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { executionFailure, journalStatus, useExecutionJournal } from '@/entities/execution';
import { ExecutionJournal, JournalControls } from '@/widgets/execution-journal';

/** The roles that read the execution journal (`R-150w`); an unknown account is left to the server. */
export function mayReadJournal(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}

export function RunEvents({ runId }: { readonly runId: string }) {
  const me = useMe();
  const allowed = mayReadJournal(me.data?.roles);
  // «Автообновление» is the journal's own switch (`UI-B-43`): on, the page is read again at the operational cadence.
  const [autoRefresh, setAutoRefresh] = useState(true);
  const journal = useExecutionJournal(runId as RunId, undefined, allowed, autoRefresh);
  if (!allowed) return null;
  const status = journal.data === undefined ? null : journalStatus(journal.data.items);
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
      {status === null || status.text === null ? null : <p data-journal-status={status.kind}><strong>{status.text}</strong></p>}
      {journal.data === undefined ? null : (
        <JournalControls entries={journal.data.items} runId={runId} autoRefresh={autoRefresh} onAutoRefresh={setAutoRefresh} />
      )}
      {journal.data !== undefined ? <ExecutionJournal scope="run" entries={journal.data.items} onNext={null} onPrevious={null} /> : null}
      <p>
        <Link href={routes.logs(runId)}>Весь журнал прогона</Link>
      </p>
    </section>
  );
}
