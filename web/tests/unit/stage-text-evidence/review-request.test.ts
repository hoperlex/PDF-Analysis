import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageReviewRequest } from '@/widgets/stage-text-evidence';
import { reviewRequest, REVIEW_SOURCE_LIMIT } from '@/widgets/stage-text-evidence/model/review-request';
import { newClient, renderScreen } from '../screens/harness';

describe('recorded expert review request', () => {
  it('requires a reason and retains the whole canonical source set without truncation', () => {
    const ids = Array.from({ length: REVIEW_SOURCE_LIMIT }, (_, index) => `stf_${index}`);
    expect(reviewRequest(ids, '  Проверить смысл совпадения  ')).toEqual({ source_ids: ids, reason: 'Проверить смысл совпадения' });
    expect(reviewRequest([...ids, 'one-more'], 'Причина')).toBeNull();
    expect(reviewRequest(ids, '  ')).toBeNull();
    expect(reviewRequest([], 'Причина')).toBeNull();
    expect(ids).toHaveLength(REVIEW_SOURCE_LIMIT);
  });
  it('offers the expert act only to an allowed actor', () => {
    const props = { runId: 'crn_run', sourceIds: ['stf_source'], label: 'На экспертную проверку' };
    expect(renderScreen(newClient(), createElement(StageReviewRequest, { ...props, mayAct: false }))).not.toContain('На экспертную проверку');
    expect(renderScreen(newClient(), createElement(StageReviewRequest, { ...props, mayAct: true }))).toContain('На экспертную проверку');
  });
});
