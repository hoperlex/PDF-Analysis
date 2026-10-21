/**
 * One answer of `getRunNormReferences`, rendered (`NORM-REFS-RUN-01`). Pure: the container
 * (`norm-references-section.tsx`) owns the query, this owns the reading.
 *
 * **A state is said, never shown as an empty list.** A run that pinned no snapshot, has no saved
 * text layer or cites more designations than one answer carries is one sentence saying what is
 * missing and what to do about it.
 *
 * **Five outcomes, one word each, and no severity.** The list is information: a newer edition in
 * the corpus is not a finding, and an earlier-only edition is explained rather than judged. A
 * citation on a page with no text layer cannot be found, so those pages are named. The corpus
 * documents whose designation the parser cannot read are listed as «не распознано» — a document
 * that can never be matched is something the expert should see, not infer.
 */

import Link from 'next/link';

import type { NormReferenceItem, NormReferenceUnrecognised, RunNormReferences } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  NORM_REFERENCE_OUTCOME_ORDER,
  citationPlaces,
  normReferenceOutcomeLabel,
  normReferenceOutcomeMeaning,
  normReferenceStateMessage,
  pageList,
} from '@/entities/norm-reference';

import styles from './norm-references.module.css';

export interface NormReferencesAnswerProps {
  readonly answer: RunNormReferences;
}

const OUTCOME_TONES: Readonly<Record<string, string>> = {
  in_corpus: 'am-badge--ok',
  newer_edition: 'am-badge--degraded',
  older_edition_only: 'am-badge--degraded',
  not_in_corpus: 'am-badge--inert',
  not_recognised: 'am-badge--inert',
};

function OutcomeBadge({ outcome }: { readonly outcome: string }) {
  return (
    <span className={`am-badge ${OUTCOME_TONES[outcome] ?? 'am-badge--inert'}`}>
      {normReferenceOutcomeLabel(outcome)}
    </span>
  );
}

function OpenNorm({ documentId }: { readonly documentId: string }) {
  return (
    <Link href={routes.normDocument(documentId)} data-open-norm={documentId}>
      Открыть норму
    </Link>
  );
}

function Matched({ item }: { readonly item: NormReferenceItem }) {
  if (item.matched_norm_document_id === undefined) return <>—</>;
  return (
    <>
      {item.matched_designation ?? '—'}
      {item.matched_title === undefined ? null : (
        <span className={styles.hint}> — {item.matched_title}</span>
      )}{' '}
      <OpenNorm documentId={item.matched_norm_document_id} />
    </>
  );
}

function Row({ item }: { readonly item: NormReferenceItem }) {
  return (
    <tr data-norm-reference={item.cited} data-norm-reference-outcome={item.outcome}>
      <td className={styles.cell}>{item.cited}</td>
      <td className={styles.cell}>
        <OutcomeBadge outcome={item.outcome} />
      </td>
      <td className={styles.cell}>{citationPlaces(item.anchors, item.occurrence_count)}</td>
      <td className={styles.cell}>
        <Matched item={item} />
      </td>
    </tr>
  );
}

function Unrecognised({ items }: { readonly items: readonly NormReferenceUnrecognised[] }) {
  if (items.length === 0) return null;
  return (
    <details className={styles.details} data-norm-unrecognised={items.length}>
      <summary>Документы корпуса с нераспознанным обозначением: {items.length}</summary>
      <p className={styles.hint}>
        Обозначение этих документов не читается разбором ссылок: проект нельзя сопоставить с ними
        автоматически, и ссылки на такие документы в тексте проекта не ищутся.
      </p>
      <ul className={styles.list}>
        {items.map((document) => (
          <li key={document.norm_document_id} data-norm-unrecognised-document={document.norm_document_id}>
            {document.designation}
            {document.title === undefined ? null : <span className={styles.hint}> — {document.title}</span>}{' '}
            <OpenNorm documentId={document.norm_document_id} />
          </li>
        ))}
      </ul>
    </details>
  );
}

function Legend() {
  return (
    <details className={styles.details} data-norm-reference-legend="">
      <summary>Как читать результат</summary>
      <dl className={styles.legend}>
        {NORM_REFERENCE_OUTCOME_ORDER.map((outcome) => (
          <div key={outcome}>
            <dt>{normReferenceOutcomeLabel(outcome)}</dt>
            <dd>{normReferenceOutcomeMeaning(outcome)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

export function NormReferencesAnswer({ answer }: NormReferencesAnswerProps) {
  if (answer.state !== 'ready') {
    return (
      <p className="am-note" data-norm-references-state={answer.state}>
        {normReferenceStateMessage(answer.state)}
      </p>
    );
  }
  const { counts, items, unread_pages: unreadPages, unrecognised } = answer;
  if (counts === undefined || items === undefined || unreadPages === undefined || unrecognised === undefined) {
    return (
      <p className="am-note" data-norm-references-state="malformed">
        Ответ сервера о готовом списке не содержит самого списка.
      </p>
    );
  }
  return (
    <div data-norm-references-state="ready">
      <ul className={styles.counts} data-norm-reference-counts="">
        {NORM_REFERENCE_OUTCOME_ORDER.map((outcome) => (
          <li key={outcome} data-norm-reference-count={outcome}>
            <OutcomeBadge outcome={outcome} /> <strong>{counts[outcome]}</strong>
          </li>
        ))}
      </ul>
      <p className={styles.hint}>
        Различных ссылок: {items.length}, упоминаний в тексте: {answer.occurrence_count ?? 0}. Нормативная
        база прогона: документов {answer.snapshot_document_count ?? 0}.
      </p>
      {unreadPages.length === 0 ? null : (
        <p className="am-note" data-norm-unread-pages={unreadPages.length}>
          Страницы без текстового слоя: {pageList(unreadPages)}. Ссылки на них не найдены.
        </p>
      )}
      {items.length === 0 ? (
        <p data-norm-references-empty="">В тексте проекта не найдено ссылок на нормативные документы.</p>
      ) : (
        <div className={styles.frame}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.cell}>Ссылка в проекте</th>
                <th className={styles.cell}>Результат</th>
                <th className={styles.cell}>Где встречается</th>
                <th className={styles.cell}>Норма в корпусе</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <Row key={`${item.cited}`} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Legend />
      <Unrecognised items={unrecognised} />
    </div>
  );
}
