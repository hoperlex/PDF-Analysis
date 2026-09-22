'use client';

/** @jsxRuntime automatic */

/**
 * Download the run's CSV.
 *
 * The column list is **consumed**, never restated: `CSV_COLUMNS` and `CSV_ENCODING` come
 * from `@/shared/api`, where `A5` froze them against `P02_SEAMS.md` §6 with a contract test.
 * A second copy of the seventeen columns in this file is how a UI ends up promising the
 * user a column the server stopped sending, so there is no literal column name anywhere
 * here — a renamed column changes what this panel displays, and the unit test beside it
 * goes red.
 *
 * The panel holds no polling state, because there is nothing to poll: the export endpoint
 * is synchronous, nothing is created, and there is no export resource and no export
 * identity (seam §7).
 *
 * Offering the control is `isExportableRunState`, which encodes `OD-11` — `published` and
 * `partial` export, and `partial` exports **with** its degradation carried in the
 * `run_state` column rather than being refused or silently emptied. The server stays the
 * authority; this only decides whether a button is worth showing.
 *
 * `provider_mode` is rendered on the run badge here as well as on the review header. A
 * recorded run must never be presentable as a live one, and the CSV the user is about to
 * hand to someone else carries `provider_mode` as its own column — the screen should say so
 * before they do.
 */

import type { ProviderMode, RunId, RunState } from '@/shared/api';
import { CSV_COLUMNS, CSV_ENCODING, csvFileName, isExportableRunState } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, NotApplicableState, RunStateBadge, STATE_LABELS } from '@/shared/ui';

export interface ExportPanelProps {
  readonly runId: RunId;
  readonly runState: RunState;
  readonly providerMode: ProviderMode;
  readonly onExport: () => void;
  readonly isPending?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  readonly lastFileName?: string | null | undefined;
}

export function ExportPanel({
  runId,
  runState,
  providerMode,
  onExport,
  isPending,
  error,
  lastFileName,
}: ExportPanelProps) {
  const exportable = isExportableRunState(runState);

  return (
    <section className="am-export" data-run-id={runId} data-exportable={exportable ? 'true' : 'false'}>
      <header className="am-export__header">
        <h3>Выгрузка</h3>
        <RunStateBadge state={runState} providerMode={providerMode} />
      </header>

      {exportable ? (
        <>
          <button
            type="button"
            className="am-button"
            data-intent="export"
            disabled={isPending === true}
            onClick={onExport}
          >
            {isPending === true ? 'Готовлю…' : `Скачать ${csvFileName(runId)}`}
          </button>
          {/*
            `R-18` names the seventeen column names printed as a list — "documentation
            standing where an interface should be". They are still here, still taken from
            `CSV_COLUMNS` and still carrying `data-csv-column`, but behind the sentence
            that describes them. The summary is the sentence this panel already had; no
            string is invented, and the disclosure is closed until a reader asks.
          */}
          <details className="am-export__disclosure">
            <summary>
              <span className="am-export__encoding">
                Колонок: {CSV_COLUMNS.length}; кодировка {CSV_ENCODING.charset}
                {CSV_ENCODING.byteOrderMark ? ' с меткой порядка байтов' : ''}; экранирование по
                RFC 4180; одна строка на свидетельство.
              </span>
            </summary>
            <ol className="am-export__columns">
              {CSV_COLUMNS.map((column) => (
                <li key={column} data-csv-column={column}>
                  {column}
                </li>
              ))}
            </ol>
          </details>
          {lastFileName !== undefined && lastFileName !== null ? (
            <p className="am-export__last" data-last-file={lastFileName}>
              Downloaded {lastFileName}
            </p>
          ) : null}
        </>
      ) : (
        <NotApplicableState
          title="У этого прогона нет результата для выгрузки"
          detail={
            <p>
              Прогон выгружается, когда его терминальное состояние публикует результат —{' '}
              <span data-run-state="published">{STATE_LABELS.published}</span> или{' '}
              <span data-run-state="partial">{STATE_LABELS.partial}</span>. Этот прогон —{' '}
              <span data-run-state={runState}>{STATE_LABELS[runState]}</span>, поэтому писать нечего. Повтор не предлагается: он не
              меняет терминальное состояние.
            </p>
          }
        />
      )}

      {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
    </section>
  );
}
