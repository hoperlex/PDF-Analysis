/**
 * `UIP-S08-02`: the «Лог» of one run. The events are in groups by the stage they name, in the order of the pipeline; the events
 * that name none lie in «Прочее»; the events of the job, the attempt and the calls to a model lie in «Выполнение», which starts
 * folded -- folded, not dropped. A line reads time · event · «стр. N из M» · state, and the code of an error stands on the line of
 * the failure only. The column «Прогон» is not drawn for one run, and stays in the journal of every run.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry, StageId } from '@/shared/api';
import { STAGE_LABELS } from '@/shared/ui';
import { ExecutionJournal, journalGroups } from '@/widgets/execution-journal';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

/** The pipeline as `stage-registry.json` orders its nine stages (a topological order of `depends_on`). */
const PIPELINE: readonly StageId[] = [
  'source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis', 'block_analysis',
  'finding_merge', 'finding_review', 'finding_correction', 'norm_verification',
];

let sequence = 0;
function entry(
  eventType: string,
  payload: Record<string, string | number | boolean | null> = {},
  over: Partial<ExecutionJournalEntry> = {},
): ExecutionJournalEntry {
  sequence += 1;
  const id = String(sequence).padStart(4, '0');
  return {
    event_id: `evt_${id}`,
    run_id: RUN_ID,
    aggregate_id: RUN_ID,
    aggregate_type: 'AuditRun',
    event_type: eventType,
    occurred_at: `2026-11-16T10:00:${String(sequence % 60).padStart(2, '0')}Z`,
    payload,
    ...over,
  };
}

const attempt = (eventType: string, payload: Record<string, string | number | boolean | null> = {}) =>
  entry(eventType, payload, { aggregate_type: 'Attempt', aggregate_id: 'att_1' });
const job = (eventType: string, payload: Record<string, string | number | boolean | null> = {}) =>
  entry(eventType, payload, { aggregate_type: 'Job', aggregate_id: 'job_1' });

function runLog(entries: readonly ExecutionJournalEntry[], extra: { onNext?: (() => void) | null } = {}): string {
  return renderToStaticMarkup(createElement(ExecutionJournal, {
    entries, onNext: extra.onNext ?? null, onPrevious: null, scope: 'run',
  }));
}

/** The markup of one group, from its `<details>` to its end. */
function groupMarkup(markup: string, key: string): string {
  const at = markup.indexOf(`data-journal-group="${key}"`);
  expect(at, `group ${key} is drawn`).toBeGreaterThan(-1);
  const open = markup.lastIndexOf('<details', at);
  return markup.slice(open, markup.indexOf('</details>', at) + '</details>'.length);
}

const groupKeys = (markup: string): string[] => [...markup.matchAll(/data-journal-group="([a-z_]+)"/g)].map((match) => match[1] as string);

describe('the groups of a run\'s log', () => {
  it('puts the stages in the order of the pipeline whatever the order of the events, then «Другой этап», «Прочее», «Выполнение»', () => {
    // Newest first, the way the journal is read: the last stage's events come first.
    const events = [
      entry('audit_run.transition', { from_state: 'running', to_state: 'published' }),
      job('job.transition', { to_state: 'succeeded' }),
      ...[...PIPELINE].reverse().map((id) => entry('stage.finished', { stage_id: id, state: 'succeeded' })),
      entry('stage.started', { stage_id: 'unlisted_stage' }),
      attempt('attempt.transition', { to_state: 'running' }),
      entry('audit_run.created'),
    ];
    expect(journalGroups(events).map((group) => group.key)).toEqual([...PIPELINE, 'other_stage', 'misc', 'execution']);
    expect(groupKeys(runLog(events))).toEqual([...PIPELINE, 'other_stage', 'misc', 'execution']);
    expect(journalGroups(events).map((group) => group.title)).toEqual([
      ...PIPELINE.map((id) => STAGE_LABELS[id]), 'Другой этап', 'Прочее', 'Выполнение',
    ]);
  });

  it('makes no group for a stage with no events, and an empty log has no groups', () => {
    const events = [entry('stage.started', { stage_id: 'text_analysis' }), entry('stage.started', { stage_id: 'source_preparation' })];
    expect(journalGroups(events).map((group) => group.key)).toEqual(['source_preparation', 'text_analysis']);
    expect(journalGroups([])).toEqual([]);
  });

  it('says on each group its name and the number of its lines, with a chevron to fold it', () => {
    const markup = runLog([
      entry('stage.finished', { stage_id: 'text_analysis', state: 'succeeded' }),
      entry('stage.progress', { stage_id: 'text_analysis', completed_pages: 2, total_pages: 5 }),
      entry('stage.started', { stage_id: 'text_analysis' }),
      entry('stage.started', { stage_id: 'source_preparation' }),
    ]);
    const analysis = groupMarkup(markup, 'text_analysis');
    expect(analysis).toContain(`<summary class="`);
    expect(analysis).toContain(`>${STAGE_LABELS.text_analysis}</span>`);
    expect(analysis).toMatch(/aria-label="строк: 3"[^>]*data-journal-group-count="">3</);
    expect(groupMarkup(markup, 'source_preparation')).toMatch(/aria-label="строк: 1"[^>]*data-journal-group-count="">1</);
  });

  it('files an event that names no stage under «Прочее»', () => {
    const events = [entry('audit_run.created'), entry('audit_run.transition', { to_state: 'queued' }), entry('raw.unknown.event', { stage_id: 'text_analysis' })];
    expect(journalGroups(events).map((group) => [group.key, group.entries.length])).toEqual([['misc', 3]]);
    // A stage given by an event that is not a stage event does not make a stage group.
    expect(groupKeys(runLog(events))).toEqual(['misc']);
    // Nor does a stage event that names no stage.
    expect(journalGroups([entry('stage.started', {})]).map((group) => group.key)).toEqual(['misc']);
  });

  it('puts the events of the job, the attempt and the calls to a model in «Выполнение», closed', () => {
    const events = [
      job('job.created'), job('job.transition', { to_state: 'running' }),
      attempt('attempt.created'), attempt('attempt.transition', { to_state: 'succeeded' }),
      attempt('provider.prepared', { state: 'prepared' }), attempt('provider.response_received'), attempt('provider.completed'),
      entry('stage.started', { stage_id: 'text_analysis' }),
    ];
    const groups = journalGroups(events);
    expect(groups.map((group) => [group.key, group.open])).toEqual([['text_analysis', true], ['execution', false]]);
    expect(groups[1]?.entries).toHaveLength(7);
    const markup = runLog(events);
    // Closed: the `<details>` has no `open`; the stage's has.
    expect(groupMarkup(markup, 'execution')).not.toMatch(/^<details[^>]* open=""/);
    expect(groupMarkup(markup, 'text_analysis')).toMatch(/^<details[^>]* open=""/);
  });

  it('does not lose the folded events: each of them is a line of the closed group', () => {
    const technical = [job('job.created'), job('job.transition', { to_state: 'running' }), attempt('attempt.created'), attempt('provider.prepared', { state: 'prepared' })];
    const events = [entry('stage.started', { stage_id: 'text_analysis' }), ...technical];
    const markup = runLog(events);
    const closed = groupMarkup(markup, 'execution');
    expect((closed.match(/<time /g) ?? []).length).toBe(technical.length);
    for (const word of ['Задача создана', 'Состояние задачи', 'Попытка создана', 'Вызов подготовлен']) expect(closed).toContain(word);
    // Every event of the page is a line, in exactly one group.
    expect((markup.match(/<time /g) ?? []).length).toBe(events.length);
    expect(journalGroups(events).reduce((sum, group) => sum + group.entries.length, 0)).toBe(events.length);
  });

  it('keeps the order the events came in inside a group', () => {
    const newest = entry('stage.finished', { stage_id: 'text_analysis', state: 'succeeded' });
    const middle = entry('stage.progress', { stage_id: 'text_analysis', completed_pages: 1, total_pages: 2 });
    const oldest = entry('stage.started', { stage_id: 'text_analysis' });
    expect(journalGroups([newest, middle, oldest])[0]?.entries.map((e) => e.event_id)).toEqual([newest, middle, oldest].map((e) => e.event_id));
  });
});

describe('a line of the run\'s log', () => {
  const progress = entry('stage.progress', { stage_id: 'text_analysis', completed_pages: 3, total_pages: 10 });
  const finished = entry('stage.finished', { stage_id: 'text_analysis', state: 'succeeded' });
  const failed = entry('stage.finished', { stage_id: 'block_analysis', state: 'failed', error_code: 'analysis_failed' });
  const queued = entry('audit_run.transition', { to_state: 'queued' });

  it('reads time, event, «стр. N из M», state', () => {
    const line = /<tr><td class="[^"]*"><time [^>]*>10:00:\d\d<\/time><\/td><td class="[^"]*"><strong>Ход этапа<\/strong>[\s\S]*?<\/td><td class="[^"]*"><span data-journal-pages="">стр\. 3 из 10<\/span><\/td><td class="[^"]*"><\/td><\/tr>/;
    expect(runLog([progress])).toMatch(line);
    const done = runLog([finished]);
    expect(done).toMatch(/<strong>Этап завершён<\/strong>[\s\S]*?<\/td><td class="[^"]*"><\/td><td class="[^"]*"><span class="am-badge am-badge--ok" data-job-state="succeeded">/);
  });

  it('says the state with the badge that already says it, tone included', () => {
    expect(runLog([queued])).toContain('data-run-state="queued"');
    expect(runLog([queued])).toContain('am-badge--pending');
    expect(runLog([entry('audit_run.transition', { to_state: 'published' })])).toContain('am-badge--ok');
    expect(runLog([entry('audit_run.transition', { to_state: 'failed' })])).toContain('am-badge--failed');
    expect(runLog([finished])).toContain('data-job-state="succeeded"');
    expect(runLog([failed])).toContain('am-badge--failed');
  });

  it('puts the code of an error on the line of the failure and on no other line', () => {
    const markup = runLog([failed, finished, queued, progress]);
    expect((markup.match(/<code>/g) ?? [])).toHaveLength(1);
    expect(markup).toContain('<code>analysis_failed</code>');
    expect(runLog([finished, queued, progress])).not.toContain('<code>');
    expect(markup).not.toContain('>Код<');
  });

  it('draws no «Прогон» column and no link to the run, where the journal of every run keeps both', () => {
    const own = runLog([queued, progress]);
    expect(own).not.toContain('>Прогон<');
    expect(own).not.toContain(RUN_ID);
    expect(own).not.toContain('/logs?run_id=');
    for (const word of ['Время', 'Событие', 'Страницы', 'Состояние']) expect(own).toContain(`>${word}</th>`);

    const all = renderToStaticMarkup(createElement(ExecutionJournal, { entries: [queued, progress], onNext: null, onPrevious: null }));
    expect(all).toContain('>Прогон</th>');
    expect(all).toContain(`href="/logs?run_id=${RUN_ID}"`);
    expect(all).toContain('>Код</th>');
    expect(all).not.toContain('data-journal-groups');
    expect(all).toContain('Страницы журнала');
  });

  it('draws no paging for a log that has nothing to turn, and keeps it when there is a page to turn to', () => {
    expect(runLog([queued])).not.toContain('Страницы журнала');
    expect(runLog([queued], { onNext: () => {} })).toContain('Страницы журнала');
  });

  it('keeps the empty state', () => {
    const markup = runLog([]);
    expect(markup).toContain('Записей пока нет');
    expect(markup).not.toContain('data-journal-groups');
  });
});

describe('the day of a line', () => {
  const at = (iso: string, stage: string) => entry('stage.started', { stage_id: stage }, { occurred_at: iso });

  it('says no date inside a group of one day: the time is the line\'s, the date is in its tooltip', () => {
    const markup = runLog([at('2026-11-16T10:00:03Z', 'text_analysis'), at('2026-11-16T10:00:01Z', 'text_analysis')]);
    expect(markup).not.toContain('data-journal-day');
    expect(markup).toContain('title="16.11.2026 10:00 · 2026-11-16 10:00:03 UTC"');
  });

  it('puts the date before the first line of each day when a group spans several', () => {
    const markup = runLog([
      at('2026-11-17T00:10:00Z', 'text_analysis'), at('2026-11-16T23:50:00Z', 'text_analysis'), at('2026-11-16T22:00:00Z', 'text_analysis'),
    ]);
    expect(markup.match(/data-journal-day="([^"]+)"/g)).toEqual(['data-journal-day="17.11.2026"', 'data-journal-day="16.11.2026"']);
    // The date stands before the line it opens.
    expect(markup).toMatch(/data-journal-day="17\.11\.2026"[\s\S]*?00:10:00[\s\S]*?data-journal-day="16\.11\.2026"[\s\S]*?23:50:00[\s\S]*?22:00:00/);
  });

  it('counts the days of each group on its own', () => {
    const markup = runLog([
      at('2026-11-17T00:10:00Z', 'text_analysis'), at('2026-11-16T23:50:00Z', 'source_preparation'),
    ]);
    expect(markup).not.toContain('data-journal-day');
  });

  it('says no date for an instant that is not one', () => {
    const markup = runLog([at('2026-11-16T10:00:00Z', 'text_analysis'), at('not-a-time', 'text_analysis')]);
    expect(markup).not.toContain('data-journal-day');
  });
});
