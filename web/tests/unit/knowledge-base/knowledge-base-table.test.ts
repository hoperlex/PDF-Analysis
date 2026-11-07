/**
 * `UI-B-34`: the knowledge base as the original's table, and the page's default view.
 *
 * What is held: one row a decision with the project, the section, the severity, the verdict, the reason and the date each in its
 * own column; the project and the section are the record's own (no further read, no label made up for a section the record
 * does not carry); «Все» draws a finding and a proposal in the same table; the widget still draws the events when it is not
 * told otherwise, so the screens that render it as it was keep their markup; the page opens on the table and the events
 * are one press away; a closed vocabulary still fails closed in the table.
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
  it('has the original’s columns, in the original’s order, and one row a decision', () => {
    const markup = table([record(), record({ decision_id: 'dec_01M2545JSD15ETSNNV904X992A' })]);
    const heads = [...markup.matchAll(/<th scope="col">([^<]*)<\/th>/g)].map((head) => head[1]);
    expect(heads).toEqual(['Тип', 'Проект', 'Раздел', 'Важность', 'Решение', 'Суть', 'Причина решения', 'Дата', 'Находка']);
    expect(markup.match(/<tr data-decision-id=/g) ?? []).toHaveLength(2);
    expect(markup).toContain('data-record-count="2"');
    expect(markup).toContain('data-knowledge-base-view="table"');
    expect(markup).not.toContain('am-kb__record');
  });

  it('puts the project over its document, the section by its short name with the title as a tooltip, and the reason in a column', () => {
    const [type, place, section, severity, verdict, gist, reason, date, link] = cells(table([record()]));
    expect(type).toBe('Внутреннее противоречие');
    expect(place).toBe('Школа АР-1');
    expect(section).toBe('АР');
    expect(severity).not.toBe('—');
    expect(verdict).toContain('принято');
    expect(gist).toBe('Срок поставки указан как 30 дней в §4 и как 45 дней в §9.');
    expect(reason).toBe('Согласовано с заказчиком.');
    expect(date).toContain('Петрова А.');
    expect(date).toContain('одно решение по находке');
    expect(link).toBe('Открыть находку');
    expect(table([record()])).toContain('title="Архитектурные решения (АР)"');
  });

  it('leaves the section’s cell empty, and names none, for a version no expert has classified', () => {
    const { section, ...unclassified } = record();
    void section;
    const markup = table([unclassified]);
    expect(cells(markup)[2]).toBe('—');
    expect(markup).not.toContain('data-section-cell');
    expect(markup).not.toContain('Без раздела');
  });

  it('says a missing comment and a missing severity as a dash, never as a blank or a zero', () => {
    const { severity, ...without } = record({ comment: null });
    void severity;
    const [, , , sev, , , reason] = cells(table([without]));
    expect(sev).toBe('—');
    expect(reason).toBe('—');
  });

  it('says how many decisions the finding holds, in words that decline', () => {
    expect(table([record({ decision_event_count: 3 })])).toContain('решений по находке: 3');
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
    expect(row).toContain('Мост через Неву');
    expect(row).toContain('Дверь металлическая ДМ-1 · поставщик ООО «Двери» · ед. шт');
    expect(row).toContain('Аналог не подходит.');
    expect(row).toContain('Открыть оптимизацию');
    expect(row).toContain('data-section-cell="AR"');
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
