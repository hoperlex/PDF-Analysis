/**
 * `REVIEW-INDICATION-SWITCH-01` (`R-146ba`, accepted risks `A-10`, `A-11`): the beta default of the
 * switch, with the REAL constant, and what the shipped screens say.
 *
 * Nothing here replaces `SHOW_REVIEW_INDICATION`. It is the one test that names the default, so
 * changing the value in `web/src/shared/config/review-indication.ts` turns this file red on purpose:
 * to restore the wording, set the constant to `true` and change the first case of this file in the
 * same commit. The other half of the proof - every string, in each state - is
 * `review-indication-states.test.ts`, which sets the value itself.
 */

import { describe, expect, it } from 'vitest';

import { analysisProfileStatusLabel } from '@/entities/analysis-profile';
import { SHOW_REVIEW_INDICATION } from '@/shared/config';
import { SHOW_REVIEW_INDICATION as FROM_THE_MODULE } from '@/shared/config/review-indication';
import { ATTESTATION_SENTENCE } from '@/widgets/ar-v3-beta-pack';

import {
  SUMMARY_LABEL,
  betaStatus,
  comparisonSummary,
  groupLookup,
  groupReview,
  packPanel,
  profileTable,
  startControl,
  v3Run,
  visible,
} from './surfaces';

/** The wording the owner took off the screens, as the pattern the static guard uses. */
const REMOVED = /предварительн|проверк\p{L}*\s+(?:эксперт|человек)|экспертн\p{L}*\s+проверк/iu;

describe('the beta default', () => {
  it('is OFF: the beta shows neither indication', () => {
    expect(SHOW_REVIEW_INDICATION).toBe(false);
    expect(FROM_THE_MODULE).toBe(false);
  });

  it('the profile status «reviewed» shows the contract word, which claims nothing about who', () => {
    expect(analysisProfileStatusLabel('reviewed')).toBe('проверен');
    const markup = profileTable('reviewed');
    expect(markup).toContain('data-profile-status="reviewed">проверен</td>');
    expect(markup).not.toContain('проверка человеком не проводилась');
    expect(visible(markup)).not.toMatch(REMOVED);
  });

  it('a draft still says it needs an expert review: the owner removed the label of a reviewed profile only', () => {
    expect(visible(profileTable('draft'))).toContain('черновик, требует экспертной проверки');
  });
});

describe('the shipped screens carry none of the removed wording', () => {
  const SCREENS: readonly (readonly [string, () => string])[] = [
    ['the group review, for an expert', () => groupReview({ roles: ['expert'] })],
    ['the group review, for an administrator', () => groupReview({ roles: ['admin'] })],
    ['the group lookup', () => groupLookup()],
    ['the beta source preview', () => betaStatus()],
    ['the control that starts the six checks', () => startControl()],
    ['a published AR v3 Run with findings', () => v3Run('published', 2)],
    ['a published AR v3 Run with no finding', () => v3Run('published', 0)],
    ['a published AR v3 Run whose count is not reported', () => v3Run('published', null)],
    ['a partial AR v3 Run', () => v3Run('partial', 0)],
    ['a queued AR v3 Run', () => v3Run('queued', 0)],
    ['a failed AR v3 Run', () => v3Run('failed', 0)],
  ];

  for (const [name, draw] of SCREENS) {
    it(`${name}`, () => {
      const text = visible(draw());
      expect(text).not.toMatch(REMOVED);
      expect(text).not.toContain('проверка человеком не проводилась');
    });
  }

  it('can fail: the pattern does see the wording on the screen that is not the switch\'s', () => {
    expect(visible(packPanel())).toMatch(REMOVED);
    expect(visible(comparisonSummary())).toMatch(REMOVED);
  });
});

describe('what the shipped screens still say', () => {
  it('the label above the version-comparison summary, whatever the switch', () => {
    const text = visible(comparisonSummary());
    expect(text).toContain(SUMMARY_LABEL);
    expect(text).toContain('Сводка не заменяет и не меняет различия; проверка человеком не проводится.');
  });

  it('the attestation record of the sealed pack', () => {
    const text = visible(packPanel());
    expect(text).toContain(ATTESTATION_SENTENCE);
    expect(text).toContain('Запись рецензента приложена при установке пакета; система её не проверяет');
  });

  it('that a verdict is the expert\'s own decision, and the limit on numbers', () => {
    const expert = visible(groupReview({ roles: ['expert'] }));
    expect(expert).toContain('Находки и решения эксперта');
    expect(expert).toContain('Формулировка модели, не решение эксперта.');
    expect(expert).toContain('Числовой или правовой вывод здесь не утверждён.');
    expect(visible(groupReview({ roles: ['admin'] }))).toContain('Решение записывает эксперт.');
    expect(visible(v3Run('published', 2))).toContain('решение по каждой записывает эксперт');
  });

  it('a published AR v3 Run that published findings no longer says that none is published', () => {
    const published = visible(v3Run('published', 2));
    expect(published).toContain('Находки с нормативными ссылками опубликованы');
    expect(published).not.toContain('Канонические находки здесь не публикуются');
    const none = visible(v3Run('published', 0));
    expect(none).toContain('Канонические находки здесь не публикуются.');
    expect(none).not.toContain('опубликованы; решение');
  });
});
