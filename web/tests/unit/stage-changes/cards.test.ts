import { describe, expect, it } from 'vitest';

import { editVerdict, groupedCards, rejectionReasonsMissing, verdictUpdates } from '@/widgets/stage-changes/model/cards';
import { journalGroups } from '@/widgets/stage-changes/model/journal';

import { card, journal } from './fixtures';
import { NOW, uid } from '../version-compare/fixtures';

describe('stage review drafts', () => {
  it('keeps the originally edited revision after a background refresh', () => {
    const before = card({ verdict: { verdict_id: uid('cdv', 1), card_id: card().card_id, revision_no: 3,
      decision: 'accepted', reason: '', evidence_digest: card().evidence_digest, created_at: NOW } });
    const draft = editVerdict(before, undefined, 'rejected', '  Требуется проверка  ');
    const refreshed = { ...before, verdict: { ...before.verdict!, revision_no: 4 } };
    const edited = editVerdict(refreshed, draft, 'rejected', '  Не подтверждено  ');
    expect(verdictUpdates([refreshed], { [before.card_id]: edited })).toEqual([
      { card_id: before.card_id, expected_revision: 3, decision: 'rejected', reason: 'Не подтверждено' },
    ]);
  });

  it('requires a nonblank rejection reason and ignores an unchanged saved verdict', () => {
    const value = card();
    expect(rejectionReasonsMissing(verdictUpdates([value], { [value.card_id]: editVerdict(value, undefined, 'rejected', '  ') }))).toBe(true);
    const accepted = card({ verdict: { verdict_id: uid('cdv', 1), card_id: value.card_id, revision_no: 1,
      decision: 'accepted', reason: '', evidence_digest: value.evidence_digest, created_at: NOW } });
    expect(verdictUpdates([accepted], { [accepted.card_id]: editVerdict(accepted, undefined, 'accepted', '') })).toEqual([]);
  });

  it('uses explicit classes/categories without inferring importance from the title', () => {
    const sections = groupedCards([card({ class_name: 'SERVICE_STRUCTURE', title: 'Очень важное изменение' }),
      card({ card_id: uid('ccd', 2), class_name: 'REVIEW' }), card({ card_id: uid('ccd', 3) })]);
    expect(sections.map((section) => [section.className, section.collapsed])).toEqual([
      ['PROJECT_CHANGE', false], ['REVIEW', false], ['SERVICE_STRUCTURE', true],
    ]);
    const service = card({ class_name: 'SERVICE_STRUCTURE' });
    expect(verdictUpdates([service], { [service.card_id]: editVerdict(service, undefined, 'accepted') })).toEqual([]);
  });
});

describe('stage journal runtime shape', () => {
  it('retains the server grouping and rows', () => {
    expect(journalGroups(journal())).toEqual([{ key: 'section', label: 'АР', rows: [card()] }]);
  });
  it('refuses malformed groups and prototype names rather than showing an empty journal', () => {
    expect(() => journalGroups(journal({ groups: [{ key: 'x', label: 'АР', rows: [null] }] }))).toThrow();
    expect(() => journalGroups(journal({ groups: [{ key: 'x', label: 'АР', rows: [{ ...card(), class_name: 'constructor' }] }] }))).toThrow();
  });
});
