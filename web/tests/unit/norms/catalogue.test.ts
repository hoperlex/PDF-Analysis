/**
 * `W57B-NORMS-CATALOGUE-XLSX-01` — «Каталог» on «Нормы»: the view is an address, the
 * catalogue renders the server's display names with a link to each document page, its
 * filters are the snapshot's own kinds, and a refusal or a missing current snapshot is said
 * in words, never as an empty table. Rendered in one static pass over seeded caches.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { NormsPage } from '@/_pages/norms';
import {
  NORM_CATALOGUE_PAGE_LIMIT, NORM_SNAPSHOT_LIMIT, normCatalogueQueryOptions,
} from '@/entities/norms';
import { NormCatalogueTable, catalogueAddress } from '@/widgets/norm-catalogue';

import { newClient, renderScreen, seedError } from '../screens/harness';
import { NORM_CATALOGUE_ITEMS, NORM_CATALOGUE_PAGE, NORM_DOCUMENT_ID, NORM_SNAPSHOTS } from './fixtures';

const SNAPSHOTS = queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT);
const CATALOGUE = queryKeys.norms.catalogue(undefined, undefined, undefined, NORM_CATALOGUE_PAGE_LIMIT);
const FILTERED = queryKeys.norms.catalogue('СП 54', 'СП', undefined, NORM_CATALOGUE_PAGE_LIMIT);
const LAST = { next_cursor: null };

function refusal(status: number, code: ErrorCode, details: Record<string, string> = {}): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.6.0',
    error_code: code,
    message: 'English the client never prints.',
    correlation_id: 'cid-catalogue-1',
    retryable: code === 'dependency_unavailable',
    details,
  };
  return new ApiError(status, envelope, 'cid-catalogue-1');
}

function render(seed: (client: ReturnType<typeof newClient>) => void, catalogue: { q: string | null; kind: string | null } | null) {
  const client = newClient();
  seed(client);
  const markup = renderScreen(client, createElement(NormsPage, { roles: ['expert'], catalogue }));
  const asked = client.getQueryCache().getAll().map((query) => String(query.queryKey[1])).sort();
  return { markup, asked };
}

describe('the catalogue view of «Нормы»', () => {
  it('lists the server’s display names, each linking to its document page, with counts and the kinds as filter options', () => {
    const { markup, asked } = render((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      c.setQueryData(CATALOGUE, NORM_CATALOGUE_PAGE);
    }, { q: null, kind: null });
    expect(markup).toContain('data-norm-view="catalogue"');
    expect(markup).toContain('Приказ МЧС России от 24.04.2013 № 288 (ред. от 27.06.2023)');
    expect(markup).toContain('Свод правил. Здания жилые многоквартирные');
    expect(markup).toContain(`href="/norms/document?id=${NORM_DOCUMENT_ID}"`);
    expect(markup).toContain('data-norm-catalogue-total="3"');
    expect(markup).toContain('Документов в текущем снимке: 3.');
    expect(markup).toContain('<option value="СП">СП (2)</option>');
    expect(markup).toContain('data-norm-content="available"');
    expect(markup).toContain('data-norm-content="absent"');
    expect(markup).toContain('name="view" value="catalogue"');
    // The next page is offered; the first page is where it starts.
    expect(markup).toContain('Дальше');
    expect(markup).not.toContain('В начало');
    // No search is sent from the catalogue view.
    expect(asked).toEqual(['catalogue', 'snapshots']);
  });

  it('asks for the filtered page under the filters’ own key', () => {
    const { markup, asked } = render((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      c.setQueryData(FILTERED, { ...NORM_CATALOGUE_PAGE, items: [NORM_CATALOGUE_ITEMS[1]], total: 1, page: LAST });
    }, { q: 'СП 54', kind: 'СП' });
    expect(markup).toContain('Документов под отбор: 1.');
    expect(markup).toContain('value="СП 54"');
    expect(asked).toEqual(['catalogue', 'snapshots']);
    expect(normCatalogueQueryOptions({ q: 'СП 54', kind: 'СП' }, undefined, true).queryKey).toEqual(FILTERED);
  });

  it('before any snapshot is current it renders the refusal and sends no catalogue read', () => {
    const { markup, asked } = render((c) => c.setQueryData(SNAPSHOTS, { items: [], page: LAST }), { q: null, kind: null });
    expect(markup).toContain('data-norms-refusal="no_current_snapshot"');
    expect(asked).toEqual(['snapshots']);
  });

  it('a refused filter is said as a refusal, a failed read with its correlation id', () => {
    const refused = render((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      seedError(c, CATALOGUE, refusal(422, 'validation_failed', { field: 'q', constraint: 'format' }));
    }, { q: null, kind: null });
    expect(refused.markup).toContain('data-norms-catalogue-failure="validation_failed"');
    expect(refused.markup).toContain('Отбор не принят');
    expect(refused.markup).not.toContain('English the client never prints');

    const failed = render((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      seedError(c, CATALOGUE, refusal(503, 'dependency_unavailable'));
    }, { q: null, kind: null });
    expect(failed.markup).toContain('Каталог не прочитан');
    expect(failed.markup).toContain('cid-catalogue-1');

    const none = render((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      seedError(c, CATALOGUE, refusal(422, 'required_norm_unavailable', { reference_kind: 'norms_snapshot' }));
    }, { q: null, kind: null });
    expect(none.markup).toContain('data-norms-refusal="no_current_snapshot"');
  });

  it('the search view stays the default and links to the catalogue', () => {
    const { markup, asked } = render((c) => c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST }), null);
    expect(markup).toContain('data-norm-view="search"');
    expect(markup).toContain(`href="${catalogueAddress().replace('&', '&amp;')}"`);
    expect(asked).toEqual(['snapshots']);
  });
});

describe('the catalogue table’s empty pages', () => {
  it('says why it is empty and never draws an empty table', () => {
    const kept = renderScreen(newClient(), createElement(NormCatalogueTable, { items: [], total: 0, filtered: true, onFirst: null, onNext: null }));
    expect(kept).toContain('Под этот отбор документов нет');
    expect(kept).not.toContain('<table');
    const later = renderScreen(newClient(), createElement(NormCatalogueTable, { items: [], total: 3, filtered: false, onFirst: () => {}, onNext: null }));
    expect(later).toContain('На этой странице документов нет');
    expect(later).toContain('В начало');
  });
});
