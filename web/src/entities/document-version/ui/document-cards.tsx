/**
 * Documents as a grid of cards (`R-151s`, register row UI-A-45; made dense by `UIP-S02-02`).
 *
 * The owner ruled that likeness to the original is layout only: its section shows the documents as a grid of
 * cards, so ours does too, on our tokens, and as close to its density as the type floor allows. A card is one line of the
 * document's name (the whole of it in the tooltip), the number of its version, the box that chooses it and, under them, the two
 * marks «Замечания N» and «Оптимизация N» with a sign of how far each has gone (✓ · —): about seven in a row at 1440 px, each at least
 * the card-height token of the grid (`UIP-G-14`). What the card used to draw in a row of its own — the state in words, the stage, the pages, «все
 * версии», the tags — stands in the tooltip and in text a screen reader reads (`cardFacts`); nothing is lost, only moved.
 *
 * Each card is one document's **current** version, as `listDocuments` answers it; the card opens the version, the number of the version
 * opens the document's history (all its versions). Presentational, like {@link VersionRow}: the screen decides every address, and an
 * optional `select` slot is where a screen that may act puts its selection control.
 *
 * `version_ordinal` is a display number: it is printed, never used as an address.
 */

import { Fragment } from 'react';
import type { DragEvent, ReactNode } from 'react';
import Link from 'next/link';

import type { DocumentVersion } from '@/shared/api';

import { activeRunHref, auditChip } from '../model/audit-state';
import { sectionTitleOf, stageBadgeText } from '../model/classification';
import { isComparisonOnly } from '../model/upload-kind';
import { AuditMarks } from './audit-chip';
import { ComparisonOnlyMark } from './comparison-only-mark';
import styles from './document-cards.module.css';

export interface DocumentCardAddresses {
  /** Where the card opens: the version, or its classification panel. */
  readonly href: string;
  /** The document's own page (every version). */
  readonly documentHref: string;
}

/**
 * `UIP-S02-07`: what a card does when the reader drags it (the browser's own drag and drop, no library). The screen decides where it may
 * be dropped; the card only says it was picked up and that the drag ended.
 */
export interface DocumentCardDrag {
  /** The card of this version was picked up. */
  readonly onStart: (version: DocumentVersion) => void;
  /** The drag ended, dropped or not. */
  readonly onEnd: () => void;
}

export interface DocumentCardGridProps {
  readonly documents: readonly DocumentVersion[];
  readonly addresses: (version: DocumentVersion) => DocumentCardAddresses;
  /** A selection control for one card, or nothing; drawn in the card's corner. */
  readonly select?: ((version: DocumentVersion) => ReactNode) | undefined;
  /**
   * `UIP-S02-07`: the card's own menu «⋯», or nothing. The screen builds it (an entity imports no feature) and it is drawn at the right
   * end of the line of the marks, above the card's stretched link.
   */
  readonly menu?: ((version: DocumentVersion) => ReactNode) | undefined;
  /** `UIP-S02-07`: with it the cards can be dragged; without it they cannot. */
  readonly drag?: DocumentCardDrag | undefined;
  /** `UIP-S02-07`: the `document_uid` of the card being dragged, so that it looks picked up. */
  readonly dragging?: string | null | undefined;
  /**
   * `UI-PARITY-DOC-AUDIT`: where «Разбор» of a result run opens. A card whose item carries an audit draws its marks
   * (`audit` is on `listDocuments` items only); with this, the mark «Замечания» of a document that was run links to the review.
   */
  readonly reviewAddress?: ((runId: string) => string) | undefined;
  /**
   * `D-461`: where the document's «Оптимизация» tab opens. With it, the mark «Оптимизация N» of a card is a link to that tab
   * (the screen builds the address; the counts are those of the latest pass, so the address names no pass). Without it, or with no
   * proposal to open, the mark stays a figure.
   */
  readonly optimisationAddress?: ((version: DocumentVersion) => string) | undefined;
  /**
   * `UI-A-53`: a card that opens the grid, as the original's Σ card «Оптимизация раздела» does. It is the section's
   * own control and not a document, so it is drawn in the grid's first cell and counted in no figure.
   */
  readonly leading?: ReactNode | undefined;
  /**
   * What the card says of the classification, in its tooltip and in words for a reader (`UIP-S02-02`). Inside a section's group the
   * section is the group's heading, so the cards pass `'stage'` (`'none'` for the group of documents with no classification).
   */
  readonly classification?: 'both' | 'stage' | 'none' | undefined;
}

export function documentCardTitle(version: DocumentVersion): string {
  return version.display_title ?? version.source_filename ?? version.version_uid;
}

/** One thing the card says in words and not in a line of its own: the tooltip and the text a screen reader reads. */
interface CardFact {
  readonly key: 'pages' | 'stage' | 'section' | 'tags' | 'archived' | 'versions';
  readonly text: string;
  /** The machine value, for an instrument (`data-project-stage`, `data-section-code`). */
  readonly attr?: readonly [string, string];
}

/**
 * What the dense card keeps out of its lines: the pages, the stage and the section the badges used to say (by `classification`), the
 * tags, the archive and «все версии», which the number of the version now opens. The state of the audit is the marks' (and the
 * tooltip's). A version with no confirmed section says so, as the badge did, wherever the group is not already the one without a
 * classification (`'none'`).
 */
function cardFacts(version: DocumentVersion, classification: 'both' | 'stage' | 'none'): readonly CardFact[] {
  const facts: CardFact[] = [{ key: 'pages', text: `${version.page_count} стр.` }];
  if (classification !== 'none') {
    const confirmed = version.classification;
    if (confirmed === undefined) {
      facts.push({ key: 'section', text: 'Раздел не подтверждён' });
    } else {
      facts.push({ key: 'stage', text: stageBadgeText(confirmed.project_stage), attr: ['data-project-stage', confirmed.project_stage] });
      if (classification === 'both') {
        facts.push({ key: 'section', text: sectionTitleOf(confirmed.section_code), attr: ['data-section-code', confirmed.section_code] });
      }
    }
  }
  const tags = version.tags ?? [];
  if (tags.length > 0) facts.push({ key: 'tags', text: `Метки: ${tags.join(', ')}` });
  if (version.archived_at !== undefined) facts.push({ key: 'archived', text: 'В архиве' });
  facts.push({ key: 'versions', text: 'все версии' });
  return facts;
}

/** The tooltip of a card: the document's whole name, then its state, then the rest, a line each. */
function cardTooltip(version: DocumentVersion, facts: readonly CardFact[]): string {
  const chip = auditChip(version.audit);
  const lines = [documentCardTitle(version)];
  if (chip !== null) lines.push(chip.partial ? `${chip.text} (частично)` : chip.text);
  if (chip?.detail !== undefined && chip.detail !== null) lines.push(chip.detail);
  // «все версии» is the last line, said with the number of the version that opens them.
  for (const fact of facts) if (fact.key !== 'versions') lines.push(fact.text);
  lines.push(`V${version.version_ordinal}: все версии документа`);
  return lines.join('\n');
}

export function DocumentCardGrid({
  documents, addresses, select, menu, drag, dragging, reviewAddress, optimisationAddress, leading, classification = 'both',
}: DocumentCardGridProps) {
  return (
    <ul className={styles.grid} data-document-cards={documents.length}>
      {leading === undefined || leading === null ? null : <li className={styles.leading} data-grid-leading="">{leading}</li>}
      {documents.map((version) => {
        const { href, documentHref } = addresses(version);
        const control = select?.(version) ?? null;
        const menuControl = menu?.(version) ?? null;
        const facts = cardFacts(version, classification);
        const archived = version.archived_at !== undefined;
        const classNames = [styles.card];
        if (archived) classNames.push(styles.cardArchived);
        if (drag !== undefined) classNames.push(styles.cardDraggable);
        if (dragging === version.document_uid) classNames.push(styles.cardPicked);
        const marks = (
          <AuditMarks
            audit={version.audit}
            reviewHref={
              version.audit?.result_run_id === undefined || reviewAddress === undefined
                ? undefined
                : reviewAddress(version.audit.result_run_id)
            }
            optimisationHref={optimisationAddress?.(version)}
            runHref={activeRunHref(version)}
          />
        );
        return (
          <li
            key={version.document_uid}
            className={classNames.join(' ')}
            data-version-uid={version.version_uid}
            data-document-uid={version.document_uid}
            {...(drag === undefined
              ? {}
              : {
                  draggable: true,
                  onDragStart: (event: DragEvent<HTMLLIElement>) => {
                    const { dataTransfer, currentTarget } = event;
                    dataTransfer.effectAllowed = 'move';
                    // A drag that starts on a link carries the link's address, and a drop outside the groups could open it: the card carries
                    // its name only (a browser starts no drag without data), and the picture of the drag is the card, not the link's text.
                    dataTransfer.clearData();
                    dataTransfer.setData('text/plain', documentCardTitle(version));
                    const box = currentTarget.getBoundingClientRect();
                    dataTransfer.setDragImage(currentTarget, event.clientX - box.left, event.clientY - box.top);
                    drag.onStart(version);
                  },
                  onDragEnd: () => drag.onEnd(),
                })}
          >
            {/* One line: the name (the whole of it in the tooltip), the number of the version, the box that chooses the card. */}
            <div className={styles.top}>
              <p className={styles.title}>
                <Link href={href} title={cardTooltip(version, facts)}>{documentCardTitle(version)}</Link>
              </p>
              <Link className={styles.ordinal} href={documentHref} title="Все версии документа">V{version.version_ordinal}</Link>
              {control === null ? null : <label className={styles.select}>{control}</label>}
            </div>
            {/* `UIP-S02-02`: the original's two pills «Замечания» and «Оптимизация», each with its sign of how far it has gone. */}
            {/* `UIP-S02-07`: the card's menu «⋯», where the screen gives one, stands at the right end of the marks' line. */}
            {menuControl === null ? marks : (
              <div className={styles.foot}>
                {marks}
                <span className={styles.menu} data-card-menu="">{menuControl}</span>
              </div>
            )}
            {archived ? <span className={styles.archived} aria-hidden="true">В архиве</span> : null}
            {isComparisonOnly(version) ? <ComparisonOnlyMark version={version} /> : null}
            <span
              className={styles.facts}
              data-card-facts=""
              {...(classification === 'none'
                ? {}
                : { 'data-version-classification': version.classification === undefined ? 'unclassified' : `${version.classification.project_stage}:${version.classification.section_code}` })}
            >
              {facts.map((fact, index) => (
                <Fragment key={fact.key}>
                  {index === 0 ? null : ' '}
                  <span data-card-fact={fact.key} {...(fact.attr === undefined ? {} : { [fact.attr[0]]: fact.attr[1] })}>{fact.text}</span>
                </Fragment>
              ))}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
