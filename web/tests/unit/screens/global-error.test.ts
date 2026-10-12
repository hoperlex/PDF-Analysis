/**
 * `C-24` — `app/global-error.tsx`, the boundary for a failure in the root layout itself.
 *
 * Next renders it in place of the whole layout, so it must write its own `<html>` and
 * `<body>`; and like `app/error.tsx` it must be Russian and print nothing of the error.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import GlobalError from '@/app/global-error';

import { WEB_ROOT } from '../../guards/lib/repo';

const thrown = Object.assign(new TypeError('Cannot read properties of undefined (reading layout)'), {
  digest: '2718281828',
});

function visibleText(markup: string): string[] {
  return [...markup.matchAll(/>([^<>]+)</g)].map((match) => (match[1] ?? '').trim()).filter(Boolean);
}

describe('the root-layout error boundary', () => {
  const markup = renderToStaticMarkup(createElement(GlobalError, { error: thrown, reset: () => {} }));

  it('is a client component that writes its own document, in Russian', () => {
    const source = readFileSync(join(WEB_ROOT, 'src/app/global-error.tsx'), 'utf8');
    expect(source.trimStart().startsWith("'use client'")).toBe(true);
    expect(markup).toMatch(/^<html lang="ru">(?:<head><\/head>)?<body>/);
    expect(markup.endsWith('</body></html>')).toBe(true);
    expect(markup).toContain('Приложение не открылось');
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Открыть ещё раз');
  });

  it('prints nothing of the error but its opaque digest', () => {
    expect(markup).not.toContain(thrown.message);
    expect(markup).not.toContain('TypeError');
    expect(markup).not.toContain(thrown.stack?.split('\n')[1]?.trim() ?? 'unreachable');
    expect(markup).toContain('<code>2718281828</code>');
    const latin = visibleText(markup.replace(/<code>[\s\S]*?<\/code>/g, ''))
      .flatMap((text) => text.match(/[A-Za-z]+/g) ?? []);
    expect(latin).toEqual([]);
  });

  it('omits the digest line when there is none', () => {
    const plain = renderToStaticMarkup(createElement(GlobalError, { error: new Error('x'), reset: () => {} }));
    expect(plain).not.toContain('<code>');
    expect(plain).not.toContain('Идентификатор');
  });
});
