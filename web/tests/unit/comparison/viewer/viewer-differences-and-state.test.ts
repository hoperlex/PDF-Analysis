/**
 * The list «Отличия: N» and the reducer behind the controls (`CMP-VIEWER-01`).
 */

import { describe, expect, it } from 'vitest';

import type { ComparisonDifference } from '@/shared/api';
import { countDifferences, differenceAt, shownIndices, stepDifference } from '@/widgets/comparison-viewer/model/differences';
import { DEFAULT_LAYERS, LAYER_ORDER } from '@/widgets/comparison-viewer/model/labels';
import { type ViewerContext, initialState, layersQuery, reduce } from '@/widgets/comparison-viewer/model/viewer-state';
import { fitView } from '@/widgets/comparison-viewer/model/pyramid';
import { markNumbers } from '@/widgets/comparison-viewer/model/text-marks';

import { A1, comparedPair } from './viewer-fixtures';

const differences = comparedPair().differences as ComparisonDifference[];
const context: ViewerContext = { raster: A1, dpi: 200, differences, canOverlay: true, hasA: true, hasB: true };
const none = { showShifts: false, showStyleOnly: false };

describe('«Отличия: N»', () => {
  it('hides the shifts and the look of lines until asked, and counts them', () => {
    expect(shownIndices(differences, none)).toEqual([0, 1, 2, 5]);
    expect(countDifferences(differences, none)).toEqual({ shown: 4, shifts: 1, styleOnly: 1 });
    expect(shownIndices(differences, { showShifts: true, showStyleOnly: false })).toEqual([0, 1, 2, 3, 5]);
    expect(shownIndices(differences, { showShifts: true, showStyleOnly: true })).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it('walks the shown ones with the arrows and wraps round', () => {
    expect(stepDifference(differences, none, null, 1)).toBe(0);
    expect(stepDifference(differences, none, null, -1)).toBe(5);
    expect(stepDifference(differences, none, 0, 1)).toBe(1);
    expect(stepDifference(differences, none, 5, 1)).toBe(0);
    expect(stepDifference(differences, none, 0, -1)).toBe(5);
    expect(stepDifference(differences, none, 3, 1)).toBe(0); // 3 is a hidden shift: the walk starts over
    expect(stepDifference([], none, null, 1)).toBeNull();
  });
});

describe('a click on the sheet', () => {
  it('picks the shown difference under the point, the smallest box where several lie', () => {
    const scale = 200 / 72;
    expect(differenceAt(differences, none, 200, { x: 140 * scale, y: 125 * scale })).toBe(0); // inside the text box (100, 120, 80 x 12)
    expect(differenceAt(differences, none, 200, { x: 415 * scale, y: 515 * scale })).toBe(1);
    expect(differenceAt(differences, none, 200, { x: 5 * scale, y: 5 * scale })).toBeNull();
    // a shift is not under the pointer until the list shows it
    const shift = { x: 320 * scale, y: 305 * scale };
    expect(differenceAt(differences, none, 200, shift)).toBeNull();
    expect(differenceAt(differences, { showShifts: true, showStyleOnly: false }, 200, shift)).toBe(3);
    const nested: ComparisonDifference[] = [
      { region_class: 'graphic_changed', layer: 'main', box: { x: 0, y: 0, width: 100, height: 100 } },
      { region_class: 'text', layer: 'main', box: { x: 10, y: 10, width: 5, height: 5 } },
    ];
    expect(differenceAt(nested, none, 72, { x: 12, y: 12 })).toBe(1);
    expect(differenceAt(nested, none, 72, { x: 50, y: 50 })).toBe(0);
  });

  it('selects it without moving the sheet', () => {
    const start = initialState(context, { width: 1000, height: 600 });
    const picked = reduce(start, { type: 'pick', point: { x: 415 * (200 / 72), y: 515 * (200 / 72) } }, context);
    expect(picked.selected).toBe(1);
    expect(picked.view).toEqual(start.view);
    expect(reduce(picked, { type: 'pick', point: { x: 1, y: 1 } }, context).selected).toBeNull();
  });
});

describe('the reducer', () => {
  const start = initialState(context, { width: 1000, height: 600 });

  it('opens as the original does: the overlay, five layers on, boxes off, nothing selected', () => {
    expect(start.mode).toBe('overlay');
    expect(start.layers).toEqual(LAYER_ORDER.filter((layer) => DEFAULT_LAYERS.includes(layer)));
    expect(start.layers).toEqual(['main', 'light_elements', 'color_change', 'line_style', 'service_zones']);
    expect([start.showBoxes, start.alignBlocks, start.swipe, start.selected, start.swipePosition]).toEqual([false, false, false, null, 0]);
    expect(start.view).toEqual(fitView(A1, { width: 1000, height: 600 }));
  });

  it('turns a second click on the chosen mode into a return to the previous one', () => {
    const side = reduce(start, { type: 'mode', mode: 'side' }, context);
    expect([side.mode, side.previousMode]).toEqual(['side', 'overlay']);
    const back = reduce(side, { type: 'mode', mode: 'side' }, context);
    expect(back.mode).toBe('overlay');
  });

  it('has no swipe in «Рядом» and drops it on the way in', () => {
    const swiped = reduce(start, { type: 'swipe', on: true }, context);
    expect(swiped.swipe).toBe(true);
    const side = reduce(swiped, { type: 'mode', mode: 'side' }, context);
    expect(side.swipe).toBe(false);
    expect(reduce(side, { type: 'swipe', on: true }, context).swipe).toBe(false);
  });

  it('fits the sheet to the half pane when the panes are two', () => {
    const side = reduce(start, { type: 'mode', mode: 'side' }, context);
    expect(side.view).toEqual(fitView(A1, { width: 500, height: 600 }));
    const lone = reduce(start, { type: 'mode', mode: 'side' }, { ...context, hasB: false });
    expect(lone.view).toEqual(fitView(A1, { width: 1000, height: 600 }));
  });

  it('keeps the layers in the order of the contract however they are switched', () => {
    let state = reduce(start, { type: 'layer', layer: 'noise', on: true }, context);
    state = reduce(state, { type: 'layer', layer: 'main', on: false }, context);
    state = reduce(state, { type: 'layer', layer: 'moved', on: true }, context);
    expect(state.layers).toEqual(['light_elements', 'color_change', 'line_style', 'moved', 'noise', 'service_zones']);
    expect(layersQuery(state.layers)).toBe('light_elements,color_change,line_style,moved,noise,service_zones');
    expect(layersQuery([])).toBeUndefined();
    expect(reduce(state, { type: 'layer', layer: 'noise', on: true }, context).layers).toEqual(state.layers);
  });

  it('shows a selected difference on the sheet', () => {
    const selected = reduce(start, { type: 'select', index: 2 }, context);
    expect(selected.selected).toBe(2);
    expect(selected.view.zoom).toBeGreaterThan(start.view.zoom);
    // the box of difference 2 (900, 700, 60 x 20 points at 200 dpi) is at the centre of the window
    const centreX = ((900 + 30) * 200) / 72;
    const centreY = ((700 + 10) * 200) / 72;
    expect(selected.view.offsetX + centreX * selected.view.zoom).toBeCloseTo(500, 6);
    expect(selected.view.offsetY + centreY * selected.view.zoom).toBeCloseTo(300, 6);
    expect(reduce(selected, { type: 'select', index: null }, context).selected).toBeNull();
    expect(reduce(start, { type: 'select', index: 99 }, context).selected).toBeNull();
  });

  it('steps through the differences that are shown', () => {
    let state = reduce(start, { type: 'step', direction: 1 }, context);
    expect(state.selected).toBe(0);
    state = reduce(state, { type: 'step', direction: 1 }, context);
    state = reduce(state, { type: 'step', direction: 1 }, context);
    state = reduce(state, { type: 'step', direction: 1 }, context);
    expect(state.selected).toBe(5);
    state = reduce(state, { type: 'shifts', on: true }, context);
    state = reduce(state, { type: 'step', direction: -1 }, context);
    expect(state.selected).toBe(3);
  });

  it('fits the sheet on the first measurement of the window and leaves what the reader did after that', () => {
    const measured = reduce(start, { type: 'viewport', viewport: { width: 800, height: 500 } }, context);
    expect(measured.measured).toBe(true);
    expect(measured.view).toEqual(fitView(A1, { width: 800, height: 500 }));
    const panned = reduce(measured, { type: 'pan', dx: 40, dy: -10 }, context);
    expect(panned.view.offsetX).toBe(measured.view.offsetX + 40);
    const resized = reduce(panned, { type: 'viewport', viewport: { width: 900, height: 500 } }, context);
    expect(resized.view).toEqual(panned.view);
    expect(reduce(resized, { type: 'fit' }, context).view).toEqual(fitView(A1, { width: 900, height: 500 }));
  });

  it('starts in «Рядом» when there is no overlay and refuses to leave it', () => {
    const noOverlay = { ...context, canOverlay: false };
    const state = initialState(noOverlay);
    expect(state.mode).toBe('side');
    expect(reduce(state, { type: 'mode', mode: 'overlay' }, noOverlay)).toBe(state);
  });

  it('shows a text change on the sheet without selecting a difference', () => {
    const state = reduce(reduce(start, { type: 'select', index: 0 }, context), {
      type: 'focus-box', box: { x: 50, y: 60, width: 20, height: 5 },
    }, context);
    expect(state.selected).toBeNull();
    expect(state.view.zoom).toBeGreaterThan(start.view.zoom);
  });

  it('zooms about the centre of the pane without an anchor, and about the pointer with one', () => {
    const centred = reduce(start, { type: 'zoom', factor: 2 }, context);
    expect((500 - centred.view.offsetX) / centred.view.zoom).toBeCloseTo((500 - start.view.offsetX) / start.view.zoom, 6);
    const pointed = reduce(start, { type: 'zoom', factor: 2, anchor: { x: 10, y: 20 } }, context);
    expect((10 - pointed.view.offsetX) / pointed.view.zoom).toBeCloseTo((10 - start.view.offsetX) / start.view.zoom, 6);
  });
});

describe('numbers marked in a text', () => {
  it('marks a changed number where it stands as a whole token and nowhere else', () => {
    expect(markNumbers('Кабель 3x2,5 длиной 120 м, 1120 м', ['120', '2,5'])).toEqual([
      { text: 'Кабель 3x', marked: false }, { text: '2,5', marked: true },
      { text: ' длиной ', marked: false }, { text: '120', marked: true }, { text: ' м, 1120 м', marked: false },
    ]);
    expect(markNumbers('без чисел', ['5'])).toEqual([{ text: 'без чисел', marked: false }]);
    expect(markNumbers('12.5 и 12', ['12'])).toEqual([
      { text: '12.5 и ', marked: false }, { text: '12', marked: true },
    ]);
    expect(markNumbers('120', [])).toEqual([{ text: '120', marked: false }]);
    expect(markNumbers('', ['1'])).toEqual([{ text: '', marked: false }]);
  });
});
