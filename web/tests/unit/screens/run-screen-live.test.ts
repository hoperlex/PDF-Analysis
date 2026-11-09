/**
 * `RUN-SCREEN-01a`: the run screen, live -- what a press does. A chip opens «Этапы анализа раздела» on it, the list inside moves
 * between chips, «Закрыть» closes it, the tabs switch, and «Запустить с этого этапа» starts from the stage of the chip with no select to
 * choose from, under the same consent and key as the control has always used.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }), usePathname: () => '/', useSearchParams: () => new URLSearchParams() }));
vi.mock('@/shared/config/review-indication', () => ({ SHOW_REVIEW_INDICATION: true }));
vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getRunStatus: vi.fn(), getExtendedRunReview: vi.fn(), listRunFindings: vi.fn(), estimateRunCost: vi.fn(), startRunFromStage: vi.fn(),
}));

import { estimateRunCost, getExtendedRunReview, getRunStatus, listRunFindings, queryKeys, startRunFromStage } from '@/shared/api';
import type { RunStatus, StageId } from '@/shared/api';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { APPROVE_COST, COST_CONSENT, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from './harness';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const NEW_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8N';
const PREP: readonly StageId[] = ['source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis'];
let live: LiveRender | null = null;

const REVIEW = { run_id: RUN_ID, status: 'completed', result: { workflow_version: 'extended-review-v3', procedures: [
  { id: 'block_analysis', title: 'Анализ блоков', status: 'completed' },
  { id: 'finding_merge', title: 'Свод наблюдений', status: 'completed' },
] } };

const ended = (over: Partial<RunStatus> = {}): RunStatus => ({
  ...runStatus(), run_id: RUN_ID, state: 'published', version_uid: VERSION_UID,
  stages: PREP.map((stage_id) => ({ stage_id, status: 'succeeded' as const, error_code: null })), ...over,
});

beforeEach(() => {
  vi.resetAllMocks();
  push.mockReset();
  vi.mocked(getRunStatus).mockImplementation(async () => ({ data: ended() }) as never);
  vi.mocked(getExtendedRunReview).mockResolvedValue({ data: REVIEW } as never);
  vi.mocked(listRunFindings).mockResolvedValue({ data: { items: [], page: { next_cursor: null } } } as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: {
    ...costEstimate({ version_uid: (body as { version_uid: string }).version_uid }),
    start_from_run_id: (body as { start_from_run_id?: string }).start_from_run_id,
    start_stage_id: (body as { start_stage_id?: string }).start_stage_id,
    reused_stage_ids: ['source_preparation', 'page_geometry_extraction', 'document_context_build'], computed_stage_ids: ['text_analysis'],
  } }) as never);
  vi.mocked(startRunFromStage).mockResolvedValue({ data: { ...runStatus(), run_id: NEW_RUN, project_uid: PROJECT_UID,
    started_from_run_id: RUN_ID, start_stage_id: 'text_analysis' } as RunStatus } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

async function mount(status: RunStatus = ended(), props: Record<string, unknown> = {}) {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID as never), status);
  client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
  live = await mountLive(createElement(QueryClientProvider, { client },
    createElement(RunProgress, { projectUid: PROJECT_UID, runId: RUN_ID, ...props })));
  await live.settle(() => undefined);
  return live;
}

describe('the rail opens the dialog', () => {
  it('on the chip that was pressed, and the list inside moves between chips', async () => {
    const view = await mount();
    expect(view.markup()).not.toContain('data-run-stages-dialog');
    await view.pressMarked('data-run-chip', 'text');
    expect(view.markup()).toContain('data-run-stages-dialog');
    expect(view.markup()).toContain('data-run-stage-detail="text"');
    await view.pressMarked('data-stage-item', 'preparation');
    expect(view.markup()).toContain('data-run-stage-detail="preparation"');
    expect(view.markup()).not.toContain('data-run-stage-detail="text"');
    // The chips the extended review added are in the list too.
    await view.pressMarked('data-stage-item', 'blocks');
    expect(view.markup()).toContain('data-extended-procedure="block_analysis"');
  });

  it('closes with «Закрыть» and leaves the page as it was', async () => {
    const view = await mount();
    await view.pressMarked('data-run-chip', 'preparation');
    await view.press('Закрыть');
    expect(view.markup()).not.toContain('data-run-stages-dialog');
    expect(view.markup()).toContain('data-run-rail=""');
  });
});

describe('the tabs', () => {
  it('switch to the journal and back, and mount the journal only while it is open', async () => {
    const view = await mount(ended(), { journal: createElement('p', { 'data-test-journal': '' }, 'СОБЫТИЯ') });
    expect(view.markup()).not.toContain('СОБЫТИЯ');
    await view.pressMarked('data-run-tab', 'journal');
    expect(view.markup()).toContain('СОБЫТИЯ');
    expect(view.markup()).not.toContain('data-run-spend=');
    expect(view.markup()).toMatch(/data-run-tab="journal"[^>]*|aria-selected="true"[^>]*data-run-tab="journal"/);
    await view.pressMarked('data-run-tab', 'overview');
    expect(view.markup()).not.toContain('СОБЫТИЯ');
    expect(view.markup()).toContain('data-run-spend=');
  });
});

describe('«Запустить с этого этапа»', () => {
  it('starts from the stage of the chip with no select, under the consent the control has always asked', async () => {
    const view = await mount();
    await view.pressMarked('data-run-chip', 'text');
    await view.press('Запустить с этого этапа');
    expect(view.markup()).toContain('data-start-from-stage-only="text_analysis"');
    const form = /<section[^>]*data-run-start-from-stage="dialog">.*?<\/section>/s.exec(view.markup())?.[0] ?? '';
    expect(form).toContain('data-start-from-stage-only');
    expect(form).not.toContain('<select');
    for (let tick = 0; tick < 20 && view.markup().includes('Загрузка: оценка стоимости запуска с этапа'); tick += 1) await view.settle(() => undefined);
    expect(estimateRunCost).toHaveBeenCalledWith(
      { body: { version_uid: VERSION_UID, start_from_run_id: RUN_ID, start_stage_id: 'text_analysis' } },
      expect.objectContaining({ signal: expect.anything() }));
    expect(startRunFromStage).not.toHaveBeenCalled();
    await view.check(APPROVE_COST, true);
    await view.press('Запустить');
    expect(vi.mocked(startRunFromStage).mock.calls[0]![0]).toEqual({
      path: { run_id: RUN_ID }, body: { stage_id: 'text_analysis', cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String),
    });
    expect(push).toHaveBeenCalledWith(`/projects/${PROJECT_UID}/runs/${NEW_RUN}`);
  });

  it('offers only the stages of the chip it is opened on when the chip has several', async () => {
    const view = await mount();
    await view.pressMarked('data-run-chip', 'preparation');
    await view.press('Запустить с этого этапа');
    const form = /<section[^>]*data-run-start-from-stage="dialog">.*?<\/section>/s.exec(view.markup())?.[0] ?? '';
    expect(form).toContain('<option value="page_geometry_extraction">');
    expect(form).toContain('<option value="document_context_build">');
    expect(form).not.toContain('<option value="text_analysis">');
    expect(form).not.toContain('<option value="source_preparation">');
    expect(estimateRunCost).not.toHaveBeenCalled();
  });
});
