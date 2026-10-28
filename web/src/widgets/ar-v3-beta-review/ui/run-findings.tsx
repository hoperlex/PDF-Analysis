'use client';

/**
 * The published findings of one AR v3 beta Run, each with the verdict controls (`R-146as`).
 *
 * A finding is a proposal that passed both gates (every PDF quote resolves; the norm quote, label
 * and values hold) and cites only provisional topics. It is `pending` until an expert records a
 * verdict with `appendDecision`; the model's sentences are shown as the model's and are never a
 * decision. The server serves no claimed number for this profile, so none is shown, and nothing
 * here computes a verdict, a severity or a compliance flag. A proposal that was withheld or
 * rejected is not a finding and has no control.
 */

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { useMe } from '@/entities/account';
import { VerdictBadge } from '@/entities/expert-decision';
import {
  SEVERITY_LABELS, SeverityBadge, admitFindings, normCitationStateLabel,
} from '@/entities/finding';
import { commentRefusalMessage, useAppendComment } from '@/features/append-comment';
import { useRecordVerdict, verdictRefusalMessage } from '@/features/record-verdict';
import type { Finding, RunId, Severity } from '@/shared/api';
import { SEVERITY_VALUES, failureMessage, listRunFindings, queryKeys } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';

import { mayRecordVerdict } from '../model/may-decide';

import styles from './ar-v3-beta-review.module.css';

function isSeverity(value: string): value is Severity {
  return (SEVERITY_VALUES as readonly string[]).includes(value);
}

function FindingCard({
  finding, runId, mayDecide,
}: { readonly finding: Finding; readonly runId: RunId; readonly mayDecide: boolean }) {
  const verdict = useRecordVerdict({ findingUid: finding.finding_uid, runId });
  const comment = useAppendComment({ findingUid: finding.finding_uid, runId });
  const [chosen, setChosen] = useState<Severity | null>(null);
  const [draft, setDraft] = useState('');
  const observation = finding.observation;
  const proposed = observation.proposed_severity;
  const busy = verdict.isPending || comment.isPending;
  const citations = observation.norm_citations ?? [];
  const failure = verdict.error !== null && verdict.error !== undefined
    ? failureMessage(verdict.error)
    : comment.error !== null && comment.error !== undefined ? failureMessage(comment.error) : null;

  return (
    <li className={styles.finding} data-ar-v3-finding data-verdict={finding.current_verdict}>
      <p>
        <VerdictBadge verdict={finding.current_verdict} />
        {finding.decided_severity === undefined ? null : (
          <> Важность, решённая экспертом: <SeverityBadge severity={finding.decided_severity} /></>
        )}
      </p>
      {observation.evidence.map((item) => (
        <div key={item.evidence_ordinal}>
          <p>Проектный документ, страница {item.page_number}:</p>
          <blockquote className={styles.quote}>{item.quote}</blockquote>
        </div>
      ))}
      {citations.map((citation, index) => (
        <div key={`${citation.norm_paragraph_id}-${index}`} data-ar-v3-finding-norm>
          <p>
            Норма: {citation.designation}, {citation.title}
            {citation.clause_number === null ? null : <>, пункт {citation.clause_number}</>}
            {' '}(страница {citation.page_label}; ссылка {normCitationStateLabel(citation.state)}):
          </p>
          <blockquote className={styles.quote}>{citation.quote}</blockquote>
        </div>
      ))}
      <p><strong>Формулировка модели, не решение эксперта.</strong></p>
      <p>{observation.finding_text}</p>
      <p>{observation.recommendation_text}</p>
      {proposed === undefined ? null : (
        <p data-proposed-severity={proposed}>
          Предложение модели о важности: <SeverityBadge severity={proposed} />
        </p>
      )}
      {!mayDecide ? <p>Решение записывает эксперт.</p> : (
        <div data-ar-v3-verdict-controls>
          {proposed === undefined ? null : (
            <label>Важность при принятии
              <select
                value={chosen ?? ''} disabled={busy}
                onChange={(event) => {
                  const next = event.target.value;
                  setChosen(isSeverity(next) ? next : null);
                  if (isSeverity(next)) verdict.clearRefusal();
                }}
              >
                <option value="">Выберите важность</option>
                {SEVERITY_VALUES.map((value) => (
                  <option key={value} value={value}>{SEVERITY_LABELS[value]}</option>
                ))}
              </select>
            </label>
          )}
          {verdict.refusal === null ? null : (
            <p role="alert" data-severity-refusal={verdict.refusal}>{verdictRefusalMessage(verdict.refusal)}</p>
          )}
          <div className={styles.verdicts}>
            <button
              type="button" className="am-button" data-intent="accept" disabled={busy}
              onClick={() => {
                verdict.record('accept', observation.finding_observation_id, {
                  proposed, decided: chosen ?? undefined,
                });
              }}
            >{verdict.pendingIntent === 'accept' ? 'Принимаю…' : 'Принять'}</button>
            <button
              type="button" className="am-button" data-intent="reject" disabled={busy}
              onClick={() => {
                verdict.record('reject', observation.finding_observation_id, { proposed });
              }}
            >{verdict.pendingIntent === 'reject' ? 'Отклоняю…' : 'Отклонить'}</button>
          </div>
          <label>Комментарий
            <textarea
              value={draft} rows={2} disabled={busy}
              onChange={(event) => { setDraft(event.target.value); }}
            />
          </label>
          {comment.refusal === null ? null : (
            <p role="alert" data-comment-refusal={comment.refusal}>{commentRefusalMessage(comment.refusal)}</p>
          )}
          <button
            type="button" className="am-button" data-intent="comment" disabled={busy}
            onClick={() => { comment.append(draft, observation.finding_observation_id); }}
          >{comment.isPending ? 'Добавляю…' : 'Добавить комментарий'}</button>
        </div>
      )}
      {failure === null ? null : (
        <ErrorState title="Решение не записано" detail={failure.detail} correlationId={failure.correlationId} />
      )}
    </li>
  );
}

export function RunFindings({ runId }: { readonly runId: RunId }) {
  const me = useMe();
  const query = useQuery({
    queryKey: queryKeys.runs.findings(runId),
    queryFn: ({ signal }) => listRunFindings({ path: { run_id: runId } }, { signal }),
  });
  const mayDecide = me.data !== undefined && mayRecordVerdict(me.data.roles);

  return (
    <section data-ar-v3-run-findings={runId} aria-label="Находки прогона">
      <h3>Находки и решения эксперта</h3>
      {query.isPending ? <LoadingState what="находок прогона" /> : null}
      {query.error !== null ? (
        <ErrorState
          title="Находки не прочитаны" detail={failureMessage(query.error).detail}
          correlationId={failureMessage(query.error).correlationId}
          onRetry={() => void query.refetch()}
        />
      ) : null}
      {query.data === undefined ? null : (() => {
        const admitted = admitFindings(query.data.data.items);
        return (
          <>
            {admitted.findings.length === 0 && admitted.integrityFaults.length === 0
              ? <p>Опубликованных находок нет.</p> : null}
            {admitted.integrityFaults.length > 0
              ? <p role="alert">Находок, не прошедших проверку отображения: {admitted.integrityFaults.length}.</p> : null}
            <ol className={styles.findings}>
              {admitted.findings.map((finding) => (
                <FindingCard key={finding.finding_uid} finding={finding} runId={runId} mayDecide={mayDecide} />
              ))}
            </ol>
          </>
        );
      })()}
    </section>
  );
}
