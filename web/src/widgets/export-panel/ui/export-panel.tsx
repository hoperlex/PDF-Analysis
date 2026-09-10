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
import { ErrorState, NotApplicableState, RunStateBadge } from '@/shared/ui';

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
        <h3>Export</h3>
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
            {isPending === true ? 'Preparing…' : `Download ${csvFileName(runId)}`}
          </button>
          <p className="am-export__encoding">
            {CSV_COLUMNS.length} columns, {CSV_ENCODING.charset}
            {CSV_ENCODING.byteOrderMark ? ' with a byte-order mark' : ''}, RFC 4180 quoting,
            one row per evidence item.
          </p>
          <ol className="am-export__columns">
            {CSV_COLUMNS.map((column) => (
              <li key={column} data-csv-column={column}>
                {column}
              </li>
            ))}
          </ol>
          {lastFileName !== undefined && lastFileName !== null ? (
            <p className="am-export__last" data-last-file={lastFileName}>
              Downloaded {lastFileName}
            </p>
          ) : null}
        </>
      ) : (
        <NotApplicableState
          title="This run has no result to export"
          detail={
            <p>
              A run is exported when its terminal publishes a result — <code>published</code>{' '}
              or <code>partial</code>. This run is <code>{runState}</code>, so there are no
              rows to write. Nothing is retried, because no retry changes a terminal.
            </p>
          }
        />
      )}

      {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
    </section>
  );
}
