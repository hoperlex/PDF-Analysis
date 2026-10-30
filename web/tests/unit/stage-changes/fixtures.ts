import type { StageChainRun, StageChangeCard, StageChangeJournal } from '@/shared/api';
import { NOW, uid } from '../version-compare/fixtures';

export function card(over: Partial<StageChangeCard> = {}): StageChangeCard {
  return { card_id: uid('ccd', 1), run_id: uid('crn', 1), card_key: 'a'.repeat(64), evidence_digest: 'b'.repeat(64),
    class_name: 'PROJECT_CHANGE', category: 'dimensions', title: 'Изменён размер проёма', system: 'architecture',
    evidence_ids: [uid('std', 1)], before: '900 мм', after: '1000 мм',
    evidence: [{ evidence_id: uid('std', 1), kind: 'TEXT', source_id: uid('std', 1), side: 'both', profile_id: uid('cpr', 1) }],
    carryover: 'none', carried_verdict_ids: [], stale: false, ...over };
}

export function run(over: Partial<StageChainRun> = {}): StageChainRun {
  return { run_id: uid('crn', 1), pair_id: uid('stp', 1), link_revision_id: uid('slk', 1),
    input_sha256: 'c'.repeat(64), pinned_version_uids: [uid('ver', 1)], state: 'completed',
    kind: 'full', with_ai: true, stale: false, created_at: NOW, updated_at: NOW,
    steps: [{ step_id: uid('cst', 1), step_no: 7, state: 'completed', counts: { cards: 1 } }], ...over };
}

export function journal(over: Partial<StageChangeJournal> = {}): StageChangeJournal {
  return { run_id: uid('crn', 1), grouping: 'designation', groups: [{ key: 'section', label: 'АР', rows: [card()] }],
    accepted_count: 1, ai_hidden_same_count: 2, ai_service_count: 3, stale: false, ...over };
}
