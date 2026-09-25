'use client';

/**
 * Panel 2 — findings by verdict.
 *
 * `D1`: `listDecisions` exists today, with `category` and `verdict` filters `R-24` put on
 * the contract precisely so a client never has to walk every run's findings by hand. This
 * panel reuses `useDecisionJournal` unfiltered — the exact query and cache key
 * `/knowledge-base` already fills — rather than opening a second source over the same
 * ledger.
 *
 * **What "by verdict" can and cannot mean from this operation**, `R-25`/`R-23`'s addendum
 * read together: `listDecisions` is the ledger of *recorded* events. A finding nobody has
 * ever judged carries no event and never appears in it, at any page size — so `pending`
 * here means "commented on, or reverted, and still undecided", never "untouched". This
 * panel says so rather than letting a reader assume the two are the same absence.
 *
 * `tallyVerdicts` also dedupes by `finding_uid`: a finding with two decision events is two
 * rows on the wire and one finding on this screen, `widgets/knowledge-base`'s own header
 * names the reason.
 *
 * **Scope.** One page of the journal (`JOURNAL_PAGE_LIMIT` events), same as
 * `/knowledge-base`'s own first screenful. A `next_cursor` on that page means the count
 * below is a page total, said as one.
 */

import Link from 'next/link';

import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { ApiError, ApiFailure, catalogMessage } from '@/shared/api';
import type { FindingCategory, Verdict } from '@/shared/api';
import { VERDICT_LABELS, useDecisionJournal } from '@/entities/expert-decision';

import { tallyVerdicts } from '../model/verdict-tally';

/**
 * Category headings, local to this panel.
 *
 * `widgets/knowledge-base` already exports `CATEGORY_LABELS`, and this is not a second
 * opinion about the wording — it cannot be imported: the FSD boundary this codebase lints
 * on (`web/eslint.config.mjs`) forbids one `widgets/*` slice importing another, on purpose,
 * so two dashboard panels never quietly depend on each other's internals. Two contract
 * values, restated once each, is the cost of that boundary and cheaper than the coupling.
 */
const CATEGORY_LABELS: Readonly<Record<FindingCategory, string>> = {
  internal_contradiction: 'Внутреннее противоречие',
  explicit_placeholder: 'Явный пропуск',
};

/** Verdicts worth a row even at zero. `needs_manual_review` has no PC-01 producer yet. */
const VERDICT_ROWS: readonly Verdict[] = ['accepted', 'rejected', 'pending', 'needs_manual_review'];

function journalFailure(error: unknown, retry: () => void): ErrorStateProps {
  if (error instanceof ApiError) {
    return {
      title: 'Находки по вердикту не удалось прочитать.',
      detail: catalogMessage(error.errorCode),
      correlationId: error.correlationId,
      ...(error.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {}),
    };
  }
  if (error instanceof ApiFailure) {
    return {
      title: 'Находки по вердикту не удалось прочитать.',
      detail: 'Сервер не ответил. Проверьте соединение и повторите запрос.',
      correlationId: error.correlationId,
      onRetry: retry,
      retryLabel: 'Повторить',
    };
  }
  return { title: 'Находки по вердикту не удалось прочитать.', onRetry: retry, retryLabel: 'Повторить' };
}

export function VerdictsPanel() {
  const journal = useDecisionJournal();

  if (journal.isPending) return <LoadingState what="находки по вердикту" />;

  if (journal.isError) {
    return <ErrorState {...journalFailure(journal.error, () => void journal.refetch())} />;
  }

  const page = journal.data;

  if (page.items.length === 0) {
    return (
      <EmptyState
        title="Решений пока нет."
        detail="Как только проверяющий примет или отклонит первую находку, она появится здесь."
      />
    );
  }

  const tally = tallyVerdicts(page.items);
  const truncated = page.page.next_cursor !== null;

  return (
    <div data-panel="findings-by-verdict">
      <p>
        Находок с решением: <strong>{tally.findingCount}</strong>.
      </p>
      <p className="am-state__correlation">
        Только находки, по которым хотя бы раз высказались: находка, которую ещё никто не
        открывал, в этом счёте не участвует — операция читает журнал решений, а не список
        всех находок.
      </p>
      {truncated ? (
        <p className="am-state__correlation">
          Показана первая страница журнала решений. Полный список — в{' '}
          <Link href="/knowledge-base">базе знаний</Link>.
        </p>
      ) : null}
      <table>
        <caption>По вердикту</caption>
        <tbody>
          {VERDICT_ROWS.map((verdict) => (
            <tr key={verdict} data-verdict={verdict}>
              <th scope="row">{VERDICT_LABELS[verdict]}</th>
              <td>{tally.byVerdict[verdict]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <table>
        <caption>По категории</caption>
        <tbody>
          {(Object.keys(CATEGORY_LABELS) as FindingCategory[]).map((category) => (
            <tr key={category} data-category={category}>
              <th scope="row">{CATEGORY_LABELS[category]}</th>
              <td>{tally.byCategory[category]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
