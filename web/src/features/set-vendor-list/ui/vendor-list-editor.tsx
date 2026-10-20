'use client';

/**
 * Editing one section's vendor list (`W60-PRICE-LIST-01`): rows of material or equipment
 * group, allowed vendor and note. Saving sends the whole list as a new revision; the revision
 * the editor opened from goes with it, so a list somebody changed meanwhile is refused rather
 * than overwritten. An empty list is a valid answer — «без ограничений».
 *
 * The same editor serves the expert's list for a project and the administrator's global list;
 * which one it writes is the caller's (`onSave`), and the API checks the role of each.
 */

import { useState } from 'react';

import type { VendorListEntry } from '@/shared/api';
import { ErrorState } from '@/shared/ui';
import type { FailureMessage } from '@/shared/api/failure-message';

/** The most entries one revision holds, as the API bounds it. */
export const VENDOR_LIST_MAX_ENTRIES = 500;

interface DraftRow {
  readonly material: string;
  readonly vendor: string;
  readonly note: string;
}

function draftOf(entries: readonly VendorListEntry[]): DraftRow[] {
  return entries.map((entry) => ({
    material: entry.material ?? '',
    vendor: entry.vendor,
    note: entry.note ?? '',
  }));
}

/** The rows as entries: blank material and note are absent, a row with no vendor is a problem. */
export function entriesOf(rows: readonly DraftRow[]): VendorListEntry[] {
  return rows.map((row) => ({
    material: row.material.trim() === '' ? null : row.material.trim(),
    vendor: row.vendor.trim(),
    note: row.note.trim() === '' ? null : row.note.trim(),
  }));
}

export function draftProblem(rows: readonly DraftRow[]): string | null {
  if (rows.length > VENDOR_LIST_MAX_ENTRIES) {
    return `В списке не больше ${VENDOR_LIST_MAX_ENTRIES} записей.`;
  }
  if (rows.some((row) => row.vendor.trim() === '')) return 'В каждой записи нужен поставщик.';
  return null;
}

export interface VendorListEditorProps {
  /** Shown above the rows: which list is being edited. */
  readonly title: string;
  readonly initial: readonly VendorListEntry[];
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  readonly onSave: (entries: VendorListEntry[]) => void;
  readonly onCancel: () => void;
}

export function VendorListEditor({
  title,
  initial,
  pending,
  failure,
  onSave,
  onCancel,
}: VendorListEditorProps) {
  const [rows, setRows] = useState<DraftRow[]>(() => draftOf(initial));
  const problem = draftProblem(rows);

  const change = (index: number, field: keyof DraftRow, value: string) =>
    setRows((current) =>
      current.map((row, at) => (at === index ? { ...row, [field]: value } : row)),
    );

  return (
    <form
      className="am-form"
      data-vendor-list-editor=""
      onSubmit={(event) => {
        event.preventDefault();
        if (problem === null) onSave(entriesOf(rows));
      }}
    >
      <p>
        <strong>{title}</strong>
      </p>
      {rows.length === 0 ? (
        <p className="am-note">Записей нет: список сохранится как «без ограничений».</p>
      ) : null}
      {rows.map((row, index) => (
        <div className="am-form__row" key={index}>
          <label>
            Материал или оборудование
            <input
              type="text"
              value={row.material}
              maxLength={500}
              onChange={(event) => change(index, 'material', event.target.value)}
            />
          </label>
          <label>
            Поставщик
            <input
              type="text"
              value={row.vendor}
              maxLength={500}
              onChange={(event) => change(index, 'vendor', event.target.value)}
            />
          </label>
          <label>
            Примечание
            <input
              type="text"
              value={row.note}
              maxLength={1000}
              onChange={(event) => change(index, 'note', event.target.value)}
            />
          </label>
          <button
            type="button"
            className="am-button am-button--quiet am-button--small"
            onClick={() => setRows((current) => current.filter((_, at) => at !== index))}
          >
            Удалить запись
          </button>
        </div>
      ))}
      <div>
        <button
          type="button"
          className="am-button am-button--quiet"
          onClick={() => setRows((current) => [...current, { material: '', vendor: '', note: '' }])}
        >
          Добавить запись
        </button>
      </div>
      {problem !== null ? <p className="am-form__problem">{problem}</p> : null}
      {failure !== null ? (
        <ErrorState
          title="Список не сохранён."
          detail={failure.detail}
          correlationId={failure.correlationId}
        />
      ) : null}
      <div>
        <button type="submit" className="am-button" disabled={problem !== null || pending}>
          Сохранить список
        </button>{' '}
        <button type="button" className="am-button am-button--quiet" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  );
}
