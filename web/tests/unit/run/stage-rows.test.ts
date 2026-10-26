/**
 * Stage rows.
 *
 * A stage the run has not reported is a visible row with no status, not an absent row.
 * The difference matters: an absent row says "there is nothing to say about this stage",
 * which is a different claim from "this stage has not run".
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus, StageId, StageState } from '@/shared/api';
import { STAGE_ID_VALUES } from '@/shared/api';
import { AR_V3_BETA_PROFILE_ID, PC01_STAGE_IDS, STAGE_DEPENDS_ON, StageTable, hasKnownRunVocabulary, stageRows } from '@/entities/audit-run';

function reading(state: RunState, stages: StageState[], analysisProfileId?: string): RunStatus {
  return {
    run_id: 'run_01M2545JSD15ETSNNV904X991J',
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state,
    stages,
    ...(analysisProfileId === undefined ? {} : { analysis_profile_id: analysisProfileId }),
  };
}

describe('the four stages PC-01 schedules', () => {
  it('are the first four of the contract registry, in order', () => {
    expect(PC01_STAGE_IDS).toEqual([
      'source_preparation',
      'page_geometry_extraction',
      'document_context_build',
      'text_analysis',
    ]);
    expect(STAGE_ID_VALUES.slice(0, 4)).toEqual(PC01_STAGE_IDS);
  });

  it('always produce four rows, even when the run has reported nothing', () => {
    const rows = stageRows(reading('queued', []));
    expect(rows).toHaveLength(4);
    expect(rows.map((r) => r.stageId)).toEqual(PC01_STAGE_IDS);
    for (const row of rows) {
      expect(row.status).toBeNull();
      expect(row.expected).toBe(true);
    }
  });

  it('numbers the scheduled stages from one, in the order they run', () => {
    // `D-62`: the order was in the data and not in the markup. Row order IMPLIED a
    // sequence and asserted nothing, so the table now carries the position as a value.
    const rows = stageRows(reading('queued', []));
    expect(rows.map((r) => r.ordinal)).toEqual([1, 2, 3, 4]);
  });

  it('carries each stage\u2019s declared dependency, which is what survives a fork', () => {
    const rows = stageRows(reading('queued', []));
    expect(rows.map((r) => [...r.dependsOn])).toEqual([
      [],
      ['source_preparation'],
      ['page_geometry_extraction'],
      ['document_context_build'],
    ]);
    // From the one map, so a dependency cannot be right in the table and wrong in the
    // model. `stage-vocabulary.guard.test.ts` holds that map to the analysis contract.
    for (const row of rows) expect(row.dependsOn).toBe(STAGE_DEPENDS_ON[row.stageId as StageId]);
  });
});

describe('a reported stage fills its row', () => {
  it('carries the status, the error code and the timestamps', () => {
    const rows = stageRows(
      reading('running', [
        {
          stage_id: 'source_preparation',
          status: 'succeeded',
          started_at: '2026-01-01T00:00:01Z',
          finished_at: '2026-01-01T00:00:09Z',
        },
        { stage_id: 'page_geometry_extraction', status: 'failed', error_code: 'analysis_failed' },
      ]),
    );

    expect(rows[0]?.status).toBe('succeeded');
    expect(rows[0]?.errorCode).toBeNull();
    expect(rows[0]?.startedAt).toBe('2026-01-01T00:00:01Z');
    expect(rows[1]?.status).toBe('failed');
    expect(rows[1]?.errorCode).toBe('analysis_failed');
    // The two the run has not reached are still rows.
    expect(rows[2]?.status).toBeNull();
    expect(rows[3]?.status).toBeNull();
  });

  it('carries a skipped stage as skipped rather than dropping it', () => {
    const rows = stageRows(reading('partial', [{ stage_id: 'text_analysis', status: 'skipped' }]));
    expect(rows.find((r) => r.stageId === 'text_analysis')?.status).toBe('skipped');
  });
});

describe('a stage PC-01 does not schedule is shown, and marked as such', () => {
  it('pins the v3 profile to the existing analysis-stage contract', () => {
    const extension = JSON.parse(readFileSync(
      resolve(process.cwd(), '../contracts/analysis/ar_v3_beta/v1/stage.json'), 'utf8',
    )) as { analysis_profile_id: string };
    expect(AR_V3_BETA_PROFILE_ID).toBe(extension.analysis_profile_id);
  });

  it('shows no legacy placeholders before a v3 Run reports its stage', () => {
    const status = reading('queued', [], AR_V3_BETA_PROFILE_ID);
    expect(hasKnownRunVocabulary(status)).toBe(true);
    const rows = stageRows(status);
    expect(rows).toEqual([]);
    const markup = renderToStaticMarkup(createElement(StageTable, { rows }));
    expect(markup).toContain('Сведения об этапах пока не поступили.');
    expect(markup).not.toContain('data-stage-id=');
    expect(stageRows(reading('queued', [], 'ap_unknown'))).toHaveLength(4);
  });

  it('shows a reported v3 citation review without inventing four legacy stages', () => {
    const status = reading('published', [
      { stage_id: 'ar_v3_citation_review', status: 'succeeded' },
    ], AR_V3_BETA_PROFILE_ID);
    const rows = stageRows(status);
    expect(hasKnownRunVocabulary(status)).toBe(true);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      stageId: 'ar_v3_citation_review', status: 'succeeded', expected: true,
      ordinal: null, dependsOn: [],
    });
    const markup = renderToStaticMarkup(createElement(StageTable, { rows }));
    expect(markup).toContain('Предварительная проверка нормативных ссылок АР v3');
    expect(markup).toContain('этап отдельного профиля АР v3');
    expect(markup).not.toContain('первый этап');
    expect(markup).not.toContain('на этом этапе не планируется');
  });

  it('refuses a v3 stage reported under another or missing profile', () => {
    const v3Stage: StageState = { stage_id: 'ar_v3_citation_review', status: 'succeeded' };
    expect(hasKnownRunVocabulary(reading('published', [v3Stage], 'ap_unknown'))).toBe(false);
    expect(hasKnownRunVocabulary(reading('published', [v3Stage]))).toBe(false);
  });

  it('appends it after the four, flagged as unexpected', () => {
    const rows = stageRows(
      reading('running', [
        { stage_id: 'source_preparation', status: 'succeeded' },
        { stage_id: 'norm_verification', status: 'partial', error_code: 'required_norm_unavailable' },
      ]),
    );

    expect(rows).toHaveLength(5);
    const extra = rows[4];
    expect(extra?.stageId).toBe('norm_verification');
    expect(extra?.expected).toBe(false);
    expect(extra?.status).toBe('partial');
    expect(extra?.errorCode).toBe('required_norm_unavailable');
    // NOT numbered. The contract's nine stages fork -- `norm_verification` waits on
    // `finding_merge`, as does `finding_review` -- so a position for a stage outside the
    // schedule would assert an order the registry does not declare. It states its
    // dependency instead, which stays true whatever else the run scheduled.
    expect(extra?.ordinal).toBeNull();
    expect(extra?.dependsOn).toEqual(['finding_merge']);
  });

  it('does not duplicate a stage that is both expected and reported', () => {
    const rows = stageRows(
      reading('running', [{ stage_id: 'document_context_build', status: 'succeeded' }]),
    );
    expect(rows.filter((r) => r.stageId === 'document_context_build')).toHaveLength(1);
  });
});
