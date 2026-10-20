/**
 * The «Оптимизация» tab rendered (`W60-PRICE-LIST-01`): the project screen's two tabs, the
 * revisions with the current one marked, positions with exact prices and the report of how the
 * file was read, the vendor lists' sources and the controls each role is given.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ProjectDetailPage } from '@/_pages/project-detail';
import { draftProblem, entriesOf } from '@/features/set-vendor-list';
import { PRICE_LIST_MAX_BYTES, precheckPriceListFile } from '@/features/upload-price-list';
import { VendorListsView } from '@/widgets/project-optimisation';

import { newClient, renderScreen } from '../screens/harness';
import { OPT_PROJECT_UID, optimisationShapes, seedLoadedOptimisation, vendorLists } from './fixtures';

function rendered(name: string): string {
  const shape = optimisationShapes().find((entry) => entry.name === name);
  if (shape === undefined) throw new Error(`no shape ${name}`);
  const client = newClient();
  shape.seedClient?.(client);
  return renderScreen(client, shape.make());
}

const noop = (): void => undefined;

describe('the project screen', () => {
  it('opens on «Документы» and offers «Оптимизация» without reading it', () => {
    const client = newClient();
    seedLoadedOptimisation(client);
    const markup = renderScreen(client, createElement(ProjectDetailPage, { projectUid: OPT_PROJECT_UID, roles: ['expert'] }));
    expect(markup).toContain('data-project-tabs="documents"');
    expect(markup).toContain('Оптимизация');
    expect(markup).not.toContain('data-project-optimisation');
  });
});

describe('the price lists', () => {
  const markup = rendered('optimisation-loaded');

  it('lists every revision and marks the current one', () => {
    expect(markup).toContain('data-price-list="prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8C"');
    expect(markup).toContain('2 (текущая)');
    expect(markup).toContain('прайс-2025.xlsx · книга Excel');
    expect(markup).toContain('Показать позиции');
  });

  it('shows each price exactly, in the currency the price list stated', () => {
    expect(markup).toContain('125,5 руб.');
    expect(markup).toContain('12 345,67 евро');
    expect(markup).toContain('ЭОМ');
  });

  it('reports how the file was read, every skipped row with its reason', () => {
    expect(markup).toContain('кириллическая кодировка 1251');
    expect(markup).toContain('data-skipped-row="4"');
    expect(markup).toContain('строка 4: цена записана не числом');
    expect(markup).toContain('строка 5: раздел не распознан');
    expect(markup).toContain('марка: «Марка», «Тип»');
    expect(markup).toContain('Перечислены первые 1000 пропущенных строк');
  });

  it('gives the upload to an expert and says who uploads to anyone else', () => {
    expect(markup).toContain('Загрузить прайс-лист');
    expect(rendered('optimisation-empty')).toContain('Прайс-лист загружает эксперт.');
    expect(rendered('optimisation-empty')).toContain('Прайс-лист ещё не загружен.');
  });

  it('says a refused read in Russian with its correlation id', () => {
    const refused = rendered('optimisation-refused');
    expect(refused).toContain('Редакции прайс-листа не удалось прочитать.');
    expect(refused).toContain('Вендор-листы не удалось прочитать.');
    expect(refused).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
  });
});

describe('the vendor lists', () => {
  it('say which list applies to each section', () => {
    const markup = rendered('optimisation-loaded');
    expect(markup).toContain('data-vendor-section="EOM" data-vendor-source="project"');
    expect(markup).toContain('Световые технологии');
    expect(markup).toContain('Общий список:');
    expect(markup).toContain('data-vendor-section="OV" data-vendor-source="global"');
    expect(markup).toContain('без ограничений');
    expect(markup).toContain('data-vendor-section="AR" data-vendor-source="none"');
  });

  it('give an expert the project list and an administrator the general one', () => {
    const view = (canEditProject: boolean, canEditGlobal: boolean) =>
      renderScreen(newClient(), createElement(VendorListsView, {
        items: vendorLists().items, canEditProject, canEditGlobal, editing: null, pending: false,
        failure: null, onEdit: noop, onInherit: noop, onSave: noop, onCancel: noop,
      }));
    const expert = view(true, false);
    expect(expert).toContain('Изменить список проекта');
    expect(expert).toContain('Вернуться к общему списку');
    expect(expert).not.toContain('Изменить общий список');
    const admin = view(false, true);
    expect(admin).toContain('Изменить общий список');
    expect(admin).not.toContain('Изменить список проекта');
  });

  it('edits rows, and refuses a row with no vendor', () => {
    expect(rendered('vendor-lists-editing-project')).toContain('Список проекта для раздела');
    expect(rendered('vendor-lists-editing-global-empty')).toContain('«без ограничений»');
    expect(draftProblem([{ material: 'Кабель', vendor: ' ', note: '' }])).toBe('В каждой записи нужен поставщик.');
    expect(entriesOf([{ material: ' ', vendor: ' Завод ', note: '' }])).toEqual([
      { material: null, vendor: 'Завод', note: null },
    ]);
  });
});

describe('the upload pre-check', () => {
  it('refuses an empty file and one over 10 MiB before sending', () => {
    expect(precheckPriceListFile(new File([], 'пусто.csv'))).toBe('Файл пуст.');
    const big = { size: PRICE_LIST_MAX_BYTES + 1 } as File;
    expect(precheckPriceListFile(big)).toMatch(/больше 10 MiB/);
    expect(precheckPriceListFile(new File(['а'], 'прайс.csv'))).toBeNull();
  });
});
