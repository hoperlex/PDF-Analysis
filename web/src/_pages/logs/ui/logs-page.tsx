'use client';

import { useState } from 'react';

import { RUN_ID_PATTERN } from '@/shared/api';
import { executionFailure, useExecutionJournal } from '@/entities/execution';
import { ExecutionJournal } from '@/widgets/execution-journal';
import { ErrorState, LoadingState, PageShell } from '@/shared/ui';

export interface LogsPageProps {
  readonly initialRunId?: string | undefined;
}

const RUN_ID = new RegExp(RUN_ID_PATTERN);

export function LogsPage({ initialRunId }: LogsPageProps) {
  const [draft, setDraft] = useState(initialRunId ?? '');
  const [filter, setFilter] = useState(initialRunId ?? '');
  const [cursors, setCursors] = useState<string[]>([]);
  const invalid = filter !== '' && !RUN_ID.test(filter);
  const cursor = cursors.at(-1);
  const journal = useExecutionJournal(invalid || filter === '' ? undefined : filter, cursor, !invalid);
  const next = journal.data?.page.next_cursor ?? null;
  const readFailure = journal.error === null ? null : executionFailure(journal.error, false);

  return (
    <PageShell
      title="Журнал выполнения"
      subtitle="События выполнения на сервере, новые сверху. Показаны только безопасные поля договора."
      actions={<button type="button" className="am-button am-button--quiet" disabled={invalid} onClick={() => void journal.refetch()}>Обновить</button>}
    >
      <form className="am-form" onSubmit={(event) => {
        event.preventDefault();
        setFilter(draft.trim());
        setCursors([]);
      }}>
        <label htmlFor="execution-run-filter">Прогон</label>
        <div className="am-form__row">
          <input
            id="execution-run-filter"
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Идентификатор прогона"
            aria-describedby="execution-run-filter-help"
          />
          <button type="submit" className="am-button">Показать</button>
        </div>
        <p id="execution-run-filter-help" className="am-form__hint">Пустое поле показывает все прогоны.</p>
      </form>
      {invalid ? <ErrorState title="Неверный идентификатор прогона" detail="Проверьте идентификатор и повторите отбор." /> : null}
      {!invalid && journal.isPending ? <LoadingState what="журнал выполнения" /> : null}
      {!invalid && readFailure !== null ? (
        <div data-execution-read-failure={readFailure.kind}>
          <ErrorState
            title="Журнал не открылся"
            detail={readFailure.detail}
            correlationId={readFailure.correlationId}
            onRetry={() => void journal.refetch()}
          />
        </div>
      ) : null}
      {!invalid && journal.data !== undefined && readFailure === null ? (
        <ExecutionJournal
          entries={journal.data.items}
          onPrevious={cursors.length === 0 ? null : () => setCursors((current) => current.slice(0, -1))}
          onNext={next === null ? null : () => setCursors((current) => [...current, next])}
        />
      ) : null}
    </PageShell>
  );
}
