/**
 * «Предложения» rendered (`W60-OPT-PROPOSALS-01`): the set chooser, the passes with their
 * counts by decision, the proposals with their provenance, both exact prices and the saving
 * only where it is stated, the controls each role is given, and every refusal in Russian.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { OPTIMISATION_MOVED_TO, OptimisationPage } from '@/_pages/optimisation';
import { ProposalCard, ProposalHistoryView, classifiedDocumentSets } from '@/widgets/optimisation-proposals';

import { newClient, renderScreen } from '../screens/harness';
import { arVersion, decision, otherSectionVersion, proposal, proposalShapes, SHEET_URL, unclassifiedVersion } from './fixtures';

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
    expect(markup).toContain('В проекте нет комплектов с подтверждённым разделом');
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
      ['proposals-documents-refused', 'Документы проекта не прочитаны'],
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
    expect(markup).toContain('вкладке проекта');
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
