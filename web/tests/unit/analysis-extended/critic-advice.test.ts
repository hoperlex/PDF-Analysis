/**
 * The critic's advice in the card of a block finding (`F8-WEB`, plan v5 section 4.5) and the run caption of a `one_list` run.
 *
 * The sealed observation reference is authoritative. Older payloads without it use an unambiguous words-and-blocks match;
 * an unresolved present reference cannot borrow another candidate's advice. Proposals remain distinct from expert decisions.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  ADVICE_EXPLANATION_LIMIT,
  CandidateNormAdvice,
  CriticAdviceLine,
  CriticAdviceView,
  ExtendedReviewSummary,
  adviceForFinding,
  adviceLine,
  candidateOfFinding,
} from '@/widgets/extended-review';

import { newClient, renderWith } from '../screens/harness';
import { finding, observation } from '../review/fixtures';

const BLK_A = `blk_${'a'.repeat(32)}`;
const BLK_B = `blk_${'b'.repeat(32)}`;
const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const WORDS = 'Размер проёма не совпадает со спецификацией.';

const candidate = (over: Record<string, unknown> = {}) => ({
  observation_id: 'xobs_1',
  title: 'Размер проёма',
  description: WORDS,
  source_ids: [BLK_A, BLK_B, 'primary_text_x'],
  review: { llm_decision: 'reject', explanation: 'Размер на чертеже верный. Спецификация устарела.', mode: 'model' },
  ...over,
});
const subject = { findingText: WORDS, blockIds: [BLK_A] };

describe('which candidate a block finding came from', () => {
  it('uses the sealed reference even when other candidates have identical words, and never guesses after an unresolved ref', () => {
    const first = candidate();
    const second = candidate({ observation_id: 'xobs_2' });
    const result = { observations: [first, second] };
    expect(candidateOfFinding(result, { ...subject, observationRef: 'xobs_2' })).toBe(second);
    expect(candidateOfFinding({ observations: [first] }, { ...subject, observationRef: 'missing' })).toBeNull();
    expect(candidateOfFinding({ observations: [first, first] }, { ...subject, observationRef: 'xobs_1' })).toBeNull();
  });
  it('is the one whose words are the finding\'s and whose sources hold every block of the finding', () => {
    const fit = candidate();
    expect(candidateOfFinding({ observations: [candidate({ description: 'Другое.', title: 'Другое' }), fit] }, subject)).toBe(fit);
    expect(candidateOfFinding({ observations: [fit] }, { findingText: WORDS, blockIds: [BLK_A, BLK_B] })).toBe(fit);
  });

  it('reads the words as the publisher wrote them: the title over a description that does not start with it', () => {
    const titled = candidate({ title: 'Заголовок', description: 'Описание.' });
    expect(candidateOfFinding({ observations: [titled] }, { findingText: 'Заголовок\n\nОписание.', blockIds: [BLK_A] })).toBe(titled);
    // The title alone, and the description alone, are not the words the publisher wrote for it.
    expect(candidateOfFinding({ observations: [titled] }, { findingText: 'Описание.', blockIds: [BLK_A] })).toBeNull();
    expect(candidateOfFinding({ observations: [titled] }, { findingText: 'Заголовок', blockIds: [BLK_A] })).toBeNull();
    // A description that starts with the title already says it: it is the words, with no title over it.
    const restated = candidate({ title: 'Заголовок', description: 'Заголовок и подробности.' });
    expect(candidateOfFinding({ observations: [restated] }, { findingText: 'Заголовок и подробности.', blockIds: [BLK_A] })).toBe(restated);
    expect(candidateOfFinding({ observations: [restated] }, { findingText: 'Заголовок\n\nЗаголовок и подробности.', blockIds: [BLK_A] })).toBeNull();
  });

  it('is none when the words differ, a block of the finding is not among the sources, or the finding names no block', () => {
    expect(candidateOfFinding({ observations: [candidate()] }, { ...subject, findingText: 'Иной текст.' })).toBeNull();
    expect(candidateOfFinding({ observations: [candidate({ source_ids: [BLK_B] })] }, subject)).toBeNull();
    expect(candidateOfFinding({ observations: [candidate()] }, { findingText: WORDS, blockIds: [] })).toBeNull();
    expect(candidateOfFinding({ observations: [candidate()] }, { findingText: '', blockIds: [BLK_A] })).toBeNull();
  });

  it('is none when two candidates fit: it does not pick one', () => {
    expect(candidateOfFinding({ observations: [candidate(), candidate({ observation_id: 'xobs_2' })] }, subject)).toBeNull();
  });

  it('is none for a review that holds no candidates, or is not a record', () => {
    for (const result of [undefined, null, 7, 'x', [], {}, { observations: 'x' }, { observations: [null, 3, 'x'] }]) {
      expect(candidateOfFinding(result, subject)).toBeNull();
    }
  });
});

describe('the critic\'s word', () => {
  it('is the recommendation, in the critic\'s own words, cut at its first sentence', () => {
    const advice = adviceForFinding({ observations: [candidate()] }, subject);

    expect(advice).toEqual({ decision: 'reject', label: 'Рекомендует снять наблюдение', mode: 'model', explanation: 'Размер на чертеже верный.' });
    expect(adviceLine(advice as NonNullable<typeof advice>)).toBe('Совет критика: рекомендует снять наблюдение — Размер на чертеже верный.');
  });

  it('says a rule\'s word is a rule\'s, without a model', () => {
    const advice = adviceForFinding({ observations: [candidate({ review: undefined, critic: { llm_decision: 'needs_human', mode: 'deterministic', explanation: '' } })] }, subject);

    expect(advice?.mode).toBe('rules');
    expect(adviceLine(advice as NonNullable<typeof advice>)).toBe('Правила критика (без модели): нужна проверка человека');
  });

  it('is shortened to one line', () => {
    const long = 'а'.repeat(400);
    const advice = adviceForFinding({ observations: [candidate({ review: { llm_decision: 'accept', explanation: long } })] }, subject);

    expect(advice?.explanation.length).toBe(ADVICE_EXPLANATION_LIMIT);
    expect(advice?.explanation.endsWith('…')).toBe(true);
  });

  it('is none when the critic did not review the candidate, or said a word this screen has no label for', () => {
    expect(adviceForFinding({ observations: [candidate({ review: undefined, review_status: 'not_reviewed' })] }, subject)).toBeNull();
    expect(adviceForFinding({ observations: [candidate({ review: { llm_decision: 'approve_everything' } })] }, subject)).toBeNull();
    expect(adviceForFinding({ observations: [candidate({ review: { llm_decision: 'toString' } })] }, subject)).toBeNull();
  });
});

describe('the line in the card', () => {
  it('draws the one line and says it is not the expert\'s decision', () => {
    const advice = adviceForFinding({ observations: [candidate()] }, subject);
    const markup = renderToStaticMarkup(createElement(CriticAdviceView, { advice: advice as NonNullable<typeof advice> }));

    expect(markup).toContain('data-critic-advice="reject"');
    expect(markup).toContain('Совет критика: рекомендует снять наблюдение');
    expect(markup).toContain('не является решением эксперта');
  });

  it('reads the saved review of the run, and draws nothing until it has been read or when it names no candidate', () => {
    const line = (reading?: unknown) => {
      const client = newClient();
      if (reading !== undefined) client.setQueryData(['extended-run-review', RUN], reading);
      return renderWith(client, createElement(CriticAdviceLine, { runId: RUN, subject }));
    };

    expect(line()).toBe('');
    expect(line({ run_id: RUN, status: 'completed', result: { observations: [] } })).toBe('');
    expect(line({ run_id: RUN, status: 'completed', result: { observations: [candidate()] } })).toContain('data-critic-advice="reject"');
  });
});

describe('the caption of the run', () => {
  const reading = { run_id: RUN, status: 'completed', result: { observations: [candidate()] } };
  const summary = (oneList?: boolean) => {
    const client = newClient();
    client.setQueryData(['extended-run-review', RUN], reading);
    return renderWith(client, createElement(ExtendedReviewSummary, { projectUid: 'prj_x', runId: RUN, ...(oneList === undefined ? {} : { oneList }) }));
  };

  it('says the candidates are separate machine observations for a run that did not publish them as findings', () => {
    for (const markup of [summary(), summary(false)]) {
      expect(markup).toContain('предварительных кандидатов: 1');
      expect(markup).toContain('Это отдельные машинные наблюдения');
    }
  });

  it('does not say it for a run of one list, where they are findings; the count and the way to the review stay', () => {
    const markup = summary(true);

    expect(markup).not.toContain('отдельные машинные наблюдения');
    expect(markup).not.toContain('Нулевой список находок');
    expect(markup).toContain('предварительных кандидатов: 1');
    expect(markup).toContain('Открыть расширенный анализ');
  });

  it('omits the extra banner when all retained candidates are already represented by findings', () => {
    const client = newClient();
    client.setQueryData(['extended-run-review', RUN], reading);
    const published = [finding({ observation: observation({ extended_observation_ref: 'xobs_1' }) })];
    expect(renderWith(client, createElement(ExtendedReviewSummary, { projectUid: 'p', runId: RUN, oneList: true, published }))).toBe('');
  });
});

describe('candidate norms on a finding', () => {
  it('reads the exact observation reference and labels search results as unconfirmed', () => {
    const client = newClient();
    client.setQueryData(['extended-run-review', RUN], { run_id: RUN, status: 'completed', result: { observations: [candidate({
      norm_candidates: [{ paragraph_id: 'paragraph', designation: 'СП 256.1325800.2016', clause_number: '8.12.4', quote: 'Текст найденного абзаца' }],
    })] } });
    const markup = renderWith(client, createElement(CandidateNormAdvice, { runId: RUN, subject: { ...subject, observationRef: 'xobs_1' } }));
    expect(markup).toContain('Нормативные кандидаты');
    expect(markup).toContain('Применимость и основание замечания не подтверждены');
    expect(markup).toContain('Текст найденного абзаца');
    expect(markup).not.toContain('data-norm-citation-state');
    expect(renderWith(client, createElement(CandidateNormAdvice, { runId: RUN, subject: { ...subject, observationRef: 'missing' } }))).toBe('');
  });
});
