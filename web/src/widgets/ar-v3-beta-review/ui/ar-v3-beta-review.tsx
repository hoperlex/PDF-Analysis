'use client';

/** A read-only, linkable view of the six verified AR v3 beta scope outcomes. */

import { useQuery } from '@tanstack/react-query';

import { looksLikeArV3GroupId, terminalReasonNote } from '@/entities/audit-run';
import type { ArV3BetaGroupReview, ArV3BetaGroupReviewMember, ArV3RunGroupId } from '@/shared/api';
import { failureMessage, getArV3BetaGroupReview, queryKeys } from '@/shared/api';
import { ErrorState, LoadingState, STATE_LABELS } from '@/shared/ui';

import { completeArV3GroupReview } from '../model/complete-group-review';

import styles from './ar-v3-beta-review.module.css';

function reviewQuery(groupId: ArV3RunGroupId) {
  return {
    queryKey: queryKeys.runs.arV3GroupReview(groupId),
    queryFn: async ({ signal }: { signal?: AbortSignal }): Promise<ArV3BetaGroupReview> =>
      (await getArV3BetaGroupReview(
        { path: { group_id: groupId } }, signal === undefined ? {} : { signal },
      )).data,
  } as const;
}

function reviewStateLabel(state: ArV3BetaGroupReviewMember['review_state']): string {
  switch (state) {
    case 'pending': return 'Ожидает результата';
    case 'failed': return 'Прогон завершился ошибкой';
    case 'verification_refused': return 'Проверка сохранённого разбора отказала';
    case 'available': return 'Предварительный разбор доступен';
  }
}

function topicModeLabel(mode: string): string {
  if (mode === 'context_only') return 'Только контекст';
  if (mode === 'provisional_citation') return 'Предварительная ссылка';
  return 'Режим источника не распознан';
}

function ScopeMember({ member }: { readonly member: ArV3BetaGroupReviewMember }) {
  const terminal = member.terminal_reason === null ? null : terminalReasonNote(member.terminal_reason);
  return (
    <li className={styles.member} data-ar-v3-review-scope={member.scope_id} data-review-state={member.review_state}>
      <details open={member.review_state !== 'pending'}>
        <summary>{member.scope_id} — {reviewStateLabel(member.review_state)}</summary>
        <p>Прогон: <code>{member.run_id}</code>. Состояние: {STATE_LABELS[member.run_state]}.</p>
        {terminal !== null ? <p>Причина остановки: <code>{member.terminal_reason}</code>. {terminal.sentence}</p> : null}
        {member.review_state === 'verification_refused' ? (
          <p>Сохранённый разбор не показан: проверка целостности отказала.
            {member.refusal_code === null ? null : <> Код: <code>{member.refusal_code}</code>.</>}
          </p>
        ) : null}
        {member.review_state === 'pending' ? <p>Ссылки появятся только после проверенного сохранения результата.</p> : null}
        {member.review_state === 'available' && member.review !== null ? (
          <div>
            <p><strong>Только предварительные ссылки.</strong> Каждая тема и цитата требует проверки эксперта. Числовой или правовой вывод здесь не утверждён.</p>
            <h3>Темы</h3>
            <ul className={styles.topics}>
              {member.review.topics.map((topic) => (
                <li key={topic.item_id} data-ar-v3-review-topic={topic.item_id}>
                  <strong>{topic.item_id}</strong> — {topicModeLabel(topic.mode)}; требует проверки эксперта.
                  {topic.source_ids.length > 0 ? <small> Источники: {topic.source_ids.join(', ')}.</small> : null}
                  {topic.reason ? <small> Основание статуса: {topic.reason}.</small> : null}
                </li>
              ))}
            </ul>
            <h3>Предварительные цитаты</h3>
            {member.review.provisional_citations.length === 0 ? <p>Предварительных цитат нет.</p> : (
              <ol className={styles.proposals}>
                {member.review.provisional_citations.map((proposal) => (
                  <li key={proposal.proposal_ordinal}>
                    <p>Предложение {proposal.proposal_ordinal + 1}; требуется проверка эксперта.</p>
                    {proposal.evidence.map((evidence, index) => (
                      <div key={`${evidence.page_number}-${index}`}>
                        <p>Проектный документ, страница {evidence.page_number}:</p>
                        <blockquote className={styles.quote}>{evidence.quote}</blockquote>
                      </div>
                    ))}
                    {proposal.citations.map((citation, index) => (
                      <div key={`${citation.item_id}-${citation.label}-${index}`}>
                        <p>{citation.item_id}, метка {citation.label}; нормативный документ <code>{citation.document_id}</code>, абзац <code>{citation.paragraph_id}</code>.</p>
                        <blockquote className={styles.quote}>{citation.raw_quote}</blockquote>
                      </div>
                    ))}
                  </li>
                ))}
              </ol>
            )}
            <p>Скрытых предложений: {member.review.withheld_proposal_count}; отклонённых: {member.review.rejected_proposal_count}.</p>
          </div>
        ) : null}
      </details>
    </li>
  );
}

export function ArV3BetaReview({ groupId }: { readonly groupId: string | null }) {
  const validGroupId = looksLikeArV3GroupId(groupId) ? groupId : null;
  const query = useQuery({
    ...reviewQuery(validGroupId ?? ''),
    enabled: validGroupId !== null,
  });
  const failure = query.error === null ? null : failureMessage(query.error);
  const review = query.data ?? null;

  return (
    <section className={styles.panel} aria-labelledby="ar-v3-group-review-title" data-ar-v3-group-review>
      <h2 id="ar-v3-group-review-title">АР v3: разбор группы прогонов</h2>
      <p>Введите идентификатор группы из ответа запуска. Здесь видны все шесть прогонов и только предварительные нормативные ссылки.</p>
      <form action="/analysis-settings" method="get" className={styles.lookup}>
        <label htmlFor="ar-v3-group-id">Идентификатор группы
          <input id="ar-v3-group-id" name="group_id" type="text"
            pattern="arg_[0-9A-HJKMNP-TV-Z]{26}" required defaultValue={groupId ?? ''}
            autoComplete="off" spellCheck={false} />
        </label>
        <button className="am-button" type="submit">Показать разбор</button>
      </form>
      {groupId !== null && validGroupId === null ? (
        <ErrorState title="Неверный идентификатор группы" detail="Укажите идентификатор группы из ответа запуска." />
      ) : null}
      {validGroupId !== null && query.isPending ? <LoadingState what="разбора группы АР v3" /> : null}
      {validGroupId !== null && failure !== null ? (
        <ErrorState title="Разбор группы не прочитан" detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={failure.retryable ? () => void query.refetch() : undefined} />
      ) : null}
      {validGroupId !== null && review !== null && failure === null ? (
        completeArV3GroupReview(review, validGroupId) ? (
          <div data-ar-v3-group-id={review.group_id}>
            <p>Группа: <code>{review.group_id}</code>. Версия документа: <code>{review.version_uid}</code>.</p>
            <ol className={styles.members}>
              {review.members.map((member) => <ScopeMember key={member.run_id} member={member} />)}
            </ol>
          </div>
        ) : (
          <ErrorState title="Разбор группы не подтверждён"
            detail="Ответ не содержит шесть согласованных прогонов. Попросите администратора проверить сохранённый результат."
            onRetry={() => void query.refetch()} />
        )
      ) : null}
    </section>
  );
}
