/**
 * The audit state of one document, as a chip on its card (`UI-PARITY-DOC-AUDIT`, UI-A-46).
 *
 * Presentational. It takes the contract's optional `audit` of a `listDocuments` item and the address of the review of
 * its result run (the screen decides every address), and draws nothing when the answer carried no audit: an
 * operation that reads no runs says nothing about them. A document that was run links its chip to «Разбор» of the
 * result run; a partial result carries the mark «частично» beside the chip (`R-150s`).
 *
 * `UI-A-47`: a run in flight (`audit.active_run`) is a second mark beside the chip, «Идёт аудит: в очереди / выполняется /
 * проверяется», linked to that run's page; the four-state chip is exactly what it was. Nothing is drawn when the server
 * names no run in flight.
 */

import Link from 'next/link';

import type { DocumentAudit } from '@/shared/api';

import type { CardMark } from '../model/audit-state';
import {
  ACTIVE_RUN_TITLE, AUDIT_PARTIAL_MARK, AUDIT_PARTIAL_TITLE, CARD_MARK_SIGNS, CARD_MARK_WORDS, activeRunMark, auditChip,
  findingsMark, optimisationMark,
} from '../model/audit-state';
import styles from './audit-chip.module.css';

export interface AuditChipProps {
  readonly audit: DocumentAudit | undefined;
  /** Where «Разбор» of the result run opens; used only while the document has a result run. */
  readonly reviewHref?: string | undefined;
  /** Where the run page of the run in flight opens (`UI-A-47`); without it the mark is drawn and not linked. */
  readonly runHref?: string | undefined;
}

export function AuditChip({ audit, reviewHref, runHref }: AuditChipProps) {
  const chip = auditChip(audit);
  if (chip === null) return null;
  const active = activeRunMark(audit);
  const activeClass = `am-badge am-badge--pending ${styles.chip}`;
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
      {active === null ? null : runHref === undefined ? (
        <span className={activeClass} title={ACTIVE_RUN_TITLE} data-audit-active-run={active.state}>{active.text}</span>
      ) : (
        <Link href={runHref} className={activeClass} title={ACTIVE_RUN_TITLE} data-audit-active-run={active.state}>
          {active.text}
        </Link>
      )}
    </span>
  );
}

// ---- the marks of a document card (`UIP-S02-02`) ----------------------------------------------------------------------

export interface AuditMarksProps {
  readonly audit: DocumentAudit | undefined;
  /** Where «Разбор» of the result run opens; the mark «Замечания» is a link only while the document has a result run. */
  readonly reviewHref?: string | undefined;
  /** Where the document's «Оптимизация» tab opens (`D-461`); without it the mark is a figure. */
  readonly optimisationHref?: string | undefined;
  /** Where the run page of the run in flight opens (`UI-A-47`); without it the mark is drawn and not linked. */
  readonly runHref?: string | undefined;
}

function CardMarkView({ mark, href, extra }: {
  readonly mark: CardMark;
  readonly href: string | undefined;
  readonly extra: Readonly<Record<string, number | string>>;
}) {
  const props = {
    className: `am-badge am-badge--${mark.tone} ${styles.mark}`,
    title: mark.title,
    'data-card-mark': mark.kind,
    'data-card-mark-state': mark.state,
    ...extra,
  };
  const content = (
    <>
      <span className={styles.label}>{mark.label}</span>
      {mark.count === null ? null : <span className={styles.count}>{mark.count}</span>}
      <span className={styles.sign} aria-hidden="true">{CARD_MARK_SIGNS[mark.state]}</span>
      <span className={styles.hidden}>{CARD_MARK_WORDS[mark.state]}</span>
    </>
  );
  return href === undefined ? <span {...props}>{content}</span> : <Link href={href} {...props}>{content}</Link>;
}

/**
 * The two marks of a document card, «Замечания N» and «Оптимизация N», each with the sign of how far it has gone — ✓ all decided,
 * · something undecided, — not run — in place of the state chip (`UIP-S02-02`, the original's pills in our tokens and at 11.5 px at
 * the least). The word of each stands visually hidden while the card is narrower than the words need (the original does the same at
 * 1440 px: the number and the sign remain) and in full beside it where the card is wide; a reader who does not see them is told them
 * in words either way. The state in words («Не запускался», «Ждёт решения: 2», «Проверен экспертом») is the first of those words, with
 * the figures of the result run in the tooltip, as the chip carried them.
 *
 * Also here, as marks of the same row: «!» for a partial result (`R-150s`), and the run in flight (`UI-A-47`) as the chip draws it.
 * Nothing at all for an answer that carried no audit: an operation that reads no runs says nothing about them.
 */
export function AuditMarks({ audit, reviewHref, optimisationHref, runHref }: AuditMarksProps) {
  const chip = auditChip(audit);
  if (audit === undefined || chip === null) return null;
  const findings = findingsMark(audit);
  const optimisation = optimisationMark(audit);
  const active = activeRunMark(audit);
  const activeClass = `am-badge am-badge--pending ${styles.chip} ${styles.run}`;
  return (
    <span className={styles.marks} data-audit-state={chip.state} data-audit-partial={chip.partial ? 'true' : 'false'}>
      <span className={styles.hidden} data-audit-status="">{chip.text}</span>
      <CardMarkView
        mark={findings}
        href={chip.resultRunId !== null ? reviewHref : undefined}
        extra={findings.count === null ? {} : { 'data-card-findings': findings.count }}
      />
      <CardMarkView
        mark={optimisation}
        href={optimisation.count === null ? undefined : optimisationHref}
        extra={optimisation.count === null
          ? {}
          : { 'data-card-optimisation': optimisation.count, 'data-card-optimisation-undecided': audit.optimisation_undecided_count ?? 0 }}
      />
      {chip.partial ? (
        <span className={`am-badge am-badge--degraded ${styles.mark} ${styles.partial}`} title={AUDIT_PARTIAL_TITLE}>
          <span aria-hidden="true">!</span>
          <span className={styles.hidden}>{AUDIT_PARTIAL_MARK}</span>
        </span>
      ) : null}
      {active === null ? null : runHref === undefined ? (
        <span className={activeClass} title={ACTIVE_RUN_TITLE} data-audit-active-run={active.state}>{active.text}</span>
      ) : (
        <Link href={runHref} className={activeClass} title={ACTIVE_RUN_TITLE} data-audit-active-run={active.state}>
          {active.text}
        </Link>
      )}
    </span>
  );
}
