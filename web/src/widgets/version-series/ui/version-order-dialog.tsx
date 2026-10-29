'use client';

/**
 * «Порядок версий» (`frontend/static/js/version-comparison.js:503-523`): the versions of the document set in the order
 * they are compared, each movable one place up or down, and a button that saves the new order as a new revision.
 *
 * The order is the reader's word; the file number, «Изм.» and the issue date are hints. Saving appends a revision against
 * the one the reader saw: if somebody saved another meanwhile the dialog says so (`comparison_version_order_stale`) and the
 * order is read again. The order does not touch the documents' own ordinal. {@link VersionOrderDialogView} is the markup.
 */

import { useState } from 'react';

import type { ComparisonVersionOrderSource } from '@/shared/api';
import type { ComparisonFailure } from '@/entities/version-series';
import { ORDER_DIALOG_TEXT, ORDER_SAVE_HINT, ORDER_SOURCE_LABELS, moveVersion, sameOrder } from '@/entities/version-series';

import { CommandRefusal } from './module-state';
import styles from './version-series.module.css';

export interface OrderRow {
  readonly versionUid: string;
  readonly name: string;
  readonly file: string;
  readonly pages: number;
}

export interface VersionOrderDialogViewProps {
  readonly heading: string;
  /** Where the order in force came from; absent while the set is compared in its own order. */
  readonly source?: ComparisonVersionOrderSource | undefined;
  readonly rows: readonly OrderRow[];
  readonly changed: boolean;
  readonly pending: boolean;
  readonly failure: ComparisonFailure | null;
  readonly onMove: (index: number, direction: -1 | 1) => void;
  readonly onSave: () => void;
  readonly onCancel: () => void;
}

export function VersionOrderDialogView({
  heading,
  source,
  rows,
  changed,
  pending,
  failure,
  onMove,
  onSave,
  onCancel,
}: VersionOrderDialogViewProps) {
  return (
    <section role="group" aria-label="Порядок версий" className={styles.dialog} data-version-order="">
      <h3 className={styles.dialogTitle}>Порядок версий · {heading}</h3>
      <p className="am-note">{ORDER_DIALOG_TEXT}</p>
      <p className="am-note" data-order-source={source ?? 'own'}>
        Порядок сейчас: {source === undefined ? 'собственный порядок документа' : ORDER_SOURCE_LABELS[source]}.
      </p>
      <div className={styles.scroller}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">№</th>
              <th scope="col">Версия</th>
              <th scope="col">Файл</th>
              <th scope="col">Страниц</th>
              <th scope="col">
                <span className={styles.visuallyHidden}>Переместить</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.versionUid}>
                <td>{index + 1}</td>
                <td>Версия {row.name}</td>
                <td className={styles.fileName}>{row.file === '' ? '—' : row.file}</td>
                <td>{row.pages}</td>
                <td>
                  <button
                    type="button"
                    className="am-button am-button--small am-button--quiet"
                    disabled={pending || index === 0}
                    aria-label={`Поднять версию ${row.name} выше`}
                    onClick={() => onMove(index, -1)}
                  >
                    ↑
                  </button>{' '}
                  <button
                    type="button"
                    className="am-button am-button--small am-button--quiet"
                    disabled={pending || index === rows.length - 1}
                    aria-label={`Опустить версию ${row.name} ниже`}
                    onClick={() => onMove(index, 1)}
                  >
                    ↓
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <CommandRefusal failure={failure} />
      <p>
        <button type="button" className="am-button am-button--quiet" disabled={pending} onClick={onCancel}>
          Отмена
        </button>{' '}
        <button type="button" className="am-button" disabled={pending || !changed} title={ORDER_SAVE_HINT} onClick={onSave}>
          {pending ? 'Сохраняем…' : 'Сохранить порядок'}
        </button>
      </p>
    </section>
  );
}

export interface VersionOrderDialogProps {
  readonly heading: string;
  readonly source?: ComparisonVersionOrderSource | undefined;
  readonly rows: readonly OrderRow[];
  readonly pending: boolean;
  readonly failure: ComparisonFailure | null;
  readonly onSave: (order: readonly string[]) => void;
  readonly onCancel: () => void;
}

export function VersionOrderDialog({ heading, source, rows, pending, failure, onSave, onCancel }: VersionOrderDialogProps) {
  const [order, setOrder] = useState<readonly string[]>(rows.map((row) => row.versionUid));
  const byUid = new Map(rows.map((row) => [row.versionUid, row] as const));
  const shown = order.flatMap((uid) => {
    const row = byUid.get(uid);
    return row === undefined ? [] : [row];
  });
  return (
    <VersionOrderDialogView
      heading={heading}
      source={source}
      rows={shown}
      changed={!sameOrder(order, rows.map((row) => row.versionUid))}
      pending={pending}
      failure={failure}
      onMove={(index, direction) => setOrder((held) => moveVersion(held, index, direction))}
      onSave={() => onSave(order)}
      onCancel={onCancel}
    />
  );
}
