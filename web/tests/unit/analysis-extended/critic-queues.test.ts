/**
 * The critic's queues as tabs in the extended review (`R-151q`, register row UI-B-78).
 *
 * Each tab says «видимо / всего»: the whole run's observations the review carries (never one page) and how many of them
 * the list's other filters leave. Choosing a tab sets the same «Рекомендация критика» filter the select offers, and the
 * row of tabs is the tabs pattern: the chosen one is the only stop of the Tab key, the arrows, `Home` and `End` move
 * between them. A critic's word is a recommendation, never a decision.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CRITIC_QUEUES, ObservationList, criticQueueCounts, queueAfterKey } from '@/widgets/extended-review';

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

  it('draw one tab per queue with «видимо / всего», «Все» chosen at first and the only stop of the Tab key', () => {
    const markup = renderToStaticMarkup(createElement(ObservationList, { observations: OBSERVATIONS, sources: [], fallbackVersion: 'ver_x' }));
    expect(markup).toContain('data-critic-queues');
    expect(markup).toContain('role="tablist"');
    for (const [, label] of CRITIC_QUEUES) expect(markup).toContain(label);
    expect(markup.match(/role="tab"/g)?.length).toBe(CRITIC_QUEUES.length);
    expect(markup).toMatch(/aria-selected="true"[^>]*tabindex="0"[^>]*>Все <span[^>]*>6 \/ 6</);
    expect(markup).toMatch(/aria-selected="false"[^>]*tabindex="-1"[^>]*>Сохранить <span[^>]*>2 \/ 2</);
    // The list is the tab's panel, named by the chosen tab.
    expect(markup).toMatch(/role="tabpanel"[^>]*aria-labelledby="extended-observations-queue-tab-all"/);
  });

  it('choosing a tab sets the recommendation filter over the same list, and the other tabs count under the other filters', async () => {
    const live = await mountLive(createElement(ObservationList, { observations: OBSERVATIONS, sources: [], fallbackVersion: 'ver_x' }));
    try {
      expect(live.markup()).toMatch(/По фильтрам: <strong>6<\/strong> из 6/);
      expect(await live.press('Снять 1 / 1')).toBe(true);
      expect(live.markup()).toMatch(/По фильтрам: <strong>1<\/strong> из 6/);
      expect(live.markup()).toMatch(/aria-selected="true"[^>]*>Снять /);
      expect(live.markup()).toMatch(/data-critic-queue-note="reject"/);
      // A search that keeps only «Первое» leaves one of the two kept observations visible; the whole count stays two.
      expect(await live.change('Поиск по заголовку, описанию, рекомендации или источнику', 'первое')).toBe(true);
      expect(live.markup()).toMatch(/>Сохранить <span[^>]*>1 \/ 2</);
      expect(live.markup()).toMatch(/>Снять <span[^>]*>0 \/ 1</);
    } finally {
      await live.unmount();
    }
  });

  it('moves between tabs by the arrows, Home and End, round the row, and by no other key', () => {
    expect(queueAfterKey('all', 'ArrowRight')).toBe('accept');
    expect(queueAfterKey('all', 'ArrowLeft')).toBe('not_reviewed');
    expect(queueAfterKey('not_reviewed', 'ArrowRight')).toBe('all');
    expect(queueAfterKey('reject', 'Home')).toBe('all');
    expect(queueAfterKey('reject', 'End')).toBe('not_reviewed');
    expect(queueAfterKey('reject', 'Enter')).toBeNull();
    expect(queueAfterKey('reject', 'ArrowDown')).toBeNull();
  });
});
