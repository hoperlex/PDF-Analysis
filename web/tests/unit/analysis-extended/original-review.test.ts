/**
 * `V2-ORIGINAL-REVIEW-01` (R-154e..g): plan v2 has the original's deterministic critic and corrector.
 *
 * The record of such a run says so (`original_review`, and `model_called: false` on its two procedures); the panel, the critic's
 * queues, the card of an observation, the rail and the exports then say that the critic is a rule's word and not a model's. A v2
 * record without the marker, and a v3 record, are what they were.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExtendedRunReview } from '@/shared/api';
import { formatExtendedRunReport, procedureReadings, runChips } from '@/entities/audit-run';
import { readinessPlan } from '@/entities/stage-layout';
import { CRITIC_QUEUE_NOTES, ObservationList, criticQueueCounts } from '@/widgets/extended-review';
import { CRITIC_QUEUE_NOTES_DETERMINISTIC, criticIsDeterministic } from '@/widgets/extended-review/ui/critic-queues';
import { ExtendedReviewView } from '@/widgets/extended-review/ui/extended-review';
import { extendedCandidateCounts } from '@/widgets/extended-review/ui/extended-review-summary';
import { PlanStagesDialog } from '@/widgets/run-stages-dialog';

import { mountLive } from '../analysis-settings/live-render';
import { runStatus } from '../review/fixtures';
import { CLAUDE_CELLS } from '../start-run/readiness-fixtures';

const runId = 'run_01M664JCG1QH0NTEWZTC3PM19K';
beforeEach(() => { vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'https://api.example.test/api/v1'); });
afterEach(() => { vi.unstubAllEnvs(); });

const PLAN = [
  { id: 'block_analysis', title: 'Анализ блоков', status: 'completed' },
  { id: 'comprehensive_analysis', title: 'Комплексная сверка', status: 'completed' },
  { id: 'finding_merge', title: 'Свод наблюдений', status: 'completed' },
  { id: 'norm_verification', title: 'Проверка нормативных ссылок', status: 'completed' },
];
const RULE_PROCEDURES = [
  { id: 'finding_review', title: 'Критик наблюдений · правила оригинала, без модели', status: 'completed', model_called: false },
  { id: 'finding_correction', title: 'Предложения по уточнению · правила оригинала, без модели', status: 'completed', model_called: false },
];
const CRITIC = (verdict: string, decision: string, extra: Record<string, unknown> = {}) => ({
  input_id: `xrd_${verdict}`, observation_id: `o_${verdict}`, source_ids: ['s1'], llm_decision: decision, human_taxonomy_reason: null, confidence: null,
  explanation: `Проверка оригинала: ${verdict}.`, evidence_checked: false, source_dependency: 'enough_source', needs_correction: false, suggested_fix: '',
  source_evidence: [], status: 'requires_expert_review', expert_decision: false, mode: 'deterministic', model_called: false,
  policy: 'deterministic-v1', original_verdict: verdict, failed_checks: [], checks: {}, ...extra,
});
const OBSERVATIONS = [
  { observation_id: 'o_pass', title: 'Чистое', description: 'Описание', source_ids: ['s1'], review_status: 'reviewed', critic: CRITIC('pass', 'accept') },
  { observation_id: 'o_no_evidence', title: 'Без источника', description: 'Описание', source_ids: [], review_status: 'reviewed',
    critic: CRITIC('no_evidence', 'needs_human', { human_taxonomy_reason: 'insufficient_source_context', source_dependency: 'needs_more_context' }),
    correction: { input_id: 'xrd_no_evidence', observation_id: 'o_no_evidence', original: { title: 'Без источника', description: 'Описание', source_ids: [] }, candidate: null,
      action: 'needs_context', source_ids: [], reason: 'Исправить нечем: указать источник должен эксперт. Наблюдение сохранено без изменений.',
      required_context: ['Блок или страница документа, подтверждающие наблюдение'], status: 'requires_expert_review', expert_decision: false,
      mode: 'deterministic', model_called: false, policy: 'deterministic-v1', original_verdict: 'no_evidence' } },
  { observation_id: 'o_page', title: 'Страница', description: 'Описание', source_ids: ['s1'], review_status: 'reviewed',
    critic: CRITIC('page_mismatch', 'rewrite', { needs_correction: true, suggested_fix: 'Проверить страницу: цитата найдена на стр. 4, указана стр. 14.' }),
    correction: { input_id: 'xrd_page_mismatch', observation_id: 'o_page', original: { title: 'Страница', description: 'Описание', source_ids: ['s1'] },
      candidate: { title: 'Страница', description: 'Описание\n\nУточнение страницы: цитата источника найдена на стр. 4; в записи указана стр. 14.', source_ids: ['s1'],
        source_evidence: [{ source_id: 's1', quote: 'Толщина утеплителя' }], norm_evidence: [], status: 'proposed_requires_expert_review' },
      action: 'propose_revision', source_ids: ['s1'], reason: 'Предложена редакция с уточнённой страницей; исходная запись сохранена.', required_context: [],
      status: 'requires_expert_review', expert_decision: false, mode: 'deterministic', model_called: false, policy: 'deterministic-v1', original_verdict: 'page_mismatch' } },
];
const ORIGINAL_REVIEW = { version: 'deterministic-v1', mode: 'deterministic', model_called: false, proposals_only: true, expert_decisions_written: false,
  reviewed: 3, verdicts: { pass: 1, no_evidence: 1, page_mismatch: 1 }, proposals: { needs_context: 1, propose_revision: 1 } };

const marked = (): ExtendedRunReview => ({ run_id: runId, status: 'completed', result: { workflow_version: 'extended-review-v2', review_scope: 'full_document',
  procedures: [...PLAN, ...RULE_PROCEDURES], original_review: ORIGINAL_REVIEW, observations: OBSERVATIONS,
  sources: [{ source_id: 's1', kind: 'text', page_number: 14, quote: 'Толщина утеплителя' }], warnings: [],
  coverage: { blocks_total: 1, blocks_selected: 1, blocks_processed: 1, blocks_remaining: 0, skipped: [] } } });
const old = (): ExtendedRunReview => ({ run_id: runId, status: 'completed', result: { workflow_version: 'extended-review-v2', review_scope: 'full_document',
  procedures: PLAN, observations: [{ observation_id: 'o1', title: 'Старое', description: 'Описание', source_ids: [] }], sources: [], warnings: [] } });
const render = (reading: ExtendedRunReview) => renderToStaticMarkup(createElement(ExtendedReviewView, { reading, projectUid: 'prj_01M4FQ53F2QEVBX84XJZZ3NACB' }));
const squash = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');

describe('the panel of a v2 record', () => {
  it('stops saying that the critique and the correction are not attributed once the record carries the original’s rules', () => {
    const html = render(marked());
    const words = squash(html);
    expect(html).toContain('data-original-review="deterministic-v1"');
    expect(words).toContain('Критик и уточнение в нём выполнены по правилам оригинала, без модели и без исполнителя');
    expect(words).toContain('Смысловая проверка не выполнялась');
    expect(words).toContain('Проверено наблюдений: 3; без замечаний: 1; с замечаниями: 2; предложено уточнений текста: 1.');
    expect(words).not.toContain('не приписываются');
    // The two procedures stand in the plan list with their words, and the counters are real numbers.
    expect(html).toContain('data-extended-procedure="finding_review"');
    expect(html).toContain('data-extended-procedure="finding_correction"');
    expect(html).toMatch(/Рекомендации машинного критика<\/dt><dd>3<\/dd>/);
    expect(html).toMatch(/Предложенные исправленные кандидаты<\/dt><dd>1<\/dd>/);
  });

  it('keeps today’s text for a v2 record without the marker, and its zero counters', () => {
    const html = render(old());
    expect(squash(html)).toContain('Новые критика, исправление и подготовка отчёта V3 ему не приписываются');
    expect(html).not.toContain('data-original-review');
    expect(html).toMatch(/Рекомендации машинного критика<\/dt><dd>0<\/dd>/);
  });

  it('counts the critic and the proposals the way it counts a model’s', () => {
    expect(extendedCandidateCounts(marked().result)).toEqual({ candidates: 3, criticRecommendations: 3, correctionProposals: 1 });
  });
});

describe('the card of an observation and the critic’s queues', () => {
  it('says a rule’s word is a rule’s: no model, no declared confidence, no «sources viewed by the model»', () => {
    const words = squash(render(marked()));
    expect(words).toContain('Рекомендация правил оригинала (без модели) не является принятием или отклонением экспертом');
    expect(words).toContain('Проверено по правилам, без модели: наличие источника, его существование в записи и страница цитаты');
    expect(words).toContain('Правило не нашло подтверждающий источник; требуется дополнительный исходный контекст.');
    expect(words).toContain('Правило сохранило исходное наблюдение: без источника исправить нечего. Ничего не удалено и не изменено.');
    expect(words).not.toContain('Заявленная моделью уверенность');
    expect(words).not.toContain('Источники просмотрены моделью');
    expect(words).not.toContain('Проверка источников моделью не подтверждена');
    expect(words).not.toContain('Рекомендация модели не является');
    // The proposal stands beside the untouched original.
    expect(words).toContain('Предложено уточнение');
    expect(words).toContain('Уточнение страницы: цитата источника найдена на стр. 4');
  });

  it('puts the observations in the queues the advice names, and never in «Снять»', () => {
    const counts = criticQueueCounts(OBSERVATIONS);
    expect(counts).toMatchObject({ all: 3, accept: 1, needs_human: 1, rewrite: 1, reject: 0 });
    expect(criticIsDeterministic(OBSERVATIONS)).toBe(true);
    expect(criticIsDeterministic([{ observation_id: 'm', critic: { llm_decision: 'accept' } }])).toBe(false);
  });

  it('words the queue notes without «совет модели» for such a record and leaves the model’s notes alone', async () => {
    for (const key of ['accept', 'needs_human', 'rewrite']) {
      expect(CRITIC_QUEUE_NOTES_DETERMINISTIC[key]).toContain('равила критика оригинала');
      expect(CRITIC_QUEUE_NOTES_DETERMINISTIC[key]).not.toContain('совет модели');
      expect(CRITIC_QUEUE_NOTES[key]).not.toContain('равила критика оригинала');
    }
    expect(CRITIC_QUEUE_NOTES_DETERMINISTIC.reject).toBe(CRITIC_QUEUE_NOTES.reject);
    const live = await mountLive(createElement(ObservationList, { observations: OBSERVATIONS, sources: [], fallbackVersion: 'ver_x' }));
    try {
      expect(await live.press('Нужен человек 1 / 1')).toBe(true);
      expect(live.markup()).toMatch(/data-critic-queue-note="needs_human"[^>]*>Правила критика оригинала просят проверку человеком/);
    } finally {
      await live.unmount();
    }
    const model = await mountLive(createElement(ObservationList,
      { observations: [{ observation_id: 'm', title: 'Модель', review: { llm_decision: 'accept' } }], sources: [], fallbackVersion: 'ver_x' }));
    try {
      expect(await model.press('Сохранить 1 / 1')).toBe(true);
      expect(model.markup()).toContain('Это совет модели, а не решение эксперта.');
    } finally {
      await model.unmount();
    }
  });
});

describe('the rail', () => {
  const procedures = (list: readonly Record<string, unknown>[]) => procedureReadings({ procedures: list });
  const chipsOf = (list: readonly Record<string, unknown>[]) => runChips({ status: runStatus({ stages: [] }), procedures: procedures(list) });

  it('reads model_called: false off a procedure and nothing else', () => {
    const read = procedures([...PLAN, ...RULE_PROCEDURES]);
    expect(read.filter((procedure) => procedure.deterministic === true).map((procedure) => procedure.id)).toEqual(['finding_review', 'finding_correction']);
    expect(procedures([{ id: 'finding_review', status: 'completed', model_called: true }])[0]).not.toHaveProperty('deterministic');
  });

  it('draws Критик and Уточнение as stages that call no model when the record says they did not', () => {
    const list = chipsOf([...PLAN, ...RULE_PROCEDURES]);
    const calls = Object.fromEntries(list.map((chip) => [chip.definition.id, chip.definition.callsModel]));
    expect(calls).toMatchObject({ blocks: true, cross_check: true, norms: true, review: false, correction: false, merge: false });
    expect(list.find((chip) => chip.definition.id === 'review')?.state).toBe('done');
  });

  it('leaves them calling a model for a v3 record, which says nothing of the kind', () => {
    const list = chipsOf([...PLAN, { id: 'finding_review', title: 'Критик', status: 'completed' }, { id: 'finding_correction', title: 'Уточнение', status: 'completed' }]);
    expect(list.filter((chip) => ['review', 'correction'].includes(chip.definition.id)).map((chip) => chip.definition.callsModel)).toEqual([true, true]);
  });
});

describe('the exports', () => {
  it('say «по правилам оригинала, без модели» and print no empty reason or fix for a pass', () => {
    const md = formatExtendedRunReport(marked(), 'md').content as string;
    expect(md).toContain('#### Рекомендация критика по правилам оригинала, без модели — не решение эксперта');
    expect(md).not.toContain('Основание: Не передано');
    expect(md).toContain('Уточнение страницы');
    expect(md).toContain('"original_review"');
    const html = formatExtendedRunReport(marked(), 'html').content as string;
    expect(html).toContain('Рекомендация критика по правилам оригинала, без модели — не решение эксперта');
    expect(html).not.toContain('<p>Не передано</p>');
    // A model’s critic keeps its heading.
    const model = formatExtendedRunReport({ run_id: runId, status: 'completed', result: { workflow_version: 'extended-review-v3', procedures: [], sources: [],
      observations: [{ observation_id: 'm', title: 'Модель', description: 'д', source_ids: ['s1'],
        critic: { llm_decision: 'accept', human_taxonomy_reason: 'other', explanation: 'ок', suggested_fix: '', source_evidence: [] } }] } }, 'md').content as string;
    expect(model).toContain('#### Рекомендация машинного критика — не решение эксперта');
    expect(model).not.toContain('по правилам оригинала');
  });
});

describe('the plan window before a run, under the plan the readiness names', () => {
  const draw = (extendedPlan?: string | null) => renderToStaticMarkup(createElement(PlanStagesDialog, {
    rows: readinessPlan(CLAUDE_CELLS), kit: null, onClose: () => undefined, staticOpen: true,
    ...(extendedPlan === undefined ? {} : { extendedPlan }),
  }));
  // The line of a stage is the last span of its button (the first is its name).
  const lineOf = (markup: string, stage: string) => new RegExp(`data-stage-item="${stage}"[^>]*>(?:(?!</button>).)*<span[^>]*>([^<]*)</span></button>`, 's')
    .exec(markup)?.[1];

  it('under v2 names Критик and Уточнение as without a model, by the original’s rules', () => {
    const markup = draw('v2');
    expect(lineOf(markup, 'review')).toBe('без модели (правила оригинала)');
    expect(lineOf(markup, 'correction')).toBe('без модели (правила оригинала)');
    expect(lineOf(markup, 'blocks')).not.toContain('правила оригинала');
  });

  it('is what it was while the answer carries no plan, or names v3 or none', () => {
    for (const plan of [undefined, null, 'v3']) {
      const markup = draw(plan);
      expect(markup, String(plan)).not.toContain('правила оригинала');
      expect(lineOf(markup, 'review'), String(plan)).toBeDefined();
    }
  });
});
