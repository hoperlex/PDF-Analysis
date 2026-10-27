/**
 * `REVIEW-INDICATION-SWITCH-01` (`R-146ba`): every string behind `SHOW_REVIEW_INDICATION`, in each
 * state of the switch, as the markup a reader sees.
 *
 * The constant is replaced here by a value this file sets, so the cases do not depend on the beta
 * default (that is pinned, with the real constant, in `review-indication-default.test.ts`). For each
 * gated string there is one case that sets the switch ON and demands the exact words the tree had
 * before the beta, and one that sets it OFF and demands the neutral wording and the absence of the
 * old. The strings that stay, in both states, are the second half: the label above the comparison
 * summary, the attestation of the sealed pack, and every statement that a verdict is the expert's.
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

import { ATTESTATION_SENTENCE } from '@/widgets/ar-v3-beta-pack';
import { ANALYSIS_PROFILE_STATUS_LABELS, analysisProfileStatusLabel } from '@/entities/analysis-profile';

import type { AvailableReview } from './surfaces';
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

const withContextOnlyTopic = (review: AvailableReview): void => {
  review.topics.push({
    item_id: 'C05', mode: 'context_only', reason: 'edition check', source_ids: ['D6_LOCAL'], review_status: 'requires_expert_review',
    provisional_citation_count: 0,
  });
};

const withoutCitations = (review: AvailableReview): void => {
  review.provisional_citations = [];
};

const GATED: readonly Gated[] = [
  {
    id: 'presentation.ts:17 — the label of a reviewed profile',
    draw: () => profileTable('reviewed'),
    on: 'data-profile-status="reviewed">рабочая версия, проверка человеком не проводилась</td>',
    off: 'data-profile-status="reviewed">проверен</td>',
    gone: ['проверка человеком не проводилась'],
  },
  {
    id: 'ar-v3-beta-review.tsx:33 — the state of an available scope',
    draw: () => groupReview(),
    on: 'F1 — Предварительный разбор доступен</summary>',
    off: 'F1 — Разбор доступен</summary>',
    gone: ['Предварительный разбор доступен'],
  },
  {
    id: 'ar-v3-beta-review.tsx:39 — the mode of a topic that may be cited',
    draw: () => groupReview(),
    on: 'C01</strong> — Предварительная ссылка',
    off: 'C01</strong> — Ссылка на норму.',
    gone: ['Предварительная ссылка'],
  },
  {
    id: 'ar-v3-beta-review.tsx:59 — the notice above the topics',
    draw: () => groupReview(),
    on: '<p><strong>Только предварительные ссылки.</strong> Каждая тема и цитата требует проверки эксперта. Числовой или правовой вывод здесь не утверждён.</p>',
    off: '<p>Числовой или правовой вывод здесь не утверждён.</p>',
    gone: ['Только предварительные ссылки', 'Каждая тема и цитата требует проверки эксперта'],
  },
  {
    id: 'ar-v3-beta-review.tsx:64 — the sentence after each topic',
    draw: () => groupReview({ edit: withContextOnlyTopic }),
    on: 'C05</strong> — Только контекст; требует проверки эксперта.',
    off: 'C05</strong> — Только контекст.',
    gone: ['требует проверки эксперта'],
  },
  {
    id: 'ar-v3-beta-review.tsx:70 — the heading of the citations',
    draw: () => groupReview(),
    on: '<h3>Предварительные цитаты</h3>',
    off: '<h3>Цитаты</h3>',
    gone: ['Предварительные цитаты'],
  },
  {
    id: 'ar-v3-beta-review.tsx:71 — no citations',
    draw: () => groupReview({ edit: withoutCitations }),
    on: '<p>Предварительных цитат нет.</p>',
    off: '<p>Цитат нет.</p>',
    gone: ['Предварительных цитат нет'],
  },
  {
    id: 'ar-v3-beta-review.tsx:75 — the sentence on each proposal',
    draw: () => groupReview(),
    on: '<p>Предложение 1; требуется проверка эксперта.</p>',
    off: '<p>Предложение 1.</p>',
    gone: ['требуется проверка эксперта'],
  },
  {
    id: 'ar-v3-beta-review.tsx:113 — the sentence above the group lookup',
    draw: () => groupLookup(),
    on: 'Здесь видны все шесть прогонов и только предварительные нормативные ссылки.',
    off: 'Здесь видны все шесть прогонов и нормативные ссылки.',
    gone: ['только предварительные нормативные ссылки'],
  },
  {
    id: 'ar-v3-beta-status.tsx:30 — a topic that may be cited',
    draw: () => betaStatus(),
    on: '<span>Предварительная ссылка — требуется проверка эксперта</span>',
    off: '<span>Ссылка на норму</span>',
    gone: ['Предварительная ссылка'],
  },
  {
    id: 'ar-v3-beta-status.tsx:31 — a context-only topic',
    draw: () => betaStatus(),
    on: '<span>Только контекст — требуется проверка эксперта</span>',
    off: '<span>Только контекст</span>',
    gone: ['Только контекст — требуется проверка эксперта'],
  },
  {
    id: 'ar-v3-beta-status.tsx:39 — the title of the map',
    draw: () => betaStatus(),
    on: '>АР v3: предварительная карта норм</h2>',
    off: '>АР v3: карта норм</h2>',
    gone: ['предварительная карта норм'],
  },
  {
    id: 'ar-v3-beta-status.tsx:46-47 — the counts line',
    draw: () => betaStatus(),
    on: 'Тем: 22; предварительные ссылки: 14; только контекст: 8. Все пункты требуют проверки эксперта.</p>',
    off: 'Тем: 22; ссылки на нормы: 14; только контекст: 8.</p>',
    gone: ['предварительные ссылки: 14', 'Все пункты требуют проверки эксперта'],
  },
  {
    id: 'start-ar-v3-group-control.tsx:64 — the note under the start button',
    draw: () => startControl(),
    on: 'Шесть отдельных прогонов; результат — предварительные цитаты для проверки экспертом, без числовых выводов.',
    off: 'Шесть отдельных прогонов; результат — нормативные цитаты, без числовых выводов.',
    gone: ['предварительные цитаты для проверки экспертом'],
  },
  {
    id: 'run-progress.tsx:133 — a published AR v3 Run',
    draw: () => v3Run('published', 0),
    on: '<p>Прогон завершён. Предварительный нормативный разбор АР v3 сохранён.</p>',
    off: '<p>Прогон завершён. Нормативный разбор АР v3 сохранён.</p>',
    gone: ['Предварительный нормативный разбор АР v3 сохранён'],
  },
  {
    id: 'run-progress.tsx:134 — a published AR v3 Run that published no finding (count 0)',
    draw: () => v3Run('published', 0),
    on: '<p>Канонические находки здесь не публикуются. Каждая тема и цитата требует проверки эксперта; числовой или правовой вывод не утверждён.</p>',
    off: '<p>Канонические находки здесь не публикуются. Числовой или правовой вывод не утверждён.</p>',
    gone: ['требует проверки эксперта'],
  },
  {
    id: 'run-progress.tsx:134 — a published AR v3 Run whose count the server did not report',
    draw: () => v3Run('published', null),
    on: '<p>Канонические находки здесь не публикуются. Каждая тема и цитата требует проверки эксперта; числовой или правовой вывод не утверждён.</p>',
    off: '<p>Канонические находки здесь не публикуются. Числовой или правовой вывод не утверждён.</p>',
    gone: ['требует проверки эксперта'],
  },
  {
    id: 'run-progress.tsx:134 — a published AR v3 Run that published findings',
    draw: () => v3Run('published', 2),
    on: '<p>Находки с предварительными нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён.</p>',
    off: '<p>Находки с нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён.</p>',
    gone: ['предварительными нормативными ссылками'],
  },
  {
    id: 'run-progress.tsx:152 — a partial AR v3 Run',
    draw: () => v3Run('partial', 0),
    on: '<p>Предварительный нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён.</p>',
    off: '<p>Нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён.</p>',
    gone: ['Предварительный нормативный разбор АР v3 завершился частично'],
  },
  {
    id: 'run-progress.tsx:153 — a partial AR v3 Run publishes no canonical finding',
    draw: () => v3Run('partial', 0),
    on: '<p>Канонические находки не публикуются; требуется проверка эксперта.</p>',
    off: '<p>Канонические находки не публикуются.</p>',
    gone: ['требуется проверка эксперта'],
  },
  {
    id: 'run-progress.tsx:410 — the title of the review box',
    draw: () => v3Run('queued', 0),
    on: '<p class="am-state__title">Предварительный разбор АР v3</p>',
    off: '<p class="am-state__title">Разбор АР v3</p>',
    gone: ['Предварительный разбор АР v3'],
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
    expect(GATED.length).toBeGreaterThanOrEqual(21);
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

    it(`${state}: the attestation record of the sealed pack`, () => {
      const text = visible(render(on, packPanel));
      expect(text).toContain(ATTESTATION_SENTENCE);
      expect(text).toContain('Запись рецензента приложена при установке пакета; система её не проверяет');
    });

    it(`${state}: every statement that a verdict is the expert's own decision`, () => {
      const expert = visible(render(on, () => groupReview({ roles: ['expert'] })));
      expect(expert).toContain('Находки и решения эксперта');
      expect(expert).toContain('Формулировка модели, не решение эксперта.');
      const administrator = visible(render(on, () => groupReview({ roles: ['admin'] })));
      expect(administrator).toContain('Решение записывает эксперт.');
      const published = visible(render(on, () => v3Run('published', 2)));
      expect(published).toContain('решение по каждой записывает эксперт');
    });

    it(`${state}: the integrity wording of the group review and the numeric limit`, () => {
      const text = visible(render(on, () => groupReview()));
      expect(text).toContain('Проверка сохранённого разбора отказала');
      expect(text).toContain('Числовой или правовой вывод здесь не утверждён.');
    });
  }
});
