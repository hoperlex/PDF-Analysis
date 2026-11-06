/**
 * The audit state of one document, as a chip on its card (`UI-PARITY-DOC-AUDIT`, UI-A-46).
 *
 * Presentational. It takes the contract's optional `audit` of a `listDocuments` item and the address of the review of
 * its result run (the screen decides every address), and draws nothing when the answer carried no audit: an
 * operation that reads no runs says nothing about them. A document that was run links its chip to «Разбор» of the
 * result run; a partial result carries the mark «частично» beside the chip (`R-150s`).
 */

import Link from 'next/link';

import type { DocumentAudit } from '@/shared/api';

import { AUDIT_PARTIAL_MARK, AUDIT_PARTIAL_TITLE, auditChip } from '../model/audit-state';
import styles from './audit-chip.module.css';

export interface AuditChipProps {
  readonly audit: DocumentAudit | undefined;
  /** Where «Разбор» of the result run opens; used only while the document has a result run. */
  readonly reviewHref?: string | undefined;
}

export function AuditChip({ audit, reviewHref }: AuditChipProps) {
  const chip = auditChip(audit);
  if (chip === null) return null;
  const className = `am-badge am-badge--${chip.tone} ${styles.chip}`;
  const title = chip.detail ?? undefined;
  return (
    <span className={styles.chips} data-audit-state={chip.state} data-audit-partial={chip.partial ? 'true' : 'false'}>
      {chip.resultRunId !== null && reviewHref !== undefined ? (
        <Link href={reviewHref} className={className} title={title}>{chip.text}</Link>
      ) : (
        <span className={className} title={title}>{chip.text}</span>
      )}
      {chip.partial ? (
        <span className={`am-badge am-badge--degraded ${styles.chip}`} title={AUDIT_PARTIAL_TITLE}>{AUDIT_PARTIAL_MARK}</span>
      ) : null}
    </span>
  );
}
