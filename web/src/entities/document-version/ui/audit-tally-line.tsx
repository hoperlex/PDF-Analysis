/**
 * «12 документов · не запускались 4 · ждут решения 3 · проверено 5 · 27 замечаний»: the original's section row of
 * numbers (`UI-A-35`), as one row of compact badges. Presentational: it takes figures already counted
 * ({@link auditTally}, {@link tallyOfCounts}) and holds no query.
 */

import Link from 'next/link';

import type { AuditTally } from '../model/audit-tally';
import { tallyParts } from '../model/audit-tally';
import styles from './audit-tally-line.module.css';

export interface AuditTallyLineProps {
  readonly tally: AuditTally;
  /** The figures cover a page of a longer listing; the line says so in words. */
  readonly partial?: boolean | undefined;
  /** Names the set in the accessible label, e.g. «Раздел АР». */
  readonly label?: string | undefined;
  /**
   * `UI-A-38`: where «не запускались N» leads, as the original's click on that number selects the section's
   * unanalysed projects. The screen decides the address (the section narrowed to the documents never run); absent,
   * the badge is plain.
   */
  readonly notRunHref?: string | undefined;
}

export function AuditTallyLine({ tally, partial = false, label, notRunHref }: AuditTallyLineProps) {
  return (
    <span
      className={styles.line}
      role="group"
      aria-label={label === undefined ? 'Состояние проверки документов' : `Состояние проверки: ${label}`}
      data-audit-tally={tally.documents}
      data-audit-tally-partial={partial ? 'true' : 'false'}
    >
      {tallyParts(tally).map((part) => {
        const content = part.key === 'findings' || part.key === 'documents'
          ? <><span className={styles.count}>{part.count}</span> {part.label}</>
          : <>{part.label} <span className={styles.count}>{part.count}</span></>;
        return part.tone === null ? (
          <span key={part.key} className={part.key === 'documents' ? styles.total : styles.part} title={part.title} data-tally={part.key}>
            {content}
          </span>
        ) : part.key === 'notRun' && notRunHref !== undefined ? (
          <Link key={part.key} href={notRunHref} className={`am-badge am-badge--${part.tone} ${styles.part}`} title={part.title} data-tally={part.key} data-tally-link="">
            {content}
          </Link>
        ) : (
          <span key={part.key} className={`am-badge am-badge--${part.tone} ${styles.part}`} title={part.title} data-tally={part.key}>
            {content}
          </span>
        );
      })}
      {partial ? <span className={styles.scope}>по документам этой страницы</span> : null}
    </span>
  );
}
