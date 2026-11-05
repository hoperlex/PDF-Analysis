'use client';

/**
 * «Загрузить решения из Excel» beside «Скачать Excel» on «Разбор» (`R-151d`, `importRunDecisions`).
 *
 * The original pdf-proverka loads «Решение эксперта» and «Причина отклонения» back from its own report by
 * the finding's ID. Ours takes the workbook «Скачать Excel» produced, edited in «Решение эксперта»
 * (принято / отклонено) and «Комментарий», and the server matches each row by «ID замечания», never by
 * «№». The answer is a line of counts and, under it, each refused row with its reason, so the expert
 * finds the row in the file. A foreign file is refused whole and nothing is recorded.
 */

import { useState } from 'react';

import type { DecisionImportRefusal, DecisionImportReport, RunId } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';

import { useImportDecisions } from '../model/use-import-decisions';
import styles from './import-decisions.module.css';

/** The largest workbook the server reads, 10 MiB. */
export const DECISION_IMPORT_MAX_BYTES = 10 * 1024 * 1024;

const ACCEPT = '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

/** Why a row was refused, as the expert reads it beside the row number. */
export const IMPORT_REFUSAL_LABELS: Readonly<Record<DecisionImportRefusal, string>> = {
  no_finding_uid: 'решение без «ID замечания»',
  duplicate_finding: 'замечание уже встречалось выше',
  unknown_finding: 'нет такого замечания',
  finding_not_in_run: 'замечание другого запуска',
  unknown_decision: 'решение не из списка: принято, отклонено',
  not_importable: 'решение не отзывается через Excel',
};

/** The file refusals the server names by `constraint`, in words. */
const FILE_REFUSALS: Readonly<Record<string, string>> = {
  not_our_export: 'Это не наша выгрузка: нужен лист «Замечания» с колонкой «ID замечания». Скачайте Excel заново.',
  unreadable: 'Файл не читается как книга Excel (.xlsx).',
  too_large: 'Файл больше 10 MiB.',
  too_many_rows: 'В листе больше 20 000 строк.',
};

/** What the control says when the whole file was refused or the request failed. */
export function importFailure(error: unknown): string {
  if (error instanceof ApiError && error.errorCode === 'validation_failed') {
    const constraint = error.details.constraint;
    if (typeof constraint === 'string' && FILE_REFUSALS[constraint] !== undefined) return FILE_REFUSALS[constraint];
  }
  return failureMessage(error).detail;
}

export interface ImportDecisionsViewProps {
  readonly pending: boolean;
  readonly report: DecisionImportReport | null;
  readonly failure: string | null;
  readonly onChoose: (file: File) => void;
}

/** The control from state already in hand; rendered by the static harness in every branch. */
export function ImportDecisionsView({ pending, report, failure, onChoose }: ImportDecisionsViewProps) {
  const refused = report?.rows.filter((row) => row.outcome === 'refused') ?? [];
  return (
    <div className={styles.control} data-decision-import="">
      <label className={`am-button am-button--quiet ${styles.pick}`} aria-disabled={pending}>
        <input
          type="file"
          accept={ACCEPT}
          className={styles.input}
          disabled={pending}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = '';
            if (file !== undefined) onChoose(file);
          }}
        />
        {pending ? 'Загружаю решения…' : 'Загрузить решения из Excel'}
      </label>
      {report !== null ? (
        <p className={styles.counts} data-import-recorded={report.recorded}>
          Записано {report.recorded} · без изменений {report.unchanged} · отклонено {report.refused}
        </p>
      ) : null}
      {refused.length > 0 ? (
        <ul className={styles.refused}>
          {refused.map((row) => (
            <li key={row.row} data-import-row={row.row}>
              Строка {row.row}: {row.reason !== undefined ? IMPORT_REFUSAL_LABELS[row.reason] : 'отклонена'}
            </li>
          ))}
        </ul>
      ) : null}
      {failure !== null ? <p className={styles.error} role="alert">{failure}</p> : null}
    </div>
  );
}

/** The connected control: checks the size before sending, then shows the server's report. */
export function ImportDecisions({ runId }: { readonly runId: RunId }) {
  const importer = useImportDecisions({ runId });
  const [precheck, setPrecheck] = useState<string | null>(null);
  return (
    <ImportDecisionsView
      pending={importer.isPending}
      report={importer.data ?? null}
      failure={precheck ?? (importer.error !== null ? importFailure(importer.error) : null)}
      onChoose={(file) => {
        if (file.size === 0 || file.size > DECISION_IMPORT_MAX_BYTES) {
          setPrecheck(file.size === 0 ? 'Файл пуст.' : FILE_REFUSALS.too_large ?? null);
          return;
        }
        setPrecheck(null);
        importer.mutate({ file });
      }}
    />
  );
}
