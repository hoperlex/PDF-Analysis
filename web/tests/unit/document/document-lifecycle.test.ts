/**
 * Rename and archive on the document page (`R-151a`).
 *
 * A document is archived (out of the lists, nothing deleted, reversible) or renamed (its identity stays); both are
 * confirmed in place. These cases pin the wording that says nothing is deleted, the in-place confirmation and the title
 * rule the server applies (trimmed, 1 to 400 characters).
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { DocumentLifecycleView, titleProblem } from '@/features/manage-document';
import type { DocumentLifecycleViewProps } from '@/features/manage-document';

const noop = (): void => {};

function view(over: Partial<DocumentLifecycleViewProps> = {}): string {
  return renderToStaticMarkup(createElement(DocumentLifecycleView, {
    title: 'Архитектурные решения', archived: false, draft: null, asking: false, busy: false, error: null,
    onEdit: noop, onDraft: noop, onSave: noop, onCancelEdit: noop, onAsk: noop, onConfirm: noop, onCancelAsk: noop,
    ...over,
  }));
}

describe('the document lifecycle controls', () => {
  it('offer «Переименовать» and «В архив» for a document in use', () => {
    const markup = view();
    expect(markup).toContain('>Переименовать<');
    expect(markup).toContain('>В архив<');
    expect(markup).not.toContain('Документ в архиве');
  });

  it('confirm the archive in place and say nothing is deleted', () => {
    const markup = view({ asking: true });
    expect(markup).toContain('Убрать документ в архив? Ничего не удаляется.');
    expect(markup).toContain('>Да, в архив<');
  });

  it('say an archived document is archived and offer to bring it back', () => {
    const markup = view({ archived: true });
    expect(markup).toContain('Документ в архиве');
    expect(markup).toContain('>Вернуть из архива<');
  });

  it('hold «Сохранить» until the title changes and is valid', () => {
    expect(view({ draft: 'Архитектурные решения' })).toMatch(/<button type="submit"[^>]*disabled=""/);
    expect(view({ draft: '   ' })).toContain('Название не может быть пустым.');
    expect(titleProblem('Новое название')).toBeNull();
    expect(titleProblem('x'.repeat(401))).toBe('Название длиннее 400 символов.');
  });
});
