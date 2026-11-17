/**
 * «Предложения» rendered (`W60-OPT-PROPOSALS-01`): the set chooser, the passes with their
 * counts by decision, the proposals with their provenance, both exact prices and the saving
 * only where it is stated, the controls each role is given, and every refusal in Russian.
 */

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { OPTIMISATION_MOVED_TO, OptimisationPage } from '@/_pages/optimisation';
import { CARRYOVER_REFUSAL_TEXT, carrySources } from '@/entities/optimisation-proposal';
import { CarryOverProposalDecisionsView } from '@/features/carry-over-proposal-decisions';
import {
  PROPOSAL_IMPORT_REFUSAL_LABELS,
  ImportProposalDecisionsView,
  importProposalFailure,
} from '@/features/import-proposal-decisions';
import {
  EXPORT_CSV_LABEL,
  EXPORT_XLSX_LABEL,
  ExportProposalsView,
  ProposalCard,
  ProposalHistoryView,
  ProposalListView,
  classifiedDocumentSets,
} from '@/widgets/optimisation-proposals';
import { ApiError } from '@/shared/api';
import type { ProposalDecisionImportRefusal } from '@/shared/api';

import { mountLive } from '../analysis-settings/live-render';
import { newClient, renderScreen } from '../screens/harness';
import {
  OLDER_PASS_ID,
  arVersion,
  decision,
  otherSectionVersion,
  pass,
  proposal,
  proposalPage,
  proposalShapes,
  SHEET_URL,
  unclassifiedVersion,
} from './fixtures';

function rendered(name: string): string {
  const shape = proposalShapes().find((entry) => entry.name === name);
  if (shape === undefined) throw new Error(`no shape ${name}`);
  const client = newClient();
  shape.seedClient?.(client);
  return renderScreen(client, shape.make());
}

describe('the sets', () => {
  it('offers every set whose current version an expert confirmed, whatever the section', () => {
    expect(classifiedDocumentSets([arVersion(), otherSectionVersion(), unclassifiedVersion()])).toEqual([
      arVersion(),
      otherSectionVersion(),
    ]);
  });

  it('names the section of each set it offers', () => {
    const markup = rendered('proposals-set-chooser');
    expect(markup).toContain('Комплект АР — версия 2, раздел АР');
    expect(markup).toContain('Комплект АР, корпус 2 — версия 2, раздел АР');
    const loaded = rendered('proposals-loaded');
    expect(loaded).toContain('Комплект КЖ — версия 2, раздел КЖ');
  });

  it('says where a section is confirmed when there is none, and that the list is partial', () => {
    const markup = rendered('proposals-no-classified-sets');
    expect(markup).toContain('В объекте нет комплектов с подтверждённым разделом');
    expect(markup).toContain('Подтвердите раздел на экране версии');
    expect(markup).not.toContain('раздела АР');
    expect(rendered('proposals-set-chooser')).toContain('Предложены комплекты первой страницы');
    expect(rendered('proposals-set-chooser')).toContain('Комплект АР, корпус 2 — версия 2');
  });
});

describe('the loaded section for an expert', () => {
  const markup = rendered('proposals-loaded');

  it('lists the passes and opens the newest, with the proposals’ own counts', () => {
    expect(markup).toContain('data-pass-count="2"');
    expect(markup).toContain('data-optimisation-pass="opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N"');
    expect(markup).toContain('data-decision-count="pending"');
    expect(markup).toContain('не решено: <strong>1</strong>');
    expect(markup).toContain('на доработку: <strong>1</strong>');
    expect(markup).toContain('не смешиваются со счётчиками замечаний');
  });

  it('opens on the table, with the link to the cards (`UIP-S09-01`)', () => {
    expect(markup).toContain('data-proposal-table');
    expect(markup).not.toContain('<article');
    expect(markup).toContain('data-proposal-layout="table"');
    expect(markup).toContain('Показать карточками');
    // The rows stand by verdict, and each says its own number and state: the first pass of the seed holds one waiting and one for revision.
    const rows = [...markup.matchAll(/<tr data-proposal="[^"]+" data-proposal-ordinal="(\d+)" data-decision="([^"]+)">/g)].map(
      (row) => `${row[1]}:${row[2]}`,
    );
    expect(rows).toEqual(['2:pending', '1:revise']);
  });

  it('shows the provenance, both exact prices and the saving where it is stated', () => {
    expect(markup).toContain('страница 2, лист 10, строки 3–4, позиция 1');
    expect(markup).toContain('25 000 руб.');
    expect(markup).toContain('21 000,5 руб.');
    expect(markup).toContain('Экономия: 17 998 руб.');
    expect(markup).toContain('Поставщик: Кнауф Гипс');
  });

  it('says a saving that cannot be computed is not computed, and shows no zero for it', () => {
    expect(markup).toContain('Экономия не рассчитана: в спецификации количество не записано числом.');
    expect(markup).toContain('«-» (не число)');
    expect(markup).toContain('Поставщик: не указан');
    expect(markup).not.toContain('Экономия: 0');
  });

  it('gives an expert the start, the decision buttons and the CSV, and the current decision', () => {
    expect(markup).toContain('Запустить проход');
    expect(markup).toContain('Принять');
    expect(markup).toContain('Отклонить');
    expect(markup).toContain('На доработку');
    expect(markup).toContain('data-proposal-decision=');
    expect(markup).toContain('Выгрузить CSV предложений');
    expect(markup).toContain('Решение: <strong>на доработку</strong>, Петрова А.');
    expect(markup).toContain('Уточнить марку двери у поставщика.');
  });

  it('reads the history only when it is opened', () => {
    expect(markup).toContain('История решений');
    expect(markup).not.toContain('data-proposal-history');
  });
});

describe('the same section for an administrator', () => {
  const markup = rendered('proposals-loaded-admin');

  it('reads everything and decides nothing', () => {
    expect(markup).toContain('data-proposal="opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Q"');
    expect(markup).toContain('Выгрузить CSV предложений');
    expect(markup).toContain('Запустить проход может эксперт');
    expect(markup).not.toContain('Запустить проход</button>');
    expect(markup).not.toContain('data-proposal-decision=');
    expect(markup).not.toContain('Принять');
  });
});

describe('the other states', () => {
  it('says nothing yet, an empty pass and a filter that admits nothing', () => {
    expect(rendered('proposals-no-passes')).toContain('Проходов по этому комплекту ещё не было');
    const empty = rendered('proposals-empty-pass');
    expect(empty).toContain('В этом проходе нет предложений');
    expect(empty).toContain('не нашлось более дешёвой позиции');
    expect(rendered('proposals-filter-admits-nothing')).toContain('Нет предложений в выбранном состоянии');
  });

  it('says every refused read in Russian with its correlation id', () => {
    for (const [name, sentence] of [
      ['proposals-documents-refused', 'Документы объекта не прочитаны'],
      ['proposals-passes-refused', 'Проходы не прочитаны'],
      ['proposals-pass-refused', 'Предложения не прочитаны'],
      ['proposals-history-refused', 'История решений не прочитана'],
      ['proposals-export-refused', 'Файл не выгружен'],
    ] as const) {
      const markup = rendered(name);
      expect(markup, name).toContain(sentence);
    }
    expect(rendered('proposals-pass-refused')).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
  });

  it('marks the state of every proposal by its current decision', () => {
    for (const state of ['pending', 'accept', 'reject', 'revise'] as const) {
      expect(rendered(`proposal-state-${state}`)).toContain(`data-decision="${state}"`);
    }
  });

  it('pages with Назад and Далее, and disables what is not there', () => {
    const second = rendered('proposals-second-page');
    expect(second).toContain('Показано 21–21 из 22.');
    expect(second).toContain('data-proposal-paging="20-end"');
  });
});

describe('the decision form', () => {
  it('blocks «На доработку» without a comment and a repeat of the current decision', () => {
    const idle = rendered('decision-form-idle');
    expect(idle).toContain('Комментарий к решению');
    expect(idle).toContain('data-revise-hint');
    expect(idle).toMatch(/<button[^>]*disabled=""[^>]*>На доработку<\/button>/);
    const repeat = rendered('decision-form-repeat-blocked');
    expect(repeat).toMatch(/<button[^>]*disabled=""[^>]*>Принять<\/button>/);
    expect(repeat).not.toMatch(/<button[^>]*disabled=""[^>]*>Отклонить<\/button>/);
    const ready = rendered('decision-form-revise-ready');
    expect(ready).not.toMatch(/<button[^>]*disabled=""[^>]*>На доработку<\/button>/);
    expect(ready).not.toContain('data-revise-hint');
  });

  it('says a refusal in Russian', () => {
    expect(rendered('decision-form-refused')).toContain('Решение по предложению не записано.');
  });

  /** `UI-B-12`: «Снять решение» is offered while a decision is in force and not otherwise. */
  it('offers «Снять решение» only while a decision is in force', () => {
    expect(rendered('decision-form-idle')).toMatch(/<button[^>]*disabled=""[^>]*data-revoke-decision=[^>]*>Снять решение<\/button>|<button[^>]*data-revoke-decision=[^>]*disabled=""[^>]*>Снять решение<\/button>/);
    expect(rendered('decision-form-withdrawn')).toMatch(/<button[^>]*(disabled=""[^>]*data-revoke-decision|data-revoke-decision[^>]*disabled="")[^>]*>Снять решение<\/button>/);
    const standing = rendered('decision-form-repeat-blocked');
    expect(standing).toContain('data-revoke-decision=');
    expect(standing).not.toMatch(/<button[^>]*(disabled=""[^>]*data-revoke-decision|data-revoke-decision[^>]*disabled="")[^>]*>Снять решение<\/button>/);
  });

  it('lets a withdrawn proposal be decided again: no verdict is blocked as a repeat', () => {
    const withdrawn = rendered('decision-form-withdrawn');
    expect(withdrawn).not.toMatch(/<button[^>]*disabled=""[^>]*>Принять<\/button>/);
    expect(withdrawn).not.toMatch(/<button[^>]*disabled=""[^>]*>Отклонить<\/button>/);
  });

  it('says that nothing stands to be withdrawn, in words', () => {
    expect(rendered('decision-form-refused-nothing-to-revoke')).toContain('Снимать нечего');
  });
});

describe('a withdrawn decision (`UI-B-12`)', () => {
  it('is said as withdrawn, by whom and when, and the proposal is «не решено» again', () => {
    const withdrawn = decision({ verdict: 'revoke', comment: 'Ошибся, пересмотрю.' });
    const markup = renderScreen(newClient(), createElement(ProposalCard, {
      proposal: proposal({ current_verdict: 'pending', current_decision: withdrawn }), controls: null, history: null,
    }));
    expect(markup).toContain('data-decision="pending"');
    expect(markup).toContain('решение снято');
    expect(markup).toContain('Петрова А.');
    expect(markup).toContain('Ошибся, пересмотрю.');
  });

  it('keeps the withdrawal in the history as an event, after the decision it withdrew', () => {
    const markup = renderScreen(newClient(), createElement(ProposalHistoryView, {
      items: [decision({ verdict: 'accept', comment: null }), decision({ proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8W', verdict: 'revoke', comment: null })],
    }));
    expect(markup).toContain('data-proposal-history="2"');
    expect(markup.indexOf('Принять')).toBeLessThan(markup.indexOf('Снять решение'));
  });
});

describe('the retired /optimisation address', () => {
  it('points to the projects list and to the project’s tab, with no number and no promise of more', () => {
    expect(OPTIMISATION_MOVED_TO).toBe('/projects');
    const markup = renderScreen(newClient(), createElement(OptimisationPage));
    expect(markup).toContain('href="/projects"');
    expect(markup).toContain('вкладке объекта');
    expect(markup).not.toMatch(/пока недоступен|ещё не готов/);
  });
});

describe('«Открыть лист» (`UI-B-09`)', () => {
  it('opens the version’s PDF on the proposal’s page in a new tab, once the PDF is fetched', () => {
    const markup = rendered('proposals-sheet-ready');
    expect(markup).toContain(`href="${SHEET_URL}#page=2"`);
    expect(markup).toContain('target="_blank"');
    expect(markup).toContain('rel="noopener noreferrer"');
    expect(markup).toContain('data-open-sheet="2"');
    expect(markup.match(/Открыть лист ↗/g)?.length).toBe(2);
    expect(markup).not.toContain('data-proposal-sheet');
  });

  it('offers nothing where no PDF is given, as before', () => {
    expect(rendered('proposals-loaded-admin')).not.toContain('data-open-sheet');
    expect(rendered('proposals-second-page')).not.toContain('Открыть лист');
  });

  it('says the PDF is on its way, and draws no link meanwhile', () => {
    const markup = rendered('proposals-sheet-loading');
    expect(markup).toContain('data-proposal-sheet="loading"');
    expect(markup).toContain('Загружается PDF версии');
    expect(markup).not.toContain('data-open-sheet');
  });

  it('says a refused PDF in Russian with its correlation id, and draws no link', () => {
    const markup = rendered('proposals-sheet-refused');
    expect(markup).toContain('PDF версии не получен: ссылок «Открыть лист» нет');
    expect(markup).toContain('PDF версии недоступен.');
    expect(markup).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
    expect(markup).not.toContain('data-open-sheet');
  });

  it('draws no link for a proposal that names no page a reader can open', () => {
    const named = renderScreen(newClient(), createElement(ProposalCard, {
      proposal: proposal(), controls: null, history: null, documentUrl: SHEET_URL,
    }));
    expect(named).toContain('data-open-sheet="2"');
    for (const page of [0, -1, 1.5]) {
      const markup = renderScreen(newClient(), createElement(ProposalCard, {
        proposal: proposal({ page_number: page }), controls: null, history: null, documentUrl: SHEET_URL,
      }));
      expect(markup, `page ${page}`).not.toContain('data-open-sheet');
    }
  });
});

/**
 * `UIP-S09-02`: the top row over the table. At the left the plates of the decisions with the pass's counts and «Всего: N»; at the
 * right «Файлы ▾» (the shared menu), «Загрузить решения» and «Перенести решения из V#», which are the features' own controls drawn
 * where they were drawn before but in one row. No paragraph of buttons and no caption stands over it, and what a file or a load
 * refuses stands under it in the words it always had.
 */
describe('the top row of the tab (`UIP-S09-02`)', () => {
  const noop = (): void => undefined;
  const loaded = rendered('proposals-loaded');
  const CORRELATION = '0f0e9d8c-7b6a-4948-b726-150413021100';

  /** The text of each button of the plates, without the separators the server render may put between text nodes. */
  const plates = (markup: string): string[] => {
    const nav = /<nav[^>]*data-decision-filter="[^"]*"[^>]*>([\s\S]*?)<\/nav>/.exec(markup)?.[1] ?? '';
    return [...nav.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g)].map((button) => (button[1] ?? '').replace(/<!-- -->/g, ''));
  };

  const earlier = [
    pass({ version_ordinal: 2 }),
    pass({ optimisation_pass_id: OLDER_PASS_ID, version_ordinal: 1, decision_counts: { pending: 2, accept: 3, reject: 1, revise: 2 } }),
  ];
  const carryOver = (failure: string | null = null) =>
    createElement(CarryOverProposalDecisionsView, {
      sources: carrySources(earlier, earlier[0] as never),
      confirming: null, pending: false, report: null, failure, onAsk: noop, onConfirm: noop, onCancel: noop,
    });
  const imported = (failure: string | null = null, report: Parameters<typeof ImportProposalDecisionsView>[0]['report'] = null) =>
    createElement(ImportProposalDecisionsView, { pending: false, report, failure, onChoose: noop });
  const row = (props: Record<string, unknown> = {}) =>
    renderScreen(newClient(), createElement(ExportProposalsView, { pending: false, failure: null, onDownload: noop, ...props }));

  it('shows the plates of the decisions with the pass’s counts, then «Всего: N», at the left of the row', () => {
    // The seed's pass holds two proposals: one waiting, one for revision.
    expect(plates(loaded)).toEqual(['Все (2)', 'не решено (1)', 'принято (0)', 'отклонено (0)', 'на доработку (1)']);
    expect(loaded).toMatch(/data-proposal-total="2"[^>]*>Всего: (<!-- -->)?2</);
    const at = (marker: string) => loaded.indexOf(marker);
    expect(at('data-decision-filter')).toBeGreaterThan(-1);
    expect(at('data-proposal-total')).toBeGreaterThan(at('data-decision-filter'));
    expect(at('data-proposal-layout=')).toBeGreaterThan(at('data-proposal-total'));
    expect(at('data-proposals-export')).toBeGreaterThan(at('data-proposal-layout='));
    expect(at('data-proposal-table')).toBeGreaterThan(at('data-proposals-export'));
  });

  it('counts the pass, not the filtered page: the plates and «Всего» are the pass’s under a filter', () => {
    const filtered = renderScreen(
      newClient(),
      createElement(ProposalListView, {
        page: proposalPage({ decision: 'accept', items: [], total: 0 }),
        canDecide: true,
        onDecision: noop,
        onPage: noop,
      }),
    );
    expect(filtered).toMatch(/data-proposal-total="2"/);
    expect(plates(filtered)).toEqual(['Все (2)', 'не решено (1)', 'принято (0)', 'отклонено (0)', 'на доработку (1)']);
    expect(filtered).toMatch(/data-decision-filter="accept"/);
  });

  it('offers «Файлы ▾» as the shared menu, and each file as an item of it, to an expert and to an administrator', () => {
    for (const markup of [loaded, rendered('proposals-loaded-admin')]) {
      expect(markup).toMatch(/<button[^>]*aria-haspopup="menu"[^>]*aria-label="Файлы"[^>]*>Файлы <span aria-hidden="true">▾<\/span><\/button>/);
      expect(markup).toContain(`role="menuitem" tabindex="-1">${EXPORT_CSV_LABEL}</button>`);
      expect(markup).toContain(`role="menuitem" tabindex="-1">${EXPORT_XLSX_LABEL}</button>`);
    }
  });

  it('draws no paragraph of buttons and no file or load over the plates', () => {
    expect(loaded).not.toMatch(/<p[^>]*>\s*<button[^>]*>Выгрузить/);
    const before = loaded.slice(0, loaded.indexOf('data-decision-filter'));
    expect(before).not.toContain('Выгрузить');
    expect(before).not.toContain('Загрузить решения');
  });

  it('stands the load and the carrying over after the files, in the one block of the row, for an expert', () => {
    const markup = row({ onDownloadXlsx: noop, importControl: imported(), carryOverControl: carryOver() });
    const at = (marker: string) => markup.indexOf(marker);
    expect(at('data-proposals-files')).toBeGreaterThan(-1);
    expect(at('data-proposal-decision-import')).toBeGreaterThan(at('data-proposals-files'));
    expect(at('data-proposal-decision-carryover')).toBeGreaterThan(at('data-proposal-decision-import'));
    expect(markup).toContain('Загрузить решения');
    expect(markup).toContain('Перенести решения из V1');
    const block = /<div class="[^"]*tools[^"]*" data-proposals-export="">([\s\S]*)<\/div>$/.exec(markup);
    expect(block?.[1], 'the row is one block').toContain('data-proposal-decision-carryover');
  });

  it('offers a reader who does not decide the files and no load', () => {
    const admin = rendered('proposals-loaded-admin');
    expect(admin).toContain(EXPORT_CSV_LABEL);
    expect(admin).not.toContain('Загрузить решения');
    expect(admin).not.toContain('Перенести решения');
  });

  it('says a refused file under the row, in the words it always had, with the server’s reason and its correlation id', () => {
    const markup = row({ failure: { detail: 'Файл не удалось выгрузить.', correlationId: CORRELATION } });
    expect(markup.indexOf('Файл не выгружен')).toBeGreaterThan(markup.indexOf('data-proposals-files'));
    expect(markup).toContain('Файл не удалось выгрузить.');
    expect(markup).toContain(CORRELATION);
    expect(markup).toContain('data-proposals-export-refusal');
    expect(row()).not.toContain('Файл не выгружен');
  });

  it('says every refused row of a load, each in its own words, inside the row’s block after the button', () => {
    const reasons = Object.keys(PROPOSAL_IMPORT_REFUSAL_LABELS) as ProposalDecisionImportRefusal[];
    const rows = reasons.map((reason, index) => ({ row: index + 2, outcome: 'refused' as const, reason }));
    const markup = row({
      importControl: imported(null, {
        optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N', recorded: 0, unchanged: 0, refused: rows.length, rows,
      }),
    });
    const upload = markup.slice(markup.indexOf('data-proposal-decision-import'));
    for (const [index, reason] of reasons.entries()) {
      const sentence = `Строка ${index + 2}: ${PROPOSAL_IMPORT_REFUSAL_LABELS[reason]}`;
      expect(upload, reason).toContain(sentence);
      expect(upload.indexOf(sentence), reason).toBeGreaterThan(upload.indexOf('Загрузить решения'));
    }
    expect(upload).toContain(`отклонено ${rows.length}`);
  });

  it('says each refusal of a whole file, and each refusal of the carrying over, in a line of the row', () => {
    const refuse = (constraint: string) =>
      new ApiError(422, {
        contract_version: '1.57.0', error_code: 'validation_failed', message: 'x',
        correlation_id: 'cid-1', retryable: false, details: { field: 'file', constraint },
      }, 'cid-1');
    for (const constraint of ['not_our_export', 'unreadable', 'too_large', 'too_many_rows']) {
      const sentence = importProposalFailure(refuse(constraint));
      const markup = row({ importControl: imported(sentence) });
      expect(markup, constraint).toContain(`role="alert">${sentence}</p>`);
    }
    for (const [reason, sentence] of Object.entries(CARRYOVER_REFUSAL_TEXT)) {
      expect(row({ carryOverControl: carryOver(sentence) }), reason).toContain(`role="alert">${sentence}</p>`);
    }
  });

  it('hands the press on a file to its handler, and ignores it while a file is being made, saying so', async () => {
    const csv = vi.fn();
    const xlsx = vi.fn();
    const live = await mountLive(createElement(ExportProposalsView, { pending: false, failure: null, onDownload: csv, onDownloadXlsx: xlsx }));
    expect(await live.press(EXPORT_CSV_LABEL)).toBe(true);
    expect(await live.press(EXPORT_XLSX_LABEL)).toBe(true);
    expect([csv.mock.calls.length, xlsx.mock.calls.length]).toEqual([1, 1]);
    expect(live.markup()).not.toContain('data-proposals-export-state');
    await live.update(createElement(ExportProposalsView, { pending: true, failure: null, onDownload: csv, onDownloadXlsx: xlsx }));
    await live.press(EXPORT_CSV_LABEL);
    await live.press(EXPORT_XLSX_LABEL);
    expect([csv.mock.calls.length, xlsx.mock.calls.length]).toEqual([1, 1]);
    expect(live.markup()).toContain('data-proposals-export-state="pending"');
    expect(live.markup()).toContain('Готовлю файл…');
    await live.unmount();
  });

  it('offers the workbook only where it is given', () => {
    const plain = row();
    expect(plain).toContain(EXPORT_CSV_LABEL);
    expect(plain).not.toContain(EXPORT_XLSX_LABEL);
  });
});
