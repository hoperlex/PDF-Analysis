/**
 * `UI-B-34`, `UIP-S12-02`: the knowledge base as the original's table, and the page's default view.
 *
 * What is held: one row a decision, the columns «Тип · Объект · документ · Раздел · Критичность · Суть · Причина решения · Дата»
 * and the way to the finding, in that order, and no «Решение» column: the verdict is the sign in the first cell (✓ green, ✕ red,
 * the word as its name) and the stripe at the row's edge; the object and the document are one cell; the date is one line with
 * the UTC stamp, the author and the count of decisions as its tooltip; the five severities are five tones. The project and the
 * section are the record's own (no further read, no label made up for a section the record does not carry); «Все» draws a finding
 * and a proposal in the same table; the widget still draws the events when it is not told otherwise, so the screens that render it
 * as it was keep their markup; a closed vocabulary still fails closed in the table.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DecisionRecord, KnowledgeBaseEntry } from '@/shared/api';
import { KnowledgeBase } from '@/widgets/knowledge-base';

const ULID = '01M2545JSD15ETSNNV904X991F';

function record(over: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    decision_id: `dec_${ULID}`,
    finding_uid: `fnd_${ULID}`,
    finding_observation_id: `fobs_${ULID}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: 'Согласовано с заказчиком.',
    author_label: 'Петрова А.',
    recorded_at: '2026-09-10T09:00:00.000Z',
    project_uid: `prj_${ULID}`,
    run_id: `run_${ULID}`,
    document_uid: `doc_${ULID}`,
    version_uid: `ver_${ULID}`,
    project_name: 'Школа',
    document_name: 'АР-1',
    section: 'AR',
    category: 'internal_contradiction',
    severity: 'critical',
    finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...over,
  };
}

const table = (records: readonly DecisionRecord[], entries?: readonly KnowledgeBaseEntry[]): string =>
  renderToStaticMarkup(createElement(KnowledgeBase, { view: 'table', records, ...(entries === undefined ? {} : { entries }) }));

/** The cells of the one row, as text. */
function cells(markup: string): string[] {
  const row = markup.match(/<tbody>[\s\S]*?<tr[^>]*>([\s\S]*?)<\/tr>/)?.[1] ?? '';
  return [...row.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((cell) => (cell[1] ?? '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim());
}

describe('the table', () => {
  it('has the original’s columns, in the original’s order, and no «Решение» column', () => {
    const markup = table([record(), record({ decision_id: 'dec_01M2545JSD15ETSNNV904X992A' })]);
    const heads = [...markup.matchAll(/<th scope="col"(?: class="[^"]*")?>([^<]*)<\/th>/g)].map((head) => head[1]);
    expect(heads).toEqual(['Тип', 'Объект · документ', 'Раздел', 'Критичность', 'Суть', 'Причина решения', 'Дата', 'Замечание']);
    expect(heads).not.toContain('Решение');
    expect(markup.match(/<tr data-decision-id=/g) ?? []).toHaveLength(2);
    expect(markup).toContain('data-record-count="2"');
    expect(markup).toContain('data-knowledge-base-view="table"');
    expect(markup).not.toContain('am-kb__record');
  });

  it('is eight cells a row, the way to the finding the last', () => {
    expect(cells(table([record()]))).toHaveLength(8);
    expect(cells(table([record()])).at(-1)).toBe('Открыть замечание');
  });

  it('puts the object and its document in one cell on one line, the whole as a tooltip, the section by its short name, the reason in a column', () => {
    const [type, place, section, severity, gist, reason, date, link] = cells(table([record()]));
    expect(type).toBe('✓ Внутреннее противоречие');
    expect(place).toBe('Школа · АР-1');
    expect(section).toBe('АР');
    expect(severity).not.toBe('—');
    expect(gist).toBe('Срок поставки указан как 30 дней в §4 и как 45 дней в §9.');
    expect(reason).toBe('Согласовано с заказчиком.');
    expect(date).toBe('10.09.2026 09:00');
    expect(link).toBe('Открыть замечание');
    const markup = table([record()]);
    expect(markup).toContain('title="Школа · АР-1"');
    expect(markup).toContain('title="Архитектурные решения (АР)"');
    // The gist and the reason are cut at two lines; the whole text is the tooltip.
    expect(markup).toContain('title="Срок поставки указан как 30 дней в §4 и как 45 дней в §9."');
    expect(markup).toContain('title="Согласовано с заказчиком."');
  });

  it('says a long name whole in the tooltip, and prints it whole for the stylesheet to cut', () => {
    const long = 'Учебный корпус «Маяк-7» с подземной парковкой и пристроенным спортивным залом';
    const markup = table([record({ project_name: long, document_name: 'АР-1. Планы этажей' })]);
    expect(markup).toContain(`title="${long} · АР-1. Планы этажей"`);
    expect(cells(markup)[1]).toBe(`${long} · АР-1. Планы этажей`);
  });

  it('draws the verdict as a sign with a name, ✓ for a decision for and ✕ for one against, and no word «приём» or «ПРИЁМ» beside it', () => {
    const accepted = table([record()]);
    expect(accepted).toMatch(/<span[^>]*role="img"[^>]*aria-label="Принято"[^>]*data-verdict="accepted"[^>]*>✓<\/span>/);
    const rejected = table([record({ current_verdict: 'rejected', verdict: 'rejected', event_type: 'reject' })]);
    expect(rejected).toMatch(/<span[^>]*role="img"[^>]*aria-label="Отклонено"[^>]*data-verdict="rejected"[^>]*>✕<\/span>/);
    for (const markup of [accepted, rejected]) {
      // What the reader sees is the cells' text: the event's word is in a tooltip only, and no cell of its own prints it.
      expect(cells(markup).join(' ')).not.toMatch(/приём|отклонение|ПРИЁМ|принято|отклонено/i);
      expect(markup).not.toContain('am-kb__verdict');
    }
  });

  it('says the sign of the verdict that STANDS, whatever event the row is: a comment on an accepted finding is still ✓', () => {
    const markup = table([record({ event_type: 'comment', verdict: null, comment: 'Спорно.' })]);
    expect(markup).toContain('aria-label="Принято"');
    expect(markup).toContain('data-event-type="comment"');
  });

  it('gives a finding nobody has decided a dash for a sign, named «Не решено», not a tick', () => {
    const markup = table([record({ current_verdict: 'pending', verdict: null, event_type: 'comment' })]);
    expect(markup).toContain('aria-label="Не решено"');
    expect(markup).not.toContain('>✓<');
    expect(markup).not.toContain('>✕<');
  });

  it('prints the date on one line, and puts the exact UTC stamp, the event, the author and the count in its tooltip', () => {
    const markup = table([record({ decision_event_count: 3 })]);
    const date = cells(markup)[6];
    expect(date).toBe('10.09.2026 09:00');
    expect(date).not.toContain('Петрова');
    expect(date).not.toContain('UTC');
    const tooltip = /<time[^>]*title="([^"]*)"/.exec(markup)?.[1] ?? '';
    expect(tooltip).toContain('2026-09-10 09:00:00 UTC');
    expect(tooltip).toContain('Петрова А.');
    expect(tooltip).toContain('решений по замечанию: 3');
    expect(tooltip).toContain('приём');
    expect(markup).toContain('data-event-count="3"');
    expect(markup).toContain('dateTime="2026-09-10T09:00:00.000Z"');
  });

  it('says one decision in words that do not read as an ordinal', () => {
    expect(table([record()])).toContain('одно решение по замечанию');
  });

  it('leaves the section’s cell empty, and names none, for a version no expert has classified', () => {
    const { section, ...unclassified } = record();
    void section;
    const markup = table([unclassified]);
    expect(cells(markup)[2]).toBe('—');
    expect(markup).not.toContain('data-section-cell');
    expect(markup).not.toContain('Без раздела');
  });

  it('says a missing severity as a dash, and a missing reason as a dash or a quiet word, never as a blank or a zero', () => {
    const { severity, ...without } = record({ comment: null });
    void severity;
    const [, , , sev, , reason] = cells(table([without]));
    expect(sev).toBe('—');
    // An accepted decision with no reason says what it is (`UIP-S12-04`); the dash is for a finding nobody has decided.
    expect(reason).toBe('Принято');
    expect(cells(table([{ ...without, current_verdict: 'pending', verdict: null, event_type: 'comment' }]))[5]).toBe('—');
  });

  it('draws the five severities in five tones: red, amber, accent, green and grey, each with its own word', () => {
    const tones: readonly (readonly [NonNullable<DecisionRecord['severity']>, string, string])[] = [
      ['critical', 'failed', 'Критическое'],
      ['economic', 'degraded', 'Экономическое'],
      ['operational', 'active', 'Эксплуатационное'],
      ['recommendation', 'ok', 'Рекомендация'],
      ['check_adjacent', 'inert', 'Проверить смежный раздел'],
    ];
    for (const [severity, tone, word] of tones) {
      const markup = table([record({ severity })]);
      expect(markup, severity).toContain(`class="am-badge am-badge--${tone}" data-severity="${severity}"`);
      expect(cells(markup)[3], severity).toBe(word);
    }
    expect(new Set(tones.map(([, tone]) => tone)).size).toBe(5);
  });

  it('links the finding by the identities the record carries and by nothing else', () => {
    const markup = table([record()]);
    expect(markup).toContain(`href="/projects/prj_${ULID}/runs/run_${ULID}/review?finding=fnd_${ULID}"`);
    expect(markup).toContain(`data-finding-uid="fnd_${ULID}"`);
  });

  it('marks each row with the verdict that stands, for the stripe at its edge', () => {
    const markup = table([record({ current_verdict: 'rejected', verdict: 'rejected', event_type: 'reject' })]);
    expect(markup).toContain('data-current-verdict="rejected"');
    expect(markup).toContain('data-verdict="rejected"');
  });

  it('fails closed on an unknown value, as the events do, and draws no table', () => {
    const markup = table([{ ...record(), category: 'guessed' } as unknown as DecisionRecord]);
    expect(markup).toContain('data-knowledge-base-fault="closed-vocabulary"');
    expect(markup).not.toContain('<table');
  });
});

describe('«Причина решения» says what the decision rests on (UIP-S12-04)', () => {
  const REASON = 5;
  const rejected = { current_verdict: 'rejected', verdict: 'rejected', event_type: 'reject' } as const;
  const reasonOf = (over: Partial<DecisionRecord>): string => cells(table([record(over)]))[REASON] ?? '';
  const STATUS_WORDS = [
    ['taken_into_account', 'Учтено'],
    ['amended', 'Внесено'],
    ['declined', 'Отклонено'],
    ['agreed', 'По согласованию'],
  ] as const;

  it('shows the expert’s reason for any decision that has one, a rejection too', () => {
    expect(reasonOf({ ...rejected, comment: 'Не согласен: нет обоснования.' })).toBe('Не согласен: нет обоснования.');
    expect(reasonOf({ comment: 'Согласовано с заказчиком.' })).toBe('Согласовано с заказчиком.');
  });

  it('puts the designer’s status beside the reason of an accepted finding, in the words of the vocabulary, all four of them', () => {
    for (const [status, word] of STATUS_WORDS) {
      expect(reasonOf({ comment: 'Согласовано.', execution_status: status }), status).toBe(`Согласовано. ${word}`);
    }
  });

  it('draws the status as a pill with its own name, which is not the verdict and not a second sign', () => {
    const markup = table([record({ execution_status: 'amended' })]);
    expect(markup).toMatch(/<span class="am-badge am-badge--inert" title="Статус исполнения проектировщиком" data-execution-status="amended">Внесено<\/span>/);
    // The sign of the row is still the expert's: one ✓, no second mark for the status.
    expect(markup.match(/role="img"/g) ?? []).toHaveLength(1);
    expect(markup).toContain('aria-label="Принято"');
  });

  it('shows the status alone, with no dash and no «Принято», when the decision has no reason of its own', () => {
    expect(reasonOf({ comment: null, execution_status: 'taken_into_account' })).toBe('Учтено');
    expect(reasonOf({ comment: null, execution_status: 'agreed' })).toBe('По согласованию');
  });

  it('says what the decision is in a quiet word when it has neither a reason nor a status: «Принято» or «Отклонено»', () => {
    expect(reasonOf({ comment: null })).toBe('Принято');
    expect(reasonOf({ ...rejected, comment: null })).toBe('Отклонено');
    const markup = table([record({ comment: null })]);
    expect(markup).toMatch(/<span class="[^"]*cellMuted[^"]*">Принято<\/span>/);
  });

  it('does not say the quiet word when there is a reason, and does not repeat the verdict the sign already says', () => {
    expect(reasonOf({ comment: 'Согласовано.' })).not.toContain('Принято');
    expect(reasonOf({ ...rejected, comment: 'Нет.' })).not.toContain('Отклонено');
  });

  it('keeps the status to an accepted finding: a rejected one with a status left on it shows none', () => {
    expect(reasonOf({ ...rejected, comment: 'Нет.', execution_status: 'amended' })).toBe('Нет.');
    expect(reasonOf({ ...rejected, comment: null, execution_status: 'amended' })).toBe('Отклонено');
  });

  it('keeps the dash for a finding nobody has decided: it is neither accepted nor rejected, so it has no word', () => {
    expect(reasonOf({ current_verdict: 'pending', verdict: null, event_type: 'comment', comment: null })).toBe('—');
    expect(reasonOf({ current_verdict: 'pending', verdict: null, event_type: 'comment', comment: 'Вопрос.' })).toBe('Вопрос.');
  });

  it('reads a status from the record: the same finding with and without one is two different cells', () => {
    expect(reasonOf({ comment: null, execution_status: 'amended' })).not.toBe(reasonOf({ comment: null }));
  });

  it('says the same in «Все»: a finding’s reason cell is the same cell, and a proposal has its own quiet word', () => {
    const FINDING = record({ comment: null, execution_status: 'agreed' });
    const markup = table([], [
      { kind: 'finding', occurred_at: FINDING.recorded_at, finding: FINDING },
      { kind: 'finding', occurred_at: FINDING.recorded_at, finding: record({ decision_id: 'dec_01M2545JSD15ETSNNV904X992A', comment: null }) },
    ]);
    const rows = [...markup.matchAll(/<tr data-decision-id=[\s\S]*?<\/tr>/g)].map(
      (row) => [...row[0].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((cell) => (cell[1] ?? '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim())[REASON],
    );
    expect(rows).toEqual(['По согласованию', 'Принято']);
  });
});

describe('«Все» in the table', () => {
  const FINDING = record();
  const ENTRIES: readonly KnowledgeBaseEntry[] = [
    { kind: 'finding', occurred_at: FINDING.recorded_at, finding: FINDING },
    {
      kind: 'proposal',
      occurred_at: '2026-11-06T09:00:00Z',
      proposal: {
        proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
        optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'reject', comment: 'Аналог не подходит.',
        actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: `prj_${ULID}`,
        project_name: 'Мост через Неву', document_uid: `doc_${ULID}`, document_name: 'Архитектурные решения',
        version_uid: `ver_${ULID}`, section: 'AR', row_text: 'Дверь металлическая ДМ-1', proposed_vendor: 'ООО «Двери»', unit: 'шт',
      },
    },
  ];
  const markup = table([], ENTRIES);

  it('draws a finding and a proposal in the one table, each saying its kind', () => {
    expect(markup).toContain('data-knowledge-base-kind="all"');
    expect(markup).toContain('data-record-count="2"');
    expect(markup.match(/<table/g) ?? []).toHaveLength(1);
    expect(markup).toContain('Замечание · ');
    expect(markup).toContain('>Предложение<');
    expect(markup.indexOf('data-decision-id')).toBeLessThan(markup.indexOf('data-proposal-decision-id'));
  });

  it('gives a proposal the same columns: place, section, the row and its vendor, the reason and the way to its optimisation', () => {
    const row = markup.slice(markup.indexOf('data-proposal-decision-id'));
    expect(row).toContain('Мост через Неву · Архитектурные решения');
    expect(row).not.toContain('Решение');
    expect(row).toContain('Дверь металлическая ДМ-1 · поставщик ООО «Двери» · ед. шт');
    expect(row).toContain('Аналог не подходит.');
    expect(row).toContain('Открыть оптимизацию');
    expect(row).toContain('data-section-cell="AR"');
  });
});

describe('a proposal’s verdict in the table', () => {
  const PROPOSAL = (verdict: 'accept' | 'reject' | 'revise' | 'revoke', comment: string | null): KnowledgeBaseEntry => ({
    kind: 'proposal',
    occurred_at: '2026-11-06T09:00:00Z',
    proposal: {
      proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
      optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict, comment, actor_label: 'Иванова А. С.',
      decided_at: '2026-11-06T09:00:00Z', project_uid: `prj_${ULID}`, project_name: 'Мост через Неву', document_uid: `doc_${ULID}`,
      document_name: 'Архитектурные решения', version_uid: `ver_${ULID}`, section: 'AR', row_text: 'Дверь металлическая ДМ-1',
      proposed_vendor: 'ООО «Двери»', unit: 'шт',
    },
  });
  const draw = (verdict: 'accept' | 'reject' | 'revise' | 'revoke', comment: string | null = null) => table([], [PROPOSAL(verdict, comment)]);

  it('is ✓ for an acceptance and ✕ for a rejection, with the stripe’s marker on the row', () => {
    expect(draw('accept')).toContain('aria-label="Принято"');
    expect(draw('accept')).toContain('data-proposal-verdict="accept"');
    expect(draw('reject')).toContain('aria-label="Отклонено"');
    expect(draw('reject')).toContain('data-proposal-verdict="reject"');
  });

  it('says «Принято» or «Отклонено» quietly for a proposal with no reason, as a finding does', () => {
    expect(cells(draw('accept'))[5]).toBe('Принято');
    expect(cells(draw('reject'))[5]).toBe('Отклонено');
    expect(cells(draw('accept', 'Аналог подходит.'))[5]).toBe('Аналог подходит.');
  });

  it('is no sign for «на доработку» and «решение снято», which are not decisions for or against: their words stand under the reason', () => {
    for (const [verdict, word] of [['revise', 'На доработку'], ['revoke', 'Решение снято']] as const) {
      const markup = draw(verdict);
      expect(markup).not.toContain('role="img"');
      expect(cells(markup)[5]).toBe(word);
    }
    expect(cells(draw('revise', 'Уточните марку.'))[5]).toBe('Уточните марку. На доработку');
  });

  it('draws the date of a proposal on one line, with the UTC stamp and the actor in the tooltip', () => {
    const markup = draw('accept');
    expect(cells(markup)[6]).toBe('06.11.2026 09:00');
    expect(markup).toContain('title="2026-11-06 09:00:00 UTC · Иванова А. С."');
  });
});

describe('the widget keeps its events when it is not told otherwise', () => {
  it('draws the rows as events by default', () => {
    const markup = renderToStaticMarkup(createElement(KnowledgeBase, { records: [record()] }));
    expect(markup).toContain('class="am-kb__record"');
    expect(markup).not.toContain('<table');
    expect(renderToStaticMarkup(createElement(KnowledgeBase, { view: 'events', records: [record()] }))).toContain('class="am-kb__record"');
  });
});
