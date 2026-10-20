'use client';

/**
 * «Нормативные ссылки» on the run page — the normative documents the project's text cites,
 * each checked against the norms snapshot the run pinned (`NORM-REFS-RUN-01`).
 *
 * Read-only and computed per request from the run's saved text: nothing here is a finding, and
 * nothing is written. The container owns the query and its failure; `NormReferencesAnswer`
 * owns the reading.
 */

import type { RunId } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { useRunNormReferences } from '@/entities/norm-reference';

import { NormReferencesAnswer } from './norm-references-answer';
import styles from './norm-references.module.css';

export interface NormReferencesSectionProps {
  readonly runId: RunId;
}

export function NormReferencesSection({ runId }: NormReferencesSectionProps) {
  const references = useRunNormReferences(runId);
  const failure = references.error === null ? null : failureMessage(references.error);

  return (
    <section className={styles.section} aria-labelledby="norm-references-heading" data-norm-references="">
      <div className={styles.bar}>
        <h2 id="norm-references-heading" className={styles.heading}>Нормативные ссылки</h2>
        <button type="button" className="am-button am-button--quiet" onClick={() => void references.refetch()}>
          Обновить
        </button>
      </div>
      <p className={styles.rule}>
        Ссылки на своды правил, стандарты, федеральные законы и постановления, найденные в
        сохранённом тексте прогона, сопоставлены с нормативной базой, закреплённой за прогоном. Это
        справка: она не создаёт замечаний и не меняет результат прогона.
      </p>
      {references.isPending ? <LoadingState what="нормативных ссылок" /> : null}
      {failure !== null ? (
        <ErrorState
          title="Нормативные ссылки не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void references.refetch()}
        />
      ) : null}
      {references.data !== undefined && failure === null ? <NormReferencesAnswer answer={references.data} /> : null}
    </section>
  );
}
