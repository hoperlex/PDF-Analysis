import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExtendedRunReview } from '@/shared/api';
import { ExtendedReviewView, extendedReviewDefinitive, extendedReviewPollInterval, MAX_TERMINAL_REVIEW_READS } from '@/widgets/extended-review/ui/extended-review';

const runId = 'run_01M664JCG1QH0NTEWZTC3PM19K';
beforeEach(() => { vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'https://api.example.test/api/v1'); });
afterEach(() => { vi.unstubAllEnvs(); });
const v2 = (over: Partial<ExtendedRunReview> = {}): ExtendedRunReview => ({ run_id: runId, status: 'running', result: {
  workflow_version: 'extended-review-v2', procedures: [
    { id: 'block_analysis', title: 'Анализ блоков', status: 'queued' },
    { id: 'comprehensive_analysis', title: 'Комплексная сверка', status: 'queued' },
    { id: 'finding_merge', title: 'Свод наблюдений', status: 'queued' },
    { id: 'norm_verification', title: 'Проверка нормативных ссылок', status: 'queued' },
  ],
}, ...over });
const render = (reading: ExtendedRunReview) => renderToStaticMarkup(createElement(ExtendedReviewView, { reading, projectUid: 'prj_01M4FQ53F2QEVBX84XJZZ3NACB' }));

describe('server-frozen extended workflow', () => {
  it('shows all server-planned procedures before any result artifact or observation exists', () => {
    const html = render(v2());
    for (const id of ['block_analysis', 'comprehensive_analysis', 'finding_merge', 'norm_verification']) expect(html).toContain(`data-extended-procedure="${id}"`);
    expect(html.match(/data-procedure-status="queued"/g)).toHaveLength(4);
    expect(html).toContain('Полная цепочка анализа');
    expect(html).not.toContain('data-procedure-status="completed"');
    expect(html).not.toContain('data-pipeline-stage=');
  });

  it('renders real partial, failed and skipped phases rather than manufacturing completion', () => {
    const html = render(v2({ status: 'partial', result: { workflow_version: 'extended-review-v2', procedures: [
      { id: 'block_analysis', title: 'Анализ блоков', status: 'completed' },
      { id: 'comprehensive_analysis', title: 'Комплексная сверка', status: 'partial' },
      { id: 'finding_merge', title: 'Свод наблюдений', status: 'failed' },
      { id: 'norm_verification', title: 'Проверка нормативных ссылок', status: 'skipped', reason: 'provider_outcome_unknown' },
    ] } }));
    for (const state of ['completed', 'partial', 'failed', 'skipped']) expect(html).toContain(`data-procedure-status="${state}"`);
    expect(html).toContain('Результат обращения к исполнителю неизвестен');
  });

  it('shows document-wide coverage and a concrete corpus absence reason', () => {
    const html = render(v2({ status: 'partial', result: { workflow_version: 'extended-review-v2', review_scope: 'full_document',
      coverage: { blocks_total: 47, blocks_selected: 47, blocks_processed: 47, blocks_remaining: 0, skipped: [] },
      warnings: ['visual_context_bounded_full_text_reviewed'],
      procedures: [{ id: 'norm_verification', title: 'Проверка нормативных ссылок', status: 'unavailable', reason: 'corpus_unavailable' }],
    } }));
    expect(html).toContain('План включает все доступные блоки');
    expect(html).toContain('полный текст страниц передан');
    expect(html).toContain('нет доступного нормативного корпуса');
    expect(html).not.toContain('ограниченном одобренном окне');
  });

  it('keeps legacy policy visible and never assigns a v2 plan to it', () => {
    const html = render({ run_id: runId, status: 'unavailable', result: { reason: 'not_in_accepted_policy', procedures: [] } });
    expect(html).toContain('полная цепочка не была предусмотрена');
    expect(html).toContain('новый прогон со свежей оценкой и согласием');
    expect(html).not.toContain('data-extended-procedure=');
    expect(html).not.toContain('Анализ блоков</strong>');
  });

  it('shows not_started instead of hiding an accepted pending reading', () => {
    expect(render(v2({ status: 'not_started' }))).toContain('Ожидает начала');
    expect(render(v2({ status: 'not_started' }))).toContain('data-extended-procedure-plan');
  });

  it('never builds a portal crop URL for native-page sources and keeps source provenance', () => {
    const html = render(v2({ result: { workflow_version: 'extended-review-v2', version_uid: 'ver_01M00000000000000000000000',
      procedures: [], observations: [{ observation_id: 'o1', title: 'Наблюдение', source_ids: ['native_example'] }],
      sources: [{ source_id: 'native_example', kind: 'image', source_type: 'native_page', page_number: 2, crop_sha256: 'a'.repeat(64) }],
    } }));
    expect(html).toContain('страница PDF');
    expect(html).toContain('data-native-page-source');
    expect(html).toContain('ver_01M00000000000000000000000');
    expect(html).toContain('a'.repeat(64));
    expect(html).toContain('Открыть исходную версию PDF');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('/portal-blocks/');
  });

  it('retains the portal crop path for actual portal IMAGE blocks', () => {
    const html = render(v2({ result: { version_uid: 'ver_01M00000000000000000000000',
      observations: [{ observation_id: 'o1', title: 'Наблюдение', source_ids: ['blk_0123456789abcdef0123456789abcdef'] }],
      sources: [{ source_id: 'blk_0123456789abcdef0123456789abcdef', kind: 'image', page_number: 1 }],
    } }));
    expect(html).toContain('<img');
    expect(html).toContain('Исходный блок на странице 1');
  });
});

describe('terminal receipt reconciliation', () => {
  it('keeps reading a pending server plan after the base Run turns terminal', () => {
    expect(extendedReviewPollInterval(false, 0, v2())).toBe(2500);
    expect(extendedReviewPollInterval(false, 1, v2({ status: 'not_started' }))).toBe(2500);
    expect(extendedReviewPollInterval(false, MAX_TERMINAL_REVIEW_READS, v2())).toBe(false);
    expect(extendedReviewDefinitive(v2())).toBe(false);
  });
  it('stops for a definitive failed/legacy or completed receipt, but not a queued procedure under a completed envelope', () => {
    const legacy: ExtendedRunReview = { run_id: runId, status: 'unavailable', result: { reason: 'not_in_accepted_policy' } };
    expect(extendedReviewDefinitive(legacy)).toBe(true);
    expect(extendedReviewPollInterval(false, 0, legacy)).toBe(false);
    expect(extendedReviewDefinitive(v2({ status: 'completed' }))).toBe(false);
    expect(extendedReviewDefinitive({ run_id: runId, status: 'failed', result: { workflow_version: 'extended-review-v2', procedures: [{ id: 'block_analysis', title: 'Анализ блоков', status: 'failed' }] } })).toBe(true);
  });
});
