/**
 * `PREC-WEB`: the neutral label in the row, the collapsed queue «Рекомендовано снять», and the one line above the list.
 *
 * Each case can fail: the mutations in `.local/evidence/lane-prec-web/mutations.txt` break the code under each one and show the case red.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => null,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

import { precedentCaption, isCancelSuggested, precedentsUnavailableLine } from '@/entities/decision-memory';

import { label, navigation, reviewPage, runPrecedents, textFinding, uidOf, vectorControl } from './precedents-fixtures';

afterEach(() => {
  navigation.search = '';
});

const A = textFinding('C1', 'Не указан предел огнестойкости перекрытия.');
const B = textFinding('C2', 'Ширина помещения на плане не совпадает с экспликацией.');
const C = textFinding('C3', 'В штампе осталась заглушка вместо шифра.');
const D = textFinding('C4', 'Отметка пола на разрезе не совпадает с планом.', { current_verdict: 'rejected' });
const EXPERT = ['expert'];

describe('the caption of a label', () => {
  it('says the plan’s words for each label, and nothing for few and none', () => {
    const cases: Array<[string, string | null]> = [
      [precedentCaption(label('x', 'often_rejected')) ?? '', 'Обычно отклоняют · 8 из 10'],
      [precedentCaption(label('x', 'cancel_suggested', { votes: { total: 7, rejected: 7, accepted: 0, independent: 7, projects: 3 } })) ?? '', 'Рекомендуется снять · 7 из 7'],
      [precedentCaption(label('x', 'likely_accepted', { votes: { total: 7, rejected: 1, accepted: 6, independent: 7, projects: 3 } })) ?? '', 'Обычно принимают · 6 из 7'],
      [precedentCaption(label('x', 'mixed', { votes: { total: 5, rejected: 2, accepted: 3, independent: 5, projects: 2 } })) ?? '', 'Решения расходятся · 3 ✓ / 2 ✕'],
    ];
    for (const [got, want] of cases) expect(got).toBe(want);
    expect(precedentCaption(label('x', 'few'))).toBeNull();
    expect(precedentCaption(label('x', 'none'))).toBeNull();
  });

  it('shows a rejection label of a finding the critic did not review neutrally', () => {
    for (const code of ['often_rejected', 'cancel_suggested'] as const) {
      expect(precedentCaption(label('x', code, { critic_reviewed: false }))).toBe('Прецедентов: 10 (критик не разбирал)');
    }
    // the acceptance and the split are not rejections: the critic's review does not change them
    expect(precedentCaption(label('x', 'likely_accepted', { critic_reviewed: false }))).toBe('Обычно принимают · 2 из 10');
  });

  it('puts only a reviewed cancel_suggested in the queue', () => {
    expect(isCancelSuggested(label('x', 'cancel_suggested'))).toBe(true);
    expect(isCancelSuggested(label('x', 'cancel_suggested', { critic_reviewed: false }))).toBe(false);
    expect(isCancelSuggested(label('x', 'often_rejected'))).toBe(false);
    expect(isCancelSuggested(undefined)).toBe(false);
  });
});

describe('the label in the row', () => {
  const precedents = runPrecedents([label(A.finding_uid, 'often_rejected'), label(B.finding_uid, 'mixed', { votes: { total: 5, rejected: 2, accepted: 3, independent: 5, projects: 2 } }), label(C.finding_uid, 'few', { votes: { total: 3, rejected: 3, accepted: 0, independent: 3, projects: 1 } })]);

  it('draws the neutral label on the rows that have one and nothing on a few', () => {
    const markup = reviewPage({ findings: [A, B, C], roles: EXPERT, precedents });
    expect(markup).toContain('data-precedent-label="often_rejected"');
    expect(markup).toContain('Обычно отклоняют · 8 из 10');
    expect(markup).toContain('data-precedent-label="mixed"');
    expect(markup).toContain('Решения расходятся · 3 ✓ / 2 ✕');
    expect(markup).not.toContain('data-precedent-label="few"');
    expect((markup.match(/data-precedent-label=/g) ?? []).length).toBe(2);
  });

  it('draws the label in the table’s cell too', () => {
    const markup = reviewPage({ findings: [A, B, C], roles: EXPERT, precedents, search: 'view=table' });
    expect(markup).toContain('data-finding-table');
    expect((markup.match(/data-precedent-label=/g) ?? []).length).toBe(2);
  });

  it('keeps a row’s two controls and adds no third', () => {
    const markup = reviewPage({ findings: [A], roles: EXPERT, precedents });
    const row = markup.match(/<li[^>]*data-verdict-bucket[\s\S]*?<\/li>/)?.[0] ?? '';
    expect((row.match(/<button/g) ?? []).length).toBe(3); // the row itself, ✓ and ✕: the label is not a control
    expect(row).not.toMatch(/<button[^>]*>[^<]*(<[^>]+>[^<]*)*Обычно отклоняют/);
  });
});

describe('no «Недоступно» in a row', () => {
  it('draws no mark and no word «Недоступно» on any row while the precedents are not there', () => {
    const markup = reviewPage({ findings: [A, B], roles: EXPERT, precedents: runPrecedents([], { available: false }), control: vectorControl({ start: '01:00', end: '06:00', tz: 'Asia/Yekaterinburg' }) });
    expect(markup).not.toContain('Недоступно');
    expect(markup).not.toContain('data-precedent-label');
    const rows = markup.match(/<li[^>]*data-verdict-bucket[\s\S]*?<\/li>/g) ?? [];
    expect(rows.length).toBe(2);
    for (const row of rows) expect(row).not.toContain('Прецедент');
  });
});

describe('the queue «Рекомендовано снять»', () => {
  const precedents = runPrecedents([
    label(A.finding_uid, 'cancel_suggested', { votes: { total: 7, rejected: 7, accepted: 0, independent: 7, projects: 3 } }),
    label(B.finding_uid, 'cancel_suggested'),
    label(C.finding_uid, 'cancel_suggested', { critic_reviewed: false }),
    label(D.finding_uid, 'cancel_suggested'),
  ]);

  it('is collapsed above the list with its count and lists the waiting reviewed findings, each a link to its finding', () => {
    const markup = reviewPage({ findings: [A, B, C, D], roles: EXPERT, precedents });
    expect(markup).toContain('data-cancel-queue="2"');
    expect(markup).toContain('Рекомендовано снять · 2');
    expect(markup).not.toMatch(/<details[^>]*data-cancel-queue[^>]*\sopen/);
    expect(markup).toContain(`href="?finding=${encodeURIComponent(A.finding_uid)}"`);
    expect(markup).toContain(`data-cancel-queue-item="${B.finding_uid}"`);
    // not the finding the critic did not review (neutral), not the one already decided
    expect(markup).not.toContain(`data-cancel-queue-item="${C.finding_uid}"`);
    expect(markup).not.toContain(`data-cancel-queue-item="${D.finding_uid}"`);
    expect(markup.indexOf('data-cancel-queue=')).toBeLessThan(markup.indexOf('am-finding-group'));
  });

  it('is empty when only neutral labels exist', () => {
    const neutral = runPrecedents([label(A.finding_uid, 'often_rejected'), label(B.finding_uid, 'mixed'), label(C.finding_uid, 'likely_accepted')]);
    const markup = reviewPage({ findings: [A, B, C], roles: EXPERT, precedents: neutral });
    expect(markup).not.toContain('data-cancel-queue');
    expect(markup).not.toContain('Рекомендовано снять');
  });

  it('is empty when a filter hides the findings that wait for a decision', () => {
    expect(reviewPage({ findings: [A, B, D], roles: EXPERT, precedents, search: 'verdict=waiting' })).toContain('data-cancel-queue="2"');
    for (const search of ['verdict=accepted', 'verdict=rejected']) {
      expect(reviewPage({ findings: [A, B, D], roles: EXPERT, precedents, search })).not.toContain('data-cancel-queue');
    }
  });

  it('is not drawn for a session that may not read the precedents', () => {
    expect(reviewPage({ findings: [A, B], roles: ['viewer'], precedents })).not.toContain('data-cancel-queue');
    expect(reviewPage({ findings: [A, B], precedents })).not.toContain('data-cancel-queue');
  });
});

describe('the line above the list', () => {
  const WINDOW = { start: '23:30', end: '05:45', tz: 'Europe/Moscow' };

  it('says the night and takes the hours and the zone from the setting', () => {
    const markup = reviewPage({ findings: [A, B], roles: EXPERT, precedents: runPrecedents([], { available: false }), control: vectorControl(WINDOW) });
    expect(markup).toContain('data-precedents-line');
    expect(markup).toContain('Прецеденты считаются ночью (23:30–05:45, Europe/Moscow) и появятся утром; после переезда в Яндекс — сразу после прогона');
    expect(markup).not.toContain('01:00');
    expect(precedentsUnavailableLine({ start: '02:15', end: '04:00', tz: 'Asia/Omsk' })).toContain('(02:15–04:00, Asia/Omsk)');
  });

  it('invents no hours when the window is not known', () => {
    expect(precedentsUnavailableLine(null)).toBe('Прецеденты считаются ночью и появятся утром; после переезда в Яндекс — сразу после прогона');
  });

  it('is drawn once over the list and is gone when the precedents are there', () => {
    const away = reviewPage({ findings: [A, B], roles: EXPERT, precedents: runPrecedents([], { available: false }), control: vectorControl(WINDOW) });
    expect((away.match(/data-precedents-line/g) ?? []).length).toBe(1);
    expect(away.indexOf('data-precedents-line')).toBeLessThan(away.indexOf('am-finding-list'));
    const there = reviewPage({ findings: [A, B], roles: EXPERT, precedents: runPrecedents([label(A.finding_uid, 'often_rejected')]), control: vectorControl(WINDOW) });
    expect(there).not.toContain('data-precedents-line');
  });

  it('is not drawn for a viewer', () => {
    expect(reviewPage({ findings: [A], roles: ['viewer'], precedents: runPrecedents([], { available: false }), control: vectorControl(WINDOW) })).not.toContain('data-precedents-line');
  });

  it('is not drawn for a run with no findings', () => {
    expect(reviewPage({ findings: [], roles: EXPERT, precedents: runPrecedents([], { available: false }), control: vectorControl(WINDOW) })).not.toContain('data-precedents-line');
  });
});

void uidOf;
