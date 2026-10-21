'use client';

/** @jsxRuntime automatic */

/**
 * What a v2 finding rests on, beside the quotation it was verified at (`REVIEW-V2-UI-01`):
 * the normative requirement and the value the document states, the norm citations, and the
 * observations that were merged into the finding.
 *
 * Everything here is read from the API as served and shown as served:
 *
 *   - `required_value` and `stated_value` are printed whole, with no trim or rewrite; they
 *     are absent on a legacy or a nonnormative finding, and an absent one prints nothing
 *     (no dash, no «нет данных»).
 *   - `norm_citations` has three states and this component keeps all three apart. Absent
 *     means the citation gate never certified this observation (v1/v2): nothing is shown,
 *     and in particular not «0». An empty array means the gate ran and persisted a checked
 *     count of zero: that is said in one sentence. A non-empty array is listed, each with
 *     its designation, clause, page, quotation, text source and a link to the norm at that
 *     page.
 *   - `merged_observations` lists every observation the server sent, the canonical one
 *     marked as such rather than dropped, each with the model's proposed severity as the
 *     MODEL's («предложение модели»).
 *
 * A finding with none of these renders nothing at all, so the viewer is byte-for-byte the
 * viewer it was for a finding that has never carried them.
 */

import Link from 'next/link';

import type { FindingObservation, NormCitation } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  SeverityBadge,
  normCitationStateLabel,
  normCitationStateMeaning,
} from '@/entities/finding';
import { declaredPages, orderedEvidence } from '@/entities/finding-observation';
import { attributionLabel, clauseLabel } from '@/entities/norms';

import styles from './finding-basis.module.css';

export interface FindingBasisProps {
  /** The canonical observation: the one a decision is recorded against. */
  readonly observation: FindingObservation;
  /** `FindingDetail.merged_observations`, when the server sent it. */
  readonly mergedObservations?: readonly FindingObservation[] | undefined;
}

function pagesLabel(pages: readonly number[]): string {
  return pages.length === 1 ? `стр. ${pages[0]}` : `стр. ${pages.join(', ')}`;
}

function Values({ observation }: { readonly observation: FindingObservation }) {
  const required = observation.required_value;
  const stated = observation.stated_value;
  if (required === undefined && stated === undefined) return null;
  return (
    <section className={styles.block} data-finding-values="">
      <h3 className={styles.heading}>Требование и значение в документе</h3>
      <dl>
        {required === undefined ? null : (
          <>
            <dt>Требуется по норме</dt>
            <dd data-required-value="">{required}</dd>
          </>
        )}
        {stated === undefined ? null : (
          <>
            <dt>Указано в документе</dt>
            <dd data-stated-value="">{stated}</dd>
          </>
        )}
      </dl>
    </section>
  );
}

function Citation({ citation }: { readonly citation: NormCitation }) {
  const clause = clauseLabel(citation.clause_number);
  const meaning = normCitationStateMeaning(citation.state);
  return (
    <li
      className={styles.item}
      data-norm-citation={citation.norm_paragraph_id}
      data-norm-citation-state={citation.state}
    >
      <p className={styles.head}>
        <strong>{citation.designation}</strong>
        {citation.title === '' ? null : <span>{citation.title}</span>}
        {clause === null ? null : <span>{clause}</span>}
        <span>стр. {citation.page_label}</span>
        <span
          className={`am-badge ${citation.state === 'verified' ? 'am-badge--ok' : 'am-badge--active'}`}
          {...(meaning === undefined ? {} : { title: meaning })}
        >
          <span className="am-badge__label">{normCitationStateLabel(citation.state)}</span>
        </span>
      </p>
      <blockquote className={`am-note ${styles.quote}`} data-norm-citation-quote={citation.quote}>
        {citation.quote}
      </blockquote>
      <p className={styles.meta}>
        {attributionLabel(citation.source_attribution)}{' '}
        <Link
          href={routes.normDocument(citation.norm_document_id, citation.page_label)}
          data-open-norm={citation.norm_document_id}
        >
          Открыть норму
        </Link>
      </p>
    </li>
  );
}

function Citations({ observation }: { readonly observation: FindingObservation }) {
  const citations = observation.norm_citations;
  if (citations === undefined) return null;
  return (
    <section className={styles.block} data-norm-citations={citations.length}>
      <h3 className={styles.heading}>Нормативные ссылки</h3>
      {citations.length === 0 ? (
        <p className="am-note">
          Проверка нормативных ссылок выполнена: подтверждённых ссылок у этой находки нет.
        </p>
      ) : (
        <ol className={styles.list}>
          {citations.map((citation) => (
            <Citation key={citation.norm_paragraph_id} citation={citation} />
          ))}
        </ol>
      )}
    </section>
  );
}

function Merged({
  canonical,
  observations,
}: {
  readonly canonical: FindingObservation;
  readonly observations: readonly FindingObservation[];
}) {
  if (observations.length === 0) return null;
  return (
    <section className={styles.block} data-merged-observations={observations.length}>
      <h3 className={styles.heading}>Объединённые наблюдения: {observations.length}</h3>
      <p className="am-note">
        В эту находку слиты несколько наблюдений. Они показаны так, как их прислал сервер;
        решение записывается по основному наблюдению.
      </p>
      <ul className={styles.list}>
        {observations.map((item) => {
          const pages = declaredPages(item);
          return (
            <li
              key={item.finding_observation_id}
              className={styles.item}
              data-merged-observation={item.finding_observation_id}
            >
              <p className={styles.head}>
                <span>{item.finding_text}</span>
                {item.finding_observation_id === canonical.finding_observation_id ? (
                  <span className="am-badge am-badge--inert">
                    <span className="am-badge__label">основное</span>
                  </span>
                ) : null}
              </p>
              {item.proposed_severity === undefined ? null : (
                <p className={styles.meta} data-proposed-severity={item.proposed_severity}>
                  Предложение модели:{' '}
                  <SeverityBadge
                    severity={item.proposed_severity}
                    title="Важность, предложенная моделью"
                  />
                </p>
              )}
              {pages.length === 0 ? null : <p className={styles.meta}>{pagesLabel(pages)}</p>}
              <ul className={styles.quotes}>
                {orderedEvidence(item).map((evidence) => (
                  <li key={evidence.evidence_ordinal}>
                    <blockquote className={`am-note ${styles.quote}`} data-merged-quote={evidence.quote}>
                      {evidence.quote}
                    </blockquote>
                    <p className={styles.meta}>стр. {evidence.page_number}</p>
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function FindingBasis({ observation, mergedObservations }: FindingBasisProps) {
  const merged = mergedObservations ?? [];
  const hasValues =
    observation.required_value !== undefined || observation.stated_value !== undefined;
  if (!hasValues && observation.norm_citations === undefined && merged.length === 0) {
    return null;
  }
  return (
    <div className={styles.basis} data-finding-basis="">
      <Values observation={observation} />
      <Citations observation={observation} />
      <Merged canonical={observation} observations={merged} />
    </div>
  );
}
