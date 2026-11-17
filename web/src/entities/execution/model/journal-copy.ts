/**
 * The text «Скопировать» puts on the clipboard from the journal (`UI-B-43`).
 *
 * It is built from the same closed projection the page draws (`visibleJournal`), never from the
 * entry itself: the event's Russian name, its time, the run, the state and the error code, and for a stage event the stage's
 * Russian name (a stage the contract's list does not hold is «Другой этап», never its raw value) and, for a progress event,
 * «стр. N из M» (`UIP-S08-01`). An unknown event is the generic «Другое событие выполнения», and the payload, the aggregate and
 * every other field of the record stay out, so what a person pastes into a message is what they
 * could read on the screen. The original's copy button joined its sections the same way: plain
 * lines, one per record, no markup.
 *
 * The time is the exact UTC stamp (`formatInstantUtc`), not the reader's local time: the text leaves the screen, and an operator
 * who checks a pasted line against a log wants the same string whatever zone each of them sits in.
 */

import type { ExecutionJournalEntry } from '@/shared/api';
import { formatInstantUtc } from '@/shared/lib';

import { journalPagesText, visibleJournal } from './presentation';

/** What the copied page is a page of: one run, or every run. */
export interface JournalCopyScope {
  /** The run the journal is narrowed to; `null` for the journal of every run. */
  readonly runId: string | null;
}

/** One record as a line: time, event, its stage and pages when it has them, run, then the state and the code when the record has them. */
export function journalCopyLine(entry: ExecutionJournalEntry): string {
  const visible = visibleJournal(entry);
  return [
    formatInstantUtc(entry.occurred_at),
    visible.event,
    ...(visible.stage === undefined ? [] : [visible.stage.label]),
    ...(visible.pages === undefined ? [] : [journalPagesText(visible.pages)]),
    `прогон ${entry.run_id}`,
    ...(visible.state === null ? [] : [`состояние: ${visible.state}`]),
    ...(visible.code === null ? [] : [`код: ${visible.code}`]),
  ].join(' · ');
}

/** The whole page: a heading that says which journal and how many records, a blank line, one line per record. */
export function journalCopyText(entries: readonly ExecutionJournalEntry[], scope: JournalCopyScope): string {
  const heading = [
    'Журнал выполнения',
    scope.runId === null ? 'все прогоны' : `прогон ${scope.runId}`,
    `записей на странице: ${entries.length}`,
  ].join(' · ');
  return [heading, '', ...entries.map(journalCopyLine)].join('\n');
}
