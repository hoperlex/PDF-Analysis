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
}

export function documentCardTitle(version: DocumentVersion): string {
  return version.display_title ?? version.source_filename ?? version.version_uid;
}

export function DocumentCardGrid({ documents, addresses, select, reviewAddress }: DocumentCardGridProps) {
  return (
    <ul className={styles.grid} data-document-cards={documents.length}>
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
              {version.archived_at === undefined ? null : <span className={styles.archived}>В архиве</span>}
              {control === null ? null : <span className={styles.select}>{control}</span>}
            </div>
            <p className={styles.title}>
              <Link href={href}>{documentCardTitle(version)}</Link>
            </p>
            <div className={styles.badges}>
              <ClassificationBadges classification={version.classification} />
            </div>
            {/* `UI-A-46`: the audit state of the current version, read by the server for the page. */}
            {version.audit === undefined ? null : (
              <div className={styles.badges}>
                <AuditChip
                  audit={version.audit}
                  reviewHref={
                    version.audit.result_run_id === undefined || reviewAddress === undefined
                      ? undefined
                      : reviewAddress(version.audit.result_run_id)
                  }
                />
              </div>
            )}
            {/* `R-151e`: the document's free tags. */}
            {(version.tags ?? []).length === 0 ? null : (
              <p className={styles.tags}>{(version.tags ?? []).map((tag) => <span key={tag} className={styles.tag}>{tag}</span>)}</p>
            )}
            {isComparisonOnly(version) ? <ComparisonOnlyMark version={version} /> : null}
            <p className={styles.meta}>
              страниц {version.page_count} · <Link href={documentHref}>все версии</Link>
            </p>
          </li>
        );
      })}
    </ul>
  );
}
