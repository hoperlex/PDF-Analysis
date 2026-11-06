'use client';

import { useState } from 'react';

import { RUN_ID_PATTERN } from '@/shared/api';
import { routes } from '@/shared/lib';
import { UpdateTime, executionFailure, useExecutionJournal } from '@/entities/execution';
import { EMPTY_PICKER_SELECTION, ExecutionJournal, JournalControls, RunPicker } from '@/widgets/execution-journal';
import type { RunPickerSelection } from '@/widgets/execution-journal';
import { ErrorState, LoadingState, PageShell } from '@/shared/ui';
import styles from './logs-page.module.css';

export interface LogsPageProps {
  readonly initialRunId?: string | undefined;
}

const RUN_ID = new RegExp(RUN_ID_PATTERN);

const SUBTITLE =
  'События выполнения на сервере, новые сверху. Показаны только безопасные поля договора.';

/**
 * Keep the run in the address, so the page can be reloaded or sent as it stands (`routes.logs`). The page
 * already reads `run_id` from the address when it opens; this is the other direction. History is replaced,
 * not pushed: choosing a run is a refinement of this screen, not a place the Back button should return to.
 */
function keepRunInAddress(runId: string): void {
  if (typeof window === 'undefined') return;
  window.history.replaceState(null, '', runId === '' ? routes.logs() : routes.logs(runId));
}

export function LogsPage({ initialRunId }: LogsPageProps) {
  const [draft, setDraft] = useState(initialRunId ?? '');
  const [filter, setFilter] = useState(initialRunId ?? '');
  const [cursors, setCursors] = useState<string[]>([]);
  const [selection, setSelection] = useState<RunPickerSelection>(EMPTY_PICKER_SELECTION);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const invalid = filter !== '' && !RUN_ID.test(filter);
  const cursor = cursors.at(-1);
  const journal = useExecutionJournal(invalid || filter === '' ? undefined : filter, cursor, !invalid, autoRefresh);
  const next = journal.data?.page.next_cursor ?? null;
  const readFailure = journal.error === null ? null : executionFailure(journal.error, false);
  const runInView = filter !== '' && !invalid ? filter : null;

  /** Narrow the journal to one run, or `''` for every run; the paste field follows the choice. */
  const showRun = (runId: string) => {
    setDraft(runId);
    setFilter(runId);
    setCursors([]);
    keepRunInAddress(runId);
  };

  return (
    <PageShell
      title="Журнал выполнения"
      subtitle={autoRefresh
        ? `${SUBTITLE} Журнал обновляется автоматически, пока вкладка открыта.`
        : `${SUBTITLE} Автообновление выключено.`}
      actions={<button type="button" className="am-button am-button--quiet" disabled={invalid} onClick={() => void journal.refetch()}>Обновить</button>}
    >
      {!invalid ? <UpdateTime dataUpdatedAt={journal.dataUpdatedAt} failed={journal.isError} /> : null}
      <div className={styles.filters}>
        <RunPicker
          selection={selection}
          runId={runInView}
          onSelection={setSelection}
          onChooseRun={(runId) => showRun(runId ?? '')}
        />
        <form className={styles.paste} onSubmit={(event) => {
          event.preventDefault();
          const typed = draft.trim();
          setFilter(typed);
          setCursors([]);
          // An identity that is not one is reported below and kept out of the address.
          if (typed === '' || RUN_ID.test(typed)) keepRunInAddress(typed);
        }}>
          <label htmlFor="execution-run-filter">Или вставьте идентификатор прогона</label>
          <input
            id="execution-run-filter"
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Идентификатор прогона"
            aria-describedby="execution-run-filter-help"
          />
          <button type="submit" className="am-button">Показать</button>
          <span id="execution-run-filter-help" className="am-form__hint">Пустое поле показывает все прогоны.</span>
        </form>
      </div>
      {invalid ? <ErrorState title="Неверный идентификатор прогона" detail="Проверьте идентификатор и повторите отбор." /> : null}
      {!invalid && journal.isPending ? <LoadingState what="журнал выполнения" /> : null}
      {!invalid && readFailure !== null ? (
        <div data-execution-read-failure={readFailure.kind}>
          <ErrorState
            title={journal.data === undefined ? 'Журнал не открылся' : 'Журнал не обновился'}
            detail={readFailure.detail}
            correlationId={readFailure.correlationId}
            onRetry={() => void journal.refetch()}
          />
        </div>
      ) : null}
      {!invalid ? (
        <div className={styles.journal}>
          <JournalControls
            entries={journal.data?.items}
            runId={runInView}
            autoRefresh={autoRefresh}
            onAutoRefresh={setAutoRefresh}
          />
          {journal.data !== undefined ? (
            <ExecutionJournal
              entries={journal.data.items}
              onPrevious={cursors.length === 0 ? null : () => setCursors((current) => current.slice(0, -1))}
              onNext={next === null ? null : () => setCursors((current) => [...current, next])}
            />
          ) : null}
        </div>
      ) : null}
    </PageShell>
  );
}
