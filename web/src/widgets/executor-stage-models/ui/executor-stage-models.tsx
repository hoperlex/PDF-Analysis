'use client';

/**
 * «Модели по этапам» (`HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §7.4): which model, and with what effort, does the work of
 * each of the six rows of an analysis.
 *
 * An expert reads a table of six rows, «строка — модель · усилие», and **has no control**. A row whose model no enabled server
 * can answer now carries «⚠ нет на серверах»; a row that is fine carries nothing. An administrator is also drawn «Изменить»,
 * which opens the form (`features/manage-stage-layout`). The layout is read for an expert and an administrator only: the
 * viewer neither sees the tab nor reads the layout (`R-150w`).
 *
 * While the layout is switched off, the table says so in a line: runs follow the routes as before, and the administrator can
 * still prepare a revision, since the switch cannot be turned on without a saved one. The revisions and the journal live on
 * the advanced page.
 */

import { useState } from 'react';

import type { Role, StageModelLayout } from '@/shared/api';
import { canExecute, executionFailure } from '@/entities/execution';
import { availableModelIds, mayReadHosts, useExecutorHosts } from '@/entities/executor-host';
import {
  EDIT_LABEL,
  LAYOUT_OFF_NOTE,
  LAYOUT_ON_NOTE,
  NOT_ON_SERVERS,
  NOT_ON_SERVERS_HINT,
  NO_LAYOUT,
  NO_LAYOUT_ADMIN,
  STAGE_ROW_LABELS,
  layoutTable,
  useModelCatalogue,
  useStageModelLayout,
} from '@/entities/stage-layout';
import type { TableRow } from '@/entities/stage-layout';
import { LayoutEditor } from '@/features/manage-stage-layout';
import { EmptyState, ErrorState, LoadingState, Table, UnsupportedState } from '@/shared/ui';

import styles from './executor-stage-models.module.css';

export interface StageModelsTableProps {
  readonly layout: StageModelLayout;
  /** An administrator: drawn «Изменить». */
  readonly admin: boolean;
  readonly onEdit?: (() => void) | undefined;
}

/** The note, the table and, for an administrator, «Изменить». The pure part of the screen. */
export function StageModelsTable({ layout, admin, onEdit }: StageModelsTableProps) {
  const rows = layoutTable(layout);
  return (
    <>
      <p className={styles.note} data-layout-state={layout.enabled ? 'on' : 'off'}>
        {layout.enabled ? LAYOUT_ON_NOTE : LAYOUT_OFF_NOTE}
      </p>
      {layout.current === undefined ? (
        <EmptyState title={admin ? NO_LAYOUT_ADMIN : NO_LAYOUT} />
      ) : (
        <Table<TableRow>
          caption="Модели по этапам"
          rowKey={(row) => row.row}
          rows={rows}
          columns={[
            { key: 'row', header: 'Строка', cell: (row) => STAGE_ROW_LABELS[row.row] },
            {
              key: 'model',
              header: 'Модель · усилие',
              cell: (row) => (
                <>
                  <ul className={styles.cells}>
                    {row.cells.map((cell) => (
                      <li key={cell.cellKey} className={styles.cell} data-layout-cell={cell.cellKey} data-stage-row={row.row} data-stage-role={cell.role} data-model-effort={cell.effort}>
                        {cell.text}
                      </li>
                    ))}
                  </ul>
                  {row.problem ? (
                    <span className={styles.missing} title={NOT_ON_SERVERS_HINT} data-layout-missing={row.row} data-host-reason="not_on_any_server">{NOT_ON_SERVERS}</span>
                  ) : null}
                </>
              ),
            },
          ]}
        />
      )}
      {admin && onEdit !== undefined ? (
        <p className={styles.actions}>
          <button className="am-button" type="button" data-layout-edit onClick={onEdit}>{EDIT_LABEL}</button>
        </p>
      ) : null}
    </>
  );
}

export interface ExecutorStageModelsProps {
  readonly roles: readonly Role[];
  /** Test seam: the administrator's form starts open. */
  readonly initiallyEditing?: boolean | undefined;
}

export function ExecutorStageModels({ roles, initiallyEditing = false }: ExecutorStageModelsProps) {
  const readable = mayReadHosts(roles);
  const admin = canExecute(roles, 'connections');
  const layout = useStageModelLayout(readable);
  // The models the form may offer are those some server can serve now, so the administrator also reads the servers.
  const hosts = useExecutorHosts(readable && admin);
  const catalogue = useModelCatalogue(readable && admin);
  const [editing, setEditing] = useState(initiallyEditing);

  if (!readable) {
    return <UnsupportedState title="Модели по этапам недоступны" detail="Набор моделей показывается экспертам и администраторам." />;
  }
  if (layout.isPending) return <LoadingState what="модели по этапам" />;
  if (layout.data === undefined) {
    const failure = executionFailure(layout.error, false);
    return (
      <div data-layout-read-failure={failure.kind}>
        <ErrorState title="Модели по этапам не прочитаны" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void layout.refetch()} />
      </div>
    );
  }

  const formReady = admin && editing && hosts.data !== undefined && catalogue.data !== undefined;
  return (
    <div className={styles.panel} data-executor-stage-models>
      {formReady ? (
        <LayoutEditor
          layout={layout.data}
          catalogue={catalogue.data}
          availableModelIds={availableModelIds(hosts.data)}
          onClose={() => setEditing(false)}
        />
      ) : (
        <StageModelsTable layout={layout.data} admin={admin} onEdit={() => setEditing(true)} />
      )}
      {admin && editing && !formReady ? <LoadingState what="серверы и каталог моделей" /> : null}
    </div>
  );
}
