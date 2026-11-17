/**
 * `UIP-S04-03`: the card «Последний прогон», the first card of the version's «Инфо».
 *
 * What is held: the card says when the last run was and how it stands, in a word, and opens the run; its row of stages has one button for
 * each chip of the run with the chip's name, its state in a word and the time it took, and the chips are the run page's (the status's,
 * completed by the stages the server read: a chip only the stages list is drawn from them, and where both speak the stages' words are the
 * chip's); no token, no cost and no model is on the card, and the model of a stage is in the chip's hint for an administrator only; a
 * press on a stage opens the run page's own window «Этапы анализа раздела», with «Запустить с этого этапа» for an account that may start
 * a run and not for one that may not; «Запустить» is the one control of `R-153a` with its line under it, in the card, and a version with
 * no run says so and offers the same button; the card reads the progress once (the list the table reads, and the stages of the newest
 * run), and a run still going says its progress is on the run page; the table of runs, told the start is elsewhere, is the table alone.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: () => undefined }), usePathname: () => '/', useSearchParams: () => new URLSearchParams() }));
vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  // The start's own read never answers: the card is judged by what it draws, not by the readiness line.
  getRunStartReadiness: vi.fn(() => new Promise(() => undefined)),
}));

import type { RunStage, RunStageFacts, RunStages, RunStatus, StageState } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { RUN_PAGE_LIMIT, runStagesKey } from '@/entities/audit-run';
import { LastRunCard, RunList, chipHint, lastRunChips, reusedStageIdsOf } from '@/widgets/run-list';

import { PROJECT_UID, RUN_ID, VERSION_UID, runStatus } from '../review/fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient, renderScreen } from '../screens/harness';

const OTHER_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';

const at = (time: string) => `2026-09-10T${time}Z`;
const row = (stage_id: StageState['stage_id'], from: string, to: string): StageState => ({
  stage_id, status: 'succeeded', error_code: null, started_at: at(from), finished_at: at(to),
});
/** The four stages PC-01 runs: preparation takes 30 s, the text analysis 1 min 30 s. */
const PC01: StageState[] = [
  row('source_preparation', '08:00:00', '08:00:05'),
  row('page_geometry_extraction', '08:00:05', '08:00:20'),
  row('document_context_build', '08:00:20', '08:00:30'),
  row('text_analysis', '08:00:30', '08:02:00'),
];

const ENDED = (over: Partial<RunStatus> = {}): RunStatus => runStatus({ stages: PC01, ...over });

const FACTS: RunStageFacts = {
  state: 'done', calls_succeeded: 0, calls_failed: 0, calls_retried: 0, input_tokens: 0, output_tokens: 0,
  subscription_input_tokens: 0, subscription_output_tokens: 0, cost_micros: 0,
};
const stage = (chip: RunStage['chip'], facts: Partial<RunStageFacts>, models: string[] = []): RunStage => ({
  chip,
  stage_ids: ['x'],
  plan: models.map((model_id, index) => ({ role: models.length === 1 ? 'main' : index === 0 ? 'leg1' : 'judge', model_id, effort: 'medium' as const })),
  facts: { ...FACTS, ...facts },
});
const STAGES: RunStages = {
  run_id: RUN_ID, state: 'published', plan_source: 'stage_plan',
  items: [
    stage('preparation', { started_at: at('08:00:00'), finished_at: at('08:00:30') }),
    stage('text', { started_at: at('08:00:30'), finished_at: at('08:02:00'), input_tokens: 61240, cost_micros: 99000 }, ['claude-opus-5-5']),
    stage('blocks', { started_at: at('08:02:00'), finished_at: at('08:03:00'), input_tokens: 102400 }, ['claude-opus-5-5', 'claude-sonnet-5-5']),
    stage('cross_check', { state: 'partial', started_at: at('08:03:00'), finished_at: at('08:03:20') }),
  ],
};

interface Options {
  readonly runs?: readonly RunStatus[] | 'failed' | 'cold';
  readonly stages?: RunStages | null;
  readonly roles?: readonly string[];
  readonly open?: Parameters<typeof LastRunCard>[0]['initiallyOpenChip'];
  readonly uploadKind?: 'comparison_pdf';
}

function clientOf({ runs = [ENDED()], stages = STAGES, roles }: Options) {
  const client = newClient();
  if (runs === 'failed') {
    // an entry in the error state: the card says so and keeps the start
    const query = client.getQueryCache().build(client, client.defaultQueryOptions({ queryKey: [...queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT)] }));
    query.setState({ status: 'error', error: new Error('down') as never, fetchStatus: 'idle', dataUpdatedAt: 0, errorUpdatedAt: Date.now(), fetchFailureCount: 1 });
  } else if (runs !== 'cold') {
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), { items: runs, page: { next_cursor: null } });
    const latest = runs[0];
    if (latest !== undefined) client.setQueryData(queryKeys.runs.detail(latest.run_id), latest);
    if (latest !== undefined && stages !== null) client.setQueryData(runStagesKey(latest.run_id), stages);
  }
  if (roles !== undefined) client.setQueryData(queryKeys.account.me(), { roles });
  return client;
}

const card = (options: Options = {}) =>
  renderScreen(clientOf(options), createElement(LastRunCard, {
    projectUid: PROJECT_UID, versionUid: VERSION_UID, initiallyOpenChip: options.open, uploadKind: options.uploadKind,
  }));

/** The part of the card outside the window a press opens. */
const withoutWindow = (markup: string) => markup.replace(/<dialog[\s\S]*?<\/dialog>/, '');

describe('the run', () => {
  const markup = card();

  it('says when the last run was and how it stands, in a word, and opens the run', () => {
    expect(markup).toContain('data-last-run-card=');
    expect(markup).toContain('>Последний прогон</h2>');
    expect(markup).toContain(`data-last-run-id="${RUN_ID}"`);
    expect(markup).toMatch(/Прогон от <time dateTime="2026-09-10T08:00:00.000Z">\d\d\.\d\d\.\d{4} \d\d:\d\d<\/time>/);
    expect(markup).toMatch(/data-run-state="published"/);
    expect(markup).toContain('>опубликован<');
    expect(markup).toMatch(new RegExp(`data-last-run-open=""[^>]*href="${routes.run(PROJECT_UID, RUN_ID)}"[^>]*>Открыть прогон<`));
  });

  it('is the newest run of the list and no other', () => {
    const newest = ENDED({ run_id: OTHER_RUN, created_at: '2026-09-11T08:00:00.000Z' });
    const two = card({ runs: [newest, ENDED()], stages: null });
    expect(two).toContain(`data-last-run-id="${OTHER_RUN}"`);
    expect(two).not.toContain(`data-last-run-id="${RUN_ID}"`);
  });

  it('says a run that is still going shows its progress on its own page, and says nothing of the kind for a run that is over', () => {
    const going = card({ runs: [ENDED({ state: 'running', terminal_at: null })], stages: null });
    expect(going).toContain('data-last-run-live=');
    expect(going).toContain('ход виден на странице прогона');
    expect(markup).not.toContain('data-last-run-live');
  });
});

describe('the row of stages', () => {
  const markup = card();

  it('has one button for each chip of the run, in the run page’s order, each with its name, its state in a word and the time it took', () => {
    const chips = [...markup.matchAll(/data-last-run-chip="([a-z_]+)"/g)].map((found) => found[1]);
    expect(chips).toEqual(['preparation', 'text', 'blocks', 'cross_check']);
    expect(markup).toContain('aria-label="Этапы последнего прогона"');
    // preparation 30 s, text 1 min 30 s, blocks 1 min 0 s
    expect(markup).toMatch(/data-last-run-chip="preparation"[^>]*data-chip-state="done"[\s\S]*?Подготовка<\/span><span[^>]*><span>выполнен<\/span><span[^>]*>30 с</);
    expect(markup).toMatch(/data-last-run-chip="text"[\s\S]*?Текст[\s\S]*?выполнен[\s\S]*?1 мин 30 с</);
    expect(markup).toMatch(/data-last-run-chip="blocks"[\s\S]*?Блоки[\s\S]*?1 мин 0 с</);
  });

  it('draws a chip only the stages list, and gives it the stages’ state in words', () => {
    expect(markup).toMatch(/data-last-run-chip="cross_check"[^>]*data-chip-state="partial"[\s\S]*?Сверка[\s\S]*?частично[\s\S]*?20 с</);
  });

  it('draws the chips of the status alone before the stages are read, and then has no chip the status has no row for', () => {
    const before = card({ stages: null });
    expect([...before.matchAll(/data-last-run-chip="([a-z_]+)"/g)].map((found) => found[1])).toEqual(['preparation', 'text']);
    expect(before).toMatch(/data-last-run-chip="preparation"[^>]*data-chip-state="done"[\s\S]*?30 с</);
  });

  it('says «из прогона» for a chip taken from the run this one was started from, and no time', () => {
    const resumed = ENDED({ started_from_run_id: OTHER_RUN, start_stage_id: 'text_analysis' });
    const markup = card({ runs: [resumed], stages: null });
    expect(markup).toMatch(/data-last-run-chip="preparation"[\s\S]*?выполнен<\/span><span[^>]*>из прогона</);
    expect(markup).toMatch(/data-last-run-chip="text"[\s\S]*?выполнен<\/span><span[^>]*>1 мин 30 с</);
  });
});

describe('what is not on the card', () => {
  it('has no token, no cost and no model line in the row of stages, though the stages say them', () => {
    // The start control under the row has its own words (its menu item speaks of the money ceiling); the row and the run's head are judged.
    const markup = withoutWindow(card({ roles: ['expert'] }));
    const row = /<div class="_head[\s\S]*?<\/ol>/.exec(markup)?.[0] ?? '';
    expect(row).toContain('data-last-run-chips');
    for (const absent of ['61', '102', 'токен', 'Токен', 'входных', 'Стоимость', '$', 'Opus', 'Sonnet', 'claude-', 'data-chip-model', 'вызов']) {
      expect(row, absent).not.toContain(absent);
    }
    for (const absent of ['входных', 'Стоимость', 'Opus', 'Sonnet', 'claude-', 'data-chip-model']) {
      expect(markup, absent).not.toContain(absent);
    }
  });

  it('puts the model of a stage in its hint for an administrator, and for nobody else', () => {
    const admin = withoutWindow(card({ roles: ['admin'] }));
    expect(admin).toMatch(/data-last-run-chip="text"[^>]*title="Анализ текста · Модель: Opus 5.5"/);
    expect(admin).toMatch(/data-last-run-chip="blocks"[^>]*title="Анализ блоков · Модели: Opus 5.5 · Sonnet 5.5"/);
    // a chip that calls no model, and one with no plan, have the name alone
    expect(admin).toMatch(/data-last-run-chip="preparation"[^>]*title="Подготовка документа"/);
    expect(admin).toMatch(/data-last-run-chip="cross_check"[^>]*title="Комплексная сверка"/);
    for (const roles of [['expert'], ['viewer']]) {
      const markup = withoutWindow(card({ roles }));
      expect(markup, roles.join()).toMatch(/data-last-run-chip="text"[^>]*title="Анализ текста"/);
      expect(markup, roles.join()).not.toMatch(/Модель:|Модели:|Opus/);
    }
  });
});

describe('«Запустить»', () => {
  it('is the one button with its line under it, in the card, for a version with runs', () => {
    const markup = card();
    expect(markup.match(/data-start-run-button=""/g)).toHaveLength(1);
    expect(markup).toContain('data-start-readiness=""');
    expect(markup.indexOf('data-last-run-chips')).toBeLessThan(markup.indexOf('data-start-run-control'));
    // one card holds it: the button is inside the card's section
    expect(/<section[^>]*data-last-run-card=[\s\S]*data-start-run-button=""[\s\S]*<\/section>/.test(markup)).toBe(true);
  });

  it('is offered with «По этой версии прогонов не запускалось» when the version has no run, with no row of stages', () => {
    const markup = card({ runs: [] });
    expect(markup).toContain('По этой версии прогонов не запускалось.');
    expect(markup).toContain('data-start-run-button=""');
    expect(markup).not.toContain('data-last-run-chips');
    expect(markup).not.toContain('data-last-run-open');
  });

  it('is offered while the runs are read, and when they could not be, which the card says in a line', () => {
    const cold = card({ runs: 'cold' });
    expect(cold).toContain('Загрузка: прогоны этой версии…');
    expect(cold).toContain('data-start-run-button=""');
    const failed = card({ runs: 'failed' });
    expect(failed).toContain('data-last-run-failed=');
    expect(failed).toContain('data-start-run-button=""');
    expect(failed).not.toContain('data-last-run-chips');
  });

  it('says a comparison PDF is analysed without the portal’s markup', () => {
    expect(card({ uploadKind: 'comparison_pdf' })).toContain('Анализ будет выполнен по исходному PDF без разметки портала.');
    expect(card()).not.toContain('без разметки портала');
  });
});

describe('the window a press on a stage opens', () => {
  it('is the run page’s «Этапы анализа раздела» on the chip that was pressed, with its facts', () => {
    const markup = card({ open: 'text', roles: ['expert'] });
    expect(markup).toContain('data-run-stages-dialog=""');
    expect(markup).toContain('>Этапы анализа раздела<');
    expect(markup).toContain('data-run-stage-detail="text"');
    // the chips of the window are the card's chips, the one only the stages list among them
    expect(markup).toContain('data-stage-item="cross_check"');
    // what the card does not say, the window does
    expect(markup).toMatch(/data-fact-row="tokens"/);
  });

  it('offers «Запустить с этого этапа» to an account that may start a run, and not to one that may not', () => {
    expect(card({ open: 'text', roles: ['expert'] })).toContain('Запустить с этого этапа');
    expect(card({ open: 'text', roles: ['admin'] })).toContain('Запустить с этого этапа');
    const viewer = card({ open: 'text', roles: ['viewer'] });
    expect(viewer).toContain('data-run-stages-dialog=""');
    expect(viewer).not.toContain('Запустить с этого этапа');
  });

  it('is closed until a stage is pressed', () => {
    expect(card({ roles: ['expert'] })).not.toContain('data-run-stages-dialog');
  });
});

describe('the progress is read once', () => {
  it('asks the list the table reads (one key) and the stages of the newest run, and nothing else of the run', () => {
    const client = clientOf({});
    renderScreen(client, createElement(LastRunCard, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
    const keys = client.getQueryCache().findAll().map((query) => JSON.stringify(query.queryKey));
    expect(keys.filter((key) => key === JSON.stringify(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT)))).toHaveLength(1);
    expect(keys.filter((key) => key === JSON.stringify(runStagesKey(RUN_ID)))).toHaveLength(1);
    expect(keys.filter((key) => key.includes('journal') || key.includes('extended'))).toEqual([]);
  });

  it('asks for no stages of a version that has no run', () => {
    const client = clientOf({ runs: [] });
    renderScreen(client, createElement(LastRunCard, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
    const stages = client.getQueryCache().findAll({ queryKey: ['runs', 'stages'] });
    expect(stages.every((query) => query.state.fetchStatus === 'idle' && query.state.data === undefined)).toBe(true);
  });
});

describe('the table of runs, told the start is elsewhere', () => {
  const table = (runs: readonly RunStatus[]) => {
    const client = clientOf({ runs });
    return renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, startElsewhere: true }));
  };

  it('is the table alone: its rows, and no start and no heading above one', () => {
    const markup = table([ENDED()]);
    expect(markup).toContain(`data-run-count="1"`);
    expect(markup).toContain(`data-run-id="${RUN_ID}"`);
    expect(markup).not.toContain('data-start-run-control');
    expect(markup).not.toContain('Запустить ещё один прогон');
  });

  it('says nothing for a version with no run: the card says it', () => {
    expect(table([])).toBe('');
  });

  it('keeps the start under the table when it is not told, as it always did', () => {
    const client = clientOf({ runs: [ENDED()] });
    const markup = renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
    expect(markup).toContain('data-start-run-control');
    expect(markup).toContain('Запустить ещё один прогон');
  });
});

describe('every state the card’s rules branch on can be drawn (the census renders these two)', () => {
  const states = (markup: string) => new Set([...markup.matchAll(/data-last-run-chip="[a-z_]+"[^>]*data-chip-state="([a-z]+)"/g)].map((found) => found[1]));

  it('draws a chip done, partial, failed and running from the stages of a run that is going', () => {
    const going = card({
      runs: [ENDED({ state: 'running', terminal_at: null })],
      stages: {
        ...STAGES, state: 'running',
        items: [stage('preparation', {}), stage('text', { state: 'partial' }), stage('blocks', { state: 'failed' }), stage('cross_check', { state: 'running' })],
      },
    });
    expect(states(going)).toEqual(new Set(['done', 'partial', 'failed', 'running']));
  });

  it('draws the first chip of a queued run, whose stages are not read, as waiting', () => {
    expect(states(card({ runs: [runStatus({ state: 'queued', terminal_at: null })], stages: null }))).toEqual(new Set(['waiting', 'pending']));
  });
});

describe('the chips, as a function', () => {
  it('completes the status’s chips with the stages’ and lets the stages’ words win where both speak', () => {
    const chips = lastRunChips(ENDED(), {
      ...STAGES,
      items: [stage('text', { state: 'failed', started_at: at('08:00:30'), finished_at: at('08:00:40'), last_error_code: 'provider_error' })],
    });
    expect(chips.map((chip) => chip.definition.id)).toEqual(['preparation', 'text']);
    const text = chips.find((chip) => chip.definition.id === 'text');
    expect(text?.state).toBe('failed');
    expect(text?.elapsedMs).toBe(10_000);
    expect(text?.errorCode).toBe('provider_error');
    // the status's stage rows stay with the chip, so the window's table of code stages is the run page's
    expect(text?.stages.length).toBeGreaterThan(0);
    expect(chips.find((chip) => chip.definition.id === 'preparation')?.state).toBe('done');
  });

  it('keeps a chip the stages do not list, and draws none from nothing', () => {
    expect(lastRunChips(ENDED(), { ...STAGES, items: [] }).map((chip) => chip.definition.id)).toEqual(['preparation', 'text']);
    expect(lastRunChips(runStatus({ stages: [] }), null).map((chip) => chip.definition.id)).toEqual(['preparation', 'text']);
  });

  it('reuses the stages before the one the run started from, as the run page does', () => {
    expect(reusedStageIdsOf(ENDED())).toBeUndefined();
    expect([...(reusedStageIdsOf(ENDED({ started_from_run_id: OTHER_RUN, start_stage_id: 'text_analysis' })) ?? [])]).toEqual([
      'source_preparation', 'page_geometry_extraction', 'document_context_build',
    ]);
  });

  it('names the stage in the hint, and the model only to an administrator and only for a stage that has one', () => {
    const [preparation, text] = lastRunChips(ENDED(), STAGES);
    expect(chipHint(text!, STAGES, false)).toBe('Анализ текста');
    expect(chipHint(text!, STAGES, true)).toBe('Анализ текста · Модель: Opus 5.5');
    expect(chipHint(text!, null, true)).toBe('Анализ текста');
    expect(chipHint(preparation!, STAGES, true)).toBe('Подготовка документа');
  });
});

describe('a press on a stage, live', () => {
  let live: LiveRender | null = null;
  beforeEach(() => { live = null; });
  afterEach(async () => { await live?.unmount(); live = null; });

  it('opens the window on that stage, moves between stages, and closes, leaving the card as it was', async () => {
    const client = clientOf({ roles: ['expert'] });
    live = await mountLive(createElement(QueryClientProvider, { client },
      createElement(LastRunCard, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    await live.settle(() => undefined);
    expect(live.markup()).not.toContain('data-run-stages-dialog');
    await live.pressMarked('data-last-run-chip', 'text');
    expect(live.markup()).toContain('data-run-stages-dialog');
    expect(live.markup()).toContain('data-run-stage-detail="text"');
    expect(live.markup()).toContain('Запустить с этого этапа');
    await live.pressMarked('data-stage-item', 'cross_check');
    expect(live.markup()).toContain('data-run-stage-detail="cross_check"');
    await live.press('Закрыть');
    expect(live.markup()).not.toContain('data-run-stages-dialog');
    expect(live.markup()).toContain('data-last-run-chips=""');
  });
});
