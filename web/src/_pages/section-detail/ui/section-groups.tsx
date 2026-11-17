'use client';

/**
 * The section's cards by group (`UIP-S02-06`, owner rulings Г11, Г12-B, Г1-C): under a compact heading — the group's name and the number of its
 * documents — each group's own grid of cards, «Без группы» last. The heading is a line of the group's frame, not a card (the
 * original's is a strip over the group's cards); «Без группы» has a dashed frame, as the original's virtual group has.
 *
 * Drawn only when the section has a group at all (`groupDocuments` answers `null` otherwise, and the page draws the plain grid with
 * no heading). The groups are made of the whole listing, so the numbers in the headings are the groups' own: while the pages are being
 * read, or when one failed, it draws no group from a part — the one line that says so, with «Повторить», is the row over the cards
 * (`SectionBatchBar`), which the choosing of whole-section documents shares (`UIP-DEBT-02`).
 *
 * The Σ card that opens the section's grid stays the first cell of the first group, as the original's does. Everything else a grid
 * of cards takes (the addresses, the selection box) is the same for every group and comes in once, as `grid`.
 *
 * **A group takes a dropped card** (`UIP-S02-07`): with `drop` a group that is not the dragged card's own is a place to drop it, and lights
 * while the card is over it. While a card is dragged and no document is in «Без группы», that group stands at the end all the same, empty,
 * so the card can be taken out of its group by dropping it there; it is not drawn at any other time (a group is there as long as a
 * document is in it).
 *
 * Presentational: the groups, the drag and the cards' slots come in as props.
 */

import type { DragEvent, ReactNode } from 'react';

import { DocumentCardGrid } from '@/entities/document-version';
import type { DocumentCardGridProps } from '@/entities/document-version';

import type { DocumentGroup } from '../model/group-documents';
import { NO_GROUP_LABEL } from '../model/group-documents';
import { dropRequest } from '../model/group-move';
import type { DragSource } from '../model/group-move';
import styles from './section-groups.module.css';

/** What every group's grid takes but its documents and its first cell: the same for each group. */
export type SectionGroupGrid = Omit<DocumentCardGridProps, 'documents' | 'leading'>;

/** What the groups need to take a dropped card (`UIP-S02-07`): the card being dragged, the group it is over, and the three events. */
export interface GroupDrop {
  /** The card being dragged, or `null` while none is. */
  readonly source: DragSource | null;
  /** The group the card is over: its name, `null` for «Без группы», `undefined` when it is over none. */
  readonly over: string | null | undefined;
  readonly onOver: (target: string | null) => void;
  readonly onLeave: (target: string | null) => void;
  /** The card was dropped on the group: its name, or `null` for «Без группы». */
  readonly onDrop: (target: string | null) => void;
}

export interface SectionGroupsProps {
  /** The groups of the whole listing, in the order they stand (`groupDocuments`). */
  readonly groups: readonly DocumentGroup[];
  /** The Σ card of the section: the first cell of the first group's grid. */
  readonly leading?: ReactNode | undefined;
  readonly grid: SectionGroupGrid;
  /** `UIP-S02-07`: where a dragged card may be dropped; without it the groups take nothing. */
  readonly drop?: GroupDrop | undefined;
}

/** One group: its frame, its heading and its cards (or, empty, the words that say a card may be dropped there). */
export function SectionGroup({ group, index, leading, grid, drop }: {
  readonly group: DocumentGroup;
  /** The group's place among the groups, for the id its heading names it by. */
  readonly index: number;
  readonly leading: ReactNode | undefined;
  readonly grid: SectionGroupGrid;
  readonly drop: GroupDrop | undefined;
}) {
  const headingId = `section-group-heading-${index}`;
  const none = group.name === null;
  // A group is a place to drop only for a card that is not in it already.
  const accepts = drop !== undefined && drop.source !== null && dropRequest(drop.source, group.name) !== null;
  const over = accepts && drop.over === group.name;
  const classNames = [styles.group];
  if (none) classNames.push(styles.groupNone);
  if (over) classNames.push(styles.groupOver);
  return (
    <section
      className={classNames.join(' ')}
      aria-labelledby={headingId}
      data-group-kind={none ? 'none' : 'named'}
      data-group-count={group.documents.length}
      {...(group.name === null ? {} : { 'data-group-name': group.name })}
      {...(accepts ? { 'data-group-drop': over ? 'over' : 'ready' } : {})}
      {...(!accepts || drop === undefined
        ? {}
        : {
            onDragOver: (event: DragEvent<HTMLElement>) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = 'move';
              if (drop.over !== group.name) drop.onOver(group.name);
            },
            onDragLeave: (event: DragEvent<HTMLElement>) => {
              // Moving over a card inside the group is not leaving the group.
              const into = event.relatedTarget;
              if (into instanceof Node && event.currentTarget.contains(into)) return;
              drop.onLeave(group.name);
            },
            onDrop: (event: DragEvent<HTMLElement>) => {
              event.preventDefault();
              drop.onDrop(group.name);
            },
          })}
    >
      <h2 className={none ? `${styles.heading} ${styles.headingNone}` : styles.heading} id={headingId}>
        <span className={styles.name}>{group.name ?? NO_GROUP_LABEL}</span>
        <span className={styles.count}>({group.documents.length})</span>
      </h2>
      {group.documents.length === 0 ? (
        <p className={styles.dropHint} data-group-drop-hint="">Перетащите карточку сюда, чтобы убрать документ из группы.</p>
      ) : (
        <DocumentCardGrid {...grid} documents={group.documents} leading={leading} />
      )}
    </section>
  );
}

export function SectionGroups({ groups, leading, grid, drop }: SectionGroupsProps) {
  // While a card is dragged out of the last named group no document is in «Без группы», and the place to drop it must still be there.
  const needsNone = drop !== undefined && drop.source !== null && drop.source.group !== null && groups.every((group) => group.name !== null);
  const shown = needsNone ? [...groups, { name: null, documents: [] }] : groups;
  return (
    <div className={styles.groups} data-section-groups={groups.length}>
      {shown.map((group, index) => (
        // A group's name is never empty and never repeats, so it is the key; «Без группы» is the one with none.
        <SectionGroup key={group.name ?? ''} group={group} index={index} leading={index === 0 ? leading : undefined} grid={grid} drop={drop} />
      ))}
    </div>
  );
}
