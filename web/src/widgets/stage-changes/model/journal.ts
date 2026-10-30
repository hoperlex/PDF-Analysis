import type { StageChangeCard, StageChangeJournal } from '@/shared/api';
import { CATEGORY_WORDS, CLASS_WORDS, SYSTEM_WORDS } from './cards';

export interface JournalGroup {
  readonly key: string;
  readonly label: string;
  readonly rows: readonly StageChangeCard[];
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function evidence(value: unknown): boolean {
  return record(value) && ['evidence_id', 'source_id'].every((key) => typeof value[key] === 'string')
    && ['TEXT', 'TABLE', 'GRAPHIC'].includes(String(value.kind)) && ['left', 'right', 'both'].includes(String(value.side))
    && (value.profile_id === undefined || typeof value.profile_id === 'string')
    && (value.absence_proven === undefined || typeof value.absence_proven === 'boolean');
}

function verdict(value: unknown): boolean {
  return record(value) && ['verdict_id', 'card_id', 'reason', 'evidence_digest', 'created_at'].every((key) => typeof value[key] === 'string')
    && (value.decision === 'accepted' || value.decision === 'rejected')
    && typeof value.revision_no === 'number' && Number.isInteger(value.revision_no) && value.revision_no >= 1;
}

function card(value: unknown): value is StageChangeCard {
  return record(value) && ['card_id', 'card_key', 'run_id', 'title', 'before', 'after', 'evidence_digest'].every((key) => typeof value[key] === 'string')
    && typeof value.stale === 'boolean' && Array.isArray(value.evidence_ids) && value.evidence_ids.every((id) => typeof id === 'string')
    && typeof value.class_name === 'string' && Object.hasOwn(CLASS_WORDS, value.class_name)
    && typeof value.category === 'string' && Object.hasOwn(CATEGORY_WORDS, value.category)
    && typeof value.system === 'string' && Object.hasOwn(SYSTEM_WORDS, value.system)
    && (value.evidence === undefined || (Array.isArray(value.evidence) && value.evidence.every(evidence)))
    && (value.verdict === undefined || verdict(value.verdict));
}

/** C4 runtime's explicit journal group shape; malformed groups are never an empty journal. */
export function journalGroups(journal: StageChangeJournal): JournalGroup[] {
  return journal.groups.map((group) => {
    if (typeof group.key !== 'string' || typeof group.label !== 'string'
        || !Array.isArray(group.rows) || !group.rows.every(card)) {
      throw new Error('Журнал не открылся. Обновите сравнение и повторите запрос.');
    }
    return { key: group.key, label: group.label, rows: group.rows };
  });
}
