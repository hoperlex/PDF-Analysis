/**
 * What the viewer shows (`CMP-VIEWER-01`, plan §1.1), rendered as the contrast census and the language guards render it:
 * the Russian names of the layers, «Отличия: N», the channel strip, the text changes with their numbers marked, the
 * service zones and their warning, «Как сравнивалось», the notes, the controls that are off, and the image tags.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ComparisonSheetPair } from '@/shared/api';
import { ComparisonViewerView, canShowOverlay, viewerGeometry } from '@/widgets/comparison-viewer';
import type { TileStatus, ViewerAction, ViewerContext, ViewerState } from '@/widgets/comparison-viewer';
import { initialState, reduce } from '@/widgets/comparison-viewer/model/viewer-state';

import { A1, addedPair, comparedPair } from './viewer-fixtures';

function contextOf(pair: ComparisonSheetPair): ViewerContext {
  const geometry = viewerGeometry(pair);
  return {
    raster: geometry?.raster ?? { widthPx: 1, heightPx: 1 }, dpi: geometry?.dpi ?? 72, differences: pair.differences ?? [],
    canOverlay: canShowOverlay(pair), hasA: pair.page_a !== undefined, hasB: pair.page_b !== undefined,
  };
}

const arrived: TileStatus = {
  urlOf: (request) => `blob:${request.mode}-${request.level}-${request.column}-${request.row}`, failed: 0, pending: 0, retry: () => {},
};

/** The pair without some of its members (an absent member is absent, not `undefined`). */
function without(pair: ComparisonSheetPair, ...keys: (keyof ComparisonSheetPair)[]): ComparisonSheetPair {
  const copy = { ...pair };
  for (const key of keys) delete copy[key];
  return copy;
}

/** The words a reader reads: the markup with every tag removed. */
function text(markup: string): string {
  return markup.replace(/<[^>]*>/g, '|');
}

function html(pair: ComparisonSheetPair, steps: ViewerAction[] = [], tiles: TileStatus = arrived, extra: object = {}): string {
  const context = contextOf(pair);
  let state: ViewerState = initialState(context, { width: 1000, height: 600 });
  for (const step of steps) state = reduce(state, step, context);
  return renderToStaticMarkup(
    createElement(ComparisonViewerView, { pair, geometry: viewerGeometry(pair), context, state, tiles, dispatch: () => {}, ...extra }),
  );
}

describe('the viewer of a compared pair', () => {
  it('names the sheets and the status in Russian', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Лист A: л. 5 · План освещения. Корпус 1, этаж 1');
    expect(markup).toContain('Лист B: л. 5 · План освещения. Корпус 1, этаж 1');
    expect(markup).toContain('Есть отличия');
    expect(html(comparedPair({ status: 'same_zones_changed' }))).toContain('Совпадает, изменены служебные зоны');
  });

  it('has the two modes, the swipe, the zoom and «Вписать»', () => {
    const markup = html(comparedPair());
    for (const word of ['Наложение', 'Рядом', 'шторка', 'Вписать', 'Уменьшить', 'Увеличить']) expect(markup).toContain(word);
    expect(markup).toContain('aria-pressed="true"');
    expect(markup).toMatch(/>\d+ %</);
  });

  it('lists the eight layers by their Russian names, five of them on', () => {
    const markup = html(comparedPair());
    for (const name of ['Основное', 'Светлые элементы', 'Места, где изменился цвет', 'Оформление линий',
      'Перемещено (сдвиг — не изменение)', 'В пределах допуска', 'Шум', 'Служебные зоны']) expect(markup).toContain(name);
    expect((markup.match(/<input type="checkbox" checked=""/g) ?? []).length).toBeGreaterThanOrEqual(5);
    for (const identifier of ['light_elements', 'color_change', 'line_style', 'within_tolerance', 'service_zones']) {
      expect(text(markup)).not.toContain(identifier);
    }
  });

  it('draws the layers only in the overlay and not in «Рядом»', () => {
    const side = html(comparedPair(), [{ type: 'mode', mode: 'side' }]);
    expect(side).not.toContain('Основное');
    expect(side).toContain('Лист A');
    expect(side).toContain('data-pane="Лист B"');
    expect(side).toContain('title="Шторка работает только в наложении"');
  });

  it('shows «Отличия: N» without the shifts and the look of lines, and offers them with their counts', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Отличия: 4');
    expect(markup).toContain('сдвиги (не изменение): 1 — показать в списке');
    expect(markup).toContain('оформление линий: 1 — показать в списке');
    expect(markup).toContain('Текст');
    expect(markup).toContain('Щит ЩО-1');
    expect(markup).toContain('Графика: добавлено (B)');
    expect(markup).toContain('Изменение цвета');
    expect(markup).not.toContain('Сдвиг надписи');
    expect(html(comparedPair(), [{ type: 'shifts', on: true }, { type: 'style-only', on: true }])).toContain('Отличия: 6');
    expect(html(comparedPair(), [{ type: 'shifts', on: true }])).toContain('Сдвиг надписи');
  });

  it('says so about a class it does not know, and keeps the class out of the visible text', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Другое отличие');
    expect(markup).toContain('data-region-class="something_new"');
    expect(text(markup)).not.toContain('something_new');
  });

  it('marks the selected difference and shows its box even with the boxes off', () => {
    const none = html(comparedPair());
    expect(none).not.toContain('data-difference="1"');
    const one = html(comparedPair(), [{ type: 'select', index: 1 }]);
    expect(one).toContain('aria-current="true"');
    expect(one).toMatch(/data-difference="1"/);
    expect((one.match(/class="[^"]*box[^"]*"/g) ?? []).length).toBe(1);
    const all = html(comparedPair(), [{ type: 'boxes', on: true }]);
    expect((all.match(/data-difference="/g) ?? []).length).toBe(4); // the shown ones
  });

  it('has the channel strip: what was checked with its counts, what was not with why, and the reasons', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Проверено:');
    expect(markup).toContain('графика (4), цвет и оформление линий (1), текст (2), служебные зоны (1), предупреждения (1)');
    expect(markup).toContain('Не проверено:');
    expect(markup).toContain('читаемость надписей — нет текстового слоя: надписи сравнены только графически');
    expect(markup).toContain('причины: нет текстового слоя');
    expect(html(comparedPair({ reasons: ['NEW_REASON'] }))).toContain('причина без описания (NEW_REASON)');
    expect(html({ ...without(comparedPair(), 'channels'), reasons: [] })).toContain('Каналы сравнения неизвестны');
  });

  it('shows «было → стало» with the numbers that changed marked', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Текст: 2 изменения');
    expect(markup).toContain('<mark class="');
    expect(markup).toMatch(/<mark[^>]*>120<\/mark>/);
    expect(markup).toMatch(/<mark[^>]*>150<\/mark>/);
    expect(markup).toMatch(/<mark[^>]*>2,5<\/mark>/);
    expect(markup).toContain('Установить датчик движения');
    expect(html(comparedPair({ text_changes: [] }))).toContain('Текст: 0 изменений');
  });

  it('lists the service zones and says that a vanished warning confirms no approval', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Служебные зоны и пометки: 2');
    expect(markup).toContain('Предупреждение удалено, зона «stamp»');
    expect(markup).toContain('Штамп изменён, зона «stamp», поле «revision»');
    expect(markup).toContain('Исчезновение предупреждения не подтверждает согласования.');
    expect(html(comparedPair({ service_notes: [{ kind: 'stamp', change: 'added' }] }))).not.toContain('Исчезновение предупреждения');
  });

  it('says how the sheets were compared', () => {
    const markup = html(comparedPair());
    expect(markup).toContain('Как сравнивалось');
    for (const text of ['vc1.13', '200 точек на дюйм', '0.5 пт', '1, 0, 0, 1, -3.7, 2.1', 'В пределах допуска', 'Шум', 'Отделённых объектов', 'Совмещённых блоков']) {
      expect(markup).toContain(text);
    }
  });

  it('turns «Совмещать блоки» off when there is nothing to align, and on when there is', () => {
    expect(html(comparedPair())).toMatch(/<input type="checkbox" disabled=""[^>]*\/>Совмещать блоки|Совмещать блоки/);
    const none = html(comparedPair({ how_compared: { algo_version: 'v', dpi: 200, tolerance_pt: 0.5, transform: [1, 0, 0, 1, 0, 0], aligned_blocks: 0 } }));
    expect(none).toContain('title="Движения блоков не найдено: совмещать нечего"');
    expect(html(comparedPair())).toContain('title="Показать перемещённые блоки листа B на их местах, не меняя PDF"');
  });

  it('puts the swipe divider and the slider in when the swipe is on, the lower sheet under the overlay', () => {
    const markup = html(comparedPair(), [{ type: 'swipe', on: true }, { type: 'swipe-position', position: 30 }]);
    expect(markup).toContain('Положение шторки');
    expect(markup).toContain('type="range"');
    // the overlay is hidden left of the divider, which opens the lower sheet there (`version-comparison-viewer.js:120`)
    expect(markup).toContain('clip-path:inset(0 0 0 30%)');
    expect(markup).toContain('left:30%');
    expect(markup).toContain('Шторка: слева лист A, справа наложение');
    expect(markup.indexOf('data-sheet="a"')).toBeLessThan(markup.indexOf('data-sheet="overlay"'));
    expect(html(comparedPair(), [{ type: 'swipe', on: true }, { type: 'under', under: 'b' }])).toContain('data-sheet="b"');
    expect(html(comparedPair())).not.toContain('type="range"');
  });

  it('draws the tiles that have arrived and none that have not', () => {
    const none = html(comparedPair(), [], { ...arrived, urlOf: () => null });
    expect(none).not.toContain('<img');
    const some = html(comparedPair());
    expect((some.match(/<img /g) ?? []).length).toBeGreaterThan(1);
    expect(some).toContain('src="blob:overlay-4-0-0"');
  });

  it('says what is loading and what failed, and offers to try again', () => {
    expect(html(comparedPair(), [], { ...arrived, pending: 3 })).toContain('Загружается плиток: 3');
    const failed = html(comparedPair(), [], { ...arrived, failed: 2 });
    expect(failed).toContain('Не загружено плиток: 2.');
    expect(failed).toContain('Повторить');
    expect(failed).toContain('role="alert"');
  });

  it('marks a scanned page, a part of a sheet and an AI-made pair', () => {
    const scanned = html(comparedPair({ page_a: { ...(comparedPair().page_a as object), scan: true } as NonNullable<ComparisonSheetPair['page_a']> }));
    expect(scanned).toContain('изображение без текста: надписи не читаются и сравниваются только как картинка');
    const part = html(comparedPair({ parts: { role: 'part', covered_percent: 72.4, parts: [] } }));
    expect(part).toContain('Лист B — часть листа A; листы-части покрывают 72 % листа A');
    expect(html(comparedPair({ ai_dependent: true }))).toContain('пара связана с участием ИИ');
  });

  it('shows the neighbouring-sheet controls only when the page passes them', () => {
    expect(html(comparedPair())).not.toContain('‹ лист');
    const markup = html(comparedPair(), [], arrived, { navigation: { onNext: () => {}, onClose: () => {} } });
    expect(markup).toContain('‹ лист');
    expect(markup).toContain('лист ›');
    expect(markup).toContain('✕ Закрыть');
  });
});

describe('the viewer of a pair that cannot be laid over', () => {
  it('draws only the page that exists, with no overlay, when the pair was never compared', () => {
    const pair = addedPair();
    const geometry = { raster: A1, dpi: 200, levels: [] };
    expect(geometry.raster).toBe(A1);
    const markup = html(pair, [], arrived);
    expect(markup).toContain('Лист нельзя показать');
    expect(markup).toContain('Лист A: нет в этой версии');
    expect(markup).toContain('Лист добавлен');
  });

  it('draws the page it has when its own size is passed, without the overlay', () => {
    const pair = addedPair();
    const raster = { widthPx: 6623, heightPx: 4678 };
    const geometry = viewerGeometry(pair, raster);
    const context: ViewerContext = { raster, dpi: 72, differences: [], canOverlay: false, hasA: false, hasB: true };
    const state = initialState(context, { width: 1000, height: 600 });
    const markup = renderToStaticMarkup(createElement(ComparisonViewerView, { pair, geometry, context, state, tiles: arrived, dispatch: () => {} }));
    expect(state.mode).toBe('side');
    expect(markup).toContain('data-pane="Лист B"');
    expect(markup).not.toContain('data-pane="Лист A"');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Наложение<\/button>/);
    expect(markup).toContain('title="Наложения нет: листы не были совмещены"');
  });

  it('says why a pair that failed cannot be shown', () => {
    expect(html({ ...without(comparedPair(), 'canvas', 'how_compared'), state: 'failed', failure_reason: 'RENDER_FAILED' })).toContain('Сравнение листа не удалось: RENDER_FAILED.');
  });
});
