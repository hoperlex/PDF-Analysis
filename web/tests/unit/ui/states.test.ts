import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { EmptyState, LoadingState } from '@/shared/ui';

describe('shared state announcements', () => {
  it('keeps the loading label available while its visual bars are hidden from assistive technology', () => {
    const markup = renderToStaticMarkup(createElement(LoadingState, { what: 'проекты' }));

    expect(markup).toContain('role="status"');
    expect(markup).toContain('Загрузка: проекты…');
    expect(markup).toMatch(/<div class="am-state__loading-lines" aria-hidden="true">/);
    expect(markup.match(/<span><\/span>/g)).toHaveLength(2);
  });

  it('does not show a loading affordance for a resolved empty state', () => {
    const markup = renderToStaticMarkup(createElement(EmptyState, { title: 'Нет проектов' }));

    expect(markup).toContain('Нет проектов');
    expect(markup).not.toContain('am-state__loading-lines');
  });
});
