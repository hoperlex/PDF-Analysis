'use client';

/** @jsxRuntime automatic */

/**
 * «Прецеденты» on the card of an open finding (`PREC-WEB`, plan-v5 sections 2.5, 3.4 and 6): the label, at most two hints, the similar cases
 * with their latest comment, and «Возможные нормы» (paragraphs the run already holds, never the encoder's guess).
 *
 * It is ONE collapsed line until it is opened, so it does not crowd the card: the summary says «Прецеденты» and the label. A finding with
 * nothing to say (no label, no hint, no case, no norm) draws nothing, and a failed or denied read draws nothing: it is a reference and the
 * expert decides without it. The words of the cases and the hints are experts' own; a model's text never appears here.
 * {@link PrecedentsCardView} is the card without the query, so the unit suite and the preview draw the markup the screen draws.
 */

import type { FindingPrecedents } from '@/shared/api';
import { clauseLabel } from '@/entities/norms';
import {
  CASE_VERDICT_MARK,
  precedentCaption,
  precedentHintLine,
  shownHints,
  similarityPercent,
  useFindingPrecedents,
} from '@/entities/decision-memory';

import styles from './precedents-card.module.css';

/** How many similar cases the card lists; the server sends at most ten. */
const CASES_SHOWN = 5;

export function PrecedentsCardView({ data }: { readonly data: FindingPrecedents }) {
  const caption = data.label === undefined ? null : precedentCaption(data.label);
  const hints = shownHints(data.hints);
  const cases = data.cases.slice(0, CASES_SHOWN);
  const norms = data.possible_norms;
  if (caption === null && hints.length === 0 && cases.length === 0 && norms.length === 0) return null;
  const counts = [
    data.cases.length === 0 ? null : `похожих случаев ${data.cases.length}`,
    norms.length === 0 ? null : `возможных норм ${norms.length}`,
  ].filter((part) => part !== null);
  return (
    <details className={`am-note ${styles.card}`} data-precedents-card={data.finding_uid} data-precedent-label={data.label?.label}>
      <summary className={styles.summary}>
        <strong>Прецеденты</strong>
        {caption === null ? null : <span className={styles.caption}> · {caption}</span>}
        {counts.length === 0 ? null : <span className={styles.counts}> · {counts.join(' · ')}</span>}
      </summary>
      {hints.length === 0 ? null : (
        <ul className={styles.list} data-precedent-hints={hints.length}>
          {hints.map((hint) => (
            <li key={`${hint.code}:${hint.case_id ?? ''}`} data-precedent-hint={hint.code}>
              {precedentHintLine(hint, data.cases)}
            </li>
          ))}
        </ul>
      )}
      {cases.length === 0 ? null : (
        <section aria-label="Похожие случаи" data-precedent-cases={data.cases.length}>
          <h4 className={styles.heading}>Похожие случаи</h4>
          <ul className={styles.list}>
            {cases.map((one) => (
              <li key={one.case_id} className={styles.case} data-precedent-case={one.case_id} data-case-verdict={one.verdict}>
                <span className={styles.meta}>
                  {CASE_VERDICT_MARK[one.verdict]} · сходство {similarityPercent(one.similarity)}
                </span>
                <span className={styles.caseText}>{one.finding_text}</span>
                {one.comment === undefined || one.comment === '' ? null : <q className={styles.comment}>{one.comment}</q>}
              </li>
            ))}
          </ul>
          {data.cases.length > cases.length ? <p className={styles.more}>и ещё {data.cases.length - cases.length}</p> : null}
        </section>
      )}
      {norms.length === 0 ? null : (
        <section aria-label="Возможные нормы" data-possible-norms={norms.length}>
          <h4 className={styles.heading}>Возможные нормы</h4>
          <ul className={styles.list}>
            {norms.map((norm) => {
              const clause = clauseLabel(norm.clause_number);
              return (
                <li key={norm.norm_paragraph_id} data-possible-norm={norm.norm_paragraph_id}>
                  <strong>{norm.designation}</strong>
                  {clause === null ? null : <> · {clause}</>} · стр. {norm.page_label}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </details>
  );
}

/** The card of the open finding. `enabled` is the session's right to read the precedents; without it nothing is asked. */
export function PrecedentsCard({ findingUid, enabled }: { readonly findingUid: string; readonly enabled: boolean }) {
  const read = useFindingPrecedents(findingUid, enabled);
  return read.data === undefined ? null : <PrecedentsCardView key={findingUid} data={read.data} />;
}
