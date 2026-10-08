import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ReleaseEntry } from '@/shared/api';
import { UnknownReleaseKindError, releaseDate, releaseKindLabel } from '@/entities/release';
import { VersionHistoryView } from '@/widgets/version-history';
import { UpdateBannerView, WhatsNewView } from '@/_app/release-notices';

const CURRENT: ReleaseEntry = {
  version: '0.3.0', revision: 1, date: '2026-10-08', title: 'История улучшений',
  is_archive: false, range_label: null,
  items: [{ kind: 'improved', screen: 'home', where: 'Работа › Главная', text: 'Д'.repeat(400) }],
};
const ARCHIVE: ReleaseEntry = {
  ...CURRENT, version: '0.2.0', is_archive: true, range_label: '0.1–0.2',
  title: 'Прототип и альфа',
};
const noop = () => undefined;

describe('release history presentation', () => {
  it('keeps the authored date and 400-character text without linking historical screens', () => {
    const html = renderToStaticMarkup(createElement(VersionHistoryView, {
      version: '0.3.0', listing: { items: [CURRENT, ARCHIVE], whats_new: [] },
      loading: false, error: null, onClose: noop, onRetry: noop,
    }));
    expect(html).toContain('Текущая версия: 0.3.0');
    expect(html).toContain('08.10.2026');
    expect(html).toContain('Д'.repeat(400));
    expect(html).toContain('Архив (1)');
    expect(html).toMatch(/<details[^>]*>/);
    expect(html).not.toMatch(/<details[^>]* open/);
    expect(html).not.toContain('href=');
    expect(releaseDate('2026-10-08')).toBe('08.10.2026');
  });

  it('shows loading, empty and an unknown-kind fault as different states', () => {
    const draw = (props: { loading: boolean; error: Error | null; items: ReleaseEntry[] }) =>
      renderToStaticMarkup(createElement(VersionHistoryView, {
        version: null, listing: { items: props.items, whats_new: [] },
        loading: props.loading, error: props.error, onClose: noop, onRetry: noop,
      }));
    expect(draw({ loading: true, error: null, items: [] })).toContain('Загрузка: истории версий…');
    expect(draw({ loading: false, error: null, items: [] })).toContain('История версий пока пуста');
    expect(draw({ loading: false, error: new UnknownReleaseKindError(), items: [] })).toContain('Неизвестная категория изменения');
    expect(() => releaseKindLabel('unknown')).toThrow(UnknownReleaseKindError);
  });

  it('shows only server-selected What’s New entries and leaves navigation free', () => {
    const html = renderToStaticMarkup(createElement(WhatsNewView, {
      listing: { items: [CURRENT, ARCHIVE], whats_new: ['0.3.0'] }, newest: '0.3.0', onClose: noop,
    }));
    expect(html).toContain('История улучшений');
    expect(html).not.toContain('Прототип и альфа');
    expect(html).toContain('aria-modal="false"');
    expect(renderToStaticMarkup(createElement(UpdateBannerView, { onUpdate: noop, onLater: noop })))
      .toContain('Доступна новая версия');
  });
});
