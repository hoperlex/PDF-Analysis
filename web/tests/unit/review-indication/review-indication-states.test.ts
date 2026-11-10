/**
 * `REVIEW-INDICATION-SWITCH-01` (`R-146ba`): every string behind `SHOW_REVIEW_INDICATION`, in each
 * state of the switch, as the markup a reader sees.
 *
 * The constant is replaced here by a value this file sets, so the cases do not depend on the beta
 * default (that is pinned, with the real constant, in `review-indication-default.test.ts`). For each
 * gated string there is one case that sets the switch ON and demands the exact words the tree had
 * before the beta, and one that sets it OFF and demands the neutral wording and the absence of the
 * old. The strings that stay, in both states, are the second half: the label above the comparison
 * summary.
 *
 * A function that ignored the switch (always on, or always off) fails one of the two cases of
 * every string; the mutation table of `docs/program/REVIEW-INDICATION-SWITCH-01.md` lists them.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

const switchState = vi.hoisted(() => ({ on: false }));

vi.mock('@/shared/config/review-indication', () => ({
  get SHOW_REVIEW_INDICATION(): boolean {
    return switchState.on;
  },
}));

import { ANALYSIS_PROFILE_STATUS_LABELS, analysisProfileStatusLabel } from '@/entities/analysis-profile';

import {
  SUMMARY_LABEL,
  comparisonSummary,
  profileTable,
  visible,
} from './surfaces';

afterEach(() => {
  switchState.on = false;
});

function render<T>(on: boolean, draw: () => T): T {
  switchState.on = on;
  return draw();
}

interface Gated {
  /** `file:line` of the string on the base tree (`docs/program/tasks/REVIEW-INDICATION-SWITCH-01.md`, P-02). */
  readonly id: string;
  readonly draw: () => string;
  /** What the base tree printed, found in the markup when the switch is ON. */
  readonly on: string;
  /** The neutral wording, found in the markup when the switch is OFF. */
  readonly off: string;
  /** Words of the old wording that must be gone when the switch is OFF (defaults to `on`). */
  readonly gone?: readonly string[];
}

const GATED: readonly Gated[] = [
  {
    id: 'presentation.ts:17 — the label of a reviewed profile',
    draw: () => profileTable('reviewed'),
    on: 'data-profile-status="reviewed"><span class="am-badge am-badge--ok">рабочая версия, проверка человеком не проводилась</span></td>',
    off: 'data-profile-status="reviewed"><span class="am-badge am-badge--ok">проверен</span></td>',
    gone: ['проверка человеком не проводилась'],
  },
];

describe('each gated string, in each state of the switch', () => {
  for (const gated of GATED) {
    it(`${gated.id}: ON prints the base tree's words`, () => {
      expect(render(true, gated.draw)).toContain(gated.on);
    });

    it(`${gated.id}: OFF prints the neutral wording and none of the old`, () => {
      const markup = render(false, gated.draw);
      expect(markup).toContain(gated.off);
      for (const old of gated.gone ?? [gated.on]) expect(markup, old).not.toContain(old);
    });
  }

  it('can fail: the table is not empty, every id is unique, and ON differs from OFF for each', () => {
    expect(GATED.length).toBeGreaterThanOrEqual(1);
    expect(new Set(GATED.map((gated) => gated.id)).size).toBe(GATED.length);
    for (const gated of GATED) {
      expect(render(true, gated.draw), gated.id).not.toBe(render(false, gated.draw));
    }
  });
});

describe('the profile status words, as functions', () => {
  it('ON: the base sentence, from the label function and from the table of labels', () => {
    switchState.on = true;
    expect(analysisProfileStatusLabel('reviewed')).toBe('рабочая версия, проверка человеком не проводилась');
    expect(ANALYSIS_PROFILE_STATUS_LABELS.reviewed).toBe('рабочая версия, проверка человеком не проводилась');
  });

  it('OFF: the contract word «проверен», which claims nothing about who', () => {
    switchState.on = false;
    expect(analysisProfileStatusLabel('reviewed')).toBe('проверен');
    expect(ANALYSIS_PROFILE_STATUS_LABELS.reviewed).toBe('проверен');
    expect(analysisProfileStatusLabel('reviewed')).not.toContain('эксперт');
    expect(analysisProfileStatusLabel('reviewed')).not.toContain('человек');
  });

  it('the label of a draft is not the switch\'s: both states', () => {
    for (const on of [true, false]) {
      switchState.on = on;
      expect(analysisProfileStatusLabel('draft')).toBe('черновик, требует экспертной проверки');
    }
  });
});

describe('what the switch does not govern, in both states', () => {
  for (const on of [true, false]) {
    const state = on ? 'ON' : 'OFF';

    it(`${state}: the label above the comparison summary and the sentence before it is asked for`, () => {
      const text = visible(render(on, comparisonSummary));
      expect(text).toContain(SUMMARY_LABEL);
      expect(text).toContain('Сводка не заменяет и не меняет различия; проверка человеком не проводится.');
    });
  }
});
