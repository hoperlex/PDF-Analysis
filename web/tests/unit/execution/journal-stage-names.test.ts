/**
 * `UIP-S08-01`: the lines «Этап начат», «Этап завершён» and «Ход этапа» of the journal name the stage, and the progress line says
 * «стр. N из M». The stage is taken only from the contract's closed list of stages (`STAGE_LABELS`); a value the list does not hold
 * reads «Другой этап», never the raw word. The text «Скопировать» puts on the clipboard says the same.
 *
 * And the test the task asks for by name, the closed projection: a field the projection does not let through -- a message, a model's
 * output, a host, a prompt, a stage given under another name -- reaches neither the screen nor the copied text.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry } from '@/shared/api';
import { STAGE_ID_VALUES } from '@/shared/api';
import { UNKNOWN_STAGE_LABEL, journalCopyLine, journalCopyText, visibleJournal } from '@/entities/execution';
import { STAGE_LABELS } from '@/shared/ui';
import { ExecutionJournal } from '@/widgets/execution-journal';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

let sequence = 0;
function entry(
  eventType: string,
  payload: Record<string, string | number | boolean | null>,
  aggregateType = 'AuditRun',
): ExecutionJournalEntry {
  sequence += 1;
  return {
    event_id: `evt_${String(sequence).padStart(4, '0')}`,
    run_id: RUN_ID,
    aggregate_id: RUN_ID,
    aggregate_type: aggregateType,
    event_type: eventType,
    occurred_at: '2026-11-16T10:00:00Z',
    payload,
  };
}

function drawn(entries: readonly ExecutionJournalEntry[]): string {
  return renderToStaticMarkup(createElement(ExecutionJournal, { entries, onNext: null, onPrevious: null }));
}

describe('the stage a line names', () => {
  it('reads the Russian name of every stage the contract lists, on «Этап начат», «Этап завершён» and «Ход этапа»', () => {
    expect(STAGE_ID_VALUES.length).toBeGreaterThan(0);
    for (const stageId of STAGE_ID_VALUES) {
      for (const [eventType, word] of [
        ['stage.started', 'Этап начат'],
        ['stage.finished', 'Этап завершён'],
        ['stage.progress', 'Ход этапа'],
      ] as const) {
        const shown = visibleJournal(entry(eventType, { stage_id: stageId }));
        expect(shown.event).toBe(word);
        expect(shown.stage).toEqual({ id: stageId, label: STAGE_LABELS[stageId] });
        const markup = drawn([entry(eventType, { stage_id: stageId })]);
        expect(markup).toContain(`>${word}</strong>`);
        expect(markup).toContain(`<span data-journal-stage="${stageId}">${STAGE_LABELS[stageId]}</span>`);
        // The machine word has its home in the attribute and is never the reader's text.
        expect(markup).not.toContain(`>${stageId}<`);
      }
    }
  });

  it('adds «стр. N из M» to the progress of a stage, and to nothing that does not report pages', () => {
    const progress = entry('stage.progress', { stage_id: 'page_geometry_extraction', completed_pages: 3, total_pages: 10 });
    expect(visibleJournal(progress).pages).toEqual({ completed: 3, total: 10 });
    expect(drawn([progress])).toContain('<span data-journal-pages="">стр. 3 из 10</span>');

    const precheck = entry('stage.pdf_precheck', { stage_id: 'source_preparation', phase: 'checking', completed_pages: 0, total_pages: 12 });
    expect(drawn([precheck])).toContain('стр. 0 из 12');
    expect(visibleJournal(precheck).stage?.label).toBe(STAGE_LABELS.source_preparation);

    // A start or an end that happens to carry counts says no pages: they are not that event's to say.
    for (const eventType of ['stage.started', 'stage.finished']) {
      const shown = visibleJournal(entry(eventType, { stage_id: 'text_analysis', completed_pages: 3, total_pages: 10 }));
      expect(shown.pages).toBeUndefined();
    }
    expect(drawn([entry('stage.started', { stage_id: 'text_analysis', completed_pages: 3, total_pages: 10 })])).not.toContain('стр.');
  });

  it('shows no pages for counts that cannot be pages', () => {
    const odd: Record<string, string | number | boolean | null>[] = [
      { completed_pages: 11, total_pages: 10 },
      { completed_pages: -1, total_pages: 10 },
      { completed_pages: 1, total_pages: 0 },
      { completed_pages: 1.5, total_pages: 10 },
      { completed_pages: '3', total_pages: '10' },
      { completed_pages: null, total_pages: 10 },
      { completed_pages: 3 },
    ];
    for (const counts of odd) {
      const shown = visibleJournal(entry('stage.progress', { stage_id: 'text_analysis', ...counts }));
      expect(shown.pages, JSON.stringify(counts)).toBeUndefined();
      expect(drawn([entry('stage.progress', { stage_id: 'text_analysis', ...counts })])).not.toContain('стр.');
    }
  });

  it('calls a stage the list does not hold «Другой этап», and keeps its raw value off the screen', () => {
    for (const raw of ['secret_stage_x', '', 'Block_Analysis', 'text_analysis ', 42, true]) {
      const shown = visibleJournal(entry('stage.started', { stage_id: raw }));
      expect(shown.stage, String(raw)).toEqual({ id: null, label: UNKNOWN_STAGE_LABEL });
      const markup = drawn([entry('stage.started', { stage_id: raw })]);
      expect(markup).toContain('<span data-journal-stage="other">Другой этап</span>');
      if (typeof raw === 'string' && raw.trim() !== '') expect(markup).not.toContain(raw);
    }
    expect(UNKNOWN_STAGE_LABEL).toBe('Другой этап');
  });

  it('names no stage for a stage event that gives none, and takes none from an event that is not a stage event', () => {
    expect(visibleJournal(entry('stage.started', {})).stage).toBeUndefined();
    expect(visibleJournal(entry('stage.started', { stage_id: null })).stage).toBeUndefined();
    expect(drawn([entry('stage.started', {})])).not.toContain('data-journal-stage');
    // A run's transition, a job's or a call's record that carries a `stage_id` does not become a stage line.
    for (const [eventType, aggregate] of [
      ['audit_run.transition', 'AuditRun'], ['job.transition', 'Job'], ['attempt.transition', 'Attempt'], ['provider.prepared', 'Attempt'],
    ] as const) {
      const shown = visibleJournal(entry(eventType, { stage_id: 'text_analysis', completed_pages: 1, total_pages: 2 }, aggregate));
      expect(shown.stage, eventType).toBeUndefined();
      expect(shown.pages, eventType).toBeUndefined();
    }
  });

  it('leaves the projection of an event with no stage as it was: the three fields and nothing more', () => {
    expect(visibleJournal(entry('audit_run.created', {}))).toEqual({ event: 'Прогон создан', state: null, code: null });
  });
});

describe('«Скопировать» says the stage and the pages in the same words', () => {
  it('puts the stage after the event and the pages after the stage', () => {
    const progress = entry('stage.progress', { stage_id: 'block_analysis', completed_pages: 3, total_pages: 10 });
    expect(journalCopyLine(progress)).toBe(
      `2026-11-16 10:00:00 UTC · Ход этапа · ${STAGE_LABELS.block_analysis} · стр. 3 из 10 · прогон ${RUN_ID}`,
    );
    expect(journalCopyLine(entry('stage.started', { stage_id: 'text_analysis' }))).toBe(
      `2026-11-16 10:00:00 UTC · Этап начат · ${STAGE_LABELS.text_analysis} · прогон ${RUN_ID}`,
    );
    expect(journalCopyLine(entry('stage.finished', { stage_id: 'norm_verification', state: 'succeeded' }))).toBe(
      `2026-11-16 10:00:00 UTC · Этап завершён · ${STAGE_LABELS.norm_verification} · прогон ${RUN_ID} · состояние: Завершена`,
    );
  });

  it('says «Другой этап» for a stage the list does not hold, and the page copied has no raw value', () => {
    const text = journalCopyText([entry('stage.started', { stage_id: 'secret_stage_x' })], { runId: RUN_ID });
    expect(text).toContain('Этап начат · Другой этап · прогон');
    expect(text).not.toContain('secret_stage_x');
  });
});

describe('the closed projection', () => {
  const FOREIGN = {
    stage_id: 'text_analysis',
    completed_pages: 3,
    total_pages: 10,
    message: 'NEVER_RENDER_message',
    text: 'NEVER_RENDER_text',
    prompt: 'NEVER_RENDER_prompt',
    model_output: 'NEVER_RENDER_model_output',
    model: 'NEVER_RENDER_model',
    host: 'NEVER_RENDER_host',
    stage_name: 'NEVER_RENDER_stage_name',
    stage: 'NEVER_RENDER_stage',
    stage_title: 'NEVER_RENDER_stage_title',
    heartbeat_at: 'NEVER_RENDER_heartbeat',
    cost_usd: 'NEVER_RENDER_cost',
    tokens: 123456789,
    phase: 'NEVER_RENDER_phase',
    reason: 'NEVER_RENDER_reason',
    error_code: 'NEVER_RENDER_error_code',
    state: 'NEVER_RENDER_state',
  } as const;

  it('lets no field of an event through but the closed ones: not on the screen, not in the copied text', () => {
    const entries = [
      entry('stage.started', FOREIGN),
      entry('stage.progress', FOREIGN),
      entry('stage.pdf_precheck', FOREIGN),
      entry('stage.finished', FOREIGN),
      entry('audit_run.transition', FOREIGN),
    ];
    const markup = drawn(entries);
    const copied = journalCopyText(entries, { runId: RUN_ID });
    for (const text of [markup, copied]) {
      expect(text).not.toContain('NEVER_RENDER');
      expect(text).not.toContain('123456789');
    }
    // What does pass, passes in the words of the contract's lists.
    expect(markup).toContain(STAGE_LABELS.text_analysis);
    expect(markup).toContain('стр. 3 из 10');
  });

  it('is built from nothing but the stage id and the two page counts of a stage event', () => {
    const shown = visibleJournal(entry('stage.progress', FOREIGN));
    expect(Object.keys(shown).sort()).toEqual(['code', 'event', 'pages', 'stage', 'state']);
    expect(shown.stage).toEqual({ id: 'text_analysis', label: STAGE_LABELS.text_analysis });
    expect(shown.pages).toEqual({ completed: 3, total: 10 });
    expect(shown.state).toBeNull();
    expect(shown.code).toBeNull();
  });
});
