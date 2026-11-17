/**
 * The table of «Модели по этапам» (`HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §7.4): which model, and with what effort, does the work of
 * each of the six rows of an analysis. One table for both places that show it: the tab «Модели по этапам» of the screen «Диспетчер»
 * and the window «Модели по этапам» of a start (`UIP-S15-02`, the entity is where the two slices meet, so neither imports the other).
 *
 * An expert reads a table of six rows, «строка — модель · усилие», and **has no control**. A row whose model no enabled server
 * can answer now carries «⚠ нет на серверах»; a row that is fine carries nothing. An administrator is also drawn «Изменить»,
 * which the caller wires to the form of `features/manage-stage-layout` (an entity does not import a feature).
 *
 * **«Сравнение версий»** (`CMP-WEB-01`) is one folded line under the table, holding a line for each of the four kinds of the comparison of
 * versions; it is the only thing the table gains. A revision with no model for the comparison (a «Свой набор» saved without them) has no
 * line to fold: it says in one sentence that the comparison will not run, because that is a problem and the normal is not shown.
 *
 * While the layout is switched off, the table says so in a line: runs follow the routes as before, and the administrator can
 * still prepare a revision, since the switch cannot be turned on without a saved one.
 */

import type { StageModelLayout } from '@/shared/api';
import { EmptyState, Table } from '@/shared/ui';

import { comparisonTable } from '../model/comparison';
import { layoutTable } from '../model/table';
import type { TableRow } from '../model/table';
import {
  COMPARISON_GROUP_TITLE,
  COMPARISON_NONE_NOTE,
  EDIT_LABEL,
  LAYOUT_OFF_NOTE,
  LAYOUT_ON_NOTE,
  NOT_ON_SERVERS,
  NOT_ON_SERVERS_HINT,
  NO_LAYOUT,
  NO_LAYOUT_ADMIN,
  STAGE_ROW_LABELS,
} from '../model/vocabulary';

import styles from './stage-models-table.module.css';

export interface StageModelsTableProps {
  readonly layout: StageModelLayout;
  /** An administrator: drawn «Изменить». */
  readonly admin: boolean;
  readonly onEdit?: (() => void) | undefined;
}

/** «Сравнение версий ▸»: one folded line with a line for each kind; or the sentence that none will run. Nothing before a revision exists. */
function ComparisonLines({ layout }: { readonly layout: StageModelLayout }) {
  if (layout.current === undefined) return null;
  const readings = comparisonTable(layout);
  if (readings.length === 0) return <p className={styles.note} data-layout-comparison-none>{COMPARISON_NONE_NOTE}</p>;
  return (
    <details className={styles.fold} data-layout-comparison-group>
      <summary>{COMPARISON_GROUP_TITLE}</summary>
      <ul className={styles.cells}>
        {readings.map((reading) => (
          <li key={reading.kind} className={styles.cell} data-comparison-kind={reading.kind} data-model-effort={reading.effort}>
            {`${reading.label}: ${reading.text}`}
            {reading.unavailable ? (
              <span className={styles.missing} title={NOT_ON_SERVERS_HINT} data-host-reason="not_on_any_server">{NOT_ON_SERVERS}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </details>
  );
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
      <ComparisonLines layout={layout} />
      {admin && onEdit !== undefined ? (
        <p className={styles.actions}>
          <button className="am-button" type="button" data-layout-edit onClick={onEdit}>{EDIT_LABEL}</button>
        </p>
      ) : null}
    </>
  );
}
