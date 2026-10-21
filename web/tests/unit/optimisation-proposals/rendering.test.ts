/**
 * «Предложения» rendered (`W60-OPT-PROPOSALS-01`): the set chooser, the passes with their
 * counts by decision, the proposals with their provenance, both exact prices and the saving
 * only where it is stated, the controls each role is given, and every refusal in Russian.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { OPTIMISATION_MOVED_TO, OptimisationPage } from '@/_pages/optimisation';
import { arDocumentSets } from '@/widgets/optimisation-proposals';

import { newClient, renderScreen } from '../screens/harness';
import { arVersion, otherSectionVersion, proposalShapes } from './fixtures';

/** A set no expert has classified: the `classification` key is absent, not `undefined`. */
function unclassified() {
  const version: Record<string, unknown> = { ...arVersion() };
  delete version['classification'];
  return version as unknown as ReturnType<typeof arVersion>;
}

function rendered(name: string): string {
  const shape = proposalShapes().find((entry) => entry.name === name);
  if (shape === undefined) throw new Error(`no shape ${name}`);
  const client = newClient();
  shape.seedClient?.(client);
  return renderScreen(client, shape.make());
}

describe('the sets', () => {
  it('offers only the sets whose current version an expert confirmed as АР', () => {
    expect(arDocumentSets([arVersion(), otherSectionVersion(), unclassified()])).toEqual([
      arVersion(),
    ]);
  });

  it('says where a section is confirmed when there is none, and that the list is partial', () => {
    const markup = rendered('proposals-no-ar-sets');
    expect(markup).toContain('В проекте нет комплектов раздела АР');
    expect(markup).toContain('Подтвердите раздел на экране версии');
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
