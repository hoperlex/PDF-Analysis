'use client';

/**
 * `/knowledge-base` — what this installation has decided, and what it decided it about.
 *
 * `R-23` makes the knowledge base required and working inside the alpha, and `R-24` gave
 * it a contract operation rather than a client-side walk over every run. This screen is
 * the reason that ruling was taken: before `listDecisions` a page like this had to fetch
 * every run, then every run's findings, then every finding's history, and could only start
 * once it already knew the identities.
 *
 * Composition only: the shell from `shared/ui`, the query from the `expert-decision`
 * entity, the list from a widget. No projection is computed here — `ADR-0012` puts the
 * knowledge-base view on the server, and a count assembled in this file would be a second
 * answer to a question the server already answers.
 *
 * The two filters are the contract's own `category` and `verdict`, and they mean what the
 * contract says they mean: the **finding's** category, and the verdict that now stands for
 * it. Neither filters the event, so a comment left on a finding that was later accepted is
 * in the `принято` page — which is right: the comment is part of how that finding came to
 * be accepted.
 */

import { useState } from 'react';

import type { ErrorStateProps } from '@/shared/ui';
import type { FindingCategory, Verdict } from '@/shared/api';
import { ApiError, ApiFailure, catalogMessage } from '@/shared/api';
import { PageShell } from '@/shared/ui';
import { useDecisionJournal } from '@/entities/expert-decision';
import { CATEGORY_LABELS, KnowledgeBase } from '@/widgets/knowledge-base';

/** `Все` is the absence of the parameter, never a value sent to the server. */
type CategoryChoice = FindingCategory | 'all';
type VerdictChoice = Verdict | 'all';

const CATEGORY_CHOICES: readonly CategoryChoice[] = [
  'all',
  'internal_contradiction',
  'explicit_placeholder',
];

/**
 * `needs_manual_review` is in the contract's closed union and has no PC-01 producer, so it
 * is deliberately not offered: a filter that can only ever return an empty page teaches a
 * reviewer that the knowledge base is empty.
 */
const VERDICT_CHOICES: readonly VerdictChoice[] = ['all', 'accepted', 'rejected', 'pending'];

const VERDICT_CHOICE_LABELS: Readonly<Record<VerdictChoice, string>> = {
  all: 'Любой вердикт',
  pending: 'Не решено',
  accepted: 'Принято',
  rejected: 'Отклонено',
  needs_manual_review: 'Нужен ручной разбор',
};

const CATEGORY_CHOICE_LABELS: Readonly<Record<CategoryChoice, string>> = {
  all: 'Любая категория',
  ...CATEGORY_LABELS,
};

/**
 * The failure, presented once.
 *
 * `classifyListingFailure` is deliberately not used and not widened. Its subject carries a
 * `parent` — `project`, `document` or `version` — because `W18-SEAL` made an unknown parent
 * a `404` that must not render as "nothing here yet". **This listing has no parent**: its
 * path addresses no identity, the contract declares no `404` on it at all, and an empty
 * journal is an empty page. Adding a fourth parent to a closed type to describe a parent
 * that does not exist would make that type describe something untrue.
 *
 * So: the catalog's own sentence for the reported code, the correlation id, and a retry
 * only where the catalog says the code is retryable — `retryable` is read from the
 * envelope, never inferred from the status.
 */
function journalFailure(error: unknown, retry: () => void): ErrorStateProps {
  if (error instanceof ApiError) {
    return {
      title: 'База знаний не открылась.',
      detail: catalogMessage(error.errorCode),
      correlationId: error.correlationId,
      ...(error.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {}),
    };
  }
  if (error instanceof ApiFailure) {
    return {
      title: 'База знаний не открылась.',
      detail: 'Сервер не ответил. Проверьте соединение и повторите запрос.',
      correlationId: error.correlationId,
      onRetry: retry,
      retryLabel: 'Повторить',
    };
  }
  return { title: 'База знаний не открылась.', onRetry: retry, retryLabel: 'Повторить' };
}

export function KnowledgeBasePage() {
  const [category, setCategory] = useState<CategoryChoice>('all');
  const [verdict, setVerdict] = useState<VerdictChoice>('all');

  const journal = useDecisionJournal({
    ...(category === 'all' ? {} : { category }),
    ...(verdict === 'all' ? {} : { verdict }),
  });

  return (
    <PageShell
      title="База знаний"
      subtitle="Все решения проверяющего по находкам, новые сверху. Это проекция над журналом решений: ничего не хранится отдельно и всё пересчитывается из событий."
    >
      <div className="am-kb__filters" role="group" aria-label="Отбор решений">
        <label className="am-kb__filter">
          <span>Категория</span>
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value as CategoryChoice)}
          >
            {CATEGORY_CHOICES.map((choice) => (
              <option key={choice} value={choice}>
                {CATEGORY_CHOICE_LABELS[choice]}
              </option>
            ))}
          </select>
        </label>
        <label className="am-kb__filter">
          <span>Вердикт</span>
          <select
            value={verdict}
            onChange={(event) => setVerdict(event.target.value as VerdictChoice)}
          >
            {VERDICT_CHOICES.map((choice) => (
              <option key={choice} value={choice}>
                {VERDICT_CHOICE_LABELS[choice]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <KnowledgeBase
        records={journal.data?.items ?? []}
        isLoading={journal.isPending}
        error={
          journal.error === null
            ? null
            : journalFailure(journal.error, () => void journal.refetch())
        }
      />
    </PageShell>
  );
}
