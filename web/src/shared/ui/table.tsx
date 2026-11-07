/**
 * `R-150f`, `UI-PARITY-01` §1c п.3: the shared table, in its minimal version for its first consumer — the
 * findings table of «Разбор» (`UI-A-68`). A native `<table>` with `scope="col"` headers and an optional
 * caption. Selection, sorting and a sticky head are not here: they arrive when a row of the register needs
 * them, under the same owner of this interface.
 */

import type { ReactNode } from 'react';

import styles from './table.module.css';

export interface TableColumn<Row> {
  readonly key: string;
  readonly header: string;
  readonly cell: (row: Row) => ReactNode;
}

export interface TableProps<Row> {
  readonly columns: readonly TableColumn<Row>[];
  readonly rows: readonly Row[];
  readonly rowKey: (row: Row) => string;
  readonly caption?: string | undefined;
  /** Marks one row as the current one (`aria-current`), e.g. the selected finding. */
  readonly currentKey?: string | null | undefined;
}

export function Table<Row>({ columns, rows, rowKey, caption, currentKey }: TableProps<Row>) {
  return (
    <div className={styles.scroll} role="region" aria-label={caption ?? 'Таблица'} tabIndex={0}>
      <table className={styles.table}>
        {caption === undefined ? null : <caption className={styles.caption}>{caption}</caption>}
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={styles.head}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const key = rowKey(row);
            return (
              <tr key={key} className={styles.row} aria-current={key === currentKey ? 'true' : undefined} data-row-key={key}>
                {columns.map((column) => (
                  <td key={column.key} className={styles.cell}>
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
