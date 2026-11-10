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

import {
  SUMMARY_LABEL,
  comparisonSummary,
  profileTable,
  runScreen,
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
    expect(markup).toContain('data-profile-status="reviewed"><span class="am-badge am-badge--ok">проверен</span></td>');
    expect(markup).not.toContain('проверка человеком не проводилась');
    expect(visible(markup)).not.toMatch(REMOVED);
  });

  it('a draft still says it needs an expert review: the owner removed the label of a reviewed profile only', () => {
    expect(visible(profileTable('draft'))).toContain('черновик, требует экспертной проверки');
  });
});

/**
 * The run screen also mounts the section-analysis panel (`widgets/extended-review`, emergency analysis,
 * `af8c69f7`) on EVERY run, and while its read is pending it says
 * «Загрузка: предварительный обзор блоков…». That panel is another feature with its own wording, pinned
 * by `tests/unit/analysis-extended/*`; it is not the beta's review indication that `R-146ba` removed, and
 * the switch does not govern it. It is cut out of what this file reads, and ONLY it: the rest of each
 * screen is still held to the pattern.
 */
const EXTENDED_PANEL = /<section id="extended-analysis"[\s\S]*?<\/section>/g;
const shipped = (markup: string): string => visible(markup.replace(EXTENDED_PANEL, ''));

describe('the shipped screens carry none of the removed wording', () => {
  const SCREENS: readonly (readonly [string, () => string])[] = [
    ['a published Run with findings', () => runScreen({ state: 'published' }, 2)],
    ['a published Run with no finding', () => runScreen({ state: 'published' }, 0)],
    ['a published Run whose count is not reported', () => runScreen({ state: 'published' }, null)],
    ['a partial Run', () => runScreen({ state: 'partial' }, 0)],
    ['a queued Run', () => runScreen({ state: 'queued' }, 0)],
    ['a failed Run', () => runScreen({ state: 'failed' }, 0)],
  ];

  for (const [name, draw] of SCREENS) {
    it(`${name}`, () => {
      const text = shipped(draw());
      expect(text).not.toMatch(REMOVED);
      expect(text).not.toContain('проверка человеком не проводилась');
    });
  }

  it('can fail: the pattern does see the wording on the screen that is not the switch\'s', () => {
    // And the cut above removes the panel and nothing else: the run screen, uncut, does carry the word.
    expect(visible(runScreen({ state: 'published' }, 2))).toMatch(REMOVED);
    expect(shipped(runScreen({ state: 'published' }, 2))).not.toMatch(REMOVED);
    expect(visible(comparisonSummary())).toMatch(REMOVED);
  });
});

describe('what the shipped screens still say', () => {
  it('the label above the version-comparison summary, whatever the switch', () => {
    const text = visible(comparisonSummary());
    expect(text).toContain(SUMMARY_LABEL);
    expect(text).toContain('Сводка не заменяет и не меняет различия; проверка человеком не проводится.');
  });
});
