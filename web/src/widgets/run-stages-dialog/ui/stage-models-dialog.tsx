'use client';

/**
 * «Модели по этапам» before a start (`UIP-S05-01`, pair S05, `Г10-B`): the window «Запустить» does **not** open — «Запустить» stays one
 * button (`R-153a`) — but the line under it does, with «Модели по этапам ▸». The window is a reading of what a start would use, in the
 * layout of the original's «Конфигурация моделей» and in our own style: the three sets on top (the one in force marked; for an expert it is a
 * display, not a switch), a table «Этап · Модель · Усилие · Доступ · Фактически работает» over the six stages, «Закрыть» at the bottom.
 *
 * The window and its buttons are the shared `Dialog`; the table is the shared `Table`.
 *
 * - **The layout is on** (`source.kind === 'plan'`): the table is the plan the readiness answer states (`readinessPlan`): the model, the
 *   effort, «по подписке» or «по ключу API», and «⚠ нет на серверах» where no server has the model. A stage with legs and a judge lists its cells
 *   with the role in front. «Фактически работает» says it in words by the roles of the cells.
 * - **The layout is off, or the route is automatic, or the readiness was not read:** there is no plan, so the table is the layout as it is saved
 *   (`useStageModelLayout`), and «Фактически работает» says the one word of the case instead of a fact it cannot read. While the layout
 *   is off, the words `LAYOUT_OFF_NOTE` stand over the table.
 *
 * It names no server and writes no number the answer does not carry. «Расширенные ▸ Модели по этапам» (the revisions, the journal and the
 * switch) is not here.
 */

import type { ReactNode } from 'react';

import type { StageModelLayout } from '@/shared/api';
import { executionFailure } from '@/entities/execution';
import { ACCESS_LABELS } from '@/entities/executor-host';
import {
  KIT_LEGEND,
  LAYOUT_OFF_NOTE,
  NOT_ON_SERVERS,
  NOT_ON_SERVERS_HINT,
  NO_LAYOUT,
  STAGE_KIT_LABELS,
  STAGE_MODELS_TITLE,
  useStageModelLayout,
} from '@/entities/stage-layout';
import type { PlanCell } from '@/entities/stage-layout';
import { Dialog, EmptyState, ErrorState, LoadingState, Table } from '@/shared/ui';

import {
  CLOSE_LABEL,
  COLUMN_ACCESS,
  COLUMN_EFFORT,
  COLUMN_FACT,
  COLUMN_MODEL,
  COLUMN_STAGE,
  KITS_IN_ORDER,
  factWordOf,
  kitOf,
  layoutStageRows,
  planStageRows,
} from '../model/stage-models-rows';
import type { StageModelsRow, StageModelsSource } from '../model/stage-models-rows';

import styles from './stage-models-dialog.module.css';

/** What the saved layout is while the window has no plan to read: the answer of its read, in the three phases of a read. */
export type StageLayoutReading =
  | { readonly state: 'loading' }
  | { readonly state: 'failed'; readonly detail: string; readonly correlationId: string | null; readonly retry: () => void }
  | { readonly state: 'ready'; readonly layout: StageModelLayout };

export interface StageModelsDialogViewProps {
  readonly source: StageModelsSource;
  /** The saved layout, for a source that has no plan; absent for the layout's own route, which reads the plan. */
  readonly layout?: StageLayoutReading | undefined;
  readonly onClose: () => void;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

/** «Только Claude · Только Codex · Свой набор»: the one in force is marked. Not a control. */
function Kits({ active }: { readonly active: string }) {
  return (
    <ul className={styles.kits} aria-label={KIT_LEGEND} data-stage-models-kits="">
      {KITS_IN_ORDER.map((kit) => (
        <li key={kit} className={styles.kit} aria-current={kit === active ? 'true' : undefined} data-layout-kit={kit}>
          {STAGE_KIT_LABELS[kit]}
        </li>
      ))}
    </ul>
  );
}

/** The cells of a row down one column, in the order of the roles; the same cells in the same order in every column. */
function CellList({ cells, draw }: { readonly cells: readonly PlanCell[]; readonly draw: (cell: PlanCell) => ReactNode }) {
  if (cells.length === 0) return null;
  return (
    <ul className={styles.cells}>
      {cells.map((cell) => (
        <li key={cell.cellKey} className={styles.cell} data-stage-cell={cell.cellKey} data-stage-role={cell.role}>
          {draw(cell)}
        </li>
      ))}
    </ul>
  );
}

/** How a cell is paid; a cell no server has says so, and nothing else in the window is marked. A cell with no access to state says nothing. */
function accessOf(cell: PlanCell): ReactNode {
  if (!cell.available) {
    return <span className={styles.missing} title={NOT_ON_SERVERS_HINT} data-host-reason="not_on_any_server">{NOT_ON_SERVERS}</span>;
  }
  return cell.access === null ? null : <span data-host-access={cell.access}>{ACCESS_LABELS[cell.access]}</span>;
}

function StageModelsTableOfWindow({ rows }: { readonly rows: readonly StageModelsRow[] }) {
  return (
    <Table<StageModelsRow>
      caption={STAGE_MODELS_TITLE}
      rowKey={(row) => row.row}
      rows={rows}
      columns={[
        { key: 'stage', header: COLUMN_STAGE, cell: (row) => row.label },
        {
          key: 'model',
          header: COLUMN_MODEL,
          cell: (row) => <CellList cells={row.cells} draw={(cell) => (cell.roleLabel === '' ? cell.model : `${cell.roleLabel}: ${cell.model}`)} />,
        },
        {
          key: 'effort',
          header: COLUMN_EFFORT,
          cell: (row) => <CellList cells={row.cells} draw={(cell) => <span data-model-effort={cell.effort}>{cell.effortLabel}</span>} />,
        },
        { key: 'access', header: COLUMN_ACCESS, cell: (row) => <CellList cells={row.cells} draw={accessOf} /> },
        { key: 'fact', header: COLUMN_FACT, cell: (row) => <span data-stage-fact={row.row}>{row.fact}</span> },
      ]}
    />
  );
}

/** The body of the window: the set, the note while the layout is off, and the table or the sentence that says why there is none. */
function Body({ source, layout }: { readonly source: StageModelsSource; readonly layout: StageLayoutReading | undefined }) {
  if (source.kind === 'plan') {
    const kit = kitOf(source, undefined);
    return (
      <>
        {kit === null ? null : <Kits active={kit} />}
        <StageModelsTableOfWindow rows={planStageRows(source.readiness)} />
      </>
    );
  }
  if (layout === undefined || layout.state === 'loading') return <LoadingState what="модели по этапам" />;
  if (layout.state === 'failed') {
    return <ErrorState title="Модели по этапам не прочитаны" detail={layout.detail} correlationId={layout.correlationId} onRetry={layout.retry} />;
  }
  const kit = kitOf(source, layout.layout);
  return (
    <>
      {kit === null ? null : <Kits active={kit} />}
      {source.kind === 'legacy' ? <p className={styles.note} data-layout-state="off">{LAYOUT_OFF_NOTE}</p> : null}
      {layout.layout.current === undefined ? (
        <EmptyState title={NO_LAYOUT} />
      ) : (
        <StageModelsTableOfWindow rows={layoutStageRows(layout.layout, factWordOf(source))} />
      )}
    </>
  );
}

/** The window as it is drawn, with its inputs given: the census, the language guard and the unit suite draw this one. */
export function StageModelsDialogView({ source, layout, onClose, staticOpen = false }: StageModelsDialogViewProps) {
  return (
    <Dialog
      title={STAGE_MODELS_TITLE}
      size="lg"
      onClose={onClose}
      staticOpen={staticOpen}
      markers={{ 'data-stage-models-dialog': '', 'data-stage-models-source': source.kind }}
      actions={
        <button type="button" className="am-button am-button--quiet" data-stage-models-close="" onClick={onClose}>
          {CLOSE_LABEL}
        </button>
      }
    >
      <Body source={source} layout={layout} />
    </Dialog>
  );
}

export interface StageModelsDialogProps {
  readonly source: StageModelsSource;
  readonly onClose: () => void;
  readonly staticOpen?: boolean | undefined;
}

/** The window of a start: the layout is read here, and only for a source that has no plan to read. */
export function StageModelsDialog({ source, onClose, staticOpen }: StageModelsDialogProps) {
  const query = useStageModelLayout(source.kind !== 'plan');
  let layout: StageLayoutReading | undefined;
  if (source.kind !== 'plan') {
    if (query.data !== undefined) {
      layout = { state: 'ready', layout: query.data };
    } else if (query.isError) {
      const failure = executionFailure(query.error, false);
      layout = { state: 'failed', detail: failure.detail, correlationId: failure.correlationId, retry: () => void query.refetch() };
    } else {
      layout = { state: 'loading' };
    }
  }
  return <StageModelsDialogView source={source} layout={layout} onClose={onClose} staticOpen={staticOpen} />;
}
