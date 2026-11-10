/**
 * `UI-A-60` / `R-151i`: what the dialog offers and how a refusal of the reuse reads. The refusal vocabulary is held to the
 * contract's own text in both directions, so a reason the server can give that the screen cannot say reddens here.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';
import {
  REUSE_REFUSAL_REASONS, STARTABLE_STAGE_IDS, mayStartFromStage, reuseRefusal, startStageOption, startableState,
} from '@/features/start-run-from-stage';

const envelope = (code: string, details: Record<string, string>) => new ApiError(422, {
  contract_version: '1.49.0', error_code: code as never, message: 'x', correlation_id: 'c', retryable: false, details,
}, 'c');

describe('the stages offered', () => {
  it('are the three after the first, numbered as the rail numbers them', () => {
    expect(STARTABLE_STAGE_IDS).toEqual(['page_geometry_extraction', 'document_context_build', 'text_analysis']);
    expect(STARTABLE_STAGE_IDS.map(startStageOption)).toEqual([
      '2. Извлечение геометрии страниц и блоков', '3. Построение контекста документа', '4. Анализ текста',
    ]);
  });

  it('are offered for an ended run to an expert or an administrator only', () => {
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) expect(startableState(state)).toBe(true);
    for (const state of ['created', 'queued', 'running', 'validating'] as const) expect(startableState(state)).toBe(false);
    expect(startableState(undefined)).toBe(false);
    expect(mayStartFromStage(['expert'])).toBe(true);
    expect(mayStartFromStage(['admin'])).toBe(true);
    expect(mayStartFromStage(['viewer'])).toBe(false);
    expect(mayStartFromStage([])).toBe(false);
    expect(mayStartFromStage(undefined)).toBe(true);
  });
});

describe('a refused reuse', () => {
  it('names the stage and says nothing was recomputed', () => {
    const text = reuseRefusal(envelope('analysis_input_invalid', { stage_id: 'page_geometry_extraction', reason: 'source_artifact_changed' }));
    expect(text).toContain('«Извлечение геометрии страниц и блоков»');
    expect(text).toContain('не совпадает с записанным');
    expect(text).toContain('Новый прогон не создан; ничего не пересчитано вместо него.');
  });

  it('is nothing for any other failure, which keeps its usual wording', () => {
    expect(reuseRefusal(new Error('x'))).toBeNull();
    expect(reuseRefusal(envelope('conflict', { stage_id: 'text_analysis', reason: 'source_artifact_changed' }))).toBeNull();
    expect(reuseRefusal(envelope('analysis_input_invalid', { stage_id: 'text_analysis', reason: 'something_else' }))).toBeNull();
    expect(reuseRefusal(envelope('analysis_input_invalid', { stage_id: 'finding_merge', reason: 'source_artifact_changed' }))).toBeNull();
  });

  it('has a sentence for each reason the contract lists, and the contract lists each sentence', () => {
    const contract = JSON.parse(readFileSync(resolve(__dirname, '../../../../contracts/api/v1/openapi.json'), 'utf-8'));
    const description: string = contract.paths['/runs/{run_id}/start-from-stage'].post.description;
    const listed = [...description.matchAll(/`(source_[a-z_]+)`/g)].map((match) => match[1]!).sort();
    expect(listed.length).toBeGreaterThan(0);
    expect([...REUSE_REFUSAL_REASONS].sort()).toEqual([...new Set(listed)]);
  });
});
