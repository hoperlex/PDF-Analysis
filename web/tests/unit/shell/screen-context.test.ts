import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ScreenContextView } from '@/_app/screen-context';

const draw = (pathname: string | null) => renderToStaticMarkup(createElement(ScreenContextView, { pathname }));

describe('topbar screen context', () => {
  it('follows the registry across top-level and nested routes', () => {
    expect(draw('/')).toContain('Главная</strong>');
    expect(draw('/blocks')).toContain('Знания</span>');
    expect(draw('/blocks')).toContain('Блоки</strong>');
    const nested = draw('/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B');
    expect(nested).toContain('Работа</span>');
    expect(nested).toContain('Проект</strong>');
    expect(nested).not.toContain('prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B');
  });

  it('uses neutral context for an unknown or unavailable pathname', () => {
    for (const path of ['/no-such-screen', null]) {
      expect(draw(path)).toContain('aria-label="Текущий раздел"');
      expect(draw(path)).toContain('>AuditManager</span>');
    }
  });
});
