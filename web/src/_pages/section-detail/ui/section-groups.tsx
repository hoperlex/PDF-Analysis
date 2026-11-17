'use client';

/**
 * The section's cards by group (`UIP-S02-06`, owner rulings Г11, Г12-B, Г1-C): under a compact heading — the group's name and the number of its
 * documents — each group's own grid of cards, «Без группы» last. The heading is a line of the group's frame, not a card (the
 * original's is a strip over the group's cards); «Без группы» has a dashed frame, as the original's virtual group has.
 *
 * Drawn only when the section has a group at all (`groupDocuments` answers `null` otherwise, and the page draws the plain grid with
 * no heading). The groups are made of the whole listing, so the numbers in the headings are the groups' own: while the pages are being
 * read the page says so ({@link GroupsWalkNote}) and when one failed it says that, with «Повторить» — it never draws groups from a part.
 *
 * The Σ card that opens the section's grid stays the first cell of the first group, as the original's does. Everything else a grid
 * of cards takes (the addresses, the selection box) is the same for every group and comes in once, as `grid`.
 *
 * Presentational: the groups, the walk and the cards' slots come in as props.
 */

import { useId } from 'react';
import type { ReactNode } from 'react';

import { ErrorState } from '@/shared/ui';
import { DocumentCardGrid } from '@/entities/document-version';
import type { DocumentCardGridProps } from '@/entities/document-version';

import type { DocumentGroup } from '../model/group-documents';
import { NO_GROUP_LABEL } from '../model/group-documents';
import type { ListingWalk } from '../model/use-listing-walk';
import styles from './section-groups.module.css';

/** What every group's grid takes but its documents and its first cell: the same for each group. */
export type SectionGroupGrid = Omit<DocumentCardGridProps, 'documents' | 'leading'>;

export interface SectionGroupsProps {
  /** The groups of the whole listing, in the order they stand (`groupDocuments`). */
  readonly groups: readonly DocumentGroup[];
  /** The Σ card of the section: the first cell of the first group's grid. */
  readonly leading?: ReactNode | undefined;
  readonly grid: SectionGroupGrid;
}

function GroupBlock({ group, leading, grid }: { readonly group: DocumentGroup; readonly leading: ReactNode | undefined; readonly grid: SectionGroupGrid }) {
  const headingId = useId();
  const none = group.name === null;
  return (
    <section
      className={none ? `${styles.group} ${styles.groupNone}` : styles.group}
      aria-labelledby={headingId}
      data-group-kind={none ? 'none' : 'named'}
      data-group-count={group.documents.length}
      {...(group.name === null ? {} : { 'data-group-name': group.name })}
    >
      <h2 className={none ? `${styles.heading} ${styles.headingNone}` : styles.heading} id={headingId}>
        <span className={styles.name}>{group.name ?? NO_GROUP_LABEL}</span>
        <span className={styles.count}>({group.documents.length})</span>
      </h2>
      <DocumentCardGrid {...grid} documents={group.documents} leading={leading} />
    </section>
  );
}

export function SectionGroups({ groups, leading, grid }: SectionGroupsProps) {
  return (
    <div className={styles.groups} data-section-groups={groups.length}>
      {groups.map((group, index) => (
        // A group's name is never empty and never repeats, so it is the key; «Без группы» is the one with none.
        <GroupBlock key={group.name ?? ''} group={group} leading={index === 0 ? leading : undefined} grid={grid} />
      ))}
    </div>
  );
}

export interface GroupsWalkNoteProps {
  /** The listing read to its end, or `idle` when the page is all of it. */
  readonly walk: ListingWalk;
}

/**
 * What the page says while it cannot yet say whether the section has groups: the line that the pages are being read, and, when one
 * could not be read, the error with the retry. Nothing once the listing is known whole.
 */
export function GroupsWalkNote({ walk }: GroupsWalkNoteProps) {
  if (walk.status === 'pending') {
    return (
      <p className={styles.reading} role="status" data-groups-walk="pending">
        Читаю все страницы раздела…
      </p>
    );
  }
  if (walk.status === 'failed') {
    return (
      <div className={styles.failed} data-groups-walk="failed">
        <ErrorState
          title="Не удалось прочитать все страницы раздела"
          detail="Группы показываются, только когда раздел прочитан целиком; пока ниже карточки этой страницы без групп."
          onRetry={walk.retry}
          retryLabel="Повторить"
        />
      </div>
    );
  }
  return null;
}
