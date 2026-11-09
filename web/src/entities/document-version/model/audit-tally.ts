/**
 * The audit figures of a set of documents, as the original's section row states them (`UI-A-35`, `UI-A-36`).
 *
 * The original shows each section as a row of five numbers: not started, no expert decision, checked by the expert,
 * total, findings. Ours counts the same things over what the screen already holds, with no further request: the
 * page of `listDocuments` items (each carries its `audit`, `UI-PARITY-DOC-AUDIT`), or the project's own
 * `audit_counts` from `listProjects` / `getProject` (`UI-PARITY-P0B`). The figures are read, never derived from a
 * file name, a label or a model's wording (AGENTS §4): a document without an `audit` is counted in the total only.
 *
 * `partial` is true when the figures cover a page of a longer listing; the screen then says so beside them, as the
 * project page says it of the structure, rather than letting a page's figures pass for the whole project's.
 */

import type { DocumentAudit, DocumentAuditCounts, DocumentVersion } from '@/shared/api';

import { pluralRu } from './audit-state';

export interface AuditTally {
  /** All documents counted, with or without an audit. */
  readonly documents: number;
  /** Never run, or run only to a failure: no result run (`R-150r`). */
  readonly notRun: number;
  /** A result run with at least one finding still undecided (`R-150o`). */
  readonly awaitingDecision: number;
  /** A result run, every finding decided. */
  readonly checked: number;
  /** A result run that published no finding. */
  readonly clean: number;
  /** The findings of the result runs; `null` when the source does not carry them (the project's counters do not). */
  readonly findings: number | null;
}

export const EMPTY_TALLY: AuditTally = { documents: 0, notRun: 0, awaitingDecision: 0, checked: 0, clean: 0, findings: 0 };

/** The figures over a page of `listDocuments` items. */
export function auditTally(items: readonly Pick<DocumentVersion, 'audit'>[]): AuditTally {
  let notRun = 0;
  let awaitingDecision = 0;
  let checked = 0;
  let clean = 0;
  let findings = 0;
  for (const item of items) {
    const audit: DocumentAudit | undefined = item.audit;
    if (audit === undefined) continue;
    findings += audit.finding_count;
    switch (audit.state) {
      case 'not_run': notRun += 1; break;
      case 'awaiting_decision': awaitingDecision += 1; break;
      case 'checked': checked += 1; break;
      case 'clean': clean += 1; break;
    }
  }
  return { documents: items.length, notRun, awaitingDecision, checked, clean, findings };
}

/** The figures of the server's own counters (a project): the findings are not among them. */
export function tallyOfCounts(counts: DocumentAuditCounts): AuditTally {
  return {
    documents: counts.document_count,
    notRun: counts.not_run,
    awaitingDecision: counts.awaiting_decision,
    checked: counts.checked,
    clean: counts.clean,
    findings: null,
  };
}

export type TallyTone = 'inert' | 'failed' | 'ok';

export interface TallyPart {
  readonly key: 'documents' | 'notRun' | 'awaitingDecision' | 'checked' | 'clean' | 'findings';
  /** The words before the number. */
  readonly label: string;
  readonly count: number;
  /** `null` for the plain total, a tone for the states. */
  readonly tone: TallyTone | null;
  /** What the number counts, for the tooltip. */
  readonly title: string;
}

const DOCUMENT_WORD: readonly [string, string, string] = ['документ', 'документа', 'документов'];
const FINDING_WORD: readonly [string, string, string] = ['замечание', 'замечания', 'замечаний'];

/**
 * The parts of the line, in the original's column order: total, not started, awaiting a decision, checked, findings.
 * A state that is zero is omitted (a row of zeros says nothing), except the total, which is always the first part;
 * «без замечаний» appears only when some document has it, so the parts always add up to the total.
 */
export function tallyParts(tally: AuditTally): readonly TallyPart[] {
  const parts: TallyPart[] = [
    {
      key: 'documents',
      label: pluralRu(tally.documents, DOCUMENT_WORD),
      count: tally.documents,
      tone: null,
      title: 'Документов с текущей версией',
    },
  ];
  const add = (key: TallyPart['key'], label: string, count: number, tone: TallyTone, title: string): void => {
    if (count > 0) parts.push({ key, label, count, tone, title });
  };
  add('notRun', 'не запускались', tally.notRun, 'inert', 'Документы без результата анализа: не запускались или запуски не дали результата');
  add('awaitingDecision', 'ждут решения', tally.awaitingDecision, 'failed', 'Документы, где есть замечание без решения эксперта');
  add('checked', 'проверено', tally.checked, 'ok', 'Документы, где эксперт решил по каждому замечанию');
  add('clean', 'без замечаний', tally.clean, 'ok', 'Анализ завершён, замечаний не опубликовано');
  if (tally.findings !== null && tally.findings > 0) {
    parts.push({
      key: 'findings',
      label: pluralRu(tally.findings, FINDING_WORD),
      count: tally.findings,
      tone: null,
      title: 'Опубликованные замечания результатов анализа',
    });
  }
  return parts;
}
