/**
 * `AR-V3-OPT-IN` (design 4.4 and 4.6): the run page's «Анализ» line.
 *
 * A run of AR v3 (beta) always says so, with its scope and a link to its group's review: it is the run that is not the
 * default, and it stays named when the deployment later stops allowing starts. A standard run says «Стандартный» only where
 * the deployment allows a start of v3 (`start_allowed`), so a deployment with one analysis shows no line about the other.
 * Only a standard run asks the server; a v3 run needs no answer. A reading from a server that predates `analysis_kind` is
 * judged by its profile id.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { AR_V3_BETA_PROFILE_ID } from '@/entities/audit-run';
import { RunProgress } from '@/widgets/run-progress';

import { NOT_INSTALLED_PACK, installedPackFixture } from '../analysis-settings/ar-v3-beta-pack-fixtures';
import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from './harness';

const PACK = queryKeys.runs.arV3PackStatus();
const GROUP = 'arg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const MEMBER: Partial<RunStatus> = {
  analysis_kind: 'ar_v3_beta',
  analysis_profile_id: AR_V3_BETA_PROFILE_ID as NonNullable<RunStatus['analysis_profile_id']>,
  ar_v3_group_id: GROUP as NonNullable<RunStatus['ar_v3_group_id']>,
  ar_v3_scope_id: 'A2',
};

function page(overrides: Partial<RunStatus>, pack?: unknown): { markup: string; asked: boolean } {
  const status = runStatus(overrides);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  if (pack !== undefined) client.setQueryData(PACK, pack);
  const markup = renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
  // The query exists in the cache once something has used the hook (a static render attaches no observer), so an unseeded
  // cache that holds it afterwards is a page that asked.
  return { markup, asked: client.getQueryCache().find({ queryKey: PACK }) !== undefined };
}

const LINE = 'data-run-analysis=';

describe('a run of AR v3 (beta) is always named', () => {
  for (const [name, pack] of [
    ['no answer of the status', undefined],
    ['starts allowed', installedPackFixture({ start_allowed: true })],
    ['starts not allowed', installedPackFixture({ start_allowed: false })],
    ['no pack', NOT_INSTALLED_PACK],
  ] as const) {
    it(`${name}: «Анализ», the scope and the link to the group`, () => {
      const { markup } = page(MEMBER, pack);
      expect(markup).toContain('<dt>Анализ</dt>');
      expect(markup).toContain('data-run-analysis="ar_v3_beta"');
      expect(markup).toContain('data-run-scope="A2"');
      expect(markup).toContain('АР v3 (бета) · A2');
      expect(markup).toContain(`href="/analysis-settings?group_id=${GROUP}"`);
    });
  }

  it('asks the server nothing: it needs no answer to say what it is', () => {
    expect(page(MEMBER).asked).toBe(false);
    expect(page({ analysis_kind: 'standard' }).asked, 'the control: a standard run does ask').toBe(true);
  });

  it('is named by its profile id when the server does not send the field', () => {
    const { markup } = page({ analysis_profile_id: AR_V3_BETA_PROFILE_ID as NonNullable<RunStatus['analysis_profile_id']> });
    expect(markup).toContain('data-run-analysis="ar_v3_beta"');
    expect(markup).toContain('АР v3 (бета)');
  });
});

describe('a standard run is named only where both analyses are on offer', () => {
  it('says «Стандартный» where starts of v3 are allowed', () => {
    const { markup } = page({ analysis_kind: 'standard' }, installedPackFixture({ start_allowed: true }));
    expect(markup).toContain('<dt>Анализ</dt>');
    expect(markup).toContain('data-run-analysis="standard"');
    expect(markup).toContain('Стандартный');
    expect(markup).not.toContain('analysis-settings?group_id');
  });

  for (const [name, pack] of [
    ['no answer of the status yet', undefined],
    ['starts not allowed', installedPackFixture({ start_allowed: false })],
    ['a server that does not say', installedPackFixture()],
    ['no pack', NOT_INSTALLED_PACK],
    ['an allowance that is not a boolean', { ...installedPackFixture(), start_allowed: 'true' }],
    ['an undeclared state', { state: 'withdrawn', start_allowed: true }],
  ] as const) {
    it(`${name}: no line, the page is the page it was`, () => {
      const { markup } = page({ analysis_kind: 'standard' }, pack);
      expect(markup).not.toContain(LINE);
      expect(markup).not.toContain('<dt>Анализ</dt>');
      expect(markup).not.toContain('Стандартный');
    });
  }

  it('a reading with no analysis_kind and no v3 profile is a standard run', () => {
    const named = page({}, installedPackFixture({ start_allowed: true })).markup;
    expect(named).toContain('data-run-analysis="standard"');
    expect(page({}, NOT_INSTALLED_PACK).markup).not.toContain(LINE);
  });
});
