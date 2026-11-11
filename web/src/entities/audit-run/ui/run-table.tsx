/**
 * The runs of one version as a dense table.
 *
 * Presentational. One row is one run: its state (the badge carries `provider_mode` with it, for the
 * reason `shared/ui` states — a recorded run is not evidence of a live one, and a caption elsewhere
 * on the page is a caption a reader can miss), when it began, who started it, how long it took, how
 * many findings it published, and the two ways into it. The table replaces the list of blocks the
 * screen had: a version with many runs is read by comparing rows, which a stack of paragraphs does
 * not allow.
 *
 * There is no progress indicator and no "running…" affordance. `D-20`: `execute_run` is
 * inline, so a run is already terminal when `startRun` answers and no client can observe
 * a `running` one. A row that animated towards a state nothing can report would be a
 * promise this system cannot keep.
 *
 * `EXEC-PAR-WEB-01`: a run that froze an executor names it, with its pinned model, in a second line of
 * the state cell; a run in the queue says it is waiting for that executor. A run with none (the
 * environment source) draws no line at all.
 *
 * `EXEC2-WEB-CAP-01`: a queued run whose reading says why names it — «В очереди: исполнитель занят»
 * or «В очереди: раннер не в сети» — in the executor line, with the machine value in
 * `data-run-queue-reason`.
 *
 * `EXEC2-WEB-GROUPS-01`: a run admitted by a rule or a group says «Плановая модель…» before dispatch
 * and «Фактическая модель…, подключение…» after it (`data-run-binding` `planned` or `bound`); it never
 * names a connection before dispatch has chosen one.
 *
 * The findings count is drawn only for a state that can publish (`published`, `partial`): the reading
 * of any other state carries a count the run did not publish, and a number there would be read as a
 * result. «Разобрать» is offered only where the canonical finding review exists — a run with a
 * published result.
 *
 * `data-run-id` is on the state cell's content, the one place a reader and a test can both find a run.
 * Hrefs are built by the screen, never by the table.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import type { RunStatus } from '@/shared/api';
import { isExportableRunState } from '@/shared/api';
import { RunStateBadge, Table } from '@/shared/ui';
import type { TableColumn } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';

import { runExecutorLine, runExecutorSentence } from '../model/run-executor';
import { runPresetLine, runPresetSentence } from '../model/run-preset';
import { elapsedMs, formatElapsed, runHasPublishedResult } from '../model/run-presentation';

import styles from './run-table.module.css';

export interface RunTableProps {
  readonly runs: readonly RunStatus[];
  /** Where a run opens. Built by the screen, never by the table. */
  readonly runHref: (run: RunStatus) => string;
  /** Where a run's findings open. Built by the screen, never by the table. */
  readonly reviewHref: (run: RunStatus) => string;
  /**
   * An action the screen adds after the two links of a row (`RUN-DELETE-01`: «Удалить», for a run that may be deleted). The table
   * decides nothing about it: the screen passes the control, which draws nothing for a run it does not apply to.
   */
  readonly rowAction?: ((run: RunStatus) => ReactNode) | undefined;
}

/** Said in the «Запустил» column when the reading carries no label (a run created before migration 0051). */
export const STARTED_BY_UNKNOWN = 'неизвестно';

function StateCell({ run }: { readonly run: RunStatus }) {
  const executor = runExecutorLine(run);
  const preset = runPresetLine(run);
  return (
    <div className={styles.state} data-run-id={run.run_id}>
      <RunStateBadge state={run.state} providerMode={run.provider_mode} />
      {executor === null ? null : (
        <p className={styles.line} data-run-executor data-run-queue-reason={executor.queueReason} data-run-binding={executor.phase}>
          {runExecutorSentence(executor)}
        </p>
      )}
      {preset === null ? null : <p className={styles.line} data-run-preset>{runPresetSentence(preset)}</p>}
    </div>
  );
}

function StartedBy({ run }: { readonly run: RunStatus }) {
  const label = run.started_by_label?.trim();
  return label === undefined || label === ''
    ? <span className={styles.unknown}>{STARTED_BY_UNKNOWN}</span>
    : <>{label}</>;
}

export function RunTable({ runs, runHref, reviewHref, rowAction }: RunTableProps) {
  const columns: readonly TableColumn<RunStatus>[] = [
    { key: 'state', header: 'Состояние', cell: (run) => <StateCell run={run} /> },
    { key: 'started', header: 'Начат', cell: (run) => <span className={styles.figure}>{formatInstant(run.created_at)}</span> },
    { key: 'startedBy', header: 'Запустил', cell: (run) => <StartedBy run={run} /> },
    {
      key: 'duration',
      header: 'Длительность',
      cell: (run) => <span className={styles.figure}>{formatElapsed(elapsedMs(run.created_at, run.terminal_at))}</span>,
    },
    {
      key: 'findings',
      header: 'Находок',
      cell: (run) => (
        <span className={styles.figure}>
          {isExportableRunState(run.state) && run.published_finding_count !== undefined ? run.published_finding_count : '—'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Действия',
      cell: (run) => (
        <div className={styles.actions}>
          <Link className="am-button am-button--quiet am-button--small" href={runHref(run)} title={run.run_id}>
            Прогон
          </Link>
          {runHasPublishedResult(run.state) ? (
            <Link className="am-button am-button--small" href={reviewHref(run)}>
              Разобрать
            </Link>
          ) : null}
          {rowAction === undefined ? null : rowAction(run)}
        </div>
      ),
    },
  ];
  return <Table columns={columns} rows={runs} rowKey={(run) => run.run_id} />;
}
