'use client';

/** @jsxRuntime automatic */

/**
 * `UI-A-68`: the original's table of findings, full width and dense — the number, the severity, the sheet and
 * page, the finding, the norms it cites, the recommendation and the decision — over the same findings as the
 * list. The original opens a strip under the row it is asked about; this table opens the finding there
 * (`renderExpansion`), so the expert reads the quotation on its page without leaving the row.
 *
 * Pure markup: findings and callbacks in, rows out. The shared `Table` is not used because it has no room for
 * an opened row, a verdict on the row or a column that is not text; it stays as it is for its other readers.
 *
 * The severity cell keeps the two apart (`R-151j`): the expert's decision is a badge, the model's proposal is a
 * labelled note and never the badge. The norm cell lists the citations the server certified (`norm_citations`);
 * absent means the citation gate never ran for the finding and prints a dash, not «0» (`finding-basis`).
 */

import { Fragment } from 'react';
import type { ReactNode } from 'react';

import type { Finding } from '@/shared/api';
import {
  EXECUTION_STATUS_LABELS,
  SEVERITY_LABELS,
  SeverityBadge,
  normCitationStateLabel,
  normCitationStateMeaning,
} from '@/entities/finding';
import { CATEGORY_LABELS, VerdictBadge } from '@/entities/expert-decision';
import { declaredPages } from '@/entities/finding-observation';
import { clauseLabel } from '@/entities/norms';

import { pagesParts, verdictBucket } from '../model/presentation';
import styles from './finding-table.module.css';

export interface FindingTableProps {
  readonly findings: readonly Finding[];
  /** The number each finding carries over the whole run (`findingNumbers`). */
  readonly numberOf: ReadonlyMap<string, number>;
  readonly selectedFindingUid: string | null;
  readonly onSelect: (findingUid: string) => void;
  /** `R-151n`: ✓/✕ in the «Решение» cell, for a session that may decide. */
  readonly renderRowActions?: ((finding: Finding) => ReactNode) | undefined;
  /** What opens under the selected row: the finding itself. Absent, the table opens nothing. */
  readonly renderExpansion?: ((finding: Finding) => ReactNode) | undefined;
  readonly sheetOf?: ((page: number) => number | undefined) | undefined;
}

const COLUMNS = ['№', 'Важность', 'Лист / стр.', 'Замечание', 'Норма', 'Рекомендация', 'Решение'] as const;

function SeverityCell({ finding }: { readonly finding: Finding }) {
  if (finding.decided_severity !== undefined) {
    return <SeverityBadge severity={finding.decided_severity} title="Важность, решённая экспертом" />;
  }
  const proposed = finding.observation.proposed_severity;
  if (proposed === undefined) return <span className={styles.none}>—</span>;
  return (
    <span className={styles.proposal} data-proposed-severity={proposed} title="Предложение модели, не решение эксперта">
      предложено: {SEVERITY_LABELS[proposed]}
    </span>
  );
}

function NormCell({ finding }: { readonly finding: Finding }) {
  const citations = finding.observation.norm_citations ?? finding.norm_citations;
  if (citations === undefined) return <span className={styles.none}>—</span>;
  if (citations.length === 0) return <span className={styles.none}>ссылок нет</span>;
  return (
    <ul className={styles.norms}>
      {citations.map((citation) => {
        const clause = clauseLabel(citation.clause_number);
        return (
          <li key={citation.norm_paragraph_id} className={styles.norm} data-norm-citation-state={citation.state}>
            <span className={styles.normHead}>
              <strong>{citation.designation}</strong>
              {clause === null ? null : <span>{clause}</span>}
              <span className={styles.normState} title={normCitationStateMeaning(citation.state)}>
                {normCitationStateLabel(citation.state)}
              </span>
            </span>
            <span className={styles.quote}>«{citation.quote}»</span>
          </li>
        );
      })}
    </ul>
  );
}

export function FindingTable({
  findings,
  numberOf,
  selectedFindingUid,
  onSelect,
  renderRowActions,
  renderExpansion,
  sheetOf,
}: FindingTableProps) {
  return (
    <div className={styles.scroll} data-finding-table="">
      <table className={styles.table} aria-label="Находки прогона">
        <colgroup>
          <col className={styles.colNumber} />
          <col className={styles.colSeverity} />
          <col className={styles.colPages} />
          <col className={styles.colText} />
          <col className={styles.colNorms} />
          <col className={styles.colRecommendation} />
          <col className={styles.colDecision} />
        </colgroup>
        <thead>
          <tr>
            {COLUMNS.map((column) => (
              <th key={column} scope="col" className={styles.head}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {findings.map((finding) => {
            const selected = finding.finding_uid === selectedFindingUid;
            const pages = pagesParts(declaredPages(finding.observation), sheetOf);
            const merged = finding.merged_observations?.length ?? 0;
            const expansion = selected && renderExpansion !== undefined ? renderExpansion(finding) : null;
            return (
              <Fragment key={finding.finding_uid}>
                <tr
                  className={styles.row}
                  aria-current={selected ? 'true' : undefined}
                  data-row-key={finding.finding_uid}
                  data-verdict-bucket={verdictBucket(finding.current_verdict)}
                >
                  <td className={styles.number}>
                    <button
                      type="button"
                      className="am-button am-button--quiet am-button--small"
                      data-finding-uid={finding.finding_uid}
                      aria-expanded={renderExpansion === undefined ? undefined : selected}
                      onClick={() => {
                        onSelect(finding.finding_uid);
                      }}
                    >
                      {numberOf.get(finding.finding_uid)}
                    </button>
                    {merged > 1 ? (
                      <span className={styles.merged} title={`Объединённых наблюдений: ${merged}`} data-merged-observations={merged}>
                        ×{merged}
                      </span>
                    ) : null}
                  </td>
                  <td className={styles.severity}>
                    <SeverityCell finding={finding} />
                  </td>
                  <td className={styles.pages}>
                    {pages.sheet === null ? null : <span className={styles.sheet}>{pages.sheet}</span>}
                    <span className={styles.page}>{pages.pages}</span>
                  </td>
                  <td className={styles.text}>
                    {finding.observation.finding_text}
                    <span className={styles.category}>{CATEGORY_LABELS[finding.observation.category]}</span>
                    {finding.execution_status === undefined ? null : (
                      <span className={styles.execution} data-execution-status={finding.execution_status}>
                        {EXECUTION_STATUS_LABELS[finding.execution_status]}
                      </span>
                    )}
                  </td>
                  <td className={styles.normCell}>
                    <NormCell finding={finding} />
                  </td>
                  <td className={styles.recommendation}>{finding.observation.recommendation_text}</td>
                  <td>
                    <div className={styles.decision}>
                      <VerdictBadge verdict={finding.current_verdict} />
                      {renderRowActions === undefined ? null : renderRowActions(finding)}
                    </div>
                  </td>
                </tr>
                {expansion === null ? null : (
                  <tr className={styles.expansion} data-finding-expansion={finding.finding_uid}>
                    <td colSpan={COLUMNS.length}>{expansion}</td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
