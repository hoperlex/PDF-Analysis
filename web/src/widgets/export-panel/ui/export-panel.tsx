'use client';

/** @jsxRuntime automatic */

/**
 * Download the run's CSV, and since `W57B-NORMS-CATALOGUE-XLSX-01` its Excel workbook.
 *
 * The column list is **consumed**, never restated: `CSV_COLUMNS` and `CSV_ENCODING` come
 * from `@/shared/api`, where `A5` froze them against `P02_SEAMS.md` §6 with a contract test.
 * A second copy of the nineteen columns in this file is how a UI ends up promising the
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
 * `provider_mode` is rendered on the run badge in the card layout, and always on the review header. A
 * recorded run must never be presentable as a live one, and the CSV the user is about to
 * hand to someone else carries `provider_mode` as its own column — the screen should say so
 * before they do. The bar (`UIP-S06-05`) draws no badge of its own: «Разбор» says the state and the mode of the run
 * in its header line (`UIP-S06-04`), one line above it, and a second badge in the file actions would be a second place
 * to keep right.
 *
 * «Скачать Excel» sits beside the CSV button, on the same exportability rule. The workbook is
 * the server's (`exportRunXlsx`); this panel owns its own download (`useExportRunXlsx`) so
 * every screen that shows the panel offers it, and says a refusal in words: a version
 * without verifiable sheet labels and a run whose norm citations do not verify are refused
 * by the server, never answered with an empty file.
 *
 * «Загрузить решения из Excel» (`R-151d`) is the way back: the same workbook, edited, for an expert.
 *
 * «Скачать пакет аудита» (UI-A-76) is the original's archive of one run: the CSV, the extended review's reports when the run
 * has them, the version's PDF and a manifest of digests, built in the browser by the evidence-package builder. It is offered
 * where the page names the run's version and says the session may export (`auditPackage`).
 *
 * ## The bar (`UIP-S06-05`)
 *
 * On «Разбор» the files take one place at the right of the top row: «Скачать ▾», a button that opens CSV, Excel and the
 * audit package (the last two on the conditions they always had), and, for an expert, «Загрузить решения». No frame, no
 * title «Выгрузка» and no state badge stand around them. What the file actions say about themselves is one line under the
 * buttons: «Готовлю…», «Собираю пакет…», «Скачан …», and each refusal in the words it had; the description of the
 * selection and «О файле: колонок N» open from the «?» beside them.
 *
 * The dropdown is the panel's own `<details>`, not the shared `Menu`: a menu item there is a string, and these items
 * keep what the buttons had — a tooltip on the package that says what it holds before the first press, a disabled state
 * while a file is being made, and the `data-intent` the browser journey and the tests press by.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import type { ProviderMode, RunId, RunState, VersionUid } from '@/shared/api';
import {
  ApiError,
  CSV_COLUMNS,
  CSV_ENCODING,
  RUN_STATE_VALUES,
  csvFileName,
  isExportableRunState,
} from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { useExportRunXlsx } from '@/features/export-run';
import type { ExportVerdictFilter } from '@/features/export-run';
import { ImportDecisions } from '@/features/import-decisions';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, NotApplicableState, RunStateBadge, STATE_LABELS } from '@/shared/ui';

import { AUDIT_PACKAGE_TITLE } from '../model/audit-package';
import { useAuditPackage } from '../model/use-audit-package';
import { AuditPackageDownload } from './audit-package-download';
import styles from './export-panel.module.css';

export interface ExportPanelProps {
  readonly runId: RunId;
  readonly runState: RunState;
  readonly providerMode: ProviderMode;
  readonly onExport: () => void;
  readonly isPending?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  readonly lastFileName?: string | null | undefined;
  /** `R-151d`: offer «Загрузить решения из Excel» — an expert's act, so the page says whether the caller is one. */
  readonly mayImportDecisions?: boolean | undefined;
  /** `UI-A-76`: offer «Скачать пакет аудита» for the run's version; absent for a session that may not export. */
  readonly auditPackage?: { readonly versionUid: VersionUid } | undefined;
  /**
   * `card` (the default) is the panel as it always was. `bar` is the original's toolbar: the title, the state and
   * the three file actions in one row over the findings, the file description beside them.
   */
  readonly layout?: 'card' | 'bar' | undefined;
  readonly verdict?: ExportVerdictFilter | undefined;
  readonly scopeCaption?: string | undefined;
}

const UNKNOWN_RUN_STATE_TITLE = 'Прогон содержит неизвестное состояние.';

/** The workbook's own refusals, in words; the codes are the server's. */
const XLSX_REFUSALS: Readonly<Record<string, string>> = {
  storage_integrity_error:
    'У версии нет проверяемой разметки листов портала, поэтому столбец «Лист/стр.» заполнить нечем — Excel не собран. CSV по-прежнему доступен.',
  required_norm_unavailable:
    'Цитаты норм этого прогона не проходят проверку по его набору норм — Excel без них не собирается. CSV по-прежнему доступен.',
};

/** What the panel says when the workbook was refused or failed. */
export function xlsxFailure(error: unknown): ErrorStateProps {
  if (error instanceof ApiError && XLSX_REFUSALS[error.errorCode] !== undefined) {
    return {
      title: 'Excel не выгружен',
      detail: XLSX_REFUSALS[error.errorCode],
      correlationId: error.correlationId,
    };
  }
  const message = failureMessage(error);
  return { title: 'Excel не выгружен', detail: message.detail, correlationId: message.correlationId };
}

/** «Скачать Excel» and its own outcome. */
function XlsxDownload({ runId, verdict }: { readonly runId: RunId; readonly verdict?: ExportVerdictFilter | undefined }) {
  const exporter = useExportRunXlsx({ runId, verdict });
  return (
    <div data-export-format="xlsx">
      <button
        type="button"
        className="am-button am-button--quiet"
        data-intent="export-xlsx"
        disabled={exporter.isPending}
        onClick={exporter.download}
      >
        {exporter.isPending ? 'Готовлю Excel…' : 'Скачать Excel'}
      </button>
      {exporter.lastFileName !== null ? (
        <p className="am-export__last" data-last-file={exporter.lastFileName}>
          Скачан {exporter.lastFileName}
        </p>
      ) : null}
      {exporter.error !== null ? <ErrorState {...xlsxFailure(exporter.error)} /> : null}
    </div>
  );
}

/** What one file action says about itself: the state of the request in flight and its last outcome. */
export interface ExportFileState {
  readonly pending: boolean;
  /** The file the last request handed to the browser; absent before one, and after a refusal. */
  readonly lastFileName: string | null;
  /** The refusal, in the words the panel says it in. */
  readonly error: ErrorStateProps | null;
  readonly onDownload: () => void;
}

/** The audit package: as a file, and it also reports its phase and can be cancelled while it builds. */
export interface ExportPackageState {
  readonly pending: boolean;
  /** The phase while it builds, what the package holds or that it was cancelled after. */
  readonly status: string | null;
  readonly error: ErrorStateProps | null;
  readonly onDownload: () => void;
  readonly onCancel: () => void;
}

/**
 * A `<details>` that opens a small panel under its summary and closes the way a popover does: a press outside it, Escape (with
 * focus back on the summary) and, for a list of actions, the choice of one (`close` is handed to the children).
 */
function Popover({ summary, summaryClassName, label, title, marker, children }: {
  readonly summary: ReactNode;
  readonly summaryClassName: string;
  readonly label?: string | undefined;
  readonly title?: string | undefined;
  readonly marker: string;
  readonly children: (close: () => void) => ReactNode;
}) {
  const root = useRef<HTMLDetailsElement>(null);
  const close = () => {
    if (root.current !== null) root.current.open = false;
  };
  useEffect(() => {
    const node = root.current;
    if (node === null) return undefined;
    const outside = (event: Event) => {
      if (node.open && event.target instanceof Node && !node.contains(event.target)) node.open = false;
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !node.open) return;
      node.open = false;
      node.querySelector('summary')?.focus();
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, []);
  return (
    <details ref={root} className={styles.popover} {...{ [marker]: '' }}>
      <summary className={summaryClassName} aria-label={label} title={title}>{summary}</summary>
      <div className={styles.popup}>{children(close)}</div>
    </details>
  );
}

export interface ExportBarViewProps {
  readonly runId: RunId;
  readonly csv: ExportFileState;
  readonly xlsx: ExportFileState;
  /** Absent for a session that may not export: «Пакет аудита» is not offered. */
  readonly pack: ExportPackageState | null;
  /** «Загрузить решения» with its own report, for an expert; absent for everyone else. */
  readonly importDecisions?: ReactNode | undefined;
  readonly verdict?: ExportVerdictFilter | undefined;
  readonly scopeCaption?: string | undefined;
}

/** What a file action says while it works: the words it always had. */
function statusLines(csv: ExportFileState, xlsx: ExportFileState, pack: ExportPackageState | null): readonly ReactNode[] {
  const lines: ReactNode[] = [];
  if (csv.pending) lines.push(<span key="csv-pending" data-export-state="csv-pending">Готовлю…</span>);
  if (xlsx.pending) lines.push(<span key="xlsx-pending" data-export-state="xlsx-pending">Готовлю Excel…</span>);
  if (pack?.pending === true) {
    lines.push(
      <span key="pack-pending" data-export-state="audit-package-pending">
        Собираю пакет…{' '}
        <button type="button" className="am-button am-button--quiet am-button--small" data-intent="cancel-audit-package" onClick={pack.onCancel}>
          Отменить
        </button>
      </span>,
    );
  }
  for (const [key, file] of [['csv', csv], ['xlsx', xlsx]] as const) {
    if (file.lastFileName !== null) {
      lines.push(
        <span key={`${key}-last`} className={`am-export__last ${styles.done}`} data-last-file={file.lastFileName}>
          Скачан {file.lastFileName}
        </span>,
      );
    }
  }
  if (pack?.status !== null && pack?.status !== undefined) {
    lines.push(
      <span key="pack-status" className={`am-export__last ${styles.done}`} role="status" aria-live="polite" data-audit-package-status="">
        {pack.status}
      </span>,
    );
  }
  return lines;
}

/**
 * The files of «Разбор» as the original's top row has them (`UIP-S06-05`): «Скачать ▾» and, for an expert, «Загрузить
 * решения», with the «?» that opens the description of the selection and of the file. Under them, in one line, what the
 * actions say: their state, the file handed over, each refusal. Pure over the states it is given, so every one of them can
 * be drawn.
 */
export function ExportBarView({ runId, csv, xlsx, pack, importDecisions, verdict, scopeCaption }: ExportBarViewProps) {
  const lines = statusLines(csv, xlsx, pack);
  const refusals = [csv.error, xlsx.error, pack?.error ?? null].filter((refusal) => refusal !== null);
  return (
    <>
      <div className={styles.row}>
        <Popover marker="data-export-menu" summaryClassName={`am-button am-button--quiet am-button--small ${styles.trigger}`} summary={<>Скачать <span aria-hidden="true">▾</span></>}>
          {(close) => (
            <ul className={styles.items}>
              <li data-export-format="csv">
                <button
                  type="button"
                  className={styles.item}
                  data-intent="export"
                  title={csvFileName(runId)}
                  disabled={csv.pending}
                  onClick={() => { close(); csv.onDownload(); }}
                >
                  CSV
                </button>
              </li>
              <li data-export-format="xlsx">
                <button
                  type="button"
                  className={styles.item}
                  data-intent="export-xlsx"
                  disabled={xlsx.pending}
                  onClick={() => { close(); xlsx.onDownload(); }}
                >
                  Excel
                </button>
              </li>
              {pack === null ? null : (
                <li data-export-format="audit-package">
                  <button
                    type="button"
                    className={styles.item}
                    data-intent="export-audit-package"
                    title={AUDIT_PACKAGE_TITLE}
                    disabled={pack.pending}
                    onClick={() => { close(); pack.onDownload(); }}
                  >
                    Пакет аудита
                  </button>
                </li>
              )}
            </ul>
          )}
        </Popover>
        {importDecisions}
        <Popover marker="data-export-help" summaryClassName={`am-button am-button--quiet am-button--small ${styles.help}`} summary="?" label="О выгрузке" title="О выгрузке">
          {() => (
            <>
              {scopeCaption === undefined ? null : <p className={styles.scope} data-export-scope={verdict ?? 'all'}>{scopeCaption}</p>}
              <details className={`am-export__disclosure ${styles.barDisclosure}`}>
                <summary>
                  <span className="am-export__encoding">О файле: колонок {CSV_COLUMNS.length}</span>
                </summary>
                <p className="am-export__encoding">
                  Колонок: {CSV_COLUMNS.length}; кодировка {CSV_ENCODING.charset}
                  {CSV_ENCODING.byteOrderMark ? ' с меткой порядка байтов' : ''}; экранирование по
                  RFC 4180; одна строка на свидетельство.
                </p>
                <ol className="am-export__columns">
                  {CSV_COLUMNS.map((column) => (
                    <li key={column} data-csv-column={column}>
                      {column}
                    </li>
                  ))}
                </ol>
              </details>
            </>
          )}
        </Popover>
      </div>
      {lines.length === 0 ? null : <div className={styles.status} data-export-status="">{lines}</div>}
      {refusals.map((refusal) => (
        <div key={refusal.title} className={styles.refusal}>
          <ErrorState {...refusal} />
        </div>
      ))}
    </>
  );
}

/** The bar with the audit package's own state: a separate component, because its hook needs the version. */
function PackageBar({ versionUid, ...bar }: Omit<ExportBarViewProps, 'pack'> & { readonly versionUid: VersionUid }) {
  const pack = useAuditPackage({ runId: bar.runId, versionUid });
  return <ExportBarView {...bar} pack={{ pending: pack.isPending, status: pack.status, error: pack.error, onDownload: pack.download, onCancel: pack.cancel }} />;
}

/** The bar over the workbook's own state; the CSV's is the page's, handed in. */
function ExportBar({ auditPackage, ...bar }: Omit<ExportBarViewProps, 'pack' | 'xlsx'> & { readonly auditPackage?: { readonly versionUid: VersionUid } | undefined }) {
  const exporter = useExportRunXlsx({ runId: bar.runId, verdict: bar.verdict });
  const xlsx: ExportFileState = {
    pending: exporter.isPending,
    lastFileName: exporter.lastFileName,
    error: exporter.error === null ? null : xlsxFailure(exporter.error),
    onDownload: exporter.download,
  };
  return auditPackage === undefined
    ? <ExportBarView {...bar} xlsx={xlsx} pack={null} />
    : <PackageBar {...bar} xlsx={xlsx} versionUid={auditPackage.versionUid} />;
}

export function ExportPanel({
  runId,
  runState,
  providerMode,
  onExport,
  isPending,
  error,
  lastFileName,
  mayImportDecisions,
  auditPackage,
  layout,
  verdict,
  scopeCaption,
}: ExportPanelProps) {
  const bar = layout === 'bar';
  if (!(RUN_STATE_VALUES as readonly unknown[]).includes(runState)) {
    return (
      <section className="am-export" data-export-fault="closed-vocabulary">
        <ErrorState
          title={UNKNOWN_RUN_STATE_TITLE}
          detail="Выгрузку нельзя предложить достоверно — панель скрыта."
        />
      </section>
    );
  }

  const exportable = isExportableRunState(runState);
  const notApplicable = (
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
  );

  if (bar) {
    // `UIP-S06-05`: no frame, no title and no state badge; the run's state and mode are the page header's.
    return (
      <section className={`am-export ${styles.bar}`} data-run-id={runId} data-exportable={exportable ? 'true' : 'false'}>
        {exportable ? (
          <ExportBar
            runId={runId}
            csv={{
              pending: isPending === true,
              lastFileName: lastFileName ?? null,
              error: error ?? null,
              onDownload: onExport,
            }}
            importDecisions={mayImportDecisions === true ? <ImportDecisions runId={runId} inline /> : undefined}
            auditPackage={auditPackage}
            verdict={verdict}
            scopeCaption={scopeCaption}
          />
        ) : (
          <>
            {notApplicable}
            {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
          </>
        )}
      </section>
    );
  }

  return (
    <section
      className="am-export"
      data-run-id={runId}
      data-exportable={exportable ? 'true' : 'false'}
    >
      <header className="am-export__header">
        <h3>Выгрузка</h3>
        <RunStateBadge state={runState} providerMode={providerMode} />
      </header>

      {exportable ? (
        <>
          {/* The three file actions in one row; each says its own outcome under it. */}
          <div className="am-export__actions">
            <button
              type="button"
              className="am-button"
              data-intent="export"
              disabled={isPending === true}
              onClick={onExport}
            >
              {isPending === true ? 'Готовлю…' : `Скачать ${csvFileName(runId)}`}
            </button>
            <XlsxDownload runId={runId} verdict={verdict} />
            {mayImportDecisions === true ? <ImportDecisions runId={runId} /> : null}
            {auditPackage === undefined ? null : <AuditPackageDownload runId={runId} versionUid={auditPackage.versionUid} />}
          </div>
          {scopeCaption === undefined ? null : <p className="am-note" data-export-scope={verdict ?? 'all'}>{scopeCaption}</p>}
          {/*
            `R-18` names the column names printed as a list — "documentation
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
              Скачан {lastFileName}
            </p>
          ) : null}
        </>
      ) : (
        notApplicable
      )}

      {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
    </section>
  );
}
