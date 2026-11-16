/**
 * `UIP-G-09`: another version, or the neighbouring document, opens on the same tab. The addresses are pure functions of
 * the tab and of what is known of the place they lead to, so each claim is read as data.
 */

import { describe, expect, it } from 'vitest';

import type { DocumentAudit } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  levelAddress,
  levelNeedsRuns,
  runLogAddress,
  targetOfAudit,
  targetOfRuns,
  versionChoiceLevel,
} from '@/widgets/document-context';
import type { TabLevel, TabTarget } from '@/widgets/document-context';

import { RUN_ID, runStatus } from '../review/fixtures';

const BASE = { projectUid: 'prj_A', documentUid: 'doc_D', versionUid: 'ver_V' } as const;
const WITH_RUNS: TabTarget = { ...BASE, resultRunId: 'run_RESULT', latestRunId: 'run_LATEST' };
const WITHOUT_RUNS: TabTarget = { ...BASE, resultRunId: null, latestRunId: null };

describe('levelAddress', () => {
  it('keeps a tab of the version on that tab of the other version', () => {
    expect(levelAddress('version', WITH_RUNS)).toBe(routes.version('prj_A', 'ver_V'));
    expect(levelAddress('blocks', WITH_RUNS)).toBe(routes.versionBlocks('prj_A', 'ver_V'));
  });

  it('opens the latest result run for «Разбор» and the latest run on its journal for «Лог», and the run itself for a run', () => {
    expect(levelAddress('review', WITH_RUNS)).toBe(routes.review('prj_A', 'run_RESULT'));
    expect(levelAddress('log', WITH_RUNS)).toBe(runLogAddress('prj_A', 'run_LATEST'));
    expect(levelAddress('log', WITH_RUNS)).toBe(`${routes.run('prj_A', 'run_LATEST')}?tab=journal`);
    expect(levelAddress('run', WITH_RUNS)).toBe(routes.run('prj_A', 'run_LATEST'));
  });

  it('opens the version’s «Инфо» where the tab needs a run the version does not have — never a link to nowhere', () => {
    for (const level of ['review', 'log', 'run'] as const) {
      expect(levelAddress(level, WITHOUT_RUNS), level).toBe(routes.version('prj_A', 'ver_V'));
    }
    // a version with a run but no result still has a journal, and no «Разбор»
    const failed: TabTarget = { ...WITHOUT_RUNS, latestRunId: 'run_LATEST' };
    expect(levelAddress('review', failed)).toBe(routes.version('prj_A', 'ver_V'));
    expect(levelAddress('log', failed)).toBe(runLogAddress('prj_A', 'run_LATEST'));
  });

  it('keeps the document’s own pages on the document', () => {
    expect(levelAddress('document', WITH_RUNS)).toBe(routes.document('prj_A', 'doc_D'));
    expect(levelAddress('optimisation', WITH_RUNS)).toBe(routes.documentOptimisation('prj_A', 'doc_D'));
  });

  it('covers every level: none is left without an address', () => {
    const levels: readonly TabLevel[] = ['document', 'optimisation', 'version', 'blocks', 'log', 'run', 'review'];
    for (const level of levels) expect(levelAddress(level, WITH_RUNS), level).toMatch(/^\/projects\/prj_A\//);
  });
});

describe('the target of a version', () => {
  it('is worked out from its runs, newest first: the result is the newest that published one, the latest is the newest of any state', () => {
    const runs = [
      runStatus({ run_id: 'run_C', state: 'running' }),
      runStatus({ run_id: 'run_B', state: 'published' }),
      runStatus({ run_id: 'run_A', state: 'failed' }),
    ];
    expect(targetOfRuns(BASE, runs)).toEqual({ ...BASE, resultRunId: 'run_B', latestRunId: 'run_C' });
    expect(targetOfRuns(BASE, [runStatus({ run_id: RUN_ID, state: 'failed' })])).toEqual({ ...BASE, resultRunId: null, latestRunId: RUN_ID });
    expect(targetOfRuns(BASE, [])).toEqual({ ...BASE, resultRunId: null, latestRunId: null });
    expect(targetOfRuns(BASE, undefined)).toEqual({ ...BASE, resultRunId: null, latestRunId: null });
  });

  it('is worked out from a listing’s audit: the result run, and the run in flight when there is one', () => {
    const audit = (over: Partial<DocumentAudit>): DocumentAudit => ({
      finding_count: 0, undecided_finding_count: 0, partial: false, state: 'not_run', ...over,
    });
    expect(targetOfAudit(BASE, audit({ result_run_id: 'run_R', state: 'checked' }))).toEqual({ ...BASE, resultRunId: 'run_R', latestRunId: 'run_R' });
    expect(targetOfAudit(BASE, audit({ result_run_id: 'run_R', active_run: { run_id: 'run_N', state: 'running' } })))
      .toEqual({ ...BASE, resultRunId: 'run_R', latestRunId: 'run_N' });
    expect(targetOfAudit(BASE, audit({}))).toEqual({ ...BASE, resultRunId: null, latestRunId: null });
    expect(targetOfAudit(BASE, undefined)).toEqual({ ...BASE, resultRunId: null, latestRunId: null });
  });
});

describe('choosing another version', () => {
  it('keeps every tab of the version, and sends the document’s own pages to the chosen version’s «Инфо»', () => {
    for (const level of ['version', 'blocks', 'log', 'run', 'review'] as const) expect(versionChoiceLevel(level), level).toBe(level);
    expect(versionChoiceLevel('document')).toBe('version');
    expect(versionChoiceLevel('optimisation')).toBe('version');
  });

  it('needs the runs of the chosen version only for the tabs that open a run', () => {
    expect(['document', 'optimisation', 'version', 'blocks', 'log', 'run', 'review'].filter((level) => levelNeedsRuns(level as TabLevel)))
      .toEqual(['log', 'run', 'review']);
  });
});
