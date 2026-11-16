import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { EmptyState, LoadingState } from '@/shared/ui';

describe('shared state announcements', () => {
  it('keeps the loading label available while its visual bars are hidden from assistive technology', () => {
    const markup = renderToStaticMarkup(createElement(LoadingState, { what: 'объекты' }));

    expect(markup).toContain('role="status"');
    expect(markup).toContain('Загрузка: объекты…');
    expect(markup).toMatch(/<div class="am-state__loading-lines" aria-hidden="true">/);
    expect(markup.match(/<span><\/span>/g)).toHaveLength(2);
  });

  it('does not show a loading affordance for a resolved empty state', () => {
    const markup = renderToStaticMarkup(createElement(EmptyState, { title: 'Нет объектов' }));

    expect(markup).toContain('Нет объектов');
    expect(markup).not.toContain('am-state__loading-lines');
  });
});
