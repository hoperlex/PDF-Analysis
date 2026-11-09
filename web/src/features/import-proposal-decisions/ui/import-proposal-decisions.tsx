'use client';

/**
 * «Загрузить решения» beside the proposals' exports on the document's «Оптимизация» tab (`UI-B-15`,
 * `importOptimisationProposalDecisions`).
 *
 * The original pdf-proverka loads the expert's decisions back from its own table. Ours takes the workbook
 * «Выгрузить таблицу решений» produced, edited in «Решение эксперта» (принято / отклонено / на доработку / не решено) and
 * «Комментарий», and the server matches each row by «ID предложения», never by «№». «не решено» over a decision in force
 * withdraws it. The answer is a line of counts and, under it, each refused row with its reason, so the expert finds the row
 * in the file. A foreign file is refused whole and nothing is recorded.
 */

import { useState } from 'react';

import type { OptimisationPassId, ProposalDecisionImportRefusal, ProposalDecisionImportReport } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';

import { useImportProposalDecisions } from '../model/use-import-proposal-decisions';
import styles from './import-proposal-decisions.module.css';

/** The largest workbook the server reads, 10 MiB. */
export const PROPOSAL_IMPORT_MAX_BYTES = 10 * 1024 * 1024;

const ACCEPT = '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

/** Why a row was refused, as the expert reads it beside the row number. */
export const PROPOSAL_IMPORT_REFUSAL_LABELS: Readonly<Record<ProposalDecisionImportRefusal, string>> = {
  no_proposal_id: 'решение без идентификатора предложения',
  duplicate_proposal: 'предложение уже встречалось выше',
  unknown_proposal: 'нет такого предложения в этом проходе',
  unknown_decision: 'решение не из списка: принято, отклонено, на доработку, не решено',
  comment_required: 'для «на доработку» нужен комментарий',
  comment_too_long: 'комментарий длиннее 2000 знаков',
};

const TOO_LARGE = 'Файл больше 10 MiB.';
const EMPTY = 'Файл пуст.';

/** The file refusals the server names by `constraint`, in words. */
const FILE_REFUSALS: Readonly<Record<string, string>> = {
  not_our_export:
    'Это не наша выгрузка: нужен лист «Предложения» с колонкой идентификаторов предложений. Выгрузите таблицу решений заново.',
  unreadable: 'Файл не читается как книга Excel (.xlsx).',
  too_large: TOO_LARGE,
  too_many_rows: 'В листе больше 20 000 строк.',
};

/** What the control says when the whole file was refused or the request failed. */
export function importProposalFailure(error: unknown): string {
  if (error instanceof ApiError && error.errorCode === 'validation_failed') {
    const constraint = error.details.constraint;
    if (typeof constraint === 'string' && FILE_REFUSALS[constraint] !== undefined) return FILE_REFUSALS[constraint];
  }
  return failureMessage(error).detail;
}

export interface ImportProposalDecisionsViewProps {
  readonly pending: boolean;
  readonly report: ProposalDecisionImportReport | null;
  readonly failure: string | null;
  readonly onChoose: (file: File) => void;
}

/** The control from state already in hand; rendered by the static harness in every branch. */
export function ImportProposalDecisionsView({ pending, report, failure, onChoose }: ImportProposalDecisionsViewProps) {
  const refused = report?.rows.filter((row) => row.outcome === 'refused') ?? [];
  return (
    <div className={styles.control} data-proposal-decision-import="">
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
        {pending ? 'Загружаю решения…' : 'Загрузить решения'}
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
              Строка {row.row}: {row.reason !== undefined ? PROPOSAL_IMPORT_REFUSAL_LABELS[row.reason] : 'отклонена'}
            </li>
          ))}
        </ul>
      ) : null}
      {failure !== null ? (
        <p className={styles.error} role="alert">
          {failure}
        </p>
      ) : null}
    </div>
  );
}

/** The connected control: checks the size before sending, then shows the server's report. */
export function ImportProposalDecisions({ passId }: { readonly passId: OptimisationPassId }) {
  const importer = useImportProposalDecisions({ passId });
  const [precheck, setPrecheck] = useState<string | null>(null);
  return (
    <ImportProposalDecisionsView
      pending={importer.isPending}
      report={importer.data ?? null}
      failure={precheck ?? (importer.error !== null ? importProposalFailure(importer.error) : null)}
      onChoose={(file) => {
        if (file.size === 0 || file.size > PROPOSAL_IMPORT_MAX_BYTES) {
          setPrecheck(file.size === 0 ? EMPTY : TOO_LARGE);
          return;
        }
        setPrecheck(null);
        importer.mutate({ file });
      }}
    />
  );
}
