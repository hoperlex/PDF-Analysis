'use client';

/** @jsxRuntime automatic */

/**
 * The findings of a run, grouped by category.
 *
 * A pure widget: contract models and callbacks in, markup out, per seam §3.4. It holds no
 * query and no mutation, which is what lets it be rendered in a test with no DOM, no
 * `jsdom` and no provider.
 *
 * Every row here is a **published** finding. `P02_SEAMS.md` §5.1 keeps an ungrounded item
 * out of the finding query entirely, and `entities/finding`'s admission gate keeps it out
 * of `groups` on this side too — so this component has no branch for one, and adding a
 * row that bypassed admission would mean writing a new code path rather than relaxing a
 * condition.
 */

import type { Finding, FindingCategory } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import type { FindingGroup } from '@/entities/finding';
import { countGrouped } from '@/entities/finding';
import { VerdictBadge } from '@/entities/expert-decision';
import { declaredPages } from '@/entities/finding-observation';

/** A finding that was admitted and then found structurally impossible. */
export interface FindingIntegrityFault {
  readonly findingUid: string;
  readonly refusal: string;
}

export interface FindingListProps {
  readonly groups: readonly FindingGroup<Finding>[];
  readonly selectedFindingUid: string | null;
  readonly onSelect: (findingUid: string) => void;
  readonly isLoading?: boolean | undefined;
  /** Already presented as `ErrorState` props by the page, so `retryable` is decided once. */
  readonly error?: ErrorStateProps | null | undefined;
  readonly integrityFaults?: readonly FindingIntegrityFault[] | undefined;
}

/** Category labels. The contract value is what the row carries; this is only the heading. */
function categoryHeading(category: FindingCategory): string {
  switch (category) {
    case 'internal_contradiction':
      return 'internal_contradiction';
    case 'explicit_placeholder':
      return 'explicit_placeholder';
    default:
      return category;
  }
}

export function FindingList({
  groups,
  selectedFindingUid,
  onSelect,
  isLoading,
  error,
  integrityFaults,
}: FindingListProps) {
  if (isLoading === true) return <LoadingState what="находки" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

  const total = countGrouped(groups);
  const faults = integrityFaults ?? [];

  if (total === 0 && faults.length === 0) {
    return (
      <EmptyState
        title="Находок нет"
        detail={
          <p>
            Прогон не опубликовал ни одной находки. Элементы модели, чьи цитаты не
            разрешились по заявленным якорям, находками не являются и сохраняются только
            как диагностика прогона.
          </p>
        }
      />
    );
  }

  return (
    <div className="am-finding-list" data-finding-count={total}>
      {faults.length > 0 ? (
        <ErrorState
          title="Нарушение целостности данных"
          detail={
            <p>
              Находок без свидетельств: {faults.length}. Шлюз свидетельств P02 делает такое
              невозможным, поэтому это сообщаемая неисправность, а не пустая панель:{' '}
              {faults.map((fault) => fault.findingUid).join(', ')}
            </p>
          }
        />
      ) : null}

      {groups.map((group) => (
        <section
          key={group.category}
          className="am-finding-group"
          data-category={group.category}
        >
          <h3 className="am-finding-group__heading">
            {categoryHeading(group.category)}{' '}
            <span className="am-finding-group__count">{group.findings.length}</span>
          </h3>
          <ul className="am-finding-group__items">
            {group.findings.map((finding) => {
              const pages = declaredPages(finding.observation);
              const selected = finding.finding_uid === selectedFindingUid;
              return (
                <li key={finding.finding_uid}>
                  <button
                    type="button"
                    className="am-finding-row am-button"
                    data-finding-uid={finding.finding_uid}
                    data-selected={selected ? 'true' : 'false'}
                    aria-current={selected ? 'true' : undefined}
                    onClick={() => {
                      onSelect(finding.finding_uid);
                    }}
                  >
                    <span className="am-finding-row__text">
                      {finding.observation.finding_text}
                    </span>
                    <VerdictBadge verdict={finding.current_verdict} />
                    <span className="am-finding-row__pages" data-pages={pages.join(',')}>
                      {pages.length === 1 ? `стр. ${pages[0]}` : `стр. ${pages.join(', ')}`}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
