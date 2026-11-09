/**
 * `D-495`: what the memory’s widgets draw from what the server sent -- and what they refuse to invent.
 *
 * One synchronous pass, no transport. Each case can fail: a crop is text and nothing in the view asks for its bytes; the contract
 * value stays on a `data-*` attribute while the reader gets Russian; a forgotten case draws its tombstone and no words; a
 * withdrawn case says so; a category or a section this build does not know is left as sent, never named.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { DecisionMemoryCaseView, DecisionMemoryFilters, DecisionMemoryList, DecisionMemoryStatusLine, boxFrameWords, formatBox, sizeLabel } from '@/widgets/decision-memory';
import { NO_MEMORY_FILTERS } from '@/entities/decision-memory';

import { COUNTS, CASE_A, CASE_B, summary, wholeCase } from './memory-fixtures';

const noop = () => undefined;

const list = (props: Partial<Parameters<typeof DecisionMemoryList>[0]> = {}) =>
  renderToStaticMarkup(createElement(DecisionMemoryList, { cases: [], isLoading: false, error: null, narrowed: false, onOpen: noop, ...props }));

const view = (props: Partial<Parameters<typeof DecisionMemoryCaseView>[0]> = {}) =>
  renderToStaticMarkup(createElement(DecisionMemoryCaseView, { data: wholeCase(), isLoading: false, error: null, manage: false, onBack: noop, ...props }));

describe('the list', () => {
  it('draws one row a case with the contract values on data attributes and Russian words on the screen', () => {
    const markup = list({
      cases: [
        summary(),
        summary({ case_id: CASE_B, status: 'withdrawn', status_reason_code: 'client_request', current_verdict: 'rejected', current_severity: null, data_class: 'real', decision_count: 2 }),
      ],
    });
    expect(markup).toContain('data-record-count="2"');
    expect(markup).toContain(`data-memory-case="${CASE_A}"`);
    expect(markup).toContain('data-memory-status="withdrawn"');
    expect(markup).toContain('data-memory-reason="client_request"');
    expect(markup).toContain('Просьба клиента');
    expect(markup).toContain('Отозвано');
    expect(markup).toContain('Отклонено');
    expect(markup).toContain('Реальные');
    expect(markup).toContain('решений: 2');
    expect(markup).toContain('Внутреннее противоречие');
    expect(markup).toContain('data-section-cell="AR"');
  });

  it('leaves a category or a section this build does not know as sent, and never names it', () => {
    const markup = list({ cases: [summary({ category: 'acoustics_v9', section_code: 'XYZ' })] });
    expect(markup).toContain('acoustics_v9');
    expect(markup).toContain('XYZ');
    expect(markup).not.toContain('data-section-cell="XYZ"');
  });

  it('draws a case with no decision yet as a dash, not as a verdict', () => {
    const markup = list({ cases: [summary({ current_verdict: null, current_severity: null })] });
    expect(markup).toContain('data-memory-verdict="none"');
    expect(markup).not.toContain('am-kb__verdict');
  });

  it('says loading, failure and the two kinds of empty page apart', () => {
    expect(list({ isLoading: true })).toContain('Загрузка: память решений');
    expect(list({ error: { title: 'Память решений не открылась', detail: 'Сервер не ответил.' } })).toContain('Память решений не открылась');
    expect(list()).toContain('Память решений пока пуста.');
    const narrowed = list({ narrowed: true, onResetFilters: vi.fn() });
    expect(narrowed).toContain('В памяти решений нет дел под этот отбор.');
    expect(narrowed).toContain('Сбросить отбор');
    expect(list({ narrowed: true })).not.toContain('Сбросить отбор');
  });
});

describe('the case', () => {
  it('draws the finding, the decisions, the evidence, the norms and the crops, and the crops are text', () => {
    const markup = view();
    expect(markup).toContain('data-memory-finding-text=""');
    expect(markup).toContain('требуется: +0,150');
    expect(markup).toContain('указано: +0,300');
    expect(markup).toContain('Построение контекста документа');
    expect(markup).toContain('из записи');
    expect(markup).toContain('data-memory-decision="dmd_01M2545JSD15ETSNNV904X994C"');
    expect(markup).toContain('решено на находке');
    // Evidence: one-based number, page, characters, block, the box with its unit and origin; three decimals at most.
    expect(markup).toContain('№1 · стр. 3 · символы 10–30');
    expect(markup).toContain('блок <code>b_000012</code>');
    expect(markup).toContain('рамка [72; 120.457; 300; 140] (пт, от левого верхнего угла)');
    expect(markup).toContain('подтверждена');
    // Crops.
    expect(markup).toContain('Кадр 1 · стр. 3 · рамка [0.1; 0.2; 0.6; 0.7] (доли страницы) · 640×480 пикс. · 20 КБ · к подтверждению №1');
    expect(markup).toContain('a'.repeat(64));
    expect(markup).not.toContain('<img');
    expect(markup).not.toContain('<a ');
    expect(markup).toContain('Изображения кадров пока не открываются');
  });

  it('draws no control for a viewer-like reader: the standing change is the administrator’s', () => {
    expect(view({ manage: false })).not.toContain('data-memory-standing-control');
  });

  it('says a withdrawn case is withdrawn, with its reason and its history', () => {
    const markup = view({
      data: wholeCase(
        { status_events: [{ status_event_id: 'dmw_01M2545JSD15ETSNNV904X996E', kind: 'withdraw', reason_code: 'test_data', created_at: '2026-11-09T10:00:00Z', forgotten_content_sha256: null }] },
        { status: 'withdrawn', status_reason_code: 'test_data', status_changed_at: '2026-11-09T10:00:00Z' },
      ),
    });
    expect(markup).toContain('data-memory-standing-note="withdrawn"');
    expect(markup).toContain('Причина: тестовые данные.');
    expect(markup).toContain('data-memory-event-kind="withdraw"');
    expect(markup).toContain('История состояния');
  });

  it('draws a forgotten case’s tombstone and nothing in place of its words', () => {
    const markup = view({
      data: wholeCase(
        {
          content: null, decisions: [], evidence: [], norm_refs: [], crops: [],
          status_events: [{ status_event_id: 'dmw_01M2545JSD15ETSNNV904X997F', kind: 'forget', reason_code: 'client_request', created_at: '2026-11-09T12:00:00Z', forgotten_content_sha256: 'c'.repeat(64) }],
        },
        { status: 'forgotten', status_reason_code: 'client_request' },
      ),
    });
    expect(markup).toContain('data-memory-standing-note="forgotten"');
    expect(markup).toContain('Содержимое дела забыто');
    expect(markup).toContain('c'.repeat(64));
    expect(markup).not.toContain('Находка и рекомендация');
    expect(markup).not.toContain('data-memory-finding-text');
    expect(markup).not.toContain('data-memory-decision=');
  });

  it('says loading and failure with the way back', () => {
    expect(view({ data: undefined, isLoading: true })).toContain('Загрузка: дело');
    const failed = view({ data: undefined, error: { title: 'Дело не открылось', detail: 'Дело не найдено.' } });
    expect(failed).toContain('Дело не открылось');
    expect(failed).toContain('← К списку дел');
  });
});

describe('the administrator’s status line', () => {
  it('names the counts, the class a new case gets and whether training is on', () => {
    const markup = renderToStaticMarkup(createElement(DecisionMemoryStatusLine, { status: COUNTS, error: null }));
    expect(markup).toContain('дел: <strong>5</strong>');
    expect(markup).toContain('решений: <strong>7</strong>');
    expect(markup).toContain('новые дела записываются как: <strong>тестовые</strong>');
    expect(markup).toContain('обучение на памяти: <strong>выключено</strong>');
    const real = renderToStaticMarkup(createElement(DecisionMemoryStatusLine, { status: { ...COUNTS, data_class: 'real', training_use: 'on' }, error: null }));
    expect(real).toContain('<strong>реальные</strong>');
    expect(real).toContain('<strong>включено</strong>');
  });

  it('draws nothing before the answer and says a failure rather than staying silent', () => {
    expect(renderToStaticMarkup(createElement(DecisionMemoryStatusLine, { status: undefined, error: null }))).toBe('');
    const failed = renderToStaticMarkup(createElement(DecisionMemoryStatusLine, { status: undefined, error: { title: 'Сводка памяти не получена', detail: 'Сервер не ответил.', correlationId: 'cid-1' } }));
    expect(failed).toContain('Сводка не получена. Сервер не ответил.');
    expect(failed).toContain('cid-1');
  });
});

describe('the filters', () => {
  it('offers the five filters the operation has, each with «all» first', () => {
    const markup = renderToStaticMarkup(createElement(DecisionMemoryFilters, { value: NO_MEMORY_FILTERS, onChange: noop }));
    for (const label of ['Состояние', 'Вердикт', 'Категория', 'Раздел', 'Данные']) expect(markup).toContain(`>${label}</label>`);
    expect(markup).toContain('Любое состояние');
    expect(markup).toContain('Любой раздел');
    expect(markup).toContain('Пояснительная записка (ПЗ)');
  });
});

describe('the plain-text forms', () => {
  it('words the unit and the origin of a box, and leaves a value it does not know as sent', () => {
    expect(boxFrameWords('pt', 'top_left')).toBe('пт, от левого верхнего угла');
    expect(boxFrameWords(null, null)).toBe('');
    expect(boxFrameWords('mm', 'centre')).toBe('mm, centre');
  });
  it('keeps three decimals at most and drops trailing zeros', () => {
    expect(formatBox([0.1, 0.123456, 0.5, 1])).toBe('[0.1; 0.123; 0.5; 1]');
  });
  it('rounds a size up to one kilobyte at the least', () => {
    expect(sizeLabel(1)).toBe('1 КБ');
    expect(sizeLabel(20480)).toBe('20 КБ');
  });
});
