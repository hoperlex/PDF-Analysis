/**
 * The page viewer as markup: its states, its marks and its one control.
 *
 * pdf.js cannot draw here (no canvas, no worker), so the drawing itself is checked in a real
 * browser and reported with the task. What this suite holds is everything around it, as a
 * function of plain props: the viewport a draw would land in, the loading and failure states
 * that stand in for an empty pane, the frames and badges at the positions the view gives them,
 * the active frame, and the pill. Rendered with `renderToStaticMarkup`, as the rest of this
 * directory is: no DOM, no `jsdom`, no testing-library.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { PageViewerViewProps, Placement, ViewerState } from '@/features/open-evidence';
import { PageViewerView } from '@/features/open-evidence';
import { fitView, focusView, makeStage, toScreen } from '@/features/open-evidence/model/view-state';

import { render } from './fixtures';

const BLOB = 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100';
const STAGE = makeStage({ width: 595, height: 842 }, { width: 900, height: 700 }) as NonNullable<ReturnType<typeof makeStage>>;

function placement(id: string, badge: string, top: number, quote?: string): Placement {
  const hull = { left: 60, top, width: 300, height: 26 };
  return {
    target: { id, badge, ...(quote === undefined ? {} : { quote }) },
    resolution: { status: 'found', method: 'lines', occurrences: 1 },
    groups: [
      {
        highlights: [
          { left: 60, top, width: 300, height: 12 },
          { left: 60, top: top + 14, width: 180, height: 12 },
        ],
        hull,
      },
    ],
  };
}

const PLACEMENTS = [placement('q1', '1', 200, 'первая цитата'), placement('q2', '2', 420, 'вторая цитата')];

function props(overrides: Partial<PageViewerViewProps> = {}): PageViewerViewProps {
  return {
    label: 'Страница 7 проверяемого документа',
    state: 'ready',
    documentUrl: BLOB,
    pageNumber: 7,
    pageCount: 31,
    stage: STAGE,
    view: fitView(STAGE),
    placements: PLACEMENTS,
    activeTargetId: 'q1',
    pulse: 0,
    animate: false,
    dragging: false,
    overlay: null,
    onZoomOut: () => {},
    onZoomIn: () => {},
    onFit: () => {},
    onFocus: () => {},
    ...overrides,
  };
}

const draw = (overrides: Partial<PageViewerViewProps> = {}) => render(createElement(PageViewerView, props(overrides)));

describe('the viewport', () => {
  it('is one focusable group named for the page, with the keys it answers to', () => {
    const markup = draw();
    expect(markup).toContain('tabindex="0"');
    expect(markup).toContain('role="group"');
    expect(markup).toContain('aria-label="Страница 7 проверяемого документа. Клавиши «+» и «−» меняют масштаб');
    // The page is one image, named, and the quotation beside it is the evidence.
    expect(markup).toMatch(/<canvas[^>]* role="img" aria-label="Страница 7 проверяемого документа"/);
  });

  it('carries the document, the page and the state on its root', () => {
    for (const state of ['loading', 'ready', 'rendering', 'failed'] as ViewerState[]) {
      const markup = draw({ state });
      expect(markup).toContain(`data-viewer-state="${state}"`);
      expect(markup).toContain(`data-viewer-src="${BLOB}"`);
      expect(markup).toContain('data-viewer-page="7"');
    }
  });

  it('is busy while it loads or reads the next page, and only then', () => {
    expect(draw({ state: 'loading' })).toContain('aria-busy="true"');
    expect(draw({ state: 'rendering' })).toContain('aria-busy="true"');
    expect(draw({ state: 'ready' })).toContain('aria-busy="false"');
  });

  it('shows the drag state for the cursor and whether a move glides', () => {
    expect(draw({ dragging: true })).toContain('data-dragging="true"');
    expect(draw({ dragging: false })).toContain('data-dragging="false"');
    expect(draw({ animate: true })).toContain('data-animate="true"');
    expect(draw({ animate: false })).toContain('data-animate="false"');
  });

  it('lays the sheet out at the fit size and moves it with a transform', () => {
    const view = focusView({ left: 60, top: 200, width: 300, height: 26 }, STAGE);
    const markup = draw({ view });
    expect(markup).toContain(`width:${STAGE.page.width * STAGE.fit}px`);
    expect(markup).toContain(`height:${STAGE.page.height * STAGE.fit}px`);
    expect(markup).toContain(`transform:translate(${view.x}px, ${view.y}px) scale(${view.zoom})`);
    expect(markup).toContain(`data-zoom="${view.zoom}"`);
  });
});

describe('before there is a page', () => {
  it('shows the loading state in the viewport, and hides the sheet and the pill', () => {
    const markup = draw({
      state: 'loading',
      stage: null,
      view: null,
      placements: [],
      overlay: createElement('p', null, 'Загрузка: страницу документа…'),
    });
    expect(markup).toContain('Загрузка: страницу документа…');
    expect(markup).toMatch(/<div class="[^"]*" hidden="">\s*<canvas|<div class="[^"]*" hidden=""><canvas/);
    expect(markup).not.toContain('Масштаб страницы');
    expect(markup).not.toContain('Перетаскивайте');
    expect(markup).not.toContain('Фрагмент 1');
  });

  it('shows a failure in the viewport and no page under it', () => {
    const markup = draw({
      state: 'failed',
      overlay: createElement('p', null, 'Страницу не удалось показать'),
    });
    expect(markup).toContain('Страницу не удалось показать');
    expect(markup).toMatch(/hidden=""/);
    expect(markup).not.toContain('Фрагмент 1');
    expect(markup).not.toContain('Масштаб страницы');
  });
});

describe('the marks', () => {
  it('draws a highlight per line and one framed, numbered button per target', () => {
    const markup = draw();
    expect(markup.match(/aria-hidden="true"/g)?.length).toBeGreaterThanOrEqual(4);
    expect(markup.match(/data-target-id="/g)).toHaveLength(2);
    expect(markup).toContain('aria-label="Фрагмент 1"');
    expect(markup).toContain('aria-label="Фрагмент 2"');
    expect(markup).toMatch(/<span class="[^"]*">1<\/span>/);
    expect(markup).toMatch(/<span class="[^"]*">2<\/span>/);
  });

  it('puts each frame where the view puts the lines, grown by its padding', () => {
    const view = fitView(STAGE);
    const box = toScreen(PLACEMENTS[0]!.groups[0]!.hull, view, STAGE);
    const grown = (value: number) => Math.round(value * 10) / 10;
    expect(draw({ view })).toContain(
      `transform:translate(${grown(box.left - 5)}px, ${grown(box.top - 5)}px);width:${grown(box.width + 10)}px;height:${grown(box.height + 10)}px`,
    );
  });

  it('follows the view: the same target is somewhere else after a zoom', () => {
    const near = draw({ view: fitView(STAGE) });
    const far = draw({ view: focusView(PLACEMENTS[1]!.groups[0]!.hull, STAGE) });
    expect(near).not.toBe(far);
  });

  it('marks exactly one frame active, the chosen one, and its highlights', () => {
    const markup = draw({ activeTargetId: 'q2' });
    const frames = [...markup.matchAll(/<button[^>]*data-active="(true|false)"[^>]*data-target-id="(q\d)"/g)].map((m) => [m[2], m[1]]);
    expect(frames).toEqual([['q1', 'false'], ['q2', 'true']]);
    expect(markup.match(/data-active="true"/g)).toHaveLength(1 + 2);
  });

  it('marks nothing active when nothing is', () => {
    expect(draw({ activeTargetId: null })).not.toContain('data-active="true"');
  });

  it('names the quotation in the tooltip of its frame, as the server sent it', () => {
    const markup = draw();
    expect(markup).toContain('title="первая цитата"');
    expect(markup).toContain('title="вторая цитата"');
  });

  it('numbers the occurrences when a quotation is framed more than once', () => {
    const twice: Placement = {
      ...placement('q1', '1', 200),
      resolution: { status: 'found', method: 'text', occurrences: 2 },
      groups: [placement('q1', '1', 200).groups[0]!, placement('q1', '1', 500).groups[0]!],
    };
    const markup = draw({ placements: [twice] });
    expect(markup).toContain('aria-label="Фрагмент 1, совпадение 1 из 2"');
    expect(markup).toContain('aria-label="Фрагмент 1, совпадение 2 из 2"');
  });

  it('draws nothing for a target nothing could place', () => {
    const lost: Placement = {
      target: { id: 'q3', badge: '3', quote: 'нигде' },
      resolution: { status: 'not-found', method: null, occurrences: 0 },
      groups: [],
    };
    const markup = draw({ placements: [lost] });
    expect(markup).not.toContain('data-target-id');
    expect(markup).not.toContain('Фрагмент 3');
  });

  it('keeps the old page and its marks while the next one is read, and they stay in the markup', () => {
    const markup = draw({ state: 'rendering' });
    expect(markup).toContain('data-viewer-state="rendering"');
    expect(markup).toContain('aria-label="Фрагмент 1"');
  });
});

describe('the one control', () => {
  it('is a small pill: less, the percentage of the whole-page fit, more, and a way to the target', () => {
    const markup = draw();
    expect(markup).toContain('role="group" aria-label="Масштаб страницы"');
    expect(markup).toContain('aria-label="Уменьшить"');
    expect(markup).toContain('aria-label="Приблизить"');
    expect(markup).toContain('aria-label="Масштаб 100 %. Показать страницу целиком"');
    expect(markup).toContain('>100 %<');
    expect(markup).toContain('aria-label="К фрагменту"');
    for (const title of ['Уменьшить (клавиша «−»)', 'Приблизить (клавиша «+»)', 'Показать страницу целиком (клавиша «0»)', 'К фрагменту']) {
      expect(markup).toContain(`title="${title}"`);
    }
  });

  it('says the zoom as a percentage', () => {
    const view = focusView({ left: 60, top: 200, width: 300, height: 26 }, STAGE);
    expect(draw({ view })).toContain(`>${Math.round(view.zoom * 100)} %<`);
  });

  it('offers the way to the target only when something is framed', () => {
    expect(draw({ placements: [] })).not.toContain('К фрагменту');
    const lost: Placement = {
      target: { id: 'q3', badge: '3' },
      resolution: { status: 'not-found', method: null, occurrences: 0 },
      groups: [],
    };
    expect(draw({ placements: [lost] })).not.toContain('К фрагменту');
  });

  it('is the only chrome: no toolbar, no thumbnails, no page list', () => {
    const markup = draw();
    expect(markup).not.toContain('<object');
    expect(markup).not.toContain('<nav');
    expect(markup).not.toContain('thumbnail');
    expect(markup.match(/<button/g)?.length).toBe(4 + 2);
  });
});

describe('the line under the viewport', () => {
  it('says how to move the page, and which page of how many', () => {
    const markup = draw();
    expect(markup).toContain('Перетаскивайте страницу, Ctrl + колесо — масштаб, двойной щелчок — приблизить.');
    expect(markup).toContain('Страница 7 из 31');
  });

  it('says the page alone until the document has said how many it has', () => {
    expect(draw({ pageCount: null })).toContain('>Страница 7<');
  });
});
