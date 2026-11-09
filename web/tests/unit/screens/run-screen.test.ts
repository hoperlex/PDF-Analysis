/**
 * `RUN-SCREEN-01a` (plan `executors-runs-rework-plan` §9): the run screen as a head over two tabs, with its blocks where the plan put them.
 *
 * Rendered over a seeded cache, as `run-progress.test.ts` does; what must be pressed is in `tests/unit/run/run-screen-live.test.ts`. Measured here: what
 * the head says and no longer says, the tabs and their keyboard, the two tiles, the place of every block the page had, the dialog's
 * content and who is offered the start from a stage in it.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

// The wording of the beta screens is pinned ON, as `run-progress.test.ts` does.
vi.mock('@/shared/config/review-indication', () => ({ SHOW_REVIEW_INDICATION: true }));

import type { RunStatus, StageId } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { RunPage } from '@/_pages/run';
import { RunEvents } from '@/_pages/run/ui/run-events';
import { runChips } from '@/entities/audit-run';
import { RUN_TABS, RunHeader, RunProgress, maySeeServer, tabAfterKey } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, finding, observation, runStatus } from '../review/fixtures';
import { runDialog } from '../run/run-dialog-fixture';
import { newClient, renderScreen, renderWith } from './harness';

const PREP: readonly StageId[] = ['source_preparation', 'page_geometry_extraction', 'document_context_build'];
const ok = (stage_id: StageId, extra: Record<string, unknown> = {}) => ({ stage_id, status: 'succeeded' as const, error_code: null, ...extra });
const EXECUTOR = { connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', display_name: 'adm1.hlab.kz', pin_id: 'claude-opus-5-5' };

function seeded(over: Partial<RunStatus> = {}, extra: (client: ReturnType<typeof newClient>) => void = () => undefined) {
  const status = runStatus(over);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  extra(client);
  return { status, client };
}

function screen(over: Partial<RunStatus> = {}, props: Record<string, unknown> = {}, extra?: (client: ReturnType<typeof newClient>) => void): string {
  const { status, client } = seeded(over, extra);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id, ...props }));
}

const review = (runId: string, result: Record<string, unknown>) => (client: ReturnType<typeof newClient>) =>
  client.setQueryData(['extended-run-review', runId], { run_id: runId, status: 'running', result });

describe('the head', () => {
  it('states the run, the stages it has, a bar of one segment per stage and the way into «Разбор»', () => {
    const markup = screen({ stages: [...PREP, 'text_analysis' as const].map((id) => ok(id)) });
    expect(markup).toContain('data-run-head=""');
    expect(markup).toContain('data-run-state="published"');
    expect(markup).toContain('этапов завершено 2 из 2');
    expect(markup).toMatch(/role="progressbar"[^>]*aria-valuemax="2"[^>]*aria-valuenow="2"[^>]*aria-valuetext="завершено 2 из 2"/);
    expect(markup.match(/data-segment="done"/g)).toHaveLength(2);
    expect(markup).toMatch(/data-run-head=""[\s\S]*?Разобрать находки/);
  });

  it('counts «этап N из M» over the chips of this run while it is open, and draws the chip it is on as live', () => {
    const markup = screen({ state: 'running', terminal_at: null, stages: PREP.map((id) => ok(id)) });
    expect(markup).toContain('этап 2 из 2');
    expect(markup).toContain('data-run-stage-count="2/2"');
    expect(markup).toContain('data-segment="live"');
    expect(markup).toMatch(/data-run-chip="text"[^>]*data-chip-state="running"/);
  });

  it('no longer prints the provider mode or the sentence about polling, and keeps the attribute the journey reads', () => {
    for (const state of ['running', 'published'] as const) {
      const markup = screen({ state, ...(state === 'running' ? { terminal_at: null } : {}), provider_mode: 'live' });
      expect(markup).not.toContain('режим провайдера:');
      expect(markup).not.toContain('Идёт опрос');
      expect(markup).not.toContain('Опрос остановлен, показание окончательное');
      expect(markup).toMatch(/data-run-activity="(polling|stopped)"/);
    }
  });

  /*
   * `WEB-INT-1`, the owner's rule that a recorded run must not look live. The head no longer carries the provider mode as a badge, but a run
   * reproduced from recordings carries the small chip «из записи» beside its state, read from the same `runProviderMode` the old badge was
   * (`badgeProviderMode`): only the value `recorded` draws it. A live run draws nothing, and neither does a reading with no mode or with
   * a value outside the vocabulary (those are said in «Подробнее», where the mode has its own row).
   */
  describe('the chip «из записи»', () => {
    const chipOf = (markup: string): string | null => /<span class="[^"]*" data-run-recorded="">([^<]*)<\/span>/.exec(markup)?.[1] ?? null;
    const head = (markup: string): string => /data-run-head="">([\s\S]*?)<\/section>/.exec(markup)?.[1] ?? '';

    it('is drawn beside the state of a recorded run, in every state of the run', () => {
      for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) {
        const markup = screen({ state, provider_mode: 'recorded' });
        expect(chipOf(head(markup)), state).toBe('из записи');
        // beside the state, before the counter: the state badge, then the chip
        expect(head(markup).indexOf(`data-run-state="${state}"`)).toBeLessThan(head(markup).indexOf('data-run-recorded'));
      }
      const open = screen({ state: 'running', terminal_at: null, provider_mode: 'recorded' });
      expect(chipOf(head(open))).toBe('из записи');
    });

    it('is drawn once, and the mode row of «Подробнее» and its sentence stay', () => {
      const markup = screen({ provider_mode: 'recorded' });
      expect(markup.match(/data-run-recorded/g)).toHaveLength(1);
      expect(markup).toContain('<strong data-provider-mode="recorded">из записи</strong>');
      expect(markup).toContain('Этот прогон не является свидетельством живого вызова провайдера.');
    });

    it('is not drawn for a live run, for a reading with no mode, or for an unrecognised one', () => {
      expect(screen({ provider_mode: 'live' })).not.toContain('data-run-recorded');
      expect(screen({ provider_mode: undefined as never })).not.toContain('data-run-recorded');
      expect(screen({ provider_mode: 'turbo' as never })).not.toContain('data-run-recorded');
      // and the live run does not say «из записи» anywhere in its head
      expect(head(screen({ provider_mode: 'live' }))).not.toContain('из записи');
    });

    it('follows the head\'s own flag: RunHeader draws it for `recorded` and only then', () => {
      const status = runStatus({ provider_mode: 'recorded' });
      const header = (recorded: boolean) => renderToStaticMarkup(createElement(RunHeader, {
        status, chips: runChips({ status, procedures: [] }), executor: null, model: null, showServer: true, liveProgress: null, recorded, polling: false,
        from: null, waiting: null, waitDetail: null, actions: null, onOpenChip: () => undefined,
      }));
      expect(header(true)).toContain('data-run-recorded=""');
      expect(header(false)).not.toContain('data-run-recorded');
    });
  });

  it('says the reading is the last one only when the poll has stopped while the run is still open', () => {
    const status = runStatus({ state: 'running', terminal_at: null });
    const header = (polling: boolean) => renderToStaticMarkup(createElement(RunHeader, {
      status, chips: runChips({ status, procedures: [] }), executor: null, model: null, showServer: true, liveProgress: null, recorded: false, polling,
      from: null, waiting: null, waitDetail: null, actions: null, onOpenChip: () => undefined,
    }));
    expect(header(false)).toContain('data-run-poll-stopped');
    expect(header(false)).toContain('показание — последнее полученное, а не окончательное');
    expect(header(false)).toContain('data-run-activity="stopped"');
    expect(header(true)).not.toContain('data-run-poll-stopped');
    expect(header(true)).toContain('data-run-activity="polling"');
  });

  it('puts the review call and the page\'s own controls in the head, and the review call only for a run that has findings', () => {
    expect(screen({ state: 'published' }, { actions: createElement('button', { 'data-test-cancel': '' }, 'Отменить') }))
      .toMatch(/data-run-head=""[\s\S]*?Разобрать находки[\s\S]*?data-test-cancel/);
    const failed = screen({ state: 'failed', terminal_reason: 'analysis_failed' });
    expect(failed).not.toContain('Разобрать находки');
  });

  it('shows the model and the server of a run that is on a chip that calls one, and neither on Подготовка', () => {
    const onText = screen({ state: 'running', terminal_at: null, stages: PREP.map((id) => ok(id)), executor: EXECUTOR });
    expect(onText).toMatch(/data-run-live="text"[\s\S]*?data-run-live-model="true" title="claude-opus-5-5">Opus 5.5<[\s\S]*?data-run-live-server="true">adm1\.hlab\.kz</);
    const onPrep = screen({ state: 'running', terminal_at: null, stages: [], executor: EXECUTOR });
    expect(onPrep).toContain('data-run-live="preparation"');
    expect(onPrep).not.toContain('data-run-live-model');
    expect(onPrep).not.toContain('data-run-live-server');
  });

  it('names the window the extended review says it is on, on the chip it belongs to', () => {
    const markup = screen(
      { state: 'running', terminal_at: null, stages: [...PREP, 'text_analysis' as const].map((id) => ok(id)), executor: EXECUTOR },
      {},
      review(RUN_ID, {
        workflow_version: 'extended-review-v3',
        procedures: [{ id: 'block_analysis', title: 'Анализ блоков', status: 'running' }],
        windows: [{ window_id: 'w1', index: 0, status: 'completed' }, { window_id: 'w2', index: 1, status: 'running' }],
        window_progress: { total: 5 },
      }),
    );
    expect(markup).toContain('data-run-live="blocks"');
    expect(markup).toContain('data-run-live-progress="window">окно 2 из 5<');
    expect(markup).toContain('Сейчас: <strong>Анализ блоков</strong>');
  });

  it('says «ждёт», and why, for a run in the queue: the chip, the reason and the executor', () => {
    const markup = screen({ state: 'queued', terminal_at: null, stages: [], executor: EXECUTOR, queue_reason: 'executor_at_capacity' });
    expect(markup).toMatch(/data-run-chip="preparation"[^>]*data-chip-state="waiting"/);
    expect(markup).toContain('data-run-live="waiting"');
    expect(markup).toContain('В очереди: исполнитель занят.');
    expect(markup).not.toContain('Сейчас:');
  });

  it('shows no model on the rail for a chip that does not call one, nor for a chip that was skipped', () => {
    const markup = screen({ state: 'published', stages: [...PREP, 'text_analysis' as const].map((id) => ok(id)), executor: EXECUTOR },
      {}, review(RUN_ID, { workflow_version: 'extended-review-v3', procedures: [
        { id: 'finding_merge', title: 'Свод', status: 'completed' }, { id: 'finding_review', title: 'Критик', status: 'skipped' }, { id: 'norm_verification', title: 'Нормы', status: 'completed' },
      ] }));
    const chip = (id: string) => new RegExp(`data-run-chip="${id}"[^>]*>(.*?)</button>`, 's').exec(markup)?.[1] ?? '';
    expect(chip('preparation')).not.toContain('Opus 5.5');
    expect(chip('merge')).not.toContain('Opus 5.5');
    expect(chip('review')).not.toContain('Opus 5.5');
    expect(chip('text')).toContain('Opus 5.5');
    expect(chip('norms')).toContain('Opus 5.5');
  });

  it('draws no token figure anywhere, because the reading has none', () => {
    const markup = screen({ stages: PREP.map((id) => ok(id)), cost_micros: 1, cost_basis: 'measured', model_call_count: 1 });
    expect(markup).not.toMatch(/токен|↓|↑/);
  });
});

describe('the tabs', () => {
  it('move with the arrow keys, wrap at either end, and answer Home and End', () => {
    expect(tabAfterKey(RUN_TABS, 'overview', 'ArrowRight')).toBe('journal');
    expect(tabAfterKey(RUN_TABS, 'journal', 'ArrowRight')).toBe('overview');
    expect(tabAfterKey(RUN_TABS, 'overview', 'ArrowLeft')).toBe('journal');
    expect(tabAfterKey(RUN_TABS, 'journal', 'Home')).toBe('overview');
    expect(tabAfterKey(RUN_TABS, 'overview', 'End')).toBe('journal');
    expect(tabAfterKey(RUN_TABS, 'overview', 'Enter')).toBeNull();
    expect(tabAfterKey(['overview'], 'overview', 'ArrowRight')).toBe('overview');
    expect(tabAfterKey(['overview'], 'journal', 'ArrowRight')).toBeNull();
  });

  it('are the WAI-ARIA pattern: a tablist of two tabs, one in the tab order, a panel labelled by its tab', () => {
    const markup = screen({}, { journal: createElement('p', null, 'СОБЫТИЯ') });
    expect(markup).toMatch(/role="tablist"[^>]*aria-label="Разделы экрана прогона"/);
    expect(markup).toMatch(/role="tab"[^>]*aria-selected="true"[^>]*tabindex="0"[^>]*data-run-tab="overview">Обзор</);
    expect(markup).toMatch(/role="tab"[^>]*aria-selected="false"[^>]*tabindex="-1"[^>]*data-run-tab="journal">Журнал</);
    const tab = /role="tab" id="([^"]+)"[^>]*data-run-tab="overview"/.exec(markup)?.[1];
    expect(tab).toBeDefined();
    expect(markup).toContain(`role="tabpanel"`);
    expect(markup).toContain(`aria-labelledby="${tab}"`);
  });

  it('open on «Обзор», and read nothing of the journal until it is asked for', () => {
    const markup = screen({}, { journal: createElement('p', null, 'СОБЫТИЯ') });
    expect(markup).toContain('data-run-panel="overview"');
    expect(markup).not.toContain('СОБЫТИЯ');
  });

  it('are not drawn at all when there is no journal to offer: one tab is not a choice', () => {
    const markup = screen({});
    expect(markup).not.toContain('role="tablist"');
    expect(markup).toContain('data-run-more=""');
    expect(markup).toContain('data-run-spend=');
  });

  it('offer «Журнал» on the page to an expert and an account not known yet, and not to a read-only account', () => {
    const page = (roles?: string[]) => {
      const { status, client } = seeded({}, (c) => { if (roles !== undefined) c.setQueryData(queryKeys.account.me(), { roles }); });
      return renderScreen(client, createElement(RunPage, { projectUid: PROJECT_UID, runId: status.run_id }));
    };
    for (const roles of [undefined, ['expert'], ['admin']]) expect(page(roles)).toContain('data-run-tab="journal"');
    const viewer = page(['viewer']);
    expect(viewer).not.toContain('data-run-tab=');
    expect(viewer).not.toContain('role="tablist"');
  });

  it('draw the events cold as loading, and their own link to the whole journal', () => {
    const markup = renderWith(newClient(), createElement(RunEvents, { runId: RUN_ID }));
    expect(markup).toContain('Загрузка: события прогона…');
    expect(markup).toContain('Весь журнал прогона');
  });

  it('take the page\'s own link to the journal away: the tab is the way to the events', () => {
    const { status, client } = seeded({});
    const markup = renderScreen(client, createElement(RunPage, { projectUid: PROJECT_UID, runId: status.run_id }));
    expect(markup).not.toContain('>Журнал прогона<');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}"`);
  });

  it('know who sees the server: an operator and an account not known yet, not the read-only role', () => {
    expect(maySeeServer(undefined)).toBe(true);
    expect(maySeeServer(['expert'])).toBe(true);
    expect(maySeeServer(['admin'])).toBe(true);
    expect(maySeeServer(['viewer'])).toBe(false);
    expect(maySeeServer([])).toBe(false);
  });
});

describe('the tiles', () => {
  const seedFindings = (items: ReturnType<typeof finding>[]) => (client: ReturnType<typeof newClient>) =>
    client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items, page: { next_cursor: null } } });
  const decided = (n: number, severity?: 'critical' | 'economic') => finding({
    finding_uid: `fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8${n}`, ...(severity === undefined ? {} : { decided_severity: severity }), observation: observation(),
  });

  it('«Находки» counts the run by the severity the expert decided and links «Разбор»', () => {
    const markup = screen({}, {}, seedFindings([decided(1, 'critical'), decided(2, 'critical'), decided(3, 'economic'), decided(4)]));
    expect(markup).toContain('data-severity-strip=""');
    expect(markup).toContain('data-severity="critical">Критическое 2<');
    expect(markup).toContain('data-severity="economic">Экономическое 1<');
    expect(markup).toContain('data-severity="undetermined">Не определена 1<');
    expect(markup).not.toContain('data-severity="operational"');
    expect(markup).toMatch(/data-run-findings-tile=""[\s\S]*?href="\/projects\/[^"]+\/runs\/[^"]+\/review">в Разбор →</);
  });

  it('claims no count it has not read: with the list unread the tile is only the way in', () => {
    const markup = screen({});
    expect(markup).toContain('data-run-findings-tile=""');
    expect(markup).not.toContain('data-severity-strip');
  });

  it('says there is nothing to review in the tile of a run that published nothing', () => {
    const markup = screen({ state: 'failed', terminal_reason: 'analysis_failed' });
    expect(markup).toMatch(/data-run-findings-tile=""[\s\S]*?Разбирать нечего\./);
    expect(markup).not.toContain('data-severity-strip');
  });

  it('«Расход» prints a figure with the calls it sums and the word for its basis, and nothing it has not', () => {
    const markup = screen({ state: 'published', cost_micros: 4_500_000, cost_basis: 'measured', model_call_count: 3 });
    expect(markup).toContain('data-run-spend="reported"');
    expect(markup).toContain('data-spend-micros="4500000">$4.5<');
    expect(markup).toContain('вызовов 3 · измерено');
  });

  it('«Расход» writes the figure as dollars, as every other money of the application, and never as the raw six digits (RUN-SCREEN-FIX-01)', () => {
    const spend = (cost_micros: number) => screen({ state: 'published', cost_micros, cost_basis: 'measured', model_call_count: 3 });
    expect(spend(6_120_000)).toContain('data-spend-micros="6120000">$6.12<');
    // The tile's figure; the raw six digits stay in the notes of «Подробнее», which spell out the unit.
    expect(spend(6_120_000)).not.toContain('data-spend-micros="6120000">6.120000<');
    expect(spend(1)).toContain('>$0.000001<');
    expect(spend(0)).toContain('data-spend-micros="0">$0<');
    expect(spend(6_120_000)).toContain('· измерено');
  });

  it('«Расход» groups the calls it sums by threes with a narrow no-break space (RUN-SCREEN-FIX-01)', () => {
    const markup = screen({ state: 'published', cost_micros: 1_000_000, cost_basis: 'measured', model_call_count: 12_345 });
    expect(markup).toContain('вызовов 12\u202F345 · измерено');
    expect(markup).not.toContain('вызовов 12345');
  });

  it('«Расход» says «по подписке» for an unmetered run with no figure, and that a run that called no provider did not', () => {
    const subscription = screen({ state: 'published', cost_basis: 'unmetered' as never, cost_micros: 0, model_call_count: 2 });
    expect(subscription).toContain('data-run-spend="unmetered"');
    expect(subscription).toContain('По подписке.');
    expect(subscription).not.toContain('data-spend-micros');
    expect(screen({ state: 'published' })).toContain('Прогон не обращался к провайдеру.');
  });

  it('an open run says what it has not got yet, and not what a finished run says (RUN-SCREEN-FIX-01)', () => {
    for (const state of ['created', 'queued', 'running', 'validating'] as const) {
      const markup = screen({ state, terminal_at: null });
      expect(markup).toMatch(/data-run-findings-tile=""[\s\S]*?Появятся по ходу прогона\./);
      expect(markup).toMatch(/data-run-spend="absent"[\s\S]*?Появится по ходу прогона\./);
      expect(markup).not.toContain('Разбирать нечего.');
      expect(markup).not.toContain('Прогон не обращался к провайдеру');
      expect(markup).not.toContain('поэтому сообщать о стоимости нечего');
    }
  });

  it('an open run that already carries a spend still prints it, and a finished run keeps its sentences (RUN-SCREEN-FIX-01)', () => {
    const running = screen({ state: 'running', terminal_at: null, cost_micros: 6_120_000, cost_basis: 'estimated', model_call_count: 2 });
    expect(running).toContain('data-run-spend="reported"');
    expect(running).toContain('>$6.12<');
    expect(running).not.toContain('Появится по ходу прогона.');
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) {
      expect(screen({ state })).toContain('Прогон не обращался к провайдеру.');
      expect(screen({ state })).not.toContain('по ходу прогона');
    }
    expect(screen({ state: 'failed', terminal_reason: 'analysis_failed' })).toContain('Разбирать нечего.');
  });

  it('«Расход» refuses a figure whose calls it cannot see and sends the reader to the notes, which open themselves', () => {
    const markup = screen({ state: 'published', cost_micros: 900 as never, cost_basis: 'estimated' as never });
    expect(markup).toContain('data-run-spend="unreadable"');
    expect(markup).not.toContain('data-spend-micros');
    expect(markup).toMatch(/<details[^>]*data-run-more=""[^>]*open=""/);
    expect(markup).toMatch(/<details[^>]*open=""[^>]*data-run-notes=""|<details[^>]*data-run-notes=""[^>]*open=""/);
  });
});

describe('where each block of the page went', () => {
  const FULL = { workflow_version: 'extended-review-v3', procedures: [
    { id: 'block_analysis', title: 'Анализ блоков', status: 'completed' },
    { id: 'comprehensive_analysis', title: 'Комплексная сверка', status: 'failed', reason: 'provider_outcome_unknown' },
  ] };

  it('keeps the identity, the checks, the norms, the full analysis and the notes in «Подробнее», in that order', () => {
    const markup = screen({ state: 'published', executor: EXECUTOR }, {}, review(RUN_ID, FULL));
    const at = (needle: string) => markup.indexOf(needle);
    expect(at('data-run-more=""')).toBeGreaterThan(-1);
    const order = ['data-run-more=""', 'Сведения о прогоне', 'data-norm-references=""', 'id="extended-analysis"', 'data-run-notes=""'].map(at);
    expect(order).toEqual([...order].sort((a, b) => a - b));
    expect(order.every((position) => position > -1)).toBe(true);
    expect(at('data-run-more=""')).toBeGreaterThan(at('data-run-spend='));
  });

  it('draws the stage table and the plan list in the dialog and not on the page', () => {
    const markup = screen({ state: 'published', stages: PREP.map((id) => ok(id)) }, {}, review(RUN_ID, FULL));
    expect(markup).not.toContain('data-stage-id=');
    expect(markup).not.toContain('data-extended-procedure-plan');
    expect(markup).not.toContain('data-extended-procedure=');
    expect(markup).toContain('Ход расширенных процедур — в окне «Этапы анализа раздела».');
    expect(markup).toContain('data-run-chip="blocks"');
    expect(markup).toContain('data-run-chip="cross_check"');
    const status = runStatus({ state: 'published', stages: PREP.map((id) => ok(id)) });
    const dialog = runDialog(status, { selected: 'cross_check', procedures: [
      { id: 'comprehensive_analysis', title: 'Комплексная сверка', status: 'failed', reason: 'provider_outcome_unknown', dependency: null, errorCode: null },
    ] });
    expect(dialog).toContain('data-extended-procedure-plan');
    expect(dialog).toContain('data-extended-procedure="comprehensive_analysis"');
    expect(dialog).toContain('Результат обращения к исполнителю неизвестен');
  });

  it('keeps the outcome, the queue card and the interrupted note on «Обзор», in the plan\'s order after the tiles', () => {
    const queued = screen({ state: 'queued', terminal_at: null });
    expect(queued.indexOf('data-run-spend=')).toBeLessThan(queued.indexOf('data-run-outcome='));
    expect(queued.indexOf('data-run-outcome=')).toBeLessThan(queued.indexOf('data-run-next-task='));
    expect(queued.indexOf('data-run-next-task=')).toBeLessThan(queued.indexOf('data-run-more=""'));
    expect(screen({ state: 'published' })).not.toContain('data-run-next-task');
    expect(screen({ state: 'running', terminal_at: null, interrupted_reason: 'worker_lost' })).toContain('У прогона указана причина прерывания: worker_lost.');
  });

  it('puts the run\'s identity, who started it and the provider mode among the facts, and drops the repeated «Запущен с этапа» row', () => {
    const markup = screen({ state: 'published', started_by_label: 'Иванов', started_from_run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z' as never, start_stage_id: 'text_analysis' });
    expect(markup).toContain('<dt>Запустил</dt>');
    expect(markup).toContain('Иванов');
    expect(markup).toContain('<dt>Режим провайдера</dt>');
    expect(markup).not.toContain('<dt>Запущен с этапа</dt>');
    expect(markup).toContain('data-run-started-from-note="text_analysis"');
  });
});

describe('«Этапы анализа раздела»', () => {
  const status = (over: Partial<RunStatus> = {}) => runStatus({ state: 'published', stages: PREP.map((id) => ok(id)), executor: EXECUTOR, ...over });

  it('is a labelled dialog with a list of the chips, the chosen one marked, and one table «План + Факт»', () => {
    const markup = runDialog(status(), { selected: 'text' });
    expect(markup).toMatch(/<dialog[^>]*aria-labelledby="([^"]+)"/);
    const id = /<dialog[^>]*aria-labelledby="([^"]+)"/.exec(markup)?.[1];
    expect(markup).toContain(`<h2 id="${id}"`);
    expect(markup).toContain('Этапы анализа раздела');
    expect(markup).toMatch(/data-stage-item="text"[^>]*aria-current="true"/);
    expect(markup).not.toMatch(/data-stage-item="preparation"[^>]*aria-current/);
    expect(markup.match(/<caption>План \+ Факт<\/caption>/g)).toHaveLength(1);
    expect(markup).toContain('data-run-stages-close=""');
  });

  it('labels the model as the run\'s, with the server, and the fact rows that exist', () => {
    const markup = runDialog(status({ stages: [...PREP, 'text_analysis' as const].map((id) => ok(id, { started_at: '2026-11-08T10:00:00.000Z', finished_at: '2026-11-08T10:00:03.000Z' })) }), { selected: 'text' });
    expect(markup).toContain('Модель (прогона)');
    expect(markup).toContain('<strong>Opus 5.5</strong>');
    expect(markup).toContain('title="Идентификатор модели прогона">claude-opus-5-5<');
    expect(markup).toMatch(/data-plan-row="server"[\s\S]*?adm1\.hlab\.kz/);
    for (const row of ['state', 'started', 'finished', 'elapsed']) expect(markup).toContain(`data-fact-row="${row}"`);
    expect(markup).toContain('<th scope="row">Длительность</th><td>3 с</td>');
    expect(markup).not.toContain('data-fact-row="error"');
  });

  it('says a chip that calls no model calls none, and names no server for it', () => {
    const markup = runDialog(status(), { selected: 'preparation' });
    expect(markup).toContain('этап не вызывает модель');
    expect(markup).not.toContain('data-plan-row="server"');
  });

  it('shows the error code of a failed chip, and says the time of a chip with no stage rows is not reported', () => {
    const failed = runDialog(status({ state: 'failed', stages: [ok('source_preparation'), { stage_id: 'page_geometry_extraction', status: 'failed' as const, error_code: 'storage_integrity_error' }] }), { selected: 'preparation' });
    expect(failed).toContain('<th scope="row">Код ошибки</th><td><code>storage_integrity_error</code></td>');
    const procedureOnly = runDialog(status(), { selected: 'blocks', procedures: [{ id: 'block_analysis', title: 'Анализ блоков', status: 'running', reason: null, dependency: null, errorCode: null }] });
    expect(procedureOnly).toContain('Время и токены по этому этапу сервер пока не передаёт.');
    expect(procedureOnly).not.toContain('data-fact-row="started"');
  });

  it('holds «Как устроен этап», collapsed, with three or four steps and arrows between them', () => {
    const markup = runDialog(status(), { selected: 'text' });
    expect(markup).toMatch(/<details[^>]*data-stage-algorithm="text"[^>]*><summary>Как устроен этап<\/summary>/);
    expect(markup).not.toMatch(/<details[^>]*data-stage-algorithm[^>]*open/);
    const steps = /data-stage-algorithm="text".*?<ol[^>]*>(.*?)<\/ol>/s.exec(markup)?.[1] ?? '';
    expect((steps.match(/<li/g) ?? []).length).toBeGreaterThanOrEqual(3);
    expect((steps.match(/<li/g) ?? []).length).toBeLessThanOrEqual(4);
    expect((steps.match(/aria-hidden="true">↓</g) ?? []).length).toBe((steps.match(/<li/g) ?? []).length - 1);
    expect(steps).toContain('data-step-result=""');
  });

  it('hides the executor row from the read-only role and keeps the preset and the model', () => {
    const withPreset = status({ preset: { preset_id: 'pre_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', revision_no: 2, name: 'Быстрый черновик' } as never });
    const operator = runDialog(withPreset, { selected: 'text' });
    expect(operator).toContain('<dt>Пресет</dt>');
    expect(operator).toContain('<dt>Исполнитель</dt>');
    const viewer = runDialog(withPreset, { selected: 'text', showServer: false });
    expect(viewer).toContain('<dt>Пресет</dt>');
    expect(viewer).not.toContain('<dt>Исполнитель</dt>');
    expect(viewer).not.toContain('adm1.hlab.kz');
    expect(viewer).toContain('Opus 5.5');
  });

  it('offers «Запустить с этого этапа» for a chip with a stage a new run may start from, on an ended run, to an operator', () => {
    for (const [chip, offered] of [['text', true], ['preparation', true], ['merge', false]] as const) {
      const markup = runDialog(status(), { selected: chip, roles: ['expert'], procedures: [
        { id: 'finding_merge', title: 'Свод', status: 'completed', reason: null, dependency: null, errorCode: null },
      ] });
      expect(markup.includes('data-run-start-from-stage="offer"'), chip).toBe(offered);
    }
    expect(runDialog(status(), { selected: 'text', roles: ['expert'] })).toContain('Запустить с этого этапа');
  });

  it('offers it to nobody for a run that is still going, for the read-only role and for a run of AR v3', () => {
    expect(runDialog(status({ state: 'running', terminal_at: null }), { selected: 'text', roles: ['expert'] })).not.toContain('data-run-start-from-stage');
    expect(runDialog(status(), { selected: 'text', roles: ['viewer'] })).not.toContain('data-run-start-from-stage');
    expect(runDialog(status({ analysis_kind: 'ar_v3_beta' }), { selected: 'text', roles: ['expert'] })).not.toContain('data-run-start-from-stage');
  });
});
