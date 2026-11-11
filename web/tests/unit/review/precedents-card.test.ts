/**
 * `PREC-WEB`: the «Прецеденты» block on the card of an open finding: the label, at most two hints, the similar cases with their latest comment,
 * «Возможные нормы»; collapsed; nothing when there is nothing to say; nothing for a session that may not read them.
 */

import { createElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => null,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

import { PrecedentsCardView } from '@/_pages/review/ui/precedents-card';

import { cardOf, label, navigation, reviewPage, runPrecedents, textFinding } from './precedents-fixtures';
import { render } from './fixtures';

afterEach(() => {
  navigation.search = '';
});

const A = textFinding('D1', 'Не указан предел огнестойкости перекрытия.');
const norm = (n: number) => ({ clause_number: `5.${n}`, designation: `СП 2.13130.2020`, norm_document_id: `ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}A`, norm_paragraph_id: `npar_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}B`, page_label: 10 + n });
const kase = (n: number, verdict: 'accepted' | 'rejected', comment?: string) => ({
  case_id: `dmc_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}C`, category: 'documentation', finding_text: `Похожая находка номер ${n}`, similarity: 0.9 - n / 100, verdict, ...(comment === undefined ? {} : { comment }),
});

const FULL = cardOf(A.finding_uid, {
  label: label(A.finding_uid, 'often_rejected', { hint_codes: ['p1'] }),
  hints: [
    { code: 'p1', text: 'Предел указан в общих данных', case_id: kase(1, 'rejected').case_id },
    { code: 'p4' },
    { code: 'p5', case_id: kase(2, 'accepted').case_id },
  ],
  cases: [kase(1, 'rejected', 'Предел указан в общих данных'), kase(2, 'accepted')],
  possible_norms: [norm(1), norm(2)],
});

describe('the block', () => {
  it('is collapsed, says «Прецеденты» and the label in its summary, and shows at most two hints', () => {
    const markup = render(createElement(PrecedentsCardView, { data: FULL }));
    expect(markup).toContain('data-precedents-card');
    expect(markup).not.toMatch(/<details[^>]*\sopen/);
    expect(markup).toMatch(/<summary[^>]*><strong>Прецеденты<\/strong>[^]*Обычно отклоняют · 8 из 10/);
    expect((markup.match(/data-precedent-hint=/g) ?? []).length).toBe(2);
    expect(markup).toContain('Причина отказов: «Предел указан в общих данных»');
    expect(markup).not.toContain('data-precedent-hint="p5"');
  });

  it('lists the similar cases with their verdict, similarity and latest comment, and the possible norms with clause and page', () => {
    const markup = render(createElement(PrecedentsCardView, { data: FULL }));
    expect((markup.match(/data-precedent-case=/g) ?? []).length).toBe(2);
    expect(markup).toContain('✕ отклонено · сходство 89 %');
    expect(markup).toContain('✓ принято · сходство 88 %');
    expect(markup).toContain('<q');
    expect(markup).toContain('Предел указан в общих данных');
    expect(markup).toContain('Возможные нормы');
    expect(markup).toContain('СП 2.13130.2020');
    expect(markup).toContain('п. 5.1');
    expect(markup).toContain('стр. 12');
  });

  it('shows a comment as text, never as markup', () => {
    const data = cardOf(A.finding_uid, { cases: [kase(1, 'rejected', '<img src=x onerror=alert(1)>')] });
    const markup = render(createElement(PrecedentsCardView, { data }));
    expect(markup).not.toContain('<img');
    expect(markup).toContain('&lt;img');
  });

  it('draws nothing when there is no label, no hint, no case and no norm, and a few label alone says nothing', () => {
    expect(render(createElement(PrecedentsCardView, { data: cardOf(A.finding_uid) }))).toBe('');
    expect(render(createElement(PrecedentsCardView, { data: cardOf(A.finding_uid, { label: label(A.finding_uid, 'few') }) }))).toBe('');
  });

  it('draws a norms-only block when the finding has no precedents yet', () => {
    const markup = render(createElement(PrecedentsCardView, { data: cardOf(A.finding_uid, { available: false, possible_norms: [norm(3)] }) }));
    expect(markup).toContain('Возможные нормы');
    expect(markup).toContain('возможных норм 1');
    expect(markup).not.toContain('Похожие случаи');
  });

  it('says the neutral label of a finding the critic did not review', () => {
    const data = cardOf(A.finding_uid, { label: label(A.finding_uid, 'cancel_suggested', { critic_reviewed: false }) });
    expect(render(createElement(PrecedentsCardView, { data }))).toContain('Прецедентов: 10 (критик не разбирал)');
  });
});

describe('on the screen', () => {
  const precedents = runPrecedents([label(A.finding_uid, 'often_rejected')]);

  it('stands under the open finding for an expert', () => {
    const markup = reviewPage({ findings: [A], roles: ['expert'], precedents, card: FULL });
    expect(markup).toContain(`data-precedents-card="${A.finding_uid}"`);
    expect(markup.indexOf('data-precedents-card')).toBeGreaterThan(markup.indexOf('am-review__recommendation'));
  });

  it('is not drawn for a viewer, nor while the account is not known', () => {
    expect(reviewPage({ findings: [A], roles: ['viewer'], precedents, card: FULL })).not.toContain('data-precedents-card');
    expect(reviewPage({ findings: [A], precedents, card: FULL })).not.toContain('data-precedents-card');
  });
});
