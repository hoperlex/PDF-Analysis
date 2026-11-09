/**
 * Documents as a grid of cards (`R-151s`, register row UI-A-45).
 *
 * The owner ruled that likeness to the original is layout only: its section shows the documents as a grid of
 * cards (name, version badge, a selection box), so ours does too, on our tokens. Each card is one document's
 * **current** version, as `listDocuments` answers it; the card opens the version and offers the document's
 * history. Presentational, like {@link VersionRow}: the screen decides every address, and an optional `select`
 * slot is where a screen that may act puts its selection control.
 *
 * `version_ordinal` is a display number: it is printed, never used as an address.
 */

import type { ReactNode } from 'react';
import Link from 'next/link';

import type { DocumentVersion } from '@/shared/api';

import { activeRunHref, optimisationPill, pluralRu } from '../model/audit-state';
import { isComparisonOnly } from '../model/upload-kind';
import { AuditChip } from './audit-chip';
import { ClassificationBadges } from './classification-badges';
import { ComparisonOnlyMark } from './comparison-only-mark';
import styles from './document-cards.module.css';

export interface DocumentCardAddresses {
  /** Where the card opens: the version, or its classification panel. */
  readonly href: string;
  /** The document's own page (every version). */
  readonly documentHref: string;
}

export interface DocumentCardGridProps {
  readonly documents: readonly DocumentVersion[];
  readonly addresses: (version: DocumentVersion) => DocumentCardAddresses;
  /** A selection control for one card, or nothing; drawn in the card's corner. */
  readonly select?: ((version: DocumentVersion) => ReactNode) | undefined;
  /**
   * `UI-PARITY-DOC-AUDIT`: where «Разбор» of a result run opens. A card whose item carries an audit draws its chip
   * (`audit` is on `listDocuments` items only); with this, the chip of a document that was run links to the review.
   */
  readonly reviewAddress?: ((runId: string) => string) | undefined;
  /**
   * `D-461`: where the document's «Оптимизация» tab opens. With it, the pill «Оптимизация N» of a card is a link to that tab
   * (the screen builds the address; the pill's counts are those of the latest pass, so the address names no pass). Without it the
   * pill stays a figure.
   */
  readonly optimisationAddress?: ((version: DocumentVersion) => string) | undefined;
  /**
   * `UI-A-53`: a card that opens the grid, as the original's Σ card «Оптимизация раздела» does. It is the section's
   * own control and not a document, so it is drawn in the grid's first cell and counted in no figure.
   */
  readonly leading?: ReactNode | undefined;
  /**
   * What the badges say of the classification. Inside a section's group the section is the group's heading, so the
   * cards pass `'stage'` and keep the line short (`'none'` for the group of documents with no classification).
   */
  readonly classification?: 'both' | 'stage' | 'none' | undefined;
}

const FINDINGS_WORD: readonly [string, string, string] = ['замечание', 'замечания', 'замечаний'];

/**
 * `D-361`, `UI-A-46` (second half): the original's second pill «Оптимизация N [метка]» -- the proposals of the document's latest
 * optimisation pass, and while an expert still has some to decide, the marker «3 не решено». Nothing for a document no pass was
 * started over, or whose pass produced no proposal.
 */
function OptimisationPillMark({ audit, href }: { readonly audit: DocumentVersion['audit']; readonly href?: string | undefined }) {
  const pill = optimisationPill(audit);
  if (pill === null) return null;
  const content = (
    <>
      {pill.text}
      {pill.mark === null ? null : <span className={styles.optimisationMark}>{pill.mark}</span>}
    </>
  );
  const marks = {
    className: styles.optimisation,
    'data-card-optimisation': pill.count,
    'data-card-optimisation-undecided': pill.undecided,
    title: pill.title,
  };
  // `D-461`: a link to the document's «Оптимизация» tab where the screen gave an address, a figure otherwise.
  return href === undefined ? <span {...marks}>{content}</span> : <Link href={href} {...marks}>{content}</Link>;
}

export function documentCardTitle(version: DocumentVersion): string {
  return version.display_title ?? version.source_filename ?? version.version_uid;
}

export function DocumentCardGrid({
  documents, addresses, select, reviewAddress, optimisationAddress, leading, classification = 'both',
}: DocumentCardGridProps) {
  return (
    <ul className={styles.grid} data-document-cards={documents.length}>
      {leading === undefined || leading === null ? null : <li className={styles.leading} data-grid-leading="">{leading}</li>}
      {documents.map((version) => {
        const { href, documentHref } = addresses(version);
        const control = select?.(version) ?? null;
        return (
          <li
            key={version.document_uid}
            className={version.archived_at === undefined ? styles.card : `${styles.card} ${styles.cardArchived}`}
            data-version-uid={version.version_uid}
            data-document-uid={version.document_uid}
          >
            <div className={styles.top}>
              <span className={styles.ordinal} title="Номер текущей версии документа">V{version.version_ordinal}</span>
              <span className={styles.pages}>{version.page_count} стр.</span>
              {version.archived_at === undefined ? null : <span className={styles.archived}>В архиве</span>}
              <span className={styles.topEnd}>
                <Link href={documentHref} title="История версий документа">все версии</Link>
                {control === null ? null : <span className={styles.select}>{control}</span>}
              </span>
            </div>
            <p className={styles.title}>
              <Link href={href}>{documentCardTitle(version)}</Link>
            </p>
            {/* The stage, and `UI-A-46` the audit state the server read for the page: one row, as the original's pills. */}
            <div className={styles.badges}>
              <ClassificationBadges classification={version.classification} shown={classification} />
              {version.audit === undefined ? null : (
                <AuditChip
                  audit={version.audit}
                  reviewHref={
                    version.audit.result_run_id === undefined || reviewAddress === undefined
                      ? undefined
                      : reviewAddress(version.audit.result_run_id)
                  }
                  runHref={activeRunHref(version)}
                />
              )}
              {/* The original's pill «Замечания N»: how many findings the result run published. */}
              {version.audit === undefined || version.audit.finding_count === 0 ? null : (
                <span className={styles.findings} data-card-findings={version.audit.finding_count}>
                  {version.audit.finding_count} {pluralRu(version.audit.finding_count, FINDINGS_WORD)}
                </span>
              )}
              <OptimisationPillMark audit={version.audit} href={optimisationAddress?.(version)} />
            </div>
            {/* `R-151e`: the document's free tags. */}
            {(version.tags ?? []).length === 0 ? null : (
              <p className={styles.tags}>{(version.tags ?? []).map((tag) => <span key={tag} className={styles.tag}>{tag}</span>)}</p>
            )}
            {isComparisonOnly(version) ? <ComparisonOnlyMark version={version} /> : null}
          </li>
        );
      })}
    </ul>
  );
}
