/**
 * A document's audit state as the screens say it (`UI-PARITY-DOC-AUDIT`, contract 1.34.0; register rows `UI-A-46`,
 * `UI-A-49`, `UI-A-38`).
 *
 * **Where the state comes from.** `listDocuments` carries `audit` on each item (`DocumentAudit`): one of four words,
 * `not_run`, `clean`, `awaiting_decision` or `checked`, the `partial` flag beside it, and the figures of the result
 * run. The server decides every one of them (the same read the counters of `listProjects` and of the section panel
 * are tallies of), so nothing here classifies a document; this module only names what it was told. A document whose
 * answer carries no `audit` (every operation but `listDocuments`) gets no chip, never an invented «Не запускался».
 *
 * **Where the order comes from.** The server (`order=audit`): checked by the expert, then processed and without
 * every verdict, then never audited, by name within each group. A screen asks for it and draws the page as it came;
 * there is no client sort here, because a sort of one page would order a section differently on every page.
 *
 * **The «не запускались» filter** is `audit_state=not_run` at the server and `?filter=not_run` in the address of the
 * section page, so a link from the dashboard's section panel lands on the narrowed list and the reader can see what
 * the number counted. Any other value of `filter` is no filter: the page shows the whole section.
 */

import type { DocumentAudit, DocumentVersion } from '@/shared/api';
import { routes } from '@/shared/lib';
import { STATE_LABELS } from '@/shared/ui';

export type AuditStateCode = DocumentAudit['state'];

/** The four states, in the order the counters list them. */
export const AUDIT_STATE_CODES: readonly AuditStateCode[] = ['not_run', 'clean', 'awaiting_decision', 'checked'];

/** A tone of the design system's badge (`.am-badge--*`): the colour is the global rule's, measured by the census. */
export type AuditChipTone = 'inert' | 'ok' | 'failed' | 'pending';

export interface AuditChip {
  readonly state: AuditStateCode;
  /** The chip's text. */
  readonly text: string;
  readonly tone: AuditChipTone;
  /** The figures of the result run, for a tooltip; `null` while there is no result run. */
  readonly detail: string | null;
  /** The result run «Разбор» opens, or `null` while the document was never run. */
  readonly resultRunId: string | null;
  /** `R-150s`: the result run is partial; the screen adds the mark «частично» beside the chip. */
  readonly partial: boolean;
}

/** The mark beside a chip whose result run was partial (`R-150s`). */
export const AUDIT_PARTIAL_MARK = 'частично';

export const AUDIT_PARTIAL_TITLE = 'Результат неполный: часть анализа не завершилась.';

const FINDINGS_WORD: readonly [string, string, string] = ['замечание', 'замечания', 'замечаний'];

/** The Russian plural of a count: 1 замечание, 2 замечания, 5 замечаний (11 to 14 take the third form). */
export function pluralRu(count: number, forms: readonly [string, string, string]): string {
  const whole = Math.abs(Math.trunc(count));
  const lastTwo = whole % 100;
  const last = whole % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return forms[2];
  if (last === 1) return forms[0];
  if (last >= 2 && last <= 4) return forms[1];
  return forms[2];
}

function findingsDetail(audit: DocumentAudit): string {
  const total = `${audit.finding_count} ${pluralRu(audit.finding_count, FINDINGS_WORD)}`;
  return audit.undecided_finding_count === 0
    ? total
    : `${total}, без решения эксперта: ${audit.undecided_finding_count}`;
}

/** The chip of one document, or `null` when its answer carried no audit. */
export function auditChip(audit: DocumentAudit | undefined): AuditChip | null {
  if (audit === undefined) return null;
  const resultRunId = audit.result_run_id ?? null;
  const base = { state: audit.state, resultRunId, partial: audit.partial } as const;
  switch (audit.state) {
    case 'not_run':
      return { ...base, text: 'Не запускался', tone: 'inert', detail: null };
    case 'clean':
      return { ...base, text: 'Замечаний нет', tone: 'ok', detail: 'Анализ завершён, замечаний не опубликовано.' };
    case 'awaiting_decision':
      return {
        ...base,
        text: `Ждёт решения: ${audit.undecided_finding_count}`,
        tone: 'failed',
        detail: findingsDetail(audit),
      };
    case 'checked':
      return { ...base, text: 'Проверен экспертом', tone: 'ok', detail: findingsDetail(audit) };
  }
}

// ---- the run in flight (`UI-A-47`, contract 1.40.0) -----------------------------------------------------------

/** The three states of a run that is in flight: waiting for an executor, being worked on, being validated. */
export type ActiveRunState = NonNullable<DocumentAudit['active_run']>['state'];

export const ACTIVE_RUN_LABEL = 'Идёт аудит';

export const ACTIVE_RUN_TITLE =
  'Прогон этого документа ещё не закончен. Состояние аудита слева не меняется, пока прогон не опубликован; ход прогона — на его странице.';

/** The mark of a document whose current version has a run in flight, beside its audit chip. */
export interface ActiveRunMark {
  readonly runId: string;
  readonly state: ActiveRunState;
  /** «Идёт аудит: в очереди» -- the run's state in the product's own words for it (`STATE_LABELS`). */
  readonly text: string;
}

/**
 * The mark, or `null` when the answer carried no audit or the server named no run in flight. It is a fact beside the four
 * states: it never replaces the chip and never changes it. The server reads it in the statement that reads the audit, and
 * only for the standard analysis; there is no progress figure to show (the run reports its stages, on its own page).
 */
export function activeRunMark(audit: DocumentAudit | undefined): ActiveRunMark | null {
  const run = audit?.active_run;
  if (run === undefined) return null;
  return { runId: run.run_id, state: run.state, text: `${ACTIVE_RUN_LABEL}: ${STATE_LABELS[run.state]}` };
}

/** The run page of the run in flight, or `undefined` when there is none. The project is the version's own. */
export function activeRunHref(version: Pick<DocumentVersion, 'project_uid' | 'audit'>): string | undefined {
  const run = version.audit?.active_run;
  return run === undefined ? undefined : routes.run(version.project_uid, run.run_id);
}

/** The audit state of a document, or `null` when its answer carried none. */
export function auditStateOf(version: Pick<DocumentVersion, 'audit'>): AuditStateCode | null {
  return version.audit?.state ?? null;
}

// ---- the «не запускались» filter of the section page ---------------------------------------------------------

/** The one filter the address of a section page carries: the documents that were never analysed. */
export type SectionAuditFilter = 'not_run';

/** The query parameter, in the address of the section page. */
export const SECTION_FILTER_PARAM = 'filter';

/** `?filter=not_run` → `'not_run'`; anything else, repeated or absent → no filter. */
export function parseSectionAuditFilter(value: string | readonly string[] | null | undefined): SectionAuditFilter | null {
  return value === 'not_run' ? 'not_run' : null;
}

/** The address of a section page narrowed to the documents that were never analysed. */
export function withNotRunFilter(sectionHref: string): string {
  return `${sectionHref}?${SECTION_FILTER_PARAM}=not_run`;
}

/**
 * The sentence over a narrowed list: it says what the list is. The count is the documents shown; when the list goes on
 * past this page the sentence says it is this page's, so a reader never takes a page for the whole.
 */
export function notRunFilterSentence(count: number, wholeList: boolean): string {
  const base = `Показаны документы, которые не анализировались: ${count}`;
  return wholeList ? base : `${base} на этой странице`;
}

export const NOT_RUN_EMPTY_TITLE = 'В этом разделе нет документов, которые не анализировались.';

export const SHOW_ALL_LABEL = 'Показать все';
