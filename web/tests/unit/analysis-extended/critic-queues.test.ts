/**
 * The critic's queues as chips in the extended review (`R-151q`, register row UI-B-78).
 *
 * Each chip counts the whole run's observations the review carries, never one page, and pressing it sets the same
 * «Рекомендация критика» filter the select offers. A critic's word is a recommendation, never a decision.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CRITIC_QUEUES, ObservationList, criticQueueCounts } from '@/widgets/extended-review';

import { mountLive } from '../analysis-settings/live-render';

const OBSERVATIONS = [
  { observation_id: 'o1', title: 'Первое', review: { llm_decision: 'accept' } },
  { observation_id: 'o2', title: 'Второе', review: { llm_decision: 'accept' } },
  { observation_id: 'o3', title: 'Третье', critic: { llm_decision: 'reject' } },
  { observation_id: 'o4', title: 'Четвёртое', review: { llm_decision: 'needs_human' } },
  { observation_id: 'o5', title: 'Пятое', review_status: 'not_reviewed' },
  { observation_id: 'o6', title: 'Шестое' },
];

describe('the critic’s queues', () => {
  it('count the whole run, each observation once, by the critic’s recommendation', () => {
    expect(criticQueueCounts(OBSERVATIONS)).toEqual({
      all: 6, accept: 2, reject: 1, borderline: 0, needs_human: 1, rewrite: 0, not_reviewed: 1,
    });
  });

  it('draw one chip per queue with its number, «Все» pressed at first', () => {
    const markup = renderToStaticMarkup(createElement(ObservationList, { observations: OBSERVATIONS, sources: [], fallbackVersion: 'ver_x' }));
    expect(markup).toContain('data-critic-queues');
    for (const [, label] of CRITIC_QUEUES) expect(markup).toContain(label);
    expect(markup).toMatch(/aria-pressed="true"[^>]*>Все <span[^>]*>6</);
    expect(markup).toMatch(/>Сохранить <span[^>]*>2</);
  });

  it('pressing a chip sets the recommendation filter over the same list', async () => {
    const live = await mountLive(createElement(ObservationList, { observations: OBSERVATIONS, sources: [], fallbackVersion: 'ver_x' }));
    try {
      expect(live.markup()).toMatch(/По фильтрам: <strong>6<\/strong> из 6/);
      expect(await live.press('Снять 1')).toBe(true);
      expect(live.markup()).toMatch(/По фильтрам: <strong>1<\/strong> из 6/);
      expect(live.markup()).toMatch(/aria-pressed="true"[^>]*>Снять /);
    } finally {
      await live.unmount();
    }
  });
});
